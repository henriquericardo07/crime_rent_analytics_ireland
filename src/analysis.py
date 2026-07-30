import pandas as pd
from .db import get_postgres_engine

def load_integrated_df():
    engine = get_postgres_engine()
    df = pd.read_sql("SELECT * FROM social_integrated", engine)
    return df

def compute_basic_stats():
    df = load_integrated_df()
    # Correlation between crime_total and median_rent
    corr = df["crime_total"].corr(df["median_rent"])

    # ranking of counties by average crime_total
    county_stats = (
        df.groupby("county", as_index=False)
        .agg(
            crime_mean=("crime_total", "mean"),
            rent_mean=("median_rent", "mean"),
        )
        .sort_values("crime_mean", ascending=False)
    )

    # We can return a dictionary of results
    return {
        "correlation_crime_rent": corr,
        "county_stats": county_stats,
    }

def prepare_timeseries():
    df = load_integrated_df()
    # Annual aggregation (sum crime, average rent)
    ts = (
        df.groupby(["year"], as_index=False)
        .agg(
            crime_total=("crime_total", "sum"),
            rent_mean=("median_rent", "mean"),
        )
        .sort_values("year")
    )
    return ts
