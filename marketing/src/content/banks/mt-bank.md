---
name: "M&T Bank"
shortName: "M&T"
slug: "mt-bank-statement-to-excel"
seoTitle: "Convert M&T Bank Statements to Excel or CSV"
description: "Convert M&T Bank statement PDFs, including former People's United accounts, to Excel or CSV. Every transaction in clean, categorized columns."
country: "US"
statementTypes: ["Checking", "Savings", "Business checking"]
intro: "M&T keeps your monthly statements as eStatements, but its transaction download is meant for recent activity, and former People's United customers saw only a short window of history carried over. For full months or older periods, the PDF statement is the record, and converting it gets those transactions into a spreadsheet."
exportLimits: "M&T's digital services agreement describes transaction downloads for personal finance software as covering recent history, without a fixed window. M&T's People's United transition FAQ says converted checking accounts show 60 days of prior history online (18 months for savings). For anything older, use the eStatement PDFs."
downloadSteps:
  - "Sign in to M&T online banking."
  - "Open the account, then go to eStatements and Notices."
  - "Choose the statement month and download the PDF."
  - "Repeat for each month you need, then upload the PDFs here."
layoutNotes:
  - title: "Account summary block"
    body: "Statements start with the beginning balance, deposits and credits, withdrawals and debits, and the ending balance. These are used to check your rows, not exported as transactions."
  - title: "Legacy People's United statements"
    body: "Older statements from before the transition use the People's United layout. They're extracted into the same columns, so check the column order lines up before merging years."
  - title: "Checks in a compact table"
    body: "Paid checks are often listed by number, date, and amount. Each becomes its own row, with the check number kept in the description."
faqs:
  - q: "Can I download M&T transactions to Excel?"
    a: "M&T offers a download of recent activity for finance software. For full statement months or older periods, convert the eStatement PDFs here."
  - q: "I was a People's United customer. How do I get my old history?"
    a: "M&T says only a short window of People's United checking history carried over online. Use your old PDF statements, or request copies from M&T, then convert them."
  - q: "Does it handle long business statements?"
    a: "Yes. Pages are processed in order with repeated headers left out, and the rows are checked against the statement totals."
  - q: "What does it cost?"
    a: "Try 10 pages free without an account, and get 100 pages free in your first month after signing up. After that it's $10 a month for 100 pages, or one-off page packs."
sources:
  - label: "M&T: eStatements and notices"
    url: "https://www.mtb.com/personal/online-and-mobile/estatements-notices"
  - label: "M&T FAQ: People's United transaction history after transition"
    url: "https://www.mtb.com/faq/peoples-united/account-access/personal-transaction-history-after-transition"
  - label: "M&T Digital Services Agreement"
    url: "https://www.mtb.com/dsa"
reviewed: 2026-11-22
---
