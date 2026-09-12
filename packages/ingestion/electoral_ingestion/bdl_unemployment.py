import csv
import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from electoral_ingestion.terc import WHOLE_MUNICIPALITY_TYPES, load_terc_snapshot

INTERIM_COLUMNS = (
    "source_teryt_code",
    "source_name",
    "year",
    "value",
    "source_file_sha256",
)
PROCESSED_COLUMNS = ("teryt_code", "year", "value", "source_file_sha256")
YEAR_HEADER = re.compile(r"ogółem;(?P<year>\d{4});\[%\]")
TERC_VALIDATION_OVERRIDES = {
    # Chełmiec appeared as urban-rural on 2018-01-01, but the change was reversed the next day.
    # BDL consistently reports the annual observation under the restored rural code.
    ("1210022", 2018): "2018-01-02",
}


@dataclass(frozen=True)
class BdlUnemploymentInterimSummary:
    """Counts produced while normalizing the wide BDL P2670 export."""

    raw_rows: int
    observations_written: int
    aggregate_rows_skipped: int
    subdivision_rows_skipped: int
    empty_values_skipped: int
    source_file_sha256: str
    output_path: Path


@dataclass(frozen=True)
class BdlUnemploymentProcessedSummary:
    """Counts produced while validating P2670 observations against historical TERC."""

    observations_written: int
    snapshots_read: int
    output_path: Path


def transform_bdl_unemployment_raw_to_interim(
    raw_path: Path, output_path: Path
) -> BdlUnemploymentInterimSummary:
    """Normalize a wide GUS/BDL P2670 CSV into source-oriented long observations."""

    source_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    with raw_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.reader(csv_file, delimiter=";")
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"{raw_path} is empty.") from exc
        year_columns = _year_columns(header, raw_path)
        rows = list(reader)

    output_rows: list[dict[str, str]] = []
    seen_codes: set[str] = set()
    seen_observations: set[tuple[str, int]] = set()
    aggregate_rows_skipped = 0
    subdivision_rows_skipped = 0
    empty_values_skipped = 0

    # Classify geography before expanding years so skipped rows are reported once.
    for row_number, row in enumerate(rows, 2):
        if len(row) != len(header):
            raise ValueError(
                f"{raw_path}:{row_number}: expected {len(header)} columns, got {len(row)}."
            )
        teryt_code = row[0].strip()
        if len(teryt_code) != 7 or not teryt_code.isdigit():
            raise ValueError(f"{raw_path}:{row_number}: invalid TERC code {teryt_code!r}.")
        if teryt_code in seen_codes:
            raise ValueError(f"{raw_path}:{row_number}: duplicate source TERC code {teryt_code}.")
        seen_codes.add(teryt_code)

        region_kind = teryt_code[-1]
        if region_kind == "0":
            aggregate_rows_skipped += 1
            continue
        if region_kind in {"4", "5"}:
            subdivision_rows_skipped += 1
            continue
        if region_kind not in WHOLE_MUNICIPALITY_TYPES:
            raise ValueError(
                f"{raw_path}:{row_number}: unsupported BDL territorial type {region_kind}."
            )

        source_name = row[1].strip()
        if not source_name:
            raise ValueError(f"{raw_path}:{row_number}: municipality name is empty.")
        for column_index, year in year_columns:
            raw_value = row[column_index].strip()
            if not raw_value:
                empty_values_skipped += 1
                continue
            value = _percentage(raw_value, raw_path, row_number)
            key = (teryt_code, year)
            if key in seen_observations:
                raise ValueError(f"{raw_path}:{row_number}: duplicate observation for {key}.")
            seen_observations.add(key)
            output_rows.append(
                {
                    "source_teryt_code": teryt_code,
                    "source_name": source_name,
                    "year": str(year),
                    "value": str(value),
                    "source_file_sha256": source_hash,
                }
            )

    _write_csv(output_path, INTERIM_COLUMNS, output_rows)
    return BdlUnemploymentInterimSummary(
        raw_rows=len(rows),
        observations_written=len(output_rows),
        aggregate_rows_skipped=aggregate_rows_skipped,
        subdivision_rows_skipped=subdivision_rows_skipped,
        empty_values_skipped=empty_values_skipped,
        source_file_sha256=source_hash,
        output_path=output_path,
    )


