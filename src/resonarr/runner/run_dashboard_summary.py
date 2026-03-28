from dotenv import load_dotenv
load_dotenv()

from resonarr.app.dashboard_service import DashboardService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("dashboard-summary")
    service = DashboardService()

    print("=== Resonarr Dashboard Summary ===")

    payload = service.get_home_summary()
    summary = payload["home_summary"]

    extend = summary["extend"]
    deepen = summary["deepen"]
    prune = summary["prune"]    

    print("[INFO] Extend overview:")
    print(f"[INFO] Total candidates: {extend['total_candidates']}")
    print(f"[INFO] Review queue count: {extend['review_queue_count']}")
    print(f"[INFO] Promotable count: {extend['promotable_count']}")
    print(f"[INFO] Recommendation count: {extend['starter_album_recommendation']}")
    print(f"[INFO] Approved count: {extend['starter_album_approved']}")
    print(f"[INFO] Rejected count: {extend['starter_album_rejected']}")
    print(f"[INFO] Exhausted count: {extend['starter_album_exhausted']}")
    print(f"[INFO] Recommended count: {extend['recommended']}")
    print(f"[INFO] New count: {extend['new']}")


    print("\n[INFO] Deepen overview:")
    print(f"[INFO] Candidate count: {deepen['candidate_count']}")
    print(f"[INFO] Partial present count: {deepen['partial_present_count']}")
    print(f"[INFO] Suppressed count: {deepen['suppressed_count']}")
    print(f"[INFO] Cooldown count: {deepen['cooldown_count']}")
    print(f"[INFO] Recommendation backoff count: {deepen['recommendation_backoff_count']}")


    print("\n[INFO] Prune overview:")
    print(f"[INFO] Live candidate count: {prune['live_candidate_count']}")
    print(f"[INFO] Matched count: {prune['matched_count']}")
    print(f"[INFO] Fallback eligible count: {prune['fallback_eligible_count']}")
    print(f"[INFO] Strictly unmatched count: {prune['strictly_unmatched_count']}")
    print(f"[INFO] History count: {prune['history_count']}")
    print(f"[INFO] Recommendation count: {prune['prune_recommendation_count']}")
    print(f"[INFO] Approved count: {prune['prune_approved_count']}")
    print(f"[INFO] Executed count: {prune['prune_executed_count']}")
    print(f"[INFO] Rejected count: {prune['prune_rejected_count']}")
    print(f"[INFO] Reviewable count: {prune['reviewable_count']}") 

    print(f"\n[INFO] Suppressed artist count: {summary['suppressed_artist_count']}")

    print("\n[INFO] Review queue highlights:")
    for item in payload["highlights"]["recent_reviewable"]:
        print(
            f"[INFO] {item.get('artist_name')} | "
            f"{item.get('status')} | "
            f"{item.get('album_title')} | "
            f"score={item.get('score')}"
        )

    print("\n[INFO] Promotable highlights:")
    for item in payload["highlights"]["top_promotable"]:
        print(
            f"[INFO] {item.get('artist_name')} | "
            f"{item.get('status')} | "
            f"score={item.get('score')}"
        )

    print("\n[INFO] Deepen candidate highlights:")
    for item in payload["highlights"]["top_deepen_candidates"]:
        print(
            f"[INFO] {item.get('artist_name')} | "
            f"plays={item.get('lastfm_playcount')} | "
            f"partial_present={item.get('partial_present')} | "
            f"eligible_albums={item.get('eligible_album_count')}"
        )

    print("\n[INFO] Prune candidate highlights:")
    for item in payload["highlights"]["top_prune_candidates"]:
        print(
            f"[INFO] {item.get('artist_name')} | "
            f"{item.get('album_title')} | "
            f"bad_ratio={item.get('score'):.2f} | "
            f"match={item.get('match_method')}"
        )    

if __name__ == "__main__":
    main()