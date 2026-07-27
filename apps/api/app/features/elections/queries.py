from electoral_db.models import Committee, Election, ElectionResult, PoliticalBloc, Region
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.elections.schemas import ElectionRead, ElectionResultRead


class ElectionQueries:
    """Read election data and map persistence rows to the election feature's DTOs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_elections(self) -> list[ElectionRead]:
        # Keep ordering in the query so every API consumer sees the same deterministic catalogue,
        # with the elections users are most likely to inspect shown first.
        statement = select(Election).order_by(
            Election.election_date.desc(),
            Election.round.desc(),
        )
        elections = self._session.scalars(statement).all()

        # Convert ORM entities at the persistence boundary. Routers and response handling therefore
        # operate on feature-owned DTOs and never receive SQLAlchemy models.
        return [
            ElectionRead(
                id=election.id,
                election_date=election.election_date,
                election_year=election.election_year,
                election_type=election.election_type,
                round=election.round,
                description=election.description,
            )
            for election in elections
        ]

    def list_results(self, election_id: int) -> list[ElectionResultRead]:
        # Join dictionary tables here because the public response needs stable labels in addition
        # to the election-result fact. Political-bloc membership remains optional.
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
        rows = self._session.execute(statement).mappings().all()

        # Validate database mappings before they cross the feature boundary, making response-shape
        # assumptions explicit and keeping untyped Row objects out of the HTTP layer.
        return [ElectionResultRead.model_validate(row) for row in rows]
