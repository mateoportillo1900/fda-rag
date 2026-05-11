# How This Project Works

A plain-English guide to every folder and the order things run in.
No prior knowledge of RAG, LangGraph, or pgvector assumed.

---

## The big idea in one paragraph

FDA drug labels are long, dense XML documents. The goal is to let a user ask a
natural-language question ("What are the contraindications for metformin?") and
get a precise, cited answer drawn from the actual label text — not a hallucination.
To do that, we first **ingest** all the label text into a searchable database, then
at query time we **retrieve** the most relevant passages, and finally an **agent**
(a small AI program) reads those passages and writes the answer. That three-step
pattern — ingest, retrieve, generate — is what "RAG" means.

---

## The two separate lifetimes of this system

Everything in this project runs in one of two modes:

```
┌──────────────────────────────────────────────────────────┐
│  OFFLINE  (runs once, or when new data arrives)           │
│                                                           │
│  Raw FDA files → ingestion → Neon (Postgres + pgvector)   │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│  ONLINE  (runs every time a user asks a question)         │
│                                                           │
│  User → UI → Agent → retrieval → Neon (Postgres)         │
│                    ↓                                      │
│              Groq / Llama 3.3 (LLM)                      │
│                    ↓                                      │
│               Answer → UI                                 │
└──────────────────────────────────────────────────────────┘
```

The offline path only runs when you are loading new data.
The online path runs on every user question.

---

## Folder-by-folder guide

### `src/fda_rag/` — the main Python package

Everything importable lives here. The name `fda_rag` is the Python package name;
you import from it like `from fda_rag.retrieval import ...`.

---

### `src/fda_rag/ingestion/` — OFFLINE path ✅ Built

**What it does:** Takes raw FDA files and loads them into Postgres.

**Inputs:** DailyMed SPL XML files in `data/sample/xml/` (10 drug labels)

**Steps in order:**
1. **Parse** (`parser.py`) — extracts label sections from HL7 XML using LOINC codes
   (indications, warnings, dosage, contraindications, adverse reactions, etc.)
2. **Chunk** (`chunker.py`) — splits long sections into overlapping 1500-char windows
   with 200-char overlap so context is preserved at boundaries
3. **Embed** (`loader.py`) — calls Voyage AI (`voyage-3`) to turn each chunk into
   a float[1024] vector that captures its meaning
4. **Store** (`loader.py`) — inserts both the raw text and its vector into Neon

**Output:** Rows in `drug_chunks` table:
`(id, drug_name, set_id, section_code, section_name, chunk_index, chunk_text, embedding vector(1024))`

**Analogy:** This is the librarian scanning books and building an index.
It happens before anyone asks a question.

**Run it:**
```bash
python scripts/run_ingestion.py
```

---

### `src/fda_rag/retrieval/` — ONLINE path, step 1 ✅ Built

**What it does:** Given a user's question, finds the most relevant text chunks
from the database.

**How it works:**

```
User question
     │
     └──► vector search (pgvector)     ──► top-20 by semantic similarity
               │
               └── embed the question first (Voyage AI voyage-3, input_type="query")
                   then query using cosine distance (<=>)
                         │
                         ▼
               Voyage AI reranker (rerank-2)
                         │
                         └── re-scores top-20, returns best 5
```

**Output:** An ordered list of 5 `RetrievedChunk` objects, highest relevance first.
These are the "context" that gets passed to the LLM.

**Why Neon?** Neon is a cloud-hosted Postgres 16 database with pgvector pre-installed.
No local software required — your Python code connects to it over the internet using
a standard Postgres connection string. The HNSW index on the embedding column makes
nearest-neighbour search fast even at scale.

---

### `src/fda_rag/agent/` — ONLINE path, step 2 ✅ Built

**What it does:** Orchestrates the full answer-generation process using LangGraph.

**The graph:**

```
[START]
   │
   ▼
[retrieve_node]   ← embeds question, searches Neon, reranks results
   │
   ▼
[generate_node]   ← calls Groq / Llama 3.3 with chunks + question → writes the answer
   │
   ▼
[END]
```

Each node is a Python function. State flows through the graph as a typed dict:
`{ question: str, chunks: list[RetrievedChunk], answer: str }`

**Files:**
- `state.py` — the `AgentState` TypedDict
- `prompts.py` — system prompt + context formatter (tells the LLM to cite sources)
- `nodes.py` — `retrieve_node` and `generate_node` functions
- `graph.py` — wires the nodes into a compiled LangGraph

---

### `src/fda_rag/api/` — ONLINE path, the interface layer ✅ Built

**What it does:** Exposes the agent as an HTTP API using FastAPI.

