from resonarr.app.prune_query_service import PruneQueryService
from resonarr.config.settings import (
    PRUNE_ENABLE_ARTIST_PRUNE,
    PRUNE_RESCAN_PLEX_AFTER_EXECUTION,
)
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.signals.plex.client import PlexClient
from resonarr.state.memory_store import MemoryStore


class PruneOperatorService:
    REVIEWABLE_STATUSES = {"prune_recommendation"}

    def __init__(self, memory=None, adapter=None, prune_query_service=None, plex_client=None):
        self.memory = memory or MemoryStore()
        self.adapter = adapter or LidarrAdapter()
        self.prune_query_service = prune_query_service or PruneQueryService()
        self.plex = plex_client or PlexClient()

    def _invalidate_dashboard_snapshot(self):
        self.memory.clear_dashboard_snapshot("home_summary")
        print("[PERF][dashboard] snapshot_invalidate: source=prune_operator")

    def _find_live_reviewable_item(self, artist_name, album_name):
        reviewable = self.prune_query_service.list_reviewable_prune_candidates()
        target_artist = (artist_name or "").lower().strip()
        target_album = (album_name or "").lower().strip()

        for item in reviewable["items"]:
            if (
                (item.get("artist_name") or "").lower().strip() == target_artist
                and (item.get("album_name") or "").lower().strip() == target_album
            ):
                return item

        return None

    def list_review_queue(self):
        live = self.prune_query_service.list_reviewable_prune_candidates()

        items = []
        for item in live["items"]:
            persisted = self.memory.upsert_prune_candidate(item)

            if persisted.get("status") not in self.REVIEWABLE_STATUSES:
                continue

            items.append({
                "artist_name": persisted.get("artist_name"),
                "artist_mbid": persisted.get("artist_mbid"),
                "album_name": persisted.get("album_name"),
                "album_mbid": persisted.get("album_mbid"),
                "lidarr_album_id": persisted.get("lidarr_album_id"),
                "lidarr_artist_id": persisted.get("lidarr_artist_id"),
                "lidarr_has_files": persisted.get("lidarr_has_files"),
                "bad_ratio": persisted.get("bad_ratio"),
                "rated_tracks": persisted.get("rated_tracks"),
                "bad_tracks": persisted.get("bad_tracks"),
                "total_tracks_seen": persisted.get("total_tracks_seen"),
                "reason": persisted.get("reason"),
                "match_method": persisted.get("match_method"),
                "matched": persisted.get("matched"),
                "status": persisted.get("status"),
            })

        items.sort(
            key=lambda c: (
                -(c.get("bad_ratio") or 0),
                -(c.get("rated_tracks") or 0),
                (c.get("artist_name") or "").lower(),
                (c.get("album_name") or "").lower(),
            )
        )

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def approve_review_item(self, artist_name, album_name, rescan_plex=None):
        if rescan_plex is None:
            rescan_plex = PRUNE_RESCAN_PLEX_AFTER_EXECUTION

        item = self._find_live_reviewable_item(artist_name, album_name)
        if not item:
            return {
                "status": "failed",
                "reason": "reviewable prune candidate not found",
                "artist_name": artist_name,
                "album_name": album_name,
            }

        album_id = item.get("lidarr_album_id")
        artist_id = item.get("lidarr_artist_id")

        if album_id is None:
            return {
                "status": "failed",
                "reason": "missing Lidarr album ID",
                "artist_name": artist_name,
                "album_name": album_name,
            }

        self.memory.upsert_prune_candidate(item)
        self.memory.mark_prune_candidate_approved(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=album_id,
        )
        self._invalidate_dashboard_snapshot()

        execution = self.adapter.prune_album(
            album_id=album_id,
            artist_id=artist_id,
            prune_artist_if_empty=PRUNE_ENABLE_ARTIST_PRUNE,
        )

        if execution.get("status") != "success":
            return {
                "status": "failed",
                "reason": execution.get("reason"),
                "artist_name": artist_name,
                "album_name": album_name,
                "response_text": execution.get("response_text"),
            }

        self.memory.mark_prune_candidate_executed(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=album_id,
        )
        self._invalidate_dashboard_snapshot()

        plex_scan = {"status": "skipped", "reason": "plex rescan disabled"}
        if rescan_plex:
            plex_scan = self.plex.scan_music_library_files()

        refreshed = self.memory.get_prune_candidate(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=album_id,
        )

        return {
            "status": "success",
            "artist_name": artist_name,
            "album_name": album_name,
            "album_id": album_id,
            "candidate_status": refreshed.get("status"),
            "artist_cleanup_status": (execution.get("artist_cleanup") or {}).get("status"),
            "plex_scan_status": plex_scan.get("status"),
        }

    def reject_review_item(self, artist_name, album_name, note="manual_reject"):
        item = self._find_live_reviewable_item(artist_name, album_name)
        if not item:
            return {
                "status": "failed",
                "reason": "reviewable prune candidate not found",
                "artist_name": artist_name,
                "album_name": album_name,
            }

        self.memory.upsert_prune_candidate(item)
        self.memory.mark_prune_candidate_rejected(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=item.get("lidarr_album_id"),
            note=note,
        )
        self._invalidate_dashboard_snapshot()

        refreshed = self.memory.get_prune_candidate(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=item.get("lidarr_album_id"),
        )

        return {
            "status": "success",
            "artist_name": artist_name,
            "album_name": album_name,
            "candidate_status": refreshed.get("status"),
        }
