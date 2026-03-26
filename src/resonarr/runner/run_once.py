# src/resonarr/runner/run_once.py

from dotenv import load_dotenv
load_dotenv()

from resonarr.execution.lidarr.adapter import LidarrAdapter

# 👉 Replace with a real MBID for testing
TEST_ARTIST_MBID = "12398bf3-1b99-47b7-930c-f3956773f35a"


def main():
    adapter = LidarrAdapter()

    # --- OPTIONAL TEST HOOKS ---
    # adapter.memory.suppress_artist(TEST_ARTIST_MBID, reason="test_dislike")
    # adapter.memory.unsuppress_artist(TEST_ARTIST_MBID)
    # adapter.memory.boost_artist_affinity(TEST_ARTIST_MBID, multiplier=2.0, reason="test_like")

    print("=== Resonarr Run Once ===")

    result = adapter.acquire_artist_best_release(TEST_ARTIST_MBID)

    print("\n=== RESULT ===")
    print(result)


if __name__ == "__main__":
    main()