**Endpoints:**
```
GET  /health   → { "status": "ok" }

POST /query
Body:     { "question": "What are the contraindications for warfarin?" }
Response: {
  "question": "...",
  "answer": "...",
  "sources": [
    { "drug_name": "Warfarin", "section_name": "CONTRAINDICATIONS",
      "chunk_text": "...", "score": 0.87 }
  ]
}
```

**Interactive docs:** `http://127.0.0.1:8000/docs` (auto-generated by FastAPI)

---

### `src/fda_rag/ui/` — ONLINE path, the user-facing layer ✅ Built

**What it does:** A Streamlit web app — the chat interface the user actually sees.

Features:
- Dark-themed chat UI with cited answers
- Drug filter to focus on a specific drug
- Compare two drugs side-by-side
- Color-coded source cards by section type (warnings, dosage, interactions, etc.)
- Copy answer button
- Deployed on Streamlit Community Cloud (free)

---

### `src/fda_rag/eval/` — separate, runs on demand 🔜 Coming

**What it does:** Measures how good the system actually is, using **RAGAS**.

RAGAS is an evaluation framework for RAG systems. Scored metrics:
- **Faithfulness** — is the answer supported by the retrieved chunks?
- **Context precision** — are the retrieved chunks relevant?
- **Context recall** — did we retrieve all the chunks we needed?

---

### `tests/` — automated correctness checks

- `conftest.py` — loads `.env`, creates the database connection fixture
- `test_smoke.py` — connection, pgvector, vector insert + cosine query
- `test_ingestion.py` — parser and chunker tests (no API keys needed)
- `test_retrieval.py` — retriever and reranker tests (requires API keys + data in Neon)

---

### `scripts/` — one-off operations

- `download_dailymed.py` — fetches XML files from the DailyMed API
- `run_ingestion.py` — runs the full offline pipeline against an XML directory
- `migrate.py` — creates the `drug_chunks` table and HNSW index in Neon (run once)

---

### `data/` — local data store

- `data/sample/xml/` — 10 FDA drug label XML files (committed)
- `data/raw/xml/` — full set (gitignored)

**Drugs in the sample set:** metformin, warfarin, atorvastatin, sertraline,
semaglutide, adalimumab, amoxicillin, prednisone, naloxone, pembrolizumab

---

## End-to-end sequence diagram

### Offline ingestion (run once per data load)

```
scripts/run_ingestion.py
         │  reads XML files from
         ▼
    data/sample/xml/
         │
         ▼
fda_rag.ingestion
  ├── parse XML    →  extract sections by LOINC code
  ├── chunk text   →  1500-char windows, 200-char overlap
  ├── embed        →  Voyage AI voyage-3 → float[1024]
  └── store        →  INSERT INTO drug_chunks (text, embedding)
         │
         ▼
    Neon (Postgres 16 + pgvector)
    HNSW index on embedding column
```

### Online query (runs on every user question)

```
User (browser)
      │  types question
      ▼
Streamlit (ui/)
      │  calls agent directly
      ▼
LangGraph agent (agent/)
      │
      ├─► [retrieve_node]
      │       embed question → Voyage AI voyage-3
      │       SELECT … ORDER BY embedding <=> query_vec LIMIT 20
      │       rerank top-20 → Voyage AI rerank-2 → top 5 chunks
      │
      ├─► [generate_node]
      │       system prompt + 5 chunks + question → Groq Llama 3.3 → answer
      │
      └─► returns { answer, chunks }
      │
      ▼
Streamlit renders answer + color-coded citations
```

---

## Where env vars are used

| Variable | Used by |
|---|---|
| `DATABASE_URL` | `ingestion/`, `retrieval/`, `tests/` — Neon connection string |
| `VOYAGE_API_KEY` | `ingestion/` (embed chunks) + `retrieval/` (embed query + rerank) |
| `GROQ_API_KEY` | `agent/` generate node — calling Groq / Llama 3.3 |
| `LANGSMITH_API_KEY` | LangSmith SDK — traces agent calls (optional) |
| `LANGSMITH_PROJECT` | Groups all traces under one project name |
| `LANGCHAIN_TRACING_V2` | Set to `true` to turn tracing on; `false` to run silently |

---

## Dependency map (what imports what)

```
ui/
 └── imports agent/ directly

agent/
 ├── imports retrieval/
 └── calls Groq API (external)

retrieval/
 ├── calls Voyage AI API (external)
 └── queries Neon (Postgres) via psycopg

ingestion/
 ├── calls Voyage AI API (external)
 └── writes to Neon (Postgres) via psycopg
```

No circular imports. Data flows one way: inward toward the database on ingestion,
outward toward the user on query.
