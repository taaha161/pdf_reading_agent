/** Persona landing pages (/for/<slug>). */
import { FREE_LABEL, PRICING_SUMMARY } from './consts';

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
      'Convert client bank statement PDFs into clean, categorized Excel or CSV files in seconds. Built for accountants and CPA firms. 100 pages free your first month.',
    eyebrow: 'For accountants and CPA firms',
    h1: 'Spend tax season on advice, not retyping client statements.',
    sub: 'Upload a client’s bank or credit card statement. Get every transaction back in clean, categorized columns, ready for your workpapers or QuickBooks.',
    pains: [
      { old: 'Clients send a stack of PDFs instead of a bank feed', new: 'Turn each PDF into rows in seconds' },
      { old: 'Staff hours lost to keying dates and amounts', new: 'Every transaction extracted and categorized' },
      { old: 'Hunting a statement for every payment to one payee', new: 'Ask for them in plain English and export just those rows' },
      { old: 'Scanned paper statements from older years', new: 'Scanned PDFs go through OCR' },
      { old: 'Ticking totals back to the statement before review', new: 'Every statement checked against its printed balances and summary' },
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
        a: PRICING_SUMMARY,
      },
    ],
  },
  {
    slug: 'bookkeepers',
    name: 'Bookkeepers',
    seoTitle: 'Bank Statement to Excel and CSV for Bookkeepers',
    description:
      'Turn client bank statement PDFs into categorized spreadsheets ready for QuickBooks or Xero. Built for bookkeepers catching up or closing the month. 100 pages free your first month.',
    eyebrow: 'For bookkeepers',
    h1: 'Catch-up bookkeeping without retyping a single statement.',
    sub: 'Upload the PDF. Get a categorized spreadsheet ready for QuickBooks or Xero in seconds, so you review a finished file instead of typing one.',
    pains: [
      { old: 'Bank feeds only reach back a few months', new: 'Convert PDF statements from any year' },
      { old: 'Copy-paste from PDFs breaks the columns', new: 'Clean date, description, amount and type columns' },
      { old: 'Categorizing hundreds of rows by hand', new: 'Every row categorized automatically' },
      { old: 'Pulling every charge from one vendor', new: 'Ask for them in plain English and export just those rows' },
      { old: 'Finding the missing month in a catch-up stack', new: 'Saved statements linked month to month, so gaps stand out' },
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
        a: 'Yes. Scanned PDFs go through OCR. For low-quality copies, pick Accurate mode. Phone photos work once saved as a PDF.',
      },
      {
        q: 'What does it cost?',
        a: PRICING_SUMMARY,
      },
    ],
  },
];
