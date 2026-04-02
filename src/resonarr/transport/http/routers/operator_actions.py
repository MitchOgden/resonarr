from fastapi import APIRouter, Depends, HTTPException

from resonarr.transport.http.dependencies import get_manual_operator_action_service
from resonarr.transport.http.schemas.actions import (
    DeepenRejectRequestModel,
    DeepenRejectResponseModel,
    ExtendRejectRequestModel,
    ExtendRejectResponseModel,
    PruneRejectRequestModel,
    PruneRejectResponseModel,
)


router = APIRouter(prefix="/api/v1/operator", tags=["operator-actions"])


@router.post("/extend/reject", response_model=ExtendRejectResponseModel)
def reject_extend(
    command: ExtendRejectRequestModel,
    service=Depends(get_manual_operator_action_service),
):
    payload = service.reject_extend(
        artist_name=command.artist_name,
        note=command.note,
        remove_from_lidarr=command.remove_from_lidarr,
    )
    return ExtendRejectResponseModel(**payload)


@router.post("/deepen/reject", response_model=DeepenRejectResponseModel)
def reject_deepen(
    command: DeepenRejectRequestModel,
    service=Depends(get_manual_operator_action_service),
):
    if not command.artist_name and not command.mbid:
        raise HTTPException(
            status_code=400,
            detail="artist_name or mbid is required",
        )

    payload = service.reject_deepen(
        artist_name=command.artist_name,
        mbid=command.mbid,
        note=command.note,
    )
    return DeepenRejectResponseModel(**payload)


@router.post("/prune/reject", response_model=PruneRejectResponseModel)
def reject_prune(
    command: PruneRejectRequestModel,
    service=Depends(get_manual_operator_action_service),
):
    payload = service.reject_prune(
        artist_name=command.artist_name,
        album_name=command.album_name,
        note=command.note,
    )
    return PruneRejectResponseModel(**payload)
