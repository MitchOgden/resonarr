from dotenv import load_dotenv
load_dotenv()

import json
import sys

from resonarr.app.prune_operator_service import PruneOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-approve-prune")
    service = PruneOperatorService()

    if len(sys.argv) < 3:
        print('Usage: python -m resonarr.runner.run_operator_approve_prune "Artist Name" "Album Name"')
        sys.exit(1)

    artist_name = sys.argv[1]
    album_name = sys.argv[2]

    print("=== Resonarr Approve Prune Recommendation ===")
    print(f"[INFO] Artist: {artist_name}")
    print(f"[INFO] Album: {album_name}")

    result = service.approve_review_item(artist_name, album_name)

    print("[INFO] Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()