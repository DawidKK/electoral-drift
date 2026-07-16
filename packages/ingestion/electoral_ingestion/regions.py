import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from electoral_db.models import Region
from sqlalchemy import select
from sqlalchemy.orm import Session

REQUIRED_COLUMNS = {"teryt_code", "name", "region_type"}


@dataclass(frozen=True)
class RegionInput:
    """A cleaned region row that is safe to write to core.regions."""

    teryt_code: str
    name: str
    region_type: str
    voivodeship: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True)
class RegionImportSummary:
    """Small report returned after importing a CSV file."""

    created: int
    updated: int
    unchanged: int

    @property
    def total_seen(self) -> int:
        return self.created + self.updated + self.unchanged


def load_regions_csv(path: Path) -> list[RegionInput]:
    """Read a CSV file and convert each row into a validated RegionInput.

    The CSV is expected to have at least these columns: teryt_code, name, region_type.
    Optional columns are voivodeship, valid_from, and valid_to.
    """

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_header(reader.fieldnames)
        return [normalize_region_row(row, row_number=index) for index, row in enumerate(reader, 2)]


def normalize_region_row(row: dict[str, str | None], row_number: int) -> RegionInput:
    """Validate one CSV row and preserve TERYT as text.

    TERYT identifiers can contain leading zeroes, so they must never be converted to int.
    """

    teryt_code = _required_text(row, "teryt_code", row_number)
    if not teryt_code.isdigit():
        raise ValueError(f"Row {row_number}: teryt_code must contain digits only.")

    return RegionInput(
        teryt_code=teryt_code,
        name=_required_text(row, "name", row_number),
        region_type=_required_text(row, "region_type", row_number),
        voivodeship=_optional_text(row, "voivodeship"),
        valid_from=_optional_date(row, "valid_from", row_number),
        valid_to=_optional_date(row, "valid_to", row_number),
    )


def import_regions(session: Session, regions: Iterable[RegionInput]) -> RegionImportSummary:
    """Insert or update regions by TERYT code.

    The importer is idempotent: running it twice with the same rows will not create
    duplicates because teryt_code is the natural unique key in core.regions.
    """

    created = 0
    updated = 0
    unchanged = 0

    for region_input in regions:
        existing = session.scalar(
            select(Region).where(Region.teryt_code == region_input.teryt_code)
        )
        if existing is None:
            session.add(
                Region(
                    teryt_code=region_input.teryt_code,
                    name=region_input.name,
                    region_type=region_input.region_type,
                    voivodeship=region_input.voivodeship,
                    valid_from=region_input.valid_from,
                    valid_to=region_input.valid_to,
                )
            )
            created += 1
            continue

        if _region_matches(existing, region_input):
            unchanged += 1
            continue

        existing.name = region_input.name
        existing.region_type = region_input.region_type
        existing.voivodeship = region_input.voivodeship
        existing.valid_from = region_input.valid_from
        existing.valid_to = region_input.valid_to
        updated += 1

    session.commit()
    return RegionImportSummary(created=created, updated=updated, unchanged=unchanged)


def _validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("CSV file is empty or has no header row.")

    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"CSV is missing required columns: {missing_columns}.")


def _required_text(row: dict[str, str | None], field: str, row_number: int) -> str:
    value = _optional_text(row, field)
    if value is None:
        raise ValueError(f"Row {row_number}: {field} is required.")
    return value


def _optional_text(row: dict[str, str | None], field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_date(row: dict[str, str | None], field: str, row_number: int) -> date | None:
    value = _optional_text(row, field)
    if value is None:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: {field} must use YYYY-MM-DD format.") from exc


def _region_matches(region: Region, region_input: RegionInput) -> bool:
    return (
        region.name == region_input.name
        and region.region_type == region_input.region_type
        and region.voivodeship == region_input.voivodeship
        and region.valid_from == region_input.valid_from
        and region.valid_to == region_input.valid_to
    )
