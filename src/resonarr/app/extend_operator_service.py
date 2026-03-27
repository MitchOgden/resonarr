from resonarr.state.memory_store import MemoryStore
from resonarr.execution.lidarr.adapter import LidarrAdapter


class ExtendOperatorService:
    REVIEWABLE_STATUSES = {"starter_album_recommendation", "starter_album_candidate"}

    def __init__(self, memory=None, adapter=None):
        self.memory = memory or MemoryStore()
        self.adapter = adapter or LidarrAdapter()

    def list_review_queue(self):
        reviewable = self.memory.list_extend_candidates_by_status(self.REVIEWABLE_STATUSES)

        reviewable.sort(
            key=lambda c: (
                0 if c.get("status") == "starter_album_candidate" else 1,
                -(c.get("starter_album_score") or 0),
                c.get("artist_name", "").lower(),
            )
        )

        items = []
        for candidate in reviewable:
            items.append({
                "artist_name": candidate.get("artist_name"),
                "status": candidate.get("status"),
                "resolved_artist_name": candidate.get("resolved_artist_name"),
                "resolved_artist_mbid": candidate.get("resolved_artist_mbid"),
                "starter_album_id": candidate.get("starter_album_id"),
                "starter_album_title": candidate.get("starter_album_title"),
                "starter_album_score": candidate.get("starter_album_score"),
                "starter_album_reason": candidate.get("starter_album_reason"),
            })

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def approve_review_item(self, artist_name):
        candidate = self.memory.find_extend_candidate_by_artist_name(artist_name)
        if not candidate:
            return {
                "status": "failed",
                "reason": "candidate not found",
                "artist_name": artist_name,
            }

        if candidate.get("status") not in self.REVIEWABLE_STATUSES:
            return {
                "status": "failed",
                "reason": f"candidate status not reviewable: {candidate.get('status')}",
                "artist_name": artist_name,
                "candidate_status": candidate.get("status"),
            }

        artist_mbid = candidate.get("resolved_artist_mbid")
        album_id = candidate.get("starter_album_id")

        if not artist_mbid or not album_id:
            return {
                "status": "failed",
                "reason": "missing MBID or starter album ID",
                "artist_name": artist_name,
                "candidate_status": candidate.get("status"),
            }

        result = self.adapter.approve_starter_album_recommendation(artist_mbid, album_id)

        if result.get("status") != "success":
            return {
                "status": "failed",
                "reason": result.get("reason"),
                "artist_name": artist_name,
                "response_text": result.get("response_text"),
            }

        self.memory.mark_extend_candidate_approved(artist_name)

        refreshed = self.memory.find_extend_candidate_by_artist_name(artist_name) or {}

        return {
            "status": "success",
            "artist_name": result.get("artist_name"),
            "album_title": result.get("album_title"),
            "album_id": result.get("album_id"),
            "candidate_status": refreshed.get("status"),
        }

    def reject_review_item(self, artist_name, remove_from_lidarr=True):
        candidate = self.memory.find_extend_candidate_by_artist_name(artist_name)
        if not candidate:
            return {
                "status": "failed",
                "reason": "candidate not found",
                "artist_name": artist_name,
            }

        artist_mbid = candidate.get("resolved_artist_mbid")
        if not artist_mbid:
            return {
                "status": "failed",
                "reason": "missing resolved artist MBID",
                "artist_name": artist_name,
            }

        self.memory.suppress_artist(
            artist_mbid,
            reason="operator_rejected_extend_recommendation"
        )

        removal = {"status": "skipped", "reason": "remove_from_lidarr disabled"}
        if remove_from_lidarr:
            removal = self.adapter.remove_staged_artist(artist_mbid)

        self.memory.mark_extend_candidate_rejected(artist_name)

        refreshed = self.memory.find_extend_candidate_by_artist_name(artist_name) or {}
        artist_state = self.memory.get_artist_state(artist_mbid)

        return {
            "status": "success",
            "artist_name": candidate.get("resolved_artist_name") or candidate.get("artist_name"),
            "candidate_status": refreshed.get("status"),
            "suppressed": artist_state.get("suppressed", False),
            "removal_status": removal.get("status"),
            "removal_reason": removal.get("reason"),
        }