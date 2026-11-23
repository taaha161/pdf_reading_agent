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
{
    slug: 'tax-preparers',
    name: 'Tax preparers',
    seoTitle: 'Bank Statement Converter for Tax Preparers',
    description:
      'Turn client bank and credit card statement PDFs into categorized Excel or CSV files for Schedule C and tax workpapers. Built for tax season bursts. 100 pages free your first month.',
    eyebrow: 'For tax preparers',
    h1: 'A year of client statements, sorted by category before you open the return.',
    sub: 'Clients hand you twelve PDFs and a shoebox. Upload the statements and get every transaction back categorized, so you total expenses instead of typing them.',
    pains: [
      { old: 'Twelve monthly PDFs per account, per client', new: 'Convert each statement in seconds and combine the rows' },
      { old: 'Adding up expense categories with a calculator', new: 'Every row categorized, ready for a pivot table' },
      { old: 'Hunting for one deductible payee across a year', new: 'Ask "every payment to the landlord in 2026" and export just those rows' },
      { old: 'Not sure the conversion caught every row', new: 'Every statement checked against its printed balances and totals' },
      { old: 'Paying for a tool all year that you need for three months', new: 'Pay per page, no annual contract, cancel anytime' },
    ],
    guide: 'tax-season-checklist-bank-statements',
    faqs: [
      {
        q: 'Can I use it for Schedule C expense totals?',
        a: 'Yes. Every transaction gets a category you can edit. Export to Excel and build a pivot table by category to total expenses for the return. Review the categories before you rely on them.',
      },
      {
        q: 'Does it handle credit card statements too?',
        a: 'Yes. Bank and credit card statements from Chase, Amex, Capital One, Discover and other US issuers convert the same way, including scanned PDFs.',
      },
      {
        q: 'How do I keep client data private?',
        a: 'Uploads are encrypted in transit, and incognito mode converts a statement without saving its data. Saved statements stay until you delete them.',
      },
      {
        q: 'How does pricing work in tax season?',
        a: PRICING_SUMMARY,
      },
    ],
  },
  {
    slug: 'small-business-owners',
    name: 'Small business owners',
    seoTitle: 'Bank Statement to Excel for Small Business Owners',
    description:
      'Convert business bank and credit card statement PDFs into categorized Excel or CSV files for your books, your accountant, or a loan application. 10 pages free with no account.',
    eyebrow: 'For small business owners',
    h1: 'Your business statements in a spreadsheet, without the weekend of data entry.',
    sub: 'Upload a business checking or credit card statement. Get every transaction back in clean, categorized columns to import into QuickBooks or Xero, or hand to your accountant.',
    pains: [
      { old: 'Behind on the books and the bank feed only reaches back a few months', new: 'Convert PDF statements from any month you can download' },
      { old: 'Sorting personal from business spending by hand', new: 'Every row categorized, so you filter instead of scan' },
      { old: 'Finding every payment to one supplier', new: 'Ask in plain English and export just those rows' },
      { old: 'Your accountant asks for spreadsheets, you have PDFs', new: 'Excel and CSV exports ready to send' },
      { old: 'Software subscriptions you use twice a year', new: 'Pay per page, no contract, cancel anytime' },
    ],
    guide: 'bank-statement-scanner-for-small-businesses',
    faqs: [
      {
        q: 'Can I import the export into QuickBooks or Xero?',
        a: 'Yes. Download a CSV and use the bank-file import in QuickBooks Online or Xero. Export is CSV or Excel; there is no direct sync.',
      },
      {
        q: 'Does it work for business statements with many pages?',
        a: 'Yes. Long statements are converted page by page, with repeated headers and balance lines left out, and the rows are checked against the statement totals.',
      },
      {
        q: 'Can I try it without signing up?',
        a: 'Yes. Convert up to 10 pages without an account. Sign up for 100 free pages in your first month, no card needed.',
      },
      {
        q: 'What does it cost after that?',
        a: PRICING_SUMMARY,
      },
    ],
  },
  {
    slug: 'real-estate',
    name: 'Real estate agents and property managers',
    seoTitle: 'Bank Statement Analysis for Real Estate Agents and Property Managers',
    description:
      'Turn buyer, borrower and tenant bank statement PDFs into clean spreadsheets. Total deposits, spot large transfers and check rent against income in minutes. 100 pages free your first month.',
    eyebrow: 'For real estate agents, brokers and property managers',
    h1: 'Read a client’s bank statements in minutes, not an afternoon.',
    sub: 'Buyers, borrowers and tenants send you months of PDF statements. Upload them and get every transaction in a spreadsheet, with money in and out totaled and the statement checked against its own balances.',
    pains: [
      { old: 'Three months of PDFs from every buyer or applicant', new: 'Each statement converted to rows in seconds' },
      { old: 'Adding up deposits with a calculator to estimate income', new: 'Money in and money out totaled for every statement' },
      { old: 'Scrolling for the large deposit the lender will ask about', new: 'Ask "deposits over $1,000" and export just those rows' },
      { old: 'Not sure a statement adds up or a month is missing', new: 'Each statement checked against its printed balances, months linked in order' },
      { old: 'Client financial data sitting in your inbox and downloads', new: 'Incognito mode converts a statement without saving it' },
    ],
    guide: '',
    faqs: [
      {
        q: 'How do agents and property managers use it?',
        a: 'Common uses are checking that a buyer has the down payment and reserves before submitting an offer, screening rental applicants by comparing their deposits to the rent, preparing proof of funds for cash offers, and keeping commission income organized for taxes.',
      },
      {
        q: 'Can it total a tenant’s or borrower’s monthly deposits?',
        a: 'Yes. Every converted statement shows total money in and money out. Export to Excel to average deposits across several months, or ask in chat for every deposit over an amount and export just those rows.',
      },
      {
        q: 'Does this replace lender income verification?',
        a: 'No. It turns statements into spreadsheets so you can review them faster. Lenders and screening services still make their own decisions, and you should only handle statements your clients have shared with you for that purpose.',
      },
      {
        q: 'How is client data protected?',
        a: 'Uploads are encrypted in transit and the original PDF is not kept after processing. Incognito mode converts a statement without saving its data. Saved statements stay until you delete them.',
      },
      {
        q: 'What does it cost?',
        a: PRICING_SUMMARY,
      },
    ],
  },
];
