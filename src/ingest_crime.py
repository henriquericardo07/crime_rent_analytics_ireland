import pandas as pd
import requests
from .config import CRIME_CSV_URL, RAW_CRIME_DIR
from .db import get_postgres_engine

def download_crime_csv() -> str:
    """Downloads the crime CSV file and saves it locally; returns the path."""
    resp = requests.get(CRIME_CSV_URL)
    resp.raise_for_status()
    path = RAW_CRIME_DIR / "crime_data.csv"
    with open(path, "wb") as f:
        f.write(resp.content)
    return str(path)

def load_crime_to_postgres(csv_path: str):
    df = pd.read_csv(csv_path)
    # Here assumes typical columns – later adjust to the real dataset column names
    # Example of normalization:
    df = df.rename(
        columns={
            "Region": "region",
            "County": "county",
            "IncidentType": "incident_type",
            "Year": "year",
            "Quarter": "quarter",
            "Value": "value",
        }
    )
    engine = get_postgres_engine()
    df.to_sql("crime_raw", engine, if_exists="append", index=False)
    return len(df)
