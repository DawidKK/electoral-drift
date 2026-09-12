import csv
from decimal import Decimal
from pathlib import Path

import pytest
from electoral_ingestion.socioeconomic import (
    SocioeconomicObservationInput,
    import_registered_unemployment_share,
    load_socioeconomic_observations_csv,
)

TEST_HASH = "a" * 64


class FakeModel:
    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def all(self) -> list[object]:
        return self.rows


class FakeSession:
    def __init__(
        self,
        *,
        scalar_results: list[object | None],
        scalars_results: list[list[object]],
    ) -> None:
        self.scalar_results = scalar_results
        self.scalars_results = scalars_results
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    def scalar(self, statement: object) -> object | None:
        return self.scalar_results.pop(0)

    def scalars(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult(self.scalars_results.pop(0))

    def add(self, model: object) -> None:
        if not hasattr(model, "id") or model.id is None:
            model.id = 100 + len(self.added)
        self.added.append(model)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def sample_row() -> SocioeconomicObservationInput:
    return SocioeconomicObservationInput(
        teryt_code="0201011",
        year=2014,
        value=Decimal("4.8"),
        source_file_sha256=TEST_HASH,
    )


def write_processed(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["teryt_code", "year", "value", "source_file_sha256"],
        )
        writer.writeheader()
        writer.writerows(rows)


def test_load_processed_observations_preserves_decimal_and_teryt(tmp_path: Path) -> None:
    path = tmp_path / "observations.csv"
    write_processed(
        path,
        [
            {
                "teryt_code": "0201011",
                "year": "2014",
                "value": "4.8",
                "source_file_sha256": TEST_HASH,
            }
        ],
    )

    assert load_socioeconomic_observations_csv(path) == [sample_row()]


def test_import_creates_variable_source_and_observation() -> None:
    region = FakeModel(id=1, teryt_code="0201011")
    session = FakeSession(
        scalar_results=[None, None],
        scalars_results=[[region], []],
    )

    summary = import_registered_unemployment_share(session, [sample_row()])

    assert summary.variable_created is True
    assert summary.source_created is True
    assert summary.observations_created == 1
    assert summary.observations_unchanged == 0
    assert session.committed is True
    assert session.rolled_back is False
    observation = session.added[-1]
    assert observation.region_id == 1
    assert observation.year == 2014
    assert observation.value == Decimal("4.8")


def test_import_is_noop_for_identical_observation() -> None:
    source = FakeModel(id=10)
    variable = FakeModel(
        id=20,
        code="registered_unemployed_working_age_share",
        name="Udział zarejestrowanych bezrobotnych w ludności w wieku produkcyjnym",
        source="GUS/BDL",
        unit="percent",
        description="GUS/BDL P2670; values are percentage points.",
    )
    region = FakeModel(id=1, teryt_code="0201011")
    existing = FakeModel(
        region_id=1,
        variable_id=20,
        year=2014,
        value=Decimal("4.8"),
        source_id=10,
        source_note=f"raw_sha256={TEST_HASH}",
    )
    session = FakeSession(
        scalar_results=[source, variable],
        scalars_results=[[region], [existing]],
    )

    summary = import_registered_unemployment_share(session, [sample_row()])

    assert summary.observations_created == 0
    assert summary.observations_unchanged == 1
    assert session.added == []
    assert session.committed is True


def test_import_rolls_back_when_existing_value_conflicts() -> None:
    source = FakeModel(id=10)
    variable = FakeModel(
        id=20,
        code="registered_unemployed_working_age_share",
        name="Udział zarejestrowanych bezrobotnych w ludności w wieku produkcyjnym",
        source="GUS/BDL",
        unit="percent",
        description="GUS/BDL P2670; values are percentage points.",
    )
    region = FakeModel(id=1, teryt_code="0201011")
    existing = FakeModel(
        region_id=1,
        variable_id=20,
        year=2014,
        value=Decimal("9.9"),
        source_id=10,
        source_note=f"raw_sha256={TEST_HASH}",
    )
    session = FakeSession(
        scalar_results=[source, variable],
        scalars_results=[[region], [existing]],
    )

    with pytest.raises(ValueError, match="conflicting socioeconomic observation"):
        import_registered_unemployment_share(session, [sample_row()])

    assert session.rolled_back is True
    assert session.committed is False


def test_import_rolls_back_for_unknown_region() -> None:
    session = FakeSession(
        scalar_results=[None, None],
        scalars_results=[[], []],
    )

    with pytest.raises(ValueError, match="Import regions first"):
        import_registered_unemployment_share(session, [sample_row()])

    assert session.rolled_back is True
