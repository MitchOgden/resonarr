from dotenv import load_dotenv
load_dotenv()

from resonarr.candidates.extend import ExtendCandidateSource
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.config.settings import EXTEND_PROMOTION_MAX_PLANS_PER_RUN
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("extend-promotion-cycle")
    source = ExtendCandidateSource()
    adapter = LidarrAdapter()
    memory = source.memory

    print("=== Resonarr Extend Promotion Cycle ===")

    candidates = source.get_persisted_candidates()
    promotable_candidates = [
        c for c in candidates
        if c.get("is_promotable", False)
    ]

    print(f"[INFO] Promotable candidates found: {len(promotable_candidates)}")

    if not promotable_candidates:
        print("[INFO] No promotable extend candidates available")
        return

    planned = 0
    skipped_backoff = 0
    skipped_existing = 0
    skipped_non_acquire = 0
    failed = 0

    for idx, candidate in enumerate(promotable_candidates, start=1):
        if planned >= EXTEND_PROMOTION_MAX_PLANS_PER_RUN:
            print("\n[INFO] Reached starter album planning cap for this run")
            break

        artist_name = candidate["artist_name"]

        print(f"\n=== Promotable Candidate {idx}/{len(promotable_candidates)} ===")
        print(f"[INFO] Artist: {artist_name}")
        print(f"[INFO] Best match score: {candidate['best_match_score']:.2f}")
        print(f"[INFO] Seed count: {candidate['seed_count']}")
        print(f"[INFO] Seen count: {candidate.get('seen_count', 1)}")
        print(f"[INFO] Recommendation count: {candidate.get('recommendation_count', 0)}")
        print(f"[INFO] Source seeds: {', '.join(candidate['source_seeds'])}")
        print(f"[INFO] Status: {candidate.get('status', 'new')}")
        print(f"[INFO] In recommendation backoff: {candidate['in_recommendation_backoff']}")

        if candidate.get("status") == "starter_album_candidate":
            skipped_existing += 1
            print("[INFO] Existing starter album acquisition candidate already recorded")
            continue

        if candidate["in_recommendation_backoff"]:
            if candidate.get("status") == "promotable":
                cleared = memory.clear_extend_recommendation_backoff(artist_name)
                if cleared:
                    print("[INFO] Cleared legacy extend recommendation backoff for promotable candidate")
                    candidate["in_recommendation_backoff"] = False

            if candidate["in_recommendation_backoff"]:
                skipped_backoff += 1
                print("[INFO] Skipping starter album planning due to recommendation backoff")
                continue

        try:
            result = adapter.plan_extended_artist_best_release(artist_name)
        except Exception as exc:
            failed += 1
            print(f"[INFO] Planning failed with exception: {exc}")
            continue

        if result.get("status") != "success":
            failed += 1
            print(f"[INFO] Planning failed: {result.get('reason')}")
            continue

        if result.get("action") != "ACQUIRE_ARTIST":
            skipped_non_acquire += 1
            print(f"[INFO] No starter album acquisition candidate emitted: {result.get('reason')}")
            continue

        intent = result["intent"]

        if not intent.target_album_id or not intent.target_album_title:
            failed += 1
            print("[INFO] Planning failed: missing target album details")
            continue

        score_text = f"{intent.score:.2f}" if intent.score is not None else "None"

        print("[INFO] Starter album acquisition candidate created")
        print(f"[INFO] Resolved artist: {result.get('resolved_artist_name') or intent.artist_name}")
        print(f"[INFO] MBID: {result.get('artist_mbid')}")
        print(f"[INFO] Album: {intent.target_album_title}")
        print(f"[INFO] Reason: {intent.reason}")
        print(f"[INFO] Score: {score_text}")

        memory.mark_extend_candidate_starter_album_candidate(
            artist_name=artist_name,
            artist_mbid=result.get("artist_mbid"),
            resolved_artist_name=result.get("resolved_artist_name") or intent.artist_name,
            album_id=intent.target_album_id,
            album_title=intent.target_album_title,
            reason=intent.reason,
            score=intent.score,
        )

        memory.set_artist_recommendation(f"extend:{artist_name.lower().strip()}")
        planned += 1

    print("\n=== EXTEND PROMOTION SUMMARY ===")
    print(f"[INFO] Starter album candidates created: {planned}")
    print(f"[INFO] Skipped existing starter album candidate: {skipped_existing}")
    print(f"[INFO] Skipped recommendation backoff: {skipped_backoff}")
    print(f"[INFO] Skipped below acquire threshold: {skipped_non_acquire}")
    print(f"[INFO] Failed planning attempts: {failed}")


if __name__ == "__main__":
    main()