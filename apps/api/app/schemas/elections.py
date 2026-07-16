from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ElectionRead(BaseModel):
    """Public JSON shape for one election event."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    election_date: date
    election_year: int
    election_type: str
    round: int
    description: str | None = None


class ElectionResultRead(BaseModel):
    """Public JSON shape for one committee result in one region."""

    region_id: int
    teryt_code: str
    region_name: str
    committee_id: int
    committee_name: str
    bloc_name: str | None = None
    votes: int | None = None
    vote_share: Decimal | None = None
    turnout: Decimal | None = None
    eligible_voters: int | None = None
    valid_votes: int | None = None
