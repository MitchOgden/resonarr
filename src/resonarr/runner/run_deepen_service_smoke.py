from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.deepen_service import DeepenService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("deepen-service-smoke")
    service = DeepenService()

    print("=== Resonarr Deepen Service Smoke Test ===")

    candidates = service.list_candidates()
    print("[INFO] Deepen candidate view:")
    print(json.dumps(candidates, indent=2, ensure_ascii=False))

    cycle_result = service.run_cycle(
        limit_evaluations=5,
        limit_acquires=2,
        dry_run=True,
    )
    print("[INFO] Deepen cycle result (dry run):")
    print(json.dumps(cycle_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()