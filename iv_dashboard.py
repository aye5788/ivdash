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
        if not df.empty:
            df["implied_volatility"] = df["greeks"].apply(lambda x: x.get("mid_iv") if x else None)
            df["expiration_date"] = expiration
        return df
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# --- Plot Implied Volatility Surface ---
def plot_iv_surface(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        filtered_data = options_data.dropna(subset=["strike", "implied_volatility"])
        fig = go.Figure(data=[
            go.Mesh3d(
                x=filtered_data["strike"],
                y=pd.to_datetime(filtered_data["expiration_date"]),
                z=filtered_data["implied_volatility"],
                colorbar_title="IV",
                colorscale="Viridis",
                intensity=filtered_data["implied_volatility"],
            )
        ])
        fig.update_layout(
            title="Implied Volatility Surface",
            scene=dict(
                xaxis_title="Strike Price",
                yaxis_title="Expiration Date",
                zaxis_title="Implied Volatility",
            ),
        )
        st.plotly_chart(fig)
    else:
        st.error("Required columns for IV visualization are missing.")

# --- Interpret Implied Volatility Surface ---
def interpret_iv_surface(options_data):
    if "implied_volatility" in options_data and "strike" in options_data:
        avg_iv_by_strike = options_data.groupby("strike")["implied_volatility"].mean()
        iv_skew = "upward" if avg_iv_by_strike.diff().mean() > 0 else "downward"
        st.write(f"""
        **Dynamic Insights for Implied Volatility Surface:**
        - The IV skew is trending **{iv_skew}**, indicating how risk varies with strike prices.
        - Watch for spikes in implied volatility, which may signal unusual pricing or risk.
        """)
    else:
        st.error("Unable to interpret IV surface due to missing data.")

# --- Plot Volatility Smile ---
def plot_vol_smile(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        smile_data = options_data.dropna(subset=["strike", "implied_volatility"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=smile_data["strike"],
            y=smile_data["implied_volatility"],
            mode="lines+markers",
        ))
        fig.update_layout(
            title="Volatility Smile",
            xaxis_title="Strike Price",
            yaxis_title="Implied Volatility",
        )
        st.plotly_chart(fig)
    else:
        st.error("Required data for Volatility Smile visualization is missing.")

# --- Interpret Volatility Smile ---
def interpret_vol_smile(options_data):
    if "implied_volatility" in options_data and "strike" in options_data:
        smile_direction = "upward" if options_data["implied_volatility"].mean() > 0 else "downward"
        st.write(f"""
        **Dynamic Insights for Volatility Smile:**
        - The Volatility Smile is trending **{smile_direction}**, indicating risk variation across strike prices.
        - Extreme volatility at deep in-the-money or out-of-the-money strikes signals market uncertainty.
        """)
    else:
        st.error("Unable to interpret Volatility Smile due to missing data.")

# --- Streamlit App ---
st.title("Implied Volatility Analysis Dashboard")
st.write("This app visualizes and interprets implied volatility data for selected tickers.")

ticker = st.text_input("Enter a Ticker Symbol:", "AAPL")
if ticker:
    st.write(f"Fetching options data for: {ticker}")
    expirations = fetch_expirations(ticker)
    if expirations:
        selected_expiration = st.selectbox("Select Expiration Date:", expirations)
        if selected_expiration:
            options_data = fetch_options_data(ticker, selected_expiration)
            if not options_data.empty:
                st.write("Options Data Preview:")
                st.dataframe(options_data.head(10))
                analysis_choice = st.sidebar.radio(
                    "Choose an analysis type:",
                    ("Implied Volatility Surface", "Volatility Smile")
                )
                if analysis_choice == "Implied Volatility Surface":
                    plot_iv_surface(options_data)
                    interpret_iv_surface(options_data)
                elif analysis_choice == "Volatility Smile":
                    plot_vol_smile(options_data)
                    interpret_vol_smile(options_data)
            else:
                st.error("No options data available for this expiration date.")
