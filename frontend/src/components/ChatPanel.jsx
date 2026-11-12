import { useState } from "react";
import { exportTransactions, sendChatMessage } from "../api/client";
import "./ChatPanel.css";

function ChatDownload({ transactions }) {
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const download = async (format) => {
    setBusy(format);
    setError(null);
    try {
      await exportTransactions(transactions, { format, filenameBase: "chat-transactions" });
    } catch (e) {
      setError(e.message || "Failed to download file");
    } finally {
      setBusy(null);
    }
  };
  const count = transactions.length;
  return (
    <div className="chat-download">
      <span className="chat-download-label">
        {count} transaction{count === 1 ? "" : "s"}
      </span>
      <button type="button" onClick={() => download("xlsx")} disabled={!!busy}>
        {busy === "xlsx" ? "Downloading…" : "Download Excel"}
      </button>
      <button type="button" onClick={() => download("csv")} disabled={!!busy}>
        {busy === "csv" ? "Downloading…" : "Download CSV"}
      </button>
      {error && <span className="chat-download-error">{error}</span>}
    </div>
  );
}

export default function ChatPanel({ jobId, disabled, requireLogin, onRequireLogin, hideHeading }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const send = async () => {
    if (requireLogin) {
      setError("Please log in to chat.");
      onRequireLogin?.();
      return;
    }
    const text = input.trim();
    if (!text || !jobId || disabled) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setLoading(true);
    setError(null);
    try {
      const { reply, transactions } = await sendChatMessage(jobId, text);
      setMessages((m) => [...m, { role: "assistant", content: reply, transactions }]);
    } catch (e) {
      setError(e.message || "Failed to get reply");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="chat-panel" data-clarity-mask="true">
      {!hideHeading && (
        <>
          <h2>Validate CSV</h2>
          <p className="chat-hint">
            Ask why a transaction was categorized a certain way or to explain any row.
          </p>
        </>
      )}
      <div className="messages">
        {messages.length === 0 && (
          <div className="message placeholder">
            No messages yet. Ask something like: &ldquo;Why is Amazon in Shopping?&rdquo; or
            &ldquo;Give me all transactions from John&rdquo; to download them as Excel/CSV.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            <span className="message-role">{msg.role === "user" ? "You" : "Assistant"}</span>
            <div className="message-content">{msg.content}</div>
            {msg.transactions?.length > 0 && <ChatDownload transactions={msg.transactions} />}
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
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && (e.preventDefault(), send())}
          placeholder="Ask about the data or categories..."
          disabled={disabled || loading}
        />
        <button type="button" onClick={send} disabled={disabled || loading || (!requireLogin && !input.trim())}>
          Send
        </button>
      </div>
    </section>
  );
}
