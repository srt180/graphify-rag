from __future__ import annotations

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: str
    filename: str
    content_type: str | None = None
    status: str
    error: str | None = None
    chunk_count: int = 0
    created_at: str
    updated_at: str


class UploadResult(BaseModel):
    filename: str
    status: str
    document: DocumentOut | None = None
    error: str | None = None


class BatchUploadResponse(BaseModel):
    results: list[UploadResult]
    success_count: int
    failure_count: int


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    top_k: int = Field(default=6, ge=1, le=20)


class SourceOut(BaseModel):
    citation_id: int
    doc_id: str
    filename: str
    chunk_id: str
    page: int | None = None
    score: float | None = None
    text: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceOut]
    history_id: str | None = None


class ChatHistoryOut(BaseModel):
    id: str
    question: str
    answer: str
    sources: list[SourceOut]
    created_at: str


class HealthOut(BaseModel):
    status: str
    qdrant: str
