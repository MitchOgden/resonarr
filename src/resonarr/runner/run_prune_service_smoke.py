from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.prune_service import PruneService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("prune-service-smoke")
    service = PruneService()

    print("=== Resonarr Prune Service Smoke Test ===")

    result = service.get_prune_summary()

    print("[INFO] Prune service result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()