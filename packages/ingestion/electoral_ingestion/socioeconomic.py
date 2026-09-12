import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from electoral_db.models import DataSource, Region, SocioeconomicObservation, SocioeconomicVariable
from sqlalchemy import select
from sqlalchemy.orm import Session

VARIABLE_CODE = "registered_unemployed_working_age_share"
VARIABLE_NAME = "Udział zarejestrowanych bezrobotnych w ludności w wieku produkcyjnym"
VARIABLE_SOURCE = "GUS/BDL"
VARIABLE_UNIT = "percent"
VARIABLE_DESCRIPTION = "GUS/BDL P2670; values are percentage points."
SOURCE_NAME = "GUS/BDL P2670"
SOURCE_URL = "https://bdl.stat.gov.pl/bdl/metadane/metryka/2670"
SOURCE_DOWNLOADED_AT = datetime(2026, 9, 12)
REQUIRED_COLUMNS = {"teryt_code", "year", "value", "source_file_sha256"}


@dataclass(frozen=True)
class SocioeconomicObservationInput:
    """One validated importer-ready socioeconomic observation."""

    teryt_code: str
    year: int
    value: Decimal
    source_file_sha256: str


@dataclass(frozen=True)
class SocioeconomicImportSummary:
    """Objects created or left unchanged by one atomic P2670 import."""

    variable_created: bool
    source_created: bool
    observations_created: int
    observations_unchanged: int


def load_socioeconomic_observations_csv(path: Path) -> list[SocioeconomicObservationInput]:
    """Load the stable processed P2670 CSV contract."""

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _require_columns(reader.fieldnames, path)
        rows = [
            normalize_socioeconomic_observation(row, index) for index, row in enumerate(reader, 2)
        ]

    keys = [(row.teryt_code, row.year) for row in rows]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{path} contains duplicate socioeconomic observations.")
    return rows


def normalize_socioeconomic_observation(
    row: dict[str, str | None], row_number: int
) -> SocioeconomicObservationInput:
    """Convert one processed row without losing TERC zeroes or decimal precision."""

    teryt_code = _required_text(row, "teryt_code", row_number)
    if len(teryt_code) != 7 or not teryt_code.isdigit():
        raise ValueError(f"Row {row_number}: teryt_code must contain exactly 7 digits.")
    year = _required_int(row, "year", row_number)
    value = _required_decimal(row, "value", row_number)
    if value < 0 or value > 100:
        raise ValueError(f"Row {row_number}: value must be between 0 and 100.")
    source_hash = _required_text(row, "source_file_sha256", row_number)
    if len(source_hash) != 64 or any(
        character not in "0123456789abcdef" for character in source_hash
    ):
        raise ValueError(f"Row {row_number}: source_file_sha256 must be a SHA-256 digest.")
    return SocioeconomicObservationInput(
        teryt_code=teryt_code,
        year=year,
        value=value,
        source_file_sha256=source_hash,
    )


