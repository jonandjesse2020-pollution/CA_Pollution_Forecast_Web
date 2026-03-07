import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from geopy.geocoders import Nominatim
from datetime import datetime, timedelta

# ==========================================
# 1. PAGE SETUP
# ==========================================
st.set_page_config(page_title="California Air Quality Forecast", page_icon="🌫️", layout="wide")
st.title("🌍 California Multi-Pollutant Forecast: SimVP-V19 vs. CAMS")
st.markdown(
    "Enter a location to view the 72-hour forecast comparing our AI model with the operational CAMS baseline across all 6 criteria pollutants.")

# Define our 6 pollutants, their internal CSV names, and their display units
POLLUTANTS = {
    "PM₂.₅ (Fine Particulate)": {"col": "PM25", "unit": "μg/m³"},
    "PM₁₀ (Coarse Particulate)": {"col": "PM10", "unit": "μg/m³"},
    "O₃ (Ozone)": {"col": "O3", "unit": "μg/m³"},
    "NO₂ (Nitrogen Dioxide)": {"col": "NO2", "unit": "μg/m³"},
    "SO₂ (Sulfur Dioxide)": {"col": "SO2", "unit": "μg/m³"},
    "CO (Carbon Monoxide)": {"col": "CO", "unit": "mg/m³"}  # CO is measured in mg
}


# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
@st.cache_data
def get_coordinates(location_name):
    """Converts a location name to Latitude and Longitude."""
    geolocator = Nominatim(user_agent="california_aqi_forecast")
    try:
        loc = geolocator.geocode(f"{location_name}, California, USA")
        if loc:
            return loc.latitude, loc.longitude, loc.address
        return None, None, None
    except:
        return None, None, None


@st.cache_data
def get_forecast_data(lat, lon):
    """
    TODO: Replace this mock function with your actual CSV data loading logic!
    Generates 72-hour forecast data for all 6 pollutants.
    """
    base_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    times = [base_time + timedelta(hours=i) for i in range(6, 78, 6)]

    df = pd.DataFrame({"Target_Time_UTC": times})

    # Generate realistic baseline ranges and spikes for each pollutant
    # Format: (Low_base, High_base, CAMS_spike_severity, AI_spike_severity)
    baselines = {
        "PM25": (5, 12, 10, 25),
        "PM10": (15, 25, 15, 35),
        "O3": (40, 60, -10, -20),  # Ozone titrates (drops) when NO2 spikes!
        "NO2": (10, 20, 8, 18),
        "SO2": (1, 4, 1, 3),
        "CO": (0.2, 0.4, 0.3, 0.8)
    }

    for pol_key, (low, high, cams_spike, ai_spike) in baselines.items():
        base_vals = np.random.uniform(low, high, 12)

        cams_vals = base_vals.copy()
        ai_vals = base_vals.copy()

        # Simulate a crisis event (Traffic/Fire) between hours 24 and 42
        cams_vals[3:6] += np.array([cams_spike * 0.5, cams_spike, cams_spike * 0.5])
        ai_vals[3:6] += np.array([ai_spike * 0.8, ai_spike, ai_spike * 0.8])

        df[f"CAMS_{pol_key}"] = np.maximum(0, cams_vals)  # Prevent negative values
        df[f"AI_{pol_key}"] = np.maximum(0, ai_vals)

    return df


# ==========================================
# 3. USER INTERFACE (SIDEBAR)
# ==========================================
st.sidebar.header("📍 Select Location")
user_input = st.sidebar.text_input("City, Zip Code, or Address (e.g., Malibu, Fresno):", "Malibu")

if st.sidebar.button("Get Forecast") or user_input:
    lat, lon, full_address = get_coordinates(user_input)

    if lat and lon:
        st.sidebar.success(f"Located: {lat:.4f}, {lon:.4f}")
        st.sidebar.caption(full_address)

        # Fetch the data
        df = get_forecast_data(lat, lon)

        st.subheader(f"📈 72-Hour Outlook for {user_input.title()}")

        # ==========================================
        # 4. DATA VISUALIZATION (TABS & PLOTLY)
        # ==========================================
        # Create 6 interactive tabs, one for each pollutant
        tabs = st.tabs(list(POLLUTANTS.keys()))

        for i, (tab_name, meta) in enumerate(POLLUTANTS.items()):
            with tabs[i]:
                pol_key = meta["col"]
                unit = meta["unit"]
                short_name = tab_name.split(" ")[0]  # Gets just the "PM₂.₅" part

                fig = go.Figure()

                # Plot CAMS (Operational Baseline)
                fig.add_trace(go.Scatter(
                    x=df["Target_Time_UTC"], y=df[f"CAMS_{pol_key}"],
                    mode='lines+markers',
                    name='CAMS Baseline',
                    line=dict(color='#1f77b4', width=2, dash='dash'),
                    marker=dict(size=6)
                ))

                # Plot AI (SimVP-V19)
                fig.add_trace(go.Scatter(
                    x=df["Target_Time_UTC"], y=df[f"AI_{pol_key}"],
                    mode='lines+markers',
                    name='SimVP-V19 (Our AI)',
                    line=dict(color='#d62728', width=3),
                    marker=dict(size=8)
                ))

                fig.update_layout(
                    title=f"Forecasted {short_name} Concentrations",
                    xaxis_title="Forecast Time (UTC)",
                    yaxis_title=f"Concentration ({unit})",
                    hovermode="x unified",
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01, bgcolor="rgba(255, 255, 255, 0.8)"),
                    margin=dict(l=0, r=0, t=40, b=0),
                    template="plotly_white"
                )

                st.plotly_chart(fig, use_container_width=True)

        # ==========================================
        # 5. DATA TABLE
        # ==========================================
        with st.expander("📊 View Raw Data (All Pollutants)"):
            display_df = df.copy()
            display_df["Target_Time_UTC"] = display_df["Target_Time_UTC"].dt.strftime('%Y-%m-%d %H:%00 UTC')
            display_df = display_df.rename(columns={"Target_Time_UTC": "Time"})

            # Format CO to 3 decimals, everything else to 2 decimals
            format_dict = {}
            for col in display_df.columns:
                if col != "Time":
                    format_dict[col] = "{:.3f}" if "CO" in col else "{:.2f}"

            st.dataframe(display_df.style.format(format_dict), use_container_width=True)

    else:
        st.sidebar.error("Location not found in California. Please try a different name or zip code.")