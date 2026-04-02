from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.catalog_snapshot_query_service import CatalogSnapshotQueryService
from resonarr.app.dashboard_snapshot_query_service import DashboardSnapshotQueryService
from resonarr.utils.logging import (
    RunnerProgress,
    configure_runner_logging,
    timed_step,
)


def main():
    configure_runner_logging("read-model-status")
    progress = RunnerProgress(total_steps=2)

    with timed_step("Inspect current read-model snapshot health"):
        catalog_health = CatalogSnapshotQueryService().get_snapshot_health()
        dashboard_health = DashboardSnapshotQueryService().get_snapshot_health()
    progress.step("Snapshot health inspected")

    with timed_step("Render snapshot status payload"):
        print("=== Resonarr Read Model Status ===")
        print("[INFO] Snapshot status:")
        print(json.dumps({
            "status": "success",
            "catalog_snapshot": catalog_health,
            "dashboard_snapshot": dashboard_health,
        }, indent=2, ensure_ascii=False))
    progress.step("Snapshot status payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
