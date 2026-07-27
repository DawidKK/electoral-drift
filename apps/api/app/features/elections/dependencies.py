from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.features.elections.queries import ElectionQueries
from app.infrastructure.database import get_db_session


def get_election_queries(
    session: Annotated[Session, Depends(get_db_session)],
) -> ElectionQueries:
    """Bind election queries to the request-scoped database session."""
    # This is the feature's persistence composition point. The router depends on the cohesive query
    # service, while SQLAlchemy session wiring remains outside HTTP endpoint functions.
    return ElectionQueries(session)
