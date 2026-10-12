# Architecture

JobPilot is a modular FastAPI monolith. Each concern is a small, independently testable
service, and job sources are plug-ins behind one interface.

## Layers

### 1. Sources (`app/sources/`)
Each connector implements `JobSource.fetch(query) -> List[RawJob]` and normalizes
provider-specific JSON into a common `RawJob`. Adding a board = adding one file and
registering it in `registry.py`. No source scrapes a site that forbids automated access.

Shipped connectors:
- **Remotive** — public JSON API (`https://remotive.com/api/remote-jobs`).
- **RemoteOK** — public JSON API (`https://remoteok.com/api`).
- **Arbeitnow** — public job board API (`https://www.arbeitnow.com/api/job-board-api`).
- **Greenhouse / Lever / Ashby** — public company board JSON endpoints, keyed by a board
  token/slug the user supplies (e.g. `boards.greenhouse.io/{board}`).

### 2. Matching (`app/services/matching.py`)
- `parse_query(text)` turns a natural-language description into a `SearchQuery`
  (keywords, seniority, remote flag, locations, excluded terms). Rule/keyword based so it
  needs no API key; an LLM can refine it when a key is present.
- `score_job(job, query, profile)` yields 0–100 using weighted signals: keyword overlap,
  title match, seniority alignment, remote/location fit, and CV-skill overlap.

### 3. CV (`app/services/cv.py`)
- `parse_cv(file)` extracts text from PDF/DOCX/Markdown/plain text and derives a
  `CVProfile` (skills, titles, years, summary).
- `tailor_cv(profile, job)` reorders/rewrites to foreground the job's keywords.
- `generate_cover_letter(profile, job)` drafts a letter.
- Both call `services/llm.py`; without a key they use deterministic templates.

### 4. LLM (`app/services/llm.py`)
A thin provider abstraction. `complete(prompt)` routes to Google Gemini when
`GEMINI_API_KEY` is set, otherwise to a local template engine. This keeps the app
**free by default** and better-with-a-key.

### 5. Persistence (`app/models/`, `app/database.py`)
SQLModel over SQLite. Tables: `User`, `CVDocument`, `SavedSearch`, `Job`, `Application`.
SQLite is a single file — trivial to run in Actions and commit back or store as an
artifact.

### 6. API + UI (`app/routers/`, `app/templates/`)
- JSON API under `/api/*` for programmatic use and the CLI.
- Server-rendered Jinja2 UI: search page, results, CV upload, tailored output, and the
  application queue/review board.

### 7. Scheduler (`app/cli.py` + `.github/workflows/scan.yml`)
The CLI runs a scan for each saved search, scores and stores matches, and marks the best
as `matched`. GitHub Actions runs it on cron for free.

## Data flow (a scan)

```
saved search ──▶ parse_query ──▶ for each source: fetch ──▶ normalize ──▶ dedupe
      ──▶ score against query + CV profile ──▶ persist Job + Application(matched)
      ──▶ (optional) tailor top N ──▶ notify
```

## Why review-based, not blind auto-submit
See [`LEGAL.md`](LEGAL.md). Short version: reliability, account safety, and application
quality. The queue is designed so approving is one click, which is the real time-saver.
