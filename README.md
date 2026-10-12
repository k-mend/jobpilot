# JobPilot

A free, multi-user job-scanning + CV-tailoring + application-queue platform.
Inspired by [hiring.cafe](https://hiringcafe.com/) — but it adds the loop hiring.cafe
doesn't give you: **describe a job in plain English → get matched real jobs → auto-tailor
your CV and cover letter per job → queue them for one-click review** — all running for
**$0** on GitHub Actions.

> **Honest scope note.** Truly "apply while you sleep" with zero human review is neither
> reliable nor safe (CAPTCHAs, custom application questions, account/ToS risk, and
> auto-rejection of low-quality blind submissions). JobPilot is built around a
> **prepare-and-review** model: it does *all* the heavy lifting (find, match, tailor,
> draft, queue, notify) and leaves you a one-click approve step. See
> [`docs/LEGAL.md`](docs/LEGAL.md) for why, and for the LinkedIn stance.

---

## What it does

1. **Describe-a-job search.** A user types "remote senior python backend role, EU time
   zone, fintech, no on-call" and JobPilot parses that into structured filters.
2. **Scans free, legal job sources.** Remotive, RemoteOK, Arbeitnow, and any public
   Greenhouse / Lever / Ashby company board. (No scraping of sites that forbid it.)
3. **Ranks matches** against the query + the user's parsed CV (skills, seniority,
   location, keywords).
4. **Tailors the CV** per job and **drafts a cover letter** using a pluggable LLM
   provider (Google Gemini free tier) with a **100%-free template fallback** that needs
   no API key.
5. **Queues applications** with statuses (`matched → tailored → ready → submitted →
   archived`) in a review dashboard.
6. **Runs free on a schedule** via GitHub Actions cron, and can notify users.

## Architecture (short version)

```
          ┌─────────────────────────────────────────────────────────┐
          │                       FastAPI app                        │
          │                                                          │
  Web UI ─┤  routers/  ── services/ ── sources/ (job connectors)     │
 (Jinja2) │     │            │             │                         │
          │     │            │             └── Remotive/RemoteOK/...  │
          │     │            ├── matching (NL query + CV scoring)     │
          │     │            ├── cv (parse + tailor + cover letter)   │
          │     │            └── llm (Gemini | free template)         │
          │     └── models/ (SQLModel) ── SQLite (file DB)            │
          └─────────────────────────────────────────────────────────┘
                      ▲                              ▲
                      │ scheduled scan               │ CI
             .github/workflows/scan.yml     .github/workflows/ci.yml
```

Full detail in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## $0-forever strategy

| Need        | Free solution                                                        |
|-------------|----------------------------------------------------------------------|
| Compute     | GitHub Actions (unlimited minutes on public repos)                   |
| Scheduling  | GitHub Actions `schedule:` cron                                      |
| Storage     | SQLite file committed by the scan workflow (or an artifact)          |
| Job data    | Free public APIs that permit programmatic access                     |
| CV tailoring| Google Gemini free tier **or** no-API template fallback             |
| Hosting UI  | Run locally, or free tier of a PaaS; the core value runs in Actions |

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Quick start

```bash
cd jobpilot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add GEMINI_API_KEY for better tailoring
uvicorn app.main:app --reload
# open http://127.0.0.1:8000
```

Run a scan from the CLI (what the GitHub Action calls):

```bash
python -m app.cli scan --query "remote python backend" --limit 25
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Repository layout

```
jobpilot/
├── app/
│   ├── main.py              FastAPI app + UI routes
│   ├── config.py            settings (env-driven)
│   ├── database.py          SQLite/SQLModel engine + session
│   ├── cli.py               `python -m app.cli scan ...` for Actions
│   ├── models/              SQLModel tables + schemas
│   ├── routers/             API endpoints
│   ├── services/            matching, cv, llm, queue, notify
│   ├── sources/             pluggable job-board connectors
│   ├── templates/           Jinja2 UI
│   └── static/              CSS
├── docs/                    ARCHITECTURE, LEGAL, DEPLOYMENT
├── tests/
├── .github/workflows/       scan.yml (cron) + ci.yml
├── requirements.txt
└── requirements-dev.txt
```

## License

MIT. Use responsibly and within each job source's Terms of Service.
