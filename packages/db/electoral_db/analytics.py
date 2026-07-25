from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from electoral_db.models import RegionPoliticalStability


@dataclass(frozen=True)
class BlocResult:
    region_id: int
    election_id: int
    election_date: date
    round: int
    bloc_name: str
    vote_share: Decimal


@dataclass(frozen=True)
class StabilityMetrics:
    region_id: int
    pis_wins: int
    ko_wins: int
    other_wins: int
    switch_count: int
    avg_winner_margin: Decimal | None
    avg_abs_pis_ko_margin: Decimal | None
    pis_ko_margin_trend: Decimal | None
    volatility_score: Decimal | None
    stability_label: str


FOUR_PLACES = Decimal("0.0001")


def _rounded(value: Decimal) -> Decimal:
    return value.quantize(FOUR_PLACES, rounding=ROUND_HALF_UP)


def _average(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    return _rounded(sum(values, start=Decimal()) / len(values))


def _stability_label(winners: Sequence[str]) -> str:
    if len(winners) < 2:
        return "fragmented_or_local"

    switch_count = sum(left != right for left, right in zip(winners, winners[1:], strict=False))
    if switch_count >= 2:
        return "swing"
    if switch_count == 1:
        return "emerging_shift"
    if winners[0] == "pis_bloc":
        return "safe_pis"
    if winners[0] == "ko_bloc":
        return "safe_ko"
    return "fragmented_or_local"


def calculate_region_stability(results: Sequence[BlocResult]) -> StabilityMetrics:
    """Calculate deterministic stability metrics from chronological bloc results."""
    # One calculation produces exactly one region snapshot. Rejecting mixed or empty input here
    # keeps the later aggregation free from defensive fallbacks and accidental cross-region data.
    if not results:
        raise ValueError("at least one bloc result is required")
    region_ids = {result.region_id for result in results}
    if len(region_ids) != 1:
        raise ValueError("all bloc results must belong to one region")

    # Election date alone is not a sufficient identity: separate rounds or election records can
    # share a date. Keeping the full event key prevents their bloc results from being merged.
    by_election: defaultdict[tuple[date, int, int], list[BlocResult]] = defaultdict(list)
    for result in results:
        by_election[(result.election_date, result.round, result.election_id)].append(result)

    # Winners drive win and switch counters. The two margin series serve different questions:
    # winner_margins measures competitiveness, while pis_ko_margins tracks directional drift.
    winners: list[str] = []
    winner_margins: list[Decimal] = []
    pis_ko_margins: list[Decimal] = []

    # Sorting the event keys makes switches, trends, and volatility independent of source row
    # order. Within an election, descending vote share exposes the winner and runner-up.
    for election_key in sorted(by_election):
        election_results = sorted(
            by_election[election_key], key=lambda result: result.vote_share, reverse=True
        )

        # A tied top share has no unique winner. Such an election contributes neither a win nor
        # a winner margin, so arbitrary bloc ordering cannot change the analytical classification.
        top_share = election_results[0].vote_share
        top_results = [result for result in election_results if result.vote_share == top_share]
        if len(top_results) == 1:
            winners.append(top_results[0].bloc_name)
            if len(election_results) >= 2:
                winner_margins.append(top_share - election_results[1].vote_share)

        # PiS–KO drift is defined only when both normalized blocs exist in the election. Other
        # blocs still participate in deciding the winner but do not substitute for a missing side.
        shares = {result.bloc_name: result.vote_share for result in election_results}
        if "pis_bloc" in shares and "ko_bloc" in shares:
            pis_ko_margins.append(shares["pis_bloc"] - shares["ko_bloc"])

    # Ties were omitted from winners above. Consequently, switches compare consecutive uniquely
    # decided elections and never manufacture a winner for an unresolved event.
    win_counts = Counter(winners)
    switch_count = sum(left != right for left, right in zip(winners, winners[1:], strict=False))

    # Volatility captures movement between consecutive PiS–KO margins regardless of direction;
    # trend retains direction by comparing the newest available margin with the oldest one.
    margin_changes = [
        abs(current - previous)
        for previous, current in zip(pis_ko_margins, pis_ko_margins[1:], strict=False)
    ]
    margin_trend = (
        _rounded(pis_ko_margins[-1] - pis_ko_margins[0]) if len(pis_ko_margins) >= 2 else None
    )

    # Only the two principal normalized blocs get dedicated counters. Every other uniquely
    # winning bloc is intentionally combined into the analytical `other_wins` category.
    return StabilityMetrics(
        region_id=next(iter(region_ids)),
        pis_wins=win_counts["pis_bloc"],
        ko_wins=win_counts["ko_bloc"],
        other_wins=sum(
            count
            for bloc_name, count in win_counts.items()
            if bloc_name not in {"pis_bloc", "ko_bloc"}
        ),
        switch_count=switch_count,
        avg_winner_margin=_average(winner_margins),
        avg_abs_pis_ko_margin=_average([abs(margin) for margin in pis_ko_margins]),
        pis_ko_margin_trend=margin_trend,
        volatility_score=_average(margin_changes),
        stability_label=_stability_label(winners),
    )


def rebuild_region_political_stability(session: Session) -> int:
    """Replace stored region stability metrics in one database transaction."""
    source_rows = session.execute(
        text(
            """
            SELECT
                summary.region_id,
                summary.election_id,
                election.election_date,
                election.round,
                summary.bloc_name,
                summary.vote_share
            FROM analytics.region_election_summary AS summary
            JOIN core.elections AS election ON election.id = summary.election_id
            WHERE summary.bloc_name IS NOT NULL
              AND summary.vote_share IS NOT NULL
            ORDER BY
                summary.region_id,
                election.election_date,
                election.round,
                summary.election_id
            """
        )
    ).mappings()

    # Calculate every region before replacing stored rows, so invalid source data cannot
    # partially clear the current analytical snapshot.
    results_by_region: defaultdict[int, list[BlocResult]] = defaultdict(list)
    for row in source_rows.all():
        result = BlocResult(
            region_id=int(row["region_id"]),
            election_id=int(row["election_id"]),
            election_date=row["election_date"],
            round=int(row["round"]),
            bloc_name=str(row["bloc_name"]),
            vote_share=Decimal(row["vote_share"]),
        )
        results_by_region[result.region_id].append(result)

    metrics = [
        calculate_region_stability(region_results) for region_results in results_by_region.values()
    ]

    # Delete and insert form one explicit transaction committed only after the full snapshot
    # has been staged successfully.
    session.execute(delete(RegionPoliticalStability))
    session.add_all(
        [
            RegionPoliticalStability(
                region_id=item.region_id,
                pis_wins=item.pis_wins,
                ko_wins=item.ko_wins,
                other_wins=item.other_wins,
                switch_count=item.switch_count,
                avg_winner_margin=item.avg_winner_margin,
                avg_abs_pis_ko_margin=item.avg_abs_pis_ko_margin,
                pis_ko_margin_trend=item.pis_ko_margin_trend,
                volatility_score=item.volatility_score,
                stability_label=item.stability_label,
            )
            for item in metrics
        ]
    )
    session.commit()
    return len(metrics)
