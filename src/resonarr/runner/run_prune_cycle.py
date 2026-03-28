from dotenv import load_dotenv
load_dotenv()

from resonarr.app.prune_service import PruneService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("prune-cycle")
    service = PruneService()

    print("=== Resonarr Prune Cycle ===")

    result = service.get_prune_summary()

    print(f"[INFO] Prune candidates found: {result['candidate_count']}")
    print(f"[INFO] Matched to Lidarr: {result['matched_count']}")
    print(f"[INFO] Unmatched in Lidarr: {result['unmatched_count']}")

    if not result["items"]:
        print("[INFO] No prune candidates")
        return

    for idx, item in enumerate(result["items"], start=1):
        print(f"\n=== Prune Candidate {idx}/{result['candidate_count']} ===")
        print(f"[INFO] Artist: {item.get('artist_name')}")
        print(f"[INFO] Album: {item.get('album_name')}")
        print(f"[INFO] Rated tracks: {item.get('rated_tracks')}")
        print(f"[INFO] Bad tracks: {item.get('bad_tracks')}")
        print(f"[INFO] Total tracks seen: {item.get('total_tracks_seen')}")
        print(f"[INFO] Bad ratio: {item.get('bad_ratio'):.2f}")
        print(f"[INFO] Reason: {item.get('reason')}")
        print(f"[INFO] Match method: {item.get('match_method')}")
        print(f"[INFO] Matched: {item.get('matched')}")
        print(f"[INFO] Lidarr album id: {item.get('lidarr_album_id')}")
        print(f"[INFO] Lidarr artist id: {item.get('lidarr_artist_id')}")
        print(f"[INFO] Lidarr has files: {item.get('lidarr_has_files')}")
        print(f"[INFO] Proposed action: {item.get('action')}")


if __name__ == "__main__":
    main()