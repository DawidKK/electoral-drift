import csv
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

RESULT_COLUMNS = (
    "election_date",
    "election_type",
    "round",
    "description",
    "teryt_code",
    "committee_name",
    "bloc_name",
    "votes",
    "vote_share",
    "turnout",
    "eligible_voters",
    "valid_votes",
)
REGION_COLUMNS = (
    "teryt_code",
    "name",
    "region_type",
    "voivodeship",
    "valid_from",
    "valid_to",
)
PERCENT_QUANTUM = Decimal("0.0001")


@dataclass(frozen=True)
class CommitteeMapping:
    """Canonical committee label and analytical bloc for one PKW source label."""

    committee_name: str
    bloc_name: str


@dataclass(frozen=True)
class MunicipalityTotals:
    """Validated election totals for one municipality."""

    election_date: str
    election_type: str
    round: str
    source_teryt: str
    teryt_code: str
    name: str
    voivodeship: str
    eligible_voters: int
    ballots_issued: int
    valid_votes: int


@dataclass(frozen=True)
class SejmProcessedSummary:
    """Counts and paths produced by an interim-to-processed batch."""

    elections_processed: int
    results_written: int
    regions_written: int
    result_paths: tuple[Path, ...]
    regions_path: Path


@dataclass(frozen=True)
class TercMunicipality:
    """Historical TERC identity used for one PKW municipality code."""

    source_teryt: str
    teryt_code: str
    name: str
    voivodeship: str


def _mapping(committee_name: str, bloc_name: str) -> CommitteeMapping:
    return CommitteeMapping(committee_name, bloc_name)


