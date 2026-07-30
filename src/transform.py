import pandas as pd
from sqlalchemy import text
from .db import get_postgres_engine

def clean_crime_data():
    engine = get_postgres_engine()
    query = "SELECT * FROM crime_raw"
    df = pd.read_sql(query, engine)

    df["county"] = df["county"].str.strip().str.title()
    df["region"] = df["region"].str.strip().str.title()
    df["incident_type"] = df["incident_type"].str.strip()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.dropna(subset=["county", "year", "value"])
    df = df[df["value"] >= 0]

    # Aggregation by county-year-quarter
    agg = (
        df.groupby(["county", "year", "quarter"], as_index=False)["value"]
        .sum()
        .rename(columns={"value": "crime_total"})
    )

    # Create temporary table and then partially replace social_integrated
    return agg

def clean_rent_data():
    engine = get_postgres_engine()
    query = "SELECT * FROM rent_raw"
    df = pd.read_sql(query, engine)

    df["county"] = df["county"].str.strip().str.title()
    df["median_rent"] = pd.to_numeric(df["median_rent"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")

    df = df.dropna(subset=["county", "year", "median_rent"])
    return df

def integrate_crime_rent():
    engine = get_postgres_engine()
    crime = clean_crime_data()
    rent = clean_rent_data()

    merged = crime.merge(
        rent,
        on=["county", "year", "quarter"],
        how="inner",
        suffixes=("_crime", "_rent"),
    )

    # Clear table before inserting
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE social_integrated RESTART IDENTITY;"))

    merged[["county", "year", "quarter", "crime_total", "median_rent"]].to_sql(
        "social_integrated", engine, if_exists="append", index=False
    )
    return len(merged)
