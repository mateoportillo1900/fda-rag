# FDA Drug Label Assistant — Documentation

Visual, end-to-end documentation for the FDA RAG project. Every page renders natively on GitHub — the Mermaid diagrams below show up directly in the browser, no extra tools required.

> **Tip:** If you're new here, read the pages in order. Each builds on the one before it.

---

## Contents

| # | Page | What's inside |
|---|---|---|
| 1 | [Architecture overview](./01-architecture.md) | The big picture — what RAG is, how the 5 services connect, the two phases (offline & online) |
| 2 | [Query flow (online path)](./02-query-flow.md) | Step-by-step trace of what happens when a user asks a question — sequence diagram + LangGraph state graph |
| 3 | [Ingestion pipeline (offline path)](./03-ingestion.md) | How FDA XML files become searchable vectors — parsing, chunking, embedding, storing |
| 4 | [Database & pgvector search](./04-database.md) | Schema, HNSW index, how cosine similarity finds the right passages |
| 5 | [Code walkthrough](./05-code-walkthrough.md) | File-by-file map of the codebase — which module does what, dependency graph |

---

## At a glance

```mermaid
flowchart LR
    User([👤 User]) -->|asks question| UI[Streamlit UI]
    UI --> Agent[LangGraph Agent]
    Agent -->|embed| Voyage[Voyage AI]
    Agent -->|search| Neon[(Neon + pgvector)]
    Agent -->|rerank| Voyage
    Agent -->|generate| Groq[Groq Llama 3.3 70B]
    Groq -->|cited answer| UI
    UI -->|response| User

    style User fill:#0d2626,stroke:#0d9488,color:#5eead4
    style UI fill:#0d2626,stroke:#0d9488,color:#5eead4
    style Agent fill:#1c1500,stroke:#d97706,color:#fcd34d
    style Voyage fill:#172554,stroke:#2563eb,color:#93c5fd
    style Neon fill:#052e16,stroke:#16a34a,color:#86efac
    style Groq fill:#2e1065,stroke:#7c3aed,color:#c4b5fd
```

---

## Project links

- **Live demo:** https://fda-rag-gmlp6hufrw3trprm8h2srz.streamlit.app
- **GitHub repo:** https://github.com/mateoportillo1900/fda-rag
- **Data source:** [DailyMed](https://dailymed.nlm.nih.gov) — official FDA drug label database

---

## Disclaimer

This documentation is for educational purposes. The FDA Drug Label Assistant is a portfolio project, not a substitute for professional medical advice.
