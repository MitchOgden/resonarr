from dotenv import load_dotenv
load_dotenv()

from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.config.settings import EXTEND_PROMOTION_MAX_PLANS_PER_RUN
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("extend-promotion-cycle")
    service = ExtendPromotionService()

    print("=== Resonarr Extend Promotion Cycle ===")

    promotable = service.list_promotable_candidates()
    print(f"[INFO] Promotable candidates found: {promotable['count']}")

    if not promotable["items"]:
        print("[INFO] No promotable extend candidates available")
        return

    result = service.run_promotion_cycle(limit=EXTEND_PROMOTION_MAX_PLANS_PER_RUN)

    for idx, item in enumerate(result["results"], start=1):
        print(f"\n=== Promotable Candidate {idx}/{result['promotable_count']} ===")
        print(f"[INFO] Artist: {item.get('artist_name')}")
        print(f"[INFO] Best match score: {item.get('best_match_score', 0):.2f}")
        print(f"[INFO] Seed count: {item.get('seed_count')}")
        print(f"[INFO] Seen count: {item.get('seen_count')}")
        print(f"[INFO] Recommendation count: {item.get('recommendation_count')}")
        print(f"[INFO] Source seeds: {', '.join(item.get('source_seeds', []))}")
        print(f"[INFO] Status: {item.get('candidate_status')}")
        print(f"[INFO] In recommendation backoff: {item.get('in_recommendation_backoff')}")

        if item.get("candidate_status") == "staged_artist":
            print("[INFO] Evaluating existing staged artist in Lidarr")

        if item.get("candidate_status") == "starter_album_exhausted":
            print("[INFO] Re-evaluating previously exhausted candidate under current staged policy")

        if item.get("legacy_backoff_cleared"):
            print("[INFO] Cleared legacy extend recommendation backoff for promotable candidate")

        if item.get("staged_artist_created"):
            print("[INFO] Extend candidate intentionally staged as unmonitored artist in Lidarr")
        elif item.get("candidate_status") in {
            "staged_artist",
            "starter_album_exhausted",
            "starter_album_recommendation",
        }:
            print("[INFO] Re-using existing staged artist in Lidarr")

        if item.get("result_type") in {
            "skipped_existing_candidate",
            "skipped_existing_approved",
            "skipped_existing_rejected",
            "skipped_existing_recommendation",
            "skipped_backoff",
        }:
            print(f"[INFO] {item.get('message')}")
            continue

        if item.get("result_type") == "failed_exception":
            print(f"[INFO] Planning failed with exception: {item.get('message')}")
            continue

        if item.get("result_type") == "failed_missing_target_for_recommendation":
            print(f"[INFO] Planning failed: {item.get('message')}")
            continue

        if item.get("result_type") == "failed_missing_target":
            print(f"[INFO] Planning failed: {item.get('message')}")
            continue

        if item.get("result_type") == "starter_album_recommendation":
            score_text = (
                f"{item.get('starter_album_score'):.2f}"
                if item.get("starter_album_score") is not None
                else "None"
            )
            print("[INFO] Starter album recommendation created")
            print(f"[INFO] Resolved artist: {item.get('resolved_artist_name')}")
            print(f"[INFO] MBID: {item.get('resolved_artist_mbid')}")
            print(f"[INFO] Album: {item.get('starter_album_title')}")
            print(f"[INFO] Reason: {item.get('starter_album_reason')}")
            print(f"[INFO] Score: {score_text}")
            continue

        if item.get("result_type") == "starter_album_candidate":
            score_text = (
                f"{item.get('starter_album_score'):.2f}"
                if item.get("starter_album_score") is not None
                else "None"
            )
            print("[INFO] Starter album acquisition candidate created")
            print(f"[INFO] Resolved artist: {item.get('resolved_artist_name')}")
            print(f"[INFO] MBID: {item.get('resolved_artist_mbid')}")
            print(f"[INFO] Album: {item.get('starter_album_title')}")
            print(f"[INFO] Reason: {item.get('starter_album_reason')}")
            print(f"[INFO] Score: {score_text}")
            continue

        if item.get("result_type") == "starter_album_exhausted":
            print("[INFO] No starter album acquisition candidate emitted: no eligible albums remain after ownership filtering")
            print("[INFO] Recorded starter album exhaustion for staged/promoted candidate")
            continue

        if item.get("result_type") == "non_acquire":
            print(f"[INFO] No starter album acquisition candidate emitted: {item.get('planner_reason')}")
            continue

    if result["planned_count"] >= result["limit"] and result["promotable_count"] > result["planned_count"]:
        print("\n[INFO] Reached starter album planning cap for this run")

    print("\n=== EXTEND PROMOTION SUMMARY ===")
    print(f"[INFO] Starter album outputs created: {result['planned_count']}")
    print(f"[INFO] Skipped existing starter album candidate: {result['skipped_existing']}")
    print(f"[INFO] Skipped recommendation backoff: {result['skipped_backoff']}")
    print(f"[INFO] Skipped below acquire threshold: {result['skipped_non_acquire']}")
    print(f"[INFO] Failed planning attempts: {result['failed']}")


if __name__ == "__main__":
    main()