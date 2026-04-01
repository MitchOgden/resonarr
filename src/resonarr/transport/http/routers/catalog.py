from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from resonarr.transport.http.dependencies import get_catalog_snapshot_query_service
from resonarr.transport.http.schemas.catalog import CatalogQueryResponseModel


router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])

SortBy = Literal["source", "kind", "artist_name", "album_title", "status", "score", "event_ts"]
SortDirection = Literal["asc", "desc"]


@router.get("/records", response_model=CatalogQueryResponseModel)
def get_catalog_records(
    kind: Annotated[list[str] | None, Query()] = None,
    source: Annotated[list[str] | None, Query()] = None,
    status: Annotated[list[str] | None, Query()] = None,
    artist_name_contains: str | None = None,
    album_title_contains: str | None = None,
    artist_mbid: str | None = None,
    live_only: bool = False,
    historical_only: bool = False,
    event_ts_min: int | None = None,
    event_ts_max: int | None = None,
    sort_by: SortBy = "source",
    sort_direction: SortDirection = "asc",
    limit: Annotated[int | None, Query(ge=0, le=500)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    service=Depends(get_catalog_snapshot_query_service),
):
    payload = service.query_records(
        kind=kind,
        source=source,
        status=status,
        artist_name_contains=artist_name_contains,
        album_title_contains=album_title_contains,
        artist_mbid=artist_mbid,
        live_only=live_only,
        historical_only=historical_only,
        event_ts_min=event_ts_min,
        event_ts_max=event_ts_max,
        sort_by=sort_by,
        sort_direction=sort_direction,
        limit=limit,
        offset=offset,
    )
    return CatalogQueryResponseModel(**payload)
