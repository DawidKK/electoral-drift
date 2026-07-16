import csv
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from electoral_db.models import Committee, Election, ElectionResult, PoliticalBloc, Region
from sqlalchemy import select
from sqlalchemy.orm import Session

REQUIRED_COLUMNS = {
    "election_date",
    "election_type",
    "round",
    "teryt_code",
    "committee_name",
    "bloc_name",
    "votes",
}


@dataclass(frozen=True)
class ElectionResultInput:
    """A cleaned CSV row describing one committee result in one region."""

    election_date: date
    election_type: str
    round: int
    teryt_code: str
    committee_name: str
    bloc_name: str
    votes: int
    description: str | None = None
    vote_share: Decimal | None = None
    turnout: Decimal | None = None
    eligible_voters: int | None = None
    valid_votes: int | None = None

    @property
    def election_year(self) -> int:
        return self.election_date.year


@dataclass(frozen=True)
class ElectionResultImportSummary:
    """Small report returned after importing election result rows."""

    elections_created: int
    committees_created: int
    results_created: int
    results_updated: int
    results_unchanged: int


def load_election_results_csv(path: Path) -> list[ElectionResultInput]:
    """Read a UTF-8 CSV file and validate each election-result row."""

    with path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        _validate_header(reader.fieldnames)
        return [normalize_election_result_row(row, index) for index, row in enumerate(reader, 2)]


def normalize_election_result_row(
    row: dict[str, str | None], row_number: int
) -> ElectionResultInput:
    """Convert one raw CSV row into typed data used by the importer."""

    teryt_code = _required_text(row, "teryt_code", row_number)
    if not teryt_code.isdigit():
        raise ValueError(f"Row {row_number}: teryt_code must contain digits only.")

    return ElectionResultInput(
        election_date=_required_date(row, "election_date", row_number),
        election_type=_required_text(row, "election_type", row_number),
        round=_required_int(row, "round", row_number),
        description=_optional_text(row, "description"),
        teryt_code=teryt_code,
        committee_name=_required_text(row, "committee_name", row_number),
        bloc_name=_required_text(row, "bloc_name", row_number),
        votes=_required_int(row, "votes", row_number),
        vote_share=_optional_decimal(row, "vote_share", row_number),
        turnout=_optional_decimal(row, "turnout", row_number),
        eligible_voters=_optional_int(row, "eligible_voters", row_number),
        valid_votes=_optional_int(row, "valid_votes", row_number),
    )


def import_election_results(
    session: Session, rows: Iterable[ElectionResultInput]
) -> ElectionResultImportSummary:
    """Insert or update elections, committees, and election results.

    The importer assumes regions and political blocs already exist. This keeps source facts
    explicit: unknown TERYT codes or bloc names fail fast instead of creating ambiguous data.
    """

    elections_created = 0
    committees_created = 0
    results_created = 0
    results_updated = 0
    results_unchanged = 0

    for row in rows:
        region = _get_required_region(session, row.teryt_code)
        bloc = _get_required_bloc(session, row.bloc_name)
        election, election_created = _get_or_create_election(session, row)
        committee, committee_created = _get_or_create_committee(session, row, election, bloc)
        result = _get_existing_result(session, region, election, committee)

        elections_created += int(election_created)
        committees_created += int(committee_created)

        if result is None:
            session.add(_build_result(row, region, election, committee, bloc))
            results_created += 1
            continue

        if _result_matches(result, row, bloc):
            results_unchanged += 1
            continue

        result.bloc_id = bloc.id
        result.votes = row.votes
        result.vote_share = row.vote_share
        result.turnout = row.turnout
        result.eligible_voters = row.eligible_voters
        result.valid_votes = row.valid_votes
        results_updated += 1

    session.commit()
    return ElectionResultImportSummary(
        elections_created=elections_created,
        committees_created=committees_created,
        results_created=results_created,
        results_updated=results_updated,
        results_unchanged=results_unchanged,
    )