def import_registered_unemployment_share(
    session: Session, rows: Iterable[SocioeconomicObservationInput]
) -> SocioeconomicImportSummary:
    """Import P2670 facts atomically, rejecting unknown regions and source revisions."""

    inputs = list(rows)
    try:
        source_hash = _one_source_hash(inputs)
        source, source_created = _get_or_create_source(session, source_hash)
        variable, variable_created = _get_or_create_variable(session)

        # Resolve all references in two queries; the production batch contains almost 30k rows.
        teryt_codes = {row.teryt_code for row in inputs}
        regions = session.scalars(select(Region).where(Region.teryt_code.in_(teryt_codes))).all()
        regions_by_code = {region.teryt_code: region for region in regions}
        missing_codes = sorted(teryt_codes.difference(regions_by_code))
        if missing_codes:
            preview = ", ".join(missing_codes[:5])
            raise ValueError(f"Unknown regions: {preview}. Import regions first.")

        region_ids = {region.id for region in regions}
        years = {row.year for row in inputs}
        existing_rows = session.scalars(
            select(SocioeconomicObservation).where(
                SocioeconomicObservation.variable_id == variable.id,
                SocioeconomicObservation.region_id.in_(region_ids),
                SocioeconomicObservation.year.in_(years),
            )
        ).all()
        existing_by_key = {(row.region_id, row.year): row for row in existing_rows}

        created = 0
        unchanged = 0
        source_note = f"raw_sha256={source_hash}"
        seen: set[tuple[str, int]] = set()
        for row in inputs:
            input_key = (row.teryt_code, row.year)
            if input_key in seen:
                raise ValueError(f"Duplicate socioeconomic observation: {input_key}.")
            seen.add(input_key)

            region = regions_by_code[row.teryt_code]
            existing = existing_by_key.get((region.id, row.year))
            if existing is None:
                session.add(
                    SocioeconomicObservation(
                        region_id=region.id,
                        variable_id=variable.id,
                        year=row.year,
                        value=row.value,
                        source_id=source.id,
                        source_note=source_note,
                    )
                )
                created += 1
                continue
            if (
                existing.value == row.value
                and existing.source_id == source.id
                and existing.source_note == source_note
            ):
                unchanged += 1
                continue
            raise ValueError(
                f"Found conflicting socioeconomic observation for {row.teryt_code} in {row.year}."
            )

        session.commit()
    except Exception:
        session.rollback()
        raise

    return SocioeconomicImportSummary(
        variable_created=variable_created,
        source_created=source_created,
        observations_created=created,
        observations_unchanged=unchanged,
    )


def _get_or_create_source(session: Session, source_hash: str) -> tuple[DataSource, bool]:
    description = f"GUS/BDL P2670; raw_sha256={source_hash}"
    source = session.scalar(
        select(DataSource).where(
            DataSource.source_name == SOURCE_NAME,
            DataSource.source_url == SOURCE_URL,
            DataSource.downloaded_at == SOURCE_DOWNLOADED_AT,
            DataSource.description == description,
        )
    )
    if source is not None:
        return source, False
    source = DataSource(
        source_name=SOURCE_NAME,
        source_url=SOURCE_URL,
        downloaded_at=SOURCE_DOWNLOADED_AT,
        description=description,
    )
    session.add(source)
    session.flush()
    return source, True


def _get_or_create_variable(session: Session) -> tuple[SocioeconomicVariable, bool]:
    variable = session.scalar(
        select(SocioeconomicVariable).where(SocioeconomicVariable.code == VARIABLE_CODE)
    )
    if variable is None:
        variable = SocioeconomicVariable(
            code=VARIABLE_CODE,
            name=VARIABLE_NAME,
            source=VARIABLE_SOURCE,
            unit=VARIABLE_UNIT,
            description=VARIABLE_DESCRIPTION,
        )
        session.add(variable)
        session.flush()
        return variable, True
    if (
        variable.name != VARIABLE_NAME
        or variable.source != VARIABLE_SOURCE
        or variable.unit != VARIABLE_UNIT
        or variable.description != VARIABLE_DESCRIPTION
    ):
        raise ValueError(f"Socioeconomic variable {VARIABLE_CODE} has conflicting metadata.")
    return variable, False


def _one_source_hash(rows: list[SocioeconomicObservationInput]) -> str:
    if not rows:
        raise ValueError("No socioeconomic observations supplied.")
    hashes = {row.source_file_sha256 for row in rows}
    if len(hashes) != 1:
        raise ValueError("One import batch must contain exactly one source file SHA-256.")
    return hashes.pop()


def _require_columns(fieldnames: list[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise ValueError(f"{path} is empty or has no header row.")
    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}.")


def _required_text(row: dict[str, str | None], field: str, row_number: int) -> str:
    value = row.get(field)
    stripped = value.strip() if value else ""
    if not stripped:
        raise ValueError(f"Row {row_number}: {field} is required.")
    return stripped


def _required_int(row: dict[str, str | None], field: str, row_number: int) -> int:
    value = _required_text(row, field, row_number)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: {field} must be an integer.") from exc


def _required_decimal(row: dict[str, str | None], field: str, row_number: int) -> Decimal:
    value = _required_text(row, field, row_number)
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Row {row_number}: {field} must be a decimal number.") from exc
