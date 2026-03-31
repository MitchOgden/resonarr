from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.dashboard_service import DashboardService
from resonarr.utils.logging import (
    RunnerProgress,
    configure_runner_logging,
    timed_step,
)


def main():
    configure_runner_logging("dashboard-service-smoke")
    progress = RunnerProgress(total_steps=3)

    with timed_step("Initialize dashboard service"):
        service = DashboardService()
    progress.step("Dashboard service initialized")

    with timed_step("Build dashboard summary"):
        payload = service.get_home_summary()
    progress.step("Dashboard summary built")

    with timed_step("Render dashboard payload"):
        print("=== Resonarr Dashboard Service Smoke Test ===")
        print("[INFO] Dashboard service result:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    progress.step("Dashboard payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
