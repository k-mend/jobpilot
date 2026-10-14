# Email alerts for new jobs (beginner friendly)

## What this does

Once set up, the **daily scan** emails you a digest of **new** jobs matching your saved
searches — only the ones you haven't already seen/saved/applied to. Empty = no email.

There are two ways to enable email. **Pick ONE.**

- **Option A — Resend (recommended).** An HTTP email API with a free tier. No App
  Password, works immediately — ideal if your Google account is new and can't create App
  Passwords yet.
- **Option B — Gmail SMTP.** Uses your Gmail with a 16-char App Password. Requires the
  account to be old/trusted enough for Google to allow App Passwords.

JobPilot tries Resend first, then Gmail SMTP, then falls back to just logging — it never
crashes the scan.

---

## Option A — Resend (recommended)

### Why
A brand-new Google account often **can't** create App Passwords for days/weeks (Google
shows a "we want to make sure it's really you" block). Resend sidesteps that entirely:
sign up, grab an API key, done.

### Steps
1. Go to <https://resend.com> and sign up (free). You can log in with the same new Google
   account — that's fine, Resend doesn't need an App Password.
2. In the Resend dashboard, open **API Keys → Create API Key**. Copy it (starts with
   `re_...`).
3. Add these settings on **Render** (service → Environment) **and** as **GitHub Actions
   secrets** (repo → Settings → Secrets and variables → Actions):

   | Key | Value |
   |-----|-------|
   | `RESEND_API_KEY` | your `re_...` key |
   | `RESEND_FROM` | `JobPilot <onboarding@resend.dev>` (default; works for testing) |
   | `BASE_URL` | your app URL, e.g. `https://jobpilot-cv39.onrender.com` |

### About the "from" address
- Until you own a domain, use **`onboarding@resend.dev`** (Resend's shared test sender).
  On a free account this reliably delivers **to your own verified email** (the address you
  signed up to Resend with). That's exactly our use case — JobPilot emails *you*.
- Later, if you want to send to *other* people or use your own address, verify a domain in
  Resend and set `RESEND_FROM` to something like `JobPilot <alerts@yourdomain.com>`.

### ⚠️ Important free-tier restriction (this will bite you if you ignore it)
On the free shared sender, Resend **only lets you send to the email address you used to
sign up to Resend** (plus `delivered@resend.dev`). Sending to anything else returns:

```
HTTP 422: Invalid `to` field. Please use our testing email address instead of
domains like `example.com`.
```

So to test alerts, **sign up to JobPilot with the SAME email you used for Resend**, then
trigger a test. JobPilot's `channel` will report `resend` on success, or `resend_error`
with the exact reason if the recipient isn't allowed. To email arbitrary recipients, you
must verify a domain in Resend (see above).

### Free-tier limits
~3,000 emails/month / 100 per day on the free plan — far more than personal use needs.

---

## Option B — Gmail SMTP (if/when App Passwords work for you)

Requires 2-Step Verification ON, then an App Password:
1. <https://myaccount.google.com/security> → enable **2-Step Verification**.
2. <https://myaccount.google.com/apppasswords> → create one named `JobPilot` → copy the
   16 characters (remove spaces).
   - If Google blocks this with a verification message, your account is too new — **use
     Option A instead** for now and come back later.
3. Set on Render + GitHub secrets:

   | Key | Value |
   |-----|-------|
   | `SMTP_HOST` | `smtp.gmail.com` |
   | `SMTP_PORT` | `587` |
   | `SMTP_USER` | your Gmail address |
   | `SMTP_PASSWORD` | the 16-char App Password |
   | `SMTP_FROM` | your Gmail address |

---

## Test it (either option)

1. Log in to the app, go to **Queue**, add a **saved search** (e.g. "remote python
   backend").
2. GitHub repo → **Actions → Daily Scan → Run workflow** (don't wait a day).
3. You should get an email if there were new matches above the score threshold.

## How it chooses a channel

`app/services/notify.py` tries, in order: **Resend → Gmail SMTP → Telegram → log**. It
uses the first one that's configured, and skips sending when there are no new matches.

## Caveats

- **Deliverability:** with the shared `onboarding@resend.dev` sender, mail goes reliably
  to your own Resend-verified inbox; sending to arbitrary strangers needs a verified
  domain. For personal alerts you're fine.
- **Keep keys secret.** If a key leaks, rotate it in the provider dashboard.
- **One channel is enough.** If both Resend and SMTP are set, Resend wins.
