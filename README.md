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

