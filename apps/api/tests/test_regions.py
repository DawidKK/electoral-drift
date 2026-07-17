from dataclasses import dataclass
from decimal import Decimal

from app.core.dependencies import get_db_session
from app.main import create_app
from fastapi.testclient import TestClient


@dataclass
class FakeRegion:
    id: int
    teryt_code: str
    name: str
    region_type: str
    voivodeship: str | None = None


class FakeScalarResult:
    def all(self) -> list[FakeRegion]:
        return [
            FakeRegion(
                id=1,
                teryt_code="0264011",
                name="Wroclaw",
                region_type="city_county",
                voivodeship="dolnoslaskie",
            )
        ]


class FakeMappingResult:
    def mappings(self) -> FakeMappingResult:
        return self

    def all(self) -> list[dict[str, object]]:
        return [
            {
                "election_id": 3,
                "election_year": 2019,
                "election_type": "parliamentary",
                "bloc_name": "ko_bloc",
                "votes": 110000,
                "vote_share": Decimal("39.2000"),
            },
            {
                "election_id": 3,
                "election_year": 2019,
                "election_type": "parliamentary",
                "bloc_name": "pis_bloc",
                "votes": 90000,
                "vote_share": Decimal("32.5000"),
            },
            {
                "election_id": 5,
                "election_year": 2023,
                "election_type": "parliamentary",
                "bloc_name": "ko_bloc",
                "votes": 120000,
                "vote_share": Decimal("42.1000"),
            },
        ]


class FakeSession:
    def scalars(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult()

    def scalar(self, statement: object) -> FakeRegion:
        return FakeRegion(
            id=1,
            teryt_code="0264011",
            name="Wroclaw",
            region_type="city_county",
            voivodeship="dolnoslaskie",
        )

    def execute(self, statement: object, params: object | None = None) -> FakeMappingResult:
        return FakeMappingResult()


def override_session() -> FakeSession:
    return FakeSession()


def test_regions_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.get("/regions")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "teryt_code": "0264011",
            "name": "Wroclaw",
            "region_type": "city_county",
            "voivodeship": "dolnoslaskie",
        }
    ]


def test_region_detail_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.get("/regions/0264011")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "teryt_code": "0264011",
        "name": "Wroclaw",
        "region_type": "city_county",
        "voivodeship": "dolnoslaskie",
    }


def test_region_timeline_returns_grouped_bloc_history() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.get("/regions/0264011/timeline")

    assert response.status_code == 200
    assert response.json() == {
        "region": {
            "id": 1,
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
