"""
github_trending.py
Scrape https://github.com/trending (and /trending/{language}) and return a
list of repository dicts.

Each dict contains:
    rank            int   — 1-based position on the trending page
    owner           str
    name            str
    full_name       str   — "owner/name"
    url             str   — full GitHub URL
    description     str   — may be empty string
    language        str   — may be empty string
    stars           int   — total stargazers count
    forks           int   — total forks count
    period_stars    int   — stars earned in the requested period
    since           str   — "daily" | "weekly" | "monthly"
"""

from __future__ import annotations

import re
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://github.com"
TRENDING_URL = f"{BASE_URL}/trending"

# Polite defaults
DEFAULT_TIMEOUT = 15
DEFAULT_HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": (
        "Mozilla/5.0 (compatible; github-news-skill/1.0; "
        "+https://github.com/skill-github-news)"
    ),
}

VALID_SINCE = {"daily", "weekly", "monthly"}


def _int(text: str) -> int:
    """Strip commas/spaces and convert to int; return 0 on failure."""
    try:
        return int(re.sub(r"[,\s]", "", text))
    except (ValueError, TypeError):
        return 0


def _parse_repos(html: str, since: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    articles = soup.select("article.Box-row")
    repos: list[dict] = []

    for rank, article in enumerate(articles, start=1):
        # ── owner / name ──────────────────────────────────────────────────
        link_tag = article.select_one("h2 a")
        if not link_tag:
            continue
        href = link_tag.get("href", "").strip("/")          # "owner/repo"
        parts = href.split("/")
        if len(parts) < 2:
            continue
        owner, name = parts[0], parts[1]

        # ── description ───────────────────────────────────────────────────
        desc_tag = article.select_one("p.col-9")
        description = desc_tag.get_text(strip=True) if desc_tag else ""

        # ── language ──────────────────────────────────────────────────────
        lang_tag = article.select_one('span[itemprop="programmingLanguage"]')
        language = lang_tag.get_text(strip=True) if lang_tag else ""

        # ── total stars ───────────────────────────────────────────────────
        stars_tag = article.select_one('a[href$="/stargazers"]')
        stars = _int(stars_tag.get_text(strip=True)) if stars_tag else 0

        # ── total forks ───────────────────────────────────────────────────
        forks_tag = article.select_one('a[href$="/forks"]')
        forks = _int(forks_tag.get_text(strip=True)) if forks_tag else 0

        # ── period stars  ("1,342 stars today" / "23 stars this week") ───
        period_tag = article.select_one("span.d-inline-block.float-sm-right")
        period_stars = 0
        if period_tag:
            m = re.search(r"([\d,]+)\s+stars?", period_tag.get_text())
            if m:
                period_stars = _int(m.group(1))

        repos.append(
            {
                "rank": rank,
                "owner": owner,
                "name": name,
                "full_name": f"{owner}/{name}",
                "url": f"{BASE_URL}/{owner}/{name}",
                "description": description,
                "language": language,
                "stars": stars,
                "forks": forks,
                "period_stars": period_stars,
                "since": since,
            }
        )

    return repos


def fetch_trending(
    language: str = "",
    spoken_language: str = "",
    since: str = "daily",
    *,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = 2,
    retry_delay: float = 2.0,
) -> list[dict]:
    """
    Scrape GitHub Trending and return a list of repo dicts.

    Parameters
    ----------
    language : str
        GitHub language slug, e.g. "python", "typescript", "c++".
        Empty string means "all languages".
    spoken_language : str
        Spoken-language code, e.g. "en", "zh".
        Empty string means "any language".
    since : str
        One of "daily" (default), "weekly", "monthly".
    timeout : int
        HTTP request timeout in seconds.
    retries : int
        Number of additional attempts on transient failures.
    retry_delay : float
        Seconds to wait between retries.

    Returns
    -------
    list[dict]
        Up to 25 repo dicts (GitHub's trending page cap).

    Raises
    ------
    ValueError
        If *since* is not one of the accepted values.
    requests.HTTPError
        On a non-2xx response after all retries are exhausted.
    """
    if since not in VALID_SINCE:
        raise ValueError(f"'since' must be one of {VALID_SINCE}, got {since!r}")

    # Build URL  ────────────────────────────────────────────────────────────
    path = "/trending"
    if language:
        # GitHub slugifies languages: spaces → -, keep lower-case
        lang_slug = language.strip().lower().replace(" ", "-").replace("+", "%2B")
        path += f"/{lang_slug}"

    params: dict[str, str] = {"since": since}
    if spoken_language:
        params["spoken_language_code"] = spoken_language.strip().lower()

    url = f"{BASE_URL}{path}"

    # Fetch with retry  ─────────────────────────────────────────────────────
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url,
                params=params,
                headers=DEFAULT_HEADERS,
                timeout=timeout,
            )
            resp.raise_for_status()
            return _parse_repos(resp.text, since)
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(retry_delay)

    raise last_exc  # type: ignore[misc]


# ── CLI smoke-test ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    repos = fetch_trending(since="daily")
    print(json.dumps(repos[:3], indent=2, ensure_ascii=False))

