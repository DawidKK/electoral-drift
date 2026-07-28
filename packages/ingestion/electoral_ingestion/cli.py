import argparse
from pathlib import Path

from electoral_db.session import SessionLocal

from electoral_ingestion.elections import import_election_results, load_election_results_csv
from electoral_ingestion.regions import import_regions, load_regions_csv
from electoral_ingestion.sejm_interim import transform_sejm_raw_to_interim
from electoral_ingestion.sejm_processed import transform_sejm_interim_to_processed


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


def transform_sejm_interim_command() -> None:
    """Command-line entry point for normalizing a raw PKW Sejm CSV."""

    parser = argparse.ArgumentParser(
        description="Transform a supported raw PKW Sejm CSV into interim CSV files."
    )
    parser.add_argument("raw_path", type=Path, help="Path to a raw 2015, 2019, or 2023 CSV.")
    parser.add_argument("output_dir", type=Path, help="Directory for the two interim CSV files.")
    args = parser.parse_args()

    summary = transform_sejm_raw_to_interim(args.raw_path, args.output_dir)
    print(
        f"Transformed Sejm {summary.year}: "
        f"{summary.municipalities_written} municipalities, "
        f"{summary.committee_results_written} committee results, "
        f"{summary.rows_without_teryt_skipped} rows without TERYT skipped, "
        f"{summary.special_rows_skipped} foreign or ship rows skipped. "
        f"Files: {summary.totals_path}, {summary.committee_results_path}."
    )


def transform_sejm_processed_command() -> None:
    """Command-line entry point for building importer-ready Sejm CSVs."""

    parser = argparse.ArgumentParser(
        description="Transform Sejm interim CSV files into importer-ready processed files."
    )
    parser.add_argument("interim_dir", type=Path, help="Directory with paired interim CSV files.")
    parser.add_argument("output_dir", type=Path, help="Directory for processed election results.")
    parser.add_argument("terc_dir", type=Path, help="Directory with historical TERC CSV files.")
    args = parser.parse_args()

    summary = transform_sejm_interim_to_processed(args.interim_dir, args.output_dir, args.terc_dir)
    print(
        f"Processed {summary.elections_processed} Sejm elections: "
        f"{summary.results_written} results and {summary.regions_written} regions. "
        f"Regions: {summary.regions_path}."
    )
