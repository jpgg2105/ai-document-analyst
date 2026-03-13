import React from "react";
import ReactMarkdown from "react-markdown";
import { Clock, BarChart3, ShieldCheck } from "lucide-react";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message ${isUser ? "message--user" : ""}`}>
      <div className={`message__label ${isUser ? "message__label--user" : ""}`}>
        {isUser ? "You" : "Analyst"}
      </div>
      <div
        className={`message__bubble ${
          isUser ? "message__bubble--user" : "message__bubble--assistant"
        }`}
      >
        {isUser ? (
          message.text
        ) : (
          <ReactMarkdown>{message.text}</ReactMarkdown>
        )}
      </div>

      {/* Sources */}
      {!isUser && message.sources && message.sources.length > 0 && (
        <div className="message__sources">
          {message.sources.map((src, i) => (
            <span key={i} className="source-tag">
              <span className="source-tag__dot" />
              {src.filename} p.{src.page_number}
            </span>
          ))}
        </div>
      )}

      {/* Meta */}
      {!isUser && message.meta && (
        <div className="message__meta">
          {message.meta.latency_ms != null && (
            <span title="Response latency">
              <Clock size={11} style={{ verticalAlign: "-1px" }} />{" "}
              {Math.round(message.meta.latency_ms)}ms
            </span>
          )}
          {message.meta.confidence != null && (
            <span title="Confidence score">
              <BarChart3 size={11} style={{ verticalAlign: "-1px" }} />{" "}
              {(message.meta.confidence * 100).toFixed(1)}%
            </span>
          )}
          {message.meta.refused && (
            <span title="Low confidence — refused to answer" style={{ color: "var(--error)" }}>
              <ShieldCheck size={11} style={{ verticalAlign: "-1px" }} /> refused
            </span>
          )}
        </div>
      )}
    </div>
  );
}
