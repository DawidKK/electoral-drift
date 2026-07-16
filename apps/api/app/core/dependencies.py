from collections.abc import Generator

from electoral_db.session import get_session
from sqlalchemy.orm import Session


def get_db_session() -> Generator[Session]:
    # FastAPI calls this per request and closes the session when the request is done.
    yield from get_session()
