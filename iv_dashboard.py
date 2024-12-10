import streamlit as st
import pandas as pd
import requests

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

# --- Function to fetch current ticker price ---
def fetch_ticker_price(symbol):
    # Replace this with your own API for fetching live ticker price (example with Alpha Vantage)
    url = f"https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": "1min",  # 1-minute intervals for live price
        "apikey": "YOUR_ALPHA_VANTAGE_API_KEY"  # Replace with your Alpha Vantage API key
    }
    response = requests.get(url, params=params)
    data = response.json()

    try:
        # Get the most recent closing price
        latest_close = data["Time Series (1min)"].popitem()[1]["4. close"]
        return float(latest_close)
    except KeyError:
        st.error(f"Could not fetch the live price for {symbol}.")
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
    # Fetch live ticker price
    ticker_price = fetch_ticker_price(ticker)
    
    if ticker_price:
        st.write(f"Current Price of {ticker}: ${ticker_price:.2f}")
        
        expirations = fetch_expirations(ticker)  # Fetch expiration dates here
        if expirations:
            selected_expiration = st.selectbox("Select Expiration Date:", expirations)
            if selected_expiration:
                options_data = fetch_options_data(ticker, selected_expiration)
                
                # Ensure that we have data in options_data
                if not options_data.empty:
                    st.write("Options Data Preview:")
                    
                    # Separate Puts and Calls
                    puts_data = options_data[options_data['type'] == 'put']
                    calls_data = options_data[options_data['type'] == 'call']

                    # Find the closest strike to the current price (ATM strikes)
                    puts_data['price_diff'] = abs(puts_data['strike'] - ticker_price)
                    calls_data['price_diff'] = abs(calls_data['strike'] - ticker_price)

                    atm_put = puts_data.loc[puts_data['price_diff'].idxmin()]
                    atm_call = calls_data.loc[calls_data['price_diff'].idxmin()]

                    # Highlight ATM in the table
                    st.write(f"ATM Put: Strike ${atm_put['strike']} | Implied Volatility: {atm_put['implied_volatility']}")
                    st.write(f"ATM Call: Strike ${atm_call['strike']} | Implied Volatility: {atm_call['implied_volatility']}")

                    # Create two columns to display the data side by side
                    col1, col2 = st.columns(2)

                    with col1:
                        st.subheader("Puts")
                        st.dataframe(puts_data.reset_index(drop=True).style.format({
                            'implied_volatility': '{:.2f}',
                            'strike': '{:.2f}',
                            'delta': '{:.2f}',
                            'gamma': '{:.2f}',
                            'theta': '{:.2f}'
                        }))  # Display Puts on the left

                    with col2:
                        st.subheader("Calls")
                        st.dataframe(calls_data.reset_index(drop=True).style.format({
                            'implied_volatility': '{:.2f}',
                            'strike': '{:.2f}',
                            'delta': '{:.2f}',
                            'gamma': '{:.2f}',
                            'theta': '{:.2f}'
                        }))  # Display Calls on the right

                    # Perform the analysis based on user selection
                    if analysis_choice == "Implied Volatility Surface":
                        plot_iv_surface(options_data)
                        interpret_iv_surface(options_data)
                    elif analysis_choice == "Volatility Smile":
                        plot_volatility_smile(options_data)
                else:
                    st.write("No options data available for the selected expiration.")
        else:
            st.write("No expiration dates available for the entered ticker.")

