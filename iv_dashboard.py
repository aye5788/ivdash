import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Tradier API credentials
API_TOKEN = "7uMZjb2elQAxxOdOGhrgDkqPEqSy"  # Replace with your Tradier API token
BASE_URL = "https://api.tradier.com/v1/markets"

# --- Function to fetch expiration dates ---
def fetch_expirations(symbol):
    url = f"{BASE_URL}/options/expirations"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    params = {"symbol": symbol}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        expirations = response.json().get("expirations", {}).get("date", [])
        return expirations if isinstance(expirations, list) and expirations else []
    else:
        st.error(f"Error fetching expiration dates: {response.text}")
        return []

# --- Function to fetch options data ---
def fetch_options_data(symbol, expiration):
    url = f"{BASE_URL}/options/chains"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    params = {
        "symbol": symbol,
        "expiration": expiration,
        "greeks": "true"  # Request Greeks and implied volatility
    }
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        options = response.json().get("options", {}).get("option", [])
        df = pd.DataFrame(options)

        # Ensure necessary columns are present
        if not df.empty:
            if "implied_volatility" not in df.columns:
                df["implied_volatility"] = None  # Add placeholder if missing
            if "strike" not in df.columns:
                df["strike"] = None
            if "expiration_date" not in df.columns:
                df["expiration_date"] = expiration  # Use expiration as fallback

        return df
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# --- Plot IV Surface ---
def plot_iv_surface(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        options_data = options_data.dropna(subset=["strike", "implied_volatility"])
        fig = go.Figure(data=[
            go.Surface(
                z=options_data["implied_volatility"].values.reshape(-1, 1),
                x=options_data["strike"],
                y=options_data["expiration_date"],
                colorscale="Viridis"
            )
        ])
        fig.update_layout(
            title="Implied Volatility Surface",
            scene=dict(
                xaxis_title="Strike Price",
                yaxis_title="Expiration Date",
                zaxis_title="Implied Volatility",
            )
        )
        st.plotly_chart(fig)
    else:
        st.error("Required columns for IV visualization are missing.")

# --- Plot Volatility Smile ---
def plot_volatility_smile(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        options_data = options_data.dropna(subset=["strike", "implied_volatility"])
        fig = go.Figure(data=[
            go.Scatter(
                x=options_data["strike"],
                y=options_data["implied_volatility"],
                mode="lines+markers",
                marker=dict(size=8),
                line=dict(width=2),
            )
        ])
        fig.update_layout(
            title="Volatility Smile",
            xaxis_title="Strike Price",
            yaxis_title="Implied Volatility",
        )
        st.plotly_chart(fig)
    else:
        st.error("Required columns for Volatility Smile analysis are missing.")

# --- Streamlit App ---
st.title("Implied Volatility Surface Dashboard")
st.write("This app visualizes implied volatility surfaces for selected tickers.")

# --- Ticker Input ---
ticker = st.text_input("Enter a Ticker Symbol:", "AAPL")
if ticker:
    st.write(f"Fetching options data for: {ticker}")
    
    # Fetch expirations
    expirations = fetch_expirations(ticker)
    if expirations:
        selected_expiration = st.selectbox("Select Expiration Date:", expirations)
        
        # Fetch options data for the selected expiration
        if selected_expiration:
            options_data = fetch_options_data(ticker, selected_expiration)
            if not options_data.empty:
                st.write("Options Data Preview:")
                st.dataframe(options_data.head(10))

                # Menu for analysis options
                st.sidebar.title("Select Analysis")
                analysis_choice = st.sidebar.radio(
                    "Choose an analysis type:",
                    ("Implied Volatility Surface", "Volatility Smile")
                )

                # Perform the selected analysis
                if analysis_choice == "Implied Volatility Surface":
                    plot_iv_surface(options_data)

                elif analysis_choice == "Volatility Smile":
                    plot_volatility_smile(options_data)
            else:
                st.write("No data available for the entered ticker and expiration.")
    else:
        st.write("No expiration dates available for the entered ticker.")
