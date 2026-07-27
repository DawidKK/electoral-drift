from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.features.analytics.queries import AnalyticsQueries
from app.infrastructure.database import get_db_session


def get_analytics_queries(
    session: Annotated[Session, Depends(get_db_session)],
) -> AnalyticsQueries:
    """Bind analytics queries to the request-scoped database session."""
    # Feature-local construction keeps endpoint tests independent from SQLAlchemy's Session API.
    return AnalyticsQueries(session)
