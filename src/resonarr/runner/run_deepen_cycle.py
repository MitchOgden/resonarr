from dotenv import load_dotenv
load_dotenv()

from resonarr.candidates.deepen import DeepenCandidateSource
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.config.settings import (
    DEEPEN_MAX_EVALUATIONS_PER_RUN,
    DEEPEN_MAX_ACQUIRES_PER_RUN,
    ARTIST_COOLDOWN_HOURS
)
import time


def main():
    source = DeepenCandidateSource()
    adapter = LidarrAdapter()

    print("=== Resonarr Deepen Cycle ===")

    candidates = source.get_candidates()

    print(f"[INFO] Candidates found: {len(candidates)}")

    if not candidates:
        print("[INFO] No deepen candidates available")
        return

    evaluations = 0
    acquires = 0
    skipped_prefilter = 0
    skipped_cooldown = 0
    recommended = 0
    no_action = 0

    for idx, candidate in enumerate(candidates, start=1):
        if evaluations >= DEEPEN_MAX_EVALUATIONS_PER_RUN:
            print("\n[INFO] Reached evaluation cap for this run")
            break

        artist_name = candidate["artist_name"]
        mbid = candidate["mbid"]
        plays = candidate["lastfm_playcount"]

        print(f"\n=== Candidate {idx}/{len(candidates)} ===")
        print(f"[INFO] Artist: {artist_name}")
        print(f"[INFO] MBID: {mbid}")
        print(f"[INFO] Last.fm plays: {plays}")
        print(f"[INFO] Partial present: {candidate['partial_present']}")
        print(f"[INFO] Eligible albums: {candidate['eligible_album_count']}")
        print(f"[INFO] Fully owned: {candidate['fully_owned']}")

        if candidate["fully_owned"] and not candidate["partial_present"]:
            print("[INFO] Skipping candidate at pre-filter: fully owned and no partials")
            skipped_prefilter += 1
            continue

        artist_state = adapter.memory.get_artist_state(mbid)
        last_action_ts = artist_state.get("last_action_ts")
        cooldown_seconds = ARTIST_COOLDOWN_HOURS * 3600

        if last_action_ts:
            elapsed = time.time() - last_action_ts
            if elapsed < cooldown_seconds:
                print(
                    f"[INFO] Skipping candidate at pre-filter: cooldown "
                    f"({int(elapsed)}s elapsed, {ARTIST_COOLDOWN_HOURS}h cooldown)"
                )
                skipped_cooldown += 1
                continue

        if acquires >= DEEPEN_MAX_ACQUIRES_PER_RUN:
            print("[INFO] Acquire cap reached — remaining candidates will not be evaluated this run")
            break

        evaluations += 1

        result = adapter.acquire_artist_best_release(mbid)

        print("[INFO] Candidate result:")
        print(result)

        action = result.get("action")

        if action == "ACQUIRE_ARTIST":
            acquires += 1
        elif action == "RECOMMEND_ONLY":
            recommended += 1
        elif action == "NO_ACTION":
            no_action += 1

    print("\n=== DEEPEN SUMMARY ===")
    print(f"[INFO] Evaluated: {evaluations}")
    print(f"[INFO] Acquired: {acquires}")
    print(f"[INFO] Recommended: {recommended}")
    print(f"[INFO] No action: {no_action}")
    print(f"[INFO] Skipped pre-filter: {skipped_prefilter}")
    print(f"[INFO] Skipped cooldown: {skipped_cooldown}")


if __name__ == "__main__":
    main()