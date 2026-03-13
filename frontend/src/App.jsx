import React, { useState, useEffect, useRef, useCallback } from "react";
import { BookOpen } from "lucide-react";

import FileUpload from "./components/FileUpload";
import DocumentList from "./components/DocumentList";
import ChatMessage from "./components/ChatMessage";
import QueryBar from "./components/QueryBar";
import ToastContainer from "./components/ToastContainer";
import { useToast } from "./hooks/useToast";
import {
  listDocuments,
  deleteDocument,
  queryDocuments,
  healthCheck,
} from "./utils/api";

const EXAMPLE_QUERIES = [
  "What are the main topics covered?",
  "Summarize the key findings",
  "What does the document say about performance?",
  "Explain the architecture described here",
];

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const chatEndRef = useRef(null);
  const { toasts, addToast } = useToast();

  // Health check on mount
  useEffect(() => {
    healthCheck().then(setConnected);
    const interval = setInterval(() => healthCheck().then(setConnected), 30000);
    return () => clearInterval(interval);
  }, []);

  // Load documents on mount
  useEffect(() => {
    listDocuments()
      .then((data) => setDocuments(data.documents))
      .catch(() => {});
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleUploaded = useCallback(
    (doc) => {
      setDocuments((prev) => [...prev, doc]);
      addToast(`${doc.filename} ingested — ${doc.total_chunks} chunks`, "success");
    },
    [addToast]
  );

  const handleDelete = useCallback(
    async (docId) => {
      try {
        await deleteDocument(docId);
        setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
        addToast("Document deleted", "success");
      } catch (err) {
        addToast(err.message, "error");
      }
    },
    [addToast]
  );

  const handleQuery = useCallback(
    async (query) => {
      const userMsg = { id: Date.now(), role: "user", text: query };
      setMessages((prev) => [...prev, userMsg]);
      setLoading(true);

      try {
        const data = await queryDocuments(query);
        const assistantMsg = {
          id: Date.now() + 1,
          role: "assistant",
          text: data.answer,
          sources: data.sources || [],
          meta: {
            latency_ms: data.latency_ms,
            confidence: data.confidence,
            refused: data.refused,
          },
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } catch (err) {
        const errorMsg = {
          id: Date.now() + 1,
          role: "assistant",
          text: `Something went wrong: ${err.message}`,
          sources: [],
          meta: null,
        };
        setMessages((prev) => [...prev, errorMsg]);
        addToast(err.message, "error");
      } finally {
        setLoading(false);
      }
    },
    [addToast]
  );

  return (
    <div className="app-layout">
      <ToastContainer toasts={toasts} />

      {/* Header */}
      <header className="app-header">
        <div className="app-header__brand">
          <span className="app-header__title">Document Analyst</span>
          <span className="app-header__tag">RAG</span>
        </div>
        <div className="app-header__status">
          <span
            className={`status-dot ${
              connected ? "" : "status-dot--disconnected"
            }`}
          />
          {connected ? "API connected" : "API disconnected"}
        </div>
      </header>

      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar__section">
          <div className="sidebar__section-title">Upload</div>
          <FileUpload
            onUploaded={handleUploaded}
            onError={(msg) => addToast(msg, "error")}
          />
        </div>
        <div className="sidebar__section" style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div className="sidebar__section-title">
            Documents ({documents.length})
          </div>
          <DocumentList documents={documents} onDelete={handleDelete} />
        </div>
      </aside>

      {/* Main */}
      <main className="main-content">
        <div className="chat-area">
          {messages.length === 0 && !loading ? (
            <div className="chat-empty">
              <BookOpen size={48} className="chat-empty__icon" />
              <h2 className="chat-empty__title">Ask your documents anything</h2>
              <p className="chat-empty__subtitle">
                Upload a document on the left, then ask questions. Answers are
                grounded in your documents with source citations.
              </p>
              <div className="chat-empty__hints">
                {EXAMPLE_QUERIES.map((q) => (
                  <button
                    key={q}
                    className="chat-empty__hint"
                    onClick={() => handleQuery(q)}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
              {loading && (
                <div className="thinking">
                  <div className="thinking__dots">
                    <div className="thinking__dot" />
                    <div className="thinking__dot" />
                    <div className="thinking__dot" />
                  </div>
                  <span className="thinking__text">Searching...</span>
                </div>
              )}
              <div ref={chatEndRef} />
            </>
          )}
        </div>
        <QueryBar onSubmit={handleQuery} disabled={loading} />
      </main>
    </div>
  );
}
