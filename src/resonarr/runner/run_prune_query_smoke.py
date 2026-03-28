from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.prune_query_service import PruneQueryService
from resonarr.utils.logging import configure_runner_logging


def main():
    configure_runner_logging("prune-query-smoke")
    service = PruneQueryService()

    print("=== Resonarr Prune Query Service Smoke Test ===")

    payload = {
        "summary": service.get_prune_summary(),
        "reviewable": service.list_reviewable_prune_candidates(),
    }

    print("[INFO] Prune query service result:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()