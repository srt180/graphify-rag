from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentRepository:
    def __init__(self, settings: Settings) -> None:
        self.db_path = settings.sqlite_path

    def init(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT,
                    file_path TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error TEXT,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_history (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    sources_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_document(self, doc_id: str, filename: str, content_type: str | None, file_path: Path) -> dict:
        now = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (
                    id, filename, content_type, file_path, status, error,
                    chunk_count, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, filename, content_type, str(file_path), "processing", None, 0, now, now),
            )
            conn.commit()
        return self.get_document(doc_id)

    def list_documents(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, filename, content_type, status, error, chunk_count, created_at, updated_at
                FROM documents
                ORDER BY created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def get_document(self, doc_id: str) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, filename, content_type, file_path, status, error,
                       chunk_count, created_at, updated_at
                FROM documents
                WHERE id = ?
                """,
                (doc_id,),
            ).fetchone()
        return dict(row) if row else None

    def mark_completed(self, doc_id: str, chunk_count: int) -> dict | None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = ?, error = NULL, chunk_count = ?, updated_at = ?
                WHERE id = ?
                """,
                ("ready", chunk_count, utc_now(), doc_id),
            )
            conn.commit()
        return self.get_document(doc_id)

    def mark_failed(self, doc_id: str, error: str) -> dict | None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE documents
                SET status = ?, error = ?, updated_at = ?
                WHERE id = ?
                """,
                ("failed", error[:2000], utc_now(), doc_id),
            )
            conn.commit()
        return self.get_document(doc_id)

    def delete_document(self, doc_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
            conn.commit()

    def create_chat_history(self, history_id: str, question: str, answer: str, sources: list[dict]) -> dict:
        created_at = utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO chat_history (id, question, answer, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (history_id, question, answer, json.dumps(sources, ensure_ascii=False), created_at),
            )
            conn.commit()
        return {
            "id": history_id,
            "question": question,
            "answer": answer,
            "sources": sources,
            "created_at": created_at,
        }

    def list_chat_history(self, limit: int = 50) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, question, answer, sources_json, created_at
                FROM chat_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        items: list[dict] = []
        for row in rows:
            item = dict(row)
            try:
                item["sources"] = json.loads(item.pop("sources_json") or "[]")
            except json.JSONDecodeError:
                item["sources"] = []
            items.append(item)
        return items

    def delete_chat_history(self, history_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM chat_history WHERE id = ?", (history_id,))
            conn.commit()
