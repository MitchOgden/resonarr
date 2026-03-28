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

    def list_promotable_candidates(self):
        candidates = self.source.get_persisted_candidates()
        promotable = [
            c for c in candidates
            if c.get("is_promotable", False)
        ]

        items = []
        for candidate in promotable:
            items.append({
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
            })

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def run_promotion_cycle(self, limit=None, dry_run=False):
        if limit is None:
            limit = EXTEND_PROMOTION_MAX_PLANS_PER_RUN

        candidates = self.source.get_persisted_candidates()
        promotable_candidates = [
            c for c in candidates
            if c.get("is_promotable", False)
        ]

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

            item = {
                "artist_name": artist_name,
                "candidate_status": candidate_status,
                "best_match_score": candidate.get("best_match_score"),
                "seed_count": candidate.get("seed_count"),
                "seen_count": candidate.get("seen_count", 1),
                "recommendation_count": candidate.get("recommendation_count", 0),
                "source_seeds": candidate.get("source_seeds", []),
                "in_recommendation_backoff": candidate.get("in_recommendation_backoff", False),
                "result_type": None,
                "message": None,
            }

            if candidate_status == "starter_album_candidate":
                skipped_existing += 1
                item["result_type"] = "skipped_existing_candidate"
                item["message"] = "Existing starter album acquisition candidate already recorded"
                results.append(item)
                continue

            if candidate_status == "starter_album_approved":
                skipped_existing += 1
                item["result_type"] = "skipped_existing_approved"
                item["message"] = "Existing approved starter album already recorded"
                results.append(item)
                continue

            if candidate_status == "starter_album_rejected":
                skipped_existing += 1
                item["result_type"] = "skipped_existing_rejected"
                item["message"] = "Existing rejected starter album already recorded"
                results.append(item)
                continue

            if candidate_status == "starter_album_recommendation":
                skipped_existing += 1
                item["result_type"] = "skipped_existing_recommendation"
                item["message"] = "Existing starter album recommendation already recorded"
                results.append(item)
                continue

            if candidate["in_recommendation_backoff"]:
                if candidate_status == "promotable":
                    cleared = self.memory.clear_extend_recommendation_backoff(artist_name)
                    if cleared:
                        candidate["in_recommendation_backoff"] = False
                        item["legacy_backoff_cleared"] = True

                if candidate["in_recommendation_backoff"]:
                    skipped_backoff += 1
                    item["result_type"] = "skipped_backoff"
                    item["message"] = "Skipping starter album planning due to recommendation backoff"
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

            item["planner_status"] = result.get("status")
            item["planner_action"] = result.get("action")
            item["planner_reason"] = result.get("reason")
            item["resolved_artist_name"] = result.get("resolved_artist_name") or result.get("artist")
            item["resolved_artist_mbid"] = result.get("artist_mbid")
            item["staged_artist_created"] = result.get("staged_artist_created", False)

            if result.get("staged_artist_created") and not dry_run:
                self.memory.mark_extend_candidate_staged_artist(
                    artist_name=artist_name,
                    artist_mbid=result.get("artist_mbid"),
                    resolved_artist_name=result.get("resolved_artist_name") or result.get("artist"),
                )

            if result.get("action") == "RECOMMEND_ONLY":
                intent = result["intent"]

                if not intent.target_album_id or not intent.target_album_title:
                    failed += 1
                    item["result_type"] = "failed_missing_target_for_recommendation"
                    item["message"] = "missing target album details for recommendation"
                    results.append(item)
                    continue

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

                planned += 1
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
                results.append(item)
                continue

            if result.get("action") != "ACQUIRE_ARTIST":
                skipped_non_acquire += 1
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

                results.append(item)
                continue

            intent = result["intent"]

            if not intent.target_album_id or not intent.target_album_title:
                failed += 1
                item["result_type"] = "failed_missing_target"
                item["message"] = "missing target album details"
                results.append(item)
                continue

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

            planned += 1
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