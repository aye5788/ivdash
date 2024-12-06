import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
import plotly.express as px

# Tradier API credentials
API_TOKEN = "your_tradier_api_token"  # Replace with your Tradier API token
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
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    response = requests.get(url, headers=headers, params=params)

    if response.status_code == 200:
        options = response.json().get("options", {}).get("option", [])
        df = pd.DataFrame(options)

        # Flatten greeks data
        if "greeks" in df.columns:
            greeks = pd.json_normalize(df["greeks"])
            df = pd.concat([df.drop(columns=["greeks"]), greeks], axis=1)

        # Ensure necessary columns are present
        if not df.empty:
            df["implied_volatility"] = df["mid_iv"]
            df["expiration_date"] = expiration  # Add expiration date
        return df
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# --- Plot IV Surface ---
def plot_iv_surface(options_data):
    if {"strike", "implied_volatility", "expiration_date"}.issubset(options_data.columns):
        fig = go.Figure(data=[
            go.Surface(
                x=options_data["strike"],
                y=options_data["expiration_date"],
                z=options_data["implied_volatility"],
                colorscale="Viridis"
            )
        ])
        fig.update_layout(
            title="Implied Volatility Surface",
            scene=dict(
                xaxis_title="Strike Price",
                yaxis_title="Expiration Date",
                zaxis_title="Implied Volatility"
            )
        )
        st.plotly_chart(fig)
    else:
        st.error("Required columns for IV visualization are missing.")

# --- Volatility Smile ---
def plot_volatility_smile(options_data):
    if {"strike", "implied_volatility"}.issubset(options_data.columns):
        fig = px.line(
            options_data.sort_values(by="strike"),
            x="strike",
            y="implied_volatility",
            title="Volatility Smile",
            labels={"strike": "Strike Price", "implied_volatility": "Implied Volatility"}
        )
        st.plotly_chart(fig)

        st.write(f"""
        **Dynamic Insights for Volatility Smile:**
        - The Volatility Smile is trending {'downward' if options_data['implied_volatility'].mean() < 0 else 'upward'}, indicating risk variation across strike prices.
        - Higher volatility at extreme strikes often signals uncertainty in pricing deep in-the-money or out-of-the-money options.
        """)
    else:
        st.error("Required columns for Volatility Smile are missing.")

# --- Streamlit App ---
st.title("Implied Volatility Analysis Dashboard")
st.write("Visualize implied volatility surfaces and smiles for selected tickers.")

# --- Ticker Input ---
ticker = st.text_input("Enter a Ticker Symbol:", "AAPL")
if ticker:
    st.write(f"Fetching options data for: {ticker}")

    # Fetch expiration dates
    expirations = fetch_expirations(ticker)
    if expirations:
        selected_expiration = st.selectbox("Select Expiration Date:", expirations)

        if selected_expiration:
            options_data = fetch_options_data(ticker, selected_expiration)

            if not options_data.empty:
                st.write("Options Data Preview:")
                st.dataframe(options_data[["symbol", "strike", "implied_volatility", "expiration_date"]])

                # Menu for analysis options
                st.sidebar.title("Select Analysis")
                analysis_choice = st.sidebar.radio(
                    "Choose an analysis type:",
                    ("Implied Volatility Surface", "Volatility Smile")
                )

                if analysis_choice == "Implied Volatility Surface":
                    plot_iv_surface(options_data)
                elif analysis_choice == "Volatility Smile":
                    plot_volatility_smile(options_data)
            else:
                st.error("No data available for the selected ticker and expiration date.")
    else:
        st.error("No expiration dates available for the entered ticker.")
