# Go-live checklist & self-check

Use this to confirm your live app is fully wired, and to send yourself a real test email.

## The two places secrets must go

JobPilot has **two runtimes**, each with its own secret store:

| Runtime | What it does | Where its secrets live |
|---------|--------------|------------------------|
| **Render** (the website) | search, login, CV, apply, the `/api/test-email` button | Render → service → **Environment** |
| **GitHub Actions** (the robots) | the **daily scan** that emails new matches, and the monthly cleanup | GitHub repo → **Settings → Secrets and variables → Actions** |

Setting a value on Render does **not** make it available to GitHub Actions, and vice
versa. For the daily email alerts you must set `DATABASE_URL`, `RESEND_API_KEY`,
`RESEND_FROM`, and `BASE_URL` **as GitHub Actions secrets** (in addition to Render).

Secret values are write-only — once saved you (and anyone) can't read them back out, which
is why they must be entered directly in each place.

## Live self-check (no secrets revealed)

Open: `https://<your-app>/api/status`

It returns something like:
```json
{"status":"ok","database":"postgres","email_configured":true,
 "email_channel":"resend","llm_provider":"gemini"}
```
- `database: postgres` → Neon is wired (if it says `sqlite`, your DATABASE_URL isn't set
  on Render).
- `email_configured: true` + `email_channel: resend` → Resend key is detected on Render.

## Send yourself a real test email (proves Resend end-to-end)

1. Log in to the website.
2. From the browser console on the site, or any tool, send a POST to `/api/test-email`
   (it uses your logged-in session). Easiest: open the interactive docs at
   `https://<your-app>/docs`, find **POST /api/test-email**, click **Try it out →
   Execute** while logged in.
3. The response shows the channel used, e.g. `{"sent_to":"you@...","channel":"resend"}`.
4. Check your inbox (and spam) for the test email.

> With Resend's shared `onboarding@resend.dev` sender, delivery is reliable to the email
> you verified when signing up to Resend. To email other addresses, verify a domain in
> Resend. See EMAIL_ALERTS.md.

## Then enable the daily scan

Once `/api/status` shows database=postgres and email=resend, add the **same** values as
GitHub Actions secrets, then trigger **Actions → Daily Scan → Run workflow**. Watch the
log: it prints the channel used and how many matches were emailed.
