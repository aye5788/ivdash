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

# --- Plot Implied Volatility Surface ---
def plot_iv_surface(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        filtered_data = options_data.dropna(subset=["strike", "implied_volatility", "expiration_date"])
        if filtered_data.empty:
            st.error("Not enough data points to create a meaningful 3D plot.")
            return
        
        # Convert expiration_date to datetime for proper plotting
        filtered_data["expiration_date"] = pd.to_datetime(filtered_data["expiration_date"])

        st.write("Processed Data for 3D Plot:")
        st.dataframe(filtered_data.head())  # Debugging output

        fig = go.Figure(data=[
            go.Scatter3d(
                x=filtered_data["strike"],
                y=filtered_data["expiration_date"],
                z=filtered_data["implied_volatility"],
                mode="markers",
                marker=dict(size=5, color=filtered_data["implied_volatility"], colorscale="Viridis"),
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

# --- Interpret IV Surface ---
def interpret_iv_surface(options_data):
    if options_data.empty:
        st.write("No options data to interpret.")
        return

    avg_iv_by_strike = options_data.groupby("strike")["implied_volatility"].mean()
    if avg_iv_by_strike.empty or avg_iv_by_strike.isna().all():
        skew_direction = "No data available to determine trends."
    else:
        skew_direction = "upward" if avg_iv_by_strike.diff().mean() > 0 else "downward"

    st.write(f"""
    **Dynamic Insights for Implied Volatility Surface:**
    - The IV skew is trending **{skew_direction}**, indicating how risk varies with strike prices.
    - Watch for spikes in implied volatility, which may signal unusual pricing or risk.
    """)

# --- Plot Volatility Smile ---
def plot_volatility_smile(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        filtered_data = options_data.dropna(subset=["strike", "implied_volatility"])
        if filtered_data.empty:
            st.error("No data available for Volatility Smile analysis.")
            return

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=filtered_data["strike"],
            y=filtered_data["implied_volatility"],
            mode="lines+markers",
            name="Volatility Smile"
        ))
        fig.update_layout(
            title="Volatility Smile",
            xaxis_title="Strike Price",
            yaxis_title="Implied Volatility",
        )
        st.plotly_chart(fig)

        st.write(f"""
        **Dynamic Insights for Volatility Smile:**
        - The Volatility Smile is trending upward, indicating risk variation across strike prices.
        - Higher volatility at extreme strikes often signals uncertainty in pricing deep in-the-money or out-of-the-money options.
        """)
    else:
        st.error("Required columns for Volatility Smile visualization are missing.")

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
                    interpret_iv_surface(options_data)

                elif analysis_choice == "Volatility Smile":
                    plot_volatility_smile(options_data)
            else:
                st.write("No data available for the entered ticker and expiration.")
    else:
        st.write("No expiration dates available for the entered ticker.")
