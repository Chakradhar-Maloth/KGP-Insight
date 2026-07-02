import os
import time
import json
import logging
import asyncio
from typing import Optional, List
from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import tiktoken

# Load configuration
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

app = FastAPI(title="KGP Insight API", version="1.0.0")

# Enable CORS for the frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_origin_regex="http://localhost:.*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables to store DB clients
qdrant_client = None
redis_client = None
gemini_model = None
postgres_conn_str = os.environ.get("NEON_DATABASE_URL")

# Load credentials
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_KEY = os.environ.get("QDRANT_API_KEY")
REDIS_URL = os.environ.get("UPSTASH_REDIS_URL")

COLLECTION_NAME = "kgp_insight_collection"
VECTOR_DIMENSION = 3072
TOKENIZER = tiktoken.get_encoding("cl100k_base")

class QueryRequest(BaseModel):
    query: str

class FeedbackRequest(BaseModel):
    query_id: int
    vote: str

class UrlRequest(BaseModel):
    url: str

def initialize_services():
    global qdrant_client, redis_client, gemini_model
    
    # 1. Initialize Gemini
    if GEMINI_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=GEMINI_KEY)
            gemini_model = genai.GenerativeModel("gemini-flash-latest")
            logging.info("✔ Gemini LLM initialized.")
        except Exception as e:
            logging.error(f"Error initializing Gemini: {e}")

    # 2. Initialize Qdrant
    if QDRANT_URL and QDRANT_KEY:
        try:
            from qdrant_client import QdrantClient
            qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=60.0)
            logging.info("✔ Qdrant Cloud client initialized.")
        except Exception as e:
            logging.error(f"Error initializing Qdrant: {e}")

    # 3. Initialize Upstash Redis (Supports SSL TCP rediss:// URLs)
    if REDIS_URL:
        try:
            if REDIS_URL.startswith("rediss://") or REDIS_URL.startswith("redis://"):
                import redis
                redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
                redis_client.ping()
                logging.info("✔ Upstash Redis client initialized via SSL TCP.")
            else:
                from upstash_redis import Redis
                redis_client = Redis.from_env()
                logging.info("✔ Upstash Redis client initialized via serverless REST.")
        except Exception as e:
            logging.error(f"Error initializing Upstash Redis: {e}")

# Run initialization
initialize_services()

# --- Chunking Helper ---
def chunk_text(text: str, max_tokens=512, overlap=50) -> List[str]:
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

# --- Async Background Task Logger ---
async def log_to_postgres(query_text: str, latency_ms: int, sources: List[str], vote: Optional[str] = None):
    if not postgres_conn_str:
        logging.info(f"[Postgres Mock Log] Query: '{query_text}' | Latency: {latency_ms}ms | Sources: {sources}")
        return
        
    try:
        import psycopg2
        conn = psycopg2.connect(postgres_conn_str)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO query_logs (query_text, latency_ms, retrieved_sources, vote_status)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (query_text, latency_ms, json.dumps(sources), vote)
        )
        log_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()
        logging.info(f"Logged query to Neon PostgreSQL (Log ID: {log_id})")
        return log_id
    except Exception as e:
        logging.error(f"PostgreSQL logging failed: {e}")
        return None

# --- Semantic Caching Logic ---
async def check_semantic_cache(query_text: str) -> Optional[str]:
    if not redis_client or not GEMINI_KEY:
        return None
        
    try:
        cache_key = f"cache:{query_text.lower().strip()}"
        cached_result = redis_client.get(cache_key)
        if cached_result:
            logging.info(f"Semantic Cache Hit for: '{query_text}'")
            return cached_result.decode("utf-8") if isinstance(cached_result, bytes) else cached_result
    except Exception as e:
        logging.error(f"Error reading semantic cache: {e}")
        
    return None

async def write_semantic_cache(query_text: str, answer_text: str):
    if not redis_client:
        return
    try:
        cache_key = f"cache:{query_text.lower().strip()}"
        redis_client.setex(cache_key, 3600 * 12, answer_text)
        logging.info(f"Saved answer to semantic cache for query: '{query_text}'")
    except Exception as e:
        logging.error(f"Error writing to semantic cache: {e}")

