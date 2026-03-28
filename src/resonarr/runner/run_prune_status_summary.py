from dotenv import load_dotenv
load_dotenv()

from resonarr.app.prune_query_service import PruneQueryService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("prune-status-summary")
    service = PruneQueryService()

    print("=== Resonarr Prune Status Summary ===")

    summary = service.get_prune_summary()

    print(f"[INFO] Live candidate count: {summary['live_candidate_count']}")
    print(f"[INFO] Matched count: {summary['matched_count']}")
    print(f"[INFO] Fallback eligible count: {summary['fallback_eligible_count']}")
    print(f"[INFO] Strictly unmatched count: {summary['strictly_unmatched_count']}")
    print(f"[INFO] History count: {summary['history_count']}")
    print(f"[INFO] Recommendation count: {summary['prune_recommendation_count']}")
    print(f"[INFO] Approved count: {summary['prune_approved_count']}")
    print(f"[INFO] Executed count: {summary['prune_executed_count']}")
    print(f"[INFO] Rejected count: {summary['prune_rejected_count']}")

    reviewable = service.list_reviewable_prune_candidates()
    print(f"\n[INFO] Reviewable prune candidates: {reviewable['count']}")

    for item in reviewable["items"]:
        print(
            f"[INFO] {item.get('artist_name')} | "
            f"{item.get('album_name')} | "
            f"bad_ratio={item.get('bad_ratio'):.2f} | "
            f"match={item.get('match_method')}"
        )


if __name__ == "__main__":
    main()