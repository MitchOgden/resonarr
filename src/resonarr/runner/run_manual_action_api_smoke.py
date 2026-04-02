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


def _pick_deepen_target(memory):
    candidates = memory.list_deepen_candidates_by_status({"deepen_recommendation"})
    candidates.sort(
        key=lambda item: (
            -(item.get("lastfm_playcount") or 0),
            (item.get("artist_name") or "").lower(),
        )
    )

    if not candidates:
        raise AssertionError("No deepen recommendation candidate available for manual action smoke")

    item = candidates[0]
    return {
        "artist_name": item.get("artist_name"),
        "mbid": item.get("mbid"),
    }


def main():
    configure_runner_logging("manual-action-api-smoke")
    progress = RunnerProgress(total_steps=8)

    with timed_step("Create FastAPI app and test client"):
        app = create_app()
        client = TestClient(app)
    progress.step("FastAPI app created")

    with timed_step("Prime snapshots outside HTTP path"):
        DashboardService().get_home_summary(force_refresh=True)
    progress.step("Snapshots primed")

    with timed_step("Pick a safe persisted deepen reject target"):
        memory = MemoryStore()
        target = _pick_deepen_target(memory)
    progress.step("Deepen target selected")

    with timed_step("Confirm read endpoints are healthy before action"):
        pre_health = client.get("/healthz")
        pre_dashboard = client.get("/api/v1/dashboard/home")
        pre_catalog = client.get("/api/v1/catalog/records?source=deepen&limit=5")
    progress.step("Pre-action reads confirmed")

    with timed_step("Execute deepen reject success path"):
        success_response = client.post(
            "/api/v1/operator/deepen/reject",
            json={
                "artist_name": target["artist_name"],
                "mbid": target["mbid"],
                "note": "manual_action_api_smoke",
            },
        )
    progress.step("Deepen reject success path executed")

    with timed_step("Capture no-op and failure behavior plus post-action reads"):
        noop_response = client.post(
            "/api/v1/operator/deepen/reject",
            json={
                "artist_name": target["artist_name"],
                "mbid": target["mbid"],
                "note": "manual_action_api_smoke",
            },
        )
        failure_response = client.post(
            "/api/v1/operator/deepen/reject",
            json={
                "artist_name": "definitely-not-a-real-artist",
                "mbid": "not-a-real-mbid",
                "note": "manual_action_api_smoke_missing",
            },
        )
        post_health = client.get("/healthz")
        post_dashboard = client.get("/api/v1/dashboard/home")
        post_catalog = client.get("/api/v1/catalog/records?source=deepen&limit=5")
    progress.step("No-op, failure, and post-action reads captured")

    with timed_step("Rebuild snapshots outside HTTP and confirm reads recover"):
        DashboardService().get_home_summary(force_refresh=True)
        recovered_health = client.get("/healthz")
        recovered_dashboard = client.get("/api/v1/dashboard/home")
        recovered_catalog = client.get("/api/v1/catalog/records?source=deepen&limit=5")
    progress.step("Read-model recovery confirmed")

    with timed_step("Assert manual action API behavior"):
        pre_health_payload = _response_payload(pre_health)
        pre_dashboard_payload = _response_payload(pre_dashboard)
        pre_catalog_payload = _response_payload(pre_catalog)

        success_payload = _response_payload(success_response)
        noop_payload = _response_payload(noop_response)
        failure_payload = _response_payload(failure_response)

        post_health_payload = _response_payload(post_health)
        post_dashboard_payload = _response_payload(post_dashboard)
        post_catalog_payload = _response_payload(post_catalog)

        recovered_health_payload = _response_payload(recovered_health)
        recovered_dashboard_payload = _response_payload(recovered_dashboard)
        recovered_catalog_payload = _response_payload(recovered_catalog)

        _assert(pre_health_payload["status_code"] == 200, "pre-action health should return 200")
        _assert(pre_dashboard_payload["status_code"] == 200, "pre-action dashboard read should return 200")
        _assert(pre_catalog_payload["status_code"] == 200, "pre-action catalog read should return 200")

        _assert(success_payload["status_code"] == 200, "success action should return 200")
        _assert(success_payload["body"]["status"] == "success", "success action payload should be success")
        _assert(success_payload["body"]["action"] == "reject_deepen", "success action should be reject_deepen")
        _assert(success_payload["body"]["applied"] is True, "success action should apply state change")
        _assert(success_payload["body"]["outcome"] == "applied", "success action outcome should be applied")
        _assert(
            success_payload["body"]["invalidated_snapshots"] == ["catalog_records", "home_summary"],
            "success action should invalidate both read-model snapshots",
        )

        _assert(noop_payload["status_code"] == 200, "noop action should return 200")
        _assert(noop_payload["body"]["applied"] is False, "noop action should not apply a state change")
        _assert(noop_payload["body"]["outcome"] == "noop", "noop action should report noop outcome")
        _assert(
            noop_payload["body"]["invalidated_snapshots"] == [],
            "noop action should not invalidate snapshots",
        )

        _assert(failure_payload["status_code"] == 404, "missing target should return 404")
        _assert(
            failure_payload["body"]["error"]["code"] == "action_target_not_found",
            "missing target error code should be action_target_not_found",
        )

        _assert(post_health_payload["status_code"] == 200, "post-action health should still return 200")
        _assert(
            post_health_payload["body"]["snapshots"]["catalog"]["available"] is False,
            "catalog snapshot should be unavailable after successful action invalidation",
        )
        _assert(
            post_health_payload["body"]["snapshots"]["dashboard"]["available"] is False,
            "dashboard snapshot should be unavailable after successful action invalidation",
        )
        _assert(post_dashboard_payload["status_code"] == 503, "dashboard read should return 503 after invalidation")
        _assert(post_catalog_payload["status_code"] == 503, "catalog read should return 503 after invalidation")

        _assert(recovered_health_payload["status_code"] == 200, "recovered health should return 200")
        _assert(
            recovered_health_payload["body"]["snapshots"]["catalog"]["available"] is True,
            "catalog snapshot should recover after non-HTTP refresh",
        )
        _assert(
            recovered_health_payload["body"]["snapshots"]["dashboard"]["available"] is True,
            "dashboard snapshot should recover after non-HTTP refresh",
        )
        _assert(recovered_dashboard_payload["status_code"] == 200, "dashboard read should recover after refresh")
        _assert(recovered_catalog_payload["status_code"] == 200, "catalog read should recover after refresh")
    progress.step("Manual action API behavior asserted")

    with timed_step("Render manual action API smoke payload"):
        print("=== Resonarr Manual Action API Smoke Test ===")
        print("[INFO] Manual action API result:")
        print(json.dumps({
            "target": target,
            "pre_action_reads": {
                "healthz": pre_health_payload,
                "dashboard_home": pre_dashboard_payload,
                "catalog_records": pre_catalog_payload,
            },
            "action_phase": {
                "success": success_payload,
                "noop": noop_payload,
                "failure": failure_payload,
            },
            "post_action_reads": {
                "healthz": post_health_payload,
                "dashboard_home": post_dashboard_payload,
                "catalog_records": post_catalog_payload,
            },
            "recovered_reads": {
                "healthz": recovered_health_payload,
                "dashboard_home": recovered_dashboard_payload,
                "catalog_records": recovered_catalog_payload,
            },
        }, indent=2, ensure_ascii=False))
    progress.step("Manual action API smoke payload rendered")

    progress.finish()


if __name__ == "__main__":
    main()
