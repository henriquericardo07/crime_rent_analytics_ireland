from dagster import (
    Definitions,
    job,
    op,
    ConfigurableResource,
    get_dagster_logger,
)
from src.db import init_postgres_schema
from src.ingest_crime import download_crime_csv, load_crime_to_postgres
from src.ingest_rent import (
    download_rent_json,
    load_rent_to_mongo,
    flatten_rent_from_mongo_to_postgres,
)
from src.transform import integrate_crime_rent
from src.analysis import compute_basic_stats
from src.viz import plot_scatter_crime_vs_rent, plot_timeseries

logger = get_dagster_logger()

# --- Resources Creation ---

class EnvironmentResource(ConfigurableResource):
    """Placeholder for shared configurations in the future"""

    env_name: str = "local"


env_resource = EnvironmentResource()

# --- OPS ---

@op
def op_init_schema():
    logger.info("Initializing Postgres schema...")
    init_postgres_schema()
    logger.info("Schema created/updated successfully.")


@op
def op_ingest_crime():
    logger.info("Download crime dataset...")
    path = download_crime_csv()
    logger.info(f"Crime CSV stored in: {path}")
    n_rows = load_crime_to_postgres(path)
    logger.info(f"Were uploaded {n_rows} Crime records to Postgres.")
    return n_rows


@op
def op_ingest_rent():
    logger.info("Download rent dataset (JSON)...")
    path = download_rent_json()
    logger.info(f"Rent JSON saved in: {path}")
    n_mongo = load_rent_to_mongo(path)
    logger.info(f"Were inserted {n_mongo} JSON documents into MongoDB.")
    n_pg = flatten_rent_from_mongo_to_postgres()
    logger.info(f"Were loaded {n_pg} rent records into Postgres.")
    return n_pg


@op
def op_integrate():
    logger.info("Integrating crime & rent into the social_integrated table...")
    n_rows = integrate_crime_rent()
    logger.info(f"{n_rows} rows integrated into social_integrated.")
    return n_rows


@op
def op_run_analysis():
    logger.info("Running statistical analysis...")
    stats = compute_basic_stats()
    corr = stats["correlation_crime_rent"]
    logger.info(f"Correlation crime_total x median_rent: {corr:.3f}")
    logger.info("Top 5 counties by average crime:")
    logger.info(stats["county_stats"].head().to_string())
    return corr


@op
def op_generate_plots():
    logger.info("Generating visualizations...")
    scatter = plot_scatter_crime_vs_rent()
    ts = plot_timeseries()
    logger.info(f"Visualizations generated: {scatter}, {ts}")
    return {"scatter": scatter, "timeseries": ts}


# --- JOB (main pipeline) ---
@job(resource_defs={"env": env_resource})
def ireland_social_analysis_pipeline():
    op_init_schema()
    op_ingest_crime()
    op_ingest_rent()
    op_integrate()
    op_run_analysis()
    op_generate_plots()


# --- Definitions for dagster dev / dagster-daemon ---

defs = Definitions(
    jobs=[ireland_social_analysis_pipeline],
    resources={"env": env_resource},
)
