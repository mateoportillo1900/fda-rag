from pydantic import BaseModel, Field

from fda_rag.retrieval.retriever import RetrievedChunk


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class ChunkResult(BaseModel):
    drug_name: str
    section_name: str
    chunk_text: str
    score: float

    @classmethod
    def from_retrieved(cls, chunk: RetrievedChunk) -> "ChunkResult":
        return cls(
            drug_name=chunk.drug_name,
            section_name=chunk.section_name,
            chunk_text=chunk.chunk_text,
            score=round(chunk.score, 4),
        )


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[ChunkResult]
