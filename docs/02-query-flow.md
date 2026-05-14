# 2. Query Flow — The Online Path

What happens between the moment a user clicks "Send" and the moment a cited answer appears in their browser. Read this if you want to understand the runtime behaviour of the app.

---

## The 60-second version

```mermaid
flowchart LR
    Q[Question] --> E[Embed]
    E --> S[Search]
    S --> R[Rerank]
    R --> G[Generate]
    G --> A[Answer]

    style Q fill:#0d2626,stroke:#0d9488,color:#5eead4
    style E fill:#172554,stroke:#2563eb,color:#93c5fd
    style S fill:#052e16,stroke:#16a34a,color:#86efac
    style R fill:#172554,stroke:#2563eb,color:#93c5fd
    style G fill:#2e1065,stroke:#7c3aed,color:#c4b5fd
    style A fill:#0d2626,stroke:#0d9488,color:#5eead4
```

| Step | Service | What happens | Typical time |
|---|---|---|---|
| 1. Embed | Voyage AI `voyage-3` | Question text → 1024-dim float vector | ~200 ms |
| 2. Search | Neon + pgvector | Find top 20 nearest vectors using HNSW index | ~50 ms |
| 3. Rerank | Voyage AI `rerank-2` | Re-score top 20 with cross-attention → top 5 | ~400 ms |
| 4. Generate | Groq Llama 3.3 70B | Read 5 chunks + question, write cited answer | ~1–2 sec |
| **Total** | | | **~2–3 sec** |

---

## Full sequence diagram

```mermaid
sequenceDiagram
    autonumber
    participant User as 👤 User
    participant UI as 🖥️ Streamlit UI<br/>(app.py)
    participant Agent as 🔗 LangGraph<br/>(graph.py)
    participant Retrieve as retrieve_node
    participant Generate as generate_node
    participant Voyage as 🚢 Voyage AI
    participant Neon as ⚡ Neon pgvector
    participant Groq as ⚙️ Groq Llama 3.3

    User->>UI: Type question + send
    UI->>Agent: invoke({question, chunks:[], answer:""})
    Agent->>Retrieve: state with question

    Retrieve->>Voyage: embed(question, model=voyage-3)
    Voyage-->>Retrieve: float[1024] vector

    Retrieve->>Neon: SELECT ... ORDER BY embedding <=> query<br/>LIMIT 20
    Neon-->>Retrieve: top 20 chunks (by cosine similarity)

    Retrieve->>Voyage: rerank(question, 20 chunks, model=rerank-2)
    Voyage-->>Retrieve: top 5 chunks (re-scored)

    Retrieve->>Agent: state.chunks = top 5
    Agent->>Generate: state with chunks

    Generate->>Groq: chat.completions.create<br/>(system + user prompt with 5 chunks)
    Groq-->>Generate: cited answer text

    Generate->>Agent: state.answer = answer
    Agent-->>UI: final state {question, chunks, answer}

    UI->>User: Render answer + source cards
```

---

## The LangGraph state graph

Internally, the agent is a tiny state machine with two nodes and one edge:

```mermaid
stateDiagram-v2
    [*] --> retrieve_node
    retrieve_node --> generate_node: state.chunks populated
    generate_node --> [*]: state.answer populated

    note right of retrieve_node
        Input:  state.question
        Output: state.chunks (list of 5)
        Calls:  Voyage embed + Neon + Voyage rerank
    end note

    note right of generate_node
        Input:  state.question, state.chunks
        Output: state.answer (cited string)
        Calls:  Groq Llama 3.3 70B
    end note
```

**Why a state graph instead of plain function calls?**

LangGraph gives us three things for free:

1. **Typed state** — every node knows exactly what fields exist (`question`, `chunks`, `answer`) and what types they are
2. **Auditable flow** — you can dump the graph as a diagram or trace every state transition
3. **Easy to extend** — want to add a "verify citations" node? Just add it as a new node between `generate_node` and the end

---

## What each node actually does

### `retrieve_node` — three calls, one job

Job: turn a question into the 5 most relevant chunks.

```python
def retrieve_node(state: AgentState) -> dict:
    # 1. Embed the question
    query_vec = voyage.embed([state["question"]], model="voyage-3", input_type="query").embeddings[0]

    # 2. Find 20 nearest chunks via pgvector cosine distance
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("""
            SELECT drug_name, section_name, chunk_text,
                   1 - (embedding <=> %s::vector) AS score
            FROM drug_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT 20
        """, (query_vec, query_vec)).fetchall()

    # 3. Rerank those 20 with Voyage's cross-encoder, keep top 5
    reranked = voyage.rerank(state["question"], [r.chunk_text for r in rows],
                             model="rerank-2", top_k=5)
    top_chunks = [rows[r.index] for r in reranked.results]

    return {"chunks": top_chunks}
```

