import os
from google import genai
from dotenv import load_dotenv

load_dotenv("//backend/.env")
key = os.getenv("GEMINI_API_KEY", "")
print("API Key loaded:", len(key) > 0)

client = genai.Client(api_key=key)

for model_name in ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemma-2-27b-it"]:
    try:
        print(f"Testing model: {model_name}...")
        response = client.models.generate_content(
            model=model_name,
            contents="Say hello in one word."
        )
        print(f"Success for {model_name}: {response.text.strip()}")
        break
    except Exception as e:
        print(f"Failed for {model_name}: {e}")
