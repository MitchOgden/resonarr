from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.dashboard_service import DashboardService
from resonarr.app.catalog_snapshot_query_service import CatalogSnapshotQueryService
from resonarr.app.dashboard_snapshot_query_service import DashboardSnapshotQueryService
from resonarr.utils.logging import (
    RunnerProgress,
    configure_runner_logging,
    timed_step,
)


def main():
    configure_runner_logging("read-model-refresh")
    progress = RunnerProgress(total_steps=3)

    with timed_step("Prime dashboard and catalog snapshots outside HTTP path"):
        payload = DashboardService().get_home_summary(force_refresh=True)
    progress.step("Snapshots primed")

    with timed_step("Inspect refreshed snapshot health"):
        catalog_health = CatalogSnapshotQueryService().get_snapshot_health()
        dashboard_health = DashboardSnapshotQueryService().get_snapshot_health()
    progress.step("Snapshot health inspected")

    with timed_step("Render refresh payload"):
        print("=== Resonarr Read Model Refresh ===")
        print("[INFO] Refresh result:")
        print(json.dumps({
            "status": "success",
            "home_summary_keys": sorted(list(payload.get("home_summary", {}).keys())),
            "catalog_snapshot": catalog_health,
            "dashboard_snapshot": dashboard_health,
        }, indent=2, ensure_ascii=False))
    progress.step("Refresh payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
