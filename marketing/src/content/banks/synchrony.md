---
name: "Synchrony (Amazon Store Card and more)"
shortName: "Synchrony"
slug: "synchrony-amazon-card-statement-to-excel"
seoTitle: "Convert Synchrony and Amazon Store Card Statements to Excel"
description: "Convert Synchrony credit card statement PDFs, including the Amazon Store Card, to Excel or CSV. Every purchase, payment, and promotional-financing line in clean columns."
country: "US"
statementTypes: ["Store credit card", "Credit card"]
intro: "Synchrony issues store cards for Amazon and many other retailers, and getting their transactions into a spreadsheet is a long-running complaint. Users disagree about whether a CSV download exists for their card, and some people have written their own scripts to read the PDF statements. Converting the PDF statement works whatever your card's export options are."
exportLimits: "Tiller and Quicken community threads show conflicting reports. Some users can't find any CSV download for the Amazon Store Card, others show an export in Synchrony's activity menu, and Quicken users report Web Connect downloads stopped working. Monthly PDF statements are available in your Synchrony account either way."
downloadSteps:
  - "Sign in to your card account at synchrony.com (for Amazon cards, synchrony.com/amazon)."
  - "Open Statements."
  - "Choose the billing period and download the PDF."
  - "Upload the PDFs here to convert them to Excel or CSV."
layoutNotes:
  - title: "Promotional financing sections"
    body: "Deferred-interest and promotional purchases are summarized in their own section with expiration dates. Purchases are extracted as rows. Keep the PDF for the promotion details."
  - title: "Billing cycles, not calendar months"
    body: "Statements run from one closing date to the next. Sort by transaction date when you combine statements into calendar-month totals."
  - title: "Payments and credits"
    body: "Payments and returns are extracted with the opposite sign to purchases, so the totals match the statement."
faqs:
  - q: "Why can't I download my Amazon Store Card transactions?"
    a: "Community reports conflict on whether a CSV export is offered for every Synchrony card. The PDF statement is always available, so converting it is the reliable route."
  - q: "Does this work for other Synchrony store cards?"
    a: "Yes. Any Synchrony credit card statement PDF converts the same way."
  - q: "Can I pull out just my Amazon purchases in one category?"
    a: "Yes. Ask your statement in plain English, for example 'all purchases over $100 in March', and export just those rows."
  - q: "Can I import the result into Tiller or a budget sheet?"
    a: "Yes. Download the CSV and import it, or copy the rows from the Excel file."
sources:
  - label: "Tiller Community: Amazon Synchrony Card CSV import"
    url: "https://community.tiller.com/t/amazon-synchrony-card-csv-import/8710"
  - label: "Quicken Community: Synchrony Bank Amazon Card"
    url: "https://community.quicken.com/discussion/7912548/synchrony-bank-amazon-card"
  - label: "Synchrony: Manage your Prime or Amazon cards"
    url: "https://www.synchrony.com/amazon"
reviewed: 2026-11-22
---
