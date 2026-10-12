# Deployment — $0 forever

## The core runs free in GitHub Actions

The valuable part — scheduled scanning, matching, tailoring, queueing — runs in
`.github/workflows/scan.yml` on a cron. On **public repos GitHub Actions minutes are
unlimited**, so this is free indefinitely.

### How state persists for free
The scan job uses a SQLite file (`jobpilot.db`). Two free options:
1. **Commit-back (default in the workflow):** the workflow commits the updated DB to a
   `data` branch after each run. Simple, free, versioned.
2. **Artifact:** upload the DB as a workflow artifact (retained up to 90 days).

### Secrets
Add optional secrets in **repo → Settings → Secrets and variables → Actions**:
- `GEMINI_API_KEY` — enables LLM tailoring (free tier). Omit for template fallback.
- Notification secrets (optional), e.g. `SMTP_*` or `TELEGRAM_*`.

### Caveats of the free tier
- Scheduled workflows can be **delayed under load** and are **paused after 60 days of
  repo inactivity** — any push/commit re-arms them (the commit-back step helps).
- Max job runtime is 6 hours (we need seconds).

## Running the UI

The UI is a normal FastAPI app:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Free hosting options for the interactive UI (optional — the pipeline doesn't need it):
- Run locally whenever you want to review the queue.
- A free-tier PaaS. Pick one with a genuine free tier; the app is a single process + a
  SQLite file.

The recommended **$0** pattern: let Actions do the scanning/tailoring on a schedule and
publish a static review page (or open a GitHub Issue per match), and run the full
interactive UI locally when you want to approve/submit.
