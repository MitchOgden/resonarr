from fastapi import APIRouter, Depends

from resonarr.transport.http.dependencies import (
    get_catalog_snapshot_query_service,
    get_dashboard_snapshot_query_service,
)
from resonarr.transport.http.schemas.common import HealthResponseModel


router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponseModel)
def get_health(
    catalog_service=Depends(get_catalog_snapshot_query_service),
    dashboard_service=Depends(get_dashboard_snapshot_query_service),
):
    return HealthResponseModel(
        status="success",
        service="resonarr-read-api",
        transport_version="v1",
        snapshots={
            "catalog": catalog_service.get_snapshot_health(),
            "dashboard": dashboard_service.get_snapshot_health(),
        },
    )