COMMITTEE_MAPPINGS = {
    # 2015
    "1 - Komitet Wyborczy Prawo i Sprawiedliwość": _mapping("Prawo i Sprawiedliwość", "pis_bloc"),
    "2 - Komitet Wyborczy Platforma Obywatelska RP": _mapping("Platforma Obywatelska", "ko_bloc"),
    "3 - Komitet Wyborczy Partia Razem": _mapping("Partia Razem", "left_bloc"),
    "4 - Komitet Wyborczy KORWiN": _mapping("KORWiN", "confederation_bloc"),
    "5 - Komitet Wyborczy Polskie Stronnictwo Ludowe": _mapping(
        "Polskie Stronnictwo Ludowe", "psl_td_bloc"
    ),
    "6 - Koalicyjny Komitet Wyborczy Zjednoczona Lewica SLD+TR+PPS+UP+Zieloni": _mapping(
        "Zjednoczona Lewica", "left_bloc"
    ),
    "7 - Komitet Wyborczy Wyborców „Kukiz'15”": _mapping("Kukiz'15", "other"),
    "8 - Komitet Wyborczy Nowoczesna Ryszarda Petru": _mapping("Nowoczesna", "ko_bloc"),
    "9 - Komitet Wyborczy Wyborców JOW Bezpartyjni": _mapping("JOW Bezpartyjni", "other"),
    "10 - Komitet Wyborczy Wyborców Zbigniewa Stonogi": _mapping(
        "Komitet Zbigniewa Stonogi", "other"
    ),
    "11 - Komitet Wyborczy Wyborców  Ruch Społeczny Rzeczypospolitej Polskiej": _mapping(
        "Ruch Społeczny Rzeczypospolitej Polskiej", "other"
    ),
    "12 - Komitet Wyborczy Wyborców Zjednoczeni dla Śląska": _mapping(
        "Zjednoczeni dla Śląska", "other"
    ),
    "13 - Komitet Wyborczy Samoobrona": _mapping("Samoobrona", "other"),
    "14 - Komitet Wyborczy Wyborców Grzegorza Brauna „Szczęść Boże!”": _mapping(
        "Grzegorz Braun „Szczęść Boże!”", "other"
    ),
    "15 - Komitet Wyborczy Kongres Nowej Prawicy": _mapping("Kongres Nowej Prawicy", "other"),
    "16 - Komitet Wyborczy Wyborców Mniejszość Niemiecka": _mapping(
        "Mniejszość Niemiecka", "other"
    ),
    "16 - Komitet Wyborczy Wyborców Obywatele do Parlamentu": _mapping(
        "Obywatele do Parlamentu", "other"
    ),
    # 2019
    (
        "KOALICYJNY KOMITET WYBORCZY KOALICJA OBYWATELSKA PO .N IPL ZIELONI - ZPOW-601-6/19"
    ): _mapping("Koalicja Obywatelska", "ko_bloc"),
    "KOMITET WYBORCZY AKCJA ZAWIEDZIONYCH EMERYTÓW RENCISTÓW - ZPOW-601-21/19": _mapping(
        "Akcja Zawiedzionych Emerytów Rencistów", "other"
    ),
    ("KOMITET WYBORCZY KONFEDERACJA WOLNOŚĆ I NIEPODLEGŁOŚĆ - ZPOW-601-5/19"): _mapping(
        "Konfederacja Wolność i Niepodległość", "confederation_bloc"
    ),
    "KOMITET WYBORCZY POLSKIE STRONNICTWO LUDOWE - ZPOW-601-19/19": _mapping(
        "Polskie Stronnictwo Ludowe", "psl_td_bloc"
    ),
    "KOMITET WYBORCZY PRAWICA - ZPOW-601-20/19": _mapping("Prawica", "other"),
    "KOMITET WYBORCZY PRAWO I SPRAWIEDLIWOŚĆ - ZPOW-601-9/19": _mapping(
        "Prawo i Sprawiedliwość", "pis_bloc"
    ),
    ("KOMITET WYBORCZY SKUTECZNI PIOTRA LIROYA-MARCA - ZPOW-601-17/19"): _mapping(
        "Skuteczni Piotra Liroya-Marca", "other"
    ),
    "KOMITET WYBORCZY SOJUSZ LEWICY DEMOKRATYCZNEJ - ZPOW-601-1/19": _mapping(
        "Sojusz Lewicy Demokratycznej", "left_bloc"
    ),
    ("KOMITET WYBORCZY WYBORCÓW KOALICJA BEZPARTYJNI I SAMORZĄDOWCY - ZPOW-601-10/19"): _mapping(
        "Koalicja Bezpartyjni i Samorządowcy", "other"
    ),
    ("KOMITET WYBORCZY WYBORCÓW MNIEJSZOŚĆ NIEMIECKA - ZPOW-601-15/19"): _mapping(
        "Mniejszość Niemiecka", "other"
    ),
    # 2023
    "KOMITET WYBORCZY BEZPARTYJNI SAMORZĄDOWCY": _mapping("Bezpartyjni Samorządowcy", "other"),
    (
        "KOALICYJNY KOMITET WYBORCZY TRZECIA DROGA POLSKA 2050 SZYMONA HOŁOWNI "
        "- POLSKIE STRONNICTWO LUDOWE"
    ): _mapping("Trzecia Droga", "psl_td_bloc"),
    "KOMITET WYBORCZY NOWA LEWICA": _mapping("Nowa Lewica", "left_bloc"),
    "KOMITET WYBORCZY PRAWO I SPRAWIEDLIWOŚĆ": _mapping("Prawo i Sprawiedliwość", "pis_bloc"),
    "KOMITET WYBORCZY KONFEDERACJA WOLNOŚĆ I NIEPODLEGŁOŚĆ": _mapping(
        "Konfederacja Wolność i Niepodległość", "confederation_bloc"
    ),
    "KOALICYJNY KOMITET WYBORCZY KOALICJA OBYWATELSKA PO .N IPL ZIELONI": _mapping(
        "Koalicja Obywatelska", "ko_bloc"
    ),
    "KOMITET WYBORCZY POLSKA JEST JEDNA": _mapping("Polska Jest Jedna", "other"),
    "KOMITET WYBORCZY WYBORCÓW RUCHU DOBROBYTU I POKOJU": _mapping(
        "Ruch Dobrobytu i Pokoju", "other"
    ),
    "KOMITET WYBORCZY NORMALNY KRAJ": _mapping("Normalny Kraj", "other"),
    "KOMITET WYBORCZY ANTYPARTIA": _mapping("Antypartia", "other"),
    "KOMITET WYBORCZY RUCH NAPRAWY POLSKI": _mapping("Ruch Naprawy Polski", "other"),
    "KOMITET WYBORCZY WYBORCÓW MNIEJSZOŚĆ NIEMIECKA": _mapping("Mniejszość Niemiecka", "other"),
}


def transform_sejm_interim_to_processed(
    interim_dir: Path, output_dir: Path, terc_dir: Path
) -> SejmProcessedSummary:
    """Build importer-ready election and region CSVs from all Sejm interim pairs."""

    totals_paths = sorted(interim_dir.glob("*-sejm-gmina-totals.csv"))
    if not totals_paths:
        raise ValueError(f"No Sejm municipality totals found in {interim_dir}.")

    result_batches: list[tuple[int, Path, list[dict[str, str]]]] = []
    latest_regions: dict[str, tuple[int, dict[str, str]]] = {}

    # Validate and materialize the entire batch before creating any output files.
    for totals_path in totals_paths:
        year = _year_from_path(totals_path)
        committee_results_path = interim_dir / f"{year}-sejm-committee-results.csv"
        if not committee_results_path.exists():
            raise ValueError(f"Missing committee results file: {committee_results_path}.")

        totals = _load_totals(totals_path)
        terc = _load_terc(terc_dir / f"{year}-01-01.csv", year)
        totals = _apply_terc(totals, terc, year)
        processed_rows = _build_processed_rows(year, totals, committee_results_path)
        result_batches.append((year, output_dir / f"{year}-sejm-gminy.csv", processed_rows))
        _update_latest_regions(latest_regions, year, totals.values())

    region_rows = [
        region
        for _, region in sorted(latest_regions.values(), key=lambda item: item[1]["teryt_code"])
    ]

    output_dir.mkdir(parents=True, exist_ok=True)
    for _, path, rows in result_batches:
        _write_csv(path, RESULT_COLUMNS, rows)
    regions_path = output_dir / "regions.csv"
    _write_csv(regions_path, REGION_COLUMNS, region_rows)

    return SejmProcessedSummary(
        elections_processed=len(result_batches),
        results_written=sum(len(rows) for _, _, rows in result_batches),
        regions_written=len(region_rows),
        result_paths=tuple(path for _, path, _ in result_batches),
        regions_path=regions_path,
    )


