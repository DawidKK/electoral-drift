import argparse
from pathlib import Path

from electoral_db.session import SessionLocal

from electoral_ingestion.regions import import_regions, load_regions_csv


def import_regions_command() -> None:
    """Command-line entry point for loading region rows from CSV into PostgreSQL."""

    parser = argparse.ArgumentParser(description="Import region records into core.regions.")
    parser.add_argument("csv_path", type=Path, help="Path to a UTF-8 CSV file with region rows.")
    args = parser.parse_args()

    # The CLI creates one database session for one import run and closes it afterwards.
    with SessionLocal() as session:
        rows = load_regions_csv(args.csv_path)
        summary = import_regions(session, rows)

    print(
        "Imported regions: "
        f"{summary.created} created, {summary.updated} updated, "
        f"{summary.unchanged} unchanged."
    )
