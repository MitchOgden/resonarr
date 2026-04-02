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


def _assert(condition, message):
    if not condition:
        raise AssertionError(message)


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

    with timed_step("Assert read API contract behavior"):
        health_missing_payload = _response_payload(health_missing)
        catalog_missing_payload = _response_payload(catalog_missing)
        dashboard_missing_payload = _response_payload(dashboard_missing)

        health_ready_payload = _response_payload(health_ready)
        catalog_ready_payload = _response_payload(catalog_ready)
        dashboard_ready_payload = _response_payload(dashboard_ready)

        _assert(health_missing_payload["status_code"] == 200, "healthz missing-snapshot phase should return 200")
        _assert(
            health_missing_payload["body"]["snapshots"]["catalog"]["available"] is False,
            "catalog snapshot should be unavailable before priming",
        )
        _assert(
            health_missing_payload["body"]["snapshots"]["dashboard"]["available"] is False,
            "dashboard snapshot should be unavailable before priming",
        )

        _assert(catalog_missing_payload["status_code"] == 503, "catalog endpoint should return 503 before priming")
        _assert(
            catalog_missing_payload["body"]["error"]["code"] == "snapshot_unavailable",
            "catalog missing-snapshot error code should be snapshot_unavailable",
        )

        _assert(dashboard_missing_payload["status_code"] == 503, "dashboard endpoint should return 503 before priming")
        _assert(
            dashboard_missing_payload["body"]["error"]["code"] == "snapshot_unavailable",
            "dashboard missing-snapshot error code should be snapshot_unavailable",
        )

        _assert(health_ready_payload["status_code"] == 200, "healthz ready phase should return 200")
        _assert(
            health_ready_payload["body"]["snapshots"]["catalog"]["available"] is True,
            "catalog snapshot should be available after priming",
        )
        _assert(
            health_ready_payload["body"]["snapshots"]["dashboard"]["available"] is True,
            "dashboard snapshot should be available after priming",
        )

        _assert(catalog_ready_payload["status_code"] == 200, "catalog endpoint should return 200 after priming")
        _assert(
            catalog_ready_payload["body"]["read_path"] == "snapshot",
            "catalog endpoint should be snapshot-backed",
        )
        _assert(
            catalog_ready_payload["body"]["count_scope"] == "full_filtered_result_set",
            "catalog endpoint should preserve count_scope semantics",
        )
        _assert(
            len(catalog_ready_payload["body"]["items"]) > 0,
            "catalog endpoint should return items after priming",
        )

        _assert(dashboard_ready_payload["status_code"] == 200, "dashboard endpoint should return 200 after priming")
        _assert(
            dashboard_ready_payload["body"]["read_path"] == "snapshot",
            "dashboard endpoint should be snapshot-backed",
        )
        _assert(
            "home_summary" in dashboard_ready_payload["body"],
            "dashboard endpoint should return home_summary",
        )
        _assert(
            "sections" in dashboard_ready_payload["body"],
            "dashboard endpoint should return sections",
        )
        _assert(
            "highlights" in dashboard_ready_payload["body"],
            "dashboard endpoint should return highlights",
        )
    progress.step("Read API contract behavior asserted")

    with timed_step("Render smoke payload"):
        print("=== Resonarr Read API Smoke Test ===")
        print("[INFO] Read API result:")
        print(json.dumps({
            "missing_snapshot_phase": {
                "healthz": health_missing_payload,
                "catalog_records": catalog_missing_payload,
                "dashboard_home": dashboard_missing_payload,
            },
            "snapshot_backed_phase": {
                "healthz": health_ready_payload,
                "catalog_records": catalog_ready_payload,
                "dashboard_home": dashboard_ready_payload,
            },
        }, indent=2, ensure_ascii=False))
    progress.step("Smoke payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
