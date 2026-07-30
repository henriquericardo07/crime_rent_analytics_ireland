from sqlalchemy import create_engine, text
from pymongo import MongoClient
from .config import POSTGRES_CONFIG, MONGO_URI, MONGO_DB_NAME

def get_postgres_engine():
    user = POSTGRES_CONFIG["user"]
    password = POSTGRES_CONFIG["password"]
    host = POSTGRES_CONFIG["host"]
    port = POSTGRES_CONFIG["port"]
    db = POSTGRES_CONFIG["database"]

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    engine = create_engine(url)
    return engine

def init_postgres_schema():
    engine = get_postgres_engine()
    ddl = """
    CREATE TABLE IF NOT EXISTS crime_raw (
        id SERIAL PRIMARY KEY,
        region VARCHAR(255),
        county VARCHAR(255),
        incident_type VARCHAR(255),
        year INT,
        quarter VARCHAR(20),
        value NUMERIC
    );

    CREATE TABLE IF NOT EXISTS rent_raw (
        id SERIAL PRIMARY KEY,
        county VARCHAR(255),
        year INT,
        quarter VARCHAR(20),
        median_rent NUMERIC
    );

    CREATE TABLE IF NOT EXISTS social_integrated (
        id SERIAL PRIMARY KEY,
        county VARCHAR(255),
        year INT,
        quarter VARCHAR(20),
        crime_total NUMERIC,
        median_rent NUMERIC
    );
    """
    with engine.begin() as conn:
        conn.execute(text(ddl))

def get_mongo_client():
    client = MongoClient(MONGO_URI)
    return client

def get_mongo_db():
    client = get_mongo_client()
    return client[MONGO_DB_NAME]
