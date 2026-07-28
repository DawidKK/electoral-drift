import csv
import re
from dataclasses import dataclass
from pathlib import Path

TOTALS_COLUMNS = (
    "election_date",
    "election_type",
    "round",
    "source_teryt",
    "gmina_name",
    "powiat_name",
    "voivodeship",
    "eligible_voters",
    "ballots_issued",
    "valid_votes",
)
COMMITTEE_RESULT_COLUMNS = (
    "election_date",
    "election_type",
    "round",
    "source_teryt",
    "gmina_name",
    "committee_source_name",
    "votes",
)


@dataclass(frozen=True)
class SejmSourceSpec:
    """Columns and election metadata used by one PKW Sejm export."""

    year: int
    election_date: str
    delimiter: str
    teryt_column: str
    gmina_column: str
    powiat_column: str | None
    voivodeship_column: str | None
    eligible_voters_column: str
    ballots_issued_column: str
    valid_votes_column: str


@dataclass(frozen=True)
class SejmInterimSummary:
    """Paths and row counts produced by one raw-to-interim transformation."""

    year: int
    totals_path: Path
    committee_results_path: Path
    municipalities_written: int
    committee_results_written: int
    rows_without_teryt_skipped: int


SOURCE_SPECS = {
    2015: SejmSourceSpec(
        year=2015,
        election_date="2015-10-25",
        delimiter=",",
        teryt_column="TERYT",
        gmina_column="Gmina",
        powiat_column=None,
        voivodeship_column=None,
        eligible_voters_column="Liczba wyborców",
        ballots_issued_column="Wydane karty",
        valid_votes_column="Głosy ważne",
    ),
    2019: SejmSourceSpec(
        year=2019,
        election_date="2019-10-13",
        delimiter=";",
        teryt_column="Kod TERYT",
        gmina_column="Gmina",
        powiat_column="Powiat",
        voivodeship_column="Województwo",
        eligible_voters_column="Liczba wyborców uprawnionych do głosowania",
        ballots_issued_column="Liczba wyborców, którym wydano karty do głosowania",
        valid_votes_column=("Liczba głosów ważnych oddanych łącznie na wszystkie listy kandydatów"),
    ),
    2023: SejmSourceSpec(
        year=2023,
        election_date="2023-10-15",
        delimiter=";",
        teryt_column="TERYT Gminy",
        gmina_column="Gmina",
        powiat_column="Powiat",
        voivodeship_column="Województwo",
        eligible_voters_column="Liczba wyborców uprawnionych do głosowania",
        ballots_issued_column=(
            "Liczba wyborców, którym wydano karty do głosowania w lokalu wyborczym oraz "
            "w głosowaniu korespondencyjnym (łącznie)"
        ),
        valid_votes_column=("Liczba głosów ważnych oddanych łącznie na wszystkie listy kandydatów"),
    ),
}


def transform_sejm_raw_to_interim(raw_path: Path, output_dir: Path) -> SejmInterimSummary:
    """Normalize one supported PKW Sejm export into totals and long committee-result CSVs."""

    spec = _source_spec_for_path(raw_path)
    totals, committee_results, skipped = _read_and_normalize(raw_path, spec)

    output_dir.mkdir(parents=True, exist_ok=True)
    totals_path = output_dir / f"{raw_path.stem}-gmina-totals.csv"
    committee_results_path = output_dir / f"{raw_path.stem}-committee-results.csv"
    _write_csv(totals_path, TOTALS_COLUMNS, totals)
    _write_csv(committee_results_path, COMMITTEE_RESULT_COLUMNS, committee_results)

    return SejmInterimSummary(
        year=spec.year,
        totals_path=totals_path,
        committee_results_path=committee_results_path,
        municipalities_written=len(totals),
        committee_results_written=len(committee_results),
        rows_without_teryt_skipped=skipped,
    )


def _source_spec_for_path(raw_path: Path) -> SejmSourceSpec:
    match = re.search(r"(?<!\d)(2015|2019|2023)(?!\d)", raw_path.stem)
    if match is None:
        supported = ", ".join(str(year) for year in SOURCE_SPECS)
        raise ValueError(
            f"Cannot determine election year from {raw_path.name}. Supported years: {supported}."
        )
    return SOURCE_SPECS[int(match.group())]


