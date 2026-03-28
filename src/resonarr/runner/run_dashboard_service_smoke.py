from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.dashboard_service import DashboardService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("dashboard-service-smoke")
    service = DashboardService()

    print("=== Resonarr Dashboard Service Smoke Test ===")

    payload = service.get_home_summary()

    print("[INFO] Dashboard service result:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()