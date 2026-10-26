---
name: "Citibank"
shortName: "Citi"
slug: "citibank-statement-to-excel"
seoTitle: "Convert Citibank Statements to Excel or CSV"
description: "Convert Citi checking and credit card statement PDFs to Excel or CSV, including Citi credit card statements, which have no native CSV export."
country: "US"
statementTypes: ["Checking", "Savings", "Credit card", "Business"]
intro: "Citi statements change shape depending on the account: checking, Priority and Citigold relationship statements, credit cards, and business account analysis each lay out transactions differently. A converter that reads the statement, rather than a fixed template, handles all of them the same way."
exportLimits: "Citi's activity download is offered for checking and savings, but reports of its window vary from about 180 days to around two years. Guides also report that Citi credit card accounts don't offer a CSV download at all, so the PDF statement is often the only source for card transactions. Statements are under Statements & Documents."
downloadSteps:
  - "Sign in at citi.com."
  - "Open the account and go to Statements & Documents (statements may also be listed under the account's Statements tab)."
  - "Select the statement month and click the download icon to save the PDF."
  - "For older statements not shown online, contact Citi customer service."
layoutNotes:
  - title: "Relationship headers push the table down"
    body: "Priority and Citigold statements add a relationship summary above the transactions, so the table starts at a different spot from one statement to the next. Tools that rely on fixed positions break here. Reading the content avoids that."
  - title: "Debit and Credit columns on checking"
    body: "Checking statements show Debit and Credit in separate columns with a running balance. City and state often appear inside the description, and their commas are quoted properly in the CSV so your columns don't shift."
  - title: "Credit cards: rewards and rebates aren't spending"
    body: "Card statements include a rewards points summary and separate sections for purchases, payments, fees, and interest. Points are loyalty data, not money, and summary tables are excluded. Merchant rebates show up as credits. Categorize them as refunds, not income."
  - title: "Business balances live in a separate table"
    body: "Business account-analysis statements can list transactions without a balance column and put balances in their own table further down. The export doesn't include balances, so that table doesn't affect your rows. Check any fee-calculation lines before importing."
faqs:
  - q: "How do I get Citi credit card transactions into Excel?"
    a: "Guides report Citi credit cards have no CSV download. Download the monthly statement PDFs and convert them here to CSV or Excel."
  - q: "Does it handle Citigold and Citi Priority statements?"
    a: "Yes. Extraction reads the statement's content rather than fixed positions, so the relationship summary at the top doesn't throw off the transaction rows."
  - q: "My converted file has shifted columns in Excel. Why?"
    a: "Citi descriptions often contain commas (for example \"SEATTLE, WA\"). Our CSV quotes those fields so Excel keeps them in one column. If you copy-paste from the PDF instead, they tend to split."
  - q: "Is there a free option?"
    a: "Your first 5 statements are free, with no card required. After that, credits are used per statement."
sources:
  - label: "ImageToTable: Citibank statement layouts"
    url: "https://imagetotable.ai/blog/convert-citibank-statement-to-excel"
  - label: "Finaloop: Citibank CSV upload"
    url: "https://help.finaloop.com/en/articles/9268537-citibank-how-to-upload-your-csv-bank-statements"
  - label: "Quicken Community: Citibank transaction history"
    url: "https://community.quicken.com/discussion/comment/20194582"
reviewed: 2026-10-26
---
