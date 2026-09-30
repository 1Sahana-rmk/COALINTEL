"""Cron/worker entrypoint for the once-per-24-hour official sync."""

from database import SessionLocal
from app.services.official_source_connector import MinistryOfCoalConnector
from app.services.official_sync_service import ensure_ministry_source, run_due_syncs


def main() -> None:
    db = SessionLocal()
    try:
        ensure_ministry_source(db)
        result = run_due_syncs(db, lambda source: MinistryOfCoalConnector())
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
