from electoral_db.analytics import rebuild_region_political_stability
from electoral_db.session import SessionLocal


def rebuild_stability_command() -> None:
    """CLI entry point for rebuilding the political-stability snapshot."""
    with SessionLocal() as session:
        region_count = rebuild_region_political_stability(session)

    print(f"Rebuilt political stability metrics for {region_count} regions.")
