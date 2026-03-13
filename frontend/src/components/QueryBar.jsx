import React, { useState, useRef } from "react";
import { ArrowUp } from "lucide-react";

export default function QueryBar({ onSubmit, disabled }) {
  const [value, setValue] = useState("");
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleInput = (e) => {
    setValue(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 120) + "px";
  };

  return (
    <div className="query-bar">
      <form className="query-bar__form" onSubmit={handleSubmit}>
        <textarea
          ref={textareaRef}
          className="query-bar__input"
          placeholder="Ask a question about your documents..."
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          rows={1}
          disabled={disabled}
        />
        <button
          type="submit"
          className="query-bar__submit"
          disabled={disabled || !value.trim()}
        >
          <ArrowUp size={18} />
        </button>
      </form>
      <div className="query-bar__hint">
        Press Enter to send · Shift+Enter for new line
      </div>
    </div>
  );
}
