from pydantic import BaseModel, ConfigDict


class RegionRead(BaseModel):
    """Public JSON shape returned by region endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    teryt_code: str
    name: str
    region_type: str
    voivodeship: str | None = None
