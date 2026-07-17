from decimal import Decimal

from electoral_db.models import Region
from sqlalchemy import select, text
from sqlalchemy.orm import Session


def list_regions(session: Session) -> list[Region]:
    # Services contain database queries so routers can stay focused on HTTP concerns.
    statement = select(Region).order_by(Region.teryt_code)
    return list(session.scalars(statement).all())


def get_region_by_teryt_code(session: Session, teryt_code: str) -> Region | None:
    statement = select(Region).where(Region.teryt_code == teryt_code)
    return session.scalar(statement)


def get_region_timeline(session: Session, teryt_code: str) -> dict[str, object] | None:
    """Build a compact political timeline for one region.

    The timeline reads from the analytics view instead of raw committee results, so each
    election is already summarized by political bloc and ready for frontend display.
    """

    region = get_region_by_teryt_code(session, teryt_code)
    if region is None:
        return None

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
    rows = session.execute(statement, {"region_id": region.id}).mappings().all()

    elections: dict[int, dict[str, object]] = {}
    for row in rows:
        election_id = int(row["election_id"])
        election = elections.setdefault(
            election_id,
            {
                "election_id": election_id,
                "election_year": row["election_year"],
                "election_type": row["election_type"],
                "blocs": [],
            },
        )
        blocs = election["blocs"]
        assert isinstance(blocs, list)
        blocs.append(
            {
                "bloc_name": row["bloc_name"],
                "votes": row["votes"],
                "vote_share": _decimal_to_string(row["vote_share"]),
            }
        )

    return {
        "region": region,
        "timeline": list(elections.values()),
    }


def _decimal_to_string(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return f"{value:.4f}"
    return str(value)
