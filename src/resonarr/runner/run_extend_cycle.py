from dotenv import load_dotenv
load_dotenv()

from resonarr.candidates.extend import ExtendCandidateSource
from resonarr.state.memory_store import MemoryStore


def main():
    source = ExtendCandidateSource()
    memory = MemoryStore()

    print("=== Resonarr Extend Cycle ===")

    candidates = source.get_candidates()

    print(f"[INFO] Extend candidates found: {len(candidates)}")

    if not candidates:
        print("[INFO] No extend candidates available")
        return

    for idx, candidate in enumerate(candidates, start=1):
        artist_name = candidate["artist_name"]

        print(f"[INFO] Artist: {artist_name}")
        print(f"[INFO] Best match score: {candidate['best_match_score']:.2f}")
        print(f"[INFO] Seed count: {candidate['seed_count']}")
        print(f"[INFO] Seed playcount: {candidate['seed_playcount']}")
        print(f"[INFO] Source seeds: {', '.join(candidate['source_seeds'])}")
        print(f"[INFO] Status: {candidate.get('status', 'new')}")
        print(f"[INFO] In recommendation backoff: {candidate['in_recommendation_backoff']}")

        if candidate["in_recommendation_backoff"]:
            print("[INFO] Skipping extend recommendation due to recommendation backoff")
            continue

        print("[INFO] Recommendation: artist extension candidate")

        memory.set_artist_recommendation(f"extend:{artist_name.lower().strip()}")
        memory.mark_extend_candidate_recommended(artist_name)

    print("\n=== EXTEND SUMMARY ===")
    print(f"[INFO] Candidates processed: {len(candidates)}")


if __name__ == "__main__":
    main()