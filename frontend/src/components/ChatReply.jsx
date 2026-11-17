// Renders the assistant's reply text and the rows it matched.
// The reply may use a tiny markdown subset ("- " / "* " / "1. " bullets and **bold**). It is turned
// into React elements (never raw HTML), so text from the statement can't inject markup.

const TABLE_PREVIEW_ROWS = 50;

function renderInline(text) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4
      ? <strong key={i}>{part.slice(2, -2)}</strong>
      : part,
  );
}

const BULLET_RE = /^\s*(?:[-*•]|\d+[.)])\s+(.*)$/;

/** Group lines into paragraphs and bullet lists. */
export function ReplyText({ text }) {
  const blocks = [];
  for (const raw of String(text || "").split("\n")) {
    const line = raw.trimEnd();
    const bullet = line.match(BULLET_RE);
    const last = blocks[blocks.length - 1];
    if (bullet) {
      if (last?.type === "list") last.items.push(bullet[1]);
      else blocks.push({ type: "list", items: [bullet[1]] });
    } else if (!line.trim()) {
      blocks.push({ type: "break" });
    } else if (last?.type === "p") {
      last.lines.push(line.trim());
    } else {
      blocks.push({ type: "p", lines: [line.trim()] });
    }
  }
  return (
    <div className="message-content reply-text">
      {blocks.map((b, i) => {
        if (b.type === "list") {
          return (
            <ul key={i}>
              {b.items.map((item, j) => <li key={j}>{renderInline(item)}</li>)}
            </ul>
          );
        }
        if (b.type === "p") return <p key={i}>{renderInline(b.lines.join(" "))}</p>;
        return null;
      })}
    </div>
  );
}

function formatAmount(value) {
  const n = Math.abs(parseFloat(String(value ?? "").replace(/[^0-9.-]/g, "")));
  if (!Number.isFinite(n)) return String(value ?? "");
  return n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Compact table of the rows the answer matched (first TABLE_PREVIEW_ROWS; the download has all). */
export function ReplyTable({ transactions }) {
  const rows = transactions.slice(0, TABLE_PREVIEW_ROWS);
  const hasGroup = transactions.some((t) => t.group);
  return (
    <div className="reply-table-wrap">
      <table className="reply-table">
        <thead>
          <tr>
            <th className="col-date">Date</th>
            <th>Description</th>
            <th className="num">Amount</th>
            <th>{hasGroup ? "Sub-category" : "Category"}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((t, i) => {
            const debit = String(t.type).toLowerCase() === "debit";
            return (
              <tr key={i}>
                <td className="nowrap col-date">{t.date}</td>
                <td className="desc" title={t.description}>
                  {t.description}
                  <span className="reply-date-inline">{t.date}</span>
                </td>
                <td className={`num ${debit ? "debit" : "credit"}`}>
                  {debit ? "−" : "+"}{formatAmount(t.amount)}
                </td>
                <td>{hasGroup ? t.group : t.category}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {transactions.length > rows.length && (
        <p className="reply-table-more">
          Showing {rows.length} of {transactions.length}. Download for the full list.
        </p>
      )}
    </div>
  );
}
