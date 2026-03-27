from dotenv import load_dotenv
load_dotenv()

import sys

from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-approve-extend")
    service = ExtendOperatorService()

    if len(sys.argv) < 2:
        print('Usage: python -m resonarr.runner.run_operator_approve_extend "Artist Name"')
        return

    artist_name = " ".join(sys.argv[1:]).strip()

    print("=== Resonarr Operator Approve Extend Recommendation ===")
    print(f"[INFO] Target artist: {artist_name}")

    result = service.approve_review_item(artist_name)

    if result.get("status") != "success":
        print(f"[INFO] Approval failed: {result.get('reason')}")
        if result.get("response_text"):
            print(f"[INFO] Response: {result.get('response_text')}")
        return

    print("[INFO] Starter album recommendation approved")
    print(f"[INFO] Artist: {result.get('artist_name')}")
    print(f"[INFO] Album: {result.get('album_title')}")
    print(f"[INFO] Candidate status: {result.get('candidate_status')}")


if __name__ == "__main__":
    main()