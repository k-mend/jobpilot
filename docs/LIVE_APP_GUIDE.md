# Your live app, its quirks, and how to keep it awake (beginner friendly)

## Your live URL

**https://jobpilot-cv39.onrender.com**

This is hosted on Render's **free** tier. Share it with anyone — they can describe a job
and search immediately. No login needed.

Verified working: the home page loads, and a search for "remote python backend" returned
230 live jobs from three job boards.

---

## The free-tier caveats (what to expect, and why)

Free hosting is amazing but comes with trade-offs. Here they are in plain language.

### 1. It "goes to sleep" after 15 minutes of no visitors

**What happens:** Render puts free apps to sleep when nobody has used them for ~15
minutes. The *next* visitor's first request then takes **~30–60 seconds** while the app
"wakes up." After that, it's fast again.

**Why:** Render gives free apps a shared, part-time server. Sleeping is how they offer it
for free. It's not a bug.

**Who feels it:** only the unlucky first person after an idle period. Everyone after them
gets a fast app.

**How to avoid it:** ping the app every few minutes so it never idles out. That's the
"keep-alive cron" below. (Honest note: this technically keeps a free server busier than
Render intends for always-on use. It's widely done and fine for a small personal app, but
it's not what the free tier is designed for. For heavy use, a paid plan is the clean
answer.)

### 2. Saved data resets when the app redeploys

**What happens:** JobPilot stores things in a SQLite file on the server. On the free tier
that file lives on a **temporary disk** that gets wiped on each redeploy (e.g. when you
push new code, or Render restarts the app).

**Why it's OK:** JobPilot re-scans the live job boards on **every** search, so search
always works with fresh data. The database is just a short-term cache + the review queue.

**What you lose on a reset:** saved application-queue entries. If you need those to
persist, you'd add a Render **persistent disk** (small monthly cost) or an external free
database later. Not needed just to search and share.

### 3. Free apps are single, small instances

Fine for personal use and sharing with friends. If hundreds of people hit it at once it
can get slow. That's the point to consider a paid plan.

---

## Keep-alive cron — stop the 15-minute sleep (free)

We use **GitHub Actions** (same free system running your daily scan) to visit the app's
health URL every ~10 minutes so it never idles out.

### It's already set up

The file [`.github/workflows/keepalive.yml`](../.github/workflows/keepalive.yml) is in
your repo. It runs on a schedule and sends one tiny request to
`https://jobpilot-cv39.onrender.com/api/health`.

### How to turn it on / confirm it

1. Go to your repo on GitHub → **Actions** tab.
2. If Actions asks you to enable workflows, click **enable**.
3. Find **"Keep Render app awake"** in the left sidebar.
4. Click **Run workflow** once to test it now (the schedule starts automatically after).

### How to change the target URL or frequency

Open `.github/workflows/keepalive.yml`:
- Change the `url=` line to your app's URL (already set to your current one).
- Change the `cron:` value to run more/less often.

> About the schedule: GitHub cron is in **UTC** and the *minimum* interval is 5 minutes.
> GitHub may also delay scheduled runs when it's busy, so pings aren't perfectly on time —
> that's normal and fine for keep-alive. Also, scheduled workflows pause after **60 days**
> of no activity in the repo; any commit re-arms them.

### How to turn it OFF

If you move to a paid plan (no sleeping) or don't want the pings:
- GitHub → **Actions** → "Keep Render app awake" → **"···" menu → Disable workflow**.

---

## Quick cheat-sheet

| Thing | Status |
|-------|--------|
| Live URL | https://jobpilot-cv39.onrender.com |
| Sleeps after idle? | Yes (~15 min) — keep-alive cron prevents it |
| Wake-up delay | ~30–60s for the first visit after sleeping |
| Data persists across redeploys? | No on free tier (search still works; it re-scans live) |
| AI provider | Gemini (you added the key) — see docs/LLM_PROVIDERS.md |
| Cost | $0 |
