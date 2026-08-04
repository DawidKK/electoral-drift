from collections.abc import Sequence
from typing import TypedDict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from electoral_db.models import CanonicalRegion, Election, ElectionResult, Region


class CanonicalRegionGroup(TypedDict):
    """Canonical name and historical database identifiers for one municipality."""

    name: str
    region_ids: tuple[int, ...]


RegionCandidate = tuple[int, str, str, int | None]


def build_canonical_region_groups(
    candidates: Sequence[RegionCandidate],
) -> dict[str, CanonicalRegionGroup]:
    """Group seven-digit TERYT versions by their stable six-digit base."""
    grouped: dict[str, list[RegionCandidate]] = {}
    for candidate in candidates:
        _, teryt_code, _, _ = candidate
        if len(teryt_code) != 7 or not teryt_code.isdigit():
            raise ValueError(f"TERYT code must contain exactly 7 digits: {teryt_code}")
        grouped.setdefault(teryt_code[:6], []).append(candidate)

    result: dict[str, CanonicalRegionGroup] = {}
    for base_teryt_code, versions in grouped.items():
        # The newest observed version supplies the display name. Region ID resolves equal or
        # missing years deterministically without pretending that names establish identity.
        latest = max(versions, key=lambda item: (item[3] if item[3] is not None else -1, item[0]))
        result[base_teryt_code] = {
            "name": latest[2],
            "region_ids": tuple(sorted(version[0] for version in versions)),
        }
    return result


def rebuild_canonical_regions(session: Session) -> int:
    """Create canonical municipalities and map every historical TERYT version atomically."""
    latest_election_year = func.max(Election.election_year)
    candidate_rows = session.execute(
        select(
            Region.id,
            Region.teryt_code,
            Region.name,
            latest_election_year,
        )
        .outerjoin(ElectionResult, ElectionResult.region_id == Region.id)
        .outerjoin(Election, Election.id == ElectionResult.election_id)
        .group_by(Region.id)
    ).all()
    candidates: list[RegionCandidate] = [
        (int(row[0]), str(row[1]), str(row[2]), int(row[3]) if row[3] is not None else None)
        for row in candidate_rows
    ]
    groups = build_canonical_region_groups(candidates)

    # Load both sides once. This keeps the rebuild linear and avoids one query per municipality.
    canonical_by_code = {
        canonical.base_teryt_code: canonical
        for canonical in session.scalars(select(CanonicalRegion)).all()
    }
    for base_teryt_code, group in groups.items():
        canonical = canonical_by_code.get(base_teryt_code)
        if canonical is None:
            canonical = CanonicalRegion(base_teryt_code=base_teryt_code, name=group["name"])
            session.add(canonical)
            canonical_by_code[base_teryt_code] = canonical
        else:
            canonical.name = group["name"]

    session.flush()

    regions_by_id = {region.id: region for region in session.scalars(select(Region)).all()}
    for base_teryt_code, group in groups.items():
        canonical_id = canonical_by_code[base_teryt_code].id
        for region_id in group["region_ids"]:
            regions_by_id[region_id].canonical_region_id = canonical_id

    session.commit()
    return len(groups)
