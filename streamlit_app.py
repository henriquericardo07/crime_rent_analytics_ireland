import os

import pandas as pd
from sqlalchemy import create_engine, text
import streamlit as st
import pydeck as pdk

# ================== CONFIGURATION ==================

st.set_page_config(
    page_title="Crime & Rent Analytics - Ireland",
    layout="wide",
)

# Connection string for PostgreSQL
PG_CONN_STR = os.getenv(
    "PG_CONN_STR",
    "postgresql+psycopg2://postgres:1234@localhost:5432/ireland_social"
)

engine = create_engine(PG_CONN_STR)

# Absolute path for the crime data file
CRIME_CSV_PATH = os.path.join(os.path.dirname(__file__), "crime_data.csv")

# ================== FUNCTIONS ==================


def derive_county_from_division(division_name):
    """Simple rules to derive the county from the division."""
    if pd.isna(division_name):
        return None
    dn = str(division_name).strip()

    # Try to catch Dublin / D.M.R.
    if (
        "D.M.R." in dn
        or "Dublin Metropolitan" in dn
        or "Co Dublin" in dn
        or "Co. Dublin" in dn
        or dn.startswith("Dublin")
    ):
        return "Dublin"

    if dn.endswith("Division"):
        dn = dn[:-len("Division")].strip()

    if dn.startswith("Co. "):
        return dn.split(" ", 2)[1].strip(" .,")
    if dn.startswith("Co "):
        return dn.split(" ", 2)[1].strip(" .,")

    if "/" in dn:
        return dn.split("/", 1)[0].strip(" .,")

    return dn.split(" ", 1)[0].strip(" .,")


def parse_station_fields(s):
    """
    From 'Garda Station' does:
    - Remove the numerical code
    - Separate the station name and division
    - Derive the county
    """
    if pd.isna(s):
        return None, None, None

    parts = str(s).split(" ", 1)
    rest = parts[1] if len(parts) > 1 else s

    if "," in rest:
        station_name, division_part = rest.split(",", 1)
    else:
        station_name, division_part = rest, ""

    station_name = station_name.strip()
    division_part = division_part.strip()

    division_name = division_part
    county = derive_county_from_division(division_name)

    return station_name, division_name, county


@st.cache_data
def load_panel():
    with engine.begin() as conn:
        panel = pd.read_sql(text("SELECT * FROM crime_rent_panel"), conn)
    panel["year"] = panel["year"].astype(int)
    return panel


@st.cache_data
def load_crime_station_year():
    with engine.begin() as conn:
        stations = pd.read_sql(text("SELECT * FROM crime_station_year"), conn)
    stations["year"] = stations["year"].astype(int)
    return stations


@st.cache_data
def load_crime_raw():
    """
    Reads the original crime_data.csv to obtain:
    - incident_type (Type of Offence)
    - approximate county
    """
    if not os.path.exists(CRIME_CSV_PATH):
        st.warning(
            f"File crime_data.csv not found at {CRIME_CSV_PATH}. "
            "Place it in the same folder as streamlit_app.py."
        )
        return pd.DataFrame()

    df = pd.read_csv(CRIME_CSV_PATH)

    expected = ["Year", "Type of Offence", "Garda Station", "VALUE"]
    missing = [c for c in expected if c not in df.columns]
    if missing:
        st.error(f"Missing columns in crime CSV: {missing}")
        return pd.DataFrame()

    df = df[expected].copy()
    df.rename(
        columns={
            "Year": "year",
            "Type of Offence": "incident_type",
            "Garda Station": "garda_station",
            "VALUE": "incidents",
        },
        inplace=True,
    )

    df[["station_name", "division_name", "county"]] = df["garda_station"].apply(
        lambda s: pd.Series(parse_station_fields(s))
    )

    df = df.dropna(subset=["county"])

    df["year"] = df["year"].astype(int)
    df["incidents"] = df["incidents"].astype(float)

    return df


# ================== LOAD DATA ==================

panel = load_panel()
stations = load_crime_station_year()
crime_raw = load_crime_raw()

# ================== LAYOUT ==================

st.title(" Crime & Rent Analytics - Ireland")

st.markdown(
    """
This panel explores the relationship between **recorded crime** and **average monthly rent**
across various regions of Ireland, using data from the **Garda** and rent data (RTB/CSO).

-  See the evolution of incidents by year and county
-  Compare rent levels with crime levels
-  See **most frequent crimes by county**
-  Explore Garda stations with the most records
-  Read **automatic insights** as notes for the report
"""
)

