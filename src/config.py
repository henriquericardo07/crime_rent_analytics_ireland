import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

load_dotenv(BASE_DIR / ".env")

def get_env_var(name: str, default=None):
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Environment variable {name} is not set")
    return value

POSTGRES_CONFIG = {
    "host": get_env_var("POSTGRES_HOST"),
    "port": get_env_var("POSTGRES_PORT"),
    "database": get_env_var("POSTGRES_DB"),
    "user": get_env_var("POSTGRES_USER"),
    "password": get_env_var("POSTGRES_PASSWORD"),
}

MONGO_URI = get_env_var("MONGO_URI")
MONGO_DB_NAME = get_env_var("MONGO_DB")

CRIME_CSV_URL = get_env_var("CRIME_CSV_URL")
RENT_JSON_URL = get_env_var("RENT_JSON_URL")

DATA_DIR = Path(get_env_var("DATA_DIR", BASE_DIR / "data"))
RAW_CRIME_DIR = DATA_DIR / "raw" / "crime"
RAW_RENT_DIR = DATA_DIR / "raw" / "rent"
PROCESSED_DIR = DATA_DIR / "processed"

for d in [RAW_CRIME_DIR, RAW_RENT_DIR, PROCESSED_DIR]:
    d.mkdir(parents=True, exist_ok=True)
