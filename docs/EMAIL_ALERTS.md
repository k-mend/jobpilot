# Email alerts for new jobs (Gmail SMTP — beginner friendly)

## What this does

Once set up, the **daily scan** emails you a digest of **new** jobs that match your saved
searches — only the ones you haven't already seen/saved/applied to. No duplicates, no
spam about jobs you've handled.

> You said you have a dedicated email account for this project — perfect. Use that one.

## Why an "App Password" (not your normal password)

Gmail blocks apps from logging in with your regular password. Instead you create a
**16-character App Password** just for JobPilot. It only works for sending mail and you
can revoke it anytime. (This requires 2-Step Verification to be ON for that Gmail
account.)

## Step 1 — Turn on 2-Step Verification

1. Sign in to the dedicated Gmail account.
2. Go to <https://myaccount.google.com/security>.
3. Under **How you sign in to Google**, enable **2-Step Verification**.

## Step 2 — Create an App Password

1. Go to <https://myaccount.google.com/apppasswords>.
2. App name: type `JobPilot`. Click **Create**.
3. Google shows a **16-character password** like `abcd efgh ijkl mnop`. Copy it
   **without spaces**: `abcdefghijklmnop`.

## Step 3 — Give the credentials to JobPilot

Set these environment variables. On **Render**: your service → **Environment** →
add each one. For the daily scan on **GitHub**: repo → **Settings → Secrets and variables
→ Actions** → add each as a secret.

| Variable | Value |
|----------|-------|
| `SMTP_HOST` | `smtp.gmail.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | your dedicated Gmail address, e.g. `you.jobpilot@gmail.com` |
| `SMTP_PASSWORD` | the 16-char App Password (no spaces) |
| `SMTP_FROM` | same Gmail address (what recipients see as sender) |
| `BASE_URL` | your live app URL, e.g. `https://jobpilot-cv39.onrender.com` (used for the "open your queue" link in the email) |

Locally you can put the same lines in `.env`.

## Step 4 — Test it

- In the app, log in, go to **Queue**, and add a **saved search** (e.g. "remote python
  backend").
- Trigger the scan now instead of waiting a day: GitHub repo → **Actions → Daily Scan →
  Run workflow**.
- You should receive an email if there were new matches above the score threshold.

## How JobPilot sends it (and safe fallbacks)

- It uses Python's standard SMTP over STARTTLS — no extra libraries.
- If SMTP isn't configured, it tries Telegram (optional) and finally just logs the digest
  — it never crashes the scan.
- It **skips sending entirely when there are no new matches**, so you won't get empty
  emails.

(Relevant code: `app/services/notify.py`.)

## Caveats

- **Gmail sending limits:** a normal Gmail account can send ~500 emails/day. Fine for
  personal/small use; not for mass mailing.
- **App Password requires 2-Step Verification** on that account — there's no way around
  it, and that's a good thing for security.
- **Deliverability:** mail from a personal Gmail may occasionally land in Spam for other
  recipients. For yourself it's usually fine. A dedicated transactional service would be
  the step up if you outgrow this.
- **Keep the App Password secret.** If it leaks, revoke it at the App Passwords page and
  create a new one.
