from dotenv import load_dotenv
load_dotenv()

from resonarr.candidates.deepen import DeepenCandidateSource
from resonarr.execution.lidarr.adapter import LidarrAdapter


def main():
    source = DeepenCandidateSource()
    adapter = LidarrAdapter()

    print("=== Resonarr Deepen Cycle ===")

    candidates = source.get_candidates()

    print(f"[INFO] Candidates found: {len(candidates)}")

    if not candidates:
        print("[INFO] No deepen candidates available")
        return

    for idx, candidate in enumerate(candidates, start=1):
        artist_name = candidate["artist_name"]
        mbid = candidate["mbid"]
        plays = candidate["lastfm_playcount"]

        print(f"\n=== Candidate {idx}/{len(candidates)} ===")
        print(f"[INFO] Artist: {artist_name}")
        print(f"[INFO] MBID: {mbid}")
        print(f"[INFO] Last.fm plays: {plays}")

        result = adapter.acquire_artist_best_release(mbid)

        print("[INFO] Candidate result:")
        print(result)


if __name__ == "__main__":
    main()