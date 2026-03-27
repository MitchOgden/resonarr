from dotenv import load_dotenv
load_dotenv()

from resonarr.candidates.extend import ExtendCandidateSource


def main():
    source = ExtendCandidateSource()

    print("=== Resonarr Extend Cycle ===")

    candidates = source.get_candidates()

    print(f"[INFO] Extend candidates found: {len(candidates)}")

    if not candidates:
        print("[INFO] No extend candidates available")
        return

    promotable_count = 0
    deferred_count = 0
    backoff_count = 0
    starter_album_count = 0

    for idx, candidate in enumerate(candidates, start=1):
        artist_name = candidate["artist_name"]

        print(f"[INFO] Artist: {artist_name}")
        print(f"[INFO] Best match score: {candidate['best_match_score']:.2f}")
        print(f"[INFO] Seed count: {candidate['seed_count']}")
        print(f"[INFO] Seen count: {candidate.get('seen_count', 1)}")
        print(f"[INFO] Recommendation count: {candidate.get('recommendation_count', 0)}")
        print(f"[INFO] Seed playcount: {candidate['seed_playcount']}")
        print(f"[INFO] Source seeds: {', '.join(candidate['source_seeds'])}")
        print(f"[INFO] Status: {candidate.get('status', 'new')}")
        print(f"[INFO] Is promotable: {candidate.get('is_promotable', False)}")
        print(f"[INFO] In recommendation backoff: {candidate['in_recommendation_backoff']}")

        if candidate.get("status") == "starter_album_candidate":
            starter_album_count += 1
            print("[INFO] Starter album acquisition candidate already exists")
            continue

        if candidate["in_recommendation_backoff"]:
            backoff_count += 1
            print("[INFO] Skipping extend promotion due to recommendation backoff")
            continue

        if not candidate.get("is_promotable", False):
            deferred_count += 1
            print("[INFO] Holding candidate until promotion threshold is met")
            continue

        promotable_count += 1
        print("[INFO] Candidate is promotable and ready for starter album planning")

    print("\n=== EXTEND SUMMARY ===")
    print(f"[INFO] Candidates processed: {len(candidates)}")
    print(f"[INFO] Promotable now: {promotable_count}")
    print(f"[INFO] Deferred pending more evidence: {deferred_count}")
    print(f"[INFO] In recommendation backoff: {backoff_count}")
    print(f"[INFO] Existing starter album candidates: {starter_album_count}")


if __name__ == "__main__":
    main()