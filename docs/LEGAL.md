# Legal, ToS, and the LinkedIn question

JobPilot is built to be useful **without** getting its users banned or breaking the law.

## LinkedIn

- LinkedIn's User Agreement **prohibits** automated scraping and automated interaction
  (including auto-apply bots) using your credentials. Doing so risks **permanent account
  suspension**.
- The official **LinkedIn Jobs API is partner-only** and not available to individual
  developers for pulling the jobs feed or submitting applications.
- Therefore JobPilot does **not** log into LinkedIn, store LinkedIn passwords, or scrape
  it. Instead:
  - Users can **paste a job URL/description** from anywhere (including LinkedIn) and
    JobPilot will tailor a CV + cover letter for it and add it to the queue.
  - JobPilot sources jobs from boards that **permit** programmatic access. A large share
    of roles posted on LinkedIn also appear on these boards or the company's own
    Greenhouse/Lever/Ashby page, which we can read legally.

## Auto-submission

JobPilot prepares everything and queues it for **human approval**. We deliberately avoid
blind auto-submission because:
- Many portals use CAPTCHAs and custom per-job questions that cannot be answered
  reliably without the applicant.
- Blind submissions are low quality and tend to be auto-rejected.
- Mass automated submission can violate a site's ToS and flag your email/accounts.

Where a job source documents a legitimate programmatic application path (e.g. apply by
email), a connector may send with explicit user opt-in.

## Job sources

Only sources whose terms allow programmatic/API access are enabled by default. If you add
a custom source, confirm its ToS first. Respect rate limits; the connectors are polite by
default.

## Data & privacy

- CVs and user data live in a local SQLite file you control.
- No user data is sent to third parties except the LLM provider **you** configure
  (optional). With no key configured, nothing leaves your machine/runner.
