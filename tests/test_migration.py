import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from sqlalchemy import inspect  # noqa: E402

from app.database import engine, init_db  # noqa: E402


def test_init_db_is_idempotent_and_has_new_columns():
    init_db()
    init_db()  # second call must not raise
    cols = {c["name"] for c in inspect(engine).get_columns("user")}
    for expected in ("is_admin", "is_disabled", "reset_token_hash",
                     "reset_expires_at"):
        assert expected in cols
