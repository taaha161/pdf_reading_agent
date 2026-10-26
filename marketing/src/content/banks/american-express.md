---
name: "American Express"
shortName: "Amex"
slug: "amex-statement-to-excel"
seoTitle: "Convert Amex Statements to Excel or CSV"
description: "Convert American Express card statement PDFs to Excel or CSV, including archived statements and multi-cardmember accounts."
country: "US"
statementTypes: ["Personal card", "Business card"]
intro: "American Express offers several downloads, including recent activity, recent billing statements, and a longer transaction history. Each covers a different period, and none of them match a closed billing cycle exactly. When you need what the statement shows, such as for expense reports or a year of business card spending, converting the statement PDF keeps your rows aligned with the billing period."
exportLimits: "From Statements & Activity, Amex offers recent activity and recent billing statements in CSV, Excel, or accounting formats, plus a longer transaction history. How far back each goes depends on the account and region. Amex's own help pages for some regions list the past six statements as downloadable. Older statements can usually be requested as archived PDFs."
downloadSteps:
  - "Sign in to your American Express account."
  - "Open Statements & Activity for the card."
  - "Select the billing period and download the statement PDF. For older periods, request archived statements."
  - "Upload the PDFs here and export to CSV or Excel."
layoutNotes:
  - title: "Multiple cardmembers on one statement"
    body: "Statements with additional cards group charges under each cardmember's name. The export lists every charge in one table without a cardmember column. If you need totals per person, note which rows fall under each name on the statement."
  - title: "Credits and fees are kept separate"
    body: "Payments and refunds are credits and shouldn't be counted as spending. Fees and interest are listed separately from purchases. Keep them apart in your categories."
  - title: "Summary boxes aren't transactions"
    body: "The payment summary, rewards summary, and account overview boxes are left out of your rows."
  - title: "Activity downloads vs. the statement"
    body: "Recent-activity downloads can include charges that haven't closed into a statement yet. If you're reconciling, work from the statement PDF so your rows match the billing period."
faqs:
  - q: "Why convert the Amex PDF when Amex offers CSV?"
    a: "The CSV downloads cover set windows such as recent activity or recent statements, and they don't always match a closed billing cycle. Converting the statement PDF gives you exactly what the statement shows, including archived periods."
  - q: "Does it handle Amex business card statements?"
    a: "Yes. Business card statements, including ones with several employee cards, are supported."
  - q: "Are foreign currency charges kept?"
    a: "The billed amount shown on the statement is extracted. Any foreign-currency detail printed in the description stays in the description."
  - q: "Is my statement data used for advertising?"
    a: "No. We don't sell or share your financial data for advertising. Incognito mode converts a statement without saving it."
sources:
  - label: "American Express Australia: Download statements (official help)"
    url: "https://www.americanexpress.com/en-au/customer-service/payments-and-billings/faq.download-statements.html"
  - label: "Invoice Data Extraction: American Express statement to Excel"
    url: "https://invoicedataextraction.com/blog/american-express-statement-to-excel"
  - label: "DocuClipper: Convert Amex statements to Excel"
    url: "https://www.docuclipper.com/blog/convert-amex-bank-statement-to-excel/"
reviewed: 2026-10-26
---