# --- Filters in the sidebar ---

st.sidebar.header("Filters")

years = sorted(panel["year"].unique())
year_min, year_max = int(min(years)), int(max(years))

year_range = st.sidebar.slider(
    "Period (year)",
    min_value=year_min,
    max_value=year_max,
    value=(year_min, year_max),
    step=1,
)

counties = sorted(panel["county"].dropna().unique())
selected_counties = st.sidebar.multiselect(
    "Counties",
    options=counties,
    default=counties,
)

focus_county = st.sidebar.selectbox(
    "County for detailed analysis (crime types)",
    options=["(all)"] + list(counties),
    index=0,
)

# Filter for incident types (based on crime_raw)
if not crime_raw.empty:
    incident_options = sorted(crime_raw["incident_type"].dropna().unique())
    selected_incidents = st.sidebar.multiselect(
        "Incident types (incident type)",
        options=incident_options,
        default=incident_options,
        help="Applies to tables/charts based on detailed crime data.",
    )
else:
    incident_options = []
    selected_incidents = []

# Filter panel
panel_filter = panel[
    (panel["year"] >= year_range[0])
    & (panel["year"] <= year_range[1])
    & (panel["county"].isin(selected_counties))
].copy()

# Filter stations
stations_filter = stations[
    (stations["year"] >= year_range[0])
    & (stations["year"] <= year_range[1])
    & (stations["county"].isin(selected_counties))
].copy()

# Filter crime_raw for analysis of crime types
if not crime_raw.empty:
    crime_filter = crime_raw[
        (crime_raw["year"] >= year_range[0])
        & (crime_raw["year"] <= year_range[1])
        & (crime_raw["county"].isin(selected_counties))
    ].copy()

    if selected_incidents:
        crime_filter = crime_filter[crime_filter["incident_type"].isin(selected_incidents)]
else:
    crime_filter = pd.DataFrame()

# ================== KPIs ==================

total_incidents = int(panel_filter["total_incidents"].sum()) if len(panel_filter) > 0 else 0
avg_rent_global = float(panel_filter["avg_rent_eur"].mean()) if len(panel_filter) > 0 else 0.0
num_counties = panel_filter["county"].nunique()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total incidents (filtered period)", f"{total_incidents:,}")
with col2:
    st.metric("Average rent (€/month)", f"{avg_rent_global:,.0f}")
with col3:
    st.metric("Number of counties (filtered)", num_counties)

st.markdown("---")

# ================== RELATIONSHIP BETWEEN CRIME AND RENT BY COUNTY ==================
st.subheader("Relationship between crime and rent by county")

if len(panel_filter) > 0:
    county_summary = (
        panel_filter
        .groupby("county", as_index=False)
        .agg(
            total_incidents=("total_incidents", "sum"),
            mean_rent=("avg_rent_eur", "mean"),
        )
    )
    county_summary["incidents_per_100_eur_rent"] = (
        county_summary["total_incidents"] / county_summary["mean_rent"] * 100
    )

    county_summary = county_summary.sort_values("total_incidents", ascending=False)

    st.dataframe(
        county_summary,
        use_container_width=True,
    )

    st.write("**Top counties by total crime (bar chart):**")
    st.bar_chart(
        county_summary.set_index("county")["total_incidents"],
        height=300,
    )

else:
    st.info("No data for the selected filters.")

st.markdown("---")

# ================== HEATMAP: CRIME & RENT ==================
st.subheader("Heatmap: crime and rent by county")

