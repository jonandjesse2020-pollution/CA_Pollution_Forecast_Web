import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from geopy.geocoders import Nominatim

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(
    page_title="California Air Quality Forecast",
    page_icon="🌫️",
    layout="wide"
)

st.title("🌍 California Multi-Pollutant Air Quality Forecast with SimVP model")

st.markdown(
    "Enter a location to view the 72-hour forecast for all 6 criteria pollutants."
)

# Define pollutants and units
POLLUTANTS = {
    "PM₂.₅ (Fine Particulate)": {"col": "PM25", "unit": "μg/m³"},
    "PM₁₀ (Coarse Particulate)": {"col": "PM10", "unit": "μg/m³"},
    "O₃ (Ozone)": {"col": "O3", "unit": "μg/m³"},
    "NO₂ (Nitrogen Dioxide)": {"col": "NO2", "unit": "μg/m³"},
    "SO₂ (Sulfur Dioxide)": {"col": "SO2", "unit": "μg/m³"},
    "CO (Carbon Monoxide)": {"col": "CO", "unit": "mg/m³"}
}

# ==========================================
# 2. HELPER FUNCTIONS & DATA LOADING
# ==========================================
@st.cache_data
def load_forecast_data():
    """Load AI forecast dataset."""

    df = pd.read_csv("v19_pollution_forecast.csv")
    df["time"] = pd.to_datetime(df["time"])

    rename_map = {
        "PM25_concentration": "PM25",
        "PM10_concentration": "PM10",
        "O3_concentration": "O3",
        "NO2_concentration": "NO2",
        "SO2_concentration": "SO2",
        "CO_concentration": "CO"
    }

    df = df.rename(columns=rename_map)

    return df


@st.cache_data
def get_coordinates(location_name):
    """Convert location name to latitude and longitude."""

    geolocator = Nominatim(user_agent="california_aqi_forecast")

    try:
        loc = geolocator.geocode(
            f"{location_name}, California, USA"
        )

        if loc:
            return loc.latitude, loc.longitude, loc.address

        return None, None, None

    except Exception:
        return None, None, None


@st.cache_data
def get_forecast_data(user_lat, user_lon, df):
    """Find nearest forecast grid point."""

    distances = (
        (df["lat"] - user_lat) ** 2
        + (df["lon"] - user_lon) ** 2
    )

    nearest_idx = distances.idxmin()

    nearest_lat = df.loc[nearest_idx, "lat"]
    nearest_lon = df.loc[nearest_idx, "lon"]

    local_df = df[
        (df["lat"] == nearest_lat)
        & (df["lon"] == nearest_lon)
    ].copy()

    local_df = local_df.sort_values("time")

    local_df = local_df.rename(
        columns={"time": "Target_Time_UTC"}
    )

    return local_df, nearest_lat, nearest_lon


# ==========================================
# 3. USER INTERFACE (SIDEBAR)
# ==========================================

master_df = load_forecast_data()

st.sidebar.header("📍 Select Location")

user_input = st.sidebar.text_input(
    "City, Zip Code, or Address (e.g., Malibu, Fresno):",
    "Malibu"
)

if st.sidebar.button("Get Forecast") or user_input:

    lat, lon, full_address = get_coordinates(user_input)

    if lat and lon:

        st.sidebar.success(
            f"Geocoded Input: {lat:.4f}, {lon:.4f}"
        )

        st.sidebar.caption(full_address)

        df, grid_lat, grid_lon = get_forecast_data(
            lat,
            lon,
            master_df
        )

        st.sidebar.info(
            f"Nearest Data Grid Point:\n"
            f"Lat: {grid_lat:.4f}, "
            f"Lon: {grid_lon:.4f}"
        )

        st.subheader(
            f"📈 72-Hour Outlook for {user_input.title()}"
        )

        # ==========================================
        # 4. VISUALIZATION
        # ==========================================

        tabs = st.tabs(list(POLLUTANTS.keys()))

        for i, (tab_name, meta) in enumerate(POLLUTANTS.items()):

            with tabs[i]:

                pol_key = meta["col"]
                unit = meta["unit"]

                short_name = tab_name.split(" ")[0]

                fig = go.Figure()

                if pol_key in df.columns:

                    fig.add_trace(
                        go.Scatter(
                            x=df["Target_Time_UTC"],
                            y=df[pol_key],
                            mode="lines+markers",
                            name="AI Forecast",
                            line=dict(width=3),
                            marker=dict(size=8)
                        )
                    )

                fig.update_layout(
                    title=f"Forecasted {short_name} Concentrations",
                    xaxis_title="Forecast Time (UTC)",
                    yaxis_title=f"Concentration ({unit})",
                    hovermode="x unified",
                    margin=dict(
                        l=0,
                        r=0,
                        t=40,
                        b=0
                    ),
                    template="plotly_white"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

        # ==========================================
        # 5. RAW DATA TABLE
        # ==========================================

        st.subheader("Raw Forecast Data")

        def format_table(data_df):

            display_df = data_df.copy()

            display_df["Target_Time_UTC"] = (
                display_df["Target_Time_UTC"]
                .dt.strftime("%Y-%m-%d %H:%00 UTC")
            )

            display_df = display_df.rename(
                columns={
                    "Target_Time_UTC": "Time"
                }
            )

            format_dict = {
                col: (
                    "{:.3f}"
                    if col == "CO"
                    else "{:.2f}"
                )
                for col in display_df.columns
                if col != "Time"
            }

            return display_df.style.format(
                format_dict
            )

        with st.expander("📊 View Raw Forecast Data"):

            forecast_cols = [
                "Target_Time_UTC",
                "PM25",
                "PM10",
                "O3",
                "NO2",
                "SO2",
                "CO"
            ]

            available_cols = [
                col
                for col in forecast_cols
                if col in df.columns
            ]

            st.dataframe(
                format_table(
                    df[available_cols]
                ),
                use_container_width=True
            )

    else:

        st.sidebar.error(
            "Location not found in California. "
            "Please try a different name or zip code."
        )

    else:
        st.sidebar.error("Location not found in California. Please try a different name or zip code.")
