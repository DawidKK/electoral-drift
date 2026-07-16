import argparse
from pathlib import Path

from electoral_db.session import SessionLocal

from electoral_ingestion.elections import import_election_results, load_election_results_csv
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


def import_elections_command() -> None:
    """Command-line entry point for loading election result rows from CSV."""

    parser = argparse.ArgumentParser(description="Import election result records.")
    parser.add_argument("csv_path", type=Path, help="Path to a UTF-8 CSV file with result rows.")
    args = parser.parse_args()

    # One import run gets one database session and commits all rows at the end.
    with SessionLocal() as session:
        rows = load_election_results_csv(args.csv_path)
        summary = import_election_results(session, rows)

    print(
        "Imported election results: "
        f"{summary.elections_created} elections created, "
        f"{summary.committees_created} committees created, "
        f"{summary.results_created} results created, "
        f"{summary.results_updated} results updated, "
        f"{summary.results_unchanged} results unchanged."
    )
