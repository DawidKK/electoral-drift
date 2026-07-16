from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.regions import RegionRead
from app.services.regions import get_region_by_teryt_code, list_regions

# This router translates HTTP requests about regions into service-layer calls.
router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionRead])
def get_regions(session: Annotated[Session, Depends(get_db_session)]) -> list[RegionRead]:
    return list_regions(session)


@router.get("/{teryt_code}", response_model=RegionRead)
def get_region(teryt_code: str, session: Annotated[Session, Depends(get_db_session)]) -> RegionRead:
    region = get_region_by_teryt_code(session, teryt_code)
    if region is None:
        raise HTTPException(status_code=404, detail="Region not found.")
    return region