if len(panel_filter) > 0:
    # Aggregate by county for the map
    map_df = (
        panel_filter
        .groupby("county", as_index=False)
        .agg(
            total_incidents=("total_incidents", "sum"),
            avg_rent_eur=("avg_rent_eur", "mean"),
        )
    )

    # Approximate coordinates of counties (center of the county)
    COUNTY_COORDS = {
        "Carlow": (52.8365, -6.9341),
        "Cavan": (53.9890, -7.3600),
        "Clare": (52.9045, -8.9812),
        "Cork": (51.8985, -8.4756),
        "Donegal": (54.6540, -8.1100),
        "Dublin": (53.3498, -6.2603),
        "Galway": (53.2707, -9.0568),
        "Kerry": (52.1545, -9.5669),
        "Kildare": (53.1589, -6.9090),
        "Kilkenny": (52.6541, -7.2448),
        "Laois": (53.0320, -7.3000),
        "Leitrim": (54.3090, -8.0000),
        "Limerick": (52.6680, -8.6305),
        "Longford": (53.7275, -7.8000),
        "Louth": (53.9500, -6.5400),
        "Mayo": (53.9000, -9.3000),
        "Meath": (53.6050, -6.6550),
        "Monaghan": (54.2490, -6.9680),
        "Offaly": (53.2000, -7.5000),
        "Roscommon": (53.6330, -8.2000),
        "Sligo": (54.2747, -8.4761),
        "Tipperary": (52.4730, -7.8740),
        "Waterford": (52.2593, -7.1101),
        "Westmeath": (53.5330, -7.3500),
        "Wexford": (52.3369, -6.4633),
        "Wicklow": (52.9800, -6.0400),
    }

    map_df["coords"] = map_df["county"].map(COUNTY_COORDS)
    map_df = map_df[map_df["coords"].notna()].copy()

    if len(map_df) > 0:
        map_df["lat"] = map_df["coords"].apply(lambda c: c[0])
        map_df["lon"] = map_df["coords"].apply(lambda c: c[1])

        st.markdown(
            "Areas with more intense color represent **higher number of incidents**. "
            "Hovering over shows the county, total incidents, and average rent."
        )

        view_state = pdk.ViewState(
            latitude=53.4,
            longitude=-8.2,
            zoom=6,
            pitch=0,
        )

        heatmap_layer = pdk.Layer(
            "HeatmapLayer",
            data=map_df,
            get_position='[lon, lat]',
            get_weight="total_incidents",
            radiusPixels=60,
        )

        scatter_layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position='[lon, lat]',
            get_radius=12000,
            pickable=True,
            opacity=0.4,
        )

        tooltip = {
            "html": (
                "<b>County:</b> {county}<br/>"
                "<b>Total incidents:</b> {total_incidents}<br/>"
                "<b>Average rent:</b> €{avg_rent_eur}"
            ),
            "style": {"backgroundColor": "white", "color": "black"},
        }

        deck = pdk.Deck(
            layers=[heatmap_layer, scatter_layer],
            initial_view_state=view_state,
            tooltip=tooltip,
            map_style="light",
        )

        st.pydeck_chart(deck)
    else:
        st.info("Could not build the map for the selected counties.")
else:
    st.info("No data in the panel to build the map with the current filters.")

st.markdown("---")

# ================== ANNUAL EVOLUTION ==================

st.subheader("Annual evolution of crime and rents (selected counties)")

if len(panel_filter) > 0:
    incidents_by_year = (
        panel_filter
        .groupby("year", as_index=False)["total_incidents"]
        .sum()
        .sort_values("year")
    )
    st.write("**Total incidents per year:**")
    st.line_chart(
        incidents_by_year.set_index("year")["total_incidents"],
        height=250,
    )

    rent_by_year = (
        panel_filter
        .groupby("year", as_index=False)["avg_rent_eur"]
        .mean()
        .sort_values("year")
    )
    st.write("**Average rent per year:**")
    st.line_chart(
        rent_by_year.set_index("year")["avg_rent_eur"],
        height=250,
    )
else:
    st.info("No data for the time series with the current filters.")

st.markdown("---")

# ================== TOP GARDA STATIONS ==================

st.subheader("Top Garda Stations by number of incidents")

if len(stations_filter) > 0:
    top_stations = (
        stations_filter
        .groupby(["county", "station_name"], as_index=False)["total_incidents"]
        .sum()
        .sort_values("total_incidents", ascending=False)
        .head(15)
    )

    st.dataframe(top_stations, use_container_width=True)

    chart_stations = top_stations.copy()
    chart_stations["label"] = chart_stations["county"] + " - " + chart_stations["station_name"]

    st.bar_chart(
        chart_stations.set_index("label")["total_incidents"],
        height=350,
    )
else:
    st.info("No data for stations with the selected filters.")

st.markdown("---")

# ================== MOST FREQUENT CRIMES BY COUNTY ==================
st.subheader("Most frequent crimes by county (incident types)")

