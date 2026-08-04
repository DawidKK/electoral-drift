from electoral_db.analytics import rebuild_region_political_stability
from electoral_db.canonical_regions import rebuild_canonical_regions
from electoral_db.session import SessionLocal


def rebuild_stability_command() -> None:
    """CLI entry point for rebuilding the political-stability snapshot."""
    with SessionLocal() as session:
        region_count = rebuild_region_political_stability(session)

    print(f"Rebuilt political stability metrics for {region_count} regions.")


def rebuild_canonical_regions_command() -> None:
    """CLI entry point for rebuilding canonical municipality mappings."""
    with SessionLocal() as session:
        canonical_count = rebuild_canonical_regions(session)

    print(f"Rebuilt {canonical_count} canonical region mappings.")
