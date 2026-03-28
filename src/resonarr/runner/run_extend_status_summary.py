from dotenv import load_dotenv
load_dotenv()

from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("extend-status-summary")
    service = ExtendQueryService()

    print("=== Resonarr Extend Status Summary ===")

    summary = service.get_extend_status_summary()
    counts = summary["counts"]

    print(f"[INFO] Total extend candidates: {summary['total_candidates']}")

    for status, count in counts.items():
        print(f"[INFO] {status}: {count}")

    print("\n[INFO] Reviewable recommendations:")
    reviewable = service.list_candidates_by_status(
        {"starter_album_recommendation", "starter_album_candidate"}
    )
    print(f"[INFO] Count: {reviewable['count']}")

    for item in reviewable["items"]:
        print(
            f"[INFO] {item.get('artist_name')} | {item.get('status')} | "
            f"{item.get('starter_album_title')} | score={item.get('starter_album_score')}"
        )

    print("\n[INFO] Suppressed artists:")
    suppressed = service.list_suppressed_artists()
    print(f"[INFO] Count: {suppressed['count']}")

    for item in suppressed["items"]:
        print(
            f"[INFO] {item.get('artist_key')} | "
            f"reason={item.get('suppression_reason')} | "
            f"ts={item.get('suppressed_ts')}"
        )


if __name__ == "__main__":
    main()