import os
from dataclasses import dataclass
from functools import lru_cache

DEFAULT_DATABASE_URL = "postgresql+psycopg://electoral:electoral@localhost:5432/electoral_db"


@dataclass(frozen=True)
class DatabaseSettings:
    database_url: str = DEFAULT_DATABASE_URL


@lru_cache
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings(database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
