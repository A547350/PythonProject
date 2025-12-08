import streamlit as st
import yfinance as yf
import pandas as pd
from agent import get_ai_response
import os

st.set_page_config(layout="wide", page_title="AI Trading Studio")

# --- Title and Logo ---
logo_path = "logo.png"
if os.path.exists(logo_path):
    col1, col2 = st.columns([0.1, 0.9])
    with col1:
        st.image(logo_path, width=100)
    with col2:
        st.title("AI-Powered Trading Studio")
else:
    st.title("AI-Powered Trading Studio")

# --- AI-Powered Recommendation Functions with Caching ---
@st.cache_data(ttl=3600) # Cache for 1 hour
def get_stock_of_the_day():
    """Generates a broad, market-wide stock recommendation."""
    prompt = "As an expert financial analyst, identify one 'Stock of the Day' from the Indian stock market (NSE)..."
    return get_ai_response(prompt)

@st.cache_data(ttl=600) # Cache for 10 minutes
def get_intraday_signal(symbol):
    """Generates a Buy/Sell signal for a specific stock."""
    prompt = f"As a technical analyst, provide an intraday trading signal for {symbol}..."
    return get_ai_response(prompt)

# --- Data Loading and Persistence ---
@st.cache_data
def fetch_nse_stocks():
    """Fetches the list of all NSE-listed equity stocks."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        df = pd.read_csv(url)[['SYMBOL', 'NAME OF COMPANY']].rename(columns={'SYMBOL': 'Symbol', 'NAME OF COMPANY': 'CompanyName'})
        df['Symbol'] = df['Symbol'] + '.NS'
        df['Display'] = df['Symbol'] + " - " + df['CompanyName']
        return df
    except Exception as e:
        st.error(f"Failed to fetch live stock list: {e}")
        return pd.DataFrame(columns=['Symbol', 'CompanyName', 'Display'])

def load_watchlist():
    if os.path.exists("watchlist.txt"):
        with open("watchlist.txt", "r") as f:
            return [line.strip() for line in f if line.strip()]
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

def save_watchlist(watchlist):
    with open("watchlist.txt", "w") as f:
        for symbol in watchlist:
            f.write(f"{symbol}\n")

# --- Initialize Session State ---
nse_stocks_df = fetch_nse_stocks()
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = load_watchlist()
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "How can I help you?"}]

# --- UI Sections ---
st.subheader("✨ AI Stock of the Day")
if st.button("Generate Today's Recommendation"):
    with st.spinner("Analyzing the market..."):
        st.session_state.stock_of_the_day = get_stock_of_the_day()
if 'stock_of_the_day' in st.session_state and st.session_state.stock_of_the_day:
    st.info(st.session_state.stock_of_the_day)

st.subheader("📈 Intraday Trading Signal")
if st.session_state.watchlist:
    selected_stock = st.selectbox("Select a stock from your watchlist for analysis:", options=[""] + st.session_state.watchlist)
    if st.button("Generate Intraday Signal"):
        if selected_stock:
            with st.spinner(f"Analyzing {selected_stock}..."):
                st.session_state.intraday_signal = get_intraday_signal(selected_stock)
        else:
            st.warning("Please select a stock first.")
if 'intraday_signal' in st.session_state and st.session_state.intraday_signal:
    st.success(st.session_state.intraday_signal)

st.divider()

# --- Main Layout ---
col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.header("My Watchlist")
    with st.expander("Add New Stock"):
        selected_stock_display = st.selectbox("Search and Add Stock", options=nse_stocks_df['Display'], index=None, placeholder="Type to search...")
        if st.button("Add Stock"):
            if selected_stock_display:
                new_stock = selected_stock_display.split(" - ")[0]
                if new_stock not in st.session_state.watchlist:
                    st.session_state.watchlist.append(new_stock)
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Added {new_stock}")
                    st.rerun()

    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Add a stock to get started.")
    else:
        watchlist_data = []
        for symbol in st.session_state.watchlist:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                data = {"Symbol": symbol, "Price": info.get('regularMarketPrice', 'N/A'), "Open": info.get('open', 'N/A'), "High": info.get('dayHigh', 'N/A'), "Low": info.get('dayLow', 'N/A')}
                watchlist_data.append(data)
            except Exception:
                st.warning(f"Could not fetch data for {symbol}.")
        
        if watchlist_data:
            df = pd.DataFrame(watchlist_data)
            df["Select"] = False
            df = df[["Select", "Symbol", "Price", "Open", "High", "Low"]]
            edited_df = st.data_editor(df, hide_index=True, column_config={"Select": st.column_config.CheckboxColumn(required=True)}, disabled=["Symbol", "Price", "Open", "High", "Low"])
            if st.button("Delete Selected Stocks"):
                symbols_to_delete = edited_df[edited_df.Select]["Symbol"].tolist()
                if symbols_to_delete:
                    st.session_state.watchlist = [s for s in st.session_state.watchlist if s not in symbols_to_delete]
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Deleted {len(symbols_to_delete)} stock(s).")
                    st.rerun()

with col2:
    st.header("AI Assistant")
    chat_container = st.container(height=500)
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    if prompt := st.chat_input("Ask the AI about a stock..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)
        with chat_container:
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = get_ai_response(prompt)
                    st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})
