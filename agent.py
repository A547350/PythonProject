import google.generativeai as genai
from google.generativeai.types import content_types
from google.api_core.exceptions import ResourceExhausted
import os
import yfinance as yf
import streamlit as st
import time

# 1. SETUP: Configure API Key using Streamlit's Secret Management
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except (FileNotFoundError, KeyError):
    st.error("GEMINI_API_KEY not found in Streamlit secrets. Please add it to your .streamlit/secrets.toml file.")
    st.stop()

# 2. THE TOOLS: Functions our Agent can use
def get_stock_price(ticker: str):
    """Returns the current trading price of a stock."""
    try:
        stock = yf.Ticker(ticker)
        price = stock.history(period="1d")['Close'].iloc[-1]
        return {"price": f"${price:.2f}"}
    except IndexError:
        return {"error": f"Could not retrieve price for {ticker}."}

def get_market_sentiment(ticker: str):
    """Returns the market sentiment for a stock."""
    try:
        stock = yf.Ticker(ticker)
        sentiment = stock.info.get('recommendationKey', 'N/A')
        return {"sentiment": sentiment.capitalize() if sentiment != 'N/A' else "Not Available"}
    except Exception:
        return {"error": f"Could not retrieve sentiment for {ticker}."}

def get_intraday_trend(ticker: str):
    """Returns the intraday trend for a stock."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        open_price, current_price = hist['Open'].iloc[0], hist['Close'].iloc[-1]
        trend = "Up" if current_price > open_price else "Down" if current_price < open_price else "Flat"
        return {"trend": trend, "open": f"{open_price:.2f}", "current": f"{current_price:.2f}"}
    except IndexError:
        return {"error": f"Could not retrieve trend for {ticker}."}

# 3. THE BRAIN: Robust Function-Calling with Retry Logic
available_tools = {
    "get_stock_price": get_stock_price,
    "get_market_sentiment": get_market_sentiment,
    "get_intraday_trend": get_intraday_trend,
}

client = genai.GenerativeModel(model_name="gemini-2.0-flash", tools=list(available_tools.values()))

def get_ai_response(prompt, retries=3):
    """
    Sends a prompt and handles function-calling loops with exponential backoff for rate limiting.
    """
    chat = client.start_chat()
    
    for i in range(retries):
        try:
            response = chat.send_message(prompt)
            
            while response.candidates[0].content.parts and response.candidates[0].content.parts[0].function_call:
                function_calls = response.candidates[0].content.parts
                tool_responses = []

                for call in function_calls:
                    tool_name = call.function_call.name
                    if tool_name not in available_tools:
                        raise ValueError(f"Tool '{tool_name}' not found.")
                    
                    tool_function = available_tools[tool_name]
                    tool_args = {key: value for key, value in call.function_call.args.items()}
                    result = tool_function(**tool_args)
                    
                    tool_responses.append(content_types.to_part({
                        "function_response": {"name": tool_name, "response": result}
                    }))

                response = chat.send_message(tool_responses)
            
            return response.text # Success

        except ResourceExhausted:
            if i < retries - 1:
                wait_time = 2 ** (i + 1)
                print(f"API quota hit. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return "Error: API Quota Exceeded. Please wait a minute and try again."
        except (ValueError, IndexError) as e:
            print(f"An unexpected error occurred: {e}")
            return "An error occurred while processing the request."
    
    return "Error: The request failed after multiple retries."
