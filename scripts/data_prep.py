"""Load, harmonise and merge the raw datasets into one tidy table.

Sources (all expected in ``data/raw/``):
  * ``2015.csv`` ... ``2019.csv``  - World Happiness Report (Kaggle), one file per year,
    each with slightly different column names.
  * ``gdp-per-capita-worldbank.csv`` - GDP per capita, PPP (Our World in Data / World Bank).
  * ``life expectancy.csv`` - World Bank development indicators (life expectancy, health
    spending, unemployment, ...), keyed by ISO country code.

Run ``python -m scripts.data_prep`` from the project root to write
``data/processed/merged.csv``.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

YEARS = range(2015, 2020)
GDP_COLUMN = "GDP per capita, PPP (constant 2021 international $)"

# Each report year names its columns differently; map them all onto one schema.
COLUMN_MAP = {
    "Country": "country",
    "Country or region": "country",
    "Region": "region",
    "Happiness Score": "happiness_score",
    "Happiness.Score": "happiness_score",
    "Score": "happiness_score",
    "Economy (GDP per Capita)": "gdp_index",
    "Economy..GDP.per.Capita.": "gdp_index",
    "GDP per capita": "gdp_index",
    "Family": "social_support",
    "Social support": "social_support",
    "Health (Life Expectancy)": "health_index",
    "Health..Life.Expectancy.": "health_index",
    "Healthy life expectancy": "health_index",
    "Freedom": "freedom",
    "Freedom to make life choices": "freedom",
    "Generosity": "generosity",
    "Trust (Government Corruption)": "trust_in_government",
    "Trust..Government.Corruption.": "trust_in_government",
    "Perceptions of corruption": "trust_in_government",
}
SCORE_COLUMNS = [
    "happiness_score", "gdp_index", "social_support", "health_index",
    "freedom", "generosity", "trust_in_government",
]

# Happiness-report spellings -> the spelling used by the GDP file.
COUNTRY_ALIASES = {
    "Congo (Brazzaville)": "Congo",
    "Congo (Kinshasa)": "Democratic Republic of Congo",
    "Czech Republic": "Czechia",
    "Hong Kong S.A.R., China": "Hong Kong",
    "Ivory Coast": "Cote d'Ivoire",
    "Macedonia": "North Macedonia",
    "North Cyprus": "Northern Cyprus",
    "Palestinian Territories": "Palestine",
    "Somaliland Region": "Somaliland",
    "Somaliland region": "Somaliland",
    "Swaziland": "Eswatini",
    "Taiwan Province of China": "Taiwan",
    "Trinidad & Tobago": "Trinidad and Tobago",
}
# Countries the GDP file does not list, so their ISO code cannot be looked up there.
EXTRA_ISO = {"Taiwan": "TWN", "Venezuela": "VEN", "Yemen": "YEM", "South Sudan": "SSD"}

WB_COLUMNS = {
    "Life Expectancy World Bank": "life_expectancy",
    "Health Expenditure %": "health_expenditure_pct",
    "Unemployment": "unemployment_pct",
    "Prevelance of Undernourishment": "undernourishment_pct",
    "Sanitation": "sanitation_pct",
    "IncomeGroup": "income_group",
    "Region": "wb_region",
}


def clean_country(name: str) -> str:
    """Strip whitespace and map known alternative spellings to one canonical name."""
    name = str(name).strip()
    return COUNTRY_ALIASES.get(name, name)


def load_happiness_year(year: int, raw_dir: Path = RAW) -> pd.DataFrame:
    """Load one World Happiness Report file and normalise it to the common schema."""
    df = pd.read_csv(raw_dir / f"{year}.csv")
    df = df.rename(columns={k: v for k, v in COLUMN_MAP.items() if k in df.columns})
    df["country"] = df["country"].map(clean_country)
    df["year"] = year
    keep = ["country", "year"] + (["region"] if "region" in df.columns else []) + SCORE_COLUMNS
    df = df[[c for c in keep if c in df.columns]].copy()
    for col in SCORE_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def load_happiness(years=YEARS, raw_dir: Path = RAW) -> pd.DataFrame:
    """Stack every yearly report into one dataframe (one row per country-year)."""
    out = pd.concat([load_happiness_year(y, raw_dir) for y in years], ignore_index=True)
    # Only 2015/2016 carry a region; propagate it to the other years by country.
    region_by_country = out.dropna(subset=["region"]).drop_duplicates("country").set_index("country")["region"]
    out["region"] = out["region"].fillna(out["country"].map(region_by_country))
    return out


def load_gdp(raw_dir: Path = RAW) -> pd.DataFrame:
    """GDP per capita (PPP), tidy: country, iso_code, year, gdp_per_capita_ppp."""
    df = pd.read_csv(raw_dir / "gdp-per-capita-worldbank.csv")
    return df.rename(columns={"Entity": "country", "Code": "iso_code", "Year": "year", GDP_COLUMN: "gdp_per_capita_ppp"})


def load_worldbank(raw_dir: Path = RAW) -> pd.DataFrame:
    """World Bank indicators, tidy: iso_code, year, plus the columns in WB_COLUMNS."""
    df = pd.read_csv(raw_dir / "life expectancy.csv")
    df = df.rename(columns={"Country Code": "iso_code", "Year": "year", **WB_COLUMNS})
    return df[["iso_code", "year", *WB_COLUMNS.values()]]


def merge_frames(happiness: pd.DataFrame, gdp: pd.DataFrame, worldbank: pd.DataFrame) -> pd.DataFrame:
    """Left-join GDP and World Bank indicators onto the happiness table."""
    iso = gdp.drop_duplicates("country").set_index("country")["iso_code"].to_dict()
    iso.update(EXTRA_ISO)
    out = happiness.copy()
    out["iso_code"] = out["country"].map(iso)
    out = out.merge(gdp[["country", "year", "gdp_per_capita_ppp"]], on=["country", "year"], how="left")
    out = out.merge(worldbank, on=["iso_code", "year"], how="left")
    out["happiness_rank"] = out.groupby("year")["happiness_score"].rank(ascending=False, method="min").astype("Int64")
    return out


def build_dataset(raw_dir: Path = RAW) -> pd.DataFrame:
    """Full pipeline: load every source and return the merged table."""
    return merge_frames(load_happiness(raw_dir=raw_dir), load_gdp(raw_dir), load_worldbank(raw_dir))


def save_processed(df: pd.DataFrame, name: str = "merged.csv") -> Path:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    fp = PROCESSED / name
    df.to_csv(fp, index=False)
    return fp


if __name__ == "__main__":
    merged = build_dataset()
    print(f"Saved {len(merged)} rows to {save_processed(merged)}")
