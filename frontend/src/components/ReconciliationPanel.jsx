import { useEffect, useRef } from "react";
import { formatMoney } from "../lib/money";
import { trackEvent } from "../lib/analytics";
import "./ReconciliationPanel.css";

const CHECK_LABELS = {
  balance_chain: "Running balances",
  opening: "Opening balance",
  closing: "Closing balance",
  credits: "Total money in",
  debits: "Total money out",
};

const close = (a, b) => Math.abs(a - b) <= 0.011;

function StatusIcon({ status }) {
  const common = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 2.25, strokeLinecap: "round", strokeLinejoin: "round", "aria-hidden": true };
  if (status === "reconciled") return <svg {...common}><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>;
  if (status === "mismatch") return <svg {...common}><path d="M6 6l12 12M18 6L6 18" /></svg>;
  return <svg {...common}><path d="M6 12h12" /></svg>;
}

/** "Opening $1,000.00 + $600.00 in − $280.00 out = closing $1,320.00" (owed version for cards). */
function equation(rec, currency) {
  const { opening_balance: o, closing_balance: c, total_credits: inn, total_debits: out } = rec;
  const m = (v) => formatMoney(v, currency);
  if (o == null || c == null) return `${m(inn)} in, ${m(out)} out`;
  if (close(o - inn + out, c)) return `Owed ${m(o)} − ${m(inn)} paid + ${m(out)} spent = ${m(c)} owed`;
  return `Opening ${m(o)} + ${m(inn)} in − ${m(out)} out = closing ${m(c)}`;
}

function rowLabel(transactions, i) {
  const t = transactions?.[i];
  const desc = t?.description ? `, ${t.description.length > 40 ? `${t.description.slice(0, 40)}…` : t.description}` : "";
  return `Row ${i + 1}${desc}`;
}

function hintText(hint, transactions, currency) {
  const amount = formatMoney(hint.amount, currency);
  if (hint.kind === "flipped_type") {
    const now = transactions?.[hint.row_index]?.type === "credit" ? "credit" : "debit";
    const other = now === "credit" ? "debit (money out)" : "credit (money in)";
    return `${rowLabel(transactions, hint.row_index)} (${amount}) may be a ${other}.`;
  }
  if (hint.kind === "duplicate_row") {
    return `${rowLabel(transactions, hint.row_index)} (${amount}) may have been read twice.`;
  }
  const what = hint.direction === "credit" ? "credit (money in)" : "debit (money out)";
  return `A ${what} of ${amount} may be missing between rows ${hint.from_row + 1} and ${hint.to_row + 1}.`;
}

function hintRows(hint) {
  return hint.kind === "missing_row" ? [hint.from_row, hint.to_row] : [hint.row_index];
}

function headline(rec, currency) {
  if (rec.status === "reconciled") return "Reconciles with the statement";
  if (rec.status === "unverified") return "Can't check this statement";
  const failed = rec.checks.find((c) => c.status === "fail" && c.difference != null && c.difference !== 0);
  return failed ? `Doesn't add up: off by ${formatMoney(Math.abs(failed.difference), currency)}` : "Doesn't add up";
}

/**
 * Whether the extracted rows add up to the statement's own balances (and, when read, its summary box).
 * onJumpToRow(indices) highlights and scrolls to the rows a hint points at.
 */
export default function ReconciliationPanel({ reconciliation: rec, currency, transactions, onJumpToRow, stale = false, jobId }) {
  const tracked = useRef(null);
  useEffect(() => {
    if (!rec || !jobId || tracked.current === jobId) return;
    tracked.current = jobId;
    trackEvent("reconciliation_shown", { status: rec.status });
  }, [rec, jobId]);

  if (!rec) return null;
  const ran = rec.checks.filter((c) => c.status !== "skipped");
  const chain = rec.checks.find((c) => c.key === "balance_chain");
  const showTable = rec.checks.some((c) => c.key !== "balance_chain");

  return (
    <section className={`recon recon--${rec.status}`} aria-labelledby="recon-title">
      <div className="recon-head">
        <span className="recon-icon"><StatusIcon status={rec.status} /></span>
        <div className="recon-head-text">
          <h2 id="recon-title" className="recon-title">{headline(rec, currency)}</h2>
          <p className="recon-sub">
            {rec.status === "unverified" ? rec.reason : equation(rec, currency)}
          </p>
          {stale && <p className="recon-stale">You've edited rows since the scan. This check reflects the original scan.</p>}
        </div>
      </div>

      {rec.hints.length > 0 && (
        <ul className="recon-hints">
          {rec.hints.map((h, i) => (
            <li key={i}>
              <span>{hintText(h, transactions, currency)}</span>
              {onJumpToRow && (
                <button type="button" className="recon-jump" onClick={() => onJumpToRow(hintRows(h))}>
                  Show {h.kind === "missing_row" ? "rows" : "row"}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {ran.length > 0 && (
        <details className="recon-details">
          <summary>How we checked</summary>
          {chain && (
            <p className="recon-detail-line">
              {chain.status === "pass"
                ? "Every balance printed on the statement matches the rows before it."
                : `${chain.breaks} ${chain.breaks === 1 ? "place where" : "places where"} the rows between two printed balances don't add up.`}
            </p>
          )}
          {showTable && (
            <div className="recon-table-wrap">
              <table className="recon-table">
                <thead>
                  <tr>
                    <th scope="col">Check</th>
                    <th scope="col" className="recon-num">Statement says</th>
                    <th scope="col" className="recon-num">We extracted</th>
                    <th scope="col" className="recon-num">Difference</th>
                  </tr>
                </thead>
                <tbody>
                  {rec.checks.filter((c) => c.key !== "balance_chain").map((c) => (
                    <tr key={c.key} className={`recon-check--${c.status}`}>
                      <th scope="row">
                        <span className="recon-check-mark" aria-hidden>{c.status === "pass" ? "✓" : c.status === "fail" ? "✗" : "–"}</span>
                        {CHECK_LABELS[c.key] || c.key}
                        <span className="sr-only"> {c.status === "pass" ? "matches" : c.status === "fail" ? "doesn't match" : "not checked"}</span>
                      </th>
                      <td className="recon-num">{c.expected == null ? "—" : formatMoney(c.expected, currency)}</td>
                      <td className="recon-num">{c.actual == null ? "—" : formatMoney(c.actual, currency)}</td>
                      <td className="recon-num">{c.difference == null ? "—" : formatMoney(c.difference, currency)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </details>
      )}
    </section>
  );
}
