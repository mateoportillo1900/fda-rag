from __future__ import annotations

from typing import TypedDict

from fda_rag.retrieval.retriever import RetrievedChunk


class AgentState(TypedDict):
    question: str
    chunks: list[RetrievedChunk]
    answer: str
