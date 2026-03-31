from dotenv import load_dotenv
load_dotenv()

import json

from resonarr.app.deepen_service import DeepenService
from resonarr.utils.logging import (
    RunnerProgress,
    configure_runner_logging,
    timed_step,
)


def main():
    configure_runner_logging("deepen-service-smoke")
    progress = RunnerProgress(total_steps=5)

    with timed_step("Initialize deepen service"):
        service = DeepenService()
    progress.step("Deepen service initialized")

    with timed_step("Build deepen candidate view"):
        candidates = service.list_candidates()
    progress.step("Deepen candidate view built")

    with timed_step("Render deepen candidate payload"):
        print("=== Resonarr Deepen Service Smoke Test ===")
        print("[INFO] Deepen candidate view:")
        print(json.dumps(candidates, indent=2, ensure_ascii=False))
    progress.step("Deepen candidate payload rendered")

    with timed_step("Run deepen dry-run cycle"):
        cycle_result = service.run_cycle(
            limit_evaluations=5,
            limit_acquires=2,
            dry_run=True,
        )
    progress.step("Deepen dry-run cycle completed")

    with timed_step("Render deepen cycle payload"):
        print("[INFO] Deepen cycle result (dry run):")
        print(json.dumps(cycle_result, indent=2, ensure_ascii=False))
    progress.step("Deepen cycle payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
