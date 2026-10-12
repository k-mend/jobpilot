"""CV parsing, profile extraction, tailoring, and cover-letter generation.

Everything degrades to deterministic templates when no LLM key is configured, so the
feature works for free.
"""
from __future__ import annotations

import io
import json
import re
from typing import List, Optional

from app.models.schemas import CVProfile, RawJob
from app.services import llm

# A pragmatic skill lexicon used by the free (no-LLM) parser.
SKILL_LEXICON = [
    "python", "java", "javascript", "typescript", "go", "golang", "rust", "c++",
    "c#", "ruby", "php", "scala", "kotlin", "swift", "sql", "nosql",
    "fastapi", "django", "flask", "node", "express", "react", "vue", "angular",
    "spring", "rails", "laravel", "dotnet", ".net",
    "postgres", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
    "kafka", "rabbitmq", "graphql", "rest", "grpc", "ci/cd", "git",
    "machine learning", "ml", "nlp", "pytorch", "tensorflow", "pandas", "numpy",
    "data", "etl", "spark", "airflow", "devops", "linux", "bash",
]

TITLE_HINTS = [
    "engineer", "developer", "architect", "scientist", "analyst", "manager",
    "designer", "lead", "consultant", "administrator", "specialist",
]


def extract_text(filename: str, content: bytes) -> str:
    """Extract plain text from PDF/DOCX/MD/TXT bytes."""
    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception:
            return ""
    if name.endswith(".docx"):
        try:
            import docx

            doc = docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            return ""
    # md / txt / anything else: decode as text
    try:
        return content.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _derive_profile(text: str) -> CVProfile:
    lowered = text.lower()
    skills = []
    for skill in SKILL_LEXICON:
        if re.search(r"\b" + re.escape(skill) + r"\b", lowered):
            skills.append(skill)

    titles: List[str] = []
    for line in text.splitlines():
        low = line.lower().strip()
        if not low or len(low) > 60:
            continue
        if any(h in low for h in TITLE_HINTS):
            titles.append(line.strip())
        if len(titles) >= 5:
            break

    years: Optional[int] = None
    m = re.search(r"(\d{1,2})\+?\s*(?:years|yrs)", lowered)
    if m:
        years = int(m.group(1))

    summary = ""
    for line in text.splitlines():
        s = line.strip()
        if len(s) > 40:
            summary = s
            break

    return CVProfile(
        summary=summary,
        skills=skills,
        titles=titles,
        years_experience=years,
        raw_text=text,
    )


def parse_cv(filename: str, content: bytes) -> CVProfile:
    """Extract text and derive a structured profile."""
    text = extract_text(filename, content)
    return _derive_profile(text)


def profile_to_json(profile: CVProfile) -> str:
    return json.dumps(
        {
            "summary": profile.summary,
            "skills": profile.skills,
            "titles": profile.titles,
            "years_experience": profile.years_experience,
        }
    )


def profile_from_json(raw: str, raw_text: str = "") -> CVProfile:
    data = json.loads(raw or "{}")
    return CVProfile(
        summary=data.get("summary", ""),
        skills=data.get("skills", []),
        titles=data.get("titles", []),
        years_experience=data.get("years_experience"),
        raw_text=raw_text,
    )


def tailor_cv(profile: CVProfile, job: RawJob) -> str:
    """Produce a job-tailored CV. Uses LLM if available, else a template."""
    prompt = (
        "Rewrite the following CV to target this job. Keep it truthful, reorder and "
        "emphasize the most relevant skills and experience, use clear sections, and "
        "mirror the job's key terminology.\n\n"
        f"JOB TITLE: {job.title}\nCOMPANY: {job.company}\n"
        f"JOB DESCRIPTION:\n{job.description[:4000]}\n\n"
        f"CURRENT CV:\n{profile.raw_text[:6000]}\n"
    )
    out = llm.complete(prompt, max_output_tokens=2048)
    if out:
        return out
    return _template_cv(profile, job)


def generate_cover_letter(profile: CVProfile, job: RawJob) -> str:
    """Draft a cover letter. Uses LLM if available, else a template."""
    prompt = (
        "Write a concise, professional cover letter (max ~250 words) for this job, "
        "grounded in the candidate's CV. Avoid clichés and do not invent facts.\n\n"
        f"JOB TITLE: {job.title}\nCOMPANY: {job.company}\n"
        f"JOB DESCRIPTION:\n{job.description[:3000]}\n\n"
        f"CANDIDATE CV:\n{profile.raw_text[:4000]}\n"
    )
    out = llm.complete(prompt, max_output_tokens=800)
    if out:
        return out
    return _template_cover_letter(profile, job)


# --- Deterministic (free) fallbacks -------------------------------------------------

def _template_cv(profile: CVProfile, job: RawJob) -> str:
    relevant = [s for s in profile.skills if s.lower() in job.description.lower()]
    other = [s for s in profile.skills if s not in relevant]
    lines = [
        f"CV TAILORED FOR: {job.title} @ {job.company or 'the company'}",
        "=" * 60,
        "",
        "SUMMARY",
        profile.summary
        or "Experienced professional aligned with this role's requirements.",
        "",
        "MOST RELEVANT SKILLS",
        ", ".join(relevant) or "(add role-specific skills here)",
        "",
        "ADDITIONAL SKILLS",
        ", ".join(other) or "(see full CV)",
        "",
        "EXPERIENCE HIGHLIGHTS",
    ]
    lines += [f"- {t}" for t in profile.titles] or ["- (see full CV)"]
    if profile.years_experience:
        lines += ["", f"YEARS OF EXPERIENCE: {profile.years_experience}+"]
    lines += [
        "",
        "-" * 60,
        "NOTE: Template-generated (no LLM key configured). Set GEMINI_API_KEY for a "
        "fully rewritten CV.",
    ]
    return "\n".join(lines)


def _template_cover_letter(profile: CVProfile, job: RawJob) -> str:
    skills = ", ".join(profile.skills[:5]) or "my background"
    company = job.company or "your team"
    body = profile.summary or (
        "I bring a track record of delivering reliable, well-tested software."
    )
    return (
        f"Dear Hiring Team at {company},\n\n"
        f"I'm excited to apply for the {job.title} role. My experience with {skills} "
        "maps closely to what you're looking for, and I'm confident I can contribute "
        "quickly.\n\n"
        f"{body}\n\n"
        "I'd welcome the chance to discuss how I can help. Thank you for your "
        "consideration.\n\n"
        "Sincerely,\n"
        "[Your Name]\n\n"
        "---\nNOTE: Template-generated (no LLM key configured)."
    )
