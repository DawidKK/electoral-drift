import csv
from pathlib import Path

import electoral_ingestion
import pytest


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def totals_row(
    *,
    year: int = 2019,
    teryt: str = "020101",
    name: str = "m. Bolesławiec",
    voivodeship: str = "dolnośląskie",
    eligible_voters: str = "100",
    ballots_issued: str = "80",
    valid_votes: str = "75",
) -> dict[str, str]:
    return {
        "election_date": f"{year}-10-13",
        "election_type": "parliamentary",
        "round": "1",
        "source_teryt": teryt,
        "gmina_name": name,
        "powiat_name": "bolesławiecki",
        "voivodeship": voivodeship,
        "eligible_voters": eligible_voters,
        "ballots_issued": ballots_issued,
        "valid_votes": valid_votes,
    }


def committee_row(
    committee: str,
    votes: str,
    *,
    year: int = 2019,
    teryt: str = "020101",
) -> dict[str, str]:
    return {
        "election_date": f"{year}-10-13",
        "election_type": "parliamentary",
        "round": "1",
        "source_teryt": teryt,
        "gmina_name": "m. Bolesławiec",
        "committee_source_name": committee,
        "votes": votes,
    }


def write_interim_year(
    interim_dir: Path,
    year: int,
    totals: list[dict[str, str]],
    committees: list[dict[str, str]],
) -> None:
    write_csv(
        interim_dir / f"{year}-sejm-gmina-totals.csv",
        list(totals[0]),
        totals,
    )
    write_csv(
        interim_dir / f"{year}-sejm-committee-results.csv",
        list(committees[0]),
        committees,
    )


def transform(interim_dir: Path, processed_dir: Path) -> object:
    return electoral_ingestion.transform_sejm_interim_to_processed(interim_dir, processed_dir)


def test_transform_creates_import_ready_results_and_latest_regions(tmp_path: Path) -> None:
    interim_dir = tmp_path / "interim"
    processed_dir = tmp_path / "processed"
    ko_2019 = "KOALICYJNY KOMITET WYBORCZY KOALICJA OBYWATELSKA PO .N IPL ZIELONI - ZPOW-601-6/19"
    pis_2019 = "KOMITET WYBORCZY PRAWO I SPRAWIEDLIWOŚĆ - ZPOW-601-9/19"
    write_interim_year(
        interim_dir,
        2019,
        [totals_row()],
        [committee_row(ko_2019, "30"), committee_row(pis_2019, "45")],
    )
    write_interim_year(
        interim_dir,
        2023,
        [
            totals_row(
                year=2023,
                name="Bolesławiec",
                eligible_voters="200",
                ballots_issued="150",
                valid_votes="140",
            )
        ],
        [
            committee_row(
                "KOALICYJNY KOMITET WYBORCZY KOALICJA OBYWATELSKA PO .N IPL ZIELONI",
                "60",
                year=2023,
            ),
            committee_row(
                "KOMITET WYBORCZY PRAWO I SPRAWIEDLIWOŚĆ",
                "80",
                year=2023,
            ),
        ],
    )

    summary = transform(interim_dir, processed_dir)

    assert summary.elections_processed == 2
    results = read_csv(processed_dir / "2019-sejm-gminy.csv")
    assert results[0] == {
        "election_date": "2019-10-13",
        "election_type": "parliamentary",
        "round": "1",
        "description": "Sejm 2019",
        "teryt_code": "020101",
        "committee_name": "Koalicja Obywatelska",
        "bloc_name": "ko_bloc",
        "votes": "30",
        "vote_share": "40.0000",
        "turnout": "80.0000",
        "eligible_voters": "100",
        "valid_votes": "75",
    }
    assert read_csv(processed_dir / "regions.csv") == [
        {
            "teryt_code": "020101",
            "name": "Bolesławiec",
            "region_type": "municipality",
            "voivodeship": "dolnośląskie",
            "valid_from": "",
            "valid_to": "",
        }
    ]


def test_transform_rejects_unknown_committee(tmp_path: Path) -> None:
    interim_dir = tmp_path / "interim"
    write_interim_year(
        interim_dir,
        2019,
        [totals_row(valid_votes="10")],
        [committee_row("NIEZNANY KOMITET", "10")],
    )

    with pytest.raises(ValueError, match="Unknown committee"):
        transform(interim_dir, tmp_path / "processed")


def test_transform_rejects_committee_sum_different_from_valid_votes(tmp_path: Path) -> None:
    interim_dir = tmp_path / "interim"
    write_interim_year(
        interim_dir,
        2019,
        [totals_row(valid_votes="11")],
        [
            committee_row(
                "KOMITET WYBORCZY PRAWO I SPRAWIEDLIWOŚĆ - ZPOW-601-9/19",
                "10",
            )
        ],
    )

    with pytest.raises(ValueError, match="sum to 10, expected 11"):
        transform(interim_dir, tmp_path / "processed")


def test_transform_normalizes_municipality_prefix_and_handles_zero_totals(
    tmp_path: Path,
) -> None:
    interim_dir = tmp_path / "interim"
    write_interim_year(
        interim_dir,
        2015,
        [
            totals_row(
                year=2015,
                name="gm. Bolesławiec",
                eligible_voters="0",
                ballots_issued="0",
                valid_votes="0",
            )
        ],
        [
            committee_row(
                "1 - Komitet Wyborczy Prawo i Sprawiedliwość",
                "0",
                year=2015,
            )
        ],
    )

    transform(interim_dir, tmp_path / "processed")

    assert read_csv(tmp_path / "processed" / "regions.csv")[0]["name"] == "Bolesławiec"
    result = read_csv(tmp_path / "processed" / "2015-sejm-gminy.csv")[0]
    assert result["vote_share"] == ""
    assert result["turnout"] == ""
