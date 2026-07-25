from datetime import date
from decimal import Decimal

import pytest
from electoral_db.analytics import (
    BlocResult,
    calculate_region_stability,
    rebuild_region_political_stability,
)


def result(election_id: int, bloc_name: str, vote_share: str, *, election_date: date) -> BlocResult:
    return BlocResult(
        region_id=1,
        election_id=election_id,
        election_date=election_date,
        round=1,
        bloc_name=bloc_name,
        vote_share=Decimal(vote_share),
    )


def test_calculates_wins_switches_margins_trend_and_volatility_chronologically() -> None:
    rows = [
        result(3, "pis_bloc", "40", election_date=date(2023, 10, 15)),
        result(1, "pis_bloc", "55", election_date=date(2015, 10, 25)),
        result(2, "ko_bloc", "52", election_date=date(2019, 10, 13)),
        result(1, "ko_bloc", "40", election_date=date(2015, 10, 25)),
        result(3, "ko_bloc", "50", election_date=date(2023, 10, 15)),
        result(2, "pis_bloc", "45", election_date=date(2019, 10, 13)),
    ]

    metrics = calculate_region_stability(rows)

    assert metrics.pis_wins == 1
    assert metrics.ko_wins == 2
    assert metrics.other_wins == 0
    assert metrics.switch_count == 1
    assert metrics.avg_winner_margin == Decimal("10.6667")
    assert metrics.avg_abs_pis_ko_margin == Decimal("10.6667")
    assert metrics.pis_ko_margin_trend == Decimal("-25.0000")
    assert metrics.volatility_score == Decimal("12.5000")
    assert metrics.stability_label == "emerging_shift"


@pytest.mark.parametrize(
    ("winner", "expected_label"),
    [("pis_bloc", "safe_pis"), ("ko_bloc", "safe_ko")],
)
def test_classifies_a_consistent_two_election_winner_as_safe(
    winner: str, expected_label: str
) -> None:
    opponent = "ko_bloc" if winner == "pis_bloc" else "pis_bloc"
    rows = [
        result(1, winner, "60", election_date=date(2019, 1, 1)),
        result(1, opponent, "40", election_date=date(2019, 1, 1)),
        result(2, winner, "55", election_date=date(2023, 1, 1)),
        result(2, opponent, "45", election_date=date(2023, 1, 1)),
    ]

    assert calculate_region_stability(rows).stability_label == expected_label


def test_classifies_repeated_switches_as_swing_and_counts_other_wins() -> None:
    rows = [
        result(1, "pis_bloc", "60", election_date=date(2011, 1, 1)),
        result(1, "ko_bloc", "40", election_date=date(2011, 1, 1)),
        result(2, "ko_bloc", "60", election_date=date(2015, 1, 1)),
        result(2, "pis_bloc", "40", election_date=date(2015, 1, 1)),
        result(3, "other", "60", election_date=date(2019, 1, 1)),
        result(3, "ko_bloc", "40", election_date=date(2019, 1, 1)),
    ]

    metrics = calculate_region_stability(rows)

    assert metrics.switch_count == 2
    assert metrics.other_wins == 1
    assert metrics.stability_label == "swing"


def test_tie_and_single_election_history_are_fragmented_without_a_winner() -> None:
    rows = [
        result(1, "pis_bloc", "50", election_date=date(2023, 1, 1)),
        result(1, "ko_bloc", "50", election_date=date(2023, 1, 1)),
    ]

    metrics = calculate_region_stability(rows)

    assert metrics.pis_wins == 0
    assert metrics.ko_wins == 0
    assert metrics.other_wins == 0
    assert metrics.switch_count == 0
    assert metrics.avg_winner_margin is None
    assert metrics.stability_label == "fragmented_or_local"


class FakeMappings:
    def all(self) -> list[dict[str, object]]:
        return [
            {
                "region_id": 1,
                "election_id": 1,
                "election_date": date(2019, 1, 1),
                "round": 1,
                "bloc_name": "pis_bloc",
                "vote_share": Decimal("60"),
            },
            {
                "region_id": 1,
                "election_id": 1,
                "election_date": date(2019, 1, 1),
                "round": 1,
                "bloc_name": "ko_bloc",
                "vote_share": Decimal("40"),
            },
            {
                "region_id": 1,
                "election_id": 2,
                "election_date": date(2023, 1, 1),
                "round": 1,
                "bloc_name": "pis_bloc",
                "vote_share": Decimal("55"),
            },
            {
                "region_id": 1,
                "election_id": 2,
                "election_date": date(2023, 1, 1),
                "round": 1,
                "bloc_name": "ko_bloc",
                "vote_share": Decimal("45"),
            },
        ]


class FakeQueryResult:
    def mappings(self) -> FakeMappings:
        return FakeMappings()


class FakeSession:
    def __init__(self) -> None:
        self.execute_calls = 0
        self.added: list[object] = []
        self.commits = 0

    def execute(self, statement: object) -> FakeQueryResult:
        self.execute_calls += 1
        return FakeQueryResult()

    def add_all(self, instances: list[object]) -> None:
        self.added.extend(instances)

    def commit(self) -> None:
        self.commits += 1


def test_rebuild_replaces_metrics_and_can_be_run_repeatedly() -> None:
    session = FakeSession()

    first_count = rebuild_region_political_stability(session)  # type: ignore[arg-type]
    second_count = rebuild_region_political_stability(session)  # type: ignore[arg-type]

    assert first_count == 1
    assert second_count == 1
    assert session.execute_calls == 4
    assert len(session.added) == 2
    assert session.commits == 2
