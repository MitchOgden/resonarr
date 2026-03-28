from resonarr.app.deepen_service import DeepenService
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.state.memory_store import MemoryStore


class DeepenOperatorService:
    REVIEWABLE_STATUSES = {"deepen_recommendation"}

    def __init__(self, deepen_service=None, adapter=None, memory=None):
        self.deepen_service = deepen_service or DeepenService()
        self.adapter = adapter or LidarrAdapter()
        self.memory = memory or MemoryStore()

    def _is_reviewable_live_candidate(self, item):
        return (
            not item.get("fully_owned")
            and not item.get("is_suppressed")
            and not item.get("in_cooldown")
            and not item.get("in_recommendation_backoff")
        )

    def _find_live_candidate(self, artist_name):
        target = (artist_name or "").lower().strip()
        live = self.deepen_service.list_candidates()

        for item in live["items"]:
            if (item.get("artist_name") or "").lower().strip() == target:
                return item

        return None

    def list_review_queue(self):
        live = self.deepen_service.list_candidates()

        items = []
        for item in live["items"]:
            if not self._is_reviewable_live_candidate(item):
                continue

            persisted = self.memory.upsert_deepen_candidate(item)

            if persisted.get("status") not in self.REVIEWABLE_STATUSES:
                continue

            items.append({
                "artist_name": persisted.get("artist_name"),
                "mbid": persisted.get("mbid"),
                "status": persisted.get("status"),
                "lastfm_playcount": persisted.get("lastfm_playcount"),
                "partial_present": persisted.get("partial_present"),
                "eligible_album_count": persisted.get("eligible_album_count"),
                "fully_owned": persisted.get("fully_owned"),
                "in_cooldown": persisted.get("in_cooldown"),
                "in_recommendation_backoff": persisted.get("in_recommendation_backoff"),
                "is_suppressed": persisted.get("is_suppressed"),
                "suppression_reason": persisted.get("suppression_reason"),
                "rank": persisted.get("rank"),
            })

        items.sort(
            key=lambda c: (
                -(c.get("partial_present") or False),
                -(c.get("lastfm_playcount") or 0),
                -(c.get("eligible_album_count") or 0),
                (c.get("artist_name") or "").lower(),
            )
        )

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def approve_review_item(self, artist_name):
        candidate = self._find_live_candidate(artist_name)
        if not candidate:
            return {
                "status": "failed",
                "reason": "candidate not found",
                "artist_name": artist_name,
            }

        mbid = candidate.get("mbid")
        if not mbid:
            return {
                "status": "failed",
                "reason": "missing MBID",
                "artist_name": artist_name,
            }

        self.memory.upsert_deepen_candidate(candidate)
        self.memory.mark_deepen_candidate_approved(mbid=mbid, artist_name=artist_name)

        result = self.adapter.acquire_artist_best_release(mbid)

        if result.get("status") != "success":
            return {
                "status": "failed",
                "reason": result.get("reason"),
                "artist_name": artist_name,
                "response_text": result.get("response_text"),
            }

        self.memory.mark_deepen_candidate_executed(mbid=mbid, artist_name=artist_name)

        refreshed = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)

        return {
            "status": "success",
            "artist_name": result.get("artist_name") or artist_name,
            "candidate_status": refreshed.get("status"),
            "planner_action": result.get("action"),
            "album_title": (result.get("selected_album") or {}).get("title"),
        }

    def reject_review_item(self, artist_name, note="manual_reject"):
        candidate = self._find_live_candidate(artist_name)
        if not candidate:
            return {
                "status": "failed",
                "reason": "candidate not found",
                "artist_name": artist_name,
            }

        mbid = candidate.get("mbid")
        if not mbid:
            return {
                "status": "failed",
                "reason": "missing MBID",
                "artist_name": artist_name,
            }

        self.memory.upsert_deepen_candidate(candidate)
        self.memory.suppress_artist(
            mbid,
            reason="operator_rejected_deepen_recommendation",
        )
        self.memory.mark_deepen_candidate_rejected(
            mbid=mbid,
            artist_name=artist_name,
            note=note,
        )

        refreshed = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)
        artist_state = self.memory.get_artist_state(mbid)

        return {
            "status": "success",
            "artist_name": artist_name,
            "candidate_status": refreshed.get("status"),
            "suppressed": artist_state.get("suppressed", False),
            "suppression_reason": artist_state.get("suppression_reason"),
        }