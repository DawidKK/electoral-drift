from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.features.regions.dependencies import get_region_queries
from app.features.regions.queries import RegionQueries
from app.features.regions.schemas import (
    RegionElectionRead,
    RegionRead,
    RegionTimelineRead,
)

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionRead])
def get_regions(
    queries: Annotated[RegionQueries, Depends(get_region_queries)],
) -> list[RegionRead]:
    """Return all regions in deterministic TERYT order."""
    return queries.list_regions()


@router.get("/{teryt_code}/elections", response_model=list[RegionElectionRead])
def get_region_elections(
    teryt_code: str,
    queries: Annotated[RegionQueries, Depends(get_region_queries)],
) -> list[RegionElectionRead]:
    """Return elections for which a region has imported results."""
    return queries.list_elections(teryt_code)


@router.get("/{teryt_code}/timeline", response_model=RegionTimelineRead)
def get_region_timeline(
    teryt_code: str,
    queries: Annotated[RegionQueries, Depends(get_region_queries)],
) -> RegionTimelineRead:
    """Return a bloc-level election timeline for one region."""
    # The query layer reports domain absence without knowing HTTP. Translate that outcome only at
    # the transport boundary, where the public status code and message belong.
    timeline = queries.get_timeline(teryt_code)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Region not found.")
    return timeline


@router.get("/{teryt_code}", response_model=RegionRead)
def get_region(
    teryt_code: str,
    queries: Annotated[RegionQueries, Depends(get_region_queries)],
) -> RegionRead:
    """Return one region identified by its TERYT code."""
    # Keep the same missing-region contract as the timeline endpoint while leaving persistence
    # details and entity conversion inside the feature query service.
    region = queries.get_region(teryt_code)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found.")
    return region
