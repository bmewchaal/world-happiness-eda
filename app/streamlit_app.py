from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="World Happiness Explorer", page_icon="🌍", layout="wide")

DATA = Path(__file__).resolve().parent.parent / "data" / "processed" / "merged.csv"
if not DATA.exists():
    st.error("Processed dataset not found. Run `python -m scripts.data_prep` first (see README).")
    st.stop()


@st.cache_data
def load() -> pd.DataFrame:
    return pd.read_csv(DATA)


df = load()

LABELS = {
    "happiness_score": "Happiness score",
    "gdp_per_capita_ppp": "GDP per capita (PPP $)",
    "life_expectancy": "Life expectancy (years)",
    "gdp_index": "GDP component",
    "social_support": "Social support",
    "health_index": "Health component",
    "freedom": "Freedom",
    "generosity": "Generosity",
    "trust_in_government": "Trust in government",
    "health_expenditure_pct": "Health expenditure (% GDP)",
    "unemployment_pct": "Unemployment (%)",
}

st.title("🌍 World Happiness Explorer")
st.caption("World Happiness Report 2015–2019 merged with World Bank indicators.")

years = sorted(df["year"].unique())
regions = sorted(df["region"].dropna().unique())
year = st.sidebar.select_slider("Year", options=years, value=years[-1])
picked = st.sidebar.multiselect("Regions", regions, default=regions)

view = df[(df["year"] == year) & (df["region"].isin(picked))]
if view.empty:
    st.warning("No countries match the current filters.")
    st.stop()

c1, c2, c3 = st.columns(3)
c1.metric("Countries", len(view))
c2.metric("Average score", f"{view['happiness_score'].mean():.2f}")
best = view.loc[view["happiness_score"].idxmax()]
c3.metric("Happiest", best["country"], f"{best['happiness_score']:.2f}", delta_color="off")

tab_rank, tab_rel, tab_country = st.tabs(["Ranking", "Relationships", "Country trend"])

with tab_rank:
    n = st.slider("Countries to show", 5, 30, 10)
    left, right = st.columns(2)
    top = view.nlargest(n, "happiness_score").sort_values("happiness_score")
    bottom = view.nsmallest(n, "happiness_score").sort_values("happiness_score", ascending=False)
    left.plotly_chart(px.bar(top, x="happiness_score", y="country", orientation="h", title=f"Top {n}"), width="stretch")
    right.plotly_chart(px.bar(bottom, x="happiness_score", y="country", orientation="h", title=f"Bottom {n}", color_discrete_sequence=["#d65a4a"]), width="stretch")

with tab_rel:
    options = [c for c in LABELS if c != "happiness_score" and c in view.columns]
    x = st.selectbox("X axis", options, format_func=LABELS.get)
    plot = view.dropna(subset=[x])
    log_x = x == "gdp_per_capita_ppp" and st.checkbox("Log scale", value=True)
    fig = px.scatter(
        plot, x=x, y="happiness_score", color="region", hover_name="country",
        log_x=log_x, labels=LABELS, trendline=None,
    )
    st.plotly_chart(fig, width="stretch")
    if len(plot) > 2:
        st.caption(f"Pearson correlation with score: {plot[x].corr(plot['happiness_score']):.2f} (n = {len(plot)})")

with tab_country:
    country = st.selectbox("Country", sorted(df["country"].unique()), index=0)
    metric = st.selectbox("Metric", [c for c in LABELS if c in df.columns], format_func=LABELS.get)
    spot = df[df["country"] == country].sort_values("year")
    st.plotly_chart(px.line(spot, x="year", y=metric, markers=True, labels=LABELS, title=f"{country}: {LABELS[metric]}"), width="stretch")

with st.expander("View data"):
    st.dataframe(view.sort_values("happiness_score", ascending=False), width="stretch")
