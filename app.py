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
st.title("🌍 California Multi-Pollutant Forecast: SimVP")
st.markdown(
    "Enter a location to view the 72-hour forecast from our AI model across all 6 criteria pollutants."
)

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
# 2. HELPER FUNCTIONS & DATA LOADING
# ==========================================
@st.cache_data
def load_data():
    """Loads the AI dataset and renames columns."""
    # Load AI Data
    ai_df = pd.read_csv("v19_pollution_forecast.csv")
    ai_df['time'] = pd.to_datetime(ai_df['time'])
    
    # Rename AI columns
    ai_rename_map = {
        'PM25_concentration': 'AI_PM25', 'PM10_concentration': 'AI_PM10',
        'O3_concentration': 'AI_O3', 'NO2_concentration': 'AI_NO2',
        'SO2_concentration': 'AI_SO2', 'CO_concentration': 'AI_CO'
    }
    ai_df = ai_df.rename(columns=ai_rename_map)

    return ai_df

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
def get_forecast_data(user_lat, user_lon, _df):
    """
    Finds the nearest coordinates in the dataset to the user's location
    and formats the DataFrame for plotting.
    """
    # 1. Find the nearest grid point using Euclidean distance on lat/lon
    distances = (_df['lat'] - user_lat)**2 + (_df['lon'] - user_lon)**2
    nearest_idx = distances.idxmin()
    nearest_lat = _df.loc[nearest_idx, 'lat']
    nearest_lon = _df.loc[nearest_idx, 'lon']
    
    # 2. Filter data for this specific nearest location
    local_df = _df[(_df['lat'] == nearest_lat) & (_df['lon'] == nearest_lon)].copy()
    local_df = local_df.sort_values('time')
    
    # 3. Rename time column for plotting logic
    local_df = local_df.rename(columns={'time': 'Target_Time_UTC'})
    
    return local_df, nearest_lat, nearest_lon


# ==========================================
# 3. USER INTERFACE (SIDEBAR)
# ==========================================
# Load the master dataset once on startup
master_df = load_data()

st.sidebar.header("📍 Select Location")
user_input = st.sidebar.text_input("City, Zip Code, or Address (e.g., Los Angeles, Fresno):", "Los Angeles")

if st.sidebar.button("Get Forecast") or user_input:
    lat, lon, full_address = get_coordinates(user_input)

    if lat and lon:
        st.sidebar.success(f"Geocoded Input: {lat:.4f}, {lon:.4f}")
        st.sidebar.caption(full_address)

        # Fetch the formatted data for the nearest grid point
        df, grid_lat, grid_lon = get_forecast_data(lat, lon, master_df)
        
        st.sidebar.info(f"Nearest Data Grid Point:\nLat: {grid_lat:.4f}, Lon: {grid_lon:.4f}")

        st.subheader(f"📈 72-Hour Outlook for {user_input.title()}")

        # ==========================================
        # 4. DATA VISUALIZATION (TABS & PLOTLY)
        # ==========================================
        tabs = st.tabs(list(POLLUTANTS.keys()))

        for i, (tab_name, meta) in enumerate(POLLUTANTS.items()):
            with tabs[i]:
                pol_key = meta["col"]
                unit = meta["unit"]
                short_name = tab_name.split(" ")[0] 

                fig = go.Figure()

                # Plot AI (SimVP-V19)
                if f"AI_{pol_key}" in df.columns:
                    fig.add_trace(go.Scatter(
                        x=df["Target_Time_UTC"], y=df[f"AI_{pol_key}"],
                        mode='lines+markers',
                        name='SimVP-V19 (Our AI)',
                        line=dict(color='#d62728', width=3), # Red solid line
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
        # 5. DATA TABLES
        # ==========================================
        st.subheader("Raw Forecast Data")
        
        # Helper function to format tables
        def format_table(data_df):
            display_df = data_df.copy()
            display_df["Target_Time_UTC"] = display_df["Target_Time_UTC"].dt.strftime('%Y-%m-%d %H:%00 UTC')
            display_df = display_df.rename(columns={"Target_Time_UTC": "Time"})
            format_dict = {col: "{:.3f}" if "CO" in col else "{:.2f}" for col in display_df.columns if col != "Time"}
            return display_df.style.format(format_dict)

        # SimVP-V19 Table
        with st.expander("📊 View Raw Data (SimVP)"):
            ai_cols = ["Target_Time_UTC"] + [col for col in df.columns if col.startswith("AI_")]
            st.dataframe(format_table(df[ai_cols]), use_container_width=True)

    else:
        st.sidebar.error("Location not found in California. Please try a different name or zip code.")
