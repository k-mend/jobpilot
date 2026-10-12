"""Command-line entrypoint used by GitHub Actions and for local ops.

Examples:
    python -m app.cli scan                      # run all active saved searches
    python -m app.cli scan --query "python" ... # ad-hoc one-off search+persist
    python -m app.cli seed --email you@x.com    # create a demo user + saved search
"""
from __future__ import annotations

import argparse
import sys

from sqlmodel import Session, select

from app.database import engine, init_db
from app.models import SavedSearch, User
from app.services import notify
from app.services import queue as queue_service


def _cmd_scan(args: argparse.Namespace) -> int:
    init_db()
    with Session(engine) as session:
        if args.query:
            user = queue_service.get_or_create_user(session, args.email or "cli@local")
            saved = SavedSearch(user_id=user.id, description=args.query, active=True)
            session.add(saved)
            session.commit()
            session.refresh(saved)
            digest = queue_service.run_scan_for_search(session, saved)
            notify.send_digest(user.email, digest)
            print(f"Scan complete: {len(digest)} match(es) for ad-hoc query.")
            return 0

        summary = queue_service.run_all_active_scans(session)
        total = 0
        for user_id, digest in summary.items():
            user = session.get(User, user_id)
            email = user.email if user else str(user_id)
            notify.send_digest(email, digest)
            total += len(digest)
        print(f"Scan complete: {total} new match(es) across "
              f"{len(summary)} user(s).")
        return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    init_db()
    with Session(engine) as session:
        user = queue_service.get_or_create_user(session, args.email, args.name or "")
        existing = session.exec(
            select(SavedSearch).where(SavedSearch.user_id == user.id)
        ).first()
        if not existing:
            session.add(SavedSearch(
                user_id=user.id,
                description=args.query or "remote python backend",
                active=True,
            ))
            session.commit()
        print(f"Seeded user {user.email} (id={user.id}).")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="jobpilot")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scan = sub.add_parser("scan", help="run scheduled scan(s)")
    p_scan.add_argument("--query", default=None, help="ad-hoc query (optional)")
    p_scan.add_argument("--email", default=None, help="user email for ad-hoc query")
    p_scan.add_argument("--limit", type=int, default=None)
    p_scan.set_defaults(func=_cmd_scan)

    p_seed = sub.add_parser("seed", help="create a demo user + saved search")
    p_seed.add_argument("--email", required=True)
    p_seed.add_argument("--name", default="")
    p_seed.add_argument("--query", default=None)
    p_seed.set_defaults(func=_cmd_seed)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
