class SnapshotUnavailableError(Exception):
    def __init__(
        self,
        *,
        snapshot_name,
        reason,
        ttl_seconds=None,
        updated_ts=None,
        age_seconds=None,
    ):
        self.snapshot_name = snapshot_name
        self.reason = reason
        self.ttl_seconds = ttl_seconds
        self.updated_ts = updated_ts
        self.age_seconds = age_seconds

        super().__init__(f"{snapshot_name} snapshot unavailable: {reason}")

    def to_details(self):
        return {
            "snapshot_name": self.snapshot_name,
            "reason": self.reason,
            "ttl_seconds": self.ttl_seconds,
            "updated_ts": self.updated_ts,
            "age_seconds": self.age_seconds,
        }
