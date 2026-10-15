# Upgrading to your own domain (to email all your users)

Right now, email alerts only deliver to **your own** Resend-registered address
(`jobpilot86@gmail.com`), because you're using Resend's shared `onboarding@resend.dev`
sender. To let **everyone** who signs up receive their job alerts, you verify a domain you
own in Resend. One-time setup; then it just works for all users.

## What you need
- A domain you own (e.g. `yourjobpilot.com`). Buy one from any registrar (~$10/yr —
  this is the only non-free part, and it's optional).

## Steps

### 1. Add the domain in Resend
1. Resend dashboard → **Domains** → **Add Domain**.
2. Enter your domain (e.g. `yourjobpilot.com`).
3. Resend shows **DNS records** to add (SPF, DKIM, and usually a return-path/MX).

### 2. Add those DNS records at your registrar
In your domain's DNS settings, add each record exactly as Resend shows (TXT/CNAME/MX).
Then click **Verify** in Resend. Verification can take minutes to a few hours.

### 3. Point JobPilot at the new sender
Set `RESEND_FROM` to an address **on your verified domain**, in both places:
- **Render** → Environment → `RESEND_FROM = JobPilot <alerts@yourjobpilot.com>`
- **GitHub Actions** secret → `RESEND_FROM = JobPilot <alerts@yourjobpilot.com>`

(The address local-part, e.g. `alerts@`, can be anything at your domain — no mailbox
needs to exist for sending.)

### 4. Done
Now the daily scan can email **any** user at **any** address. No code changes — JobPilot
already reads `RESEND_FROM` from the environment.

## Optional: a custom web address too
You can also serve the site at your domain:
- Render → service → **Settings → Custom Domains** → add `app.yourjobpilot.com`, then add
  the CNAME Render gives you at your registrar.
- Update `BASE_URL` (Render + GitHub secret) to the new URL so email links point there.

## Costs & limits (honest)
- The domain itself costs money (~$10/yr). Everything else stays on free tiers.
- Resend free tier: ~3,000 emails/month, 100/day. Plenty for a modest user base; upgrade
  Resend if you outgrow it.
- Deliverability improves with a verified domain (less likely to hit spam) vs the shared
  test sender.
