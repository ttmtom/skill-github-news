---
name: github_news
description: Scrapes GitHub Trending and queries the GitHub REST API to deliver trending repos, language trends, and open-source updates.
metadata: {"openclaw": {"emoji": "📰", "requires": {"bins": ["python3"]}, "primaryEnv": "GITHUB_TOKEN"}}
---

# GitHub News

Fetch trending repositories, search open-source projects, and analyze language trends from GitHub.

## Usage

Trigger this skill with phrases like:

- "show trending repos"
- "what's trending in Python this week"
- "search open source projects about LLM"
- "show language trends"
- "trending Rust repos this month"

## Actions

| Action            | Description                                                                |
|-------------------|----------------------------------------------------------------------------|
| `trending`        | Scrape GitHub Trending with optional language, spoken-language, and period. |
| `search`          | Search repositories via the GitHub REST API by keyword, sorted by stars.   |
| `language_trends` | Aggregate language distribution across top search or trending results.     |

## How to invoke

Pass a JSON object via stdin to `{baseDir}/src/main.py`:

```bash
echo '{"action": "trending", "language": "python", "since": "weekly"}' | python3 {baseDir}/src/main.py
```

### Parameters

| Parameter         | Type   | Default  | Description                                              |
|-------------------|--------|----------|----------------------------------------------------------|
| `action`          | string | —        | One of `trending`, `search`, `language_trends`.          |
| `language`        | string | `""`     | Programming language filter (e.g. `python`, `rust`).     |
| `since`           | string | `daily`  | Time range: `daily`, `weekly`, or `monthly`.             |
| `query`           | string | `""`     | Search keyword(s) (used by `search` and `language_trends`). |
| `spoken_language` | string | `""`     | Spoken-language filter code (e.g. `en`, `zh`).           |

## Setup

Install dependencies before first use:

```bash
pip install -r {baseDir}/requirements.txt
```

## Environment

| Variable       | Required | Description                                                                                   |
|----------------|----------|-----------------------------------------------------------------------------------------------|
| `GITHUB_TOKEN` | Optional | Personal access token for the GitHub API. Unauthenticated: 60 req/hr; authenticated: 5,000 req/hr. |

## Output

Results are formatted as a Markdown table with columns: rank, name, stars, forks, and description.
