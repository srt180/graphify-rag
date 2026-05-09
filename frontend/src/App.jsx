import React, { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  AlertCircle,
  CheckCircle2,
  Database,
  FileText,
  History,
  Loader2,
  Send,
  Trash2,
  Upload,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(false);
  const [chatBusy, setChatBusy] = useState(false);
  const [error, setError] = useState("");

  const readyCount = useMemo(
    () => documents.filter((doc) => doc.status === "ready").length,
    [documents]
  );

  useEffect(() => {
    refreshDocuments();
    refreshHistory();
  }, []);

  async function refreshDocuments() {
    const response = await fetch(`${API_BASE}/api/documents`);
    if (!response.ok) {
      setError("Failed to load documents.");
      return;
    }
    setDocuments(await response.json());
  }

  async function refreshHistory() {
    const response = await fetch(`${API_BASE}/api/chat/history?limit=40`);
    if (!response.ok) {
      return;
    }
    setHistory(await response.json());
  }

  async function uploadDocument(event) {
    event.preventDefault();
    if (selectedFiles.length === 0) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    selectedFiles.forEach((file) => form.append("files", file));
    try {
      const response = await fetch(`${API_BASE}/api/documents/upload-batch`, {
        method: "POST",
        body: form,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Upload failed.");
      }
      if (payload.failure_count > 0) {
        const failedNames = (payload.results || [])
          .filter((result) => result.status === "failed")
          .map((result) => `${result.filename}: ${result.error || "failed"}`)
          .join("; ");
        setError(`${payload.failure_count} file(s) failed. ${failedNames}`);
      }
      setSelectedFiles([]);
      event.target.reset();
      await refreshDocuments();
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteDocument(docId) {
    setError("");
    const response = await fetch(`${API_BASE}/api/documents/${docId}`, {
      method: "DELETE",
    });
    if (!response.ok) {
      setError("Delete failed.");
      return;
    }
    await refreshDocuments();
  }

  async function askQuestion(event) {
    event.preventDefault();
    if (!question.trim()) return;
    setChatBusy(true);
    setError("");
    setAnswer("");
    setSources([]);
    try {
      const response = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: 6 }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Question failed.");
      }
      setAnswer(payload.answer);
      setSources(payload.sources || []);
      await refreshHistory();
    } catch (chatError) {
      setError(chatError.message);
    } finally {
      setChatBusy(false);
    }
  }

  function openHistoryItem(item) {
    setQuestion(item.question);
    setAnswer(item.answer);
    setSources(item.sources || []);
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Database size={24} />
          <div>
            <h1>Graphify RAG</h1>
            <p>{readyCount} ready / {documents.length} total</p>
          </div>
        </div>

        <form className="upload-box" onSubmit={uploadDocument}>
          <label className="file-picker">
            <Upload size={18} />
            <span>{formatSelectedFiles(selectedFiles)}</span>
            <input
              type="file"
              accept=".pdf,.md,.markdown,.txt,.docx"
              multiple
              onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))}
            />
          </label>
          <button className="primary-button" disabled={selectedFiles.length === 0 || busy}>
            {busy ? <Loader2 className="spin" size={18} /> : <Upload size={18} />}
            <span>{selectedFiles.length > 1 ? `Index ${selectedFiles.length}` : "Index"}</span>
          </button>
        </form>

        {error && (
          <div className="error-box">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <section className="document-list">
          {documents.map((doc) => (
            <article className="document-row" key={doc.id}>
              <FileText size={18} />
              <div className="document-meta">
                <strong>{doc.filename}</strong>
                <span>{doc.chunk_count} chunks</span>
              </div>
              <StatusBadge status={doc.status} />
              <button
                className="icon-button"
                aria-label={`Delete ${doc.filename}`}
                title="Delete"
                onClick={() => deleteDocument(doc.id)}
              >
                <Trash2 size={17} />
              </button>
            </article>
          ))}
          {documents.length === 0 && <p className="empty-state">No documents indexed.</p>}
        </section>

        <section className="history-list">
          <div className="section-heading">
            <History size={17} />
            <h2>History</h2>
          </div>
          {history.map((item) => (
            <button className="history-item" key={item.id} onClick={() => openHistoryItem(item)}>
              <strong>{item.question}</strong>
              <span>{formatDate(item.created_at)}</span>
            </button>
          ))}
          {history.length === 0 && <p className="empty-state">No question history.</p>}
        </section>
      </aside>

      <section className="workspace">
        <form className="question-bar" onSubmit={askQuestion}>
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask the knowledge base"
          />
          <button className="send-button" disabled={!question.trim() || chatBusy}>
            {chatBusy ? <Loader2 className="spin" size={20} /> : <Send size={20} />}
          </button>
        </form>

        <section className="answer-panel">
          {answer ? (
            <div className="answer-text markdown-body">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
            </div>
          ) : (
            <div className="answer-placeholder">
              <Database size={28} />
              <span>Upload documents, then ask a question.</span>
            </div>
          )}
        </section>

        {sources.length > 0 && (
          <section className="source-list">
            <h2>Sources</h2>
            {sources.map((source) => (
              <article className="source-item" key={source.chunk_id}>
                <div className="source-heading">
                  <span>[{source.citation_id}] {source.filename}</span>
                  {source.page && <small>page {source.page}</small>}
                </div>
                <p>{source.text}</p>
              </article>
            ))}
          </section>
        )}
      </section>
    </main>
  );
}

function formatSelectedFiles(files) {
  if (files.length === 0) return "Choose documents";
  if (files.length === 1) return files[0].name;
  return `${files.length} documents selected`;
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function StatusBadge({ status }) {
  if (status === "ready") {
    return (
      <span className="status ready">
        <CheckCircle2 size={15} />
        ready
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="status failed">
        <AlertCircle size={15} />
        failed
      </span>
    );
  }
  return (
    <span className="status processing">
      <Loader2 className="spin" size={15} />
      processing
    </span>
  );
}
