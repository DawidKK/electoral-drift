import csv
from pathlib import Path

from electoral_ingestion.sejm_interim import transform_sejm_raw_to_interim


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def test_transform_2019_creates_totals_and_long_committee_results(tmp_path: Path) -> None:
    raw_path = tmp_path / "2019-sejm.csv"
    raw_path.write_text(
        '"Kod TERYT";"Gmina";"Powiat";"Województwo";'
        '"Liczba wyborców uprawnionych do głosowania";'
        '"Liczba wyborców, którym wydano karty do głosowania";'
        '"Liczba głosów ważnych oddanych łącznie na wszystkie listy kandydatów";'
        '"KOMITET A";"KOMITET B"\n'
        '"020101";"m. Bolesławiec";"bolesławiecki";"dolnośląskie";'
        '"29\u00a0895";"18\u00a0201";"17\u00a0989";"4\u00a0308";"0"\n',
        encoding="utf-8",
    )

    summary = transform_sejm_raw_to_interim(raw_path, tmp_path / "interim")

    assert summary.year == 2019
    assert summary.municipalities_written == 1
    assert summary.committee_results_written == 2
    assert summary.rows_without_teryt_skipped == 0

    totals = read_csv_rows(summary.totals_path)
    assert totals == [
        {
            "election_date": "2019-10-13",
            "election_type": "parliamentary",
            "round": "1",
            "source_teryt": "020101",
            "gmina_name": "m. Bolesławiec",
            "powiat_name": "bolesławiecki",
            "voivodeship": "dolnośląskie",
            "eligible_voters": "29895",
            "ballots_issued": "18201",
            "valid_votes": "17989",
        }
    ]
    assert read_csv_rows(summary.committee_results_path) == [
        {
            "election_date": "2019-10-13",
            "election_type": "parliamentary",
            "round": "1",
            "source_teryt": "020101",
            "gmina_name": "m. Bolesławiec",
            "committee_source_name": "KOMITET A",
            "votes": "4308",
        },
        {
            "election_date": "2019-10-13",
            "election_type": "parliamentary",
            "round": "1",
            "source_teryt": "020101",
            "gmina_name": "m. Bolesławiec",
            "committee_source_name": "KOMITET B",
            "votes": "0",
        },
    ]


def test_transform_2023_skips_foreign_rows_without_teryt(tmp_path: Path) -> None:
    raw_path = tmp_path / "2023-sejm.csv"
    raw_path.write_text(
        '\ufeff"TERYT Gminy";"Gmina";"Powiat";"Województwo";'
        '"Liczba wyborców uprawnionych do głosowania";'
        '"Liczba wyborców, którym wydano karty do głosowania w lokalu wyborczym oraz '
        'w głosowaniu korespondencyjnym (łącznie)";'
        '"Liczba głosów ważnych oddanych łącznie na wszystkie listy kandydatów";'
        '"KOMITET A"\n'
        ';"Albania";"zagranica";;"855";"815";"811";"378"\n'
        '"20101";"m. Bolesławiec";"bolesławiecki";"dolnośląskie";'
        '"30000";"20000";"19800";"5000"\n',
        encoding="utf-8",
    )

    summary = transform_sejm_raw_to_interim(raw_path, tmp_path / "interim")

    assert summary.municipalities_written == 1
    assert summary.committee_results_written == 1
    assert summary.rows_without_teryt_skipped == 1
    assert read_csv_rows(summary.totals_path)[0]["source_teryt"] == "020101"


def test_transform_2015_normalizes_dash_as_missing_value(tmp_path: Path) -> None:
    raw_path = tmp_path / "2015-sejm.csv"
    raw_path.write_text(
        "TERYT,Gmina,Liczba wyborców,Wydane karty,Głosy ważne,"
        "1 - Komitet Wyborczy A,2 - Komitet Wyborczy B\n"
        "020101,m. Bolesławiec,31\u00a0388,15\u00a0363,15\u00a0005,4\u00a0579,-\n",
        encoding="utf-8",
    )

    summary = transform_sejm_raw_to_interim(raw_path, tmp_path / "interim")

    assert summary.municipalities_written == 1
    assert summary.committee_results_written == 1
    assert read_csv_rows(summary.committee_results_path)[0]["votes"] == "4579"


def test_transform_skips_special_pkw_regions_with_synthetic_teryt(tmp_path: Path) -> None:
    raw_path = tmp_path / "2019-sejm.csv"
    raw_path.write_text(
        '"Kod TERYT";"Gmina";"Powiat";"Województwo";'
        '"Liczba wyborców uprawnionych do głosowania";'
        '"Liczba wyborców, którym wydano karty do głosowania";'
        '"Liczba głosów ważnych oddanych łącznie na wszystkie listy kandydatów";'
        '"KOMITET A"\n'
        '"149801";"statki";"statki";"mazowieckie";"10";"10";"10";"10"\n'
        '"149901";"zagranica";"zagranica";"mazowieckie";"20";"20";"20";"20"\n'
        '"020101";"m. Bolesławiec";"bolesławiecki";"dolnośląskie";'
        '"100";"80";"75";"75"\n',
        encoding="utf-8",
    )

    summary = transform_sejm_raw_to_interim(raw_path, tmp_path / "interim")

    assert summary.municipalities_written == 1
    assert summary.special_rows_skipped == 2
    assert read_csv_rows(summary.totals_path)[0]["source_teryt"] == "020101"
