import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("Fetching available models...")

try:
    # Configure the API key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file. Please make sure it's set.")
    
    genai.configure(api_key=api_key)

    # List all models and check if they support the 'generateContent' method
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"✅ Found model: {m.name}")

except Exception as e:
    print(f"\n❌ An error occurred: {e}")
    print("\n💡 Tip: If the error persists, your API key might be invalid or not enabled for the Generative Language API in your Google Cloud project.")

