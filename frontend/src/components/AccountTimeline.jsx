import { Fragment } from "react";
import { Link } from "react-router-dom";
import { formatMoney } from "../lib/money";
import "./AccountTimeline.css";

const STATUS = {
  reconciled: { mark: "✓", label: "reconciles" },
  mismatch: { mark: "✗", label: "doesn't add up" },
  unverified: { mark: "–", label: "not checked" },
};

function month(iso) {
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00`);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { month: "short", year: "numeric" });
}

function missingLabel(link) {
  const from = month(link.missing_from);
  const to = month(link.missing_to);
  return from === to ? from : `${from} – ${to}`;
}

function accountName(account) {
  const kind = account.account_type === "credit_card" ? "card" : "account";
  return `${account.bank_name || `Unnamed ${kind}`} ••${account.account_last4}`;
}

function Connector({ link, currency }) {
  if (link.kind === "gap") {
    return (
      <li className="acct-link acct-link--gap">
        <span className="acct-missing">Missing: {missingLabel(link)}</span>
      </li>
    );
  }
  if (link.kind === "balance_mismatch") {
    return (
      <li className="acct-link acct-link--bad">
        <span className="acct-link-note">
          <span aria-hidden>✗</span> Balances differ by {formatMoney(Math.abs(link.difference), currency)}
        </span>
      </li>
    );
  }
  if (link.kind === "duplicate") {
    return (
      <li className="acct-link">
        <span className="acct-link-note">Same period twice</span>
      </li>
    );
  }
  return (
    <li className="acct-link acct-link--ok" aria-label="Balances connect">
      <span className="acct-link-line" aria-hidden />
    </li>
  );
}

function summary(account) {
  const n = account.statements.length;
  const gaps = account.links.filter((l) => l.kind === "gap").length;
  const breaks = account.links.filter((l) => l.kind === "balance_mismatch").length;
  const parts = [`${n} statements`];
  if (gaps) parts.push(`${gaps} ${gaps === 1 ? "gap" : "gaps"}`);
  if (breaks) parts.push(`${breaks} ${breaks === 1 ? "balance doesn't" : "balances don't"} carry over`);
  if (!gaps && !breaks) parts.push("every month connects");
  return parts.join(" · ");
}

/** Each account's saved statements in date order, flagging missing months and balances that don't carry over. */
export default function AccountTimeline({ accounts }) {
  const shown = (accounts || []).filter((a) => a.statements.length >= 2);
  if (!shown.length) return null;
  return (
    <section className="dashboard-sheet acct" aria-labelledby="acct-h">
      <h2 id="acct-h" className="dashboard-sheet-title">Accounts</h2>
      <p className="dashboard-sheet-note">Each statement&rsquo;s closing balance should be the next one&rsquo;s opening balance</p>
      <div className="acct-list">
        {shown.map((account) => (
          <div key={`${account.account_last4}-${account.currency}-${account.account_type}`} className="acct-row">
            <div className="acct-head">
              <h3 className="acct-name">{accountName(account)}</h3>
              <p className="acct-summary">{summary(account)}</p>
            </div>
            <ol className="acct-chips">
              {account.statements.map((s, i) => {
                const st = STATUS[s.status] || STATUS.unverified;
                return (
                  <Fragment key={s.job_id}>
                    {i > 0 && <Connector link={account.links[i - 1]} currency={account.currency} />}
                    <li>
                      <Link
                        to={`/scanner/${s.job_id}`}
                        className={`acct-chip acct-chip--${s.status}`}
                        aria-label={`${month(s.period_end)} statement, ${st.label}`}
                      >
                        <span className="acct-chip-mark" aria-hidden>{st.mark}</span>
                        {month(s.period_end)}
                      </Link>
                    </li>
                  </Fragment>
                );
              })}
            </ol>
          </div>
        ))}
      </div>
    </section>
  );
}
