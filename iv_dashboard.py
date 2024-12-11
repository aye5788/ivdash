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

# --- Function to fetch previous day's closing price ---
def fetch_ticker_price(symbol):
    url = f"https://api.tradier.com/v1/markets/quotes"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    params = {"symbols": symbol}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        try:
            data = response.json()
            quote = data.get("quotes", {}).get("quote", {})
            latest_close = quote.get("close") or quote.get("last")
            
            if latest_close is not None:
                return float(latest_close)
            else:
                st.error(f"Closing price not available for {symbol}.")
                return None
        except KeyError as e:
            st.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    else:
        st.error(f"Error fetching price for {symbol}: {response.text}")
        return None

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

            # Extract Greeks (delta, gamma, theta) from the greeks column
            df["delta"] = df["greeks"].apply(lambda x: x.get("delta") if x and "delta" in x else None)
            df["gamma"] = df["greeks"].apply(lambda x: x.get("gamma") if x and "gamma" in x else None)
            df["theta"] = df["greeks"].apply(lambda x: x.get("theta") if x and "theta" in x else None)

            # Keep both the important columns and the additional ones like type, change, etc.
            df = df[['ticker', 'description', 'strike', 'implied_volatility', 'delta', 'gamma', 'theta', 'expiration_date', 'type', 'change', 'volume', 'open', 'high', 'low', 'close', 'bid', 'ask']]

        return df
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# --- Plot Implied Volatility Surface ---
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
    # Fetch previous day's closing price
    ticker_price = fetch_ticker_price(ticker)
    
    if ticker_price:
        st.write(f"Previous Day's Close Price of {ticker}: ${ticker_price:.2f}")
        
        expirations = fetch_expirations(ticker)  # Fetch expiration dates here
        if expirations:
            selected_expiration = st.selectbox("Select Expiration Date:", expirations)
            if selected_expiration:
                options_data = fetch_options_data(ticker, selected_expiration)
                
                # Ensure that we have data in options_data
                if not options_data.empty:
                    # Create two columns to display the data side by side
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Puts and Calls Data Removed (Analysis Only)")
                        # No tables, only the analysis now.

                    with col2:
                        st.subheader("Analysis Results")
                        # Perform the analysis based on user selection
                        if analysis_choice == "Implied Volatility Surface":
                            plot_iv_surface(options_data)
                        elif analysis_choice == "Volatility Smile":
                            plot_volatility_smile(options_data)
                else:
                    st.write("No options data available for the selected expiration.")
        else:
            st.write("No expiration dates available for the entered ticker.")
