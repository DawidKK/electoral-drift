from fastapi import FastAPI

from app.features.analytics.router import router as analytics_router
from app.features.elections.router import router as elections_router
from app.features.health.router import router as health_router
from app.features.regions.router import router as regions_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Electoral Drift API",
        version="0.1.0",
        description="API for regional electoral drift analysis in Poland.",
    )
    # Register complete business features at the composition root. Feature packages remain
    # independent of one another and expose only their HTTP router to the application.
    app.include_router(health_router)
    app.include_router(regions_router)
    app.include_router(elections_router)
    app.include_router(analytics_router)
    return app


app = create_app()
