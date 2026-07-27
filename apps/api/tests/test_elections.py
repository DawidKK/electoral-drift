from datetime import date
from decimal import Decimal

from app.features.elections.dependencies import get_election_queries
from app.features.elections.schemas import ElectionRead, ElectionResultRead
from app.main import create_app
from fastapi.testclient import TestClient


class FakeElectionQueries:
    def list_elections(self) -> list[ElectionRead]:
        return [
            ElectionRead(
                id=1,
                election_date=date(2023, 10, 15),
                election_year=2023,
                election_type="parliamentary",
                round=1,
                description="Sejm 2023",
            )
        ]

    def list_results(self, election_id: int) -> list[ElectionResultRead]:
        return [
            ElectionResultRead(
                region_id=1,
                teryt_code="0264011",
                region_name="Wroclaw",
                committee_id=10,
                committee_name="Koalicja Obywatelska",
                bloc_name="ko_bloc",
                votes=120000,
                vote_share=Decimal("42.1000"),
                turnout=Decimal("74.5000"),
                eligible_voters=300000,
                valid_votes=285000,
            )
        ]


def override_queries() -> FakeElectionQueries:
    return FakeElectionQueries()


def test_elections_returns_public_shape() -> None:
    app = create_app()
    app.dependency_overrides[get_election_queries] = override_queries
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
    app.dependency_overrides[get_election_queries] = override_queries
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
