import os
from dotenv import load_dotenv
load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY", "")
print("OpenAI key length:", len(openai_key))
print("OpenAI key starts with:", openai_key[:10] if openai_key else "None")

try:
    import openai
    client = openai.OpenAI(api_key=openai_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Say hello"}],
        temperature=0.2
    )
    print("OpenAI Success:", response.choices[0].message.content)
except Exception as e:
    print("OpenAI Error:", e)

gemini_key = os.getenv("GEMINI_API_KEY", "")
print("Gemini key length:", len(gemini_key))
try:
    import google.generativeai as genai
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say hello")
    print("Gemini Success:", response.text)
except Exception as e:
    print("Gemini Error:", e)
