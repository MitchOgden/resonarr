from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.catalog_query_service import CatalogQueryService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("catalog-query-smoke")
    service = CatalogQueryService()

    print("=== Resonarr Catalog Query Smoke Test ===")
    print("[INFO] Collecting normalized catalog records...")

    records = service._collect_records()

    print(f"[INFO] Collected {len(records)} normalized records.")

    print("[INFO] Building all-records view...")
    all_records = service.query_records(records=records)

    print("[INFO] Building live-records view...")
    live_records = service.query_records(records=records, live_only=True)

    print("[INFO] Building historical-records view...")
    historical_records = service.query_records(records=records, historical_only=True)

    print("[INFO] Building suppressed-records view...")
    suppressed_records = service.query_records(records=records, source=["suppression"])

    print("[INFO] Building live-records sorted by score descending...")
    live_records_sorted_by_score_desc = service.query_records(
        records=records,
        live_only=True,
        sort_by="score",
        sort_direction="desc",
    )

    print("[INFO] Building historical-records sorted by event timestamp descending...")
    historical_records_sorted_by_event_ts_desc = service.query_records(
        records=records,
        historical_only=True,
        sort_by="event_ts",
        sort_direction="desc",
    )

    payload = {
        "all_records": all_records,
        "live_records": live_records,
        "historical_records": historical_records,
        "suppressed_records": suppressed_records,
        "live_records_sorted_by_score_desc": {
            "status": live_records_sorted_by_score_desc["status"],
            "count": live_records_sorted_by_score_desc["count"],
            "counts_by_kind": live_records_sorted_by_score_desc["counts_by_kind"],
            "counts_by_source": live_records_sorted_by_score_desc["counts_by_source"],
            "counts_by_status": live_records_sorted_by_score_desc["counts_by_status"],
            "top_items": live_records_sorted_by_score_desc["items"][:10],
        },
        "historical_records_sorted_by_event_ts_desc": {
            "status": historical_records_sorted_by_event_ts_desc["status"],
            "count": historical_records_sorted_by_event_ts_desc["count"],
            "counts_by_kind": historical_records_sorted_by_event_ts_desc["counts_by_kind"],
            "counts_by_source": historical_records_sorted_by_event_ts_desc["counts_by_source"],
            "counts_by_status": historical_records_sorted_by_event_ts_desc["counts_by_status"],
            "top_items": historical_records_sorted_by_event_ts_desc["items"][:10],
        },
    }

    print("[INFO] Catalog query result:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()