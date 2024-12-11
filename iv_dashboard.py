import streamlit as st
import pandas as pd
import requests
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Function to fetch options data from Tradier API
def fetch_options_data(symbol, expiration):
    url = f"https://api.tradier.com/v1/markets/options/chains"
    headers = {"Authorization": "Bearer 7uMZjb2elQAxxOdOGhrgDkqPEqSy", "Accept": "application/json"}
    params = {
        "symbol": symbol,
        "expiration": expiration,
        "greeks": "true"  # Request Greeks and implied volatility
    }
    response = requests.get(url, headers=headers, params=params)
    options = response.json().get("options", {}).get("option", [])
    return pd.DataFrame(options)

# Function to fetch the previous day's closing price from Tradier
def fetch_previous_day_close(symbol):
    url = f"https://api.tradier.com/v1/markets/quotes"
    headers = {"Authorization": "Bearer YOUR_API_TOKEN", "Accept": "application/json"}
    params = {"symbols": symbol}
    response = requests.get(url, headers=headers, params=params)
    data = response.json().get('quotes', {}).get('quote', [])
    if data:
        return float(data[0].get('close', 0))  # Return the close price
    return None

# Define Streamlit UI
st.title("Options Analytics Dashboard")
symbol = st.text_input("Enter a Ticker Symbol:", "AAPL")

# Fetch the previous day's close price
previous_close = fetch_previous_day_close(symbol)
if previous_close:
    st.write(f"Previous Day's Close Price of {symbol}: ${previous_close}")
else:
    st.write(f"Could not fetch the live price for {symbol}.")

# Select expiration date
expiration_date = st.date_input("Select Expiration Date:")

# Fetch options data
if symbol and expiration_date:
    options_data = fetch_options_data(symbol, expiration_date)

    # Filter the puts and calls separately
    puts_data = options_data[options_data['type'] == 'put']
    calls_data = options_data[options_data['type'] == 'call']

    # Remove the Puts and Calls Data Preview header
    st.empty()  # Remove unnecessary Puts and Calls preview table

    # Perform analysis based on user selection
    analysis_choice = st.radio("Choose an analysis type:", ["Implied Volatility Surface", "Volatility Smile"])

    if analysis_choice == "Implied Volatility Surface":
        # Prepare data for plotting the implied volatility surface
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='3d')

        # Create meshgrid for plotting
        strike_values = np.array(options_data['strike'])
        expiry_dates = np.array(options_data['expiration_date'])
        iv_values = np.array(options_data['implied_volatility'])

        X, Y = np.meshgrid(strike_values, expiry_dates)
        Z = iv_values.reshape(X.shape)

        ax.plot_surface(X, Y, Z, cmap='viridis')

        ax.set_xlabel('Strike Price')
        ax.set_ylabel('Expiration Date')
        ax.set_zlabel('Implied Volatility')
        ax.set_title('Implied Volatility Surface')

        st.pyplot(fig)

    elif analysis_choice == "Volatility Smile":
        # Plot volatility smile
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(puts_data['strike'], puts_data['implied_volatility'], color='blue', label='Puts')
        ax.scatter(calls_data['strike'], calls_data['implied_volatility'], color='red', label='Calls')

        ax.set_xlabel('Strike Price')
        ax.set_ylabel('Implied Volatility')
        ax.set_title('Volatility Smile')
        ax.legend()

        st.pyplot(fig)

else:
    st.write("No options data available for the selected expiration or ticker.")
