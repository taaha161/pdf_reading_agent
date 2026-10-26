---
name: "Chase"
shortName: "Chase"
slug: "chase-bank-statement-to-excel"
seoTitle: "Convert Chase Bank Statements to Excel or CSV"
description: "Convert Chase checking, savings, and credit card statement PDFs to Excel or CSV. Get every transaction, not just the last 90 days, with dates, descriptions, and amounts in clean columns."
country: "US"
statementTypes: ["Checking", "Savings", "Credit card", "Business checking"]
intro: "Chase gives you two ways to get your transactions out: the monthly PDF statement and an activity download. The activity download is quick, but it only reaches back a short way. For anything older, such as a full tax year, a loan application, or catch-up bookkeeping, the PDF statement is the record you have, and it needs converting before a spreadsheet or QuickBooks can use it."
exportLimits: "Chase's \"Download account activity\" option exports a spreadsheet file, but guides consistently report that it covers only roughly the last 90 days, and it is offered on desktop rather than in the Chase Mobile app. Monthly PDF statements go back much further (guides commonly cite about seven years) under Statements & documents. Older months are only available as PDFs."
downloadSteps:
  - "Sign in at chase.com on a desktop browser."
  - "Select the account, then open Statements & documents."
  - "Pick the statement month and click the download icon. The file saves as a PDF."
  - "Repeat for each month you need. Each statement is its own PDF, and you can upload several at once."
layoutNotes:
  - title: "Summary block above the transactions"
    body: "Checking statements open with beginning balance, deposits and additions, withdrawals, fees, and ending balance. These are totals, not transactions, so they're left out of your rows. They're still useful for checking your export afterwards."
  - title: "Dates without a year"
    body: "Transaction rows show the month and day (for example 04/15), and the year appears only in the statement period. Your export keeps dates as printed. If you combine a December and a January statement, add the year from each statement's period before sorting."
  - title: "Purchase dates inside descriptions"
    body: "Debit card lines often embed the purchase date in the description, as in \"DEBIT CARD PURCHASE 04/15 …\", while the row date is the posting date. Descriptions are kept exactly as printed, so you can still tell when a purchase was made from when it posted."
  - title: "Repeated headers on long statements"
    body: "Business statements can run many pages, and column headers repeat on each one. Header rows and opening and closing balance lines are excluded from your export. On your first upload, compare the row count with the statement to confirm nothing was split at a page break."
faqs:
  - q: "Can I download Chase statements directly as Excel?"
    a: "Only recent account activity can be downloaded as a spreadsheet, and guides report the window is about 90 days. Monthly statements download as PDF. To get older statements into Excel, download the PDFs and convert them."
  - q: "Does this work for Chase credit card statements?"
    a: "Yes. Upload the credit card statement PDF the same way. Purchases, payments, and credits are extracted into rows you can export to CSV or Excel."
  - q: "Can I convert a scanned or printed Chase statement?"
    a: "Yes. Scanned statements go through OCR. For best accuracy, use a clear scan at 300 DPI or higher, and pick the accurate mode for low-quality copies."
  - q: "How do I check the converted file is complete?"
    a: "Add up the deposits and withdrawals in your export and compare them with the totals in the summary block at the top of the statement. Opening balance plus deposits minus withdrawals should equal the ending balance."
sources:
  - label: "Digital Citizen: How to download Chase bank statements"
    url: "https://www.digitalcitizen.life/how-to-download-chase-bank-statements/"
  - label: "ImageToTable: Chase statement layout and export window"
    url: "https://imagetotable.ai/blog/convert-chase-bank-statement-to-excel"
relatedPost: "how-to-download-chase-bank-statements"
reviewed: 2026-10-26
---
