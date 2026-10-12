# Build-Along Guide — build a project like JobPilot from scratch

This is the tutorial version of JobPilot. It walks you through building the whole thing
in the **same order it was actually built**, explains *why* each decision was made, and
flags the mistakes to avoid. Follow it top to bottom and you'll end with the same
working app — or adapt the steps for your own idea.

Estimated time: a focused afternoon.

---

## 0. The idea and the honest constraints (decide this first)

Before any code, pin down what is actually buildable. For JobPilot the goals were:

1. Multi-user "describe a job → get matched jobs" (like hiring.cafe).
2. Auto-tailor a CV + cover letter per job.
3. Run **$0 forever**.
4. "Apply while you sleep."

Two of these need a reality check *up front* — doing this early saves weeks:

- **"Apply while you sleep" (blind auto-submit)** is unreliable and risky: CAPTCHAs,
  per-job custom questions, account bans, auto-rejection of low-quality submissions.
  Decision: build **prepare-and-review** instead (do all the work, queue for one click).
- **LinkedIn auto-apply via your login** violates their ToS and gets accounts banned;
  their Jobs API is partner-only. Decision: **don't log into LinkedIn**; use job boards
  that permit API access, and let users paste any job URL.

> Lesson: separate "what the user asked for" from "what is actually achievable," and
> write down the deviations and *why*. See `docs/LEGAL.md` for how this was recorded.

The **$0** path: GitHub Actions (unlimited minutes on public repos) for compute +
schedule, SQLite committed to a branch for storage, free job APIs, and an optional free
LLM tier with a no-key fallback.

---

## 1. Verify your toolchain

```bash
python3 --version   # 3.9+ (JobPilot was built/tested on 3.9 locally, 3.11 in CI)
git --version
gh --version && gh auth status   # GitHub CLI, logged in
```

> Lesson: if you're on Python 3.9 locally, keep type hints 3.9-compatible
> (`Optional[int]`, `List[str]` — not `int | None` or `list[str]`). The code uses
> `from __future__ import annotations` to relax this, but runtime type usage still
> matters.

---

## 2. Scaffold the project skeleton

Create the folder layout first so imports are stable:

```
app/
  __init__.py
  config.py        # settings from env
  database.py      # engine + session
  main.py          # FastAPI app
  cli.py           # entrypoint for the scheduled job
  models/          # DB tables + plain dataclasses
  routers/         # api.py (JSON) + ui.py (pages)
  services/        # matching, cv, llm, queue, notify
  sources/         # one file per job board + a registry
  templates/       # Jinja2 HTML
  static/          # CSS
tests/
docs/
.github/workflows/
```

Then the plumbing files: `requirements.txt`, `requirements-dev.txt`, `.env.example`,
`.gitignore` (ignore `.venv/`, `*.db`, `.env`), `LICENSE`.

> Lesson: pin dependency versions in `requirements.txt`. It makes CI reproducible and
> avoids "works on my machine."

---

## 3. Config and database (the two foundations)

- `config.py`: use `pydantic-settings`. Give **every** setting a free, working default
  so the app runs with an empty `.env`. Expose a derived `llm_enabled` property.
- `database.py`: SQLModel `create_engine` over SQLite. For SQLite + FastAPI you need
  `connect_args={"check_same_thread": False}`. Provide `init_db()` (imports models, then
  `SQLModel.metadata.create_all`) and a `get_session()` generator for dependency
  injection.

> Lesson: `init_db()` must import the models module *before* `create_all`, or SQLModel
> won't know about the tables. This is a classic silent "no such table" bug.

---

## 4. Data model

Two kinds of types:

- **Tables** (`models/__init__.py`): `User`, `CVDocument`, `SavedSearch`, `Job`,
  `Application`. Give `Application` a `status` field with a clear lifecycle:
  `matched → tailored → ready → submitted → archived`.
- **Plain dataclasses** (`models/schemas.py`): `RawJob`, `SearchQuery`, `CVProfile` —
  used *between services* so you're not passing ORM rows everywhere.

> Lesson: keep a boundary between "normalized data moving through the pipeline"
> (dataclasses) and "persisted rows" (tables). It keeps services testable without a DB.

---

## 5. Job sources (the plugin pattern)

- `sources/base.py`: a `JobSource` base class with `fetch(query) -> List[RawJob]`, a
  shared polite HTTP client, and a small keyword gate for APIs that lack server-side
  search.
- One file per board: `remotive.py`, `remoteok.py`, `arbeitnow.py`, plus `ats.py`
  (Greenhouse/Lever/Ashby, keyed by a company board slug).
- `sources/registry.py`: `build_sources(settings)` assembles the enabled connectors.

> Lesson: normalize everything into `RawJob` *inside each connector*. The rest of the
> app then never cares which board a job came from. Adding a new board = one new file +
> one registry line.
> Lesson: RemoteOK's first JSON element is a legal/metadata notice, not a job — skip it.
> Little per-API quirks like this are normal; isolate them in the connector.

---

## 6. Matching engine (works with zero API keys)

`services/matching.py`:
- `parse_query(text)`: rule/keyword-based NL → `SearchQuery` (keywords, seniority,
  remote flag, exclusions). No API key required.
- `score_job(job, query, profile)`: weighted 0–100 score (title hits > body hits,
  seniority alignment, remote fit, CV-skill overlap, hard penalties for exclusions).
- `rank_jobs(...)`: sort desc.

> Lesson: make the core logic deterministic and keyless. The LLM should *enhance*, never
> be *required*. This is both the $0 story and what makes the engine unit-testable.

---

## 7. CV parsing + tailoring + LLM abstraction

