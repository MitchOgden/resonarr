from resonarr.app.prune_service import PruneService


class PruneQueryService:
    def __init__(self, prune_service=None):
        self.prune_service = prune_service or PruneService()

    def list_prune_candidates(self, limit=None):
        return self.prune_service.list_prune_candidates(limit=limit)

    def get_prune_summary(self, limit=None):
        result = self.prune_service.list_prune_candidates(limit=limit)
        items = result["items"]

        matched_count = sum(1 for item in items if item.get("matched"))
        fallback_eligible_count = sum(
            1
            for item in items
            if (
                not item.get("matched")
                and item.get("name_match_found")
                and item.get("name_match_available_but_disabled")
            )
        )
        strictly_unmatched_count = sum(
            1
            for item in items
            if (
                not item.get("matched")
                and not (
                    item.get("name_match_found")
                    and item.get("name_match_available_but_disabled")
                )
            )
        )

        return {
            "status": "success",
            "candidate_count": len(items),
            "matched_count": matched_count,
            "fallback_eligible_count": fallback_eligible_count,
            "strictly_unmatched_count": strictly_unmatched_count,
            "items": items,
        }

    def list_reviewable_prune_candidates(self, limit=None):
        result = self.prune_service.list_prune_candidates(limit=limit)

        items = [
            item
            for item in result["items"]
            if item.get("matched")
        ]

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }