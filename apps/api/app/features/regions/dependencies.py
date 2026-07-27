from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.features.regions.queries import RegionQueries
from app.infrastructure.database import get_db_session


def get_region_queries(
    session: Annotated[Session, Depends(get_db_session)],
) -> RegionQueries:
    """Bind region queries to the request-scoped database session."""
    # Keep construction beside the feature that consumes it, while the reusable session lifecycle
    # remains an infrastructure responsibility.
    return RegionQueries(session)
