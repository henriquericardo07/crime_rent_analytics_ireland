import json
import pandas as pd
import requests
from .config import RENT_JSON_URL, RAW_RENT_DIR
from .db import get_mongo_db, get_postgres_engine

def download_rent_json() -> str:
    """It makes a request to the JSON endpoint and saves it to disk."""
    resp = requests.get(RENT_JSON_URL)
    resp.raise_for_status()
    data = resp.json()

    path = RAW_RENT_DIR / "rent_data.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return str(path)

def load_rent_to_mongo(json_path: str):
    db = get_mongo_db()
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Assume that data is a list of records; if not, adjust here:
    if isinstance(data, dict):
        # e.g., {"records": [...]} etc
        records = data.get("records", [])
    else:
        records = data

    if not records:
        return 0

    result = db.rent_raw.insert_many(records)
    return len(result.inserted_ids)

def flatten_rent_from_mongo_to_postgres():
    """Reads JSON from MongoDB, normalizes with pandas, and writes to Postgres as rent_raw."""
    db = get_mongo_db()
    docs = list(db.rent_raw.find())
    if not docs:
        return 0

    # Remove the _id from Mongo
    for d in docs:
        d.pop("_id", None)

    df = pd.DataFrame(docs)

    # Adjust column names to standard schema
    mapping = {
        "county_name": "county",
        "year": "year",
        "quarter": "quarter",
        "median_rent": "median_rent",
    }
    df = df.rename(columns=mapping)

    # If dates are in a single field, you can extract year/quarter here.
    engine = get_postgres_engine()
    df[["county", "year", "quarter", "median_rent"]].to_sql(
        "rent_raw", engine, if_exists="append", index=False
    )
    return len(df)
