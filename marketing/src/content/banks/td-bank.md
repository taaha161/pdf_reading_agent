---
name: "TD Bank"
shortName: "TD Bank"
slug: "td-bank-statement-to-excel"
seoTitle: "Convert TD Bank Statements to Excel or CSV"
description: "Convert TD Bank checking, savings, and credit card statement PDFs to Excel or CSV. Use up to 7 years of online statements, not just recent activity."
country: "US"
statementTypes: ["Checking", "Savings", "Credit card", "Business"]
intro: "TD Bank keeps up to seven years of statements online, while its spreadsheet-friendly downloads cover much less. For a full tax year, a loan file, or catch-up bookkeeping, the PDF statements are the complete record, and converting them gets every row into Excel or your accounting software."
exportLimits: "TD Bank says you can review up to 7 years of statements and notices in Online Banking and the mobile app, and download account information to Quicken or QuickBooks. Third-party guides report that CSV transaction downloads only reach back about 18 months, so older months are available only as PDF statements."
downloadSteps:
  - "Sign in to TD Bank Online Banking or the TD Bank app."
  - "Open Statements & Documents and pick the account."
  - "Select the statement date and download the PDF."
  - "Repeat for each month, then convert the files one after another."
layoutNotes:
  - title: "Deposits and withdrawals listed separately"
    body: "TD statements group deposits, electronic payments, and other withdrawals into their own sections. Your export combines them into one table with each row marked as a credit or debit."
  - title: "Check images and check lists"
    body: "Checking statements can include a list of paid checks or check images. Check entries come through as transactions with their numbers kept in the description; the images themselves are ignored."
  - title: "Wrapped descriptions"
    body: "Card purchases and transfers often wrap to a second line. Extraction keeps wrapped text with its transaction instead of creating extra rows."
  - title: "Daily balance tables"
    body: "Some statements end with a daily balance summary. These are balances, not transactions, so they're left out of your export."
faqs:
  - q: "How far back can I get TD Bank statements?"
    a: "TD Bank says up to 7 years of statements are available in Online Banking and the app."
  - q: "Can I download TD Bank transactions as CSV?"
    a: "Recent transactions can be downloaded, and TD supports Quicken and QuickBooks downloads. Guides report CSV covers about 18 months. For older months, convert the PDF statements."
  - q: "Does this work for TD Canada Trust?"
    a: "Yes. Statements from TD Canada Trust and other banks convert the same way. This page covers TD Bank in the US."
  - q: "Will this work on a scanned TD statement?"
    a: "Yes. Scanned and photographed statements go through OCR. Choose accurate mode for faint or skewed scans."
sources:
  - label: "TD Bank: Online Banking and statements (official)"
    url: "https://www.td.com/us/en/personal-banking/online-banking"
  - label: "Invoice Data Extraction: TD Bank statement to Excel"
    url: "https://invoicedataextraction.com/blog/td-bank-statement-to-excel"
reviewed: 2026-11-04
---
