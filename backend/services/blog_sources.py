"""Curated external sources for blog posts.

Every post ends with a "Sources" section linking two or more authoritative outside
sites (IRS, CFPB, SBA, Microsoft/Google docs, Wikipedia, the bank's own help pages).
Citing outside sources is a trust signal for readers and AI answer engines alike.

URLs come from this hand-checked list only, never from the model, so a post can't
cite a page that doesn't exist. Add a URL here only after confirming it loads.
"""

from __future__ import annotations

import re

SOURCES: dict[str, tuple[str, str]] = {
    # id: (label, url)
    "irs_records": ("IRS: Recordkeeping for small businesses",
                    "https://www.irs.gov/businesses/small-businesses-self-employed/recordkeeping"),
    "irs_keep": ("IRS: How long should I keep records?",
                 "https://www.irs.gov/businesses/small-businesses-self-employed/how-long-should-i-keep-records"),
    "irs_kind": ("IRS: What kind of records should I keep?",
                 "https://www.irs.gov/businesses/small-businesses-self-employed/what-kind-of-records-should-i-keep"),
    "irs_p583": ("IRS Publication 583: Starting a Business and Keeping Records",
                 "https://www.irs.gov/publications/p583"),
    "irs_schc": ("IRS: About Schedule C (Form 1040)",
                 "https://www.irs.gov/forms-pubs/about-schedule-c-form-1040"),
    "cfpb_statement": ("CFPB: What is a checking account statement?",
                       "https://www.consumerfinance.gov/ask-cfpb/what-is-a-checking-account-statement-en-1035/"),
    "cfpb_accounts": ("CFPB: Bank accounts and services",
                      "https://www.consumerfinance.gov/consumer-tools/bank-accounts/"),
    "cfpb_cc": ("CFPB: Credit cards", "https://www.consumerfinance.gov/consumer-tools/credit-cards/"),
    "cfpb_cc_read": ("CFPB: How do I read my credit card statement?",
                     "https://www.consumerfinance.gov/ask-cfpb/how-do-i-read-my-credit-card-statement-en-61/"),
    "cfpb_home": ("CFPB: Owning a home", "https://www.consumerfinance.gov/owning-a-home/"),
    "sba_finances": ("SBA: Manage your finances",
                     "https://www.sba.gov/business-guide/manage-your-business/manage-your-finances"),
    "sba_loans": ("SBA: Loans", "https://www.sba.gov/funding-programs/loans"),
    "nist_privacy": ("NIST Privacy Framework", "https://www.nist.gov/privacy-framework"),
    "ms_csv": ("Microsoft Support: Import or export text (.txt or .csv) files",
               "https://support.microsoft.com/en-us/office/import-or-export-text-txt-or-csv-files-5250ac4c-663c-47ce-937b-339e391393ba"),
    "ms_pivot": ("Microsoft Support: Create a PivotTable to analyze worksheet data",
                 "https://support.microsoft.com/en-us/office/create-a-pivottable-to-analyze-worksheet-data-a9a84538-bfe9-40a9-a8e9-f99134456576"),
    "gsheets_import": ("Google Docs Editors Help: Import data sets in Google Sheets",
                       "https://support.google.com/docs/answer/40608"),
    "wiki_statement": ("Wikipedia: Bank statement", "https://en.wikipedia.org/wiki/Bank_statement"),
    "wiki_recon": ("Wikipedia: Bank reconciliation", "https://en.wikipedia.org/wiki/Bank_reconciliation"),
    "wiki_bookkeeping": ("Wikipedia: Bookkeeping", "https://en.wikipedia.org/wiki/Bookkeeping"),
    "wiki_double": ("Wikipedia: Double-entry bookkeeping",
                    "https://en.wikipedia.org/wiki/Double-entry_bookkeeping"),
    "wiki_ocr": ("Wikipedia: Optical character recognition",
                 "https://en.wikipedia.org/wiki/Optical_character_recognition"),
    "wiki_idp": ("Wikipedia: Intelligent document processing",
                 "https://en.wikipedia.org/wiki/Intelligent_document_processing"),
    "wiki_ofx": ("Wikipedia: Open Financial Exchange (OFX)",
                 "https://en.wikipedia.org/wiki/Open_Financial_Exchange"),
    "wiki_csv": ("Wikipedia: Comma-separated values", "https://en.wikipedia.org/wiki/Comma-separated_values"),
    "wiki_acctsw": ("Wikipedia: Accounting software", "https://en.wikipedia.org/wiki/Accounting_software"),
    "wiki_coa": ("Wikipedia: Chart of accounts", "https://en.wikipedia.org/wiki/Chart_of_accounts"),
    "wiki_forgery": ("Wikipedia: Forgery", "https://en.wikipedia.org/wiki/Forgery"),
    "wiki_pivot": ("Wikipedia: Pivot table", "https://en.wikipedia.org/wiki/Pivot_table"),
    "wiki_dataentry": ("Wikipedia: Data entry", "https://en.wikipedia.org/wiki/Data_entry"),
    "wiki_cashflow": ("Wikipedia: Cash flow statement", "https://en.wikipedia.org/wiki/Cash_flow_statement"),
    "wiki_cc": ("Wikipedia: Credit card", "https://en.wikipedia.org/wiki/Credit_card"),
    "wiki_qb": ("Wikipedia: QuickBooks", "https://en.wikipedia.org/wiki/QuickBooks"),
    "wf_statements": ("Wells Fargo: Online statements", "https://www.wellsfargo.com/online-banking/statements/"),
    "bofa_online": ("Bank of America: Online banking", "https://www.bankofamerica.com/online-banking/"),
    "citi_home": ("Citi: Official site", "https://www.citi.com/"),
    "usbank_kb": ("U.S. Bank: Viewing statements online",
                  "https://www.usbank.com/customer-service/knowledge-base/KB0069323.html"),
    "ally_help": ("Ally: Account information help", "https://www.ally.com/help/bank/account-information.html"),
    "nfcu_paperless": ("Navy Federal: Paperless statements",
                       "https://www.navyfederal.org/content/nfo/en/home/services/mobile-online-banking/paperless-statements"),
}