def _validate_header(fieldnames: list[str] | None) -> None:
    if fieldnames is None:
        raise ValueError("CSV file is empty or has no header row.")

    missing = REQUIRED_COLUMNS.difference(fieldnames)
    if missing:
        missing_columns = ", ".join(sorted(missing))
        raise ValueError(f"CSV is missing required columns: {missing_columns}.")


def _get_required_region(session: Session, teryt_code: str) -> Region:
    region = session.scalar(select(Region).where(Region.teryt_code == teryt_code))
    if region is None:
        raise ValueError(f"Unknown region teryt_code: {teryt_code}. Import regions first.")
    return region


def _get_required_bloc(session: Session, bloc_name: str) -> PoliticalBloc:
    bloc = session.scalar(select(PoliticalBloc).where(PoliticalBloc.name == bloc_name))
    if bloc is None:
        raise ValueError(f"Unknown political bloc: {bloc_name}.")
    return bloc


def _get_or_create_election(
    session: Session, row: ElectionResultInput
) -> tuple[Election, bool]:
    election = session.scalar(
        select(Election).where(
            Election.election_date == row.election_date,
            Election.election_type == row.election_type,
            Election.round == row.round,
            Election.description == row.description,
        )
    )
    if election is not None:
        return election, False

    election = Election(
        election_date=row.election_date,
        election_year=row.election_year,
        election_type=row.election_type,
        round=row.round,
        description=row.description,
    )
    session.add(election)
    session.flush()
    return election, True


def _get_or_create_committee(
    session: Session,
    row: ElectionResultInput,
    election: Election,
    bloc: PoliticalBloc,
) -> tuple[Committee, bool]:
    committee = session.scalar(
        select(Committee).where(
            Committee.name == row.committee_name,
            Committee.election_id == election.id,
        )
    )
    if committee is not None:
        committee.bloc_id = bloc.id
        return committee, False

    committee = Committee(name=row.committee_name, election_id=election.id, bloc_id=bloc.id)
    session.add(committee)
    session.flush()
    return committee, True


def _get_existing_result(
    session: Session,
    region: Region,
    election: Election,
    committee: Committee,
) -> ElectionResult | None:
    return session.scalar(
        select(ElectionResult).where(
            ElectionResult.region_id == region.id,
            ElectionResult.election_id == election.id,
            ElectionResult.committee_id == committee.id,
        )
    )


def _build_result(
    row: ElectionResultInput,
    region: Region,
    election: Election,
    committee: Committee,
    bloc: PoliticalBloc,
) -> ElectionResult:
    return ElectionResult(
        region_id=region.id,
        election_id=election.id,
        committee_id=committee.id,
        bloc_id=bloc.id,
        votes=row.votes,
        vote_share=row.vote_share,
        turnout=row.turnout,
        eligible_voters=row.eligible_voters,
        valid_votes=row.valid_votes,
    )


def _result_matches(result: ElectionResult, row: ElectionResultInput, bloc: PoliticalBloc) -> bool:
    return (
        result.bloc_id == bloc.id
        and result.votes == row.votes
        and result.vote_share == row.vote_share
        and result.turnout == row.turnout
        and result.eligible_voters == row.eligible_voters
        and result.valid_votes == row.valid_votes
    )


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


def _required_date(row: dict[str, str | None], field: str, row_number: int) -> date:
    value = _required_text(row, field, row_number)
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: {field} must use YYYY-MM-DD format.") from exc


def _required_int(row: dict[str, str | None], field: str, row_number: int) -> int:
    value = _required_text(row, field, row_number)
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: {field} must be an integer.") from exc


def _optional_int(row: dict[str, str | None], field: str, row_number: int) -> int | None:
    value = _optional_text(row, field)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: {field} must be an integer.") from exc


def _optional_decimal(row: dict[str, str | None], field: str, row_number: int) -> Decimal | None:
    value = _optional_text(row, field)
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Row {row_number}: {field} must be a decimal number.") from exc
