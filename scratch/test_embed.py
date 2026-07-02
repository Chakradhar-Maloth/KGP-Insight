import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

if not GEMINI_KEY:
    print("Error: GEMINI_API_KEY is not set.")
    exit(1)

genai.configure(api_key=GEMINI_KEY)

print("Listing all generative models:")
try:
    for m in genai.list_models():
        print(f"Model: {m.name} | Supported methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"Failed to list models: {e}")

print("\nTesting embedding with models/text-embedding-004:")
try:
    res = genai.embed_content(
        model="models/text-embedding-004",
        content="Testing connection",
        task_type="retrieval_query"
    )
    print("✔ Success! text-embedding-004 works.")
except Exception as e:
    print(f"Failed text-embedding-004: {e}")

print("\nTesting embedding with models/embedding-001:")
try:
    res = genai.embed_content(
        model="models/embedding-001",
        content="Testing connection",
        task_type="retrieval_query"
    )
    print("✔ Success! embedding-001 works.")
except Exception as e:
    print(f"Failed embedding-001: {e}")
