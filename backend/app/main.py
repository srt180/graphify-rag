from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.bailian import BailianClient
from app.chunking import chunk_sections
from app.config import get_settings
from app.document_loaders import SUPPORTED_EXTENSIONS, parse_document
from app.schemas import (
    BatchUploadResponse,
    ChatRequest,
    ChatResponse,
    ChatHistoryOut,
    DocumentOut,
    HealthOut,
    SourceOut,
    UploadResult,
)
from app.storage import DocumentRepository
from app.vector_store import ChunkPayload, VectorStore

settings = get_settings()
repository = DocumentRepository(settings)
vector_store = VectorStore(settings)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    repository.init()


@app.get("/health", response_model=HealthOut)
def health() -> HealthOut:
    qdrant_status = vector_store.healthcheck()
    status = "ok" if qdrant_status == "ok" else "degraded"
    return HealthOut(status=status, qdrant=qdrant_status)


@app.get("/api/documents", response_model=list[DocumentOut])
def list_documents() -> list[DocumentOut]:
    return [DocumentOut(**doc) for doc in repository.list_documents()]


@app.post("/api/documents/upload", response_model=DocumentOut)
async def upload_document(file: UploadFile = File(...)) -> DocumentOut:
    return await _save_and_index_upload(file)


@app.post("/api/documents/upload-batch", response_model=BatchUploadResponse)
async def upload_documents(files: list[UploadFile] = File(...)) -> BatchUploadResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    results: list[UploadResult] = []
    for file in files:
        filename = file.filename or "document"
        try:
            document = await _save_and_index_upload(file)
            failed = document.status == "failed"
            results.append(
                UploadResult(
                    filename=filename,
                    status="failed" if failed else "success",
                    document=document,
                    error=document.error if failed else None,
                )
            )
        except HTTPException as exc:
            results.append(
                UploadResult(
                    filename=filename,
                    status="failed",
                    error=str(exc.detail),
                )
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                UploadResult(
                    filename=filename,
                    status="failed",
                    error=str(exc),
                )
            )

    failure_count = sum(1 for result in results if result.status == "failed")
    return BatchUploadResponse(
        results=results,
        success_count=len(results) - failure_count,
        failure_count=failure_count,
    )


async def _save_and_index_upload(file: UploadFile) -> DocumentOut:
    original_name = file.filename or "document"
    ext = Path(original_name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Supported: {supported}")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB.")

    doc_id = str(uuid.uuid4())
    safe_name = _safe_filename(original_name)
    target = settings.upload_dir / f"{doc_id}_{safe_name}"
    target.write_bytes(content)

    repository.create_document(doc_id, original_name, file.content_type, target)
    try:
        completed = _index_document(doc_id=doc_id, filename=original_name, path=target)
    except Exception as exc:  # noqa: BLE001
        failed = repository.mark_failed(doc_id, str(exc))
        if failed:
            return DocumentOut(**failed)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return DocumentOut(**completed)


@app.delete("/api/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str) -> None:
    doc = repository.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    vector_store.delete_document(doc_id)
    file_path = Path(doc["file_path"])
    if file_path.exists():
        file_path.unlink()
    repository.delete_document(doc_id)


@app.get("/api/chat/history", response_model=list[ChatHistoryOut])
def list_chat_history(limit: int = 50) -> list[ChatHistoryOut]:
    bounded_limit = max(1, min(limit, 200))
    return [ChatHistoryOut(**item) for item in repository.list_chat_history(limit=bounded_limit)]


@app.delete("/api/chat/history/{history_id}", status_code=204)
def delete_chat_history(history_id: str) -> None:
    repository.delete_chat_history(history_id)


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not any(doc["status"] == "ready" for doc in repository.list_documents()):
        response = ChatResponse(
            answer="The knowledge base does not contain enough information.",
            sources=[],
        )
        return _save_chat_response(request.question, response)

    try:
        client = BailianClient(settings)
        query_vector = client.embed_texts([request.question])[0]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    hits = vector_store.query(query_vector, top_k=request.top_k)
    sources = [
        SourceOut(
            citation_id=index,
            doc_id=str(hit.get("doc_id", "")),
            filename=str(hit.get("filename", "")),
            chunk_id=str(hit.get("chunk_id", "")),
            page=hit.get("page"),
            score=hit.get("score"),
            text=str(hit.get("text", "")),
        )
        for index, hit in enumerate(hits, start=1)
        if hit.get("text")
    ]
    if not sources:
        response = ChatResponse(
            answer="The knowledge base does not contain enough information.",
            sources=[],
        )
        return _save_chat_response(request.question, response)
    try:
        answer = client.answer(request.question, sources)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return _save_chat_response(request.question, ChatResponse(answer=answer, sources=sources))


def _save_chat_response(question: str, response: ChatResponse) -> ChatResponse:
    history_id = str(uuid.uuid4())
    repository.create_chat_history(
        history_id=history_id,
        question=question,
        answer=response.answer,
        sources=[source.model_dump() for source in response.sources],
    )
    response.history_id = history_id
    return response


def _index_document(doc_id: str, filename: str, path: Path) -> dict:
    sections = parse_document(path)
    chunks = chunk_sections(sections, chunk_size=settings.chunk_size, overlap=settings.chunk_overlap)
    if not chunks:
        raise ValueError("No readable text was extracted from this document.")

    payloads = [
        ChunkPayload(
            doc_id=doc_id,
            filename=filename,
            chunk_id=f"{doc_id}:{index}",
            chunk_index=index,
            text=chunk.text,
            page=chunk.page,
            section_label=chunk.section_label,
        )
        for index, chunk in enumerate(chunks)
    ]
    client = BailianClient(settings)
    vectors = client.embed_texts([payload.text for payload in payloads])
    vector_store.upsert_chunks(vectors, payloads)
    completed = repository.mark_completed(doc_id, len(payloads))
    if not completed:
        raise RuntimeError("Document disappeared while indexing.")
    return completed


def _safe_filename(filename: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename).strip("._")
    return cleaned or "document"
