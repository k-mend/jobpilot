# How to apply for jobs with JobPilot (beginner friendly)

This is the full, click-by-click walkthrough of using JobPilot to find a job, tailor your
CV, and apply. No technical knowledge needed.

**Live app:** https://jobpilot-cv39.onrender.com

> First, the honest bit: JobPilot does **not** click "submit" on job sites for you.
> It does everything *up to* that point — finds jobs, scores them against your CV, writes
> a tailored CV and cover letter, and keeps track of each application — then you do the
> final submit on the job site (one copy-paste). Why? See the "Why not fully automatic?"
> section at the end. This is deliberate, and it's what keeps your applications high
> quality and your accounts safe.

---

## The whole flow in one picture

```
Upload CV  ─▶  Search jobs  ─▶  Save ones you like  ─▶  Open each in your Queue
                                                              │
                                                              ▼
                 Tailor (CV + cover letter)  ─▶  Copy/Download  ─▶  Apply on the job site
                                                              │
                                                              ▼
                                              Mark it "submitted" to track it
```

---

## Step 1 — Upload your CV (do this once)

1. Open the app and click **CV** in the top menu.
2. Enter your email (this is your identity in JobPilot — no password needed).
3. Choose your CV file (PDF, Word .docx, or plain text) and click **Upload & parse**.
4. You'll see the skills JobPilot detected. That's it.

> Why: your CV powers two things — better job *matching*, and the *tailoring* of each
> application. You can re-upload anytime; the newest one is used.

## Step 2 — Search for jobs

1. Click **Search** (the home page).
2. Describe the job in plain English, e.g.
   *"remote senior python backend role, fintech, no on-call"*.
3. (Optional) put your email in the box so results can use your CV for scoring.
4. Click **Find jobs**. You'll get a ranked list — the number on the left is the match
   score (higher = better fit).

## Step 3 — Save the jobs you want to apply to

On the results page:
1. Type your email in the bar at the top (needed to save).
2. For any job you like, click **“Save to apply →”**.
3. JobPilot saves it to your **Queue** and takes you straight to that job's **apply
   page**. If you've uploaded a CV, it also *immediately* writes a tailored CV + cover
   letter for that job.

## Step 4 — Prepare & apply (the apply page)

Each saved job has its own page with **3 steps**:

**Step 1 — Prepare documents.** If the tailored CV / cover letter aren't there yet, click
**Tailor now** (needs a CV uploaded). You'll get:
- a **Tailored CV** box — with **Copy** and **Download .txt** buttons,
- a **Cover letter** box — same buttons.

**Step 2 — Apply on the job site.** Click **Open job posting ↗**. It opens the real job
listing in a new tab. Paste your tailored CV + cover letter into their application form
and submit there.

**Step 3 — Track status.** Use the dropdown to set the status:
- `matched` → you saved it
- `tailored` → documents generated
- `ready` → you're about to apply
- `submitted` → you applied ✅
- `archived` → done/closed

## Step 5 — Manage everything from the Queue

Click **Queue**, enter your email, and you'll see all your saved jobs with their
statuses. Click any one to go back to its apply page.

---

## Tips

- **Better documents:** by default JobPilot uses free templates. Add a free AI key
  (OpenRouter or Gemini) for fully rewritten, sharper CVs/cover letters — see
  [`LLM_PROVIDERS.md`](LLM_PROVIDERS.md). (Your live app already has a Gemini key set.)
- **Re-tailor anytime:** on the apply page, click **Re-tailor** to regenerate.
- **Paste a job from anywhere (incl. LinkedIn):** there isn't a dedicated paste box yet
  (see roadmap), but you can save jobs found via JobPilot's search today.

---

## Why not fully automatic ("apply while I sleep")?

Short version — it would hurt you:
- Most job sites use **CAPTCHAs** and **custom questions** ("Why do you want to work
  here?") that a bot can't answer well.
- **Blindly submitted** applications are low quality and often auto-rejected.
- Mass auto-submission can **violate sites' terms** and get your email/accounts flagged.
- **LinkedIn** specifically bans automated applying with your login (and their jobs API
  isn't open to individuals).

So JobPilot removes ~90% of the effort (finding, matching, writing, organizing) and
leaves the final human click to you. Details and the LinkedIn stance:
[`LEGAL.md`](LEGAL.md).

---

## Quick troubleshooting

| Problem | Fix |
|--------|-----|
| "Save to apply" asks for email | Type your email in the top bar first. |
| No tailored CV on the apply page | Upload a CV on the **CV** page, then click **Tailor now**. |
| Documents look like a template, not AI-written | No AI key set, or the free model was busy. See LLM_PROVIDERS.md. |
| Queue is empty | Enter the same email you used to save jobs. |
| First load is slow (~30–60s) | Free host was asleep; see LIVE_APP_GUIDE.md. |
