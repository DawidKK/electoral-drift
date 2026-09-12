import csv
from dataclasses import dataclass
from pathlib import Path

REGION_TYPES = {
    "1": "urban_municipality",
    "2": "rural_municipality",
    "3": "urban_rural_municipality",
    "8": "warsaw_district",
    "9": "city_delegation",
}
WHOLE_MUNICIPALITY_TYPES = frozenset({"1", "2", "3"})
SUPPORTED_REGION_TYPES = frozenset(REGION_TYPES)
REQUIRED_TERC_COLUMNS = {"WOJ", "POW", "GMI", "RODZ", "NAZWA", "NAZWA_DOD", "STAN_NA"}


@dataclass(frozen=True)
class TercRegion:
    """One territorial identity from an exact historical TERC snapshot."""

    teryt_code: str
    name: str
    region_type: str
    voivodeship: str
    snapshot_date: str


def load_terc_snapshot(
    path: Path,
    expected_date: str,
    *,
    allowed_types: frozenset[str] = SUPPORTED_REGION_TYPES,
) -> dict[str, TercRegion]:
    """Load supported regions after verifying the snapshot's exact effective date."""

    if not path.exists():
        raise ValueError(f"Missing historical TERC snapshot for {expected_date}: {path}.")

    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        _require_columns(reader.fieldnames, path)
        rows = list(reader)

    for row_number, row in enumerate(rows, 2):
        if row["STAN_NA"] != expected_date:
            raise ValueError(
                f"{path}:{row_number}: expected TERC STAN_NA {expected_date}, "
                f"got {row['STAN_NA']!r}."
            )

    voivodeships = {
        row["WOJ"]: row["NAZWA"].lower()
        for row in rows
        if row["WOJ"] and not row["POW"] and not row["GMI"]
    }
    regions: dict[str, TercRegion] = {}
    for row_number, row in enumerate(rows, 2):
        if not row["GMI"] or row["RODZ"] not in allowed_types:
            continue

        teryt_code = f"{row['WOJ']}{row['POW']}{row['GMI']}{row['RODZ']}"
        if len(teryt_code) != 7 or not teryt_code.isdigit():
            raise ValueError(f"{path}:{row_number}: invalid full TERC code {teryt_code!r}.")
        if teryt_code in regions:
            raise ValueError(f"{path}:{row_number}: duplicate TERC region {teryt_code}.")

        regions[teryt_code] = TercRegion(
            teryt_code=teryt_code,
            name=row["NAZWA"],
            region_type=REGION_TYPES[row["RODZ"]],
            voivodeship=voivodeships.get(row["WOJ"], ""),
            snapshot_date=expected_date,
        )
    return regions


def _require_columns(fieldnames: list[str] | None, path: Path) -> None:
    if fieldnames is None:
        raise ValueError(f"{path} is empty or has no header row.")
    missing = REQUIRED_TERC_COLUMNS.difference(fieldnames)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}.")
