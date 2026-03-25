"""
github_api.py
Wrapper around the GitHub REST API (api.github.com) for:
  (a) search_repos  — keyword search sorted by stars, optional date-range filter
  (b) get_repo      — single repository detail fetch
  (c) language_stats — language distribution across the top N search results

Authentication
--------------
Set the GITHUB_TOKEN environment variable to raise the rate-limit from
60 req/hr (unauthenticated) to 5 000 req/hr (authenticated).
"""

from __future__ import annotations

import os
import time
from datetime import date, timedelta
from typing import Optional
from collections import Counter

import requests

API_BASE = "https://api.github.com"
DEFAULT_TIMEOUT = 15
DEFAULT_HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": (
        "github-news-skill/1.0 (+https://github.com/skill-github-news)"
    ),
}


def _session() -> requests.Session:
    """Return a Session with auth header injected when GITHUB_TOKEN is set."""
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        s.headers["Authorization"] = f"Bearer {token}"
    return s


def _get(
    session: requests.Session,
    url: str,
    params: Optional[dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retries: int = 2,
    retry_delay: float = 2.0,
) -> dict:
    """GET *url* with retry / back-off; raises on final failure."""
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, params=params, timeout=timeout)
            # Surface the rate-limit message when available
            if resp.status_code == 403:
                msg = resp.json().get("message", resp.text)
                raise requests.HTTPError(f"403 Forbidden: {msg}", response=resp)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(retry_delay)
    raise last_exc  # type: ignore[misc]


# ── (a) Keyword search ────────────────────────────────────────────────────


def search_repos(
    query: str,
    *,
    language: str = "",
    pushed_within_days: int = 0,
    since_date: Optional[str] = None,
    sort: str = "stars",
    order: str = "desc",
    per_page: int = 10,
    page: int = 1,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """
    Search GitHub repositories by keyword, sorted by stars by default.

    Parameters
    ----------
    query : str
        Free-text search terms.
    language : str
        Restrict results to this programming language, e.g. "python".
    pushed_within_days : int
        If > 0, add a ``pushed:>YYYY-MM-DD`` qualifier so only recently
        active repos are returned.  Ignored when *since_date* is given.
    since_date : str | None
        Explicit ISO date string ``"YYYY-MM-DD"`` used as the ``pushed:>``
        lower bound.  Overrides *pushed_within_days*.
    sort : str
        GitHub sort field: "stars" | "forks" | "help-wanted-issues" |
        "updated".  Default "stars".
    order : str
        "desc" (default) or "asc".
    per_page : int
        Results per page (1–100).  Default 10.
    page : int
        1-based page number.  Default 1.

    Returns
    -------
    list[dict]
        Normalised repo dicts — same shape as :func:`get_repo`.
    """
    q_parts = [query.strip()]

    if language:
        q_parts.append(f"language:{language.strip()}")

    if since_date:
        q_parts.append(f"pushed:>{since_date}")
    elif pushed_within_days > 0:
        cutoff = (date.today() - timedelta(days=pushed_within_days)).isoformat()
        q_parts.append(f"pushed:>{cutoff}")

    params = {
        "q": " ".join(q_parts),
        "sort": sort,
        "order": order,
        "per_page": min(max(per_page, 1), 100),
        "page": page,
    }

    session = _session()
    data = _get(session, f"{API_BASE}/search/repositories", params=params, timeout=timeout)
    return [_normalise(item) for item in data.get("items", [])]


# ── (b) Single repo detail ────────────────────────────────────────────────


def get_repo(owner: str, repo: str, *, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """
    Fetch details for a single repository.

    Parameters
    ----------
    owner : str
        Repository owner (user or organisation).
    repo : str
        Repository name.

    Returns
    -------
    dict
        Normalised repo dict.
    """
    session = _session()
    data = _get(session, f"{API_BASE}/repos/{owner}/{repo}", timeout=timeout)
    return _normalise(data)


# ── (c) Language distribution ─────────────────────────────────────────────


def language_stats(
    query: str,
    *,
    top_n: int = 30,
    pushed_within_days: int = 0,
    timeout: int = DEFAULT_TIMEOUT,
) -> list[dict]:
    """
    Aggregate the language distribution across the top *top_n* search results.

    Parameters
    ----------
    query : str
        Free-text search terms (same as :func:`search_repos`).
    top_n : int
        Number of top results to inspect (max 100).  Default 30.
    pushed_within_days : int
        Same as in :func:`search_repos`.

    Returns
    -------
    list[dict]
        Sorted list of ``{"language": str, "count": int, "pct": float}``
        dicts, most popular first.  Repos with no declared language are
        counted under ``"(unknown)"``.
    """
    repos = search_repos(
        query,
        pushed_within_days=pushed_within_days,
        per_page=min(top_n, 100),
        timeout=timeout,
    )

    counts: Counter[str] = Counter()
    for r in repos:
        lang = r.get("language") or "(unknown)"
        counts[lang] += 1

    total = len(repos) or 1  # avoid division by zero
    return [
        {"language": lang, "count": cnt, "pct": round(cnt / total * 100, 1)}
        for lang, cnt in counts.most_common()
    ]


# ── Internal normalisation ────────────────────────────────────────────────


def _normalise(raw: dict) -> dict:
    """
    Convert a raw GitHub API repo object into the canonical shape used
    throughout the skill.
    """
    owner_obj = raw.get("owner") or {}
    return {
        "full_name": raw.get("full_name", ""),
        "owner": owner_obj.get("login", ""),
        "name": raw.get("name", ""),
        "url": raw.get("html_url", ""),
        "description": raw.get("description") or "",
        "language": raw.get("language") or "",
        "stars": raw.get("stargazers_count", 0),
        "forks": raw.get("forks_count", 0),
        "open_issues": raw.get("open_issues_count", 0),
        "watchers": raw.get("watchers_count", 0),
        "topics": raw.get("topics", []),
        "license": (raw.get("license") or {}).get("spdx_id", ""),
        "created_at": raw.get("created_at", ""),
        "pushed_at": raw.get("pushed_at", ""),
        "archived": raw.get("archived", False),
    }


# ── CLI smoke-test ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    print("=== search_repos(llm, language=python, pushed_within_days=30) ===")
    results = search_repos("llm", language="python", pushed_within_days=30, per_page=3)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    print("\n=== get_repo(torvalds, linux) ===")
    detail = get_repo("torvalds", "linux")
    print(json.dumps(detail, indent=2, ensure_ascii=False))

    print("\n=== language_stats(ai agent, top_n=20) ===")
    stats = language_stats("ai agent", top_n=20)
    print(json.dumps(stats, indent=2, ensure_ascii=False))

