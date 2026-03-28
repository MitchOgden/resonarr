from dotenv import load_dotenv
load_dotenv()

import json
import sys

from resonarr.app.deepen_operator_service import DeepenOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-approve-deepen")
    service = DeepenOperatorService()

    if len(sys.argv) < 2:
        print('Usage: python -m resonarr.runner.run_operator_approve_deepen "Artist Name"')
        sys.exit(1)

    artist_name = sys.argv[1]

    print("=== Resonarr Approve Deepen Recommendation ===")
    print(f"[INFO] Artist: {artist_name}")

    result = service.approve_review_item(artist_name)

    print("[INFO] Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()