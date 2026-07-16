from electoral_db.models import Region
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_regions(session: Session) -> list[Region]:
    statement = select(Region).order_by(Region.teryt_code)
    return list(session.scalars(statement).all())
