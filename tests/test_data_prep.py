import pandas as pd
import pytest

from scripts import data_prep


@pytest.fixture(scope="module")
def merged():
    if not (data_prep.RAW / "2019.csv").exists():
        pytest.skip("raw data not downloaded")
    return data_prep.build_dataset()


def test_clean_country_maps_aliases_and_strips():
    assert data_prep.clean_country("  Ivory Coast ") == "Cote d'Ivoire"
    assert data_prep.clean_country("Finland") == "Finland"


def test_every_year_uses_the_common_schema():
    if not (data_prep.RAW / "2015.csv").exists():
        pytest.skip("raw data not downloaded")
    for year in data_prep.YEARS:
        df = data_prep.load_happiness_year(year)
        assert {"country", "year", "happiness_score", "gdp_index", "freedom"} <= set(df.columns)
        assert (df["year"] == year).all()


def test_no_duplicate_country_years(merged):
    assert not merged.duplicated(["country", "year"]).any()


def test_scores_are_in_range_and_complete(merged):
    assert merged["happiness_score"].between(0, 10).all()
    assert merged["happiness_score"].notna().all()


def test_rank_is_per_year(merged):
    top = merged[merged["happiness_rank"] == 1]
    assert sorted(top["year"]) == list(data_prep.YEARS)


def test_merge_adds_external_indicators(merged):
    finland = merged[(merged["country"] == "Finland") & (merged["year"] == 2019)].iloc[0]
    assert finland["gdp_per_capita_ppp"] > 40000
    assert 78 < finland["life_expectancy"] < 85


def test_merge_frames_keeps_all_happiness_rows():
    happiness = pd.DataFrame({"country": ["A", "B"], "year": [2019, 2019], "happiness_score": [7.0, 4.0]})
    gdp = pd.DataFrame({"country": ["A"], "iso_code": ["AAA"], "year": [2019], "gdp_per_capita_ppp": [1000.0]})
    wb = pd.DataFrame({"iso_code": ["AAA"], "year": [2019], "life_expectancy": [80.0]})
    out = data_prep.merge_frames(happiness, gdp, wb)
    assert len(out) == 2
    assert out.loc[out["country"] == "B", "gdp_per_capita_ppp"].isna().all()
