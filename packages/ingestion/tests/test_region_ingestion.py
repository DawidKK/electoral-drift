from datetime import date

import pytest
from electoral_ingestion.regions import (
    RegionInput,
    import_regions,
    load_regions_csv,
    normalize_region_row,
)


class ExistingRegion:
    def __init__(
        self,
        teryt_code: str = "0264011",
        name: str = "Wroclaw",
        region_type: str = "city_county",
        voivodeship: str | None = "dolnoslaskie",
        valid_from: date | None = None,
        valid_to: date | None = None,
    ) -> None:
        self.teryt_code = teryt_code
        self.name = name
        self.region_type = region_type
        self.voivodeship = voivodeship
        self.valid_from = valid_from
        self.valid_to = valid_to


class FakeSession:
    """Tiny in-memory stand-in for SQLAlchemy Session used by importer unit tests."""

    def __init__(self, existing: ExistingRegion | None = None) -> None:
        self.existing = existing
        self.added: list[object] = []
        self.committed = False

    def scalar(self, statement: object) -> ExistingRegion | None:
        return self.existing

    def add(self, model: object) -> None:
        self.added.append(model)

    def commit(self) -> None:
        self.committed = True


def test_normalize_region_row_preserves_leading_zeroes() -> None:
    region = normalize_region_row(
        {
            "teryt_code": "0264011",
            "name": "Wroclaw",
            "region_type": "city_county",
            "voivodeship": "dolnoslaskie",
            "valid_from": "1999-01-01",
        },
        row_number=2,
    )

    assert region.teryt_code == "0264011"
    assert region.valid_from == date(1999, 1, 1)


def test_normalize_region_row_rejects_missing_teryt() -> None:
    with pytest.raises(ValueError, match="teryt_code is required"):
        normalize_region_row({"teryt_code": "", "name": "Wroclaw", "region_type": "city"}, 2)


def test_load_regions_csv_requires_core_columns(tmp_path) -> None:
    csv_path = tmp_path / "regions.csv"
    csv_path.write_text("teryt_code,name\n0264011,Wroclaw\n", encoding="utf-8")

    with pytest.raises(ValueError, match="region_type"):
        load_regions_csv(csv_path)


def test_import_regions_creates_new_rows() -> None:
    session = FakeSession(existing=None)

    summary = import_regions(
        session,
        [
            RegionInput(
                teryt_code="0264011",
                name="Wroclaw",
                region_type="city_county",
                voivodeship="dolnoslaskie",
            )
        ],
    )

    assert summary.created == 1
    assert summary.updated == 0
    assert summary.unchanged == 0
    assert len(session.added) == 1
    assert session.committed is True


def test_import_regions_leaves_unchanged_rows_alone() -> None:
    session = FakeSession(existing=ExistingRegion())

    summary = import_regions(
        session,
        [
            RegionInput(
                teryt_code="0264011",
                name="Wroclaw",
                region_type="city_county",
                voivodeship="dolnoslaskie",
            )
        ],
    )

    assert summary.unchanged == 1
    assert session.added == []
    assert session.committed is True


def test_import_regions_updates_existing_rows() -> None:
    existing = ExistingRegion(name="Old name")
    session = FakeSession(existing=existing)

    summary = import_regions(
        session,
        [
            RegionInput(
                teryt_code="0264011",
                name="Wroclaw",
                region_type="city_county",
                voivodeship="dolnoslaskie",
            )
        ],
    )

    assert summary.updated == 1
    assert existing.name == "Wroclaw"
    assert session.committed is True
