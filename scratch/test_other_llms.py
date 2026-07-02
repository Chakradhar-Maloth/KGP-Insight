import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

def test_model(model_name):
    print(f"Testing LLM generation with {model_name}:")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Say hello in one word")
        print(f"✔ Success! Response: {response.text}")
        return True
    except Exception as e:
        print(f"✘ Failed: {e}\n")
        return False

# Test different models
test_model("gemini-1.5-flash")
test_model("gemini-2.0-flash-lite")
test_model("gemini-flash-latest")
