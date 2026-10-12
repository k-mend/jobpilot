# Go live — publish JobPilot at a shareable URL (free)

The scheduled scanner already runs free on GitHub Actions. This guide gives you a
**public URL** anyone can open to search jobs. Two free paths; pick one.

> Reality check: free tiers trade away either uptime or persistent storage. JobPilot
> treats its SQLite DB as a cache — every search re-scans the live job boards — so
> ephemeral storage is fine. Saved applications/queue data won't survive a redeploy on
> the free tier; add a disk or external DB later if you need that.

Deploy files already in the repo: `render.yaml`, `Procfile`, `runtime.txt`, `Dockerfile`.
The start command (verified) is:
`uvicorn app.main:app --host 0.0.0.0 --port $PORT`

---

## Option A — Render (recommended, real "web app" feel)

1. Go to <https://render.com> and sign up / log in with GitHub.
2. **New → Blueprint** (or **New → Web Service**).
3. Connect the GitHub account `k-mend` and pick the **`jobpilot`** repo.
   - If using Blueprint, Render reads `render.yaml` automatically.
   - If using Web Service manually, set:
     - Runtime: **Python**
     - Build command: `pip install -r requirements.txt`
     - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
     - Instance type: **Free**
4. (Optional) Add env var `GEMINI_API_KEY` for AI-tailored CVs/cover letters.
5. **Create**. First build takes a few minutes.
6. You'll get a URL like `https://jobpilot-xxxx.onrender.com` — **that's the link to
   share.**

Free-tier notes:
- The service **sleeps after ~15 min idle**; the next visit takes ~30–60s to wake, then
  it's fast. Totally fine for sharing.
- Redeploys reset the SQLite file (see the reality-check note above).

---

## Option B — Hugging Face Spaces (always-on public demo)

1. Go to <https://huggingface.co> and sign up / log in.
2. **New → Space**. Name it, choose **Docker** as the SDK, visibility **Public**.
3. Push this repo to the Space (HF gives you a git remote), or point the Space at the
   GitHub repo. The included `Dockerfile` builds it; it listens on port **7860** (HF's
   default) and honors `$PORT`.
4. (Optional) In **Settings → Variables and secrets**, add `GEMINI_API_KEY`.
5. The Space URL (e.g. `https://huggingface.co/spaces/<you>/jobpilot`) is your shareable
   link.

Notes: Spaces storage is ephemeral unless you add persistent storage; same cache-style
behavior applies.

---

## After it's live

- Share the URL. Anyone can open it, describe a job, and search. No login required
  (public by design — see below).
- The daily GitHub Actions scan keeps running independently and is unaffected.

## Security note (read before sharing widely)

The live app has **no authentication** — anyone with the URL can search and upload a CV.
That matches the "share with anyone" goal, but it means:
- Don't store sensitive data expecting privacy on the free tier.
- If you later want per-user accounts, the `User` model already exists; add
  session/OAuth login on top of it.

## Custom domain (optional, still free-ish)

Both Render and HF let you attach a custom domain you own (the domain itself isn't free).
Point a CNAME to the provided hostname in the host's dashboard.
