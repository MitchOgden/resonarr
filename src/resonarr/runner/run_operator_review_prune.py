from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.prune_operator_service import PruneOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-review-prune")
    service = PruneOperatorService()

    print("=== Resonarr Prune Review Queue ===")

    result = service.list_review_queue()

    print("[INFO] Prune review queue:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()