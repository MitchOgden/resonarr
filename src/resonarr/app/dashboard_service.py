from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.app.deepen_service import DeepenService
from resonarr.app.prune_query_service import PruneQueryService
from resonarr.app.prune_operator_service import PruneOperatorService
from resonarr.app.view_models import (
    build_extend_review_card,
    build_extend_promotable_card,
    build_deepen_candidate_card,
    build_suppressed_artist_card,
    build_prune_candidate_card,
)


class DashboardService:
    def __init__(
        self,
        extend_query_service=None,
        extend_operator_service=None,
        extend_promotion_service=None,
        deepen_service=None,
        prune_query_service=None,
        prune_operator_service=None,
    ):
        self.extend_query_service = extend_query_service or ExtendQueryService()
        self.extend_operator_service = extend_operator_service or ExtendOperatorService()
        self.extend_promotion_service = extend_promotion_service or ExtendPromotionService()
        self.deepen_service = deepen_service or DeepenService()
        self.prune_query_service = prune_query_service or PruneQueryService()
        self.prune_operator_service = prune_operator_service or PruneOperatorService()

    def _build_extend_review_cards(self, items):
        return [build_extend_review_card(item) for item in items]

    def _build_extend_promotable_cards(self, items):
        return [build_extend_promotable_card(item) for item in items]

    def _build_deepen_candidate_cards(self, items):
        return [build_deepen_candidate_card(item) for item in items]

    def _build_suppressed_artist_cards(self, items):
        return [build_suppressed_artist_card(item) for item in items]
    
    def _build_prune_candidate_cards(self, items):
        return [build_prune_candidate_card(item) for item in items]    

    def get_home_summary(self):
        extend_summary = self.extend_query_service.get_extend_status_summary()
        extend_review_queue = self.extend_operator_service.list_review_queue()
        extend_promotable = self.extend_promotion_service.list_promotable_candidates()
        deepen_candidates = self.deepen_service.list_candidates()
        suppressed = self.extend_query_service.list_suppressed_artists()
        prune_summary = self.prune_query_service.get_prune_summary()
        prune_reviewable = self.prune_operator_service.list_review_queue()

        extend_counts = extend_summary["counts"]
        deepen_items = deepen_candidates["items"]

        deepen_summary = {
            "candidate_count": deepen_candidates["count"],
            "partial_present_count": sum(1 for item in deepen_items if item.get("partial_present")),
            "suppressed_count": sum(1 for item in deepen_items if item.get("is_suppressed")),
            "cooldown_count": sum(1 for item in deepen_items if item.get("in_cooldown")),
            "recommendation_backoff_count": sum(
                1 for item in deepen_items if item.get("in_recommendation_backoff")
            ),
        }

        extend_review_cards = self._build_extend_review_cards(extend_review_queue["items"])
        extend_promotable_cards = self._build_extend_promotable_cards(extend_promotable["items"])
        deepen_candidate_cards = self._build_deepen_candidate_cards(deepen_items)
        suppressed_artist_cards = self._build_suppressed_artist_cards(suppressed["items"])
        prune_candidate_cards = self._build_prune_candidate_cards(prune_reviewable["items"])

        recent_reviewable = extend_review_cards[:5]
        top_promotable = extend_promotable_cards[:5]
        top_deepen = deepen_candidate_cards[:5]
        top_prune = prune_candidate_cards[:5]

        return {
            "status": "success",
            "home_summary": {
                "extend": {
                    "total_candidates": extend_summary["total_candidates"],
                    "starter_album_recommendation": extend_counts.get("starter_album_recommendation", 0),
                    "starter_album_approved": extend_counts.get("starter_album_approved", 0),
                    "starter_album_rejected": extend_counts.get("starter_album_rejected", 0),
                    "starter_album_exhausted": extend_counts.get("starter_album_exhausted", 0),
                    "recommended": extend_counts.get("recommended", 0),
                    "new": extend_counts.get("new", 0),
                    "promotable_count": extend_promotable["count"],
                    "review_queue_count": extend_review_queue["count"],
                },
                "deepen": deepen_summary,
                "prune": {
                    "candidate_count": prune_summary["candidate_count"],
                    "matched_count": prune_summary["matched_count"],
                    "fallback_eligible_count": prune_summary["fallback_eligible_count"],
                    "strictly_unmatched_count": prune_summary["strictly_unmatched_count"],
                    "reviewable_count": prune_reviewable["count"],
                },
                "suppressed_artist_count": suppressed["count"],
            },
            "sections": {
                "extend_review_queue": {
                    "status": extend_review_queue["status"],
                    "count": extend_review_queue["count"],
                    "items": extend_review_cards,
                },
                "extend_promotable": {
                    "status": extend_promotable["status"],
                    "count": extend_promotable["count"],
                    "items": extend_promotable_cards,
                },
                "deepen_candidates": {
                    "status": deepen_candidates["status"],
                    "count": deepen_candidates["count"],
                    "items": deepen_candidate_cards,
                },
                "suppressed_artists": {
                    "status": suppressed["status"],
                    "count": suppressed["count"],
                    "items": suppressed_artist_cards,
                },
                "prune_review_queue": {
                    "status": prune_reviewable["status"],
                    "count": prune_reviewable["count"],
                    "items": prune_candidate_cards,
                },
            },
            "highlights": {
                "recent_reviewable": recent_reviewable,
                "top_promotable": top_promotable,
                "top_deepen_candidates": top_deepen,
                "top_prune_candidates": top_prune,
            },
        }