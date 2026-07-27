from electoral_db.models import Region, RegionPoliticalStability
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.analytics.schemas import RegionStabilityRead


class AnalyticsQueries:
    """Read precomputed analytics without rebuilding metrics in HTTP requests."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_stability(
        self,
        *,
        labels: tuple[str, ...] | None = None,
        limit: int = 100,
    ) -> list[RegionStabilityRead]:
        # Select only fields required by the public ranking. This avoids loading unrelated region
        # relationships or exposing the analytics persistence model outside this feature boundary.
        statement = (
            select(
                RegionPoliticalStability.region_id,
                Region.teryt_code,
                Region.name.label("region_name"),
                RegionPoliticalStability.pis_wins,
                RegionPoliticalStability.ko_wins,
                RegionPoliticalStability.other_wins,
                RegionPoliticalStability.switch_count,
                RegionPoliticalStability.avg_winner_margin,
                RegionPoliticalStability.avg_abs_pis_ko_margin,
                RegionPoliticalStability.pis_ko_margin_trend,
                RegionPoliticalStability.volatility_score,
                RegionPoliticalStability.stability_label,
            )
            .join(Region, Region.id == RegionPoliticalStability.region_id)
            .order_by(
                RegionPoliticalStability.switch_count.desc(),
                RegionPoliticalStability.volatility_score.desc().nulls_last(),
                Region.teryt_code,
            )
            .limit(limit)
        )

        # Apply the optional product classification before execution so the limit counts matching
        # regions rather than trimming an unfiltered result in application memory.
        if labels is not None:
            statement = statement.where(RegionPoliticalStability.stability_label.in_(labels))
        rows = self._session.execute(statement).mappings().all()

        # Validate nullable database values and the public shape at the query boundary.
        return [RegionStabilityRead.model_validate(row) for row in rows]