# First matching rules win, in order; each rule's ids are added until MAX_SOURCES.
# Patterns run against "<slug> <keyword> <title>" in lower case.
RULES: list[tuple[str, list[str]]] = [
    (r"wells[- ]fargo", ["wf_statements"]),
    (r"bank[- ]of[- ]america", ["bofa_online"]),
    (r"\bciti", ["citi_home"]),
    (r"u\.?s\.?[- ]bank", ["usbank_kb"]),
    (r"\bally\b", ["ally_help"]),
    (r"navy[- ]federal", ["nfcu_paperless"]),
    (r"credit[- ]card", ["cfpb_cc_read", "wiki_cc"]),
    (r"generator|fake|forg", ["wiki_forgery", "cfpb_statement"]),
    (r"reconcil", ["wiki_recon"]),
    (r"pivot", ["ms_pivot", "wiki_pivot"]),
    (r"google[- ]sheets", ["gsheets_import"]),
    (r"ocr|scan", ["wiki_ocr"]),
    (r"extraction|analysis[- ]software|\bai\b", ["wiki_idp"]),
    (r"quickbooks|qbo|ofx|qfx", ["wiki_ofx", "wiki_qb"]),
    (r"csv|excel", ["ms_csv", "wiki_csv"]),
    (r"schedule[- ]c", ["irs_schc"]),
    (r"tax|year[- ]end|keep[- ]bank|retention", ["irs_keep", "irs_kind"]),
    (r"chart[- ]of[- ]accounts", ["wiki_coa"]),
    (r"cash[- ]flow", ["wiki_cashflow"]),
    (r"mortgage", ["cfpb_home"]),
    (r"loan", ["sba_loans"]),
    (r"privacy|safe|secur", ["nist_privacy"]),
    (r"data[- ]entry|manual", ["wiki_dataentry"]),
    (r"bookkeeping|accountant|month[- ]end|catch[- ]up|small[- ]business|organizer", ["wiki_bookkeeping", "irs_records"]),
    (r"accounting[- ]software|bookkeeping[- ]software|bank[- ]feed", ["wiki_acctsw"]),
    (r"business|expense", ["sba_finances", "irs_p583"]),
]

# Used when the rules give fewer than MIN_DOMAINS distinct sites.
FALLBACK = ["cfpb_statement", "wiki_statement", "irs_records"]

MIN_DOMAINS = 2
MAX_SOURCES = 4
HEADING = "## Sources"

_LINK_RE = re.compile(r"\]\((https?://[^)\s]+)\)")


def _domain(url: str) -> str:
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    return host.removeprefix("www.")


def external_domains(body: str, own_domain: str = "bankstatementscanner.com") -> set[str]:
    return {d for d in (_domain(u) for u in _LINK_RE.findall(body)) if d != own_domain}


def pick_sources(slug: str, keyword: str = "", title: str = "") -> list[tuple[str, str]]:
    """Two to four (label, url) pairs spanning at least two domains."""
    text = f"{slug.replace('-', ' ')} {slug} {keyword} {title}".lower()
    ids: list[str] = []
    for pattern, rule_ids in RULES:
        if re.search(pattern, text):
            ids += [i for i in rule_ids if i not in ids]
        if len(ids) >= MAX_SOURCES:
            break
    ids = ids[:MAX_SOURCES]
    for fid in FALLBACK:
        if len({_domain(SOURCES[i][1]) for i in ids}) >= MIN_DOMAINS and len(ids) >= 2:
            break
        if fid not in ids:
            ids.append(fid)
    return [SOURCES[i] for i in ids]


def ensure_sources(body: str, slug: str, keyword: str = "", title: str = "") -> str:
    """Append a Sources section unless the body already links two or more outside sites."""
    if HEADING in body or len(external_domains(body)) >= MIN_DOMAINS:
        return body
    lines = "\n".join(f"- [{label}]({url})" for label, url in pick_sources(slug, keyword, title))
    return body.rstrip() + f"\n\n{HEADING}\n\n{lines}\n"
