import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

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
        if not df.empty and "greeks" in df.columns:
            df["implied_volatility"] = df["greeks"].apply(lambda x: x.get("mid_iv", None) if isinstance(x, dict) else None)
        else:
            df["implied_volatility"] = None

        return df
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# --- Plot Volatility Surface ---
def plot_iv_surface(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns and "expiration_date" in options_data.columns:
        options_data = options_data.dropna(subset=["strike", "implied_volatility"])
        fig = go.Figure(data=[
            go.Scatter3d(
                x=options_data["strike"],
                y=options_data["expiration_date"],
                z=options_data["implied_volatility"],
                mode="markers",
                marker=dict(size=5, color=options_data["implied_volatility"], colorscale="Viridis"),
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

# --- Interpret Volatility Smile ---
def interpret_volatility_smile(options_data):
    if options_data.empty or "strike" not in options_data.columns or "implied_volatility" not in options_data.columns:
        st.error("Insufficient data for Volatility Smile interpretation.")
        return

    avg_iv_by_strike = options_data.groupby("strike")["implied_volatility"].mean().dropna()
    skew_direction = "upward" if avg_iv_by_strike.diff().mean() > 0 else "downward"

    st.write(f"""
    **Dynamic Insights for Volatility Smile:**
    - The Volatility Smile is trending **{skew_direction}**, indicating risk variation across strike prices.
    - Higher volatility at extreme strikes often signals uncertainty in pricing deep in-the-money or out-of-the-money options.
    """)

# --- Plot Volatility Smile ---
def plot_volatility_smile(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        fig = px.scatter(
            options_data,
            x="strike",
            y="implied_volatility",
            title="Volatility Smile",
            labels={"strike": "Strike Price", "implied_volatility": "Implied Volatility"},
        )
        fig.update_traces(mode="lines+markers")
        st.plotly_chart(fig)
    else:
        st.error("Required columns for Volatility Smile visualization are missing.")

# --- Streamlit App ---
st.title("Implied Volatility Surface and Smile Dashboard")
st.write("This app visualizes implied volatility surfaces and smiles for selected tickers.")

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
                    interpret_iv_surface(options_data)

                elif analysis_choice == "Volatility Smile":
                    plot_volatility_smile(options_data)
                    interpret_volatility_smile(options_data)
            else:
                st.write("No data available for the entered ticker and expiration.")
    else:
        st.write("No expiration dates available for the entered ticker.")
