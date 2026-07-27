from decimal import Decimal

from electoral_db.models import Election, ElectionResult, Region
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.features.regions.schemas import (
    RegionElectionRead,
    RegionRead,
    RegionTimelineBlocRead,
    RegionTimelineElectionRead,
    RegionTimelineRead,
)


class RegionQueries:
    """Read region data and build DTOs owned by the region feature."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_regions(self) -> list[RegionRead]:
        # TERYT order is stable across database runs and useful to clients joining API responses
        # with official territorial datasets.
        regions = self._session.scalars(select(Region).order_by(Region.teryt_code)).all()
        return [self._to_region_read(region) for region in regions]

    def get_region(self, teryt_code: str) -> RegionRead | None:
        # TERYT is the public identifier of a region. Resolve it once here and avoid exposing the
        # ORM entity to the endpoint when no matching territorial unit exists.
        region = self._find_region(teryt_code)
        return self._to_region_read(region) if region is not None else None

    def list_elections(self, teryt_code: str) -> list[RegionElectionRead]:
        # This query belongs to the region feature because it serves a region-scoped endpoint.
        # Keeping the DTO local prevents the region contract from depending on the elections module.
        statement = (
            select(Election)
            .join(ElectionResult, ElectionResult.election_id == Election.id)
            .join(Region, Region.id == ElectionResult.region_id)
            .where(Region.teryt_code == teryt_code)
            .distinct()
            .order_by(Election.election_date.desc(), Election.round.desc())
        )
        elections = self._session.scalars(statement).all()

        # Map ORM rows into a region-owned projection even though the source entity is Election.
        # This small duplication deliberately preserves feature independence.
        return [
            RegionElectionRead(
                id=election.id,
                election_date=election.election_date,
                election_year=election.election_year,
                election_type=election.election_type,
                round=election.round,
                description=election.description,
            )
            for election in elections
        ]

    def get_timeline(self, teryt_code: str) -> RegionTimelineRead | None:
        """Build a chronological, bloc-level political timeline for one region."""
        # Resolve the public identifier before querying analytics. Returning None here gives the
        # router enough context to translate a missing region into the public 404 response.
        region = self._find_region(teryt_code)
        if region is None:
            return None

        # Read the pre-aggregated analytics view rather than reconstructing bloc totals from raw
        # committee facts during an HTTP request.
        statement = text(
            """
            SELECT
                res.election_id,
                res.election_year,
                res.election_type,
                res.bloc_name,
                res.votes,
                res.vote_share
            FROM analytics.region_election_summary res
            WHERE res.region_id = :region_id
            ORDER BY res.election_year, res.election_id, res.bloc_name
            """
        )
        rows = self._session.execute(statement, {"region_id": region.id}).mappings().all()

        # Preserve the database ordering while grouping consecutive bloc rows under their election.
        # A dictionary also protects against repeating election metadata in the public response.
        elections: dict[int, RegionTimelineElectionRead] = {}
        for row in rows:
            election_id = int(row["election_id"])
            election = elections.setdefault(
                election_id,
                RegionTimelineElectionRead(
                    election_id=election_id,
                    election_year=int(row["election_year"]),
                    election_type=str(row["election_type"]),
                    blocs=[],
                ),
            )

            # Decimal values are formatted to strings to preserve the established API contract and
            # avoid binary floating-point changes in downstream visualisations.
            election.blocs.append(
                RegionTimelineBlocRead(
                    bloc_name=str(row["bloc_name"]) if row["bloc_name"] is not None else None,
                    votes=int(row["votes"]) if row["votes"] is not None else None,
                    vote_share=self._decimal_to_string(row["vote_share"]),
                )
            )

        # Convert the region entity and grouped rows before returning from the persistence boundary.
        return RegionTimelineRead(
            region=self._to_region_read(region),
            timeline=list(elections.values()),
        )

    def _find_region(self, teryt_code: str) -> Region | None:
        statement = select(Region).where(Region.teryt_code == teryt_code)
        return self._session.scalar(statement)

    @staticmethod
    def _to_region_read(region: Region) -> RegionRead:
        return RegionRead(
            id=region.id,
            teryt_code=region.teryt_code,
            name=region.name,
            region_type=region.region_type,
            voivodeship=region.voivodeship,
        )

    @staticmethod
    def _decimal_to_string(value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, Decimal):
            return f"{value:.4f}"
        return str(value)
