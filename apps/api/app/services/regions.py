from electoral_db.models import Region
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_regions(session: Session) -> list[Region]:
    # Services contain database queries so routers can stay focused on HTTP concerns.
    statement = select(Region).order_by(Region.teryt_code)
    return list(session.scalars(statement).all())


def get_region_by_teryt_code(session: Session, teryt_code: str) -> Region | None:
    statement = select(Region).where(Region.teryt_code == teryt_code)
    return session.scalar(statement)
