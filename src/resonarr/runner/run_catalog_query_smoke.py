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

    payload = {
        "all_records": all_records,
        "live_records": live_records,
        "historical_records": historical_records,
        "suppressed_records": suppressed_records,
    }

    print("[INFO] Catalog query result:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()