# Known caveats & limitations (read me)

An honest, consolidated list of what works and what to watch out for.

## Email
- **Alerts only reach your own Resend-registered email** (`jobpilot86@gmail.com`) until
  you verify a domain in Resend. Other users can sign up and use the site, but won't get
  emails yet. Fix: `CUSTOM_DOMAIN.md`.
- **No rate-limiting** on forgot-password requests yet.
- Resend free tier: ~3,000/month, 100/day.

## Accounts & security
- **Lightweight session auth** (bcrypt + signed cookie), not OAuth/SSO. Good for a small
  app, not a bank.
- **No email verification on signup** — anyone can register with any email string.
- **No login attempt rate-limiting / lockout** yet.
- `APP_SECRET` must stay stable in production; changing it logs everyone out.
- Admin delete is **permanent** (no soft-delete/restore). Revoke first if unsure.

## Hosting (free tiers)
- **Render free** sleeps after ~15 min idle; first visit then takes ~30–60s to wake. The
  keep-alive workflow mitigates this (`LIVE_APP_GUIDE.md`).
- **Neon free** auto-suspends when idle; first query after idle is slightly slower.
- Free tiers have limited backups — don't store anything irreplaceable.

## Scanning & matching
- Scan runs **once daily** (06:00 UTC) via GitHub Actions; scheduled runs can be delayed
  when GitHub is busy, and pause after 60 days of repo inactivity (any commit re-arms).
- Matching is rule/keyword + CV-skill based; good, not magical. Tune saved-search wording
  for better results.
- Sources are only boards that allow programmatic access; **LinkedIn is not scraped**
  (`LEGAL.md`).

## Applying
- JobPilot **prepares** applications (tailored CV + cover letter) but does **not**
  auto-submit on job sites — by design (`LEGAL.md`, `APPLY_WORKFLOW.md`).

## Data growth
- Monthly cleanup deletes stale/old backlog so the database stays small (`RETENTION.md`).

## What would lift these limits
- Verify a domain in Resend → email everyone.
- Paid Render/Neon tier → no sleeping, more storage, backups.
- Add rate-limiting + email verification before opening to many untrusted users.
