from decimal import Decimal

from app.features.analytics.dependencies import get_analytics_queries
from app.features.analytics.schemas import RegionStabilityRead
from app.main import create_app
from fastapi.testclient import TestClient


class FakeAnalyticsQueries:
    def list_stability(
        self,
        *,
        labels: tuple[str, ...] | None = None,
        limit: int = 100,
    ) -> list[RegionStabilityRead]:
        return [
            RegionStabilityRead(
                region_id=1,
                teryt_code="0264011",
                region_name="Wrocław",
                pis_wins=1,
                ko_wins=3,
                other_wins=0,
                switch_count=1,
                avg_winner_margin=Decimal("8.2500"),
                avg_abs_pis_ko_margin=Decimal("7.5000"),
                pis_ko_margin_trend=Decimal("-12.0000"),
                volatility_score=Decimal("9.5000"),
                stability_label="emerging_shift",
            )
        ]


def override_queries() -> FakeAnalyticsQueries:
    return FakeAnalyticsQueries()


def test_stability_ranking_returns_precomputed_region_metrics() -> None:
    app = create_app()
    app.dependency_overrides[get_analytics_queries] = override_queries
    client = TestClient(app)

    response = client.get("/analytics/stability-ranking")

    assert response.status_code == 200
    assert response.json() == [
        {
            "region_id": 1,
            "teryt_code": "0264011",
            "region_name": "Wrocław",
            "pis_wins": 1,
            "ko_wins": 3,
            "other_wins": 0,
            "switch_count": 1,
            "avg_winner_margin": "8.2500",
            "avg_abs_pis_ko_margin": "7.5000",
            "pis_ko_margin_trend": "-12.0000",
            "volatility_score": "9.5000",
            "stability_label": "emerging_shift",
        }
    ]


def test_swing_counties_returns_only_swing_regions() -> None:
    app = create_app()
    app.dependency_overrides[get_analytics_queries] = override_queries
    client = TestClient(app)

    response = client.get("/analytics/swing-counties")

    assert response.status_code == 200
    assert response.json()[0]["stability_label"] == "emerging_shift"


def test_stability_endpoints_reject_an_invalid_limit() -> None:
    client = TestClient(create_app())

    response = client.get("/analytics/stability-ranking?limit=0")

    assert response.status_code == 422
