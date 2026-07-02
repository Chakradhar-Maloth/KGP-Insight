import os
import google.generativeai as genai
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_KEY = os.environ.get("QDRANT_API_KEY")
COLLECTION_NAME = "kgp_insight_collection"

genai.configure(api_key=GEMINI_KEY)
qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=60.0)

# Generate dummy vector
embed_res = genai.embed_content(
    model="models/gemini-embedding-001",
    content="How do hostel allotments work?",
    task_type="retrieval_query"
)
query_vector = embed_res["embedding"]

print("Testing search via query_points...")
try:
    response = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3
    )
    print("✔ Success! Retrieved points count:", len(response.points))
    for hit in response.points:
        print(f"Point ID: {hit.id} | Score: {hit.score} | Title: {hit.payload.get('title')}")
except Exception as e:
    print(f"✘ Failed query_points: {e}")
