from app.models.schemas import RawJob
from app.services import cv


SAMPLE_CV = b"""Jane Doe
Senior Software Engineer with 7 years experience building backend systems.
Skills: Python, FastAPI, PostgreSQL, Docker, AWS, Kubernetes.
Experience:
Backend Engineer at Acme
Software Developer at Globex
"""


def test_extract_text_plaintext():
    text = cv.extract_text("cv.txt", SAMPLE_CV)
    assert "FastAPI" in text


def test_parse_cv_detects_skills_and_years():
    profile = cv.parse_cv("cv.txt", SAMPLE_CV)
    assert "python" in profile.skills
    assert "fastapi" in profile.skills
    assert profile.years_experience == 7


def test_profile_json_roundtrip():
    profile = cv.parse_cv("cv.txt", SAMPLE_CV)
    raw = cv.profile_to_json(profile)
    back = cv.profile_from_json(raw, profile.raw_text)
    assert set(back.skills) == set(profile.skills)
    assert back.years_experience == profile.years_experience


def test_tailor_cv_template_fallback():
    profile = cv.parse_cv("cv.txt", SAMPLE_CV)
    job = RawJob(source="t", external_id="1", title="Backend Engineer",
                 company="Acme", description="python fastapi postgres")
    out = cv.tailor_cv(profile, job)
    assert "Backend Engineer" in out
    assert "fastapi" in out.lower() or "python" in out.lower()


def test_cover_letter_template_fallback():
    profile = cv.parse_cv("cv.txt", SAMPLE_CV)
    job = RawJob(source="t", external_id="1", title="Backend Engineer",
                 company="Acme", description="python")
    letter = cv.generate_cover_letter(profile, job)
    assert "Acme" in letter
    assert "Backend Engineer" in letter