def transform_bdl_unemployment_interim_to_processed(
    interim_path: Path, output_path: Path, terc_dir: Path
) -> BdlUnemploymentProcessedSummary:
    """Validate long P2670 observations against the exact TERC snapshot for each year."""

    with interim_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _require_columns(reader.fieldnames, set(INTERIM_COLUMNS), interim_path)
        source_rows = list(reader)

    observations: list[dict[str, str]] = []
    seen: set[tuple[str, int]] = set()
    snapshots: dict[str, dict[str, object]] = {}
    for row_number, row in enumerate(source_rows, 2):
        teryt_code = row["source_teryt_code"]
        year = _year(row["year"], interim_path, row_number)
        key = (teryt_code, year)
        if key in seen:
            raise ValueError(f"{interim_path}:{row_number}: duplicate observation for {key}.")
        seen.add(key)

        expected_date = f"{year}-01-01"
        if expected_date not in snapshots:
            snapshots[expected_date] = load_terc_snapshot(
                terc_dir / f"{expected_date}.csv",
                expected_date,
                allowed_types=WHOLE_MUNICIPALITY_TYPES,
            )
        if teryt_code not in snapshots[expected_date]:
            override_date = TERC_VALIDATION_OVERRIDES.get(key)
            if override_date is not None:
                if override_date not in snapshots:
                    snapshots[override_date] = load_terc_snapshot(
                        terc_dir / f"{override_date}.csv",
                        override_date,
                        allowed_types=WHOLE_MUNICIPALITY_TYPES,
                    )
                if teryt_code in snapshots[override_date]:
                    expected_date = override_date
        if teryt_code not in snapshots[expected_date]:
            raise ValueError(
                f"{interim_path}:{row_number}: {teryt_code} is missing from TERC {year}-01-01."
            )

        observations.append(
            {
                "teryt_code": teryt_code,
                "year": str(year),
                "value": row["value"],
                "source_file_sha256": row["source_file_sha256"],
            }
        )

    _write_csv(output_path, PROCESSED_COLUMNS, observations)
    return BdlUnemploymentProcessedSummary(
        observations_written=len(observations),
        snapshots_read=len(snapshots),
        output_path=output_path,
    )


def _year_columns(header: list[str], path: Path) -> list[tuple[int, int]]:
    if len(header) < 3 or header[:2] != ["Kod", "Nazwa"]:
        raise ValueError(f"{path} must start with the columns Kod and Nazwa.")
    columns: list[tuple[int, int]] = []
    for index, name in enumerate(header[2:], 2):
        if not name:
            continue
        match = YEAR_HEADER.fullmatch(name)
        if match is None:
            raise ValueError(f"{path}: unsupported P2670 column {name!r}.")
        columns.append((index, int(match.group("year"))))
    years = [year for _, year in columns]
    if not years or len(years) != len(set(years)) or years != sorted(years):
        raise ValueError(f"{path}: P2670 years must be unique and ascending.")
    return columns


def _percentage(value: str, path: Path, row_number: int) -> Decimal:
    try:
        parsed = Decimal(value.replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"{path}:{row_number}: invalid percentage {value!r}.") from exc
    if parsed < 0 or parsed > 100:
        raise ValueError(f"{path}:{row_number}: percentage outside 0-100 range: {parsed}.")
    return parsed


def _year(value: str, path: Path, row_number: int) -> int:
    try:
        year = int(value)
    except ValueError as exc:
        raise ValueError(f"{path}:{row_number}: invalid year {value!r}.") from exc
    if year < 1900 or year > 2200:
        raise ValueError(f"{path}:{row_number}: year outside supported range: {year}.")
    return year


def _require_columns(fieldnames: list[str] | None, required: set[str], path: Path) -> None:
    if fieldnames is None:
        raise ValueError(f"{path} is empty or has no header row.")
    missing = required.difference(fieldnames)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}.")


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
