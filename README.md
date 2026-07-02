# KGP Insight 🎓

> **Empirical Campus RAG & Analytics Engine for IIT Kharagpur**

KGP Insight is a retrieval-augmented generation (RAG) system built to answer natural language questions about IIT Kharagpur academics, curriculum regulations, HMC hostel allotments, administrative calendars, and societies. 

Instead of browsing dozens of unorganized portal pages, students can ask queries like *"How do hostel allotments work?"* or *"What is the CGPA eligibility to minor in AI?"* and receive context-supported answers anchored to verified campus documents.

[🚀 Visit Live Demo (Deployment Pending)]()

---

## 🛠️ Key Engineering Highlights

* **Dense-Sparse Hybrid Retrieval:** Integrates dense semantic vector search via Qdrant Cloud (`gemini-embedding-001`) alongside sparse lexical keyword matching (BM25) fused using **Reciprocal Rank Fusion (RRF)**.
* **Semantic Caching:** Employs **Upstash Redis** to cache semantically equivalent queries, bypassing the LLM generation loop and reducing search latency from **1.8s to <15ms (120x speedup)**.
* **$0 Dynamic Knowledge Ingestion:** Supports local user PDF uploads and pasted link references:
  * **PDFs:** Parsed sub-second using **PyMuPDF (fitz)**, fitting easily within free-tier server limits (512MB RAM).
  * **URLs:** Parsed using **BeautifulSoup** with an **automatic Playwright headless browser fallback** to capture JavaScript-rendered Single-Page Applications (SPAs).
* **Asynchronous Telemetry:** Tracks user thumbs up/down feedback and query token count latency using **Neon PostgreSQL** in background async threads.
* **Premium Client SPA:** Refactored React application using **Poppins** typography, dark-accented glassmorphism, responsive sidebar toggle states, and citation mapping indicators.

---

## 📈 Empirical RAG Performance Metrics

These benchmarks are calculated against our live Qdrant Cloud and Gemini API endpoints using our custom LLM-as-a-judge test suite (`tests/eval_rag.py`) over 15 ground-truth student queries:

| Metric | Score | Industry Standard | RAG Pipeline Validation |
| :--- | :---: | :---: | :--- |
| **Context Precision** | **80.0%** | >75% | Validates Dense-Sparse hybrid index and keyword re-ranking. |
| **Faithfulness** | **90.0%** | >90% | Confirms LLM is properly anchored to retrieved contexts (no hallucinations). |
| **Answer Relevance** | **90.0%** | >85% | Assesses query-alignment and semantic clarity. |
| **Average Latency** | **1735.8ms** | <2.0s | Measured query-to-response generation time (Cold). |

---

## 📁 Repository Directory Map

```bash
├── backend/
│   └── main.py              # FastAPI server hosting query, upload-pdf, scrape-link, & feedback endpoints
├── data/
│   ├── parsed_pdf_data.jsonl # Layout-aware text segments from HMC/Academic PDF regulations
│   └── evaluation_metrics.md # Output report of the RAG test metrics
├── frontend/
│   ├── src/
│   │   ├── assets/          # SVG logo variants (mainLogo & smallLogo)
│   │   ├── components/      # Modular Sidebar, ChatFeed, ChatInput, & MessageBubble
│   │   ├── App.jsx          # React state and stream controller
│   │   ├── App.css          # Glassmorphism and sidebar toggle styles
│   │   └── index.css        # Light theme variables and Poppins imports
│   └── index.html
├── scraper/
│   ├── index_data.py        # Token sliding chunker and Qdrant database indexer
│   ├── static_crawler.py    # Scrapy recursive web crawler
│   ├── erp_scraper.py       # Headless Playwright script logging into ERP gateways
│   └── pdf_parser.py        # pdfplumber script preserving table structures
├── tests/
│   ├── eval_rag.py          # Custom LLM-as-a-judge evaluation harness
│   └── locustfile.py        # Locust performance load testing script
├── .env_example             # Environment credentials template
├── requirements.txt         # Server and RAG python dependencies
└── chat.md                  # Complete chronological pair-programming conversation log
```

---

## 🚀 Getting Started

### 1. Prerequisites & Environment Setup
Clone the repository and set up a Python 3.14 virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Set up the frontend packages:
```bash
cd frontend
npm install
```

### 2. Configure Environment Variables
Copy `.env_example` to `.env` and fill in your API credentials:
```bash
cp .env_example .env
```
Fill in your `GEMINI_API_KEY`, `QDRANT_URL`, `QDRANT_API_KEY`, `UPSTASH_REDIS_URL`, and `NEON_DATABASE_URL`.

### 3. Initialize & Index Qdrant Cloud
Generate vector embeddings and upload your campus knowledge base to Qdrant:
```bash
python scraper/index_data.py
```

### 4. Running the Application
Start the **FastAPI Backend Server** (listens on `http://127.0.0.1:8000`):
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Start the **Vite React Frontend** (serves on `http://127.0.0.1:5173`):
```bash
cd frontend
npm run dev
```

---

## 🧪 Running Evaluations & Load Tests

### RAG Quality Metrics:
Run the evaluation test harness to calculate context precision and faithfulness:
```bash
python tests/eval_rag.py
```

### Locust Load Testing:
1. Install Locust:
   ```bash
   pip install locust
   ```
2. Launch the Locust tester:
   ```bash
   locust -f tests/locustfile.py
   ```
3. Open `http://localhost:8089` in your browser to run concurrent load simulation tests.
