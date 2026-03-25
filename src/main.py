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

# ── helpers ───────────────────────────────────────────────────────────────


def _trunc(text: str, max_len: int = 72) -> str:
    """Truncate *text* and append … if it exceeds *max_len* characters."""
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _fmt_trending(repos: list[dict], since: str) -> str:
    result = {
        "title": "GitHub Trending",
        "period": since.capitalize(),
        "source": "https://github.com/trending",
        "repos": [
            {
                "rank": r["rank"],
                "full_name": r["full_name"],
                "url": r["url"],
                "stars": r["stars"],
                "forks": r["forks"],
                "period_stars": r["period_stars"],
                "language": r["language"] or None,
                "description": _trunc(r["description"]),
            }
            for r in repos
        ],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _fmt_search(repos: list[dict], query: str) -> str:
    result = {
        "title": f'GitHub Search — "{query}"',
        "query": query,
        "source": "https://api.github.com",
        "sorted_by": "stars",
        "repos": [
            {
                "rank": i,
                "full_name": r["full_name"],
                "url": r["url"],
                "stars": r["stars"],
                "forks": r["forks"],
                "language": r["language"] or None,
                "description": _trunc(r["description"]),
            }
            for i, r in enumerate(repos, start=1)
        ],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _fmt_language_trends(stats: list[dict], query: str) -> str:
    result = {
        "title": f'Language Trends — "{query}"',
        "source": "GitHub Search API — language distribution across top results",
        "languages": [
            {
                "rank": i,
                "language": s["language"],
                "repos": s["count"],
                "share_pct": s["pct"],
            }
            for i, s in enumerate(stats, start=1)
        ],
    }
    return json.dumps(result, ensure_ascii=False, indent=2)


def _error(msg: str) -> str:
    return json.dumps({"error": msg}, ensure_ascii=False, indent=2)


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

