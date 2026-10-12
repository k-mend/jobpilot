"""Natural-language query parsing and job scoring.

Rule/keyword based so it works with zero API keys. If an LLM key is present the query
parse can be refined, but the deterministic path is always available and is what the
tests exercise.
"""
from __future__ import annotations

import re
from typing import List, Optional

from app.models.schemas import CVProfile, RawJob, SearchQuery

SENIORITY_TERMS = {
    "intern": "junior",
    "junior": "junior",
    "entry": "junior",
    "graduate": "junior",
    "mid": "mid",
    "intermediate": "mid",
    "senior": "senior",
    "sr": "senior",
    "staff": "lead",
    "principal": "lead",
    "lead": "lead",
    "head": "lead",
}

# Common filler words we don't want as "keywords".
STOPWORDS = {
    "a", "an", "the", "and", "or", "for", "to", "in", "on", "with", "no", "as",
    "role", "roles", "job", "jobs", "position", "want", "looking", "need", "i",
    "me", "my", "of", "at", "that", "which", "work", "working", "time", "zone",
}

REMOTE_HINTS = ("remote", "work from home", "wfh", "anywhere")
EXCLUDE_HINT = re.compile(r"\bno\s+([a-z\-]+)", re.IGNORECASE)


def parse_query(text: str) -> SearchQuery:
    """Turn a free-text job description into a structured SearchQuery."""
    lowered = text.lower()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z\+\#\.\-]*", lowered)

    seniority: Optional[str] = None
    for tok in tokens:
        if tok in SENIORITY_TERMS:
            seniority = SENIORITY_TERMS[tok]
            break

    remote: Optional[bool] = None
    if any(h in lowered for h in REMOTE_HINTS):
        remote = True

    exclude = [m.group(1).lower() for m in EXCLUDE_HINT.finditer(lowered)]

    keywords: List[str] = []
    for tok in tokens:
        if tok in STOPWORDS or tok in SENIORITY_TERMS or tok in exclude:
            continue
        if len(tok) <= 1:
            continue
        if tok not in keywords:
            keywords.append(tok)

    return SearchQuery(
        raw=text,
        keywords=keywords,
        seniority=seniority,
        remote=remote,
        locations=[],
        exclude=exclude,
    )


def _norm(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").lower()


def score_job(
    job: RawJob,
    query: SearchQuery,
    profile: Optional[CVProfile] = None,
) -> float:
    """Return a 0-100 relevance score for job vs query (and optional CV)."""
    title = _norm(job.title)
    body = _norm(job.description)
    tags = " ".join(t.lower() for t in job.tags)

    score = 0.0

    # Keyword overlap (query -> job). Title hits weigh more than body hits.
    kw = [k.lower() for k in query.keywords] or []
    if kw:
        title_hits = sum(1 for k in kw if k in title)
        body_hits = sum(1 for k in kw if k in body or k in tags)
        score += 35.0 * (title_hits / len(kw))
        score += 25.0 * (body_hits / len(kw))

    # Exclusions are hard penalties.
    for ex in query.exclude:
        if ex and (ex in title or ex in body):
            score -= 25.0

    # Seniority alignment.
    if query.seniority:
        if query.seniority in title or query.seniority in body:
            score += 10.0
        else:
            score -= 3.0

    # Remote preference.
    if query.remote:
        if job.remote or "remote" in title or "remote" in _norm(job.location):
            score += 10.0
        else:
            score -= 5.0

    # CV skill overlap.
    if profile and profile.skills:
        skills = [s.lower() for s in profile.skills]
        skill_hits = sum(1 for s in skills if s in title or s in body or s in tags)
        score += 20.0 * (skill_hits / len(skills))

    return max(0.0, min(100.0, round(score, 1)))


def rank_jobs(
    jobs: List[RawJob],
    query: SearchQuery,
    profile: Optional[CVProfile] = None,
):
    """Return (job, score) pairs sorted high-to-low."""
    scored = [(j, score_job(j, query, profile)) for j in jobs]
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored
