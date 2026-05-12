# Graphify RAG

Graphify RAG is a standalone document knowledge-base app inspired by the useful
parts of Graphify's document extraction flow, but independent of Claude Code or
any AI editor integration.

The MVP supports PDF, Markdown, plain text, and DOCX ingestion, stores vectors
in Qdrant, and answers questions through Alibaba Cloud Model Studio / DashScope
using its OpenAI-compatible API.

## Stack

- Backend: FastAPI
- Frontend: React + Vite
- Vector store: Qdrant
- LLM provider: DashScope OpenAI-compatible chat and embedding APIs
- Metadata: SQLite
- File storage: local `data/`

## Roadmap: What Is Worth Building Next

The current MVP is a practical document RAG baseline: upload documents, chunk
them, embed them, retrieve relevant chunks from Qdrant, and answer with cited
sources. The next stage should focus on making it more reliable on real
enterprise document collections, not just adding UI polish.

### 1. Hybrid retrieval

Add keyword and sparse retrieval alongside dense vectors.

- Dense vector search handles semantic similarity.
- BM25 or sparse vectors handle exact terms such as model numbers, clauses,
  error codes, parameter names, and product IDs.
- A fused retrieval layer can combine both results before generation.

This is important for manuals, contracts, technical specifications, SOPs, and
Chinese enterprise documents where exact identifiers matter.

### 2. Reranking

Add a rerank step after initial retrieval.

- Retrieve a wider candidate set from Qdrant.
- Use a rerank model to sort chunks by question relevance.
- Send only the strongest evidence into the answer prompt.

This should reduce hallucination and improve citation quality, especially when
many documents contain similar wording.

### 3. Graphify-style structure extraction

The project is inspired by Graphify, but it currently does not depend on
Graphify or build a graph. The most valuable next step is to add an optional
structure layer:

- Extract entities, concepts, document sections, product models, parameters,
  procedures, and cross-document references.
- Store relationships such as `mentions`, `defines`, `depends_on`,
  `supersedes`, `troubleshoots`, and `related_to`.
- Use the graph to expand retrieval beyond top-k chunks.

This would move the project from ordinary vector RAG toward a hybrid
Vector RAG + Graph RAG knowledge base.

### 4. Better ingestion pipeline

Move indexing out of the request/response path.

- Use background jobs for parsing, embedding, and Qdrant writes.
- Track document status per stage: uploaded, parsing, chunking, embedding,
  indexed, failed.
- Support retry, cancellation, and re-indexing.
- Add duplicate detection and incremental updates.

This is necessary before indexing large folders or many 200 MB documents.

### 5. Document quality and citation improvements

Improve how documents are parsed and cited.

- Preserve PDF page numbers, headings, tables, and section hierarchy.
- Add table-aware chunking for manuals and specifications.
- Show citations with document name, page, and nearby heading.
- Add source preview and jump-to-page support.

The goal is not only to answer, but to make every answer auditable.

### 6. Knowledge-base product features

Add the features expected from a real knowledge-base app:

- Multiple knowledge bases or collections.
- Tags and metadata filters.
- Per-document delete/re-index controls.
- Chat history search.
- Exportable answers and citations.
- Basic user/auth support for team usage.

### 7. Evaluation and observability

Add a small evaluation loop before the system grows too complex.

- Save test questions with expected source documents.
- Track retrieval hit rate and answer citation quality.
- Log embedding cost, latency, chunk counts, and model usage.
- Add regression tests for retrieval behavior.

This keeps future GraphRAG, rerank, and hybrid-search changes measurable.

## Quick Start

1. Create your environment file:

```bash
cp .env.example .env
```

2. Set `DASHSCOPE_API_KEY` in `.env`.

3. Start the app:

```bash
docker compose up --build
```

4. Open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Qdrant: http://localhost:6333/dashboard

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

For local backend development, keep Qdrant running:

```bash
docker compose up qdrant
```

## Configuration

Important variables:

- `DASHSCOPE_API_KEY`: Alibaba Cloud Model Studio API key.
- `DASHSCOPE_BASE_URL`: OpenAI-compatible endpoint. Default is Beijing region.
- `CHAT_MODEL`: default `qwen-plus`.
- `EMBEDDING_MODEL`: default `text-embedding-v4`.
- `EMBEDDING_DIMENSIONS`: default `1024`.
- `QDRANT_URL`: Qdrant HTTP URL.
- `QDRANT_COLLECTION`: collection name for document chunks.
- `CHUNK_SIZE` and `CHUNK_OVERLAP`: character-based chunk controls.

DashScope official references:

- OpenAI-compatible chat: https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api
- OpenAI-compatible embeddings: https://help.aliyun.com/zh/model-studio/embedding-interfaces-compatible-with-openai
- Embedding model guidance: https://help.aliyun.com/zh/model-studio/embedding-rerank-model/

Qdrant references:

- Installation: https://qdrant.tech/documentation/installation/
- Hybrid queries roadmap target: https://qdrant.tech/documentation/concepts/hybrid-queries/
