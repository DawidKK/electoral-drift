"""Utilities that load external public data into the database.

The ingestion package is intentionally separate from the API. API code answers HTTP
requests, while ingestion code prepares data in batch jobs before the API reads it.
"""

from electoral_ingestion.elections import (
    ElectionResultImportSummary,
    import_election_results,
    load_election_results_csv,
)
from electoral_ingestion.regions import RegionImportSummary, import_regions, load_regions_csv

__all__ = [
    "ElectionResultImportSummary",
    "RegionImportSummary",
    "import_election_results",
    "import_regions",
    "load_election_results_csv",
    "load_regions_csv",
]
