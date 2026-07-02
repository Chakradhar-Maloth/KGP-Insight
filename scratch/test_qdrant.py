import os
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_KEY = os.environ.get("QDRANT_API_KEY")

qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)

print("QdrantClient type:", type(qdrant))
print("\nDirectory list of QdrantClient methods:")
methods = [m for m in dir(qdrant) if not m.startswith("_")]
for m in sorted(methods):
    print(m)
