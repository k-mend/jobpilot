# Accounts & login (how it works, and the caveats)

## What changed

JobPilot used to just ask for your email as a label — no real login. Now it has proper
**accounts with email + password**, so:

- your CV, saved searches, and applications are tied to **your** account,
- the daily scan knows **who** to email and **what** you've already handled (so it won't
  show you the same job twice or suggest re-applying),
- other people can't see your queue.

## How to use it

1. Go to **Sign up**, enter email + a password (min 8 characters).
2. You're logged in immediately (a secure cookie is set) and sent to your **Queue**.
3. Next time, use **Log in**. Use **Log out** to clear the session.

That's it — Search is public, but CV upload, saving jobs, the queue, and applying all
require being logged in.

## How it works under the hood (plain language)

- **Passwords are hashed with bcrypt.** We never store your actual password — only a
  one-way scrambled version. Even we can't read it.
- **Login is remembered with a signed cookie** (`jobpilot_session`). The cookie only
  contains your user id, and it's cryptographically **signed** with `APP_SECRET` so it
  can't be faked or tampered with. It's `HttpOnly` (JavaScript can't read it) and lasts
  30 days.
- **Ownership checks:** every page that shows an application verifies it belongs to the
  logged-in user, so you can't open someone else's by guessing a URL.

(Relevant code: `app/services/auth.py`, `app/routers/auth.py`.)

## Setup requirement

Set a strong, random **`APP_SECRET`** in production (Render can generate one for you — the
blueprint does this automatically). If you change `APP_SECRET` later, existing login
cookies become invalid and everyone just logs in again. On localhost the default secret
is fine.

## Honest caveats (so you know the limits)

- **This is lightweight session auth, not enterprise SSO.** It's appropriate for a small
  personal/shared app, not a bank.
- **No email verification or password reset yet.** If you forget your password, there's
  currently no self-serve reset flow. (It's on the roadmap — it would reuse the same
  Gmail sender as the job alerts.) For now, keep your password somewhere safe.
- **No rate limiting on login attempts yet.** Fine behind a single personal deployment;
  add it before exposing to many untrusted users.
- **HTTPS matters.** On Render your app is served over HTTPS, so the cookie travels
  encrypted. Don't run the public site over plain HTTP.
- **Durable storage is required** for accounts to persist — see `DATABASE_NEON.md`.
  Without Neon, a redeploy wipes all accounts.

## For developers / CLI

The scan CLI can create "users" without passwords (for seeding/testing). Such a user
**cannot log in** until a password is set via signup with the same email, which upgrades
the account in place (`create_user` handles this). Real people should always sign up
through the web form.
