from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.regions import RegionRead
from app.services.regions import list_regions

router = APIRouter(prefix="/regions", tags=["regions"])


@router.get("", response_model=list[RegionRead])
def get_regions(session: Annotated[Session, Depends(get_db_session)]) -> list[RegionRead]:
    return list_regions(session)
