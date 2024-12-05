import streamlit as st
import pandas as pd
import requests

# Tradier API credentials
API_TOKEN = "7uMZjb2elQAxxOdOGhrgDkqPEqSy"  # Replace with your Tradier API token
BASE_URL = "https://api.tradier.com/v1/markets"

# Function to fetch options data
def fetch_options_data(symbol):
    url = f"{BASE_URL}/options/chains"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    params = {"symbol": symbol}
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        options = response.json().get("options", {}).get("option", [])
        return pd.DataFrame(options)
    else:
        st.error(f"Error fetching options data: {response.text}")
        return pd.DataFrame()

# App Title
st.title("Implied Volatility Surface Dashboard")
st.write("This app visualizes implied volatility surfaces for selected tickers.")

# User Input for Ticker
ticker = st.text_input("Enter a Ticker Symbol:", "AAPL")
if ticker:
    st.write(f"Fetching options data for: {ticker}")
    
    # Fetch data and display
    options_data = fetch_options_data(ticker)
    if not options_data.empty:
        st.write("Options Data Preview:")
        st.dataframe(options_data.head(10))
    else:
        st.write("No data available for the entered ticker.")
