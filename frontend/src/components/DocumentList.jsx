import React from "react";
import { FileText, Trash2 } from "lucide-react";

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentList({ documents, onDelete }) {
  if (!documents.length) {
    return (
      <div style={{ padding: "12px 0", textAlign: "center" }}>
        <p
          style={{
            fontSize: "0.78rem",
            color: "var(--text-muted)",
            lineHeight: 1.6,
          }}
        >
          No documents yet.
          <br />
          Upload one to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="doc-list">
      {documents.map((doc) => (
        <div key={doc.document_id} className="doc-item">
          <FileText size={18} className="doc-item__icon" />
          <div className="doc-item__info">
            <div className="doc-item__name" title={doc.filename}>
              {doc.filename}
            </div>
            <div className="doc-item__meta">
              {doc.total_chunks} chunks · {formatSize(doc.file_size_bytes)}
            </div>
          </div>
          <button
            className="doc-item__delete"
            onClick={() => onDelete(doc.document_id)}
            title="Delete document"
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
