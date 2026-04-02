from resonarr.app.action_errors import (
    ActionConflictError,
    ActionExecutionError,
    ActionTargetNotFoundError,
)
from resonarr.app.extend_operator_service import ExtendOperatorService
from resonarr.execution.lidarr.adapter import LidarrAdapter
from resonarr.state.memory_store import MemoryStore


class ManualOperatorActionService:
    INVALIDATED_SNAPSHOTS = ["catalog_records", "home_summary"]

    def __init__(self, memory=None, adapter=None):
        self.memory = memory or MemoryStore()
        self.adapter = adapter or LidarrAdapter()

    def _invalidate_read_models(self, *, action, target_identifier):
        self.memory.clear_catalog_snapshot("catalog_records")
        self.memory.clear_dashboard_snapshot("home_summary")
        print(
            f"[ACTION][manual_api] {action}: "
            f"target={target_identifier} changed=true "
            f"invalidated={','.join(self.INVALIDATED_SNAPSHOTS)}"
        )
        return list(self.INVALIDATED_SNAPSHOTS)

    def _log_noop(self, *, action, target_identifier, current_status):
        print(
            f"[ACTION][manual_api] {action}: "
            f"target={target_identifier} changed=false noop=true "
            f"current_status={current_status}"
        )

    def reject_extend(self, *, artist_name, note="manual_reject", remove_from_lidarr=False):
        action = "reject_extend"
        candidate = self.memory.find_extend_candidate_by_artist_name(artist_name)
        if not candidate:
            raise ActionTargetNotFoundError(
                action=action,
                message="extend candidate not found",
                details={"artist_name": artist_name},
            )

        current_status = candidate.get("status")
        if current_status == "starter_album_rejected":
            self._log_noop(
                action=action,
                target_identifier={"artist_name": artist_name},
                current_status=current_status,
            )
            return {
                "status": "success",
                "action": action,
                "target_type": "extend_candidate",
                "target_identifier": {"artist_name": artist_name},
                "applied": False,
                "outcome": "noop",
                "candidate_status": current_status,
                "note": note,
                "invalidated_snapshots": [],
                "artist_name": artist_name,
                "suppressed": bool(
                    self.memory.get_artist_state(candidate.get("resolved_artist_mbid") or "").get("suppressed", False)
                ),
                "removal_status": "skipped",
                "removal_reason": "already rejected",
            }

        if current_status not in ExtendOperatorService.REVIEWABLE_STATUSES:
            raise ActionConflictError(
                action=action,
                message="extend candidate is not in a rejectable state",
                details={
                    "artist_name": artist_name,
                    "current_status": current_status,
                },
            )

        artist_mbid = candidate.get("resolved_artist_mbid")
        if not artist_mbid:
            raise ActionConflictError(
                action=action,
                message="extend candidate is missing resolved artist MBID",
                details={"artist_name": artist_name, "current_status": current_status},
            )

        self.memory.suppress_artist(
            artist_mbid,
            reason="operator_rejected_extend_recommendation",
            artist_name=candidate.get("resolved_artist_name") or candidate.get("artist_name"),
        )
        self.memory.mark_extend_candidate_rejected(artist_name, note=note)

        removal_status = "skipped"
        removal_reason = "remove_from_lidarr disabled"

        if remove_from_lidarr:
            removal = self.adapter.remove_staged_artist(artist_mbid)
            removal_status = removal.get("status")
            removal_reason = removal.get("reason")
            if removal_status == "failed":
                raise ActionExecutionError(
                    action=action,
                    message="extend rejection applied but staged artist removal failed",
                    details={
                        "artist_name": artist_name,
                        "current_status": "starter_album_rejected",
                        "removal_reason": removal_reason,
                        "response_text": removal.get("response_text"),
                    },
                )

        invalidated = self._invalidate_read_models(
            action=action,
            target_identifier={"artist_name": artist_name},
        )
        refreshed = self.memory.find_extend_candidate_by_artist_name(artist_name) or {}
        artist_state = self.memory.get_artist_state(artist_mbid)

        return {
            "status": "success",
            "action": action,
            "target_type": "extend_candidate",
            "target_identifier": {"artist_name": artist_name},
            "applied": True,
            "outcome": "applied",
            "candidate_status": refreshed.get("status"),
            "note": note,
            "invalidated_snapshots": invalidated,
            "artist_name": artist_name,
            "suppressed": artist_state.get("suppressed", False),
            "removal_status": removal_status,
            "removal_reason": removal_reason,
        }

    def reject_deepen(self, *, artist_name=None, mbid=None, note="manual_reject"):
        action = "reject_deepen"
        candidate = self.memory.get_deepen_candidate(mbid=mbid, artist_name=artist_name)
        if not candidate or not candidate.get("status"):
            raise ActionTargetNotFoundError(
                action=action,
                message="deepen candidate not found",
                details={"artist_name": artist_name, "mbid": mbid},
            )

        current_status = candidate.get("status")
        resolved_artist_name = candidate.get("artist_name") or artist_name
        resolved_mbid = candidate.get("mbid") or mbid

        if current_status == "deepen_rejected":
            self._log_noop(
                action=action,
                target_identifier={"artist_name": resolved_artist_name, "mbid": resolved_mbid},
                current_status=current_status,
            )
            artist_state = self.memory.get_artist_state(resolved_mbid or "")
            return {
                "status": "success",
                "action": action,
                "target_type": "deepen_candidate",
                "target_identifier": {"artist_name": resolved_artist_name, "mbid": resolved_mbid},
                "applied": False,
                "outcome": "noop",
                "candidate_status": current_status,
                "note": note,
                "invalidated_snapshots": [],
                "artist_name": resolved_artist_name,
                "mbid": resolved_mbid,
                "suppressed": artist_state.get("suppressed", False),
                "suppression_reason": artist_state.get("suppression_reason"),
            }

        if current_status != "deepen_recommendation":
            raise ActionConflictError(
                action=action,
                message="deepen candidate is not in a rejectable state",
                details={
                    "artist_name": resolved_artist_name,
                    "mbid": resolved_mbid,
                    "current_status": current_status,
                },
            )

        if not resolved_mbid:
            raise ActionConflictError(
                action=action,
                message="deepen candidate is missing MBID",
                details={
                    "artist_name": resolved_artist_name,
                    "current_status": current_status,
                },
            )

        self.memory.suppress_artist(
            resolved_mbid,
            reason="operator_rejected_deepen_recommendation",
            artist_name=resolved_artist_name,
        )
        self.memory.mark_deepen_candidate_rejected(
            mbid=resolved_mbid,
            artist_name=resolved_artist_name,
            note=note,
        )

        invalidated = self._invalidate_read_models(
            action=action,
            target_identifier={"artist_name": resolved_artist_name, "mbid": resolved_mbid},
        )
        refreshed = self.memory.get_deepen_candidate(mbid=resolved_mbid, artist_name=resolved_artist_name)
        artist_state = self.memory.get_artist_state(resolved_mbid)

        return {
            "status": "success",
            "action": action,
            "target_type": "deepen_candidate",
            "target_identifier": {"artist_name": resolved_artist_name, "mbid": resolved_mbid},
            "applied": True,
            "outcome": "applied",
            "candidate_status": refreshed.get("status"),
            "note": note,
            "invalidated_snapshots": invalidated,
            "artist_name": resolved_artist_name,
            "mbid": resolved_mbid,
            "suppressed": artist_state.get("suppressed", False),
            "suppression_reason": artist_state.get("suppression_reason"),
        }

    def reject_prune(self, *, artist_name, album_name, note="manual_reject"):
        action = "reject_prune"
        candidate = self.memory.get_prune_candidate(
            artist_name=artist_name,
            album_name=album_name,
        )
        if not candidate or not candidate.get("status"):
            raise ActionTargetNotFoundError(
                action=action,
                message="prune candidate not found",
                details={"artist_name": artist_name, "album_name": album_name},
            )

        current_status = candidate.get("status")

        if current_status == "prune_rejected":
            self._log_noop(
                action=action,
                target_identifier={"artist_name": artist_name, "album_name": album_name},
                current_status=current_status,
            )
            return {
                "status": "success",
                "action": action,
                "target_type": "prune_candidate",
                "target_identifier": {"artist_name": artist_name, "album_name": album_name},
                "applied": False,
                "outcome": "noop",
                "candidate_status": current_status,
                "note": note,
                "invalidated_snapshots": [],
                "artist_name": artist_name,
                "album_name": album_name,
            }

        if current_status != "prune_recommendation":
            raise ActionConflictError(
                action=action,
                message="prune candidate is not in a rejectable state",
                details={
                    "artist_name": artist_name,
                    "album_name": album_name,
                    "current_status": current_status,
                },
            )

        self.memory.mark_prune_candidate_rejected(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=candidate.get("album_mbid"),
            lidarr_album_id=candidate.get("lidarr_album_id"),
            note=note,
        )

        invalidated = self._invalidate_read_models(
            action=action,
            target_identifier={"artist_name": artist_name, "album_name": album_name},
        )
        refreshed = self.memory.get_prune_candidate(
            artist_name=artist_name,
            album_name=album_name,
            album_mbid=candidate.get("album_mbid"),
            lidarr_album_id=candidate.get("lidarr_album_id"),
        )

        return {
            "status": "success",
            "action": action,
            "target_type": "prune_candidate",
            "target_identifier": {"artist_name": artist_name, "album_name": album_name},
            "applied": True,
            "outcome": "applied",
            "candidate_status": refreshed.get("status"),
            "note": note,
            "invalidated_snapshots": invalidated,
            "artist_name": artist_name,
            "album_name": album_name,
        }
