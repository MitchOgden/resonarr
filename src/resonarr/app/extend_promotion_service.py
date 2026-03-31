from resonarr.candidates.extend import ExtendCandidateSource
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.config.settings import EXTEND_PROMOTION_MAX_PLANS_PER_RUN


class ExtendPromotionService:
    STAGED_STATUSES = {
        "staged_artist",
        "starter_album_exhausted",
        "starter_album_recommendation",
    }

    def __init__(self, source=None, adapter=None):
        self.source = source or ExtendCandidateSource()
        self.adapter = adapter or LidarrAdapter()
        self.memory = self.source.memory

    def _build_result_item(self, candidate):
        return {
            "artist_name": candidate["artist_name"],
            "candidate_status": candidate.get("status", "new"),
            "best_match_score": candidate.get("best_match_score"),
            "seed_count": candidate.get("seed_count"),
            "seen_count": candidate.get("seen_count", 1),
            "recommendation_count": candidate.get("recommendation_count", 0),
            "source_seeds": candidate.get("source_seeds", []),
            "in_recommendation_backoff": candidate.get("in_recommendation_backoff", False),
            "result_type": None,
            "message": None,
        }

    def _apply_existing_status_skip(self, candidate_status, item):
        if candidate_status == "starter_album_candidate":
            item["result_type"] = "skipped_existing_candidate"
            item["message"] = "Existing starter album acquisition candidate already recorded"
            return True

        if candidate_status == "starter_album_approved":
            item["result_type"] = "skipped_existing_approved"
            item["message"] = "Existing approved starter album already recorded"
            return True

        if candidate_status == "starter_album_rejected":
            item["result_type"] = "skipped_existing_rejected"
            item["message"] = "Existing rejected starter album already recorded"
            return True

        if candidate_status == "starter_album_recommendation":
            item["result_type"] = "skipped_existing_recommendation"
            item["message"] = "Existing starter album recommendation already recorded"
            return True

        return False

    def _handle_recommendation_backoff(self, candidate, candidate_status, item):
        if not candidate["in_recommendation_backoff"]:
            return {"skipped": False, "cleared": False}

        cleared = False
        if candidate_status == "promotable":
            cleared = self.memory.clear_extend_recommendation_backoff(candidate["artist_name"])
            if cleared:
                candidate["in_recommendation_backoff"] = False
                item["legacy_backoff_cleared"] = True
                item["in_recommendation_backoff"] = False

        if candidate["in_recommendation_backoff"]:
            item["result_type"] = "skipped_backoff"
            item["message"] = "Skipping starter album planning due to recommendation backoff"
            return {"skipped": True, "cleared": cleared}

        return {"skipped": False, "cleared": cleared}

    def _decorate_item_from_planner_result(self, item, result):
        item["planner_status"] = result.get("status")
        item["planner_action"] = result.get("action")
        item["planner_reason"] = result.get("reason")
        item["resolved_artist_name"] = result.get("resolved_artist_name") or result.get("artist")
        item["resolved_artist_mbid"] = result.get("artist_mbid")
        item["staged_artist_created"] = result.get("staged_artist_created", False)

    def _apply_staged_artist_side_effect(self, artist_name, result, dry_run):
        if result.get("staged_artist_created") and not dry_run:
            self.memory.mark_extend_candidate_staged_artist(
                artist_name=artist_name,
                artist_mbid=result.get("artist_mbid"),
                resolved_artist_name=result.get("resolved_artist_name") or result.get("artist"),
            )

    def _handle_recommend_only_result(self, artist_name, result, item, dry_run):
        intent = result["intent"]

        if not intent.target_album_id or not intent.target_album_title:
            item["result_type"] = "failed_missing_target_for_recommendation"
            item["message"] = "missing target album details for recommendation"
            return "failed"

        if not dry_run:
            self.memory.mark_extend_candidate_starter_album_recommendation(
                artist_name=artist_name,
                artist_mbid=result.get("artist_mbid"),
                resolved_artist_name=result.get("resolved_artist_name") or intent.artist_name,
                album_id=intent.target_album_id,
                album_title=intent.target_album_title,
                reason=intent.reason,
                score=intent.score,
            )

            self.memory.set_artist_recommendation(f"extend:{artist_name.lower().strip()}")

        item["result_type"] = "starter_album_recommendation"
        item["message"] = (
            "Starter album recommendation would be created"
            if dry_run else
            "Starter album recommendation created"
        )
        item["starter_album_id"] = intent.target_album_id
        item["starter_album_title"] = intent.target_album_title
        item["starter_album_score"] = intent.score
        item["starter_album_reason"] = intent.reason
        return "planned"

    def _handle_non_acquire_result(self, artist_name, result, item, dry_run):
        item["result_type"] = "non_acquire"

        if result.get("reason") == "no eligible albums remain after ownership filtering":
            if not dry_run:
                self.memory.mark_extend_candidate_starter_album_exhausted(
                    artist_name=artist_name,
                    artist_mbid=result.get("artist_mbid"),
                    resolved_artist_name=result.get("resolved_artist_name") or result.get("artist"),
                    reason=result.get("reason"),
                )

            item["result_type"] = "starter_album_exhausted"
            item["message"] = (
                "Would record starter album exhaustion for staged/promoted candidate"
                if dry_run else
                "Recorded starter album exhaustion for staged/promoted candidate"
            )
        else:
            item["message"] = result.get("reason")

        return "skipped_non_acquire"

    def _handle_acquire_result(self, artist_name, result, item, dry_run):
        intent = result["intent"]

        if not intent.target_album_id or not intent.target_album_title:
            item["result_type"] = "failed_missing_target"
            item["message"] = "missing target album details"
            return "failed"

        if not dry_run:
            self.memory.mark_extend_candidate_starter_album_candidate(
                artist_name=artist_name,
                artist_mbid=result.get("artist_mbid"),
                resolved_artist_name=result.get("resolved_artist_name") or intent.artist_name,
                album_id=intent.target_album_id,
                album_title=intent.target_album_title,
                reason=intent.reason,
                score=intent.score,
            )

            self.memory.set_artist_recommendation(f"extend:{artist_name.lower().strip()}")

        item["result_type"] = "starter_album_candidate"
        item["message"] = (
            "Starter album acquisition candidate would be created"
            if dry_run else
            "Starter album acquisition candidate created"
        )
        item["starter_album_id"] = intent.target_album_id
        item["starter_album_title"] = intent.target_album_title
        item["starter_album_score"] = intent.score
        item["starter_album_reason"] = intent.reason
        return "planned"

    def _list_promotable_candidates(self):
        candidates = self.source.get_persisted_candidates()
        return [
            candidate
            for candidate in candidates
            if candidate.get("is_promotable", False)
        ]

    def _build_promotable_candidate_view(self, candidate):
        return {
            "artist_name": candidate.get("artist_name"),
            "status": candidate.get("status", "new"),
            "resolved_artist_name": candidate.get("resolved_artist_name"),
            "resolved_artist_mbid": candidate.get("resolved_artist_mbid"),
            "best_match_score": candidate.get("best_match_score"),
            "seed_count": candidate.get("seed_count"),
            "seen_count": candidate.get("seen_count", 1),
            "recommendation_count": candidate.get("recommendation_count", 0),
            "source_seeds": candidate.get("source_seeds", []),
            "in_recommendation_backoff": candidate.get("in_recommendation_backoff", False),
            "is_promotable": candidate.get("is_promotable", False),
            "starter_album_id": candidate.get("starter_album_id"),
            "starter_album_title": candidate.get("starter_album_title"),
            "starter_album_score": candidate.get("starter_album_score"),
            "starter_album_reason": candidate.get("starter_album_reason"),
        }

    def list_promotable_candidates(self):
        promotable = self._list_promotable_candidates()
        items = [self._build_promotable_candidate_view(candidate) for candidate in promotable]

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def run_promotion_cycle(self, limit=None, dry_run=False):
        if limit is None:
            limit = EXTEND_PROMOTION_MAX_PLANS_PER_RUN

        promotable_candidates = self._list_promotable_candidates()

        results = []
        planned = 0
        skipped_backoff = 0
        skipped_existing = 0
        skipped_non_acquire = 0
        failed = 0

        for candidate in promotable_candidates:
            if planned >= limit:
                break

            artist_name = candidate["artist_name"]
            candidate_status = candidate.get("status", "new")

            item = self._build_result_item(candidate)

            if self._apply_existing_status_skip(candidate_status, item):
                skipped_existing += 1
                results.append(item)
                continue

            backoff_result = self._handle_recommendation_backoff(candidate, candidate_status, item)
            if backoff_result["skipped"]:
                skipped_backoff += 1
                results.append(item)
                continue

            try:
                result = self.adapter.plan_extended_artist_best_release(
                    artist_name,
                    is_staged_artist=(candidate_status in self.STAGED_STATUSES),
                )
            except Exception as exc:
                failed += 1
                item["result_type"] = "failed_exception"
                item["message"] = str(exc)
                results.append(item)
                continue

            self._decorate_item_from_planner_result(item, result)
            self._apply_staged_artist_side_effect(artist_name, result, dry_run)

            if result.get("action") == "RECOMMEND_ONLY":
                outcome = self._handle_recommend_only_result(
                    artist_name=artist_name,
                    result=result,
                    item=item,
                    dry_run=dry_run,
                )

                if outcome == "failed":
                    failed += 1
                elif outcome == "planned":
                    planned += 1

                results.append(item)
                continue

            if result.get("action") != "ACQUIRE_ARTIST":
                outcome = self._handle_non_acquire_result(
                    artist_name=artist_name,
                    result=result,
                    item=item,
                    dry_run=dry_run,
                )

                if outcome == "skipped_non_acquire":
                    skipped_non_acquire += 1

                results.append(item)
                continue

            outcome = self._handle_acquire_result(
                artist_name=artist_name,
                result=result,
                item=item,
                dry_run=dry_run,
            )

            if outcome == "failed":
                failed += 1
            elif outcome == "planned":
                planned += 1

            results.append(item)

        return {
            "status": "success",
            "promotable_count": len(promotable_candidates),
            "planned_count": planned,
            "skipped_existing": skipped_existing,
            "skipped_backoff": skipped_backoff,
            "skipped_non_acquire": skipped_non_acquire,
            "failed": failed,
            "limit": limit,
            "dry_run": dry_run,
            "results": results,
        }