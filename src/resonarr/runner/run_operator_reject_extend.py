from dotenv import load_dotenv
load_dotenv()

import sys

from resonarr.state.memory_store import MemoryStore
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-reject-extend")
    memory = MemoryStore()
    adapter = LidarrAdapter()

    if len(sys.argv) < 2:
        print("Usage: python -m resonarr.runner.run_operator_reject_extend \"Artist Name\"")
        return

    artist_name = " ".join(sys.argv[1:]).strip()

    print("=== Resonarr Operator Reject Extend Recommendation ===")
    print(f"[INFO] Target artist: {artist_name}")

    candidate = memory.find_extend_candidate_by_artist_name(artist_name)
    if not candidate:
        print("[INFO] Candidate not found")
        return

    artist_mbid = candidate.get("resolved_artist_mbid")
    if not artist_mbid:
        print("[INFO] Missing resolved artist MBID")
        return

    memory.suppress_artist(artist_mbid, reason="operator_rejected_extend_recommendation")
    removal = adapter.remove_staged_artist(artist_mbid)
    memory.mark_extend_candidate_rejected(artist_name)

    print("[INFO] Starter album recommendation rejected")
    print(f"[INFO] Artist: {candidate.get('resolved_artist_name') or candidate.get('artist_name')}")
    print(f"[INFO] Lidarr removal status: {removal.get('status')}")
    if removal.get("reason"):
        print(f"[INFO] Lidarr removal reason: {removal.get('reason')}")


if __name__ == "__main__":
    main()