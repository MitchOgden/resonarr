from dotenv import load_dotenv
load_dotenv()

import sys

from resonarr.state.memory_store import MemoryStore
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-approve-extend")
    memory = MemoryStore()
    adapter = LidarrAdapter()

    if len(sys.argv) < 2:
        print("Usage: python -m resonarr.runner.run_operator_approve_extend \"Artist Name\"")
        return

    artist_name = " ".join(sys.argv[1:]).strip()

    print("=== Resonarr Operator Approve Extend Recommendation ===")
    print(f"[INFO] Target artist: {artist_name}")

    candidate = memory.find_extend_candidate_by_artist_name(artist_name)
    if not candidate:
        print("[INFO] Candidate not found")
        return

    if candidate.get("status") not in {"starter_album_recommendation", "starter_album_candidate"}:
        print(f"[INFO] Candidate status not reviewable: {candidate.get('status')}")
        return

    artist_mbid = candidate.get("resolved_artist_mbid")
    album_id = candidate.get("starter_album_id")

    if not artist_mbid or not album_id:
        print("[INFO] Missing MBID or starter album ID")
        return

    result = adapter.approve_starter_album_recommendation(artist_mbid, album_id)

    if result.get("status") != "success":
        print(f"[INFO] Approval failed: {result.get('reason')}")
        if result.get("response_text"):
            print(f"[INFO] Response: {result.get('response_text')}")
        return

    memory.mark_extend_candidate_approved(artist_name)

    print("[INFO] Starter album recommendation approved")
    print(f"[INFO] Artist: {result.get('artist_name')}")
    print(f"[INFO] Album: {result.get('album_title')}")


if __name__ == "__main__":
    main()