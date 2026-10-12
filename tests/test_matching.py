from app.models.schemas import CVProfile, RawJob
from app.services import matching


def test_parse_query_extracts_signals():
    q = matching.parse_query(
        "remote senior python backend role, fintech, no on-call"
    )
    assert q.remote is True
    assert q.seniority == "senior"
    assert "python" in q.keywords
    assert "backend" in q.keywords
    # "no on-call" -> exclude 'on'? we capture the token right after 'no'
    assert "on" in q.exclude or "on-call" in q.exclude


def test_parse_query_junior_mapping():
    q = matching.parse_query("entry level java developer")
    assert q.seniority == "junior"
    assert "java" in q.keywords


def test_score_job_rewards_keyword_and_title_match():
    q = matching.parse_query("remote python backend")
    strong = RawJob(
        source="t", external_id="1",
        title="Senior Python Backend Engineer",
        description="We use python and build backend services.",
        remote=True,
    )
    weak = RawJob(
        source="t", external_id="2",
        title="Marketing Manager",
        description="Social media and campaigns.",
        remote=False,
    )
    assert matching.score_job(strong, q) > matching.score_job(weak, q)


def test_score_job_uses_cv_profile():
    q = matching.parse_query("backend engineer")
    job = RawJob(
        source="t", external_id="1",
        title="Backend Engineer",
        description="Work with fastapi, postgres and docker.",
    )
    with_cv = matching.score_job(
        job, q, CVProfile(skills=["fastapi", "postgres", "docker"])
    )
    without_cv = matching.score_job(job, q, CVProfile(skills=[]))
    assert with_cv > without_cv


def test_rank_jobs_orders_desc():
    q = matching.parse_query("python")
    jobs = [
        RawJob(source="t", external_id="1", title="Chef", description="cooking"),
        RawJob(source="t", external_id="2", title="Python Developer",
               description="python python"),
    ]
    ranked = matching.rank_jobs(jobs, q)
    assert ranked[0][0].title == "Python Developer"
    assert ranked[0][1] >= ranked[1][1]


def test_exclusion_penalizes():
    q = matching.parse_query("python no php")
    job = RawJob(source="t", external_id="1", title="PHP and Python Dev",
                 description="php php php")
    # excluded 'php' present should drag the score down vs a clean python job
    clean = RawJob(source="t", external_id="2", title="Python Dev",
                   description="python backend")
    assert matching.score_job(clean, q) > matching.score_job(job, q)
