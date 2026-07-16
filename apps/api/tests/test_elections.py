from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.dependencies import get_db_session
from app.main import create_app
from fastapi.testclient import TestClient


@dataclass
class FakeElection:
    id: int
    election_date: date
    election_year: int
    election_type: str
    round: int
    description: str | None = None


class FakeScalarResult:
    def all(self) -> list[FakeElection]:
        return [
            FakeElection(
                id=1,
                election_date=date(2023, 10, 15),
                election_year=2023,
                election_type="parliamentary",
                round=1,
                description="Sejm 2023",
            )
        ]


class FakeResultRows:
    def all(self) -> list[object]:
        class FakeRow:
            _mapping = {
                "region_id": 1,
                "teryt_code": "0264011",
                "region_name": "Wroclaw",
                "committee_id": 10,
                "committee_name": "Koalicja Obywatelska",
                "bloc_name": "ko_bloc",
                "votes": 120000,
                "vote_share": Decimal("42.1000"),
                "turnout": Decimal("74.5000"),
                "eligible_voters": 300000,
                "valid_votes": 285000,
            }

        return [FakeRow()]


class FakeSession:
    def scalars(self, statement: object) -> FakeScalarResult:
        return FakeScalarResult()

    def execute(self, statement: object) -> FakeResultRows:
        return FakeResultRows()


def override_session() -> FakeSession:
    return FakeSession()


def test_elections_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.get("/elections")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 1,
            "election_date": "2023-10-15",
            "election_year": 2023,
            "election_type": "parliamentary",
            "round": 1,
            "description": "Sejm 2023",
        }
    ]


def test_election_results_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_db_session] = override_session
    client = TestClient(app)

    response = client.get("/elections/1/results")

    assert response.status_code == 200
    assert response.json() == [
        {
            "region_id": 1,
            "teryt_code": "0264011",
            "region_name": "Wroclaw",
            "committee_id": 10,
            "committee_name": "Koalicja Obywatelska",
            "bloc_name": "ko_bloc",
            "votes": 120000,
            "vote_share": "42.1000",
            "turnout": "74.5000",
            "eligible_voters": 300000,
            "valid_votes": 285000,
        }
    ]
