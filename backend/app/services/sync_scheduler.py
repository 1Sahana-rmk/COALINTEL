"""Small scheduler abstraction that can be called by cron, a worker, or startup."""

from datetime import datetime, timezone


class OfficialSyncScheduler:
    interval_seconds = 24 * 60 * 60

    def is_due(self, last_sync_at):
        return last_sync_at is None or (datetime.now(timezone.utc) - last_sync_at).total_seconds() >= self.interval_seconds

    def run_once(self, db, connector_factory, *, force=False, user_id=None):
        from app.services.official_sync_service import run_due_syncs
        return run_due_syncs(db, connector_factory, force=force, user_id=user_id)
