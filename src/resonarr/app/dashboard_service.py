import time

from resonarr.app.catalog_query_service import CatalogQueryService
from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.utils.api_resilience import ExternalApiError, append_api_error_event
from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.app.deepen_service import DeepenService
from resonarr.app.prune_query_service import PruneQueryService
from resonarr.app.prune_operator_service import PruneOperatorService
from resonarr.app.deepen_query_service import DeepenQueryService
from resonarr.config.settings import DASHBOARD_SNAPSHOT_TTL_SECONDS
from resonarr.state.memory_store import MemoryStore
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
        deepen_query_service=None,
        catalog_query_service=None,
        memory=None,
    ):
        self.memory = memory or MemoryStore()
        self.extend_query_service = extend_query_service or ExtendQueryService()
        self.extend_operator_service = extend_operator_service or ExtendOperatorService()
        self.extend_promotion_service = extend_promotion_service or ExtendPromotionService()
        self.deepen_service = deepen_service or DeepenService()
        self.prune_query_service = prune_query_service or PruneQueryService()
        self.prune_operator_service = prune_operator_service or PruneOperatorService()
        self.deepen_query_service = deepen_query_service or DeepenQueryService()
        self.catalog_query_service = catalog_query_service or CatalogQueryService(
            extend_query_service=self.extend_query_service,
            extend_operator_service=self.extend_operator_service,
            extend_promotion_service=self.extend_promotion_service,
            deepen_service=self.deepen_service,
            prune_query_service=self.prune_query_service,
            prune_operator_service=self.prune_operator_service,
            deepen_query_service=self.deepen_query_service,
            memory=self.memory,
        )

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

    def _log_phase_elapsed(self, label, started_at):
        elapsed = time.perf_counter() - started_at
        print(f"[PERF][dashboard] {label}: {elapsed:.2f}s")

    def _get_cached_home_summary(self):
        snapshot = self.memory.get_dashboard_snapshot("home_summary") or {}
        payload = snapshot.get("payload")
        updated_ts = snapshot.get("updated_ts")

        if not payload or not updated_ts:
            print("[PERF][dashboard] snapshot_cache_miss: reason=missing")
            return None

        age_seconds = int(time.time()) - int(updated_ts)
        if age_seconds < 0:
            age_seconds = 0

        if age_seconds > DASHBOARD_SNAPSHOT_TTL_SECONDS:
            print(
                f"[PERF][dashboard] snapshot_cache_miss: "
                f"reason=expired age_seconds={age_seconds} "
                f"ttl_seconds={DASHBOARD_SNAPSHOT_TTL_SECONDS}"
            )
            return None

        print(
            f"[PERF][dashboard] snapshot_cache_hit: "
            f"age_seconds={age_seconds} ttl_seconds={DASHBOARD_SNAPSHOT_TTL_SECONDS}"
        )
        return payload

    def _persist_home_summary_snapshot(self, payload):
        self.memory.set_dashboard_snapshot("home_summary", payload)
        print(
            f"[PERF][dashboard] snapshot_store: "
            f"ttl_seconds={DASHBOARD_SNAPSHOT_TTL_SECONDS}"
        )

    def _persist_catalog_snapshot(self, records):
        self.catalog_query_service.persist_snapshot(records)

    def _record_dashboard_error(self, errors, section, exc):
        message = str(exc)
        errors.append({
            "section": section,
            "error_type": type(exc).__name__,
            "message": message,
        })

        append_api_error_event(
            source="dashboard",
            operation=section,
            message=message,
            exception_type=type(exc).__name__,
            context={"section": section},
        )

    def _safe_call(self, *, section, func, fallback):
        try:
            return func()
        except Exception as exc:
            raise ExternalApiError(
                source="dashboard",
                operation=section,
                message=f"{section} failed: {exc}",
                cause=exc,
            ) from exc

    def get_home_summary(self, force_refresh=False):
        total_started_at = time.perf_counter()

        if not force_refresh:
            cached_payload = self._get_cached_home_summary()
            if cached_payload is not None:
                self._log_phase_elapsed("total_get_home_summary", total_started_at)
                return cached_payload

        errors = []

        extend_summary = {
            "status": "failed",
            "total_candidates": 0,
            "counts": {},
        }
        extend_review_queue = {"status": "failed", "count": 0, "items": []}
        extend_promotable = {"status": "failed", "count": 0, "items": []}
        deepen_candidates = {"status": "failed", "count": 0, "items": []}
        deepen_review_queue = {"status": "failed", "count": 0, "items": []}
        suppressed = {"status": "failed", "count": 0, "items": []}
        prune_live = {"status": "failed", "count": 0, "items": []}
        prune_summary = {
            "status": "failed",
            "live_candidate_count": 0,
            "matched_count": 0,
            "fallback_eligible_count": 0,
            "strictly_unmatched_count": 0,
            "history_count": 0,
            "prune_recommendation_count": 0,
            "prune_approved_count": 0,
            "prune_executed_count": 0,
            "prune_rejected_count": 0,
            "items": [],
            "history_items": [],
        }
        prune_reviewable = {"status": "failed", "count": 0, "items": []}

        phase_started_at = time.perf_counter()
        try:
            extend_summary = self.extend_query_service.get_extend_status_summary()
        except Exception as exc:
            self._record_dashboard_error(errors, "extend_status_summary", exc)
        self._log_phase_elapsed("extend_status_summary", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            extend_review_queue = self.extend_operator_service.list_review_queue()
        except Exception as exc:
            self._record_dashboard_error(errors, "extend_review_queue", exc)
        self._log_phase_elapsed("extend_review_queue", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            extend_promotable = self.extend_promotion_service.list_promotable_candidates()
        except Exception as exc:
            self._record_dashboard_error(errors, "extend_promotable", exc)
        self._log_phase_elapsed("extend_promotable", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            deepen_candidates = self.deepen_service.list_candidates()
        except Exception as exc:
            self._record_dashboard_error(errors, "deepen_candidates", exc)
        self._log_phase_elapsed("deepen_candidates", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            deepen_review_queue = self.deepen_query_service.list_review_queue_from_live_items(
                deepen_candidates["items"]
            )
        except Exception as exc:
            self._record_dashboard_error(errors, "deepen_review_queue", exc)
        self._log_phase_elapsed("deepen_review_queue", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            suppressed = self.extend_query_service.list_suppressed_artists()
        except Exception as exc:
            self._record_dashboard_error(errors, "suppressed_artists", exc)
        self._log_phase_elapsed("suppressed_artists", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            prune_live = self.prune_query_service.list_prune_candidates()
        except Exception as exc:
            self._record_dashboard_error(errors, "prune_live_candidates", exc)
        self._log_phase_elapsed("prune_live_candidates", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            prune_summary = self.prune_query_service.build_prune_summary_from_live_items(
                prune_live["items"]
            )
        except Exception as exc:
            self._record_dashboard_error(errors, "prune_summary", exc)
        self._log_phase_elapsed("prune_summary", phase_started_at)

        phase_started_at = time.perf_counter()
        try:
            prune_reviewable = self.prune_query_service.list_reviewable_prune_candidates_from_live_items(
                prune_live["items"]
            )
        except Exception as exc:
            self._record_dashboard_error(errors, "prune_reviewable", exc)
        self._log_phase_elapsed("prune_reviewable", phase_started_at)

        catalog_records = []
        phase_started_at = time.perf_counter()
        try:
            catalog_records = self.catalog_query_service.build_records_from_results(
                extend_review_items=extend_review_queue.get("items", []),
                extend_promotable_items=extend_promotable.get("items", []),
                deepen_candidate_items=deepen_candidates.get("items", []),
                deepen_review_items=deepen_review_queue.get("items", []),
                prune_live_items=prune_live.get("items", []),
                prune_review_items=prune_reviewable.get("items", []),
                prune_history_items=prune_summary.get("history_items", []),
                suppressed_artist_items=suppressed.get("items", []),
            )

            if not errors:
                self._persist_catalog_snapshot(catalog_records)
            else:
                print("[PERF][catalog] snapshot_store_skipped: reason=errors_present")
        except Exception as exc:
            self._record_dashboard_error(errors, "catalog_snapshot_refresh", exc)
        self._log_phase_elapsed("catalog_snapshot_refresh", phase_started_at)

        phase_started_at = time.perf_counter()
        extend_counts = extend_summary.get("counts", {})
        deepen_items = deepen_candidates.get("items", [])

        deepen_summary = {
            "candidate_count": deepen_candidates.get("count", 0),
            "review_queue_count": deepen_review_queue.get("count", 0),
            "partial_present_count": sum(1 for item in deepen_items if item.get("partial_present")),
            "suppressed_count": sum(1 for item in deepen_items if item.get("is_suppressed")),
            "cooldown_count": sum(1 for item in deepen_items if item.get("in_cooldown")),
            "recommendation_backoff_count": sum(
                1 for item in deepen_items if item.get("in_recommendation_backoff")
            ),
        }
        self._log_phase_elapsed("build_summary_counts", phase_started_at)

        phase_started_at = time.perf_counter()
        if catalog_records:
            extend_review_records = [
                item for item in catalog_records if item.get("kind") == "extend_review"
            ]
            extend_promotable_records = [
                item for item in catalog_records if item.get("kind") == "extend_promotable"
            ]
            deepen_candidate_records = [
                item for item in catalog_records if item.get("kind") == "deepen_candidate"
            ]
            deepen_review_records = [
                item for item in catalog_records if item.get("kind") == "deepen_review"
            ]
            suppressed_artist_records = [
                item for item in catalog_records if item.get("kind") == "suppressed_artist"
            ]
            prune_review_records = [
                item for item in catalog_records if item.get("kind") == "prune_review"
            ]

            extend_review_cards = self._build_extend_review_cards(extend_review_records)
            extend_promotable_cards = self._build_extend_promotable_cards(extend_promotable_records)
            deepen_candidate_cards = self._build_deepen_candidate_cards(deepen_candidate_records)
            deepen_review_cards = self._build_deepen_candidate_cards(deepen_review_records)
            suppressed_artist_cards = self._build_suppressed_artist_cards(suppressed_artist_records)
            prune_candidate_cards = self._build_prune_candidate_cards(prune_review_records)
        else:
            extend_review_cards = self._build_extend_review_cards(extend_review_queue.get("items", []))
            extend_promotable_cards = self._build_extend_promotable_cards(extend_promotable.get("items", []))
            deepen_candidate_cards = self._build_deepen_candidate_cards(deepen_items)
            deepen_review_cards = self._build_deepen_candidate_cards(deepen_review_queue.get("items", []))
            suppressed_artist_cards = self._build_suppressed_artist_cards(suppressed.get("items", []))
            prune_candidate_cards = self._build_prune_candidate_cards(prune_reviewable.get("items", []))
        self._log_phase_elapsed("build_view_cards", phase_started_at)

        phase_started_at = time.perf_counter()
        extend_review_section_count = len(extend_review_cards)
        extend_promotable_section_count = len(extend_promotable_cards)
        deepen_candidate_section_count = len(deepen_candidate_cards)
        deepen_review_section_count = len(deepen_review_cards)
        suppressed_artist_section_count = len(suppressed_artist_cards)
        prune_review_section_count = len(prune_candidate_cards)
        self._log_phase_elapsed("build_section_counts", phase_started_at)

        phase_started_at = time.perf_counter()
        recent_reviewable = extend_review_cards[:5]
        top_promotable = extend_promotable_cards[:5]
        top_deepen = deepen_review_cards[:5]
        top_prune = prune_candidate_cards[:5]

        payload = {
            "status": "success" if not errors else "partial_success",
            "errors": errors,
            "home_summary": {
                "extend": {
                    "total_candidates": extend_summary.get("total_candidates", 0),
                    "starter_album_recommendation": extend_counts.get("starter_album_recommendation", 0),
                    "starter_album_approved": extend_counts.get("starter_album_approved", 0),
                    "starter_album_rejected": extend_counts.get("starter_album_rejected", 0),
                    "starter_album_exhausted": extend_counts.get("starter_album_exhausted", 0),
                    "recommended": extend_counts.get("recommended", 0),
                    "new": extend_counts.get("new", 0),
                    "promotable_count": extend_promotable.get("count", 0),
                    "review_queue_count": extend_review_queue.get("count", 0),
                },
                "deepen": deepen_summary,
                "prune": {
                    "live_candidate_count": prune_summary.get("live_candidate_count", 0),
                    "matched_count": prune_summary.get("matched_count", 0),
                    "fallback_eligible_count": prune_summary.get("fallback_eligible_count", 0),
                    "strictly_unmatched_count": prune_summary.get("strictly_unmatched_count", 0),
                    "history_count": prune_summary.get("history_count", 0),
                    "prune_recommendation_count": prune_summary.get("prune_recommendation_count", 0),
                    "prune_approved_count": prune_summary.get("prune_approved_count", 0),
                    "prune_executed_count": prune_summary.get("prune_executed_count", 0),
                    "prune_rejected_count": prune_summary.get("prune_rejected_count", 0),
                    "reviewable_count": prune_reviewable.get("count", 0),
                },
                "suppressed_artist_count": suppressed.get("count", 0),
            },
            "sections": {
                "extend_review_queue": {
                    "status": extend_review_queue.get("status", "failed"),
                    "count": extend_review_section_count,
                    "items": extend_review_cards,
                },
                "extend_promotable": {
                    "status": extend_promotable.get("status", "failed"),
                    "count": extend_promotable_section_count,
                    "items": extend_promotable_cards,
                },
                "deepen_candidates": {
                    "status": deepen_candidates.get("status", "failed"),
                    "count": deepen_candidate_section_count,
                    "items": deepen_candidate_cards,
                },
                "deepen_review_queue": {
                    "status": deepen_review_queue.get("status", "failed"),
                    "count": deepen_review_section_count,
                    "items": deepen_review_cards,
                },
                "suppressed_artists": {
                    "status": suppressed.get("status", "failed"),
                    "count": suppressed_artist_section_count,
                    "items": suppressed_artist_cards,
                },
                "prune_review_queue": {
                    "status": prune_reviewable.get("status", "failed"),
                    "count": prune_review_section_count,
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
        self._log_phase_elapsed("assemble_payload", phase_started_at)

        if not errors:
            self._persist_home_summary_snapshot(payload)
        else:
            print("[PERF][dashboard] snapshot_store_skipped: reason=errors_present")

        self._log_phase_elapsed("total_get_home_summary", total_started_at)
        return payload
