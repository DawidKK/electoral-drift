from datetime import date

from pydantic import BaseModel


class RegionRead(BaseModel):
    """Public representation of one territorial region."""

    id: int
    canonical_region_id: int | None = None
    teryt_code: str
    name: str
    region_type: str
    voivodeship: str | None = None


class RegionElectionRead(BaseModel):
    """Election summary owned by the region-election use case."""

    id: int
    election_date: date
    election_year: int
    election_type: str
    round: int
    description: str | None = None


class RegionTimelineBlocRead(BaseModel):
    """One bloc-level result within a region's election timeline."""

    bloc_name: str | None = None
    votes: int | None = None
    vote_share: str | None = None


class RegionTimelineElectionRead(BaseModel):
    """One election point on a region's political timeline."""

    election_id: int
    election_year: int
    election_type: str
    blocs: list[RegionTimelineBlocRead]


class RegionTimelineRead(BaseModel):
    """Complete political timeline returned for one region."""

    region: RegionRead
    timeline: list[RegionTimelineElectionRead]
