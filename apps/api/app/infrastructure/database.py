from collections.abc import Generator

from electoral_db.session import get_session
from sqlalchemy.orm import Session


def get_db_session() -> Generator[Session]:
    """Provide one database session for the lifetime of an HTTP request."""
    # Session creation stays in infrastructure so feature routers do not depend directly on
    # SQLAlchemy configuration or on the database package's session factory.
    yield from get_session()
