from electoral_db.canonical_regions import build_canonical_region_groups


def test_groups_historical_teryt_versions_and_uses_latest_name() -> None:
    groups = build_canonical_region_groups(
        [
            (1, "0603112", "Stara nazwa", 2015),
            (2, "0603113", "Siedliszcze", 2019),
            (3, "0218032", "Miękinia", 2019),
        ]
    )

    assert groups == {
        "060311": {"name": "Siedliszcze", "region_ids": (1, 2)},
        "021803": {"name": "Miękinia", "region_ids": (3,)},
    }


def test_uses_region_id_as_stable_tiebreaker_for_equal_latest_year() -> None:
    groups = build_canonical_region_groups(
        [
            (10, "0603112", "Earlier id", 2019),
            (11, "0603113", "Later id", 2019),
        ]
    )

    assert groups["060311"]["name"] == "Later id"


def test_rejects_teryt_without_seven_digits() -> None:
    try:
        build_canonical_region_groups([(1, "060311", "Siedliszcze", 2019)])
    except ValueError as exc:
        assert str(exc) == "TERYT code must contain exactly 7 digits: 060311"
    else:
        raise AssertionError("invalid TERYT code was accepted")
