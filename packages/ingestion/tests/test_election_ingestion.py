from datetime import date
from decimal import Decimal

import pytest
from electoral_ingestion.elections import (
    ElectionResultInput,
    import_election_results,
    load_election_results_csv,
    normalize_election_result_row,
)


class FakeModel:
    def __init__(self, **kwargs: object) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


class FakeElectionSession:
    """In-memory session that returns objects in the order the importer asks for them."""

    def __init__(self, scalar_results: list[object | None]) -> None:
        self.scalar_results = scalar_results
        self.added: list[object] = []
        self.committed = False
        self.flush_count = 0

    def scalar(self, statement: object) -> object | None:
        return self.scalar_results.pop(0)

    def add(self, model: object) -> None:
        if not hasattr(model, "id"):
            model.id = 100 + len(self.added)
        self.added.append(model)

    def flush(self) -> None:
        self.flush_count += 1

    def commit(self) -> None:
        self.committed = True


def sample_row() -> ElectionResultInput:
    return ElectionResultInput(
        election_date=date(2023, 10, 15),
        election_type="parliamentary",
        round=1,
        description="Sejm 2023",
        teryt_code="0264011",
        committee_name="Koalicja Obywatelska",
        bloc_name="ko_bloc",
        votes=120000,
        vote_share=Decimal("42.1000"),
        turnout=Decimal("74.5000"),
        eligible_voters=300000,
        valid_votes=285000,
    )


def test_normalize_election_result_row_preserves_types() -> None:
    row = normalize_election_result_row(
        {
            "election_date": "2023-10-15",
            "election_type": "parliamentary",
            "round": "1",
            "description": "Sejm 2023",
            "teryt_code": "0264011",
            "committee_name": "Koalicja Obywatelska",
            "bloc_name": "ko_bloc",
            "votes": "120000",
            "vote_share": "42.1000",
            "turnout": "74.5000",
            "eligible_voters": "300000",
            "valid_votes": "285000",
        },
        row_number=2,
    )

    assert row.teryt_code == "0264011"
    assert row.election_year == 2023
    assert row.vote_share == Decimal("42.1000")


def test_load_election_results_csv_requires_core_columns(tmp_path) -> None:
    csv_path = tmp_path / "election_results.csv"
    csv_path.write_text("election_date,teryt_code\n2023-10-15,0264011\n", encoding="utf-8")

    with pytest.raises(ValueError, match="committee_name"):
        load_election_results_csv(csv_path)


def test_import_election_results_creates_missing_fact_objects() -> None:
    session = FakeElectionSession(
        scalar_results=[
            FakeModel(id=1, teryt_code="0264011"),
            FakeModel(id=2, name="ko_bloc"),
            None,
            None,
            None,
        ]
    )

    summary = import_election_results(session, [sample_row()])

    assert summary.elections_created == 1
    assert summary.committees_created == 1
    assert summary.results_created == 1
    assert session.committed is True
    assert len(session.added) == 3


def test_import_election_results_updates_existing_result() -> None:
    existing_result = FakeModel(
        bloc_id=2,
        votes=1,
        vote_share=Decimal("1.0000"),
        turnout=None,
        eligible_voters=None,
        valid_votes=None,
    )
    session = FakeElectionSession(
        scalar_results=[
            FakeModel(id=1, teryt_code="0264011"),
            FakeModel(id=2, name="ko_bloc"),
            FakeModel(id=3),
            FakeModel(id=4, bloc_id=2),
            existing_result,
        ]
    )

    summary = import_election_results(session, [sample_row()])

    assert summary.results_updated == 1
    assert existing_result.votes == 120000
    assert existing_result.vote_share == Decimal("42.1000")
    assert session.committed is True


def test_import_election_results_rejects_unknown_region() -> None:
    session = FakeElectionSession(scalar_results=[None])

    with pytest.raises(ValueError, match="Import regions first"):
        import_election_results(session, [sample_row()])
