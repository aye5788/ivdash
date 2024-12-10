import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Tradier API credentials
API_TOKEN = "7uMZjb2elQAxxOdOGhrgDkqPEqSy"  # Replace with your API token
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

        # Extract implied volatility from the greeks
        if not df.empty:
            df["implied_volatility"] = df["greeks"].apply(
                lambda x: x.get("mid_iv") if x and "mid_iv" in x else (
                    x.get("ask_iv") if x and "ask_iv" in x else (
                        x.get("bid_iv") if x and "bid_iv" in x else None
                    )
                )
            )
            df["strike"] = df["strike"]
            df["expiration_date"] = expiration

            # Add a new column with only the root symbol (ticker)
            df["ticker"] = symbol

            # Remove the 'symbol' column (since it's redundant)
            df = df.drop(columns=["symbol", "greeks", "exch", "type", "change", "volume", "open", "high", "low", "close", "bid", "ask", "underlying"])

            # Only keep the relevant columns for preview
            df = df[['ticker', 'description', 'strike', 'implied_volatility', 'expiration_date']]

        return df
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# --- Plot IV Surface ---
def plot_iv_surface(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        options_data = options_data.dropna(subset=["strike", "implied_volatility"])
        fig = go.Figure(data=[
            go.Scatter3d(
                x=options_data["strike"],
                y=pd.to_datetime(options_data["expiration_date"]),
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

# --- Plot Volatility Smile ---
def plot_volatility_smile(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        smile_data = options_data.groupby("strike")["implied_volatility"].mean().dropna()
        fig = go.Figure(data=go.Scatter(
            x=smile_data.index,
            y=smile_data.values,
            mode="lines+markers",
            marker=dict(size=8),
        ))
        fig.update_layout(
            title="Volatility Smile",
            xaxis_title="Strike Price",
            yaxis_title="Implied Volatility",
        )
        st.plotly_chart(fig)
        st.write("""
        **Dynamic Insights for Volatility Smile:**
        - The Volatility Smile reflects risk variations across strikes.
        - Higher IV at extreme strikes indicates uncertainty in deep in/out-of-the-money options.
        - Use the smile shape to identify pricing inefficiencies or arbitrage opportunities.
        """)
    else:
        st.error("Required columns for volatility smile visualization are missing.")

# --- Interpret IV Surface ---
def interpret_iv_surface(options_data):
    required_columns = {"strike", "implied_volatility", "expiration_date"}
    if not required_columns.issubset(options_data.columns):
        missing_columns = required_columns - set(options_data.columns)
        st.error(f"The following required columns are missing from the data: {', '.join(missing_columns)}")
        return

    if options_data.empty:
        st.write("No options data to interpret.")
        return

    avg_iv_by_strike = options_data.groupby("strike")["implied_volatility"].mean()
    avg_iv_by_ttm = options_data.groupby("expiration_date")["implied_volatility"].mean()

    if avg_iv_by_ttm.empty or avg_iv_by_ttm.isna().all():
        ttm_trend = "No data available to determine trends."
    else:
        ttm_trend = "higher for near-term expirations" if avg_iv_by_ttm.idxmax() < avg_iv_by_ttm.idxmin() else "higher for long-term expirations"

    skew_direction = "upward" if avg_iv_by_strike.diff().mean() > 0 else "downward"

    st.write(f"""
    **Dynamic Insights for Implied Volatility Surface:**
    - The IV skew is trending **{skew_direction}**, indicating how risk changes with strike prices.
    - Implied volatility is **{ttm_trend}**, suggesting how market uncertainty evolves with time.
    - Look for sharp IV spikes to identify unusual pricing opportunities.
    """)

# --- Streamlit App ---
st.title("Options Analytics Dashboard")
st.sidebar.title("Select Analysis")
analysis_choice = st.sidebar.radio(
    "Choose an analysis type:",
    ("Implied Volatility Surface", "Volatility Smile")
)

# --- Input for Ticker and Expiration ---
ticker = st.text_input("Enter a Ticker Symbol:", "AAPL")
if ticker:
    expirations = fetch_expirations(ticker)
    if expirations:
        selected_expiration = st.selectbox("Select Expiration Date:", expirations)
        if selected_expiration:
            options_data = fetch_options_data(ticker, selected_expiration)
            if not options_data.empty:
                st.write("Options Data Preview:")
                st.dataframe(options_data.head(10))  # Display preview with ticker column only
                if analysis_choice == "Implied Volatility Surface":
                    plot_iv_surface(options_data)
                    interpret_iv_surface(options_data)
                elif analysis_choice == "Volatility Smile":
                    plot_volatility_smile(options_data)
            else:
                st.write("No options data available for the selected expiration.")
    else:
        st.write("No expiration dates available for the entered ticker.")
