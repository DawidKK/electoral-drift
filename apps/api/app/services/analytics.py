from electoral_db.models import Region, RegionPoliticalStability
from sqlalchemy import select
from sqlalchemy.orm import Session


def list_stability_ranking(
    session: Session, *, labels: tuple[str, ...] | None = None, limit: int = 100
) -> list[dict[str, object]]:
    """Read the precomputed stability ranking without rebuilding analytics in HTTP."""
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
    if labels is not None:
        statement = statement.where(RegionPoliticalStability.stability_label.in_(labels))
    return [dict(row._mapping) for row in session.execute(statement).all()]
