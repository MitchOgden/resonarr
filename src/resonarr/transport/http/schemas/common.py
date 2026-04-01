from typing import Any

from pydantic import BaseModel


class ErrorDetailModel(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ErrorResponseModel(BaseModel):
    status: str
    error: ErrorDetailModel


class SnapshotStatusModel(BaseModel):
    available: bool
    reason: str | None = None
    updated_ts: int | None = None
    age_seconds: int | None = None
    ttl_seconds: int | None = None


class HealthResponseModel(BaseModel):
    status: str
    service: str
    transport_version: str
    snapshots: dict[str, SnapshotStatusModel]
