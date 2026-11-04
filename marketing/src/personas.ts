/** Persona landing pages (/for/<slug>). */
import { FREE_STATEMENTS } from './consts';

export type Persona = {
  slug: string;
  name: string;
  seoTitle: string;
  description: string;
  eyebrow: string;
  h1: string;
  sub: string;
  pains: { old: string; new: string }[];
  guide: string;
  faqs: { q: string; a: string }[];
};

export const PERSONAS: Persona[] = [
  {
    slug: 'accountants',
    name: 'Accountants',
    seoTitle: 'Bank Statement Converter for Accountants and CPA Firms',
    description:
      'Convert client bank statement PDFs into clean, categorized Excel or CSV files in seconds. Built for accountants and CPA firms. 3 statements free.',
    eyebrow: 'For accountants and CPA firms',
    h1: 'Spend tax season on advice, not retyping client statements.',
    sub: 'Upload a client’s bank or credit card statement. Get every transaction back in clean, categorized columns, checked against the statement’s balances, ready for your workpapers or QuickBooks.',
    pains: [
      { old: 'Clients send a stack of PDFs instead of a bank feed', new: 'Turn each PDF into rows in seconds' },
      { old: 'Staff hours lost to keying dates and amounts', new: 'Every transaction extracted and categorized' },
      { old: 'A typo throws off the reconciliation', new: 'Opening + credits − debits checked against closing' },
      { old: 'Scanned paper statements from older years', new: 'Scans and photos go through OCR' },
    ],
    guide: 'bank-statement-scanner-for-accountants',
    faqs: [
      {
        q: 'Can I use it for client statements from different banks?',
        a: 'Yes. Upload statements from Chase, Wells Fargo, Amex, Bank of America and 100+ other banks and card issuers, including scanned PDFs.',
      },
      {
        q: 'Does the export work with QuickBooks or Xero?',
        a: 'Yes. Download a CSV to import into QuickBooks, Xero or other accounting tools, or an Excel file for review and workpapers.',
      },
      {
        q: 'How do I keep client data private?',
        a: 'Uploads are encrypted in transit, and incognito mode converts a statement without keeping the file or its data after your session. Saved jobs stay until you delete them.',
      },
      {
        q: 'How is it priced for a practice?',
        a: `Your first ${FREE_STATEMENTS} statements are free. After that, $10 a month adds $10 of scan credit, about 10 statements on Balanced mode. Top up in busy months. Monthly billing, no annual contract.`,
      },
    ],
  },
  {
    slug: 'bookkeepers',
    name: 'Bookkeepers',
    seoTitle: 'Bank Statement to Excel and CSV for Bookkeepers',
    description:
      'Turn client bank statement PDFs into categorized spreadsheets ready for QuickBooks or Xero. Built for bookkeepers catching up or closing the month. 3 statements free.',
    eyebrow: 'For bookkeepers',
    h1: 'Catch-up bookkeeping without retyping a single statement.',
    sub: 'Upload the PDF. Get a categorized spreadsheet ready for QuickBooks or Xero in seconds, with balances checked against the statement so nothing slips through.',
    pains: [
      { old: 'Bank feeds only reach back a few months', new: 'Convert PDF statements from any year' },
      { old: 'Copy-paste from PDFs breaks the columns', new: 'Clean date, description, amount and type columns' },
      { old: 'Categorizing hundreds of rows by hand', new: 'Every row categorized automatically' },
      { old: 'Finding the one missing transaction', new: 'Balance check shows when something is off' },
    ],
    guide: 'automate-monthly-bookkeeping-data-entry',
    faqs: [
      {
        q: 'Can I convert old statements for catch-up work?',
        a: 'Yes. Bank downloads often cover only recent months, but PDF statements go back years. Upload each PDF and export the rows.',
      },
      {
        q: 'What columns does the export have?',
        a: 'Date, description, amount, type (credit or debit) and category. Open the sample export on this page to see a real file.',
      },
      {
        q: 'Does it work with scanned statements?',
        a: 'Yes. Scanned PDFs and photos go through OCR. For low-quality copies, pick Accurate mode.',
      },
      {
        q: 'What does it cost?',
        a: `Your first ${FREE_STATEMENTS} statements are free. Then $10 a month adds $10 of scan credit, about 10 statements on Balanced mode. Monthly, cancel anytime.`,
      },
    ],
  },
];
