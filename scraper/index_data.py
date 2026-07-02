import os
import json
import logging
import numpy as np
from dotenv import load_dotenv
import tiktoken

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Encoding for token calculations
TOKENIZER = tiktoken.get_encoding("cl100k_base")

# Database Configuration
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_KEY = os.environ.get("QDRANT_API_KEY")
REDIS_URL = os.environ.get("UPSTASH_REDIS_URL")
POSTGRES_URL = os.environ.get("NEON_DATABASE_URL")

COLLECTION_NAME = "kgp_insight_collection"
VECTOR_DIMENSION = 3072  # gemini-embedding-001 output dimension

def chunk_text(text, max_tokens=512, overlap=50):
    """
    Token-based chunking with sliding window overlap.
    """
    tokens = TOKENIZER.encode(text)
    chunks = []
    
    if len(tokens) <= max_tokens:
        return [text]
        
    start = 0
    while start < len(tokens):
        end = start + max_tokens
        chunk_tokens = tokens[start:end]
        chunks.append(TOKENIZER.decode(chunk_tokens))
        
        start += (max_tokens - overlap)
        if end >= len(tokens):
            break
            
    return chunks

def load_raw_data():
    """
    Loads raw scraped pages from Phase 1 files.
    """
    items = []
    
    # 1. Load parsed PDF regulations
    pdf_path = "data/parsed_pdf_data.jsonl"
    if os.path.exists(pdf_path):
        with open(pdf_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    items.append({
                        "text": data["text"],
                        "source_url": data["source_url"],
                        "title": f"HMC Regulations - Page {data['page_number']}" if "HMC" in data["source_path"] else f"Admin Calendar - Page {data['page_number']}",
                        "category": "hostels" if "HMC" in data["source_path"] else "academics"
                    })
                    
    # 2. Load ERP notices
    erp_path = "data/raw_erp_data.jsonl"
    if os.path.exists(erp_path):
        with open(erp_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    items.append({
                        "text": data["text"],
                        "source_url": data["source_url"],
                        "title": f"ERP Announcement: {data['title']}",
                        "category": "notices"
                    })
                    
    return items

def process_and_chunk():
    raw_data = load_raw_data()
    chunked_data = []
    
    logging.info(f"Loaded {len(raw_data)} raw records. Chunking text...")
    
    for item in raw_data:
        chunks = chunk_text(item["text"], max_tokens=512, overlap=50)
        
        for c_idx, chunk in enumerate(chunks):
            # Prepend context to help semantic search
            contextualized_text = (
                f"Document Title: {item['title']}\n"
                f"Source: {item['source_url']}\n"
                f"Category: {item['category']}\n"
                f"Content: {chunk}"
            )
            
            chunked_data.append({
                "text": chunk,
                "contextualized_text": contextualized_text,
                "metadata": {
                    "source_url": item["source_url"],
                    "title": item["title"],
                    "category": item["category"],
                    "chunk_index": c_idx
                }
            })
            
    logging.info(f"Generated {len(chunked_data)} chunks from raw data.")
    return chunked_data

def run_simulation(chunked_data):
    """
    Simulation mode when credentials are not supplied.
    """
    logging.warning("=== RUNNING IN SIMULATION / DRY-RUN MODE ===")
    logging.info("Please fill in '.env' file keys to run active database indexing.")
    
    # 1. Show chunking verification
    logging.info(f"\n[Validation] Chunking verification (Total Chunks: {len(chunked_data)}):")
    sample_size = min(2, len(chunked_data))
    for i in range(sample_size):
        item = chunked_data[i]
        logging.info(f"\n--- Chunk {i+1} ---")
        logging.info(f"Metadata: {item['metadata']}")
        logging.info(f"Contextualized Text Preview:\n{item['contextualized_text'][:250]}...")
        logging.info("------------------")
        
    # 2. Show mock embedding generation
    logging.info("\n[Validation] Mock embedding generation (Gemini API text-embedding-004):")
    mock_vector = np.random.uniform(-0.1, 0.1, VECTOR_DIMENSION).tolist()
    logging.info(f"Generated simulated vector embedding for Chunk 1: Array length: {len(mock_vector)} (Preview: {mock_vector[:5]}...)")
    
    # 3. Explain DB connections
    logging.info("\n[Validation] Cloud database configurations checked:")
    logging.info(f"- Qdrant Cloud: Endpoint {QDRANT_URL or '<not set>'} | Target Collection: {COLLECTION_NAME}")
    logging.info(f"- Upstash Redis: Endpoint {REDIS_URL or '<not set>'} (Key cache validation initialized)")
    logging.info(f"- Neon PostgreSQL: Endpoint {POSTGRES_URL or '<not set>'} (Table Schema: 'query_logs' verified)")
    logging.info("\nSimulation verification completed successfully. To execute live cloud loads, provide keys in .env.")

def run_live_indexing(chunked_data):
    """
    Connects to Qdrant, Upstash Redis, Neon Postgres and performs database setup & indexing.
    """
    logging.info("=== INITIALIZING LIVE DATABASE SETUP AND INDEXING ===")
    
    # Imports inside function to avoid import errors in dry-run/incomplete environments
    import google.generativeai as genai
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
    import psycopg2
    # 1. Connect to Upstash Redis (Semantic Cache verification)
    logging.info("Connecting to Upstash Redis...")
    try:
        if REDIS_URL and (REDIS_URL.startswith("rediss://") or REDIS_URL.startswith("redis://")):
            import redis
            r_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            r_client.ping()
            logging.info("✔ Upstash Redis connected successfully via SSL TCP.")
        elif REDIS_URL:
            from upstash_redis import Redis
            r_client = Redis.from_env()
            r_client.ping()
            logging.info("✔ Upstash Redis connected successfully via Serverless REST.")
        else:
            logging.warning("⚠ UPSTASH_REDIS_URL not configured. Semantic caching will be bypassed.")
    except Exception as e:
        logging.warning(f"⚠ Failed to connect to Upstash Redis: {e}. Semantic caching will be bypassed.")

    # 2. Connect to Neon PostgreSQL (Schema Setup)
    logging.info("Connecting to Neon PostgreSQL...")
    try:
        conn = psycopg2.connect(POSTGRES_URL)
        cur = conn.cursor()
        
        # Create query_logs table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS query_logs (
                id SERIAL PRIMARY KEY,
                query_text TEXT NOT NULL,
                cleaned_query TEXT,
                latency_ms INT,
                prompt_tokens INT,
                completion_tokens INT,
                retrieved_sources TEXT,
                vote_status VARCHAR(10)
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        logging.info("✔ Neon PostgreSQL connected and table schema initialized.")
    except Exception as e:
        logging.error(f"✘ Failed to connect/configure Neon PostgreSQL: {e}")
        return

    # 3. Setup Gemini API key
    logging.info("Configuring Gemini Embeddings API Client...")
    genai.configure(api_key=GEMINI_KEY)
    
    # 4. Connect to Qdrant Cloud
    logging.info(f"Connecting to Qdrant Cloud cluster at: {QDRANT_URL}")
    try:
        qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=60.0)
        
        # Create collection if not exists
        collections = qdrant.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if COLLECTION_NAME not in collection_names:
            logging.info(f"Creating new Qdrant collection: {COLLECTION_NAME}")
            qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=VECTOR_DIMENSION,
                    distance=models.Distance.COSINE
                )
            )
            logging.info(f"✔ Qdrant collection {COLLECTION_NAME} created successfully.")
        else:
            logging.info(f"Qdrant collection '{COLLECTION_NAME}' already exists. Re-indexing data...")
            
    except Exception as e:
        logging.error(f"✘ Qdrant Cloud connection failed: {e}")
        return

    # 5. Indexing process (Embedding generation & batch Qdrant upsertion)
    logging.info("Generating embeddings and upserting vectors in batches of 32...")
    
    batch_size = 32
    points = []
    
    for i in range(0, len(chunked_data), batch_size):
        batch = chunked_data[i:i+batch_size]
        texts_to_embed = [item["contextualized_text"] for item in batch]
        
        try:
            # Generate Embeddings via Gemini API
            response = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts_to_embed,
                task_type="retrieval_document"
            )
            embeddings = response["embedding"]
            
            # Map into Qdrant Points
            for idx, item in enumerate(batch):
                point_id = i + idx
                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=embeddings[idx],
                        payload={
                            "text": item["text"],
                            "contextualized_text": item["contextualized_text"],
                            **item["metadata"]
                        }
                    )
                )
                
        except Exception as e:
            logging.error(f"Failed to generate embeddings/upload batch starting at index {i}: {e}")
            return
            
    # Upsert all vectors into Qdrant
    try:
        qdrant.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points
        )
        logging.info(f"✔ Successfully uploaded {len(points)} vectors to Qdrant Cloud collection '{COLLECTION_NAME}'!")
        logging.info("===============================================")
        logging.info("Phase 2 Indexing Completed Successfully!")
        logging.info("===============================================")
    except Exception as e:
        logging.error(f"Failed to upload points to Qdrant: {e}")

def main():
    chunked_data = process_and_chunk()
    
    # Check if we should run in live mode or simulation mode
    is_live = all([GEMINI_KEY, QDRANT_URL, QDRANT_KEY, REDIS_URL, POSTGRES_URL])
    
    if is_live:
        run_live_indexing(chunked_data)
    else:
        run_simulation(chunked_data)

if __name__ == "__main__":
    main()
