from typing import Annotated

from fastapi import APIRouter, Depends

from app.features.elections.dependencies import get_election_queries
from app.features.elections.queries import ElectionQueries
from app.features.elections.schemas import ElectionRead, ElectionResultRead

router = APIRouter(prefix="/elections", tags=["elections"])


@router.get("", response_model=list[ElectionRead])
def get_elections(
    queries: Annotated[ElectionQueries, Depends(get_election_queries)],
) -> list[ElectionRead]:
    """Return the election catalogue ordered from newest to oldest."""
    return queries.list_elections()


@router.get("/{election_id}/results", response_model=list[ElectionResultRead])
def get_election_results(
    election_id: int,
    queries: Annotated[ElectionQueries, Depends(get_election_queries)],
) -> list[ElectionResultRead]:
    """Return committee-level results for one election."""
    return queries.list_results(election_id)
