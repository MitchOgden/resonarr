from fastapi import FastAPI

from resonarr.transport.http.errors import install_exception_handlers
from resonarr.transport.http.routers import catalog, dashboard, health, operator_actions


def create_app():
    app = FastAPI(
        title="Resonarr Read API",
        version="v1",
    )

    install_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(catalog.router)
    app.include_router(dashboard.router)
    app.include_router(operator_actions.router)

    return app


app = create_app()
