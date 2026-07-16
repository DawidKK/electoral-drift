from electoral_db.models import Committee, Election, ElectionResult, PoliticalBloc, Region
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_elections(session: Session) -> list[Election]:
    # Election rows are sorted newest first because users usually inspect recent results first.
    statement = select(Election).order_by(Election.election_date.desc(), Election.round.desc())
    return list(session.scalars(statement).all())


def list_region_elections(session: Session, teryt_code: str) -> list[Election]:
    statement = (
        select(Election)
        .join(ElectionResult, ElectionResult.election_id == Election.id)
        .join(Region, Region.id == ElectionResult.region_id)
        .where(Region.teryt_code == teryt_code)
        .distinct()
        .order_by(Election.election_date.desc(), Election.round.desc())
    )
    return list(session.scalars(statement).all())


def list_election_results(session: Session, election_id: int) -> list[dict[str, object]]:
    # The API response combines fact rows with region, committee, and bloc labels.
    statement = (
        select(
            Region.id.label("region_id"),
            Region.teryt_code,
            Region.name.label("region_name"),
            Committee.id.label("committee_id"),
            Committee.name.label("committee_name"),
            PoliticalBloc.name.label("bloc_name"),
            ElectionResult.votes,
            ElectionResult.vote_share,
            ElectionResult.turnout,
            ElectionResult.eligible_voters,
            ElectionResult.valid_votes,
        )
        .join(Region, Region.id == ElectionResult.region_id)
        .join(Committee, Committee.id == ElectionResult.committee_id)
        .outerjoin(PoliticalBloc, PoliticalBloc.id == ElectionResult.bloc_id)
        .where(ElectionResult.election_id == election_id)
        .order_by(Region.teryt_code, Committee.name)
    )
    return [dict(row._mapping) for row in session.execute(statement).all()]
