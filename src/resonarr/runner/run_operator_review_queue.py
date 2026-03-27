from dotenv import load_dotenv
load_dotenv()

from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-review-queue")
    service = ExtendOperatorService()

    print("=== Resonarr Operator Review Queue ===")

    result = service.list_review_queue()

    print(f"[INFO] Reviewable outputs found: {result['count']}")

    if not result["items"]:
        print("[INFO] No reviewable starter album outputs")
        return

    for idx, item in enumerate(result["items"], start=1):
        print(f"\n=== Review Item {idx}/{len(result['items'])} ===")
        print(f"[INFO] Artist: {item.get('artist_name')}")
        print(f"[INFO] Status: {item.get('status')}")
        print(f"[INFO] Resolved artist: {item.get('resolved_artist_name')}")
        print(f"[INFO] MBID: {item.get('resolved_artist_mbid')}")
        print(f"[INFO] Album: {item.get('starter_album_title')}")
        print(f"[INFO] Album ID: {item.get('starter_album_id')}")
        print(f"[INFO] Score: {item.get('starter_album_score')}")
        print(f"[INFO] Reason: {item.get('starter_album_reason')}")


if __name__ == "__main__":
    main()