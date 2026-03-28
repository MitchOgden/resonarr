from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.deepen_operator_service import DeepenOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-review-deepen")
    service = DeepenOperatorService()

    print("=== Resonarr Deepen Review Queue ===")

    result = service.list_review_queue()

    print("[INFO] Deepen review queue:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()