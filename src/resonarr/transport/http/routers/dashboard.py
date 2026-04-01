from fastapi import APIRouter, Depends

from resonarr.transport.http.dependencies import get_dashboard_snapshot_query_service
from resonarr.transport.http.schemas.dashboard import DashboardHomeResponseModel


router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


@router.get("/home", response_model=DashboardHomeResponseModel)
def get_dashboard_home(service=Depends(get_dashboard_snapshot_query_service)):
    payload = service.get_home()
    return DashboardHomeResponseModel(**payload)
