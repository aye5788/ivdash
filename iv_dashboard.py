import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go

# Function to fetch options data from Tradier API
def fetch_options_data(symbol, expiration):
    url = f"https://api.tradier.com/v1/markets/options/chains"
    headers = {
        "Authorization": "Bearer 7uMZjb2elQAxxOdOGhrgDkqPEqSy",  # Replace with your API token
        "Accept": "application/json"
    }
    params = {
        "symbol": symbol,
        "expiration": expiration,
        "greeks": "true"  # Include Greeks and implied volatility
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        options = response.json().get("options", {}).get("option", [])
        return pd.DataFrame(options)
    else:
        st.error(f"Failed to fetch options data. Status Code: {response.status_code}")
        st.write(f"Raw Response Text: {response.text}")
        return None

# Function to fetch the previous day's closing price from Tradier
def fetch_previous_day_close(symbol):
    url = "https://api.tradier.com/v1/markets/quotes"
    headers = {
        "Authorization": "Bearer YOUR_API_TOKEN",  # Replace with your API token
        "Accept": "application/json"
    }
    params = {
        "symbols": symbol
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        data = response.json().get("quotes", {}).get("quote", {})
        return data.get("prevclose")
    else:
        st.error(f"Failed to fetch previous day's close price. Status Code: {response.status_code}")
        st.write(f"Raw Response Text: {response.text}")
        return None

# Function to plot the implied volatility surface
def plot_iv_surface(options_data):
    calls = options_data[options_data["option_type"] == "call"]
    if "implied_volatility" in calls.columns and "strike" in calls.columns and "expiration_date" in calls.columns:
        fig = go.Figure(
            data=[
                go.Scatter3d(
                    x=calls["strike"],
                    y=pd.to_datetime(calls["expiration_date"]),
                    z=calls["implied_volatility"],
                    mode="markers",
                    marker=dict(size=5, color=calls["implied_volatility"], colorscale="Viridis"),
                )
            ]
        )
        fig.update_layout(
            scene=dict(
                xaxis_title="Strike Price",
                yaxis_title="Expiration Date",
                zaxis_title="Implied Volatility"
            ),
            title="Implied Volatility Surface"
        )
        st.plotly_chart(fig)
    else:
        st.error("Insufficient data to plot implied volatility surface.")

# Streamlit App
st.title("Options Analytics Dashboard")

# Input for symbol
symbol = st.text_input("Enter a Ticker Symbol:", value="AAPL")

# Fetch previous day's close price
if symbol:
    previous_close = fetch_previous_day_close(symbol)
    if previous_close:
        st.write(f"Previous Day's Close Price of {symbol}: ${previous_close:.2f}")
    else:
        st.error("Previous day's close price not available.")

# Input for expiration date
expiration = st.date_input("Select Expiration Date:")
if expiration:
    expiration = expiration.strftime("%Y-%m-%d")

# Fetch and display options data
if st.button("Fetch Options Data") and symbol and expiration:
    options_data = fetch_options_data(symbol, expiration)
    if options_data is not None and not options_data.empty:
        # Perform analysis
        analysis_choice = st.radio("Choose an analysis type:", ("Implied Volatility Surface", "Volatility Smile"))
        if analysis_choice == "Implied Volatility Surface":
            plot_iv_surface(options_data)
        elif analysis_choice == "Volatility Smile":
            st.write("Volatility Smile analysis is under development.")
    else:
        st.error("No options data available for the selected expiration date.")
