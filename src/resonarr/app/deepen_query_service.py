from resonarr.app.deepen_service import DeepenService
from resonarr.state.memory_store import MemoryStore


class DeepenQueryService:
    REVIEWABLE_STATUSES = {"deepen_recommendation"}

    def __init__(self, deepen_service=None, memory=None):
        self.deepen_service = deepen_service or DeepenService()
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

    def _candidate_lookup_key(self, item):
        mbid = (item.get("mbid") or "").strip().lower()
        if mbid:
            return ("mbid", mbid)

        artist_name = (item.get("artist_name") or "").strip().lower()
        if artist_name:
            return ("name", artist_name)

        return None

    def _sync_reviewable_candidates_from_live_items(self, live_items):
        synced = []
        reviewable_keys = set()

        for item in live_items:
            if not self._is_reviewable_live_candidate(item):
                continue

            persisted = self.memory.upsert_deepen_candidate(item)
            synced.append(self._candidate_view(persisted))

            lookup_key = self._candidate_lookup_key(persisted)
            if lookup_key:
                reviewable_keys.add(lookup_key)

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
            "reviewable_keys": reviewable_keys,
        }

    def sync_reviewable_candidates(self):
        live = self.deepen_service.list_candidates()
        return self._sync_reviewable_candidates_from_live_items(live["items"])

    def _build_review_queue_from_reviewable_keys(self, reviewable_keys=None):
        items = []
        for candidate in self.memory.list_deepen_candidates_by_status(self.REVIEWABLE_STATUSES):
            if reviewable_keys is not None:
                lookup_key = self._candidate_lookup_key(candidate)
                if lookup_key not in reviewable_keys:
                    continue

            items.append(self._candidate_view(candidate))

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

    def list_review_queue(self, sync_live=True):
        reviewable_keys = None

        if sync_live:
            sync_result = self.sync_reviewable_candidates()
            reviewable_keys = sync_result.get("reviewable_keys", set())

        return self._build_review_queue_from_reviewable_keys(reviewable_keys=reviewable_keys)

    def list_review_queue_from_live_items(self, live_items):
        sync_result = self._sync_reviewable_candidates_from_live_items(live_items)
        return self._build_review_queue_from_reviewable_keys(
            reviewable_keys=sync_result.get("reviewable_keys", set())
        )

    def get_review_candidate(self, mbid=None, artist_name=None, sync_live=True):
        if sync_live:
            self.sync_reviewable_candidates()

        candidate = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)
        if not candidate:
            return {}

        return candidate