from resonarr.app.deepen_query_service import DeepenQueryService
from resonarr.app.deepen_service import DeepenService
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.state.memory_store import MemoryStore


class DeepenOperatorService:
    REVIEWABLE_STATUSES = {"deepen_recommendation"}

    def __init__(self, deepen_service=None, deepen_query_service=None, adapter=None, memory=None):
        self.deepen_service = deepen_service or DeepenService()
        self.memory = memory or MemoryStore()
        self.deepen_query_service = deepen_query_service or DeepenQueryService(
            deepen_service=self.deepen_service,
            memory=self.memory,
        )
        self.adapter = adapter or LidarrAdapter()

    def _invalidate_dashboard_snapshot(self):
        self.memory.clear_dashboard_snapshot("home_summary")
        self.memory.clear_catalog_snapshot("catalog_records")
        print(
            "[PERF][read_models] snapshot_invalidate: "
            "source=deepen_operator targets=home_summary,catalog_records"
        )


    def _find_live_candidate(self, artist_name=None, mbid=None):
        target_name = (artist_name or "").lower().strip()
        target_mbid = (mbid or "").lower().strip()

        live = self.deepen_service.list_candidates()

        for item in live["items"]:
            item_mbid = (item.get("mbid") or "").lower().strip()
            item_name = (item.get("artist_name") or "").lower().strip()

            if target_mbid and item_mbid == target_mbid:
                return item

            if target_name and item_name == target_name:
                return item

        return None

    def list_review_queue(self, sync_live=True):
        return self.deepen_query_service.list_review_queue(sync_live=sync_live)

    def approve_review_item(self, artist_name=None, mbid=None):
        candidate = self.deepen_query_service.get_review_candidate(
            mbid=mbid,
            artist_name=artist_name,
            sync_live=True,
        )
        if not candidate:
            return {
                "status": "failed",
                "reason": "candidate not found",
                "artist_name": artist_name,
                "mbid": mbid,
            }

        if candidate.get("status") not in self.REVIEWABLE_STATUSES:
            return {
                "status": "failed",
                "reason": f"candidate status not reviewable: {candidate.get('status')}",
                "artist_name": candidate.get("artist_name") or artist_name,
                "mbid": candidate.get("mbid") or mbid,
                "candidate_status": candidate.get("status"),
            }

        mbid = candidate.get("mbid")
        artist_name = candidate.get("artist_name") or artist_name

        if not mbid:
            return {
                "status": "failed",
                "reason": "missing MBID",
                "artist_name": artist_name,
            }

        live_candidate = self._find_live_candidate(artist_name=artist_name, mbid=mbid)
        if not live_candidate:
            return {
                "status": "failed",
                "reason": "live candidate not found",
                "artist_name": artist_name,
                "mbid": mbid,
            }

        self.memory.mark_deepen_candidate_approved(mbid=mbid, artist_name=artist_name)
        self._invalidate_dashboard_snapshot()

        result = self.adapter.acquire_artist_best_release(mbid)

        if result.get("status") != "success":
            return {
                "status": "failed",
                "reason": result.get("reason"),
                "artist_name": artist_name,
                "response_text": result.get("response_text"),
            }

        self.memory.mark_deepen_candidate_executed(mbid=mbid, artist_name=artist_name)
        self._invalidate_dashboard_snapshot()

        refreshed = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)

        return {
            "status": "success",
            "artist_name": result.get("artist_name") or artist_name,
            "candidate_status": refreshed.get("status"),
            "planner_action": result.get("action"),
            "album_title": (result.get("selected_album") or {}).get("title"),
        }

    def reject_review_item(self, artist_name=None, mbid=None, note="manual_reject"):
        candidate = self.deepen_query_service.get_review_candidate(
            mbid=mbid,
            artist_name=artist_name,
            sync_live=True,
        )
        if not candidate:
            return {
                "status": "failed",
                "reason": "candidate not found",
                "artist_name": artist_name,
                "mbid": mbid,
            }

        if candidate.get("status") not in self.REVIEWABLE_STATUSES:
            return {
                "status": "failed",
                "reason": f"candidate status not reviewable: {candidate.get('status')}",
                "artist_name": candidate.get("artist_name") or artist_name,
                "mbid": candidate.get("mbid") or mbid,
                "candidate_status": candidate.get("status"),
            }

        mbid = candidate.get("mbid")
        artist_name = candidate.get("artist_name") or artist_name

        if not mbid:
            return {
                "status": "failed",
                "reason": "missing MBID",
                "artist_name": artist_name,
            }

        self.memory.suppress_artist(
            mbid,
            reason="operator_rejected_deepen_recommendation",
            artist_name=artist_name,
        )
        self.memory.mark_deepen_candidate_rejected(
            mbid=mbid,
            artist_name=artist_name,
            note=note,
        )
        self._invalidate_dashboard_snapshot()

        refreshed = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)
        artist_state = self.memory.get_artist_state(mbid)

        return {
            "status": "success",
            "artist_name": artist_name,
            "candidate_status": refreshed.get("status"),
            "suppressed": artist_state.get("suppressed", False),
            "suppression_reason": artist_state.get("suppression_reason"),
        }
