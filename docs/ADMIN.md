# Admin console — see and manage who signed up

As the owner, you can see everyone who registered on your JobPilot and revoke or delete
accounts.

## Who is an admin?

An account is an admin if **either**:
1. its email is listed in the `ADMIN_EMAILS` env var (comma-separated), **or**
2. it's the **very first account** created on the site (automatic bootstrap, so there's
   always an owner).

Since `jobpilot86@gmail.com` was the first account created, **it is already your admin.**
To be explicit (recommended), also set it in the environment:

- On **Render** → service → Environment: `ADMIN_EMAILS = jobpilot86@gmail.com`
- Admin status is (re)applied on signup and on login, so setting it then logging in
  upgrades the account.

## Where to look

1. Log in as the admin account.
2. Click **Admin** in the top nav (only admins see this link), or go to `/admin`.

You'll see a table of every user:
- **Email** (with an `admin` tag where relevant)
- **Joined** date
- **Apps** — how many applications they've saved
- **Status** — active or revoked
- **Actions** — Revoke / Re-enable, and Delete

## What you can do

### Revoke (disable) an account
Click **Revoke**. The user **can no longer log in**, but their data is kept. Click
**Re-enable** to restore access. Use this to pause an account without losing anything.

### Delete an account
Click **Delete** (asks for confirmation). This **permanently removes** the user and all
their data (applications, CVs, saved searches). This cannot be undone.

### Safety rails
- You can't revoke or delete **your own** admin account from the console (prevents
  locking yourself out).
- Only admins can reach `/admin` or the revoke/delete actions; everyone else is redirected
  or shown "no admin access".

## How it was built (brief)
- `User` gained `is_admin` and `is_disabled` flags (`app/models`).
- `authenticate()` refuses disabled users; admin is granted via `ADMIN_EMAILS` or
  first-user bootstrap (`app/services/auth.py`).
- `/admin`, `/admin/users/{id}/revoke`, `/admin/users/{id}/delete` live in
  `app/routers/auth.py`, each guarded by an `is_admin_user` check.

## Caveats
- **Email alerts to other users** still require a verified domain in Resend — see
  `CUSTOM_DOMAIN.md`. Admin/revoke/delete work regardless.
- Deletion is immediate and permanent (no soft-delete/restore). Revoke first if unsure.
