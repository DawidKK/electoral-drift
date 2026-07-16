from electoral_db.base import Base
from electoral_db.models import Region


def test_required_schema_tables_are_declared() -> None:
    tables = Base.metadata.tables

    assert "core.regions" in tables
    assert "core.elections" in tables
    assert "core.election_results" in tables
    assert "core.socioeconomic_observations" in tables
    assert "analytics.region_political_stability" in tables
    assert "ml.modeling_dataset" in tables
    assert "ml.model_runs" in tables
    assert "ml.predictions" in tables


def test_teryt_code_is_string_column() -> None:
    assert Region.__table__.c.teryt_code.type.python_type is str
