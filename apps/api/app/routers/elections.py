from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_db_session
from app.schemas.elections import ElectionRead, ElectionResultRead
from app.services.elections import list_election_results, list_elections

# This router exposes election events and their imported result facts.
router = APIRouter(prefix="/elections", tags=["elections"])


@router.get("", response_model=list[ElectionRead])
def get_elections(session: Annotated[Session, Depends(get_db_session)]) -> list[ElectionRead]:
    return list_elections(session)


@router.get("/{election_id}/results", response_model=list[ElectionResultRead])
def get_election_results(
    election_id: int, session: Annotated[Session, Depends(get_db_session)]
) -> list[dict[str, object]]:
    return list_election_results(session, election_id)
