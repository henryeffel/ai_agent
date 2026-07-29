from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentChunkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1, max_length=100)
    document_id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=300)
    content: str = Field(min_length=10, max_length=20_000)
    category: str = Field(default="reference", min_length=1, max_length=50)
    chunk_index: int = Field(ge=0)
    source_url: str | None = Field(default=None, max_length=2000)
    created_at: datetime | None = None


class ChunkIndexRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunks: list[DocumentChunkInput] = Field(min_length=1, max_length=100)


class ChunkIndexResponse(BaseModel):
    indexed_count: int = Field(ge=0)
    provider: str


class KnowledgeSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=2, max_length=1000)
    category: str | None = Field(default=None, max_length=50)
    top_k: int = Field(default=3, ge=1, le=20)
    min_score: float = Field(default=0.2, ge=-1.0, le=1.0)


class KnowledgeSearchHit(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    content: str
    category: str
    chunk_index: int
    source_url: str | None
    score: float


class KnowledgeSearchResponse(BaseModel):
    provider: str
    grounded: bool
    hits: list[KnowledgeSearchHit]
