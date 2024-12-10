import streamlit as st
import pandas as pd
import requests

# Tradier API credentials
API_TOKEN = "7uMZjb2elQAxxOdOGhrgDkqPEqSy"  # Replace with your API token
BASE_URL = "https://api.tradier.com/v1/markets"

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

                # Separate Puts and Calls
                puts_data = options_data[options_data['type'] == 'put']
                calls_data = options_data[options_data['type'] == 'call']

                # Create two columns to display the data side by side
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Puts")
                    st.dataframe(puts_data.reset_index(drop=True).head(10))  # Display Puts on the left

                with col2:
                    st.subheader("Calls")
                    st.dataframe(calls_data.reset_index(drop=True).head(10))  # Display Calls on the right

                if analysis_choice == "Implied Volatility Surface":
                    plot_iv_surface(options_data)
                    interpret_iv_surface(options_data)
                elif analysis_choice == "Volatility Smile":
                    plot_volatility_smile(options_data)
            else:
                st.write("No options data available for the selected expiration.")
    else:
        st.write("No expiration dates available for the entered ticker.")