def _year_from_path(path: Path) -> int:
    match = re.match(r"(\d{4})-sejm-", path.name)
    if match is None:
        raise ValueError(f"Cannot determine election year from {path.name}.")
    return int(match.group(1))


def _load_totals(path: Path) -> dict[tuple[str, str], MunicipalityTotals]:
    totals: dict[tuple[str, str], MunicipalityTotals] = {}
    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _require_columns(
            reader.fieldnames,
            {
                "election_date",
                "election_type",
                "round",
                "source_teryt",
                "gmina_name",
                "voivodeship",
                "eligible_voters",
                "ballots_issued",
                "valid_votes",
            },
            path,
        )
        for row_number, row in enumerate(reader, 2):
            key = (row["election_date"], row["source_teryt"])
            if key in totals:
                raise ValueError(f"{path}:{row_number}: duplicate municipality totals for {key}.")
            totals[key] = MunicipalityTotals(
                election_date=row["election_date"],
                election_type=row["election_type"],
                round=row["round"],
                source_teryt=row["source_teryt"],
                teryt_code=row["source_teryt"],
                name=_normalize_municipality_name(row["gmina_name"]),
                voivodeship=row["voivodeship"],
                eligible_voters=_non_negative_int(row["eligible_voters"], path, row_number),
                ballots_issued=_non_negative_int(row["ballots_issued"], path, row_number),
                valid_votes=_non_negative_int(row["valid_votes"], path, row_number),
            )
    return totals


def _load_terc(path: Path, year: int) -> dict[str, TercMunicipality]:
    if not path.exists():
        raise ValueError(f"Missing historical TERC file for {year}: {path}.")

    with path.open(newline="", encoding="utf-8-sig") as csv_file:
        reader = csv.DictReader(csv_file, delimiter=";")
        _require_columns(
            reader.fieldnames,
            {"WOJ", "POW", "GMI", "RODZ", "NAZWA", "NAZWA_DOD", "STAN_NA"},
            path,
        )
        rows = list(reader)

    voivodeships = {
        row["WOJ"]: row["NAZWA"].lower()
        for row in rows
        if row["WOJ"] and not row["POW"] and not row["GMI"]
    }
    municipalities: dict[str, TercMunicipality] = {}
    for row_number, row in enumerate(rows, 2):
        if not row["GMI"] or row["RODZ"] not in REGION_TYPES:
            continue
        if not row["STAN_NA"].startswith(str(year)):
            raise ValueError(f"{path}:{row_number}: TERC snapshot does not match {year}.")

        source_teryt = f"{row['WOJ']}{row['POW']}{row['GMI']}"
        if source_teryt in municipalities:
            raise ValueError(f"{path}:{row_number}: duplicate TERC municipality {source_teryt}.")
        municipalities[source_teryt] = TercMunicipality(
            source_teryt=source_teryt,
            teryt_code=f"{source_teryt}{row['RODZ']}",
            name=row["NAZWA"],
            voivodeship=voivodeships.get(row["WOJ"], ""),
        )
    return municipalities


REGION_TYPES = {
    "1": "urban_municipality",
    "2": "rural_municipality",
    "3": "urban_rural_municipality",
    "8": "warsaw_district",
    "9": "city_delegation",
}


def _apply_terc(
    totals: dict[tuple[str, str], MunicipalityTotals],
    terc: dict[str, TercMunicipality],
    year: int,
) -> dict[tuple[str, str], MunicipalityTotals]:
    enriched: dict[tuple[str, str], MunicipalityTotals] = {}
    for key, municipality in totals.items():
        reference = terc.get(municipality.source_teryt)
        if reference is None:
            raise ValueError(
                f"Municipality {municipality.source_teryt} is missing from TERC {year}."
            )
        enriched[key] = MunicipalityTotals(
            election_date=municipality.election_date,
            election_type=municipality.election_type,
            round=municipality.round,
            source_teryt=municipality.source_teryt,
            teryt_code=reference.teryt_code,
            name=reference.name,
            voivodeship=reference.voivodeship,
            eligible_voters=municipality.eligible_voters,
            ballots_issued=municipality.ballots_issued,
            valid_votes=municipality.valid_votes,
        )
    return enriched


