"""
main.py
Entry point for the github_news OpenClaw skill.

Reads a single JSON object from stdin, dispatches to the right module,
and prints a Markdown-formatted result to stdout.

Input schema
------------
{
    "action":           "trending" | "language_trends" | "search",  // required
    "language":         str,   // optional — filter/target language
    "since":            str,   // optional — "daily" | "weekly" | "monthly"  (trending)
    "query":            str,   // optional — free-text keywords  (search)
    "spoken_language":  str,   // optional — ISO code e.g. "en"  (trending)
    "pushed_within_days": int, // optional — recency filter  (search / language_trends)
    "per_page":         int,   // optional — results per page  (search, default 10)
    "top_n":            int    // optional — repos to analyse  (language_trends, default 30)
}

Actions
-------
trending        — Scrape github.com/trending and return a ranked Markdown table.
language_trends — Aggregate language distribution via GitHub search API.
search          — Keyword search sorted by stars, rendered as a Markdown table.

Output
------
Plain Markdown printed to stdout.  On error a short Markdown error block is
printed to stdout and the process exits with code 1.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make sure sibling modules are importable when invoked as  python src/main.py
sys.path.insert(0, str(Path(__file__).parent))

from github_trending import fetch_trending
from github_api import search_repos, language_stats


def _trunc(text: str, max_len: int = 72) -> str:
    """Truncate *text* and append … if it exceeds *max_len* characters."""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _stars(n: int) -> str:
    """Format star counts with k/M suffix for readability."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M ⭐"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k ⭐"
    return f"{n} ⭐"


def _fmt_trending(repos: list[dict], since: str) -> str:
    lines = [
        f"## 🔥 GitHub Trending — {since.capitalize()}",
        f"_Source: <https://github.com/trending>_",
        "",
    ]
    for r in repos:
        lang = f" · {r['language']}" if r.get("language") else ""
        period_note = f" (+{r['period_stars']:,} this {since.rstrip('ly')})" if r.get("period_stars") else ""
        desc = _trunc(r["description"])
        lines.append(
            f"**{r['rank']}.** [{r['full_name']}]({r['url']}){lang}  \n"
            f"  {_stars(r['stars'])} · {r['forks']:,} forks{period_note}  \n"
            f"  _{desc}_\n"
        )
    return "\n".join(lines)


def _fmt_search(repos: list[dict], query: str) -> str:
    lines = [
        f"## 🔍 GitHub Search — \"{query}\"",
        f"_Sorted by stars · Source: GitHub REST API_",
        "",
    ]
    for i, r in enumerate(repos, start=1):
        lang = f" · {r['language']}" if r.get("language") else ""
        desc = _trunc(r["description"])
        lines.append(
            f"**{i}.** [{r['full_name']}]({r['url']}){lang}  \n"
            f"  {_stars(r['stars'])} · {r['forks']:,} forks  \n"
            f"  _{desc}_\n"
        )
    return "\n".join(lines)


def _fmt_language_trends(stats: list[dict], query: str) -> str:
    lines = [
        f"## 📊 Language Trends — \"{query}\"",
        "_Language distribution across top GitHub search results_",
        "",
    ]
    bar_width = 20
    for i, s in enumerate(stats, start=1):
        filled = round(s["pct"] / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        lines.append(f"**{i}.** {s['language']:20s}  `{bar}`  {s['pct']:.1f}%  ({s['count']} repos)")
    return "\n".join(lines)


def _error(msg: str) -> str:
    return f"❌ **Error:** {msg}"


# ── dispatch ──────────────────────────────────────────────────────────────


def run(payload: dict) -> str:
    action = payload.get("action", "").strip().lower()

    if action == "trending":
        since = payload.get("since", "daily")
        language = payload.get("language", "")
        spoken = payload.get("spoken_language", "")
        repos = fetch_trending(language=language, spoken_language=spoken, since=since)
        if not repos:
            return _error("No trending repos found for the given filters.")
        return _fmt_trending(repos, since)

    elif action == "search":
        query = payload.get("query", "").strip()
        if not query:
            return _error("'query' is required for action='search'.")
        language = payload.get("language", "")
        pushed_within_days = int(payload.get("pushed_within_days", 0))
        per_page = int(payload.get("per_page", 10))
        repos = search_repos(
            query,
            language=language,
            pushed_within_days=pushed_within_days,
            per_page=per_page,
        )
        if not repos:
            return _error(f"No results found for query: {query!r}")
        return _fmt_search(repos, query)

    elif action == "language_trends":
        query = payload.get("query", "").strip()
        if not query:
            return _error("'query' is required for action='language_trends'.")
        top_n = int(payload.get("top_n", 30))
        pushed_within_days = int(payload.get("pushed_within_days", 0))
        stats = language_stats(query, top_n=top_n, pushed_within_days=pushed_within_days)
        if not stats:
            return _error(f"No results found for query: {query!r}")
        return _fmt_language_trends(stats, query)

    else:
        valid = "'trending', 'search', 'language_trends'"
        return _error(
            f"Unknown action: {action!r}. Valid actions are: {valid}"
        )


# ── entry point ───────────────────────────────────────────────────────────


def main() -> None:
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            print(_error("Empty input — expected a JSON object on stdin."))
            sys.exit(1)
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(_error(f"Invalid JSON input: {exc}"))
        sys.exit(1)

    try:
        output = run(payload)
        print(output)
    except Exception as exc:  # noqa: BLE001
        print(_error(str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    main()

