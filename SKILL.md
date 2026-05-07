---
name: github-news
description: Scrapes GitHub Trending and queries the GitHub REST API to deliver trending repos, language trends, and open-source updates.
version: 1.0.0
metadata:
  hermes:
    tags: [github, trending, open-source, news, python]
    category: development
    requires_toolsets: [terminal]
required_environment_variables:
  - name: GITHUB_TOKEN
    prompt: GitHub Personal Access Token
    help: Generate at https://github.com/settings/tokens — unauthenticated limit is 60 req/hr; authenticated is 5,000 req/hr.
    required_for: higher API rate limits (optional — skill works without it)
---

# GitHub News

Fetch trending repositories, search open-source projects, and analyze language trends from GitHub.

## When to Use

Trigger this skill when the user asks about:

- "show trending repos"
- "what's trending in Python this week"
- "search open source projects about LLM"
- "show language trends"
- "trending Rust repos this month"

## Procedure

1. **Install dependencies** (first run only):
   ```bash
   pip install -r {baseDir}/requirements.txt
   ```

2. **Invoke the skill** by piping a JSON action object to `{baseDir}/src/main.py`:
   ```bash
   echo '{"action": "trending", "language": "python", "since": "weekly"}' | python3 {baseDir}/src/main.py
   ```

3. **Choose the right action** based on the user's request:

   | Action            | Description                                                                 |
   |-------------------|-----------------------------------------------------------------------------|
   | `trending`        | Scrape GitHub Trending with optional language, spoken-language, and period. |
   | `search`          | Search repositories via the GitHub REST API by keyword, sorted by stars.   |
   | `language_trends` | Aggregate language distribution across top search or trending results.      |

4. **Pass parameters** as needed:

   | Parameter         | Type   | Default  | Description                                               |
   |-------------------|--------|----------|-----------------------------------------------------------|
   | `action`          | string | —        | One of `trending`, `search`, `language_trends`.           |
   | `language`        | string | `""`     | Programming language filter (e.g. `python`, `rust`).      |
   | `since`           | string | `daily`  | Time range: `daily`, `weekly`, or `monthly`.              |
   | `query`           | string | `""`     | Search keyword(s) (used by `search` and `language_trends`). |
   | `spoken_language` | string | `""`     | Spoken-language filter code (e.g. `en`, `zh`).            |

## Examples

```bash
# Trending Python repos this week
echo '{"action": "trending", "language": "python", "since": "weekly"}' | python3 {baseDir}/src/main.py

# Search for LLM-related repos
echo '{"action": "search", "query": "large language model"}' | python3 {baseDir}/src/main.py

# Language trend analysis for AI topics
echo '{"action": "language_trends", "query": "AI agent"}' | python3 {baseDir}/src/main.py
```

## Pitfalls

- Without `GITHUB_TOKEN`, the GitHub REST API is limited to 60 requests/hour. Set the token to raise this to 5,000/hr.
- GitHub Trending scraping may break if GitHub changes its page structure — check `src/github_trending.py` if results are empty.
- `since` only applies to the `trending` action; `search` always returns by star count.

## Verification

Run a quick trending fetch and confirm repos are returned:

```bash
echo '{"action": "trending"}' | python3 {baseDir}/src/main.py
```

A successful response is a JSON array of repository objects with `name`, `url`, `stars`, and `description` fields.
