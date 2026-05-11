"""FastAPI application — wraps the LangGraph agent in an HTTP API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pathlib import Path

load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")

from fda_rag.agent.graph import build_graph
from fda_rag.api.models import ChunkResult, QueryRequest, QueryResponse

_agent = build_graph()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    app.state.db_url = url
    yield


app = FastAPI(
    title="FDA Drug Label RAG API",
    description="Ask questions about FDA-approved drug labels. Answers are grounded in official DailyMed data.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        result = _agent.invoke(
            {"question": request.question, "chunks": [], "answer": ""},
            config={"configurable": {"db_url": app.state.db_url}},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    sources = [ChunkResult.from_retrieved(c) for c in result["chunks"]]
    return QueryResponse(
        question=request.question,
        answer=result["answer"],
        sources=sources,
    )
