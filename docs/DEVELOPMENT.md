# Local development

## Setup

```bash
git clone https://github.com/k-mend/jobpilot.git
cd jobpilot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt      # runtime + test deps
cp .env.example .env                      # optional; app runs with empty .env
```

## Run the app

```bash
uvicorn app.main:app --reload
# http://127.0.0.1:8000  (UI)
# http://127.0.0.1:8000/docs  (auto API docs)
```

## Run a scan from the CLI (what the scheduled Action calls)

```bash
# ad-hoc one-off query:
python -m app.cli scan --query "remote python backend" --email you@example.com

# all active saved searches (multi-user mode):
python -m app.cli scan

# create a demo user + saved search:
python -m app.cli seed --email you@example.com --query "remote python backend"
```

## Tests

```bash
pytest -q
```
Tests are offline: `tests/test_api.py` monkeypatches `queue.fetch_all` so no network
calls are made. Matching and CV tests are pure functions.

## Project map

| Path | Responsibility |
|------|----------------|
| `app/config.py` | env-driven settings, all with free defaults |
| `app/database.py` | SQLite engine + `init_db()` + `get_session()` |
| `app/models/` | tables (`__init__.py`) and dataclasses (`schemas.py`) |
| `app/sources/` | one connector per job board + `registry.py` |
| `app/services/matching.py` | NL query parse + scoring |
| `app/services/cv.py` | CV parse, tailor, cover letter |
| `app/services/llm.py` | Gemini-or-fallback `complete()` |
| `app/services/queue.py` | scan orchestration + application workflow |
| `app/services/notify.py` | email/Telegram/log digest |
| `app/routers/api.py` | JSON API |
| `app/routers/ui.py` + `templates/` | web UI |
| `app/cli.py` | scheduled-job entrypoint |
| `.github/workflows/` | `scan.yml` (cron) + `ci.yml` (tests) |

## Adding a new job source

1. Create `app/sources/<name>.py` with a class extending `JobSource` that implements
   `fetch(query) -> List[RawJob]`.
2. Register it in `app/sources/registry.py`.
3. Confirm the source's Terms of Service allow programmatic access (see `docs/LEGAL.md`).

## Common pitfalls (already hit, documented so you don't repeat them)

- **"no such table"** → `init_db()` wasn't called (lifespan doesn't run under a bare
  `TestClient`; call it explicitly in tests).
- **Actions "No such file or directory .../jobpilot/jobpilot"** → a stale
  `working-directory` default; the project is at the repo root.
- **Python 3.9 f-string parse error** → no nested implicit string concatenation inside
  `{...}`.
