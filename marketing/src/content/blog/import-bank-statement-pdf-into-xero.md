---
converter: true
title: "How to Import a Bank Statement PDF into Xero (Step by Step)"
seoTitle: "Import Bank Statement PDF into Xero"
excerpt: "Xero imports CSV, OFX and QIF statements, not PDFs. Here's how to turn a PDF into a Xero-ready CSV, import it, and avoid date, sign and duplicate problems."
date: 2026-11-25
category: "Guides"
readTime: "7 min read"
image: "/blog/images/import-bank-statement-pdf-into-xero.jpg"
keyword: "import bank statement pdf into xero"
tags: ["xero", "bank statement import", "pdf to csv", "bookkeeping"]
---

Xero's bank feeds cover most months, but not all of them. A feed that starts after the period you need, a bank with no feed, a few days the feed dropped, or a new client with a year of history: each one leaves you holding PDF statements. Xero won't read those PDFs. Its **Import a statement** tool takes CSV, OFX and QIF files.

So the job is always the same: **PDF → Xero-ready CSV → import → reconcile.** Here's how to do each step without the import failing or the statement balance drifting.

## What a Xero statement CSV needs

Xero's statement import maps a small set of columns. A file that imports on the first try has:

- **Date.** One format for the whole file, matching your organisation's region: DD/MM/YYYY for UK, Australian and New Zealand organisations, MM/DD/YYYY for US ones. "Jan 5" or "05 Jan" with no year won't import.
- **Amount.** One signed column: money in positive, money out negative. Separate Debit and Credit columns have to be merged first.
- **Payee.** Usually the statement description. Xero's bank rules match on it, so filling it in saves coding time later.
- **Description and Reference.** Optional. Leave them blank or use them for your own notes.
- **Nothing else.** No balance column, no opening or closing balance rows, no page totals. Those import as statement lines and throw off the balance Xero shows for the statement.

## Step 1: Convert the PDF to a Xero CSV

Upload the statement to [Bank Statement Scanner](/bank-statement-to-xero). It reads digital, scanned and password-protected PDFs and pulls out every transaction. Before you download, check the result:

- The app checks the rows against the statement's printed running balances and summary box. A statement marked as reconciled has every row accounted for.
- If it flags a mismatch, it points to the row that's missing, doubled or on the wrong side. Fix it there, not after it's in Xero.

Then open **Download** and choose **Xero**. You get a CSV with Date, Amount, Payee, Description and Reference columns, signed amounts, and every date rewritten to one full format with the year filled in.

Backfilling a whole year? [Bulk upload](/bulk-bank-statement-converter) converts up to 50 statements at once, and the Xero download puts every line into one file in date order.

## Step 2: Import the statement in Xero

1. Go to **Accounting → Bank accounts** and open the account the statement belongs to. For a card statement, open the credit card account.
2. Click **Manage account**, then **Import a statement**.
3. Browse to the CSV and click **Import**.
4. Check the column mapping: Date to Transaction Date, Amount to Transaction Amount, Payee to Payee. Save it so next month's file maps itself.
5. Complete the import. The lines appear on the account's **Reconcile** tab.

## Step 3: Reconcile and check the balance

Reconcile the new lines the usual way, with bank rules or by matching existing invoices and bills. Then check one number: the closing balance on the PDF should match the statement balance Xero shows for that date. If it doesn't, the usual causes are:

- **A month imported twice.** Overlapping files, or dates the bank feed already covered. Delete the duplicate statement lines.
- **A row with the wrong sign.** A refund read as a payment, or a fee read as a deposit.
- **A missing row.** Usually where a page break split a transaction.

Checking the conversion against the statement's own balances before you import catches the last two before they reach Xero.

## Common Xero import errors

- **Dates that won't read.** The file mixes formats, or uses month-first dates in a day-first organisation. Use one format that matches your region.
- **Amounts with currency symbols or commas.** "$1,200.00" can fail to import. The amount should be a plain number like 1200.00.
- **Extra rows.** Headers repeated on every page, "Balance brought forward" lines and totals all import as transactions. Remove them.
- **Weekday in the date.** Some banks print "Mon 05 Jan". Xero needs the date on its own.

The Xero export from Bank Statement Scanner handles all four for you. If you also work in QuickBooks, the same statement downloads as a [QuickBooks Online CSV](/bank-statement-to-quickbooks).

## Frequently asked questions

### Can Xero import a PDF bank statement?

No. Xero's Import a statement tool takes CSV, OFX and QIF files. Convert the PDF to a CSV first, then import it into the bank account in Xero.

### What date format does Xero need for a statement import?

The format your Xero organisation's region uses: DD/MM/YYYY for UK, Australia and New Zealand, MM/DD/YYYY for the US. Use one format for every row.

### Should the Amount column be signed?

Yes. Use one Amount column with money in as positive and money out as negative. Separate Debit and Credit columns need to be combined first.

### Will importing a statement duplicate my bank feed?

It can, if the statement covers dates the feed already imported. Import only the dates the feed is missing, and delete any duplicate statement lines before you reconcile.

### Does Bank Statement Scanner connect to Xero directly?

No. You download the Xero CSV and import it yourself, so nothing is posted to your Xero organisation without you.

## Sources

- [Wikipedia: Xero (software)](https://en.wikipedia.org/wiki/Xero_(software))
- [Wikipedia: Bank reconciliation](https://en.wikipedia.org/wiki/Bank_reconciliation)
- [Wikipedia: Comma-separated values](https://en.wikipedia.org/wiki/Comma-separated_values)
