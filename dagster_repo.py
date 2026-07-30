import os
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from pymongo import MongoClient

from dagster import op, job, In, Out, Definitions

# ====== REPLICATED CONFIGURATION (same as the notebook) ======
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "1234"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = "5432"
POSTGRES_DB = "ireland_social"

DATABASE_URL = (
    f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL)

MONGO_URI = "mongodb://localhost:27017"
MONGO_DB_NAME = "ireland_social"
MONGO_COLLECTION_RENT = "rent_raw_mongo"

mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client[MONGO_DB_NAME]
rent_collection = mongo_db[MONGO_COLLECTION_RENT]

BASE_DIR = Path.cwd()
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CRIME_PATH = RAW_DIR / "crime_data.csv"
RENT_PATH = RAW_DIR / "rent_data.JSON"


def clean_station_name(station: str) -> str:
    if not isinstance(station, str):
        return station
    parts = station.split(" ", 1)
    name_div = parts[1] if len(parts) > 1 else station
    if name_div.endswith(" Division"):
        name_div = name_div[: -len(" Division")]
    return name_div.strip()


def load_crime_source() -> pd.DataFrame:
    df = pd.read_csv(CRIME_PATH)
    df["station_clean"] = df["Garda Station"].astype(str).apply(clean_station_name)
    df["Year"] = df["Year"].astype(int)
    df = df[df["Year"] >= 2008].copy()
    df = df[["Year", "station_clean", "Type of Offence", "VALUE"]].rename(
        columns={
            "Year": "year",
            "station_clean": "location",
            "Type of Offence": "offence_type",
            "VALUE": "incidents",
        }
    )
    df["incidents"] = pd.to_numeric(df["incidents"], errors="coerce").fillna(0)
    return df


def load_rent_source() -> pd.DataFrame:
    import json
    with open(RENT_PATH, "r") as f:
        rent_json = json.load(f)

    dataset = rent_json["dataset"]
    dim = dataset["dimension"]
    dim_ids = dim["id"]
    sizes = dim["size"]
    values = dataset["value"]

    dim_info = {}
    for dim_id in dim_ids:
        d = dim[dim_id]
        labels = d["category"]["label"]
        index = d["category"]["index"]
        pos_to_label = {pos: labels[key] for key, pos in index.items()}
        dim_info[dim_id] = pos_to_label

    sizes_np = np.array(sizes)
    rows = []
    for i, v in enumerate(values):
        if v is None:
            continue
        coords = np.unravel_index(i, sizes_np)
        row = {"value": float(v)}
        for dim_id, pos in zip(dim_ids, coords):
            row[dim_id] = dim_info[dim_id][int(pos)]
        rows.append(row)

    df = pd.DataFrame(rows).rename(
        columns={
            "STATISTIC": "statistic",
            "TLIST(A1)": "year",
            "C02970V03592": "bedrooms",
            "C02969V03591": "property_type",
            "C03004V03625": "location",
            "value": "avg_monthly_rent",
        }
    )
    df["year"] = df["year"].astype(int)
    df_macro = df[
        (df["bedrooms"] == "All bedrooms")
        & (df["property_type"] == "All property types")
    ].copy()
    df_macro = df_macro[["year", "location", "avg_monthly_rent"]]
    df_macro["avg_monthly_rent"] = pd.to_numeric(
        df_macro["avg_monthly_rent"], errors="coerce"
    )
    df_macro = df_macro.dropna(subset=["avg_monthly_rent"])
    return df_macro


def ingest_crime_to_postgres() -> int:
    df = load_crime_source()
    with engine.begin() as conn:
        df.to_sql("crime_raw", conn, if_exists="replace", index=False)
    return len(df)


def ingest_rent_to_mongo_and_postgres() -> int:
    df = load_rent_source()
    rent_collection.delete_many({}
    )
    records = df.to_dict(orient="records")
    if records:
        rent_collection.insert_many(records)
    with engine.begin() as conn:
        df.to_sql("rent_raw", conn, if_exists="replace", index=False)
    return len(df)


def build_aggregated_panel() -> int:
    with engine.begin() as conn:
        crime = pd.read_sql(text("SELECT * FROM crime_raw"), conn)
        rent = pd.read_sql(text("SELECT * FROM rent_raw"), conn)

    crime_agg = (
        crime.groupby(["year", "location"], as_index=False)["incidents"]
        .sum()
        .rename(columns={"incidents": "total_incidents"})
    )

    rent_agg = (
        rent.groupby(["year", "location"], as_index=False)["avg_monthly_rent"]
        .mean()
        .rename(columns={"avg_monthly_rent": "avg_monthly_rent"})
    )

    panel = crime_agg.merge(
        rent_agg,
        on=["year", "location"],
        how="inner",
        validate="many_to_many",
    )

    with engine.begin() as conn:
        crime_agg.to_sql("crime_agg", conn, if_exists="replace", index=False)
        rent_agg.to_sql("rent_agg", conn, if_exists="replace", index=False)
        panel.to_sql("crime_rent_panel", conn, if_exists="replace", index=False)

    return len(panel)


@op(out=Out(int))
def op_ingest_crime():
    return ingest_crime_to_postgres()


@op(out=Out(int))
def op_ingest_rent():
    return ingest_rent_to_mongo_and_postgres()


@op(ins={"crime_count": In(int), "rent_count": In(int)}, out=Out(int))
def op_build_panel(crime_count: int, rent_count: int) -> int:
    return build_aggregated_panel()


@job
def ireland_social_job():
    c = op_ingest_crime()
    r = op_ingest_rent()
    op_build_panel(c, r)


defs = Definitions(
    jobs=[ireland_social_job],
)
