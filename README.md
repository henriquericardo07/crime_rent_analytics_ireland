# Crime and Rent Analytics in Ireland

## Project Overview

This project examines the relationship between recorded crime levels and rental prices across Irish counties over time.

The solution integrates crime data from the Central Statistics Office and rental market data from the Residential Tenancies Board into a consolidated county-year analytical dataset.

## Research Question

To what extent is there a relationship between recorded crime levels and rental prices across Irish counties over time?

## Objectives

- Integrate crime and rental datasets from different formats.
- Standardise geographical and temporal fields.
- Create a consolidated county-year analytical database.
- Build an automated data pipeline using Dagster.
- Store structured data in PostgreSQL and metadata in MongoDB.
- Develop an interactive Streamlit dashboard.
- Analyse crime and rent trends across Irish counties.

## Data Sources

- CSO Recorded Crime Offences
- RTB Rent Index

## Technology Stack

- Python
- Pandas
- PostgreSQL
- MongoDB
- Dagster
- Streamlit
- Plotly

## Pipeline

1. Extract crime CSV and rental JSON data.
2. Clean and standardise columns.
3. Map Garda divisions to Irish counties.
4. Aggregate records by county and year.
5. Load analytical tables into PostgreSQL.
6. Store pipeline metadata in MongoDB.
7. Orchestrate the process using Dagster.
8. Visualise results through Streamlit.

## Key Findings

- The analysis identified a weak-to-moderate positive correlation of approximately 0.51 between crime incidents and rental prices.
- Dublin recorded the highest levels of both crime incidents and rent.
- Cork, Galway and Limerick appeared as secondary urban hotspots.
- Rural counties generally recorded lower rental prices and fewer incidents.
- The relationship should not be interpreted as causal because population density, urbanisation and socioeconomic factors may affect both variables.

## Limitations

- County-level aggregation may hide neighbourhood-level patterns.
- Population and socioeconomic variables were not included.
- Garda divisions required manual geographical mapping.
- Correlation does not imply causation.

## Future Work

- Add Census and population data.
- Calculate crime rates per capita.
- Apply panel regression and time-series models.
- Add crime forecasting.
- Deploy the pipeline and dashboard to the cloud.
