import csv
from decimal import Decimal
from pathlib import Path

import pytest
from electoral_ingestion.bdl_unemployment import (
    transform_bdl_unemployment_interim_to_processed,
    transform_bdl_unemployment_raw_to_interim,
)

TEST_HASH = "a" * 64


def write_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
    *,
    delimiter: str = ",",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def write_raw(path: Path, rows: list[dict[str, str]]) -> None:
    write_csv(
        path,
        ["Kod", "Nazwa", "ogółem;2014;[%]", "ogółem;2015;[%]", ""],
        rows,
        delimiter=";",
    )


def write_terc(
    path: Path,
    year: int,
    *,
    state: str | None = None,
    source_teryt: str = "020101",
    kind: str = "1",
) -> None:
    write_csv(
        path,
        ["WOJ", "POW", "GMI", "RODZ", "NAZWA", "NAZWA_DOD", "STAN_NA"],
        [
            {
                "WOJ": source_teryt[:2],
                "POW": "",
                "GMI": "",
                "RODZ": "",
                "NAZWA": "DOLNOŚLĄSKIE",
                "NAZWA_DOD": "województwo",
                "STAN_NA": state or f"{year}-01-01",
            },
            {
                "WOJ": source_teryt[:2],
                "POW": source_teryt[2:4],
                "GMI": source_teryt[4:],
                "RODZ": kind,
                "NAZWA": "Chełmiec" if source_teryt == "121002" else "Bolesławiec",
                "NAZWA_DOD": "gmina",
                "STAN_NA": state or f"{year}-01-01",
            },
        ],
        delimiter=";",
    )


def test_raw_to_interim_filters_geography_and_normalizes_decimal_comma(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    interim_path = tmp_path / "interim.csv"
    write_raw(
        raw_path,
        [
            {
                "Kod": "0000000",
                "Nazwa": "POLSKA",
                "ogółem;2014;[%]": "7,5",
                "ogółem;2015;[%]": "6,5",
                "": "",
            },
            {
                "Kod": "0201011",
                "Nazwa": "Bolesławiec (1)",
                "ogółem;2014;[%]": "4,8",
                "ogółem;2015;[%]": "",
                "": "",
            },
            {
                "Kod": "0201044",
                "Nazwa": "Nowogrodziec - miasto (4)",
                "ogółem;2014;[%]": "3,0",
                "ogółem;2015;[%]": "2,8",
                "": "",
            },
        ],
    )

    summary = transform_bdl_unemployment_raw_to_interim(raw_path, interim_path)

    assert summary.raw_rows == 3
    assert summary.observations_written == 1
    assert summary.aggregate_rows_skipped == 1
    assert summary.subdivision_rows_skipped == 1
    assert summary.empty_values_skipped == 1
    assert read_csv(interim_path) == [
        {
            "source_teryt_code": "0201011",
            "source_name": "Bolesławiec (1)",
            "year": "2014",
            "value": "4.8",
            "source_file_sha256": summary.source_file_sha256,
        }
    ]


def test_raw_to_interim_rejects_percentage_outside_range(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.csv"
    write_raw(
        raw_path,
        [
            {
                "Kod": "0201011",
                "Nazwa": "Bolesławiec (1)",
                "ogółem;2014;[%]": "100,1",
                "ogółem;2015;[%]": "4,1",
                "": "",
            }
        ],
    )

    with pytest.raises(ValueError, match="outside 0-100"):
        transform_bdl_unemployment_raw_to_interim(raw_path, tmp_path / "interim.csv")


def test_interim_to_processed_requires_exact_year_snapshot(tmp_path: Path) -> None:
    interim_path = tmp_path / "interim.csv"
    write_csv(
        interim_path,
        ["source_teryt_code", "source_name", "year", "value", "source_file_sha256"],
        [
            {
                "source_teryt_code": "0201011",
                "source_name": "Bolesławiec (1)",
                "year": "2014",
                "value": "4.8",
                "source_file_sha256": TEST_HASH,
            }
        ],
    )
    terc_dir = tmp_path / "terc"
    write_terc(terc_dir / "2014-01-01.csv", 2014, state="2014-01-02")

    with pytest.raises(ValueError, match="2014-01-01"):
        transform_bdl_unemployment_interim_to_processed(
            interim_path, tmp_path / "processed.csv", terc_dir
        )


def test_interim_to_processed_validates_exact_terc_code(tmp_path: Path) -> None:
    interim_path = tmp_path / "interim.csv"
    processed_path = tmp_path / "processed.csv"
    write_csv(
        interim_path,
        ["source_teryt_code", "source_name", "year", "value", "source_file_sha256"],
        [
            {
                "source_teryt_code": "0201011",
                "source_name": "Historyczna etykieta BDL",
                "year": "2014",
                "value": "4.8",
                "source_file_sha256": TEST_HASH,
            }
        ],
    )
    terc_dir = tmp_path / "terc"
    write_terc(terc_dir / "2014-01-01.csv", 2014)

    summary = transform_bdl_unemployment_interim_to_processed(
        interim_path, processed_path, terc_dir
    )

    assert summary.observations_written == 1
    assert read_csv(processed_path) == [
        {
            "teryt_code": "0201011",
            "year": "2014",
            "value": "4.8",
            "source_file_sha256": TEST_HASH,
        }
    ]


def test_interim_to_processed_uses_declared_chelmiec_exception(tmp_path: Path) -> None:
    interim_path = tmp_path / "interim.csv"
    processed_path = tmp_path / "processed.csv"
    write_csv(
        interim_path,
        ["source_teryt_code", "source_name", "year", "value", "source_file_sha256"],
        [
            {
                "source_teryt_code": "1210022",
                "source_name": "Chełmiec (2)",
                "year": "2018",
                "value": "4.7",
                "source_file_sha256": TEST_HASH,
            }
        ],
    )
    terc_dir = tmp_path / "terc"
    write_terc(terc_dir / "2018-01-01.csv", 2018, source_teryt="121002", kind="3")
    write_terc(
        terc_dir / "2018-01-02.csv",
        2018,
        state="2018-01-02",
        source_teryt="121002",
        kind="2",
    )

    summary = transform_bdl_unemployment_interim_to_processed(
        interim_path, processed_path, terc_dir
    )

    assert summary.observations_written == 1
    assert summary.snapshots_read == 2
    assert read_csv(processed_path)[0]["teryt_code"] == "1210022"


def test_real_source_transforms_all_whole_municipality_observations(tmp_path: Path) -> None:
    source_path = Path("data/raw/features/bezrobocie_2014_2025.csv")
    terc_dir = Path("data/raw/teryt/terc")
    if not source_path.exists() or not terc_dir.exists():
        pytest.skip("Repository source file is not available.")

    interim_path = tmp_path / "bezrobocie-long.csv"
    summary = transform_bdl_unemployment_raw_to_interim(source_path, interim_path)

    assert summary.observations_written == 29_732
    assert summary.source_file_sha256 == (
        "2eb9eb1ed57d2fa505521b69ab067dfcf6c6287400ca93d4311f3aa554b4717b"
    )
    values = [Decimal(row["value"]) for row in read_csv(interim_path)]
    assert min(values) == Decimal("0.5")
    assert max(values) == Decimal("24.8")

    processed_path = tmp_path / "bezrobocie-gminy.csv"
    processed = transform_bdl_unemployment_interim_to_processed(
        interim_path, processed_path, terc_dir
    )
    assert processed.observations_written == 29_732
    assert processed.snapshots_read == 13
    assert len(read_csv(processed_path)) == 29_732
