from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.app.deepen_service import DeepenService


class DashboardService:
    def __init__(
        self,
        extend_query_service=None,
        extend_operator_service=None,
        extend_promotion_service=None,
        deepen_service=None,
    ):
        self.extend_query_service = extend_query_service or ExtendQueryService()
        self.extend_operator_service = extend_operator_service or ExtendOperatorService()
        self.extend_promotion_service = extend_promotion_service or ExtendPromotionService()
        self.deepen_service = deepen_service or DeepenService()

    def get_home_summary(self):
        extend_summary = self.extend_query_service.get_extend_status_summary()
        extend_review_queue = self.extend_operator_service.list_review_queue()
        extend_promotable = self.extend_promotion_service.list_promotable_candidates()
        deepen_candidates = self.deepen_service.list_candidates()
        suppressed = self.extend_query_service.list_suppressed_artists()

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

        recent_reviewable = extend_review_queue["items"][:5]
        top_promotable = extend_promotable["items"][:5]
        top_deepen = deepen_items[:5]

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
                "suppressed_artist_count": suppressed["count"],
            },
            "sections": {
                "extend_review_queue": extend_review_queue,
                "extend_promotable": extend_promotable,
                "deepen_candidates": deepen_candidates,
                "suppressed_artists": suppressed,
            },
            "highlights": {
                "recent_reviewable": recent_reviewable,
                "top_promotable": top_promotable,
                "top_deepen_candidates": top_deepen,
            },
        }