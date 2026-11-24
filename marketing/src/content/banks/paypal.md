---
name: "PayPal"
shortName: "PayPal"
slug: "paypal-statement-to-excel"
seoTitle: "Convert PayPal Statements (PDF) to Excel or CSV"
description: "Convert PayPal monthly statement PDFs to Excel or CSV. Useful when a client or lender gives you the PDF, or you need many months at once."
country: "US"
statementTypes: ["Personal account", "Business account"]
intro: "If you can sign in to the PayPal account, its activity report is the quickest route to a CSV. But bookkeepers and lenders are often handed PDF statements instead, by a client who won't share a login or a borrower who already downloaded them. That's when a PDF converter earns its keep."
exportLimits: "PayPal's activity download covers up to the last seven years, but each report is capped at 12 months, so several years means several reports. CSV and TAB reports are limited to 50,000 records. Monthly statements are separate documents you request and then download. When all you have is the PDF, it has to be converted."
downloadSteps:
  - "Sign in at paypal.com."
  - "Open Activity, then Statements (or Reports in a business account)."
  - "Request the monthly statement you need, then download it when it's ready."
  - "If you have the login and just need rows, the activity report's CSV is faster. If you only have PDFs, upload them here."
layoutNotes:
  - title: "Gross, fee, and net"
    body: "PayPal records each payment with a gross amount, a fee, and a net amount. Before importing, check that your rows use the amount that actually moved the balance, so fees aren't counted twice or missed."
  - title: "Currency conversions as extra lines"
    body: "A payment in another currency can appear with separate conversion lines. Each line is its own row, so check them together when you categorize."
  - title: "Holds and transfers to bank"
    body: "Transfers to your bank and holds appear as their own activity. They're kept as rows, so you can match them against the bank statement on the other side."
faqs:
  - q: "Can I download PayPal activity as CSV?"
    a: "Yes. PayPal's activity report can be downloaded as CSV for any period in the last seven years, up to 12 months per report. Convert the PDF statements when that's what you've been given."
  - q: "Does this work for PayPal business accounts?"
    a: "Yes. Business statements can run long, and every page is converted, with headers and balance lines left out of your rows."
  - q: "Will the converted file import into QuickBooks?"
    a: "Download the CSV and use QuickBooks' bank-file import, mapping date, description, and amount."
  - q: "What about Venmo?"
    a: "Venmo statements already download as CSV, so you usually don't need a converter for them."
sources:
  - label: "PayPal Developer: Activity Download report (7 years, 12 months per report, formats)"
    url: "https://developer.paypal.com/docs/reports/online-reports/activity-download/"
  - label: "PayPal Help: How do I view and download statements and reports?"
    url: "https://www.paypal.com/us/cshelp/article/help145"
reviewed: 2026-11-24
---
