from dataclasses import dataclass

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
