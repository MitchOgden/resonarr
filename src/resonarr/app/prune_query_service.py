from resonarr.app.prune_service import PruneService
from resonarr.state.memory_store import MemoryStore


class PruneQueryService:
    NON_REVIEWABLE_FINAL_STATUSES = {"prune_executed", "prune_rejected"}

    def __init__(self, prune_service=None, memory=None):
        self.prune_service = prune_service or PruneService()
        self.memory = memory or MemoryStore()

    def _merge_with_state(self, item):
        persisted = self.memory.get_prune_candidate(
            artist_name=item.get("artist_name"),
            album_name=item.get("album_name"),
            album_mbid=item.get("album_mbid"),
            lidarr_album_id=item.get("lidarr_album_id"),
        ) or {}

        merged = dict(item)

        if persisted.get("status"):
            merged["status"] = persisted.get("status")
        else:
            merged["status"] = "prune_recommendation"

        for field in (
            "prune_approved_ts",
            "prune_approved_note",
            "prune_executed_ts",
            "prune_executed_note",
            "prune_rejected_ts",
            "prune_rejected_note",
            "first_seen_ts",
            "last_seen_ts",
        ):
            if field in persisted:
                merged[field] = persisted.get(field)

        return merged

    def list_prune_candidates(self, limit=None):
        result = self.prune_service.list_prune_candidates(limit=limit)
        items = [self._merge_with_state(item) for item in result["items"]]

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def list_prune_history(self):
        items = self.memory.list_prune_candidates()

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def get_prune_summary(self, limit=None):
        live_result = self.list_prune_candidates(limit=limit)
        live_items = live_result["items"]

        history_result = self.list_prune_history()
        history_items = history_result["items"]

        matched_count = sum(1 for item in live_items if item.get("matched"))
        fallback_eligible_count = sum(
            1
            for item in live_items
            if (
                not item.get("matched")
                and item.get("name_match_found")
                and item.get("name_match_available_but_disabled")
            )
        )
        strictly_unmatched_count = sum(
            1
            for item in live_items
            if (
                not item.get("matched")
                and not (
                    item.get("name_match_found")
                    and item.get("name_match_available_but_disabled")
                )
            )
        )

        recommendation_count = sum(
            1 for item in history_items if item.get("status") == "prune_recommendation"
        )
        approved_count = sum(
            1 for item in history_items if item.get("status") == "prune_approved"
        )
        executed_count = sum(
            1 for item in history_items if item.get("status") == "prune_executed"
        )
        rejected_count = sum(
            1 for item in history_items if item.get("status") == "prune_rejected"
        )

        return {
            "status": "success",
            "live_candidate_count": len(live_items),
            "matched_count": matched_count,
            "fallback_eligible_count": fallback_eligible_count,
            "strictly_unmatched_count": strictly_unmatched_count,
            "history_count": len(history_items),
            "prune_recommendation_count": recommendation_count,
            "prune_approved_count": approved_count,
            "prune_executed_count": executed_count,
            "prune_rejected_count": rejected_count,
            "items": live_items,
            "history_items": history_items,
        }

    def list_reviewable_prune_candidates(self, limit=None):
        result = self.list_prune_candidates(limit=limit)

        items = [
            item
            for item in result["items"]
            if (
                item.get("matched")
                and item.get("status") not in self.NON_REVIEWABLE_FINAL_STATUSES
            )
        ]

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }