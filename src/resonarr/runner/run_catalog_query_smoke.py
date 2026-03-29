from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.catalog_query_service import CatalogQueryService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("catalog-query-smoke")
    service = CatalogQueryService()

    print("=== Resonarr Catalog Query Smoke Test ===")

    payload = {
        "all_records": service.query_records(),
        "live_records": service.query_records(live_only=True),
        "historical_records": service.query_records(historical_only=True),
        "suppressed_records": service.query_records(source=["suppression"]),
    }

    print("[INFO] Catalog query result:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()