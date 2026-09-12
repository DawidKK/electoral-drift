import csv
from pathlib import Path

import pytest
from electoral_ingestion.terc_regions import build_historical_region_dictionary


def write_terc(path: Path, year: int, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["WOJ", "POW", "GMI", "RODZ", "NAZWA", "NAZWA_DOD", "STAN_NA"],
            delimiter=";",
        )
        writer.writeheader()
        writer.writerow(
            {
                "WOJ": "02",
                "POW": "",
                "GMI": "",
                "RODZ": "",
                "NAZWA": "DOLNOŚLĄSKIE",
                "NAZWA_DOD": "województwo",
                "STAN_NA": f"{year}-01-01",
            }
        )
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def municipality(year: int, kind: str, name: str) -> dict[str, str]:
    return {
        "WOJ": "02",
        "POW": "01",
        "GMI": "01",
        "RODZ": kind,
        "NAZWA": name,
        "NAZWA_DOD": "gmina",
        "STAN_NA": f"{year}-01-01",
    }


def test_dictionary_uses_latest_metadata_and_excludes_subdivisions(tmp_path: Path) -> None:
    terc_dir = tmp_path / "terc"
    write_terc(
        terc_dir / "2014-01-01.csv",
        2014,
        [municipality(2014, "1", "Stara nazwa"), municipality(2014, "4", "Część miejska")],
    )
    write_terc(
        terc_dir / "2015-01-01.csv",
        2015,
        [municipality(2015, "1", "Nowa nazwa"), municipality(2015, "4", "Część miejska")],
    )
    output_path = tmp_path / "regions.csv"

    summary = build_historical_region_dictionary(terc_dir, output_path)

    assert summary.snapshots_read == 2
    assert summary.regions_written == 1
    assert read_csv(output_path) == [
        {
            "teryt_code": "0201011",
            "name": "Nowa nazwa",
            "region_type": "urban_municipality",
            "voivodeship": "dolnośląskie",
            "valid_from": "",
            "valid_to": "",
        }
    ]


def test_dictionary_rejects_snapshot_whose_state_differs_from_filename(tmp_path: Path) -> None:
    terc_dir = tmp_path / "terc"
    row = municipality(2014, "1", "Bolesławiec")
    row["STAN_NA"] = "2014-01-02"
    write_terc(terc_dir / "2014-01-01.csv", 2014, [row])

    with pytest.raises(ValueError, match="2014-01-01"):
        build_historical_region_dictionary(terc_dir, tmp_path / "regions.csv")


def test_real_snapshots_build_shared_historical_dictionary(tmp_path: Path) -> None:
    terc_dir = Path("data/raw/teryt/terc")
    if not terc_dir.exists():
        pytest.skip("Repository TERC snapshots are not available.")

    summary = build_historical_region_dictionary(terc_dir, tmp_path / "regions.csv")

    assert summary.snapshots_read == 12
    assert summary.regions_written == 2_629
    regions = {row["teryt_code"]: row for row in read_csv(summary.output_path)}
    assert regions["1465011"]["name"] == "Warszawa"
    assert regions["1465011"]["region_type"] == "urban_municipality"
