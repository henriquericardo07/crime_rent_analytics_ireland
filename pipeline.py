# pipeline.py
"""
Dagster job to visually demonstrathe the orchestration.
Represents the ETL of:
- Crime ingestion
- Revenue ingestion
- combined dashboard creation
"""

from dagster import job, op


@op
def ingest_crime_op():
    # Here, in a real scenario, you might read crime_data.csv and write to Postgres.
    # For academic purposes (and for the UI), a print statement suffices.
    print("Crime data ingestion (crime_data.csv) completed.")
    return "crime_ok"


@op
def ingest_rent_op():
    # Here, this would be the ingestion of rent_data.JSON to Mongo/Postgres.
    print("Rent data ingestion (rent_data.JSON) completed.")
    return "rent_ok"


@op
def build_panel_op(crime_status: str, rent_status: str):
    # Here, normally, you would do joins, aggregations, and create crime_rent_panel.
    print(f"Building crime+rent panel with statuses: {crime_status}, {rent_status}")
    return "panel_ok"


@op
def quality_check_op(panel_status: str):
    # Basic quality checks: record counts, nulls, etc.
    print(f"Quality checks on panel: {panel_status}")
    return "checks_ok"


@job
def ireland_social_job():
    """
    Orchestration:
    1) ingest_crime_op
    2) ingest_rent_op
    3) build_panel_op
    4) quality_check_op
    """
    crime_res = ingest_crime_op()
    rent_res = ingest_rent_op()
    panel_res = build_panel_op(crime_res, rent_res)
    quality_check_op(panel_res)