def _build_processed_rows(
    year: int,
    totals: dict[tuple[str, str], MunicipalityTotals],
    committee_results_path: Path,
) -> list[dict[str, str]]:
    processed_rows: list[dict[str, str]] = []
    vote_sums: dict[tuple[str, str], int] = {}
    processed_keys: set[tuple[str, str, str]] = set()

    with committee_results_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _require_columns(
            reader.fieldnames,
            {
                "election_date",
                "source_teryt",
                "committee_source_name",
                "votes",
            },
            committee_results_path,
        )
        for row_number, row in enumerate(reader, 2):
            totals_key = (row["election_date"], row["source_teryt"])
            municipality = totals.get(totals_key)
            if municipality is None:
                raise ValueError(
                    f"{committee_results_path}:{row_number}: no municipality totals for "
                    f"{totals_key}."
                )

            source_name = row["committee_source_name"]
            mapping = COMMITTEE_MAPPINGS.get(source_name)
            if mapping is None:
                raise ValueError(
                    f"{committee_results_path}:{row_number}: Unknown committee: {source_name}."
                )

            votes = _non_negative_int(row["votes"], committee_results_path, row_number)
            if votes > municipality.valid_votes:
                raise ValueError(
                    f"{committee_results_path}:{row_number}: votes exceed valid votes."
                )
            result_key = (
                municipality.election_date,
                municipality.teryt_code,
                mapping.committee_name,
            )
            if result_key in processed_keys:
                raise ValueError(
                    f"{committee_results_path}:{row_number}: duplicate processed result "
                    f"for {result_key}."
                )
            processed_keys.add(result_key)
            vote_sums[totals_key] = vote_sums.get(totals_key, 0) + votes
            processed_rows.append(_processed_row(year, municipality, mapping, votes))

    for totals_key, municipality in totals.items():
        actual_votes = vote_sums.get(totals_key, 0)
        if actual_votes != municipality.valid_votes:
            raise ValueError(
                f"Committee votes for {totals_key} sum to {actual_votes}, "
                f"expected {municipality.valid_votes}."
            )

    return processed_rows


def _processed_row(
    year: int,
    municipality: MunicipalityTotals,
    mapping: CommitteeMapping,
    votes: int,
) -> dict[str, str]:
    return {
        "election_date": municipality.election_date,
        "election_type": municipality.election_type,
        "round": municipality.round,
        "description": f"Sejm {year}",
        "teryt_code": municipality.teryt_code,
        "committee_name": mapping.committee_name,
        "bloc_name": mapping.bloc_name,
        "votes": str(votes),
        "vote_share": _percentage(votes, municipality.valid_votes),
        "turnout": _percentage(municipality.ballots_issued, municipality.eligible_voters),
        "eligible_voters": str(municipality.eligible_voters),
        "valid_votes": str(municipality.valid_votes),
    }


def _percentage(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return ""
    percentage = (Decimal(numerator) * 100 / Decimal(denominator)).quantize(
        PERCENT_QUANTUM, rounding=ROUND_HALF_UP
    )
    if percentage < 0 or percentage > 100:
        raise ValueError(f"Percentage outside 0-100 range: {percentage}.")
    return f"{percentage:.4f}"


def _update_latest_regions(
    latest_regions: dict[str, tuple[int, dict[str, str]]],
    year: int,
    totals: Iterable[MunicipalityTotals],
) -> None:
    for municipality in totals:
        current = latest_regions.get(municipality.teryt_code)
        if current is not None and current[0] > year:
            continue
        latest_regions[municipality.teryt_code] = (
            year,
            {
                "teryt_code": municipality.teryt_code,
                "name": municipality.name,
                "region_type": _region_type_from_teryt(municipality.teryt_code),
                "voivodeship": municipality.voivodeship,
                "valid_from": "",
                "valid_to": "",
            },
        )


def _region_type_from_teryt(teryt_code: str) -> str:
    return REGION_TYPES[teryt_code[-1]]


def _normalize_municipality_name(name: str) -> str:
    return re.sub(r"^(?:m\.|gm\.)\s+", "", name).strip()


def _non_negative_int(value: str, path: Path, row_number: int) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{path}:{row_number}: expected an integer, got {value!r}.") from exc
    if parsed < 0:
        raise ValueError(f"{path}:{row_number}: expected a non-negative integer.")
    return parsed


def _require_columns(fieldnames: list[str] | None, required: set[str], path: Path) -> None:
    if fieldnames is None:
        raise ValueError(f"{path} is empty or has no header row.")
    missing = required.difference(fieldnames)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}.")


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
