from decimal import Decimal

from pydantic import BaseModel


class RegionStabilityRead(BaseModel):
    """Precomputed political-stability metrics for one region."""

    region_id: int
    teryt_code: str
    region_name: str
    pis_wins: int
    ko_wins: int
    other_wins: int
    switch_count: int
    avg_winner_margin: Decimal | None
    avg_abs_pis_ko_margin: Decimal | None
    pis_ko_margin_trend: Decimal | None
    volatility_score: Decimal | None
    stability_label: str
