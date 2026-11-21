# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two primary audiences, weighted equally:

- **Small practices.** Bookkeepers, accountants and tax preparers at 1–10 person firms. They convert client bank and credit card statements in bursts (catch-up bookkeeping, month-end, tax season), not every day. They review the result before it goes into workpapers, QuickBooks or Xero.
- **Individuals and small business owners** who do their own books or taxes and need a statement in a spreadsheet.

Both arrive holding a PDF they would otherwise retype. Both are handing over a sensitive financial document, so trust is part of the task, not decoration.

## Product Purpose

Bank Statement Scanner turns bank and credit card statement PDFs (digital or scanned) into clean, categorized transactions in Excel or CSV. The user can then ask the statement questions in plain English and export exactly the rows they need.

Success: a statement goes from PDF to a checked, usable spreadsheet in minutes, with no retyping, and the user comes back next time they have a stack.

## Positioning

Four claims, all true today:

1. **Checked against the statement.** Every converted statement is checked against its own printed running balances and summary box (opening balance, total in, total out, closing balance). When the rows don't add up, the user sees how far off they are and which rows to look at (a line that may be missing, read twice, or on the wrong side). Saved statements for the same account are linked month to month, so a missing month or a balance that doesn't carry over stands out. This matches what MoneyThumb, DocuClipper and Bankstatemently offer, at our price.
2. **Ask your statement.** A chat over the extracted transactions that finds, totals and exports any subset ("every payment to John in March", "all ATM withdrawals"), downloaded as Excel or CSV.
3. **Fair billing.** Pay per page. No annual contract. Cancel anytime. This is the opposite of the lock-in and post-cancel charges that dominate complaints about the category leader (DocuClipper).
4. **Low-friction free tier.** 10 pages free without an account, 100 pages free in the first month after signup with no card, then $10/month for 100 pages, or one-off page packs.

## Operating Context

- Inputs are PDF statements from any US bank or card issuer: digital, scanned, password-protected, or phone photos saved as PDF.
- Work happens at a desk during a burst: a client sends a stack of PDFs, or a year of statements needs catching up. Mobile use is mostly first contact (an ad or search click), not production work.
- Outputs go into Excel workbooks, workpapers, or CSV imports into QuickBooks or Xero.
- Paid acquisition runs on LinkedIn (US, signup goal), with Google Search planned. Organic comes from per-bank `/convert/*` pages, `/compare/*` alternative pages, `/for/*` persona pages and a daily blog.

## Capabilities and Constraints

**Built:**
- Extraction from digital and scanned PDFs, including password-protected ones.
- Three conversion modes: Fast, Balanced, Accurate. Accurate costs 2 pages per PDF page.
- AI categorization of every row. Rows can be edited in the app.
- CSV and XLSX export.
- "Ask your statement" chat, with export of any subset it returns.
- Reconciliation on every statement: running balances and the printed summary box checked against the rows, with likely-cause hints and a Reconciliation sheet in Excel downloads. Statements that print no balances or totals are shown as "can't check", never as passed.
- Account timeline on the dashboard: saved statements grouped by account (last 4 digits) and linked month to month, flagging missing months and balances that don't carry over. Incognito and guest scans aren't saved, so they aren't in it.
- Import from Google Drive or a URL.
- Guests can email themselves the spreadsheet.
- Dashboard of past jobs. Saved data can be deleted per job.
- Incognito mode (signed-in users): the statement is processed without saving its data.
- Referral/affiliate program.

**Limits:**
- Upload size: 20 MB as a guest, 30 MB on a free account, 50 MB on Monthly. Enforced by the server; mirrored in `frontend/src/lib/fileSize.js` and `marketing/src/consts.ts`.
- PDF only. Image files are not accepted.

**Not built (never claim):**
- Matching bank rows against QuickBooks or Xero ledger entries. Reconciliation here means the statement checks above, not book-to-bank reconciliation.
- QBO, OFX or direct accounting-software sync. Export is CSV/XLSX only.
- Batch or multi-file upload.

**Terminology:**
- A "page" is one PDF page, the billing unit.
- "Statement" is the user's word. "Job" and "scan" are internal and should not appear in user-facing copy.

**Undecided:**
- What is disclosed on /security about retention for saved jobs, AI/OCR subprocessors, and model training. Pending vendor DPA answers.

**Stack:**
- Marketing site: Astro (`marketing/`).
- App: React/Vite (`frontend/`).
- API: FastAPI (`backend/`).
- Auth: Supabase. Payments: Stripe.
- Hosting: Vercel for both frontends, Render for the API.

## Brand Commitments

- Name: **Bank Statement Scanner**. Domain: bankstatementscanner.com.
- Existing logo asset: `frontend/src/assets/pdf_to_excel_logo.png`.
- Voice: plain, specific and honest. It names what the product does and doesn't do, as the `/compare` pages already do ("Not automatic yet").
- No unverifiable claims (user counts, hours saved, accuracy percentages) unless backed by real data.

## Evidence on Hand

- A real sample statement and its exports: `marketing/public/samples/` (PDF, CSV, XLSX), and `/scanner?sample=1`.
- A 22-second product demo video: `marketing/public/video/product-demo.mp4`, with poster.
- Bank logos: `marketing/public/logos/banks/`.
- Honest, specific competitor and bank-specific copy: `marketing/src/competitors.ts` and `marketing/src/content/banks/`.
- **The founder will appear on the site** (name, photo, short story). The details are not supplied yet; `FOUNDER` in `marketing/src/consts.ts` stays null until they are. Don't invent them.
- **Real usage numbers and named customer quotes** will be supplied by the owner. Until then, use none: no placeholder stats or testimonials.
- Stock avatar photos in `marketing/public/avatars/` are not evidence of customers and must not be used as social proof.

## Product Principles

1. **Never claim what the product doesn't do.** Trust is the product in a category that handles bank statements. One false claim costs more than any feature earns.
2. **Get the file in first.** The fastest path to value is a statement dropped in and a result on screen. Accounts, pricing and features come after the user has seen their own data.
3. **Show the ledger, not the pitch.** Real rows, real categories and real exports persuade a bookkeeper more than adjectives or numbers about other people.
4. **Privacy at the moment of upload.** Reassurance belongs where the document is handed over, not only on a security page.
5. **Billing that respects bursts.** Pricing and copy should make occasional, bursty use feel safe: no contracts, no surprise charges, clear page counts.