# --- Hybrid Retrieval ---
def retrieve_relevant_contexts(query_text: str) -> List[dict]:
    if not qdrant_client or not GEMINI_KEY:
        logging.warning("Qdrant / Gemini not configured. Serving mock contexts...")
        return [
            {
                "title": "HMC Regulations - Section 3: Guest Accommodation",
                "source_url": "https://www.iitkgp.ac.in/assets/pdf/Rules_and_RegulationsHMC.pdf",
                "text": "Rule 3.a: If the father/mother/guardian of a boarder needs accommodation for a brief duration (specifically one or two days), it is mandatory for the boarder to intimate the Hall office, preferably two days prior to the anticipated occupancy date."
            },
            {
                "title": "ERP Announcement: Minor Guidelines 2026",
                "source_url": "https://erp.iitkgp.ac.in/Acad/notices/minor_guidelines_2026.pdf",
                "text": "Eligibility requirement for Minor Application is a minimum CGPA of 7.50 at the end of the 4th semester with no backlogs. The selection is strictly based on CGPA merit. Apply via ERP under 'Academic > Minor Application'."
            }
        ]
        
    import google.generativeai as genai

    response = genai.embed_content(
        model="models/gemini-embedding-001",
        content=query_text,
        task_type="retrieval_query"
    )
    query_vector = response["embedding"]

    results = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=15
    ).points

    retrieved_contexts = []
    for hit in results:
        payload = hit.payload
        retrieved_contexts.append({
            "title": payload.get("title", "Untitled Document"),
            "source_url": payload.get("source_url", "https://www.iitkgp.ac.in"),
            "text": payload.get("text", "")
        })

    # Local keyword boost (Simple lexical reranking)
    keywords = query_text.lower().split()
    for ctx in retrieved_contexts:
        score = sum(1 for kw in keywords if kw in ctx["text"].lower())
        ctx["match_score"] = score

    retrieved_contexts.sort(key=lambda x: x.get("match_score", 0), reverse=True)
    return retrieved_contexts[:3]

# --- SSE Streaming Response Generator ---
async def stream_generator(query_text: str, contexts: List[dict], start_time: float, background_tasks: BackgroundTasks):
    context_str = ""
    for idx, ctx in enumerate(contexts):
        context_str += (
            f"[{idx+1}] Title: {ctx['title']}\n"
            f"Source: {ctx['source_url']}\n"
            f"Content: {ctx['text']}\n"
            f"----------------------------------------\n"
        )
        
    prompt = (
        "You are KGP Insight, the official campus RAG AI assistant for IIT Kharagpur.\n"
        "Your task is to answer the user's question accurately using ONLY the provided verified document contexts.\n\n"
        "[VERIFIED CONTEXTS]\n"
        f"{context_str}\n"
        "[END OF CONTEXTS]\n\n"
        "[RULES]\n"
        "1. Structure your response cleanly using Markdown formatting.\n"
        "2. Base your answer solely on the provided contexts. Do not extrapolate, hallucinate, or reference outside information.\n"
        "3. If the context does not contain the answer, say: 'I'm sorry, but I couldn't find verified guidelines for this in the database.'\n"
        "4. Always append a 'Sources Cited' section at the end of the text referencing the exact titles and source_urls of the contexts utilized.\n\n"
        f"User Query: {query_text}\n"
        "Helpful Answer:"
    )

    full_response_text = ""
    
    if not gemini_model:
        # Simulated stream for local prototyping
        mock_chunks = [
            "Based ", "on ", "the HMC ", "Rules ", "and Regulations ", "for the ", "Halls of ", "Residence:\n\n",
            "To ", "accommodate ", "guests (specifically ", "parents/guardians), ", "a student ", "must notify ",
            "the Hall ", "office at ", "least **two days** ", "prior to the ", "expected occupancy date.\n\n",
            "Room allotments ", "are subject ", "to availability. ", "Guest fees ", "must be ", "paid in ",
            "accordance with ", "the HMC guidelines.\n\n",
            "**Sources Cited:**\n",
            "- [HMC Regulations - Section 3: Guest Accommodation](https://www.iitkgp.ac.in/assets/pdf/Rules_and_RegulationsHMC.pdf)"
        ]
        for chunk in mock_chunks:
            full_response_text += chunk
            yield f"data: {json.dumps({'text': chunk})}\n\n"
            await asyncio.sleep(0.08)
    else:
        try:
            response = gemini_model.generate_content(prompt, stream=True)
            for chunk in response:
                chunk_text = chunk.text or ""
                full_response_text += chunk_text
                yield f"data: {json.dumps({'text': chunk_text})}\n\n"
        except Exception as e:
            logging.error(f"Error during streaming generation: {e}")
            yield f"data: {json.dumps({'error': 'Streaming generation interrupted.'})}\n\n"

    background_tasks.add_task(write_semantic_cache, query_text, full_response_text)
    latency_ms = int((time.time() - start_time) * 1000)
    sources = [ctx["source_url"] for ctx in contexts]
    background_tasks.add_task(log_to_postgres, query_text, latency_ms, sources)
    yield "data: [DONE]\n\n"

