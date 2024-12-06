import streamlit as st
import pandas as pd
import requests
import json
import plotly.express as px
import plotly.graph_objects as go

# Set your API key here
API_KEY = "7uMZjb2elQAxxOdOGhrgDkqPEqSy"

# Function to fetch expiration dates
def fetch_expiration_dates(symbol):
    try:
        url = f"https://api.tradier.com/v1/markets/options/expirations"
        headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
        params = {"symbol": symbol}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("expirations", [])
    except Exception as e:
        st.error(f"Failed to fetch expiration dates: {e}")
        return []

# Function to fetch options data for a specific expiration
def fetch_options_data(symbol, expiration):
    try:
        url = f"https://api.tradier.com/v1/markets/options/chains"
        headers = {"Authorization": f"Bearer {API_KEY}", "Accept": "application/json"}
        params = {"symbol": symbol, "expiration": expiration}
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        return pd.DataFrame(data.get("options", {}).get("option", []))
    except Exception as e:
        st.error(f"Failed to fetch options data: {e}")
        return pd.DataFrame()

# Function to generate the implied volatility surface plot
def plot_iv_surface(options_data):
    try:
        options_data = options_data[options_data["implied_volatility"] > 0]
        if options_data.empty:
            st.warning("No valid data available to plot the implied volatility surface.")
            return

        fig = go.Figure(
            data=[
                go.Surface(
                    z=options_data["implied_volatility"],
                    x=options_data["strike"],
                    y=options_data["expiration_date"],
                    colorscale="Viridis",
                )
            ]
        )
        fig.update_layout(
            scene=dict(
                xaxis_title="Strike Price",
                yaxis_title="Expiration Date",
                zaxis_title="Implied Volatility",
            ),
            title="Implied Volatility Surface",
        )
        st.plotly_chart(fig)
    except Exception as e:
        st.error(f"Failed to generate IV surface plot: {e}")

# Function to generate the volatility smile plot
def plot_volatility_smile(options_data):
    try:
        smile_data = options_data[["strike", "implied_volatility"]].dropna()
        smile_data = smile_data[smile_data["implied_volatility"] > 0]
        if smile_data.empty:
            st.warning("No valid data available to plot the volatility smile.")
            return

        fig = px.line(smile_data, x="strike", y="implied_volatility", title="Volatility Smile")
        fig.update_layout(xaxis_title="Strike Price", yaxis_title="Implied Volatility")
        st.plotly_chart(fig)
    except Exception as e:
        st.error(f"Failed to generate volatility smile plot: {e}")

# Sidebar input for analysis type
st.sidebar.title("Select Analysis")
analysis_type = st.sidebar.radio(
    "Choose an analysis type:", ["Implied Volatility Surface", "Volatility Smile"]
)

# Main dashboard
st.title("Options Analytics Dashboard")
st.subheader("Input Parameters")

# Input for ticker symbol
ticker = st.text_input("Enter a Ticker Symbol:", value="AAPL").upper()

# Fetch and display expiration dates
if ticker:
    expirations = fetch_expiration_dates(ticker)
    if expirations:
        expiration = st.selectbox("Select an Expiration Date:", options=expirations)
    else:
        expiration = None
        st.warning("No available expirations for the given symbol.")

# Fetch and display options data
if ticker and expiration:
    if st.button("Fetch Data"):
        options_data = fetch_options_data(ticker, expiration)
        if not options_data.empty:
            st.subheader("Options Data Preview:")
            st.dataframe(options_data)

            # Analysis type: Implied Volatility Surface
            if analysis_type == "Implied Volatility Surface":
                plot_iv_surface(options_data)

            # Analysis type: Volatility Smile
            elif analysis_type == "Volatility Smile":
                plot_volatility_smile(options_data)
        else:
            st.warning("No data available for the selected expiration.")
