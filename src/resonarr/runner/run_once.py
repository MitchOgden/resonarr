# src/resonarr/runner/run_once.py

from dotenv import load_dotenv
load_dotenv()

from resonarr.execution.lidarr.adapter import LidarrAdapter

# 👉 Replace with a real MBID for testing
TEST_ARTIST_MBID = "cc197bad-dc9c-440d-a5b5-d52ba2e14234"  # Radiohead


def main():
    adapter = LidarrAdapter()

    print("=== Resonarr Run Once ===")

    result = adapter.acquire_artist_best_release(TEST_ARTIST_MBID)

    print("\n=== RESULT ===")
    print(result)


if __name__ == "__main__":
    main()