import time

from resonarr.app.read_model_errors import SnapshotUnavailableError
from resonarr.config.settings import DASHBOARD_SNAPSHOT_TTL_SECONDS
from resonarr.state.memory_store import MemoryStore


class DashboardSnapshotQueryService:
    SNAPSHOT_NAME = "home_summary"

    def __init__(self, memory=None):
        self.memory = memory or MemoryStore()

    def _compute_age_seconds(self, updated_ts):
        if updated_ts is None:
            return None

        age_seconds = int(time.time()) - int(updated_ts)
        if age_seconds < 0:
            age_seconds = 0

        return age_seconds

    def get_snapshot_health(self):
        snapshot = self.memory.get_dashboard_snapshot(self.SNAPSHOT_NAME) or {}
        payload = snapshot.get("payload")
        updated_ts = snapshot.get("updated_ts")
        age_seconds = self._compute_age_seconds(updated_ts)

        if not payload or updated_ts is None:
            return {
                "available": False,
                "reason": "snapshot_miss",
                "updated_ts": updated_ts,
                "age_seconds": age_seconds,
                "ttl_seconds": DASHBOARD_SNAPSHOT_TTL_SECONDS,
            }

        if age_seconds is not None and age_seconds > DASHBOARD_SNAPSHOT_TTL_SECONDS:
            return {
                "available": False,
                "reason": "snapshot_expired",
                "updated_ts": updated_ts,
                "age_seconds": age_seconds,
                "ttl_seconds": DASHBOARD_SNAPSHOT_TTL_SECONDS,
            }

        if not isinstance(payload, dict):
            return {
                "available": False,
                "reason": "snapshot_invalid",
                "updated_ts": updated_ts,
                "age_seconds": age_seconds,
                "ttl_seconds": DASHBOARD_SNAPSHOT_TTL_SECONDS,
            }

        required_keys = {"home_summary", "sections", "highlights"}
        if not required_keys.issubset(payload.keys()):
            return {
                "available": False,
                "reason": "snapshot_invalid",
                "updated_ts": updated_ts,
                "age_seconds": age_seconds,
                "ttl_seconds": DASHBOARD_SNAPSHOT_TTL_SECONDS,
            }

        return {
            "available": True,
            "reason": None,
            "updated_ts": updated_ts,
            "age_seconds": age_seconds,
            "ttl_seconds": DASHBOARD_SNAPSHOT_TTL_SECONDS,
        }

    def get_home(self):
        health = self.get_snapshot_health()

        if not health["available"]:
            raise SnapshotUnavailableError(
                snapshot_name=self.SNAPSHOT_NAME,
                reason=health["reason"],
                ttl_seconds=health["ttl_seconds"],
                updated_ts=health["updated_ts"],
                age_seconds=health["age_seconds"],
            )

        snapshot = self.memory.get_dashboard_snapshot(self.SNAPSHOT_NAME) or {}
        payload = snapshot.get("payload") or {}

        print(
            f"[PERF][dashboard_snapshot] snapshot_read_hit: "
            f"age_seconds={health['age_seconds']} "
            f"ttl_seconds={health['ttl_seconds']}"
        )

        return {
            "status": "success",
            "read_path": "snapshot",
            "snapshot_updated_ts": health["updated_ts"],
            "snapshot_age_seconds": health["age_seconds"],
            "home_summary": payload.get("home_summary", {}),
            "sections": payload.get("sections", {}),
            "highlights": payload.get("highlights", {}),
        }
