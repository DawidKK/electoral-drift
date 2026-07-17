from pydantic import BaseModel, ConfigDict


class RegionRead(BaseModel):
    """Public JSON shape returned by region endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    teryt_code: str
    name: str
    region_type: str
    voivodeship: str | None = None


class RegionTimelineBlocRead(BaseModel):
    """One bloc-level result inside a single election on the region timeline."""

    bloc_name: str | None = None
    votes: int | None = None
    vote_share: str | None = None


class RegionTimelineElectionRead(BaseModel):
    """One election point on the region timeline."""

    election_id: int
    election_year: int
    election_type: str
    blocs: list[RegionTimelineBlocRead]


class RegionTimelineRead(BaseModel):
    """Product-ready timeline response for one region."""

    region: RegionRead
    timeline: list[RegionTimelineElectionRead]
