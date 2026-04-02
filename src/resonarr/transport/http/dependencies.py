from fastapi import Depends

from resonarr.app.catalog_query_service import CatalogQueryService
from resonarr.app.catalog_snapshot_query_service import CatalogSnapshotQueryService
from resonarr.app.dashboard_snapshot_query_service import DashboardSnapshotQueryService
from resonarr.app.manual_operator_action_service import ManualOperatorActionService
from resonarr.state.memory_store import MemoryStore


def get_memory_store():
    return MemoryStore()


def get_catalog_snapshot_query_service(memory=Depends(get_memory_store)):
    return CatalogSnapshotQueryService(
        catalog_query_service=CatalogQueryService(memory=memory)
    )


def get_dashboard_snapshot_query_service(memory=Depends(get_memory_store)):
    return DashboardSnapshotQueryService(memory=memory)


def get_manual_operator_action_service(memory=Depends(get_memory_store)):
    return ManualOperatorActionService(memory=memory)
