from typing import Literal

from pydantic import BaseModel


class ExtendRejectRequestModel(BaseModel):
    artist_name: str
    note: str = "manual_reject"
    remove_from_lidarr: bool = False


class DeepenRejectRequestModel(BaseModel):
    artist_name: str | None = None
    mbid: str | None = None
    note: str = "manual_reject"


class PruneRejectRequestModel(BaseModel):
    artist_name: str
    album_name: str
    note: str = "manual_reject"


class OperatorActionResponseBaseModel(BaseModel):
    status: Literal["success"]
    action: str
    target_type: str
    target_identifier: dict[str, str | int | None]
    applied: bool
    outcome: Literal["applied", "noop"]
    candidate_status: str | None = None
    note: str | None = None
    invalidated_snapshots: list[str]


class ExtendRejectResponseModel(OperatorActionResponseBaseModel):
    artist_name: str
    suppressed: bool
    removal_status: str | None = None
    removal_reason: str | None = None


class DeepenRejectResponseModel(OperatorActionResponseBaseModel):
    artist_name: str
    mbid: str | None = None
    suppressed: bool
    suppression_reason: str | None = None


class PruneRejectResponseModel(OperatorActionResponseBaseModel):
    artist_name: str
    album_name: str
