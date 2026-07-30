import streamlit as st
import pandas as pd
from pathlib import Path
from src.analysis import load_integrated_df, compute_basic_stats
from src.config import PROCESSED_DIR

st.set_page_config(page_title="Crime & Housing in Ireland", layout="wide")

st.title("Crime & Housing in Ireland – Social Insights Dashboard")

df = load_integrated_df()
stats = compute_basic_stats()

st.subheader("Statistical Summary")
st.write(f"Correlation crime_total x median_rent: **{stats['correlation_crime_rent']:.3f}**")

st.subheader("Integrated Dataset (sample)")
st.dataframe(df.head(50))

st.subheader("Ranking of counties by average crime")
st.dataframe(stats["county_stats"].head(20))

scatter_path = PROCESSED_DIR / "scatter_crime_vs_rent.png"
ts_path = PROCESSED_DIR / "timeseries_crime_rent.png"

if scatter_path.exists():
    st.image(str(scatter_path), caption="Crime vs Rent")
if ts_path.exists():
    st.image(str(ts_path), caption="Time series crime & rent")