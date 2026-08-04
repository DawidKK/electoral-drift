from datetime import date
from decimal import Decimal

from app.features.regions.dependencies import get_region_queries
from app.features.regions.schemas import (
    RegionElectionRead,
    RegionRead,
    RegionTimelineBlocRead,
    RegionTimelineElectionRead,
    RegionTimelineRead,
)
from app.main import create_app
from fastapi.testclient import TestClient


class FakeRegionQueries:
    def list_regions(self) -> list[RegionRead]:
        return [
            RegionRead(
                id=1,
                canonical_region_id=10,
                teryt_code="0264011",
                name="Wroclaw",
                region_type="city_county",
                voivodeship="dolnoslaskie",
            )
        ]

    def get_region(self, teryt_code: str) -> RegionRead | None:
        if teryt_code == "missing":
            return None
        return RegionRead(
            id=1,
            canonical_region_id=10,
            teryt_code="0264011",
            name="Wroclaw",
            region_type="city_county",
            voivodeship="dolnoslaskie",
        )

    def list_elections(self, teryt_code: str) -> list[RegionElectionRead]:
        return [
            RegionElectionRead(
                id=3,
                election_date=date(2019, 10, 13),
                election_year=2019,
                election_type="parliamentary",
                round=1,
            )
        ]

    def get_timeline(self, teryt_code: str) -> RegionTimelineRead | None:
        if teryt_code == "missing":
            return None
        region = self.get_region(teryt_code)
        assert region is not None
        return RegionTimelineRead(
            region=region,
            timeline=[
                RegionTimelineElectionRead(
                    election_id=3,
                    election_year=2019,
                    election_type="parliamentary",
                    blocs=[
                        RegionTimelineBlocRead(
                            bloc_name="ko_bloc",
                            votes=110000,
                            vote_share=f"{Decimal('39.2000'):.4f}",
                        ),
                        RegionTimelineBlocRead(
                            bloc_name="pis_bloc",
                            votes=90000,
                            vote_share=f"{Decimal('32.5000'):.4f}",
                        ),
                    ],
                ),
                RegionTimelineElectionRead(
                    election_id=5,
                    election_year=2023,
                    election_type="parliamentary",
                    blocs=[
                        RegionTimelineBlocRead(
                            bloc_name="ko_bloc",
                            votes=120000,
                            vote_share=f"{Decimal('42.1000'):.4f}",
                        )
                    ],
                ),
            ],
        )


def override_queries() -> FakeRegionQueries:
    return FakeRegionQueries()


def test_regions_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_region_queries] = override_queries
    client = TestClient(app)

    response = client.get("/regions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "canonical_region_id": 10,
            "teryt_code": "0264011",
            "name": "Wroclaw",
            "region_type": "city_county",
            "voivodeship": "dolnoslaskie",
        }
    ]


def test_region_detail_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_region_queries] = override_queries
    client = TestClient(app)

    response = client.get("/regions/0264011")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "canonical_region_id": 10,
        "teryt_code": "0264011",
        "name": "Wroclaw",
        "region_type": "city_county",
        "voivodeship": "dolnoslaskie",
    }


def test_region_timeline_returns_grouped_bloc_history() -> None:
    app = create_app()
    app.dependency_overrides[get_region_queries] = override_queries
    client = TestClient(app)

    response = client.get("/regions/0264011/timeline")

    assert response.status_code == 200
    assert response.json() == {
        "region": {
            "id": 1,
            "canonical_region_id": 10,
            "teryt_code": "0264011",
            "name": "Wroclaw",
            "region_type": "city_county",
            "voivodeship": "dolnoslaskie",
        },
        "timeline": [
            {
                "election_id": 3,
                "election_year": 2019,
                "election_type": "parliamentary",
                "blocs": [
                    {
                        "bloc_name": "ko_bloc",
                        "votes": 110000,
                        "vote_share": "39.2000",
                    },
                    {
                        "bloc_name": "pis_bloc",
                        "votes": 90000,
                        "vote_share": "32.5000",
                    },
                ],
            },
            {
                "election_id": 5,
                "election_year": 2023,
                "election_type": "parliamentary",
                "blocs": [
                    {
                        "bloc_name": "ko_bloc",
                        "votes": 120000,
                        "vote_share": "42.1000",
                    }
                ],
            },
        ],
    }


def test_region_detail_returns_not_found_for_unknown_teryt() -> None:
    app = create_app()
    app.dependency_overrides[get_region_queries] = override_queries
    client = TestClient(app)

    response = client.get("/regions/missing")

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found."}


def test_region_timeline_returns_not_found_for_unknown_teryt() -> None:
    app = create_app()
    app.dependency_overrides[get_region_queries] = override_queries
    client = TestClient(app)

    response = client.get("/regions/missing/timeline")

    assert response.status_code == 404
    assert response.json() == {"detail": "Region not found."}
