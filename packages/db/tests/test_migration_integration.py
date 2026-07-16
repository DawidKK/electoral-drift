import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

TEST_DATABASE_URL = os.getenv("ELECTORAL_TEST_DATABASE_URL")


@pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set ELECTORAL_TEST_DATABASE_URL to run PostgreSQL migration integration tests.",
)
def test_required_schemas_exist_when_migrated() -> None:
    engine = create_engine(TEST_DATABASE_URL)
    try:
        with engine.connect() as connection:
            schemas = set(
                connection.execute(
                    text(
                        """
                        SELECT schema_name
                        FROM information_schema.schemata
                        WHERE schema_name IN ('raw', 'core', 'analytics', 'ml')
                        """
                    )
                ).scalars()
            )
    except SQLAlchemyError as exc:
        pytest.fail(f"Could not inspect test database: {exc}")

    assert schemas == {"raw", "core", "analytics", "ml"}
