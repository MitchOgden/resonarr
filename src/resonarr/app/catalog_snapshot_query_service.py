from resonarr.app.catalog_query_service import CatalogQueryService
from resonarr.app.read_model_errors import SnapshotUnavailableError
from resonarr.config.settings import CATALOG_SNAPSHOT_TTL_SECONDS


class CatalogSnapshotQueryService:
    def __init__(self, catalog_query_service=None):
        self.catalog_query_service = catalog_query_service or CatalogQueryService()

    def get_snapshot_health(self):
        records, meta = self.catalog_query_service.get_snapshot_records()
        read_path = meta.get("read_path")
        available = read_path == "snapshot"

        return {
            "available": available,
            "reason": None if available else read_path,
            "updated_ts": meta.get("snapshot_updated_ts"),
            "age_seconds": meta.get("snapshot_age_seconds"),
            "ttl_seconds": CATALOG_SNAPSHOT_TTL_SECONDS,
            "record_count": len(records) if available else 0,
        }

    def _require_snapshot_records(self):
        records, meta = self.catalog_query_service.get_snapshot_records()
        read_path = meta.get("read_path")

        if read_path != "snapshot":
            raise SnapshotUnavailableError(
                snapshot_name=self.catalog_query_service.SNAPSHOT_NAME,
                reason=read_path,
                ttl_seconds=CATALOG_SNAPSHOT_TTL_SECONDS,
                updated_ts=meta.get("snapshot_updated_ts"),
                age_seconds=meta.get("snapshot_age_seconds"),
            )

        return records, meta

    def query_records(
        self,
        *,
        kind=None,
        source=None,
        status=None,
        artist_name_contains=None,
        album_title_contains=None,
        artist_mbid=None,
        live_only=False,
        historical_only=False,
        event_ts_min=None,
        event_ts_max=None,
        sort_by="source",
        sort_direction="asc",
        limit=None,
        offset=0,
    ):
        records, meta = self._require_snapshot_records()

        payload = self.catalog_query_service.query_records(
            kind=kind,
            source=source,
            status=status,
            artist_name_contains=artist_name_contains,
            album_title_contains=album_title_contains,
            artist_mbid=artist_mbid,
            live_only=live_only,
            historical_only=historical_only,
            event_ts_min=event_ts_min,
            event_ts_max=event_ts_max,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=limit,
            offset=offset,
            records=records,
            force_refresh=False,
        )

        payload["read_path"] = meta.get("read_path")
        payload["snapshot_age_seconds"] = meta.get("snapshot_age_seconds")
        payload["snapshot_updated_ts"] = meta.get("snapshot_updated_ts")
        return payload
