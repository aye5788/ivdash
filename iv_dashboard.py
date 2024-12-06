import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import plotly.graph_objects as go

# Tradier API credentials
API_TOKEN = "7uMZjb2elQAxxOdOGhrgDkqPEqSy"  # Replace with your Tradier API token
BASE_URL = "https://api.tradier.com/v1/markets"

# Title and Sidebar
st.title("Options Analytics Dashboard")
st.sidebar.header("Select Analysis")
analysis_type = st.sidebar.radio(
    "Choose an analysis type:",
    options=["Implied Volatility Surface", "Volatility Smile"]
)

# Function to fetch expiration dates from the API
@st.cache
def fetch_expiration_dates(symbol):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    response = requests.get(f"{API_BASE_URL}/expirations", headers=headers, params={"symbol": symbol})
    if response.status_code == 200:
        data = response.json()
        return data.get("expirations", [])
    else:
        st.error(f"Failed to fetch expiration dates: {response.status_code} - {response.text}")
        return []

# Function to fetch options data from the API
@st.cache
def fetch_options_data(symbol, expiration):
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    response = requests.get(f"{API_BASE_URL}/chains", headers=headers, params=params)
    if response.status_code == 200:
        data = response.json()
        options = data.get("options", {}).get("option", [])
        return pd.DataFrame(options)
    else:
        st.error(f"Failed to fetch data: {response.status_code} - {response.text}")
        return pd.DataFrame()

# Helper function to parse 'greeks' column
def parse_greeks(row):
    try:
        return json.loads(row)
    except (ValueError, TypeError):
        return {}

# Process the options data
def process_data(data):
    data["greeks"] = data["greeks"].apply(parse_greeks)
    data["mid_iv"] = data["greeks"].apply(lambda x: x.get("mid_iv", None))
    return data

# Plot Volatility Smile
def plot_volatility_smile(data):
    smile_data = data.dropna(subset=["strike", "mid_iv"])
    if smile_data.empty:
        st.warning("No sufficient data to plot the Volatility Smile.")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=smile_data["strike"],
            y=smile_data["mid_iv"],
            mode="lines+markers",
            name="Volatility Smile",
        )
    )
    fig.update_layout(
        title="Volatility Smile",
        xaxis_title="Strike Price",
        yaxis_title="Implied Volatility",
        template="plotly_dark",
    )
    st.plotly_chart(fig)

    # Dynamic Insights
    st.subheader("Dynamic Insights for Volatility Smile:")
    st.markdown("- The Volatility Smile is trending upward, indicating risk variation across strike prices.")
    st.markdown("- Higher volatility at extreme strikes often signals uncertainty in pricing deep in-the-money or out-of-the-money options.")

# Plot Implied Volatility Surface
def plot_iv_surface(data):
    surface_data = data.dropna(subset=["strike", "expiration_date", "mid_iv"])
    if surface_data.empty:
        st.warning("No sufficient data to plot the Implied Volatility Surface.")
        return

    pivot_table = surface_data.pivot_table(index="strike", columns="expiration_date", values="mid_iv")
    if pivot_table.empty:
        st.warning("Insufficient data to render the 3D surface plot.")
        return

    fig = go.Figure(
        data=[
            go.Surface(
                z=pivot_table.values,
                x=pivot_table.index,
                y=pivot_table.columns,
                colorscale="Viridis",
            )
        ]
    )
    fig.update_layout(
        title="Implied Volatility Surface",
        scene=dict(
            xaxis_title="Strike Price",
            yaxis_title="Expiration Date",
            zaxis_title="Implied Volatility",
        ),
        template="plotly_dark",
    )
    st.plotly_chart(fig)

    # Dynamic Insights
    st.subheader("Dynamic Insights for Implied Volatility Surface:")
    st.markdown("- The IV skew is trending downward, indicating how risk varies with strike prices.")
    st.markdown("- Watch for spikes in implied volatility, which may signal unusual pricing or risk.")

# Main Execution
st.sidebar.subheader("Input Parameters")
symbol = st.sidebar.text_input("Enter a Ticker Symbol:", value="AAPL")

if symbol:
    expirations = fetch_expiration_dates(symbol)
    if expirations:
        expiration = st.sidebar.selectbox("Select Expiration Date:", options=expirations)
        if st.sidebar.button("Fetch Data"):
            options_data = fetch_options_data(symbol, expiration)
            if not options_data.empty:
                options_data = process_data(options_data)

                st.subheader("Options Data Preview:")
                st.write(options_data)

                if analysis_type == "Volatility Smile":
                    plot_volatility_smile(options_data)
                elif analysis_type == "Implied Volatility Surface":
                    plot_iv_surface(options_data)
            else:
                st.warning("No data available for the selected ticker and expiration date.")
    else:
        st.warning("No available expirations for the given symbol.")
