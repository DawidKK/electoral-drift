from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.analytics import RegionStabilityRead
from app.services.analytics import list_stability_ranking

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/stability-ranking", response_model=list[RegionStabilityRead])
def get_stability_ranking(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[dict[str, object]]:
    return list_stability_ranking(session, limit=limit)


@router.get("/swing-counties", response_model=list[RegionStabilityRead])
def get_swing_counties(
    session: Annotated[Session, Depends(get_db_session)],
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
) -> list[dict[str, object]]:
    return list_stability_ranking(session, labels=("swing", "emerging_shift"), limit=limit)
