# Keeping storage small — the monthly cleanup (beginner friendly)

## The problem it solves

Every scan can add job + application rows. Over months that piles up and could overwhelm
a free Neon database. Since **most job postings expire within about a month**, keeping old
entries forever is pointless. So JobPilot runs a **monthly cleanup** that deletes old,
unimportant rows — while carefully **never** touching things you're actively working on.

## When it runs

A GitHub Action (`.github/workflows/cleanup.yml`) runs **on the 1st of each month at
04:00 UTC**. You can also run it any time from GitHub → **Actions → Monthly Cleanup →
Run workflow**, or locally:

```bash
python -m app.cli cleanup
```

## Exactly what gets deleted (and what's protected)

| Item | Deleted when… | Default age |
|------|---------------|-------------|
| **Archived** applications (you marked them done/closed) | older than `RETAIN_ARCHIVED_DAYS` | 90 days |
| **Matched** applications you never acted on (still "matched", never tailored/applied) | older than `RETAIN_STALE_MATCHED_DAYS` | 35 days |
| **Orphan jobs** (job rows with no application attached to anyone) | older than `RETAIN_ORPHAN_JOB_DAYS` | 45 days |

**Always protected — never auto-deleted:**
- applications in `tailored`, `ready`, or `submitted` status (you're actively using them),
- anything newer than the cutoffs above.

So your in-progress and submitted applications are safe regardless of age. Only true
backlog (ignored matches, finished-and-old items, and jobs nobody saved) gets cleared.

## Tuning it

Change these env vars (on GitHub Actions secrets/variables, Render, or `.env`):

```
RETAIN_ARCHIVED_DAYS=90
RETAIN_STALE_MATCHED_DAYS=35
RETAIN_ORPHAN_JOB_DAYS=45
```

Set a number higher to keep things longer, lower to clean more aggressively. Because jobs
expire in ~1 month, 35–45 days for stale items is a sensible default.

(Relevant code: `app/services/queue.py` → `cleanup_old_data`.)

## Caveats

- **Deletion is permanent.** There's no trash/undo. If you want to keep a job long-term,
  move it out of `matched`/`archived` (e.g. mark it `submitted`) or raise the retention
  days.
- **It needs the database URL.** The cleanup Action uses the same `DATABASE_URL` secret as
  the scan (see `DATABASE_NEON.md`). Without it, it would clean a throwaway SQLite file
  and do nothing useful.
- **Monthly, by design.** You asked for monthly (not weekly) because postings expire about
  monthly — so weekly would delete things barely before they'd expire anyway, and monthly
  keeps the database comfortably small.
