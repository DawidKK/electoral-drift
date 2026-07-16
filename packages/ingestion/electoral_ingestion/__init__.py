"""Utilities that load external public data into the database.

The ingestion package is intentionally separate from the API. API code answers HTTP
requests, while ingestion code prepares data in batch jobs before the API reads it.
"""

from electoral_ingestion.regions import RegionImportSummary, import_regions, load_regions_csv

__all__ = ["RegionImportSummary", "import_regions", "load_regions_csv"]