if not crime_filter.empty:
    if focus_county != "(todos)":
        crime_focus = crime_filter[crime_filter["county"] == focus_county].copy()
    else:
        crime_focus = crime_filter.copy()

    if len(crime_focus) > 0:
        top_incident_types = (
            crime_focus
            .groupby(["county", "incident_type"], as_index=False)["incidents"]
            .sum()
            .sort_values("incidents", ascending=False)
            .head(15)
        )

        st.markdown(
            f"Top incident types in the selected period "
            f"{'(only ' + focus_county + ')' if focus_county != '(todos)' else '(all counties)'} "
            f"and with the types filtered in the sidebar."
        )

        st.dataframe(top_incident_types, use_container_width=True)
    else:
        st.info("No data for the selected county and incident type filters.")
else:
    st.info("No raw crime data (CSV) to calculate crime types.")

st.markdown("---")

# ================== SCATTER: RELATION INCIDENTS x RENT ==================
st.subheader("Scatter: incidents vs average rent (by county/year)")

if len(panel_filter) > 0:
    st.write(
        "Each point represents a pair (county, year), with the total incidents "
        "and the average rent in that year. Useful to see if counties with higher rents "
        "also have more or less crime."
    )
    st.scatter_chart(
        panel_filter[["avg_rent_eur", "total_incidents"]],
        x="avg_rent_eur",
        y="total_incidents",
        height=300,
    )
else:
    st.info("No data available for correlation analysis.")

st.markdown("---")

# ================== AUTOMATIC TEXT INSIGHTS ==================
st.subheader(" Interpretation Guide (automatic insights)")

if len(panel_filter) == 0:
    st.info("Adjust the filters to see automatic insights.")
else:
    insights = []

    # --- County with most / least crime ---
    county_ins = (
        panel_filter
        .groupby("county", as_index=False)
        .agg(
            total_incidents=("total_incidents", "sum"),
            mean_rent=("avg_rent_eur", "mean"),
        )
    )

    county_ins = county_ins.sort_values("total_incidents", ascending=False)
    top_crime = county_ins.iloc[0]
    bottom_crime = county_ins.iloc[-1]

    insights.append(
        f"- The county with the **most incidents** in the selected period is **{top_crime['county']}**, "
        f"with approximately **{int(top_crime['total_incidents']):,}** records."
    )

    if bottom_crime["county"] != top_crime["county"]:
        insights.append(
            f"- The county with the **least incidents** is **{bottom_crime['county']}**, "
            f"with approximately **{int(bottom_crime['total_incidents']):,}** incidents."
        )

    # --- County with highest/lowest rent ---
    rent_sorted = county_ins.sort_values("mean_rent", ascending=False)
    top_rent = rent_sorted.iloc[0]
    bottom_rent = rent_sorted.iloc[-1]

    insights.append(
        f"- The county with the **highest average rent** is **{top_rent['county']}**, "
        f"with approximately **{top_rent['mean_rent']:.0f} €/month**."
    )

    if bottom_rent["county"] != top_rent["county"]:
        insights.append(
            f"- The county with the **lowest average rent** is **{bottom_rent['county']}**, "
            f"with approximately **{bottom_rent['mean_rent']:.0f} €/month**."
        )

    # --- Simple correlation between crime and rent ---
    corr_val = panel_filter["total_incidents"].corr(panel_filter["avg_rent_eur"])
    if pd.notna(corr_val):
        if corr_val > 0.3:
            desc = "a **moderate positive** relationship"
        elif corr_val > 0.1:
            desc = "a **weak positive** relationship"
        elif corr_val < -0.3:
            desc = "a **moderate negative** relationship"
        elif corr_val < -0.1:
            desc = "a **weak negative** relationship"
        else:
            desc = "a **very weak or practically null** relationship"
        insights.append(
            f"- The correlation between **average rent** and **number of incidents** in the filtered set is "
            f"approximately **{corr_val:.2f}**, suggesting {desc}."
        )

    # --- Most frequent crime types ---
    if not crime_filter.empty:
        if focus_county != "(all)":
            cf = crime_filter[crime_filter["county"] == focus_county].copy()
            county_label = focus_county
        else:
            cf = crime_filter.copy()
            county_label = "the selected counties"

        if len(cf) > 0:
            top_type = (
                cf.groupby("incident_type", as_index=False)["incidents"]
                .sum()
                .sort_values("incidents", ascending=False)
                .iloc[0]
            )
            insights.append(
                f"- In **{county_label}**, considering the types of crime currently filtered, "
                f"the most frequent type is **{top_type['incident_type']}**, with approximately "
                f"**{int(top_type['incidents']):,}** incidents in the analyzed period."
            )

    st.markdown(
        """
These phrases can be used directly in your report/presentation
(with the current filters):

"""
        + "\n".join(insights)
    )
