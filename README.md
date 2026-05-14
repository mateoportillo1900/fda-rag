# 💊 FDA Drug Label Assistant

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?logo=streamlit&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-Agent-purple)
![pgvector](https://img.shields.io/badge/pgvector-Neon-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

> Ask plain-English questions about FDA-approved drug labels and get cited, grounded answers — no hallucination.

**[🚀 Live Demo →](https://fda-rag-gmlp6hufrw3trprm8h2srz.streamlit.app)** · **[📚 Documentation →](./docs/README.md)**

---

## What this does

FDA drug labels contain the official, government-approved information about every prescription drug — what it treats, how to dose it, what it interacts with, what the warnings are. This information is public but buried in dense XML documents that are hard to search.

This project lets you ask questions like:

- *"What are the contraindications for warfarin?"*
- *"What drug interactions does atorvastatin have?"*
- *"What is the recommended dosage for amoxicillin?"*
- *"Compare metformin and semaglutide interactions"*

...and get back a specific, cited answer drawn directly from the official FDA label text.

---

## How it works

```
Your question
     │
     ▼
Embed question as a vector (Voyage AI)
     │
     ▼
Search 1,000+ label passages for the most similar ones (Neon + pgvector)
     │
     ▼
Rerank top results by relevance (Voyage AI reranker)
     │
     ▼
Feed best passages to an LLM with instructions to cite sources (Groq / Llama 3.3)
     │
     ▼
Answer + citations displayed in browser (Streamlit)
```

This pattern — retrieve relevant context, then generate an answer — is called **RAG (Retrieval-Augmented Generation)**. It prevents the AI from making things up because it can only answer from the passages it was given.

---

## Tech stack

| What | Tool | Why |
|------|------|-----|
| Data source | [DailyMed](https://dailymed.nlm.nih.gov) SPL XML | Official FDA drug labels |
| Database | [Neon](https://neon.tech) (Postgres + pgvector) | Stores text + vector embeddings in the cloud |
| Embeddings | [Voyage AI](https://voyageai.com) `voyage-3` | Converts text to vectors for semantic search |
| Reranker | Voyage AI `rerank-2` | Re-scores search results by true relevance |
| Agent | [LangGraph](https://langchain-ai.github.io/langgraph/) | Orchestrates the retrieve → generate pipeline |
| LLM | [Groq](https://groq.com) `llama-3.3-70b-versatile` | Generates cited answers from retrieved passages |
| API | [FastAPI](https://fastapi.tiangolo.com) | HTTP interface wrapping the agent |
| UI | [Streamlit](https://streamlit.io) | Chat interface in the browser |

---

## Project structure

```
fda-rag/
│
├── src/fda_rag/
│   ├── ingestion/      # Parses FDA XML → chunks text → embeds → stores in DB
│   ├── retrieval/      # Searches DB for relevant passages + reranks results
│   ├── agent/          # LangGraph workflow: retrieve → generate
│   ├── api/            # FastAPI endpoints (POST /query, GET /health)
│   └── ui/             # Streamlit chat interface
│
├── scripts/
│   ├── download_dailymed.py   # Downloads drug label XML from FDA
│   ├── migrate.py             # Creates the database table (run once)
│   └── run_ingestion.py       # Loads all XML files into the database
│
├── tests/                     # Automated tests for each layer
├── data/sample/xml/           # 10 sample drug labels (committed)
├── .env.example               # Template — copy to .env and fill in keys
└── requirements.txt           # Python dependencies
```

---

## Running it yourself

### What you need (all free)

| Service | Sign up at | What for |
|---------|-----------|---------|
| [Neon](https://neon.tech) | neon.tech | Cloud Postgres database |
| [Voyage AI](https://voyageai.com) | dash.voyageai.com | Embeddings + reranker |
| [Groq](https://console.groq.com) | console.groq.com | LLM API (Llama 3.3, free) |

### Setup

**1. Install dependencies**
```bash
pip install -r requirements.txt
```

**2. Copy the environment template and fill in your keys**
```bash
cp .env.example .env
# Open .env and add your DATABASE_URL, VOYAGE_API_KEY, GROQ_API_KEY
```

**3. Set up the database (run once)**
```bash
python scripts/migrate.py
```

**4. Load the drug label data**
```bash
python scripts/run_ingestion.py
```

**5. Run the app**
```bash
streamlit run src/fda_rag/ui/app.py
```

Open **http://localhost:8501** in your browser.

---

## Data

10 drug labels are included in `data/sample/xml/`:

| Drug | Common use |
|------|-----------|
| Metformin | Type 2 diabetes |
| Warfarin | Blood thinner / anticoagulant |
| Atorvastatin | High cholesterol |
| Sertraline | Depression / anxiety |
| Semaglutide | Type 2 diabetes / weight loss |
| Adalimumab | Rheumatoid arthritis / autoimmune |
| Amoxicillin | Bacterial infections |
| Prednisone | Inflammation / autoimmune |
| Naloxone | Opioid overdose reversal |
| Pembrolizumab | Cancer immunotherapy |

All data is sourced from [DailyMed](https://dailymed.nlm.nih.gov), the official FDA drug label database maintained by the National Library of Medicine.

---

## Disclaimer

This tool is for educational and informational purposes only. It is not a substitute for professional medical advice. Always consult a qualified healthcare provider before making any medical decisions.
