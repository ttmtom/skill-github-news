# 📰 skill-github-news

An [OpenClaw](https://github.com/openclaw) skill that scrapes **GitHub Trending** and queries the **GitHub REST API** to deliver trending repositories, open-source project search, and language distribution analysis — all as structured JSON output.

---

## Features

| Action | Description |
|---|---|
| `trending` | Scrape [github.com/trending](https://github.com/trending) — filter by language, spoken language, and time period |
| `search` | Search repositories via the GitHub REST API by keyword, sorted by stars |
| `language_trends` | Aggregate language distribution across top search results |

---

## Requirements

- Python 3.8+
- Internet access to reach `github.com` and `api.github.com`

---

## Installation

```bash
pip install -r requirements.txt
```

Dependencies: `requests`, `beautifulsoup4`, `lxml`

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GITHUB_TOKEN` | Optional | GitHub personal access token. Raises rate limit from 60 req/hr (unauthenticated) to 5,000 req/hr (authenticated). |

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

---

## Usage

Pass a JSON object via **stdin** to `src/main.py`. Output is a JSON object printed to **stdout**.

```bash
echo '<json payload>' | python3 src/main.py
```

### Action: `trending`

Scrape GitHub's trending page.

```bash
echo '{"action": "trending"}' | python3 src/main.py
```

```bash
# Trending Python repos this week
echo '{"action": "trending", "language": "python", "since": "weekly"}' | python3 src/main.py

# Trending Rust repos this month, English repos only
echo '{"action": "trending", "language": "rust", "since": "monthly", "spoken_language": "en"}' | python3 src/main.py
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `language` | string | `""` | Programming language filter (e.g. `python`, `rust`, `typescript`) |
| `since` | string | `"daily"` | Time range: `daily`, `weekly`, or `monthly` |
| `spoken_language` | string | `""` | Spoken-language filter code (e.g. `en`, `zh`) |

**Example output:**

```json
{
  "title": "GitHub Trending",
  "period": "Weekly",
  "source": "https://github.com/trending",
  "repos": [
    {
      "rank": 1,
      "full_name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "stars": 42000,
      "forks": 3100,
      "period_stars": 2500,
      "language": "Python",
      "description": "An amazing open-source project"
    }
  ]
}
```

---

### Action: `search`

Search GitHub repositories by keyword, sorted by stars.

```bash
echo '{"action": "search", "query": "LLM agent"}' | python3 src/main.py

# Search Python LLM repos updated in the last 30 days, top 20 results
echo '{"action": "search", "query": "LLM", "language": "python", "pushed_within_days": 30, "per_page": 20}' | python3 src/main.py
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | — | **Required.** Search keyword(s) |
| `language` | string | `""` | Programming language filter |
| `pushed_within_days` | int | `0` | Only include repos pushed within N days (0 = no filter) |
| `per_page` | int | `10` | Number of results to return (max 100) |

**Example output:**

```json
{
  "title": "GitHub Search — \"LLM agent\"",
  "query": "LLM agent",
  "source": "https://api.github.com",
  "sorted_by": "stars",
  "repos": [
    {
      "rank": 1,
      "full_name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "stars": 18000,
      "forks": 1200,
      "language": "Python",
      "description": "A framework for building LLM agents"
    }
  ]
}
```

---

### Action: `language_trends`

Analyze the language distribution across the top search results for a keyword.

```bash
echo '{"action": "language_trends", "query": "machine learning"}' | python3 src/main.py

# Top 50 repos for "ai agent", active in the last 90 days
echo '{"action": "language_trends", "query": "ai agent", "top_n": 50, "pushed_within_days": 90}' | python3 src/main.py
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | string | — | **Required.** Search keyword(s) |
| `top_n` | int | `30` | Number of top repos to analyze (max 100) |
| `pushed_within_days` | int | `0` | Only include repos pushed within N days (0 = no filter) |

**Example output:**

```json
{
  "title": "Language Trends — \"machine learning\"",
  "source": "GitHub Search API — language distribution across top results",
  "languages": [
    { "rank": 1, "language": "Python", "repos": 22, "share_pct": 73.3 },
    { "rank": 2, "language": "Jupyter Notebook", "repos": 5, "share_pct": 16.7 },
    { "rank": 3, "language": "R", "repos": 2, "share_pct": 6.7 }
  ]
}
```

---

## Project Structure

```
skill-github-news/
├── src/
│   ├── main.py              # Entry point — reads JSON from stdin, dispatches actions
│   ├── github_trending.py   # Scrapes github.com/trending via HTML parsing
│   └── github_api.py        # GitHub REST API wrapper (search, repo detail, language stats)
├── requirements.txt         # Python dependencies
├── SKILL.md                 # OpenClaw skill manifest
└── README.md
```

---

## Error Handling

On error, the program prints a JSON error object to stdout and exits with code `1`:

```json
{ "error": "Description of what went wrong" }
```

Common error scenarios:
- Empty or invalid JSON input
- Unknown `action` value
- Missing required `query` for `search` / `language_trends`
- No results found for the given filters
- GitHub rate limit exceeded (set `GITHUB_TOKEN` to raise the limit)

---

## Rate Limits

| Mode | Rate Limit |
|---|---|
| Unauthenticated | 60 requests/hour |
| Authenticated (`GITHUB_TOKEN` set) | 5,000 requests/hour |

> **Note:** The `trending` action scrapes the GitHub HTML page and does not count against the REST API rate limit.

