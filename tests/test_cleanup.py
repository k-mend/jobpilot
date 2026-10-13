import os
import tempfile
from datetime import datetime, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from sqlmodel import Session  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.models import Application, Job, User  # noqa: E402
from app.services import queue as queue_service  # noqa: E402

init_db()


def _old(days):
    return datetime.utcnow() - timedelta(days=days)


def test_cleanup_removes_stale_but_keeps_active():
    with Session(engine) as s:
        user = User(email="cleanup@example.com", password_hash="x")
        s.add(user)
        s.commit()
        s.refresh(user)

        # job + 4 applications in different states/ages
        job = Job(source="t", external_id="j1", title="Old Job", created_at=_old(100))
        s.add(job)
        s.commit()
        s.refresh(job)

        stale_archived = Application(user_id=user.id, job_id=job.id,
                                     status="archived", updated_at=_old(120))
        stale_matched = Application(user_id=user.id, job_id=job.id,
                                    status="matched", created_at=_old(60))
        active_submitted = Application(user_id=user.id, job_id=job.id,
                                       status="submitted", updated_at=_old(200))
        recent_matched = Application(user_id=user.id, job_id=job.id,
                                     status="matched", created_at=_old(1))
        s.add_all([stale_archived, stale_matched, active_submitted, recent_matched])
        s.commit()

        result = queue_service.cleanup_old_data(s)

        # stale archived + stale matched removed; active + recent kept
        assert result["removed_applications"] == 2
        from sqlmodel import select
        remaining = s.exec(
            select(Application).where(Application.user_id == user.id)
        ).all()
        statuses = sorted(a.status for a in remaining)
        assert statuses == ["matched", "submitted"]  # recent matched + active submitted


def test_cleanup_removes_orphan_jobs():
    with Session(engine) as s:
        orphan = Job(source="t", external_id="orphan", title="Nobody wants me",
                     created_at=_old(100))
        s.add(orphan)
        s.commit()
        before = s.get(Job, orphan.id)
        assert before is not None
        result = queue_service.cleanup_old_data(s)
        assert result["removed_jobs"] >= 1
        assert s.get(Job, orphan.id) is None
