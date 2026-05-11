"""LangGraph node functions: retrieve and generate."""

from __future__ import annotations

import os

import psycopg
from groq import Groq
from langchain_core.runnables import RunnableConfig

from fda_rag.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from fda_rag.agent.state import AgentState
from fda_rag.retrieval.reranker import rerank
from fda_rag.retrieval.retriever import retrieve

GROQ_MODEL = "llama-3.3-70b-versatile"
RETRIEVAL_TOP_K = 20   # candidates fetched from vector DB
RERANK_TOP_N = 5       # chunks passed to the LLM after reranking


def retrieve_node(state: AgentState, config: RunnableConfig) -> dict:
    """Embed the question, search Neon, rerank, return top chunks."""
    db_url = (config.get("configurable") or {}).get(
        "db_url", os.environ["DATABASE_URL"]
    )
    with psycopg.connect(db_url) as conn:
        candidates = retrieve(state["question"], conn, top_k=RETRIEVAL_TOP_K)

    chunks = rerank(state["question"], candidates, top_n=RERANK_TOP_N)
    return {"chunks": chunks}


def generate_node(state: AgentState) -> dict:
    """Generate an answer from retrieved chunks.

    Uses Groq if GROQ_API_KEY is set and functional, otherwise returns
    a structured plain-text summary of the retrieved chunks for development.
    """
    chunks = state["chunks"]
    question = state["question"]

    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            client = Groq(api_key=groq_key)
            user_prompt = build_user_prompt(question, chunks)
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return {"answer": response.choices[0].message.content}
        except Exception as e:
            return {"answer": f"⚠️ Groq error ({GROQ_MODEL}): {e}\n\nFalling back to raw retrieved chunks:\n\n" + _format_chunks(chunks, question)}

    # No API key configured — return raw chunks
    return {"answer": _format_chunks(chunks, question)}


def _format_chunks(chunks: list, question: str) -> str:
    if not chunks:
        return "No relevant drug label excerpts found for your question."
    lines = [f"Retrieved {len(chunks)} chunk(s) relevant to: {question!r}\n"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"[{i}] {chunk.drug_name} — {chunk.section_name}")
        lines.append(chunk.chunk_text[:300] + ("..." if len(chunk.chunk_text) > 300 else ""))
        lines.append("")
    return "\n".join(lines)
