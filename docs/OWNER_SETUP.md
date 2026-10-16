# Owner setup — do these, in order (follow-along)

This is your personal checklist. Everything in the app is already built and deployed.
There are **2 actions only you can do** (they touch your Render dashboard / your
password). Do them top to bottom.

Your live app: **https://jobpilot-cv39.onrender.com**
Your repo: **https://github.com/k-mend/jobpilot**

---

## ✅ Already done (for reference)
- Website live on Render, durable Neon Postgres, Gemini AI tailoring.
- Email alerts via Resend — a real digest (27 matches) was delivered to
  `jobpilot86@gmail.com`.
- Daily scan (GitHub Actions) + monthly cleanup + keep-alive all scheduled.
- Accounts, apply flow, password reset, and an admin console are built and deployed.
- GitHub Actions secrets set: `DATABASE_URL`, `RESEND_API_KEY`, `RESEND_FROM`, `BASE_URL`.

---

## ▢ ACTION 1 — Make yourself admin (2 minutes)

**Why:** your account `jobpilot86@gmail.com` was created *before* the admin feature
existed, so it isn't flagged as admin yet. Setting `ADMIN_EMAILS` grants admin at your
next login.

**Steps:**
1. Go to the Render dashboard → your **jobpilot** service → **Environment**.
2. Add a variable:
   - Key: `ADMIN_EMAILS`
   - Value: `jobpilot86@gmail.com`
3. **Save** (Render redeploys automatically, ~1–3 min).
4. Go to https://jobpilot-cv39.onrender.com → **Log out** (if logged in) → **Log in**
   again as `jobpilot86@gmail.com`.
5. You should now see an **Admin** link in the top menu. Click it (or go to `/admin`) —
   you'll see the list of everyone who signed up, with **Revoke** and **Delete** buttons.

**How to confirm it worked:** the `/admin` page shows a table of users (not a
"you don't have admin access" message).

More detail: [`ADMIN.md`](ADMIN.md).

---

## ▢ ACTION 2 — Change your JobPilot password (1 minute)

**Why:** I set a temporary password (`jobpilot2026`) to run the live tests, and it
appeared in our chat. This is your **JobPilot website** password — NOT your Gmail
password (your Gmail was never touched).

**Steps:**
1. Log in at https://jobpilot-cv39.onrender.com as `jobpilot86@gmail.com`.
2. Click **Account** in the top menu.
3. Under **Change password**: enter current (`jobpilot2026`) and a new password → **Update
   password**.

(If you ever forget it: **Log in → Forgot password?** sends a reset link to your inbox.)

More detail: [`PASSWORD_RESET.md`](PASSWORD_RESET.md).

---

## ▢ ACTION 3 (optional, later) — Let OTHER people get email alerts

Right now other people can **sign up and use the site**, but email alerts only reach
**your** Resend-registered address. To email everyone, verify a domain you own in Resend
(costs ~$10/yr for the domain; everything else stays free).

Full step-by-step: [`CUSTOM_DOMAIN.md`](CUSTOM_DOMAIN.md).

---

## Everyday use (once Actions 1 & 2 are done)
1. **Log in.**
2. **CV page** → upload your CV (improves matching + tailoring).
3. **Queue page** → add one or more **saved searches** (e.g. "remote python backend").
4. Each day at 06:00 UTC the scan emails you new matches. Open the app, review the queue,
   **Tailor**, then **Open & apply** on the job site.
5. **Admin page** (you only) → manage who's signed up.

## If something looks off, start here
- `CAVEATS.md` — the honest list of current limitations and how to lift them.
- `GO_LIVE_CHECKLIST.md` — the `/api/status` self-check and how to send a test email.
- `LIVE_APP_GUIDE.md` — why the first visit can be slow (free-tier sleep) + keep-alive.

## Where things live (so you can find them later)
| Area | File(s) |
|------|---------|
| Accounts / login / admin / reset | `app/services/auth.py`, `app/routers/auth.py` |
| Email sending | `app/services/notify.py` |
| Database + migrations | `app/database.py` |
| Settings (env vars) | `app/config.py`, `.env.example` |
| Daily scan / cleanup entrypoint | `app/cli.py`, `.github/workflows/` |
| All guides | `docs/` |
