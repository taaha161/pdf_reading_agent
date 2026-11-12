import { useEffect, useRef, useState } from "react";
import { exportTransactions, sendChatMessage } from "../api/client";
import "./ChatPanel.css";

const SUGGESTIONS = [
  "Show all money received",
  "List every ATM withdrawal",
  "Which categories did I spend the most on?",
  "Give me all transactions from Amazon",
];

function SparkIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z" />
      <path d="M19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" />
    </svg>
  );
}

function SendIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M5 12h14" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

function TableIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 4v16" />
    </svg>
  );
}

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
      <span className="chat-download-icon"><TableIcon /></span>
      <span className="chat-download-label">
        <strong>{count} transaction{count === 1 ? "" : "s"}</strong>
        <span>ready to download</span>
      </span>
      <div className="chat-download-actions">
        <button type="button" onClick={() => download("xlsx")} disabled={!!busy}>
          {busy === "xlsx" ? "Downloading…" : "Excel"}
        </button>
        <button type="button" onClick={() => download("csv")} disabled={!!busy}>
          {busy === "csv" ? "Downloading…" : "CSV"}
        </button>
      </div>
      {error && <span className="chat-download-error">{error}</span>}
    </div>
  );
}

export default function ChatPanel({ jobId, disabled, requireLogin, onRequireLogin, hideHeading }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const listRef = useRef(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  const send = async (preset) => {
    if (requireLogin) {
      setError("Please log in to chat.");
      onRequireLogin?.();
      return;
    }
    const text = (preset ?? input).trim();
    if (!text || !jobId || disabled || loading) return;
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
        <header className="chat-head">
          <span className="chat-head-icon"><SparkIcon /></span>
          <div>
            <h2>Ask your statement</h2>
            <p className="chat-hint">Find, total and export any transactions in plain English.</p>
          </div>
        </header>
      )}
      <div className="messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p className="chat-empty-title">Ask anything about this statement</p>
            <p className="chat-empty-body">
              Pull out the transactions you need, like &ldquo;Give me all transactions from John&rdquo;,
              then download them as Excel or CSV.
            </p>
            <div className="chat-suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => send(s)} disabled={disabled || loading}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.role === "assistant" && <span className="message-avatar"><SparkIcon /></span>}
            <div className="message-bubble">
              <div className="message-content">{msg.content}</div>
              {msg.transactions?.length > 0 && <ChatDownload transactions={msg.transactions} />}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <span className="message-avatar"><SparkIcon /></span>
            <div className="message-bubble">
              <span className="typing" aria-label="Assistant is typing"><i /><i /><i /></span>
            </div>
          </div>
        )}
      </div>
      {error && <div className="chat-error">{error}</div>}
      <form
        className="chat-input-wrap"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Show all transactions from John"
          aria-label="Ask about your statement"
          disabled={disabled || loading}
        />
        <button
          type="submit"
          aria-label="Send"
          disabled={disabled || loading || (!requireLogin && !input.trim())}
        >
          <SendIcon />
        </button>
      </form>
    </section>
  );
}
