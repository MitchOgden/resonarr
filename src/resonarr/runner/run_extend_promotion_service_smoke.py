from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.extend_promotion_service import ExtendPromotionService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("extend-promotion-service-smoke")
    service = ExtendPromotionService()

    print("=== Resonarr Extend Promotion Service Smoke Test ===")

    promotable = service.list_promotable_candidates()
    print("[INFO] Promotable candidate view:")
    print(json.dumps(promotable, indent=2, ensure_ascii=False))

    cycle_result = service.run_promotion_cycle(limit=3, dry_run=True)
    print("[INFO] Promotion cycle result (dry run):")
    print(json.dumps(cycle_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()