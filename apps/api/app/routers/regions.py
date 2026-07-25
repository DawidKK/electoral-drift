from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.elections import ElectionRead
from app.schemas.regions import RegionRead, RegionTimelineRead
from app.services.elections import list_region_elections
from app.services.regions import get_region_by_teryt_code, get_region_timeline, list_regions

# This router translates HTTP requests about regions into service-layer calls.
router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionRead])
def get_regions(session: Annotated[Session, Depends(get_db_session)]) -> list[RegionRead]:
    regions = list_regions(session)
    return [RegionRead.model_validate(region) for region in regions]


@router.get("/{teryt_code}/elections", response_model=list[ElectionRead])
def get_region_elections(
    teryt_code: str, session: Annotated[Session, Depends(get_db_session)]
) -> list[ElectionRead]:
    elections = list_region_elections(session, teryt_code)
    return [ElectionRead.model_validate(election) for election in elections]


@router.get("/{teryt_code}/timeline", response_model=RegionTimelineRead)
def get_region_timeline_endpoint(
    teryt_code: str, session: Annotated[Session, Depends(get_db_session)]
) -> dict[str, object]:
    timeline = get_region_timeline(session, teryt_code)
    if timeline is None:
        raise HTTPException(status_code=404, detail="Region not found.")
    return timeline


@router.get("/{teryt_code}", response_model=RegionRead)
def get_region(teryt_code: str, session: Annotated[Session, Depends(get_db_session)]) -> RegionRead:
    region = get_region_by_teryt_code(session, teryt_code)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found.")
    return RegionRead.model_validate(region)
