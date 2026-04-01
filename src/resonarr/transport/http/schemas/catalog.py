from pydantic import BaseModel


class CatalogRecordModel(BaseModel):
    kind: str
    source: str
    status: str
    live: bool
    historical: bool
    artist_name: str | None = None
    artist_mbid: str | None = None
    album_title: str | None = None
    album_id: int | str | None = None
    score: float | None = None
    reason: str | None = None
    event_ts: int | None = None


class CatalogQueryResponseModel(BaseModel):
    status: str
    contract_version: str
    count_scope: str
    read_path: str
    snapshot_age_seconds: int | None = None
    snapshot_updated_ts: int | None = None
    count: int
    total_count: int
    offset: int
    limit: int | None = None
    sort_by: str
    sort_direction: str
    counts_by_kind: dict[str, int]
    counts_by_source: dict[str, int]
    counts_by_status: dict[str, int]
    items: list[CatalogRecordModel]
