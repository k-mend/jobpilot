# Password change & reset (how it's built + how to use it)

Two ways to change a password: **logged-in change** and **forgot-password email reset**.

## For users

### Change your password (while logged in)
1. Click **Account** in the top nav (visible when logged in).
2. Enter your **current** password and a **new** one (min 8 chars) → **Update password**.

### Reset a forgotten password
1. On the **Log in** page, click **Forgot password?**
2. Enter your email → you get a reset link by email (valid **60 minutes**).
3. Open the link, set a new password, then log in.

> The reset email is sent through the same channel as job alerts (Resend). The
> free-tier recipient restriction applies — see `EMAIL_ALERTS.md`. For your own admin
> account (the Resend-registered email) it works out of the box.

## How it was built (for your learning)

### Data model (`app/models/__init__.py`)
Two fields were added to `User`:
- `reset_token_hash` — the **hash** of the reset token (never the raw token),
- `reset_expires_at` — when the token stops working.

### Service logic (`app/services/auth.py`)
- `change_password(session, user, current, new)` — verifies the current password with
  bcrypt, then stores a new bcrypt hash. Returns False if the current one is wrong.
- `create_reset_token(session, email)` — generates a cryptographically random token with
  `secrets.token_urlsafe(32)`, stores only its **bcrypt hash** + a 60-minute expiry, and
  returns the **raw** token (to email once). Storing only the hash means a database leak
  can't reveal usable tokens.
- `reset_password_with_token(session, email, token, new)` — checks the token hash matches
  and isn't expired, sets the new password, then **clears the token** (single-use).

### Routes (`app/routers/auth.py`)
- `GET/POST /account` + `/account/password` — the logged-in change form.
- `GET/POST /forgot-password` — issues a token and emails the link. It always shows the
  same "if that email has an account…" message so it never reveals whether an email is
  registered (prevents account enumeration).
- `GET/POST /reset-password` — the form the email link opens; consumes the token.

### Email (`app/services/notify.py`)
`send_reset_email(to, url)` reuses the Resend/SMTP sender via a shared `_send_raw` helper.

### Security choices worth noting
- Tokens are **random, hashed-at-rest, single-use, and time-limited**.
- The forgot flow is **enumeration-safe** (identical response for known/unknown emails).
- Passwords are always bcrypt-hashed; plaintext is never stored or logged.

### Tests (`tests/test_account_admin.py`)
Cover: wrong vs correct current password, token issue→consume→reuse-blocked, expired
token rejected, and the generic forgot-password response.

## Caveats
- Reset **requires email to be working** (Resend/SMTP). With no email configured, the
  link is only printed to logs.
- There's no rate-limiting on reset requests yet — fine for a small app; add it before
  large-scale public use.
