---
name: "Truist"
shortName: "Truist"
slug: "truist-bank-statement-to-excel"
seoTitle: "Convert Truist Bank Statements to Excel or CSV"
description: "Convert Truist statement PDFs, including legacy SunTrust and BB&T periods, to Excel or CSV, with every row checked against the statement totals."
country: "US"
statementTypes: ["Checking", "Savings", "Business checking", "Credit card"]
intro: "Truist lets you download recent transactions as a file, but that download only covers a limited window and is labeled as a tracking copy, not an official record. When you need a full tax year, older months, or statements from the SunTrust and BB&T days, the PDF statement is the record, and it has to be converted before Excel, QuickBooks, or Xero can use it."
exportLimits: "Guides report that Truist's transaction download (CSV and similar formats) reaches back about 18 months, and Truist's small-business pages describe downloading or printing up to 18 months of account history. Each account needs its own download, and pending transactions are left out. Monthly PDF statements reach further back, including legacy SunTrust and BB&T periods."
downloadSteps:
  - "Sign in to Truist online banking on a desktop browser."
  - "Open the account, then go to Statements and documents (sometimes shown as Documents)."
  - "Choose the statement period and download it. The file saves as a PDF."
  - "Repeat for each month and each account you need, then upload the PDFs here one after another."
layoutNotes:
  - title: "Legacy SunTrust and BB&T statements"
    body: "Older statements may use the SunTrust or BB&T layout rather than the current Truist one. They're read the same way, but if you combine years, check that the column order (date, description, amount) lines up in your spreadsheet before you merge files."
  - title: "Deposits and withdrawals in separate sections"
    body: "Checking statements group deposits, withdrawals, and checks into their own sections rather than one running list. Every section's rows are extracted, with money in and money out kept as separate signed amounts so totals still add up."
  - title: "Summary totals to check against"
    body: "The account summary lists the beginning balance, total deposits, total withdrawals, and the ending balance. These are printed totals, not transactions, so they aren't turned into rows. They're used to check that the extracted rows add up."
  - title: "Checks listed by number"
    body: "Paid checks often appear in a compact table of check number, date, and amount. Each check becomes its own row, with the check number kept in the description so you can match it to your register."
faqs:
  - q: "Can I download Truist transactions straight to Excel?"
    a: "Truist offers a transaction download, but guides report it only covers about 18 months, one account at a time, and it excludes pending items. For anything older, download the monthly PDF statements and convert them."
  - q: "Does this work on old SunTrust or BB&T statements?"
    a: "Yes. Upload the PDF the same way. Legacy layouts are extracted into the same date, description, and amount columns."
  - q: "Can I convert a Truist business statement with many pages?"
    a: "Yes. Long statements are processed page by page, with repeated headers and balance lines left out of your rows. The rows are checked against the statement's printed totals so you can see if anything is missing."
  - q: "Will the export import into QuickBooks or Xero?"
    a: "Yes. Download the CSV and use the bank-file import in QuickBooks Online or Xero, or open the Excel file for review first."
sources:
  - label: "Tiller: How to export Truist bank transactions to a spreadsheet"
    url: "https://tiller.com/export-truist-bank-statements/"
  - label: "Invoice Data Extraction: Truist statement to Excel (18-month download window)"
    url: "https://invoicedataextraction.com/blog/truist-bank-statement-to-excel"
reviewed: 2026-11-22
---
