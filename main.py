import yfinance as yf
from agent import get_ai_response

def fetch_stock_data(symbol):
    """Fetches stock data from Yahoo Finance."""
    stock = yf.Ticker(symbol)
    return stock.info

def display_watchlist(watchlist):
    """Displays the watchlist."""
    print("--- My Watchlist ---")
    for symbol, data in watchlist.items():
        print(f"{symbol}: {data.get('regularMarketPrice', 'N/A')}")

def main():
    """Main function to run the watchlist app."""
    watchlist_symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS"]  # Example watchlist
    watchlist_data = {}

    for symbol in watchlist_symbols:
        data = fetch_stock_data(symbol)
        watchlist_data[symbol] = data

    display_watchlist(watchlist_data)

    print("\n--- AI Assistant ---")
    while True:
        prompt = input("Ask the AI about a stock (or type 'quit'): ")
        if prompt.lower() == 'quit':
            break
        response = get_ai_response(prompt)
        print(f"AI: {response}")

if __name__ == "__main__":
    main()
