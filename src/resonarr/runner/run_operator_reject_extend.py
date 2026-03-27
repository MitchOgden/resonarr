from dotenv import load_dotenv
load_dotenv()

import sys

from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("operator-reject-extend")
    service = ExtendOperatorService()

    if len(sys.argv) < 2:
        print('Usage: python -m resonarr.runner.run_operator_reject_extend "Artist Name"')
        return

    artist_name = " ".join(sys.argv[1:]).strip()

    print("=== Resonarr Operator Reject Extend Recommendation ===")
    print(f"[INFO] Target artist: {artist_name}")

    result = service.reject_review_item(artist_name)

    if result.get("status") != "success":
        print(f"[INFO] Rejection failed: {result.get('reason')}")
        return

    print("[INFO] Starter album recommendation rejected")
    print(f"[INFO] Artist: {result.get('artist_name')}")
    print(f"[INFO] Candidate status: {result.get('candidate_status')}")
    print(f"[INFO] Suppressed: {result.get('suppressed')}")
    print(f"[INFO] Lidarr removal status: {result.get('removal_status')}")
    if result.get("removal_reason"):
        print(f"[INFO] Lidarr removal reason: {result.get('removal_reason')}")


if __name__ == "__main__":
    main()