from resonarr.candidates.deepen import DeepenCandidateSource
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.config.settings import (
    DEEPEN_MAX_EVALUATIONS_PER_RUN,
    DEEPEN_MAX_ACQUIRES_PER_RUN,
    ARTIST_COOLDOWN_HOURS,
    RECOMMENDATION_BACKOFF_HOURS,
)


class DeepenService:
    def __init__(self, source=None, adapter=None):
        self.source = source or DeepenCandidateSource()
        self.adapter = adapter or LidarrAdapter()
        self.memory = self.adapter.memory

    def list_candidates(self):
        candidates = self.source.get_candidates()

        items = []
        for candidate in candidates:
            items.append({
                "artist_name": candidate.get("artist_name"),
                "mbid": candidate.get("mbid"),
                "lastfm_playcount": candidate.get("lastfm_playcount"),
                "partial_present": candidate.get("partial_present"),
                "eligible_album_count": candidate.get("eligible_album_count"),
                "fully_owned": candidate.get("fully_owned"),
                "total_album_count": candidate.get("total_album_count"),
                "fully_owned_album_count": candidate.get("fully_owned_album_count"),
                "in_cooldown": candidate.get("in_cooldown"),
                "cooldown_remaining_seconds": candidate.get("cooldown_remaining_seconds"),
                "in_recommendation_backoff": candidate.get("in_recommendation_backoff"),
                "is_suppressed": candidate.get("is_suppressed"),
                "suppression_reason": candidate.get("suppression_reason"),
                "rank": candidate.get("rank"),
            })

        return {
            "status": "success",
            "count": len(items),
            "items": items,
        }

    def run_cycle(
        self,
        limit_evaluations=None,
        limit_acquires=None,
        dry_run=False,
    ):
        if limit_evaluations is None:
            limit_evaluations = DEEPEN_MAX_EVALUATIONS_PER_RUN
        if limit_acquires is None:
            limit_acquires = DEEPEN_MAX_ACQUIRES_PER_RUN

        candidates = self.source.get_candidates()

        results = []
        evaluations = 0
        acquires = 0
        skipped_prefilter = 0
        skipped_cooldown = 0
        skipped_suppressed = 0
        skipped_recommendation_backoff = 0
        recommended = 0
        no_action = 0

        for candidate in candidates:
            if evaluations >= limit_evaluations:
                break

            artist_name = candidate["artist_name"]
            mbid = candidate["mbid"]
            plays = candidate["lastfm_playcount"]

            item = {
                "artist_name": artist_name,
                "mbid": mbid,
                "lastfm_playcount": plays,
                "partial_present": candidate["partial_present"],
                "eligible_album_count": candidate["eligible_album_count"],
                "fully_owned": candidate["fully_owned"],
                "in_cooldown": candidate["in_cooldown"],
                "in_recommendation_backoff": candidate["in_recommendation_backoff"],
                "is_suppressed": candidate["is_suppressed"],
                "suppression_reason": candidate.get("suppression_reason"),
                "result_type": None,
                "message": None,
            }

            if candidate["fully_owned"] and not candidate["partial_present"]:
                skipped_prefilter += 1
                item["result_type"] = "skipped_prefilter_fully_owned"
                item["message"] = "fully owned and no partials"
                results.append(item)
                continue

            if candidate["is_suppressed"]:
                skipped_suppressed += 1
                item["result_type"] = "skipped_suppressed"
                item["message"] = f"suppressed ({candidate.get('suppression_reason') or 'unknown'})"
                results.append(item)
                continue

            if candidate["in_recommendation_backoff"]:
                skipped_recommendation_backoff += 1
                item["result_type"] = "skipped_recommendation_backoff"
                item["message"] = f"recommendation backoff ({RECOMMENDATION_BACKOFF_HOURS}h)"
                results.append(item)
                continue

            artist_state = self.adapter.memory.get_artist_state(mbid)
            last_action_ts = artist_state.get("last_action_ts")
            cooldown_seconds = ARTIST_COOLDOWN_HOURS * 3600

            if last_action_ts:
                import time
                elapsed = time.time() - last_action_ts
                if elapsed < cooldown_seconds:
                    skipped_cooldown += 1
                    item["result_type"] = "skipped_cooldown"
                    item["message"] = (
                        f"cooldown ({int(elapsed)}s elapsed, {ARTIST_COOLDOWN_HOURS}h cooldown)"
                    )
                    results.append(item)
                    continue

            if acquires >= limit_acquires:
                item["result_type"] = "stopped_acquire_cap"
                item["message"] = "acquire cap reached"
                results.append(item)
                break

            evaluations += 1

            if dry_run:
                result = self.adapter.plan_artist_best_release(mbid)
            else:
                result = self.adapter.acquire_artist_best_release(mbid)

            action = result.get("action")
            item["planner_status"] = result.get("status")
            item["planner_action"] = action
            item["planner_reason"] = result.get("reason")
            item["selected_album"] = result.get("selected_album")
            item["album_count"] = result.get("album_count")

            if action == "ACQUIRE_ARTIST":
                acquires += 1
                item["result_type"] = "acquire_artist"
                item["message"] = (
                    "would acquire artist best release" if dry_run
                    else "acquired artist best release"
                )
            elif action == "RECOMMEND_ONLY":
                recommended += 1
                item["result_type"] = "recommend_only"
                item["message"] = "recommendation only"
            elif action == "NO_ACTION":
                no_action += 1
                item["result_type"] = "no_action"
                item["message"] = "no action"

            results.append(item)

        return {
            "status": "success",
            "candidate_count": len(candidates),
            "evaluated": evaluations,
            "acquired": acquires,
            "recommended": recommended,
            "no_action": no_action,
            "skipped_prefilter": skipped_prefilter,
            "skipped_suppressed": skipped_suppressed,
            "skipped_recommendation_backoff": skipped_recommendation_backoff,
            "skipped_cooldown": skipped_cooldown,
            "limit_evaluations": limit_evaluations,
            "limit_acquires": limit_acquires,
            "dry_run": dry_run,
            "results": results,
        }