### `generate_node` — one call, with constraints

Job: turn 5 chunks + a question into a grounded, cited answer.

```python
SYSTEM_PROMPT = """
You are a medical information assistant. Answer ONLY from the provided
drug label excerpts. Cite the drug name and section for every claim.
If the excerpts don't contain the answer, say so explicitly.
"""

def generate_node(state: AgentState) -> dict:
    user_prompt = build_user_prompt(state["question"], state["chunks"])
    response = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return {"answer": response.choices[0].message.content}
```

The system prompt is the *entire* safety mechanism. The model literally cannot hallucinate drug facts because it only ever sees the 5 chunks we hand it.

---

## A real example — traced end to end

**Question:** *"What are the contraindications for warfarin?"*

```mermaid
flowchart TB
    Q["Q: What are the contraindications<br/>for warfarin?"]

    Q --> E["voyage-3 embed<br/>→ [0.021, -0.184, 0.077, ...] (1024 dims)"]

    E --> S["pgvector cosine search<br/>SELECT ... ORDER BY embedding <=> query LIMIT 20"]

    S --> Top20["20 nearest chunks<br/>(mostly Warfarin: CONTRAINDICATIONS, WARNINGS,<br/>plus a few false positives)"]

    Top20 --> RR["rerank-2 cross-encoder<br/>scores each chunk against the question"]

    RR --> Top5["Top 5 chunks<br/>3× Warfarin CONTRAINDICATIONS<br/>1× Warfarin WARNINGS<br/>1× Warfarin DRUG INTERACTIONS"]

    Top5 --> Prompt["Build prompt:<br/>System + Question + 5 chunks"]

    Prompt --> LLM["Groq Llama 3.3 70B<br/>llama-3.3-70b-versatile"]

    LLM --> Ans["Answer with inline citations:<br/>'According to the Warfarin label,<br/>CONTRAINDICATIONS section…'"]

    style Q fill:#0d2626,stroke:#0d9488,color:#5eead4
    style E fill:#172554,stroke:#2563eb,color:#93c5fd
    style S fill:#052e16,stroke:#16a34a,color:#86efac
    style Top20 fill:#052e16,stroke:#16a34a,color:#86efac
    style RR fill:#172554,stroke:#2563eb,color:#93c5fd
    style Top5 fill:#052e16,stroke:#16a34a,color:#86efac
    style Prompt fill:#1c1500,stroke:#d97706,color:#fcd34d
    style LLM fill:#2e1065,stroke:#7c3aed,color:#c4b5fd
    style Ans fill:#0d2626,stroke:#0d9488,color:#5eead4
```

---

## Why retrieve 20 then rerank to 5?

Vector similarity is **fast** but only approximately models relevance. It's great at "these texts feel similar" and bad at "which one actually answers this question?"

```mermaid
flowchart LR
    Q[Question] --> V[Embed → 1024-dim vec]

    V --> P{Vector search}
    P -->|Fast: ~50ms<br/>Approximate relevance| Top20[Top 20<br/>recall-optimised]

    Top20 --> X{Reranker}
    X -->|Slower: ~400ms<br/>True relevance| Top5[Top 5<br/>precision-optimised]

    Top5 --> L[LLM]

    style Q fill:#0d2626,stroke:#0d9488,color:#5eead4
    style V fill:#172554,stroke:#2563eb,color:#93c5fd
    style Top20 fill:#052e16,stroke:#16a34a,color:#86efac
    style Top5 fill:#052e16,stroke:#16a34a,color:#86efac
    style L fill:#2e1065,stroke:#7c3aed,color:#c4b5fd
```

The two-stage approach gives us:
- **Recall** from the vector search (don't miss the right chunk)
- **Precision** from the reranker (don't waste LLM context on near-misses)

It's a classic information retrieval pattern and it works really well.

---

## Where this code lives

| File | What it contains |
|------|------------------|
| `src/fda_rag/ui/app.py` | Streamlit chat UI, sidebar, calls `agent.invoke()` |
| `src/fda_rag/agent/graph.py` | Builds the LangGraph `StateGraph` |
| `src/fda_rag/agent/nodes.py` | `retrieve_node` and `generate_node` implementations |
| `src/fda_rag/agent/state.py` | `AgentState` TypedDict |
| `src/fda_rag/retrieval/` | Vector search and rerank helpers |

---

**Next:** [→ Ingestion pipeline (offline path)](./03-ingestion.md)
