from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-service-smoke")
    service = ExtendOperatorService()

    print("=== Resonarr Operator Service Smoke Test ===")

    review_result = service.list_review_queue()

    print("[INFO] Review queue service result:")
    print(json.dumps(review_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()