- `services/llm.py`: a single `complete(prompt)` that calls Gemini when `GEMINI_API_KEY`
  is set and returns `None` otherwise (or on any error — quota, network). Callers treat
  `None` as "use the template."
- `services/cv.py`: `extract_text` (PDF via pypdf, DOCX via python-docx, else decode),
  `parse_cv` → `CVProfile`, `tailor_cv`, `generate_cover_letter`. Each tailoring function
  tries the LLM, then falls back to a deterministic template.

> Lesson: graceful degradation everywhere. A missing key or a failed API call should
> downgrade quality, never crash the pipeline.
> Lesson (Python 3.9): don't nest implicit string concatenation inside an f-string
> expression — `f"{x or 'a' 'b'}"` fails to parse. Compute the string first.

---

## 8. Orchestration + the queue

`services/queue.py` ties it together:
- `fetch_all(query)`: run every source, **dedupe**, and tolerate a single source failing
  (wrap each in try/except — one dead API shouldn't kill the scan).
- `run_scan_for_search(...)`: fetch → rank → upsert `Job` rows → create `matched`
  Applications → tailor the top N → return a digest.
- `run_all_active_scans(...)`: loop over active saved searches for all users (this is
  what the scheduled job calls).
- Workflow transitions: `advance`, `set_status`, `tailor_application`.

`services/notify.py`: optional email/Telegram, defaulting to a log line (stdlib only, no
new deps).

> Lesson: the scheduled entrypoint should iterate *all users' saved searches*, not just
> yours — that's what makes it a product, not a personal script.

---

## 9. API + UI

- `routers/api.py`: JSON endpoints (`/api/search`, users, CV upload, saved searches,
  applications, workflow transitions, `/api/health`).
- `routers/ui.py` + `templates/`: server-rendered Jinja2 pages (search, results, CV
  upload, review queue). Jinja2 + FastAPI's `Jinja2Templates` keeps it dependency-light,
  no separate frontend build.
- `main.py`: create the app with a `lifespan` that calls `init_db()`, mount `/static`,
  include routers. Import the UI router *after* `templates` is defined to avoid a
  circular import.

> Lesson: a server-rendered UI is the fastest way to a usable product. You can swap in a
> SPA later; don't start there.

---

## 10. The scheduled job (the $0 heart)

`app/cli.py`: an argparse entrypoint with `scan` (all active searches, or ad-hoc
`--query`) and `seed`. This is what the Action runs.

`.github/workflows/scan.yml`:
1. checkout → setup Python → install deps
2. **restore** the SQLite DB from a dedicated `data` branch (if present)
3. seed a demo search if the DB is empty
4. run `python -m app.cli scan` (secrets passed via `env:`)
5. **commit the DB back** to the `data` branch

`.github/workflows/ci.yml`: checkout → setup Python → install dev deps → `pytest`.

> Lesson (the bug that actually happened): don't set
> `defaults.run.working-directory: <subdir>` unless that subdir really exists at the repo
> root. If you build in a local `project/` folder but push *from inside* it, the repo
> root *is* the project — a `working-directory: project` points at a non-existent
> `project/project` and the runner fails with "No such file or directory." Either push
> the parent folder, or don't set `working-directory`.
> Lesson: public repo = unlimited Actions minutes. Scheduled workflows pause after 60
> days of repo inactivity; the commit-back step doubles as a keep-alive.

---

## 11. Tests + verification (don't skip)

- `tests/test_matching.py`: query parsing + scoring are pure functions — easy wins.
- `tests/test_cv.py`: parsing + template fallbacks (no network, no key).
- `tests/test_api.py`: FastAPI `TestClient`, with `fetch_all` monkeypatched to a fake so
  tests never hit the network.

> Lesson: when using `TestClient(app)` **without** a `with` block, the `lifespan` doesn't
> run, so `init_db()` isn't called and you get "no such table." Call `init_db()`
> explicitly in the test module (or use the context-manager form). This exact bug
> happened here.

Verify locally before pushing:
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --port 8099   # curl /api/health and /
```

---

## 12. Ship it on GitHub

```bash
git init && git branch -M main
git add -A && git commit -m "feat: initial version"
gh repo create <name> --public --source=. --remote=origin --push
```

Then **actually trigger the scheduled workflow** and read the logs — don't assume:
```bash
gh workflow run scan.yml --ref main
gh run list --workflow=scan.yml --limit 1
gh run view <run-id> --json jobs --jq '.jobs[].steps[] | "\(.conclusion)\t\(.name)"'
```

> Lesson: "it should work" is not verification. Run it, confirm every step is `success`,
> and confirm the side effects (here: the DB landed on the `data` branch).

---

## 13. Make it your own — extension ideas

- **New job board:** add `sources/<board>.py` returning `RawJob`s, register it. Done.
- **Better matching:** add embeddings (there are free/local options) behind the same
  `score_job` interface.
- **Auth:** the models already have `User`; add sessions/OAuth when you need real
  multi-tenant login.
- **PDF export** of the tailored CV (e.g. a lightweight HTML→PDF step).
- **Different LLM:** `services/llm.py` is one function — point it at any provider, keep
  the `None` fallback.

---

## The meta-lessons (the ones that generalize)

1. **Decide feasibility before coding.** Name the impossible/risky parts and redesign
   around them.
2. **Free-by-default, better-with-a-key.** Every paid/external dependency needs a working
   fallback.
3. **Normalize at the edges** (connectors) so the core stays simple.
4. **Keep the core deterministic** so it's testable and keyless.
5. **Verify side effects, not just exit codes.** Trigger the real workflow and inspect
   it.
6. **Write down deviations and reasons** so future-you (and users) understand the design.
