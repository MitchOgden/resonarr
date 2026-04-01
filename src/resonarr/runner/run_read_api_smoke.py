from dotenv import load_dotenv
load_dotenv()

import json

from fastapi.testclient import TestClient

from resonarr.app.dashboard_service import DashboardService
from resonarr.state.memory_store import MemoryStore
from resonarr.transport.http.fastapi_app import create_app
from resonarr.utils.logging import (
    RunnerProgress,
    configure_runner_logging,
    timed_step,
)


def _response_payload(response):
    try:
        payload = response.json()
    except Exception:
        payload = {"non_json_body": response.text}

    return {
        "status_code": response.status_code,
        "body": payload,
    }


def main():
    configure_runner_logging("read-api-smoke")
    progress = RunnerProgress(total_steps=7)

    with timed_step("Clear snapshots to prove unavailable behavior"):
        memory = MemoryStore()
        memory.clear_catalog_snapshot("catalog_records")
        memory.clear_dashboard_snapshot("home_summary")
    progress.step("Snapshots cleared")

    with timed_step("Create FastAPI app and test client"):
        app = create_app()
        client = TestClient(app)
    progress.step("FastAPI app created")

    with timed_step("Call health endpoint with missing snapshots"):
        health_missing = client.get("/healthz")
    progress.step("Health endpoint with missing snapshots called")

    with timed_step("Call read endpoints with missing snapshots"):
        catalog_missing = client.get("/api/v1/catalog/records?limit=5")
        dashboard_missing = client.get("/api/v1/dashboard/home")
    progress.step("Missing snapshot behavior captured")

    with timed_step("Prime snapshots outside HTTP path"):
        DashboardService().get_home_summary(force_refresh=True)
    progress.step("Snapshots primed outside HTTP path")

    with timed_step("Call snapshot-backed read endpoints"):
        health_ready = client.get("/healthz")
        catalog_ready = client.get(
            "/api/v1/catalog/records"
            "?source=deepen"
            "&sort_by=score"
            "&sort_direction=desc"
            "&limit=5"
        )
        dashboard_ready = client.get("/api/v1/dashboard/home")
    progress.step("Snapshot-backed read endpoints called")

    with timed_step("Render smoke payload"):
        print("=== Resonarr Read API Smoke Test ===")
        print("[INFO] Read API result:")
        print(json.dumps({
            "missing_snapshot_phase": {
                "healthz": _response_payload(health_missing),
                "catalog_records": _response_payload(catalog_missing),
                "dashboard_home": _response_payload(dashboard_missing),
            },
            "snapshot_backed_phase": {
                "healthz": _response_payload(health_ready),
                "catalog_records": _response_payload(catalog_ready),
                "dashboard_home": _response_payload(dashboard_ready),
            },
        }, indent=2, ensure_ascii=False))
    progress.step("Smoke payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
