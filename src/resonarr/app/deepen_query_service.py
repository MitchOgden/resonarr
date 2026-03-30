from resonarr.state.memory_store import MemoryStore


class DeepenQueryService:
    REVIEWABLE_STATUSES = {"deepen_recommendation"}

    def __init__(self, memory=None):
        self.memory = memory or MemoryStore()

    def _is_reviewable_live_candidate(self, item):
        return (
            not item.get("fully_owned")
            and not item.get("is_suppressed")
            and not item.get("in_cooldown")
            and not item.get("in_recommendation_backoff")
        )

    def _candidate_view(self, item):
        return {
            "artist_name": item.get("artist_name"),
            "mbid": item.get("mbid"),
            "status": item.get("status"),
            "lastfm_playcount": item.get("lastfm_playcount"),
            "partial_present": item.get("partial_present"),
            "eligible_album_count": item.get("eligible_album_count"),
            "fully_owned": item.get("fully_owned"),
            "in_cooldown": item.get("in_cooldown"),
            "in_recommendation_backoff": item.get("in_recommendation_backoff"),
            "is_suppressed": item.get("is_suppressed"),
            "suppression_reason": item.get("suppression_reason"),
            "rank": item.get("rank"),
        }

    def sync_reviewable_candidates(self):
        live = self.deepen_service.list_candidates()

        synced = []
        for item in live["items"]:
            if not self._is_reviewable_live_candidate(item):
                continue

            persisted = self.memory.upsert_deepen_candidate(item)
            synced.append(self._candidate_view(persisted))

        synced.sort(
            key=lambda c: (
                -(c.get("partial_present") or False),
                -(c.get("lastfm_playcount") or 0),
                -(c.get("eligible_album_count") or 0),
                (c.get("artist_name") or "").lower(),
            )
        )

        return {
            "status": "success",
            "count": len(synced),
            "items": synced,
        }

    def list_review_queue(self, sync_live=True):
        if sync_live:
            self.sync_reviewable_candidates()

        items = [
            self._candidate_view(candidate)
            for candidate in self.memory.list_deepen_candidates_by_status(self.REVIEWABLE_STATUSES)
        ]

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

    def get_review_candidate(self, mbid=None, artist_name=None, sync_live=True):
        if sync_live:
            self.sync_reviewable_candidates()

        candidate = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)
        if not candidate:
            return {}

        return candidate