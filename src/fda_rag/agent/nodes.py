"""LangGraph node functions: retrieve and generate."""

from __future__ import annotations

import os

import psycopg
from google import genai
from google.genai import types
from langchain_core.runnables import RunnableConfig

from fda_rag.agent.prompts import SYSTEM_PROMPT, build_user_prompt
from fda_rag.agent.state import AgentState
from fda_rag.retrieval.reranker import rerank
from fda_rag.retrieval.retriever import retrieve

GEMINI_MODEL = "gemini-1.5-flash"
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

    Uses Gemini if GEMINI_API_KEY is set and functional, otherwise returns
    a structured plain-text summary of the retrieved chunks for development.
    """
    chunks = state["chunks"]
    question = state["question"]

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    if gemini_key and not gemini_key.startswith("AIza..."):
        try:
            client = genai.Client(api_key=gemini_key)
            user_prompt = build_user_prompt(question, chunks)
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                contents=user_prompt,
            )
            return {"answer": response.text}
        except Exception:
            pass  # fall through to stub

    # Development stub — returns retrieved chunks as structured text
    if not chunks:
        return {"answer": "No relevant drug label excerpts found for your question."}

    lines = [f"Retrieved {len(chunks)} chunk(s) relevant to: {question!r}\n"]
    for i, chunk in enumerate(chunks, 1):
        lines.append(f"[{i}] {chunk.drug_name} — {chunk.section_name}")
        lines.append(chunk.chunk_text[:300] + ("..." if len(chunk.chunk_text) > 300 else ""))
        lines.append("")
    return {"answer": "\n".join(lines)}
