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

# --- Function to fetch previous day's closing price using Tradier ---
def fetch_ticker_price(symbol):
    url = f"https://api.tradier.com/v1/markets/quotes"
    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    params = {"symbols": symbol}
    
    response = requests.get(url, headers=headers, params=params)
    
    # Log the response to debug the issue
    st.write(f"Response from Tradier API for {symbol}: {response.json()}")  # Debugging line
    
    if response.status_code == 200:
        try:
            # Extract the latest closing price from Tradier's response
            data = response.json()
            quote = data.get("quotes", {}).get("quote", {})
            # Prefer the 'close' price if available, otherwise fallback to 'last'
            latest_close = quote.get("close") or quote.get("last")  # Using 'last' price as a fallback
            
            if latest_close is not None:
                return float(latest_close)
            else:
                st.error(f"Closing price (or last trade price) not available for {symbol}.")
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

# --- Interpret IV Surface ---
def interpret_iv_surface(options_data):
    if "strike" in options_data.columns and "implied_volatility" in options_data.columns:
        avg_iv_by_strike = options_data.groupby("strike")["implied_volatility"].mean()

        if avg_iv_by_strike.empty:
            st.write("No volatility data to interpret.")
            return

        # Determine if the volatility is trending up or down
        trend_direction = "upward" if avg_iv_by_strike.diff().mean() > 0 else "downward"

        st.write(f"**Implied Volatility Surface Insights:**")
        st.write(f"Volatility is trending **{trend_direction}** across strike prices.")
        st.write(f"Implied Volatility analysis helps to identify which strikes are overpriced or underpriced.")
    else:
        st.error("Required columns for IV surface interpretation are missing.")

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
                    st.write("Options Data Preview:")
                    
                    # Separate Puts and Calls
                    puts_data = options_data[options_data['type'] == 'put']
                    calls_data = options_data[options_data['type'] == 'call']

                    # Find the closest strike to the current price (ATM strikes)
                    puts_data['price_diff'] = abs(puts_data['strike'] - ticker_price)
                    calls_data['price_diff'] = abs(calls_data['strike'] - ticker_price)

                    # Remove NaN values before finding the minimum difference
                    puts_data = puts_data.dropna(subset=['price_diff'])
                    calls_data = calls_data.dropna(subset=['price_diff'])

                    # Get the ATM (closest strike) for puts and calls
                    atm_put = puts_data.loc[puts_data['price_diff'].idxmin()] if not puts_data.empty else None
                    atm_call = calls_data.loc[calls_data['price_diff'].idxmin()] if not calls_data.empty else None

                    # Highlight ATM in the table
                    if atm_put is not None:
                        st.write(f"ATM Put: Strike ${atm_put['strike']} | Implied Volatility: {atm_put['implied_volatility']}")
                    if atm_call is not None:
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
