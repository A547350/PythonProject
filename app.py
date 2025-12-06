import streamlit as st
import yfinance as yf
import pandas as pd
from agent import get_ai_response
import os

st.set_page_config(layout="wide")

st.title("AI-Powered Trading Studio")

WATCHLIST_FILE = "watchlist.txt"

# --- AI-Powered Recommendation Functions ---
def get_stock_of_the_day():
    """Generates a broad, market-wide stock recommendation."""
    prompt = """
    As an expert financial analyst, identify one 'Stock of the Day' from the Indian stock market (NSE).
    Analyze current market sentiment, sector strength, and geopolitical factors to provide a recommendation
    in the format: **Stock:** [SYMBOL], **Company:** [Name], **Sector:** [Sector], **Reasoning:** [Justification].
    """
    return get_ai_response(prompt)

def get_intraday_signal(symbol):
    """Generates a Buy/Sell signal for a specific stock."""
    prompt = f"""
    As a technical analyst, provide an intraday trading signal for the stock: {symbol}.
    Focus on short-term momentum, recent price action, and key technical indicators (like RSI, MACD, Volume).
    Your response must be concise and start with either **BUY** or **SELL**.
    
    Format:
    **Signal:** [BUY or SELL]
    **Reasoning:** [A brief, 2-3 sentence justification based on technical factors.]
    """
    return get_ai_response(prompt)

# --- Data Loading and Persistence ---
@st.cache_data
def fetch_nse_stocks():
    """Fetches the list of all NSE-listed equity stocks."""
    try:
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        df = pd.read_csv(url)
        df = df[['SYMBOL', 'NAME OF COMPANY']].rename(columns={'SYMBOL': 'Symbol', 'NAME OF COMPANY': 'CompanyName'})
        df['Symbol'] = df['Symbol'] + '.NS'
        df['Display'] = df['Symbol'] + " - " + df['CompanyName']
        return df
    except Exception as e:
        st.error(f"Failed to fetch live stock list: {e}")
        return pd.DataFrame(columns=['Symbol', 'CompanyName', 'Display'])

def load_watchlist():
    """Loads the watchlist from a text file."""
    if os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "r") as f:
            return [line.strip() for line in f if line.strip()]
    return ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]

def save_watchlist(watchlist):
    """Saves the watchlist to a text file."""
    with open(WATCHLIST_FILE, "w") as f:
        for symbol in watchlist:
            f.write(f"{symbol}\n")

# --- Initialize Session State ---
nse_stocks_df = fetch_nse_stocks()
for key, default in [('watchlist', load_watchlist()), 
                     ('messages', [{"role": "assistant", "content": "How can I help you?"}]),
                     ('stock_of_the_day', None),
                     ('intraday_signal', None)]:
    if key not in st.session_state:
        st.session_state[key] = default

# --- UI Sections ---
st.subheader("✨ AI Stock of the Day")
if st.button("Generate Today's Recommendation"):
    with st.spinner("Analyzing the market..."):
        st.session_state.stock_of_the_day = get_stock_of_the_day()
if st.session_state.stock_of_the_day:
    st.info(st.session_state.stock_of_the_day)

st.subheader("📈 Intraday Trading Signal")
if st.session_state.watchlist:
    selected_stock_for_signal = st.selectbox("Select a stock from your watchlist for analysis:", options=[""] + st.session_state.watchlist, key="intraday_stock_selector")
    if st.button("Generate Intraday Signal"):
        if selected_stock_for_signal:
            with st.spinner(f"Analyzing {selected_stock_for_signal}..."):
                st.session_state.intraday_signal = get_intraday_signal(selected_stock_for_signal)
        else:
            st.warning("Please select a stock first.")
if st.session_state.intraday_signal:
    st.success(st.session_state.intraday_signal)

st.divider()

col1, col2 = st.columns([0.6, 0.4])

with col1:
    st.header("My Watchlist")
    
    with st.expander("Add New Stock"):
        selected_stock_display = st.selectbox(
            "Search and Add Stock",
            options=nse_stocks_df['Display'],
            index=None,
            placeholder="Type to search for any NSE stock..."
        )
        if st.button("Add Stock"):
            if selected_stock_display:
                new_stock_symbol = selected_stock_display.split(" - ")[0]
                if new_stock_symbol not in st.session_state.watchlist:
                    st.session_state.watchlist.append(new_stock_symbol)
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Added {new_stock_symbol}")
                    st.rerun()
                else:
                    st.warning(f"{new_stock_symbol} is already in the watchlist.")

    if not st.session_state.watchlist:
        st.info("Your watchlist is empty. Add a stock to get started.")
    else:
        watchlist_data = []
        for symbol in st.session_state.watchlist:
            try:
                stock = yf.Ticker(symbol)
                info = stock.info
                data = {
                    "Symbol": symbol,
                    "Price": info.get('regularMarketPrice', 'N/A'),
                    "Open": info.get('open', 'N/A'),
                    "High": info.get('dayHigh', 'N/A'),
                    "Low": info.get('dayLow', 'N/A'),
                }
                watchlist_data.append(data)
            except Exception:
                st.warning(f"Could not fetch data for {symbol}.")
        
        if watchlist_data:
            df = pd.DataFrame(watchlist_data)
            df["Select"] = False
            df = df[["Select", "Symbol", "Price", "Open", "High", "Low"]]
            
            edited_df = st.data_editor(
                df, 
                hide_index=True,
                column_config={"Select": st.column_config.CheckboxColumn(required=True)},
                disabled=["Symbol", "Price", "Open", "High", "Low"]
            )

            if st.button("Delete Selected Stocks"):
                symbols_to_delete = edited_df[edited_df.Select]["Symbol"].tolist()
                if symbols_to_delete:
                    st.session_state.watchlist = [s for s in st.session_state.watchlist if s not in symbols_to_delete]
                    save_watchlist(st.session_state.watchlist)
                    st.success(f"Deleted {len(symbols_to_delete)} stock(s).")
                    st.rerun()
                else:
                    st.warning("No stocks selected for deletion.")

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
