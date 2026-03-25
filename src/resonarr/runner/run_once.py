# src/resonarr/runner/run_once.py

from dotenv import load_dotenv
load_dotenv()

from resonarr.execution.lidarr.adapter import LidarrAdapter

# 👉 Replace with a real MBID for testing
TEST_ARTIST_MBID = "bf600e2b-dc2d-4839-a1be-6ebef4087cd0"  # 311


def main():
    adapter = LidarrAdapter()

    # --- TEST: simulate negative feedback ---
    # Uncomment to test suppression
    # adapter.memory.suppress_artist(TEST_ARTIST_MBID, reason="test_dislike")
    # adapter.memory.unsuppress_artist(TEST_ARTIST_MBID)

    # --- TEST: simulate positive affinity ---
    # Uncomment to test deepening
    adapter.memory.boost_artist_affinity(TEST_ARTIST_MBID, multiplier=2.0, reason="test_like")

    print("=== Resonarr Run Once ===")

    result = adapter.acquire_artist_best_release(TEST_ARTIST_MBID)

    print("\n=== RESULT ===")
    print(result)


if __name__ == "__main__":
    main()