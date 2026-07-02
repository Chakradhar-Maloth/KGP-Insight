import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

print("Testing LLM generation with gemini-2.0-flash:")
try:
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content("Say hello in one word")
    print(f"✔ Success! Response: {response.text}")
except Exception as e:
    print(f"Failed gemini-2.0-flash: {e}")

print("\nTesting LLM generation with models/gemini-2.0-flash:")
try:
    model = genai.GenerativeModel("models/gemini-2.0-flash")
    response = model.generate_content("Say hello in one word")
    print(f"✔ Success! Response: {response.text}")
except Exception as e:
    print(f"Failed models/gemini-2.0-flash: {e}")
