from fastapi import FastAPI

from app.routers import elections, health, regions


def create_app() -> FastAPI:
    app = FastAPI(
        title="Electoral Drift API",
        version="0.1.0",
        description="API for regional electoral drift analysis in Poland.",
    )
    app.include_router(health.router)
    app.include_router(regions.router)
    app.include_router(elections.router)
    return app


app = create_app()
