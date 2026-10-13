# Set up durable storage with Neon (beginner friendly)

## Why you need this

By default JobPilot stores data in a SQLite file. On Render's free tier that file lives
on a **temporary disk that gets wiped on every redeploy** — so your account, saved
searches, and "already applied" history would vanish. To keep them, we use **Neon**, a
free cloud Postgres database.

> One-time setup, ~10 minutes. After this, your data survives redeploys, logins work,
> and the daily email alerts have somewhere permanent to track what's new.

## Step 1 — Create a free Neon database

1. Go to <https://neon.tech> and sign up (GitHub/Google login works).
2. Click **Create project** (any name, e.g. `jobpilot`). Pick the region closest to you.
3. Neon creates a database and shows a **connection string**. Click **Connect** / copy
   the **psql / connection string**. It looks like:
   ```
   postgresql://alex:npg_abc123@ep-cool-name-123.eu-central-1.aws.neon.tech/neondb?sslmode=require
   ```
4. Keep `?sslmode=require` at the end — Neon needs SSL.

> That string contains a password. Treat it like one — don't paste it into public places.

## Step 2 — Give it to JobPilot

**On Render (your live app):**
1. Render dashboard → your `jobpilot` service → **Environment**.
2. Add a variable:
   - Key: `DATABASE_URL`
   - Value: *(paste the Neon connection string)*
3. Save. Render redeploys. On startup JobPilot auto-creates its tables in Neon.

**Locally (optional):** put the same line in your `.env`:
```
DATABASE_URL=postgresql://...sslmode=require
```
Leave it as the default `sqlite:///jobpilot.db` if you just want to test locally.

## Step 3 — Also give it to the GitHub Actions (for the daily scan + monthly cleanup)

The scheduled jobs run on GitHub, not Render, so they need the URL too:
1. GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**.
2. Name: `DATABASE_URL`, Value: *(the same Neon string)*.

Now the daily scan and monthly cleanup read/write the **same** database your website uses.

## How JobPilot handles the connection (so you don't have to)

- It accepts `postgres://` or `postgresql://` and normalizes it to the `psycopg` driver.
- It uses a small connection pool with `pool_pre_ping` + `pool_recycle`, so Neon's habit
  of closing idle connections doesn't cause errors.
- SQLite is still used automatically whenever `DATABASE_URL` starts with `sqlite:` — great
  for local dev and the test suite.

(Relevant code: `app/database.py`.)

## Caveats (plain language)

- **Free tier limits:** Neon's free tier is generous but finite (storage + compute
  hours). The **monthly cleanup** (see `RETENTION.md`) keeps usage small by deleting old
  backlog. For heavy use you'd upgrade Neon.
- **Neon auto-suspends** an idle database; the first query after idle can be slightly
  slower while it wakes. Normal and free.
- **Backups:** the free tier has limited history. Don't store anything you can't afford
  to lose. For JobPilot that's fine — the data is job matches, not irreplaceable records.
- **Redis?** You asked about Redis too. You don't need it yet. Postgres/Neon is the
  durable source of truth. Redis would only be a *cache* later (with TTL expiry) if the
  app gets busy. Not added on purpose, to keep things simple and free.
