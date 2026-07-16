from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from electoral_db.config import get_database_settings


def get_engine(database_url: str | None = None) -> Engine:
    # The engine owns the connection pool and knows how to talk to PostgreSQL.
    url = database_url or get_database_settings().database_url
    return create_engine(url, pool_pre_ping=True)


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_session() -> Generator[Session]:
    # One Session represents one short unit of database work, usually one API request.
    with SessionLocal() as session:
        yield session
