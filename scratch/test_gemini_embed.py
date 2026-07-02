import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)

print("Testing models/gemini-embedding-001:")
try:
    res = genai.embed_content(
        model="models/gemini-embedding-001",
        content="Testing connection",
        task_type="retrieval_query"
    )
    vec = res["embedding"]
    print(f"✔ Success! Vector length: {len(vec)}")
except Exception as e:
    print(f"Failed models/gemini-embedding-001: {e}")

print("\nTesting models/gemini-embedding-2:")
try:
    res = genai.embed_content(
        model="models/gemini-embedding-2",
        content="Testing connection",
        task_type="retrieval_query"
    )
    vec = res["embedding"]
    print(f"✔ Success! Vector length: {len(vec)}")
except Exception as e:
    print(f"Failed models/gemini-embedding-2: {e}")