def _read_and_normalize(
    raw_path: Path, spec: SejmSourceSpec
) -> tuple[list[dict[str, str]], list[dict[str, str]], int]:
    totals: list[dict[str, str]] = []
    committee_results: list[dict[str, str]] = []
    skipped = 0

    with raw_path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=spec.delimiter)
        committee_columns = _validate_and_get_committee_columns(reader.fieldnames, spec)

        for row_number, row in enumerate(reader, 2):
            source_teryt = _text(row, spec.teryt_column)
            if not source_teryt:
                skipped += 1
                continue
            if not source_teryt.isdigit() or len(source_teryt) > 6:
                raise ValueError(
                    f"Row {row_number}: {spec.teryt_column} must be at most six digits."
                )
            teryt = source_teryt.zfill(6)

            gmina_name = _required_text(row, spec.gmina_column, row_number)
            totals.append(_build_totals_row(row, row_number, spec, teryt, gmina_name))
            committee_results.extend(
                _build_committee_rows(row, row_number, spec, committee_columns, teryt, gmina_name)
            )

    return totals, committee_results, skipped


def _validate_and_get_committee_columns(
    fieldnames: list[str] | None, spec: SejmSourceSpec
) -> list[str]:
    if fieldnames is None:
        raise ValueError("Raw PKW CSV is empty or has no header row.")

    required = {
        spec.teryt_column,
        spec.gmina_column,
        spec.eligible_voters_column,
        spec.ballots_issued_column,
        spec.valid_votes_column,
    }
    required.update(
        column for column in (spec.powiat_column, spec.voivodeship_column) if column is not None
    )
    missing = required.difference(fieldnames)
    if missing:
        raise ValueError(f"Raw PKW CSV is missing columns: {', '.join(sorted(missing))}.")

    first_committee_index = fieldnames.index(spec.valid_votes_column) + 1
    committee_columns = fieldnames[first_committee_index:]
    if not committee_columns:
        raise ValueError("Raw PKW CSV has no committee result columns.")
    return committee_columns


def _build_totals_row(
    row: dict[str, str | None],
    row_number: int,
    spec: SejmSourceSpec,
    teryt: str,
    gmina_name: str,
) -> dict[str, str]:
    return {
        "election_date": spec.election_date,
        "election_type": "parliamentary",
        "round": "1",
        "source_teryt": teryt,
        "gmina_name": gmina_name,
        "powiat_name": _text(row, spec.powiat_column) if spec.powiat_column else "",
        "voivodeship": (_text(row, spec.voivodeship_column) if spec.voivodeship_column else ""),
        "eligible_voters": _required_integer(row, spec.eligible_voters_column, row_number),
        "ballots_issued": _required_integer(row, spec.ballots_issued_column, row_number),
        "valid_votes": _required_integer(row, spec.valid_votes_column, row_number),
    }


def _build_committee_rows(
    row: dict[str, str | None],
    row_number: int,
    spec: SejmSourceSpec,
    committee_columns: list[str],
    teryt: str,
    gmina_name: str,
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    for committee_name in committee_columns:
        votes = _optional_integer(row, committee_name, row_number)
        if votes is None:
            continue
        results.append(
            {
                "election_date": spec.election_date,
                "election_type": "parliamentary",
                "round": "1",
                "source_teryt": teryt,
                "gmina_name": gmina_name,
                "committee_source_name": committee_name.strip(),
                "votes": votes,
            }
        )
    return results


def _required_text(row: dict[str, str | None], column: str, row_number: int) -> str:
    value = _text(row, column)
    if not value:
        raise ValueError(f"Row {row_number}: {column} is required.")
    return value


def _text(row: dict[str, str | None], column: str | None) -> str:
    if column is None:
        return ""
    value = row.get(column)
    return value.strip() if value is not None else ""


def _required_integer(row: dict[str, str | None], column: str, row_number: int) -> str:
    value = _optional_integer(row, column, row_number)
    if value is None:
        raise ValueError(f"Row {row_number}: {column} is required.")
    return value


def _optional_integer(row: dict[str, str | None], column: str, row_number: int) -> str | None:
    value = _text(row, column)
    if not value or value == "-":
        return None

    normalized = value.replace("\u00a0", "").replace("\u202f", "").replace(" ", "")
    if not normalized.isdigit():
        raise ValueError(f"Row {row_number}: {column} must be a non-negative integer.")
    return normalized


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
