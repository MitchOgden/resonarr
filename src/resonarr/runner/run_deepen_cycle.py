from dotenv import load_dotenv
load_dotenv()

from resonarr.app.deepen_service import DeepenService
from resonarr.config.settings import (
    DEEPEN_MAX_EVALUATIONS_PER_RUN,
    DEEPEN_MAX_ACQUIRES_PER_RUN,
)
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("deepen-cycle")
    service = DeepenService()

    print("=== Resonarr Deepen Cycle ===")

    candidates = service.list_candidates()
    print(f"[INFO] Candidates found (post-ranking pool): {candidates['count']}")

    if not candidates["items"]:
        print("[INFO] No deepen candidates available")
        return

    result = service.run_cycle(
        limit_evaluations=DEEPEN_MAX_EVALUATIONS_PER_RUN,
        limit_acquires=DEEPEN_MAX_ACQUIRES_PER_RUN,
        dry_run=False,
    )

    for idx, item in enumerate(result["results"], start=1):
        print(f"\n=== Candidate {idx}/{result['candidate_count']} ===")
        print(f"[INFO] Artist: {item.get('artist_name')}")
        print(f"[INFO] MBID: {item.get('mbid')}")
        print(f"[INFO] Last.fm plays: {item.get('lastfm_playcount')}")
        print(f"[INFO] Partial present: {item.get('partial_present')}")
        print(f"[INFO] Eligible albums: {item.get('eligible_album_count')}")
        print(f"[INFO] Fully owned: {item.get('fully_owned')}")
        print(f"[INFO] In cooldown: {item.get('in_cooldown')}")
        print(f"[INFO] In recommendation backoff: {item.get('in_recommendation_backoff')}")
        print(f"[INFO] Is suppressed: {item.get('is_suppressed')}")

        rt = item.get("result_type")

        if rt == "skipped_prefilter_fully_owned":
            print("[INFO] Skipping candidate at pre-filter: fully owned and no partials")
            continue

        if rt == "skipped_suppressed":
            print(f"[INFO] Skipping candidate at pre-filter: {item.get('message')}")
            continue

        if rt == "skipped_recommendation_backoff":
            print(f"[INFO] Skipping candidate at pre-filter: {item.get('message')}")
            continue

        if rt == "skipped_cooldown":
            print(f"[INFO] Skipping candidate at pre-filter: {item.get('message')}")
            continue

        if rt == "stopped_acquire_cap":
            print("[INFO] Acquire cap reached — remaining candidates will not be evaluated this run")
            continue

        print("[INFO] Candidate result:")
        print({
            "status": item.get("planner_status"),
            "action": item.get("planner_action"),
            "artist": item.get("artist_name"),
            "selected_album": item.get("selected_album"),
            "reason": item.get("planner_reason"),
            "album_count": item.get("album_count"),
        })

    if result["evaluated"] >= result["limit_evaluations"] and result["candidate_count"] > result["evaluated"]:
        print("\n[INFO] Reached evaluation cap for this run")

    print("\n=== DEEPEN SUMMARY ===")
    print(f"[INFO] Evaluated: {result['evaluated']}")
    print(f"[INFO] Acquired: {result['acquired']}")
    print(f"[INFO] Recommended: {result['recommended']}")
    print(f"[INFO] No action: {result['no_action']}")
    print(f"[INFO] Skipped pre-filter: {result['skipped_prefilter']}")
    print(f"[INFO] Skipped suppressed: {result['skipped_suppressed']}")
    print(f"[INFO] Skipped recommendation backoff: {result['skipped_recommendation_backoff']}")
    print(f"[INFO] Skipped cooldown: {result['skipped_cooldown']}")


if __name__ == "__main__":
    main()