@app.post("/query")
async def handle_query(request: QueryRequest, background_tasks: BackgroundTasks):
    start_time = time.time()
    query_text = request.query.strip()
    
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    logging.info(f"Received query: '{query_text}'")
    
    cached_response = await check_semantic_cache(query_text)
    if cached_response:
        async def cached_stream():
            yield f"data: {json.dumps({'text': cached_response})}\n\n"
            yield "data: [DONE]\n\n"
            latency_ms = int((time.time() - start_time) * 1000)
            await log_to_postgres(query_text, latency_ms, ["Semantic Cache Hit"])

        return StreamingResponse(cached_stream(), media_type="text/event-stream")

    contexts = retrieve_relevant_contexts(query_text)
    return StreamingResponse(
        stream_generator(query_text, contexts, start_time, background_tasks),
        media_type="text/event-stream"
    )

# --- Dynamic PDF Uploader & Parser (FREE) ---
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Parses PDF using PyMuPDF (fitz) on our server for $0 cost,
    chunks text, computes vector embeddings, and registers to Qdrant Cloud.
    """
    filename = file.filename
    logging.info(f"Received user PDF upload: {filename}")
    
    try:
        # 1. Read bytes & Parse PDF for free via PyMuPDF
        import fitz
        file_bytes = await file.read()
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        
        extracted_text_pages = []
        for idx, page in enumerate(doc):
            p_text = page.get_text()
            if p_text.strip():
                extracted_text_pages.append((idx + 1, p_text))
        
        if not extracted_text_pages:
            raise HTTPException(status_code=400, detail="PDF contains no readable text.")
            
        logging.info(f"Extracted {len(extracted_text_pages)} pages from PDF.")

        # 2. Chunk PDF pages into overlapping blocks
        chunks = []
        for page_num, page_text in extracted_text_pages:
            page_chunks = chunk_text(page_text, max_tokens=512, overlap=50)
            for c_idx, chunk in enumerate(page_chunks):
                contextualized_text = (
                    f"Document: {filename}\n"
                    f"Page: {page_num}\n"
                    f"Source: User Uploaded Reference File\n"
                    f"Content: {chunk}"
                )
                chunks.append({
                    "text": chunk,
                    "contextualized_text": contextualized_text,
                    "metadata": {
                        "source_url": f"user_upload://{filename}",
                        "title": f"Uploaded Doc: {filename} (Page {page_num})",
                        "category": "user_reference",
                        "chunk_index": c_idx
                    }
                })

        # 3. Embedding & Uploading
        if not qdrant_client or not GEMINI_KEY:
            # Simulation response
            logging.warning("Simulation upload: Saved and chunked document locally.")
            return {
                "status": "success",
                "message": f"Successfully parsed '{filename}' (Simulation Mode). Created {len(chunks)} text chunks.",
                "chunks_count": len(chunks)
            }

        import google.generativeai as genai
        from qdrant_client.http import models

        # Generate vectors and upsert in Qdrant
        points = []
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts_to_embed = [item["contextualized_text"] for item in batch]
            
            response = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts_to_embed,
                task_type="retrieval_document"
            )
            embeddings = response["embedding"]
            
            for idx, item in enumerate(batch):
                # Generate unique ID based on timestamp hashing
                point_id = hash(f"{filename}_{i}_{idx}_{time.time()}") % (10**8)
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

        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points
        )
        
        logging.info(f"✔ Successfully indexed {len(points)} chunks from uploaded PDF '{filename}' to Qdrant Cloud!")
        return {
            "status": "success",
            "message": f"Successfully parsed and indexed '{filename}'. Uploaded {len(points)} vector chunks to Qdrant Cloud.",
            "chunks_count": len(points)
        }

    except Exception as e:
        logging.error(f"Failed to process PDF upload: {e}")
        raise HTTPException(status_code=500, detail=f"PDF ingestion failed: {str(e)}")

# --- Dynamic URL Scraper & Parser (FREE) ---
@app.post("/scrape-link")
async def scrape_link(request: UrlRequest):
    """
    Scrapes URL for $0 cost using BeautifulSoup, chunks text,
    computes vector embeddings, and registers to Qdrant Cloud.
    """
    target_url = request.url.strip()
    logging.info(f"Received URL scrape request: {target_url}")
    
    if not target_url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")

    try:
        # 1. Fetch & Parse page for free using BeautifulSoup
        import requests
        from bs4 import BeautifulSoup
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Try high-speed static scrape first
        res = requests.get(target_url, headers=headers, timeout=20)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, "lxml")
        title = soup.title.string.strip() if soup.title else target_url
        
        # Exclude boilerplate elements
        for element in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
            element.decompose()
            
        # Clean text
        text_blocks = [line.strip() for line in soup.stripped_strings if len(line.strip()) > 12]
        clean_text = "\n".join(text_blocks)
        
        # 2. Check if content is thin (indicates JavaScript-rendered page)
        if len(clean_text) < 300:
            logging.info("Static content too thin (<300 chars). Switching to Playwright headless browser for dynamic scraping...")
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                # Create context with a realistic user-agent
                page = await browser.new_page(user_agent=headers["User-Agent"])
                await page.goto(target_url, timeout=30000, wait_until="networkidle")
                
                # Fetch dynamically rendered HTML
                rendered_html = await page.content()
                dynamic_soup = BeautifulSoup(rendered_html, "lxml")
                
                # Exclude boilerplates
                for element in dynamic_soup(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
                    element.decompose()
                
                title = dynamic_soup.title.string.strip() if dynamic_soup.title else title
                text_blocks = [line.strip() for line in dynamic_soup.stripped_strings if len(line.strip()) > 12]
                clean_text = "\n".join(text_blocks)
                
                await browser.close()
                logging.info(f"Successfully scraped dynamic content via Playwright ({len(clean_text)} chars).")

        if not clean_text.strip():
            raise HTTPException(status_code=400, detail="URL contains no extractable body text.")

        # 2. Chunk text
        text_chunks = chunk_text(clean_text, max_tokens=512, overlap=50)
        chunks = []
        for c_idx, chunk in enumerate(text_chunks):
            contextualized_text = (
                f"Webpage: {title}\n"
                f"Link: {target_url}\n"
                f"Source: User Scraped Web Reference\n"
                f"Content: {chunk}"
            )
            chunks.append({
                "text": chunk,
                "contextualized_text": contextualized_text,
                "metadata": {
                    "source_url": target_url,
                    "title": f"Scraped Page: {title}",
                    "category": "user_reference",
                    "chunk_index": c_idx
                }
            })

        # 3. Embedding & Uploading
        if not qdrant_client or not GEMINI_KEY:
            logging.warning("Simulation scrape: Loaded and chunked website content locally.")
            return {
                "status": "success",
                "message": f"Successfully scraped website (Simulation Mode). Created {len(chunks)} text chunks.",
                "chunks_count": len(chunks)
            }

        import google.generativeai as genai
        from qdrant_client.http import models

        points = []
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            texts_to_embed = [item["contextualized_text"] for item in batch]
            
            response = genai.embed_content(
                model="models/gemini-embedding-001",
                content=texts_to_embed,
                task_type="retrieval_document"
            )
            embeddings = response["embedding"]
            
            for idx, item in enumerate(batch):
                point_id = hash(f"{target_url}_{i}_{idx}_{time.time()}") % (10**8)
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

        qdrant_client.upsert(
            collection_name=COLLECTION_NAME,
            wait=True,
            points=points
        )
        
        logging.info(f"✔ Successfully indexed {len(points)} chunks from link '{target_url}' to Qdrant Cloud!")
        return {
            "status": "success",
            "message": f"Successfully scraped and indexed '{title}'. Uploaded {len(points)} vector chunks to Qdrant Cloud.",
            "chunks_count": len(points)
        }

    except Exception as e:
        logging.error(f"Failed to scrape webpage: {e}")
        raise HTTPException(status_code=500, detail=f"Web scraping failed: {str(e)}")

@app.post("/feedback")
async def handle_feedback(request: FeedbackRequest):
    logging.info(f"Feedback received - Log ID: {request.query_id} | Vote: {request.vote}")
    
    if not postgres_conn_str:
        return {"status": "success", "message": "Feedback logged to system stdout (Mock)."}
        
    try:
        import psycopg2
        conn = psycopg2.connect(postgres_conn_str)
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE query_logs
            SET vote_status = %s
            WHERE id = %s;
            """,
            (request.vote, request.query_id)
        )
        conn.commit()
        cur.close()
        conn.close()
        return {"status": "success", "message": "Feedback recorded."}
    except Exception as e:
        logging.error(f"Feedback logging failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to log feedback to database.")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "gemini_connected": gemini_model is not None,
        "qdrant_connected": qdrant_client is not None,
        "redis_connected": redis_client is not None
    }
