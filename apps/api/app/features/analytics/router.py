from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.features.analytics.dependencies import get_analytics_queries
from app.features.analytics.queries import AnalyticsQueries
from app.features.analytics.schemas import RegionStabilityRead

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stability-ranking", response_model=list[RegionStabilityRead])
def get_stability_ranking(
    queries: Annotated[AnalyticsQueries, Depends(get_analytics_queries)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[RegionStabilityRead]:
    """Return the political-stability ranking with a bounded result size."""
    return queries.list_stability(limit=limit)


@router.get("/swing-counties", response_model=list[RegionStabilityRead])
def get_swing_counties(
    queries: Annotated[AnalyticsQueries, Depends(get_analytics_queries)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[RegionStabilityRead]:
    """Return regions classified as swing or as an emerging political shift."""
    # The label set is part of this endpoint's product semantics, while filtering and ordering
    # remain a persistence concern handled by the feature query service.
    return queries.list_stability(labels=("swing", "emerging_shift"), limit=limit)
