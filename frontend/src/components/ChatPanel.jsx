import { useState } from "react";
import { sendChatMessage } from "../api/client";
import "./ChatPanel.css";

export default function ChatPanel({ jobId, disabled }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const send = async () => {
    const text = input.trim();
    if (!text || !jobId || disabled) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    setError(null);
    try {
      const reply = await sendChatMessage(jobId, text);
      setMessages((m) => [...m, { role: "assistant", content: reply }]);
    } catch (e) {
      setError(e.message || "Failed to get reply");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="chat-panel">
      <h2>Validate CSV</h2>
      <p className="chat-hint">
        Ask why a transaction was categorized a certain way or to explain any row.
      </p>
      <div className="messages">
        {messages.length === 0 && (
          <div className="message placeholder">
            No messages yet. Ask something like: &ldquo;Why is Amazon in Shopping?&rdquo;
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <span className="message-role">{msg.role === "user" ? "You" : "Assistant"}</span>
            <div className="message-content">{msg.content}</div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <span className="message-role">Assistant</span>
            <div className="message-content">...</div>
          </div>
        )}
      </div>
      {error && <div className="chat-error">{error}</div>}
      <div className="chat-input-wrap">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask about the data or categories..."
          disabled={disabled || loading}
        />
        <button type="button" onClick={send} disabled={disabled || loading || !input.trim()}>
          Send
        </button>
      </div>
    </section>
  );
}
