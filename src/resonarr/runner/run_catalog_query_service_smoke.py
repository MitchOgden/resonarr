from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.catalog_query_service import CatalogQueryService
from resonarr.utils.logging import (
    RunnerProgress,
    configure_runner_logging,
    timed_step,
)


def main():
    configure_runner_logging("catalog-query-service-smoke")
    progress = RunnerProgress(total_steps=5)

    with timed_step("Initialize catalog query service"):
        service = CatalogQueryService()
    progress.step("Catalog query service initialized")

    with timed_step("Clear catalog snapshot"):
        service.memory.clear_catalog_snapshot(service.SNAPSHOT_NAME)
    progress.step("Catalog snapshot cleared")

    with timed_step("Refresh catalog snapshot from live sources"):
        refresh_result = service.refresh_snapshot()
    progress.step("Catalog snapshot refreshed")

    with timed_step("Run canonical snapshot queries"):
        all_page = service.query_records(
            sort_by="event_ts",
            sort_direction="desc",
            limit=5,
            offset=0,
        )
        deepen_page = service.query_records(
            source=["deepen"],
            sort_by="score",
            sort_direction="desc",
            limit=5,
            offset=0,
        )
        deepen_page_two = service.query_records(
            source=["deepen"],
            sort_by="score",
            sort_direction="desc",
            limit=5,
            offset=5,
        )
    progress.step("Canonical snapshot queries completed")

    with timed_step("Render catalog query payload"):
        print("=== Resonarr Catalog Query Service Smoke Test ===")
        print("[INFO] Catalog query service result:")
        print(json.dumps({
            "contract": service.get_contract_definition(),
            "refresh_result": refresh_result,
            "all_page": all_page,
            "deepen_page": deepen_page,
            "deepen_page_two": deepen_page_two,
        }, indent=2, ensure_ascii=False))
    progress.step("Catalog query payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
