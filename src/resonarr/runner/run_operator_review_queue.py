from dotenv import load_dotenv
load_dotenv()

from resonarr.state.memory_store import MemoryStore
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-review-queue")
    memory = MemoryStore()

    print("=== Resonarr Operator Review Queue ===")

    reviewable = memory.list_extend_candidates_by_status(
        {"starter_album_recommendation", "starter_album_candidate"}
    )

    reviewable.sort(
        key=lambda c: (
            0 if c.get("status") == "starter_album_candidate" else 1,
            -(c.get("starter_album_score") or 0),
            c.get("artist_name", "").lower(),
        )
    )

    print(f"[INFO] Reviewable outputs found: {len(reviewable)}")

    if not reviewable:
        print("[INFO] No reviewable starter album outputs")
        return

    for idx, candidate in enumerate(reviewable, start=1):
        print(f"\n=== Review Item {idx}/{len(reviewable)} ===")
        print(f"[INFO] Artist: {candidate.get('artist_name')}")
        print(f"[INFO] Status: {candidate.get('status')}")
        print(f"[INFO] Resolved artist: {candidate.get('resolved_artist_name')}")
        print(f"[INFO] MBID: {candidate.get('resolved_artist_mbid')}")
        print(f"[INFO] Album: {candidate.get('starter_album_title')}")
        print(f"[INFO] Album ID: {candidate.get('starter_album_id')}")
        print(f"[INFO] Score: {candidate.get('starter_album_score')}")
        print(f"[INFO] Reason: {candidate.get('starter_album_reason')}")


if __name__ == "__main__":
    main()