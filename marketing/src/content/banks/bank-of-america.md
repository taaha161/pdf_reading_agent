---
name: "Bank of America"
shortName: "Bank of America"
slug: "bank-of-america-statement-to-excel"
seoTitle: "Convert Bank of America Statements to Excel or CSV"
description: "Turn Bank of America checking, savings, and credit card statement PDFs into Excel or CSV, with running balances and statement periods the activity download leaves out."
country: "US"
statementTypes: ["Checking", "Savings", "Credit card", "Business"]
intro: "Bank of America lets you download transaction activity, but that file isn't the statement. It leaves out the running balance and the period totals, and it only covers a recent window. When you need the official record, for reconciliation, an audit, or a lender, you work from the PDF statement."
exportLimits: "Several guides put the Online Banking activity download at about 18 months of history for most checking and savings accounts, and note that it includes transaction rows only, without running balances, statement totals, or the account summary. Statements under Statements & Documents are PDF only."
downloadSteps:
  - "Sign in to Bank of America Online Banking."
  - "Open the account and go to Statements & Documents."
  - "Choose the statement period and download the PDF."
  - "For business accounts in CashPro, statements and reports are under the reporting section. Download the statement PDFs for the months you need."
layoutNotes:
  - title: "Separate deposit and withdrawal columns"
    body: "Money in and money out sit in adjacent columns rather than one signed amount, so each row has a blank cell on one side. Your export has an amount column plus a type column marked credit or debit, taken from the column the amount was printed in."
  - title: "Long, packed descriptors"
    body: "Card, ACH, and wire lines pack the transaction type, date code, merchant, store number, location, and reference into one string, and they often wrap onto a second line. Extraction reads the statement table as a whole rather than line by line, which keeps wrapped text with its transaction."
  - title: "Transactions split across pages"
    body: "A transaction near the bottom of a page can continue at the top of the next. Generic PDF-to-Excel tools often drop or duplicate these rows. On your first upload, compare the row count with the statement."
  - title: "Running balance moves around"
    body: "Where a running balance is printed, its position shifts by transaction type, which throws off tools that read fixed column positions. The export leaves balances out. Use the statement's ending balance to check your totals."
faqs:
  - q: "Why not use the Bank of America CSV download?"
    a: "It works for recent activity, but guides report it reaches back about 18 months and leaves out running balances and statement totals. For older periods, or a statement-accurate record, convert the PDF statements."
  - q: "Can I convert several months at once?"
    a: "Yes. Upload multiple Bank of America statement PDFs together and export each one to CSV or Excel."
  - q: "Does it work with Bank of America business statements?"
    a: "Yes. Business statement PDFs, including longer multi-page statements, are supported. Use accurate mode for scanned copies."
  - q: "Is my Bank of America statement stored?"
    a: "Use incognito mode to convert without saving anything to your account. Otherwise saved jobs stay until you delete them. See our Security page for details."
sources:
  - label: "Invoice Data Extraction: Bank of America statement to Excel"
    url: "https://invoicedataextraction.com/blog/bank-of-america-statement-to-excel"
  - label: "The Bricks: Downloading Bank of America statements in Excel"
    url: "https://www.thebricks.com/resources/how-to-download-bank-of-america-statements-in-excel"
  - label: "Finaloop: Bank of America CSV upload"
    url: "https://help.finaloop.com/en/articles/9306344-bank-of-america-how-to-upload-your-csv-bank-statements"
reviewed: 2026-10-26
---
