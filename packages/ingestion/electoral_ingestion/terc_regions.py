import csv
import re
from dataclasses import dataclass
from pathlib import Path

from electoral_ingestion.terc import SUPPORTED_REGION_TYPES, TercRegion, load_terc_snapshot

REGION_COLUMNS = (
    "teryt_code",
    "name",
    "region_type",
    "voivodeship",
    "valid_from",
    "valid_to",
)
SNAPSHOT_NAME = re.compile(r"(?P<date>\d{4}-01-01)\.csv")


@dataclass(frozen=True)
class HistoricalRegionDictionarySummary:
    """Counts and output produced from historical TERC snapshots."""

    snapshots_read: int
    regions_written: int
    output_path: Path


def build_historical_region_dictionary(
    terc_dir: Path, output_path: Path
) -> HistoricalRegionDictionarySummary:
    """Build one shared importer-ready dictionary from all annual TERC snapshots."""

    snapshot_paths = sorted(terc_dir.glob("*-01-01.csv"))
    if not snapshot_paths:
        raise ValueError(f"No historical TERC snapshots found in {terc_dir}.")

    latest_regions: dict[str, TercRegion] = {}
    for snapshot_path in snapshot_paths:
        match = SNAPSHOT_NAME.fullmatch(snapshot_path.name)
        if match is None:
            continue
        expected_date = match.group("date")
        snapshot = load_terc_snapshot(
            snapshot_path,
            expected_date,
            allowed_types=SUPPORTED_REGION_TYPES,
        )
        latest_regions.update(snapshot)

    rows = [
        {
            "teryt_code": region.teryt_code,
            "name": region.name,
            "region_type": region.region_type,
            "voivodeship": region.voivodeship,
            "valid_from": "",
            "valid_to": "",
        }
        for region in sorted(latest_regions.values(), key=lambda item: item.teryt_code)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=REGION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return HistoricalRegionDictionarySummary(
        snapshots_read=len(snapshot_paths),
        regions_written=len(rows),
        output_path=output_path,
    )
