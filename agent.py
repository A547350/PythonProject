import google.generativeai as genai
from google.generativeai.types import content_types
import os
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

# 1. SETUP: Configure API Key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")
genai.configure(api_key=api_key)

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
        open_price = hist['Open'].iloc[0]
        current_price = hist['Close'].iloc[-1]
        if current_price > open_price:
            trend = "Up"
        elif current_price < open_price:
            trend = "Down"
        else:
            trend = "Flat"
        return {"trend": trend, "open": f"{open_price:.2f}", "current": f"{current_price:.2f}"}
    except IndexError:
        return {"error": f"Could not retrieve trend for {ticker}."}

# 3. THE BRAIN: Robust Function-Calling Implementation
available_tools = {
    "get_stock_price": get_stock_price,
    "get_market_sentiment": get_market_sentiment,
    "get_intraday_trend": get_intraday_trend,
}

client = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    tools=list(available_tools.values())
)

def get_ai_response(prompt):
    """
    Sends a prompt and handles single or parallel function-calling loops manually.
    """
    chat = client.start_chat()
    response = chat.send_message(prompt)
    
    try:
        # Loop as long as the model wants to call functions
        while response.candidates[0].content.parts and response.candidates[0].content.parts[0].function_call:
            function_calls = response.candidates[0].content.parts
            tool_responses = []

            # Execute all function calls requested in parallel
            for call in function_calls:
                tool_name = call.function_call.name
                if tool_name not in available_tools:
                    raise ValueError(f"Tool '{tool_name}' not found.")
                
                tool_function = available_tools[tool_name]
                tool_args = {key: value for key, value in call.function_call.args.items()}
                
                # Call the tool and get the result
                result = tool_function(**tool_args)
                
                tool_responses.append(content_types.to_part({
                    "function_response": {"name": tool_name, "response": result}
                }))

            # Send all tool responses back to the model in a single message
            response = chat.send_message(tool_responses)

    except (ValueError, IndexError) as e:
        # If there's no function call or an unexpected structure, we assume it's a text response
        print(f"Exiting function-calling loop due to: {e}") # Optional: for debugging
        pass

    return response.text

# 4. Example Usage
if __name__ == "__main__":
    user_prompt = "What is the price and intraday trend for both RELIANCE.NS and TCS.NS?"
    ai_response = get_ai_response(user_prompt)
    print(ai_response)
