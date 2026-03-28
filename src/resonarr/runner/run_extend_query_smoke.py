from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.extend_query_service import ExtendQueryService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("extend-query-smoke")
    service = ExtendQueryService()

    print("=== Resonarr Extend Query Service Smoke Test ===")

    summary = service.get_extend_status_summary()
    reviewable = service.list_candidates_by_status(
        {"starter_album_recommendation", "starter_album_candidate"}
    )
    suppressed = service.list_suppressed_artists()

    payload = {
        "summary": summary,
        "reviewable": reviewable,
        "suppressed": suppressed,
    }

    print("[INFO] Extend query service result:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()