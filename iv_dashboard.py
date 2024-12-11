import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Function to fetch options data from Tradier API
def fetch_options_data(symbol, expiration):
    url = "https://api.tradier.com/v1/markets/options/chains"
    headers = {"Authorization": "Bearer 7uMZjb2elQAxxOdOGhrgDkqPEqSy", "Accept": "application/json"}
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        options = response.json().get("options", {}).get("option", [])
        return pd.DataFrame(options)
    st.error("Failed to fetch options data.")
    return pd.DataFrame()

# Function to fetch the previous day's closing price from Tradier
def fetch_previous_day_close(symbol):
    url = "https://api.tradier.com/v1/markets/quotes"
    headers = {"Authorization": "Bearer YOUR_API_TOKEN", "Accept": "application/json"}
    params = {"symbols": symbol}
    response = requests.get(url, headers=headers, params=params)
    
    # Log the raw response for debugging
    st.write("Raw Response Text:", response.text)
    
    if response.status_code == 200:
        try:
            data = response.json().get("quotes", {}).get("quote", {})
            if data:
                return float(data.get("prevclose", 0))  # Return the previous close price
        except requests.exceptions.JSONDecodeError:
            st.error("Invalid response from Tradier API. Please check your API key and symbol.")
            return None
    st.error("Failed to fetch previous day's close price.")
    return None

# Function to plot the implied volatility surface
def plot_iv_surface(options_data):
    if not options_data.empty:
        calls = options_data[options_data['option_type'] == 'call']
        puts = options_data[options_data['option_type'] == 'put']
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.scatter(
            calls['strike'], pd.to_datetime(calls['expiration_date']), calls['implied_volatility'],
            label='Calls', c='b', marker='o'
        )
        ax.scatter(
            puts['strike'], pd.to_datetime(puts['expiration_date']), puts['implied_volatility'],
            label='Puts', c='r', marker='x'
        )
        ax.set_xlabel('Strike Price')
        ax.set_ylabel('Expiration Date')
        ax.set_zlabel('Implied Volatility')
        ax.legend()
        st.pyplot(fig)
    else:
        st.error("No options data available to plot IV surface.")

# Streamlit UI
st.title("Options Analytics Dashboard")

# User input for ticker symbol
symbol = st.text_input("Enter a Ticker Symbol:", value="AAPL")

# Fetch and display the previous day's close price
if symbol:
    previous_close = fetch_previous_day_close(symbol)
    if previous_close:
        st.write(f"Previous Day's Close Price of {symbol.upper()}: ${previous_close}")
    else:
        st.write("Previous day's close price not available.")

# Dropdown for expiration dates
expiration_dates = ["2024-12-13", "2024-12-20"]  # Placeholder expiration dates
selected_expiration = st.selectbox("Select Expiration Date:", expiration_dates)

# Fetch and analyze options data
if selected_expiration:
    options_data = fetch_options_data(symbol, selected_expiration)
    if not options_data.empty:
        st.write("Analysis Results")
        analysis_choice = st.radio(
            "Choose an analysis type:", ["Implied Volatility Surface", "Volatility Smile"]
        )
        if analysis_choice == "Implied Volatility Surface":
            plot_iv_surface(options_data)
        elif analysis_choice == "Volatility Smile":
            fig, ax = plt.subplots()
            ax.scatter(options_data['strike'], options_data['implied_volatility'])
            ax.set_xlabel("Strike Price")
            ax.set_ylabel("Implied Volatility")
            ax.set_title("Volatility Smile")
            st.pyplot(fig)
    else:
        st.error("No options data available for the selected expiration date.")
