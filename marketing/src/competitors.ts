/**
 * Data for /compare/[slug] pages, rendered by components/ComparePage.astro.
 *
 * Rules: every claim about another product comes from that product's own site
 * (listed in `sources`) and is dated by `checked`. Say where they win, too.
 * Re-check prices before editing `checked`.
 */

export type CompareCategory =
  | 'Statement converters'
  | 'Desktop & PDF tools'
  | 'Document AI & parsers'
  | 'Accounting data capture'
  | 'General AI';

interface Row { label: string; us: string; them: string }
interface Section { heading: string; paras?: string[]; bullets?: string[] }

export interface Competitor {
  slug: string;
  category: CompareCategory;
  /** One line for the /compare card. */
  card: string;
  seoTitle: string;
  description: string;
  crumb: string;
  eyebrow: string;
  h1: string;
  intro: string[];
  themName: string;
  rows: Row[];
  tableNote?: string;
  sections: Section[];
  fit: { us: string[]; them: string[] };
  faqs: { q: string; a: string }[];
  sources: { label: string; url: string }[];
  checked: string;
}

// Our side of the table, kept in one place so every page says the same thing.
const US = {
  price: '$10/month, added to your account as $10 of credit',
  perStatement: 'Per statement: fast mode under 1¢, balanced $1, accurate $1.50',
  free: '3 statements free, no card',
  exports: 'CSV, Excel (XLSX)',
  scanned: 'Yes, with an accurate mode for poor scans',
  balance: 'Not automatic yet. Compare totals with the statement yourself',
  data: 'Incognito mode stores no transaction data; payments through Stripe',
  setup: 'None. Upload a statement and review the rows',
};

const QB_FAQ = {
  q: 'Can I get my transactions into QuickBooks or Xero?',
  a: 'Export to CSV and use the bank-statement import in QuickBooks or Xero. Direct QBO and Xero export isn’t available yet.',
};
const TRIAL_FAQ = {
  q: 'Can I try Bank Statement Scanner before paying?',
  a: 'Yes. Your first 3 statements are free, and you don’t need a credit card.',
};

const CHECKED = '2026-11-08';

export const competitors: Competitor[] = [
  // ───────────── Statement converters ─────────────
  {
    slug: 'bankconvert-alternative',
    category: 'Statement converters',
    card: 'No free plan and a $49 monthly entry price, vs $10 of credit and 3 free statements.',
    seoTitle: 'BankConvert Alternative: Bank Statement Scanner vs BankConvert',
    description: 'Comparing Bank Statement Scanner and BankConvert on pricing, free use, exports, and data handling. Start with 3 free statements, then $10 a month.',
    crumb: 'BankConvert alternative',
    eyebrow: 'BankConvert alternative',
    h1: 'Bank Statement Scanner vs BankConvert',
    intro: [
      'BankConvert is a full-featured converter with many export formats and plans that scale to thousands of statements a month. It has no free plan, and its entry plan is $49 a month on monthly billing.',
      'Bank Statement Scanner starts with 3 free statements and then costs $10 a month in credit, used per statement. Here’s how the two compare, including where BankConvert is the better pick.',
    ],
    themName: 'BankConvert',
    rows: [
      { label: 'Starting price', us: US.price, them: 'Starter $49/month monthly, or $24/month billed annually ($288/yr)' },
      { label: 'What you get', us: US.perStatement, them: 'Starter: 50 statements and 90 scanned pages a month' },
      { label: 'Free use', us: US.free, them: 'No free plan' },
      { label: 'Export formats', us: US.exports, them: 'CSV, Excel, OFX, QFX, QBO, QIF, JSON' },
      { label: 'Scanned statements', us: US.scanned, them: 'Yes, counted by page with a daily cap (30 pages/day on Starter)' },
      { label: 'Teams and API', us: 'Single user', them: 'Business plan adds 5 seats, a team workspace, and API access' },
      { label: 'Data', us: US.data, them: 'Files encrypted in transit and at rest, discarded after conversion' },
    ],
    tableNote: 'BankConvert prices are from its pricing page in USD and may have changed.',
    sections: [
      {
        heading: 'The cost of a few statements',
        paras: [
          'If you convert five statements this month, BankConvert’s cheapest monthly option is $49. On Bank Statement Scanner, five statements in balanced mode use $5 of your $10 credit, and fast mode costs less than a cent each.',
          'At high volume the picture changes. BankConvert’s Pro plan covers 300 statements a month, and if you convert that many every month, a page plan can work out cheaper.',
        ],
      },
    ],
    fit: {
      us: ['You convert statements occasionally', 'You want to try it free first', 'CSV or Excel is all you need', 'You want an incognito mode that saves nothing'],
      them: ['You need QBO, OFX, QFX, or QIF files', 'You convert hundreds of statements every month', 'Your team needs shared seats or an API', 'You want month-to-month plans with high limits'],
    },
    faqs: [
      { q: 'Does BankConvert have a free plan?', a: 'Its pricing page says there is no free plan. Bank Statement Scanner gives you 3 statements free with no card.' },
      { q: 'Which is cheaper?', a: 'For a handful of statements a month, Bank Statement Scanner. For hundreds a month every month, BankConvert’s larger plans may cost less per statement.' },
      QB_FAQ,
    ],
    sources: [{ label: 'BankConvert pricing', url: 'https://www.bankconvert.com/pricing' }],
    checked: CHECKED,
  },
  {
    slug: 'bankstatemently-alternative',
    category: 'Statement converters',
    card: 'Page-based plans with QBO and Xero export, vs per-statement credit with no page counting.',
    seoTitle: 'Bankstatemently Alternative: Bank Statement Scanner vs Bankstatemently',
    description: 'Bank Statement Scanner vs Bankstatemently: page limits, free use, exports, and checks compared. Convert per statement with 3 free to start.',
    crumb: 'Bankstatemently alternative',
    eyebrow: 'Bankstatemently alternative',
    h1: 'Bank Statement Scanner vs Bankstatemently',
    intro: [
      'Bankstatemently sells plans by the page, with a free tier of 10 pages a month, QBO and Xero exports, and a balance-to-balance check across statements. It’s a strong tool, especially for bookkeepers who import into accounting software.',
      'Bank Statement Scanner charges per statement instead of per page, so a long statement costs the same as a short one. Here’s the comparison.',
    ],
    themName: 'Bankstatemently',
    rows: [
      { label: 'How you pay', us: US.perStatement, them: 'By page: Beginner 400 pages/month, Pro 1,000 pages/month, or a one-time 50-page pack valid 30 days' },
      { label: 'Free use', us: US.free, them: '10 pages a month (max 5 a day), no card' },
      { label: 'Export formats', us: US.exports, them: 'CSV, Excel, QBO, Xero, JSON via API' },
      { label: 'Balance check', us: US.balance, them: 'Chains statements balance to balance, so a missing month shows as a gap' },
      { label: 'Integrations', us: 'None', them: 'API, MCP server, and use inside ChatGPT or Claude' },
      { label: 'Data', us: US.data, them: 'Encrypted in transit and at rest; GDPR compliant; data not sold' },
    ],
    tableNote: 'Bankstatemently doesn’t show plan prices in its page text; check its pricing page for current amounts.',
    sections: [
      {
        heading: 'Pages vs statements',
        paras: [
          'A busy business account can run 10 to 20 pages a month. On a page plan, a year of statements for one account can use a few hundred pages. On Bank Statement Scanner, that same year is 12 statements, whatever their length.',
          'If your statements are short and you need QBO or Xero files, Bankstatemently’s page plans may suit you better.',
        ],
      },
    ],
    fit: {
      us: ['Your statements are long', 'You only need CSV or Excel', 'You want to pay for what you use, not a page allowance', 'You want an incognito mode that saves nothing'],
      them: ['You need QBO or Xero import files', 'You want an automatic balance check across months', 'You want an API or MCP integration', 'Your statements are only a few pages each'],
    },
    faqs: [
      { q: 'Is Bankstatemently free?', a: 'It has a free tier of 10 pages a month, up to 5 a day. Bank Statement Scanner gives you 3 full statements free.' },
      { q: 'Does Bank Statement Scanner count pages?', a: 'No. You pay per statement, from under 1¢ in fast mode to $1.50 in accurate mode.' },
      QB_FAQ,
    ],
    sources: [
      { label: 'Bankstatemently pricing', url: 'https://bankstatemently.com/pricing' },
      { label: 'Bankstatemently homepage', url: 'https://bankstatemently.com/' },
    ],
    checked: CHECKED,
  },
  {
    slug: 'moneythumb-alternative',
    category: 'Statement converters',
    card: 'SOC 2 desktop and server converters from $599.95/yr, vs a $10/month browser tool.',
    seoTitle: 'MoneyThumb Alternative: Bank Statement Scanner vs MoneyThumb',
    description: 'Comparing Bank Statement Scanner and MoneyThumb on price, reconciliation, exports, and setup. Convert in your browser from $10 a month, 3 statements free.',
    crumb: 'MoneyThumb alternative',
    eyebrow: 'MoneyThumb alternative',
    h1: 'Bank Statement Scanner vs MoneyThumb',
    intro: [
      'MoneyThumb has been converting statements for years. It offers desktop converters (2qfx Convert) and online platform plans with reconciliation against the statement summary, SOC 2 Type II, and QuickBooks formats like QBO and QFX.',
      'That depth comes at a price: platform plans start at $599.95 a year and trials go through MoneyThumb’s team. Bank Statement Scanner runs in your browser and starts at $10 a month after 3 free statements.',
    ],
    themName: 'MoneyThumb',
    rows: [
      { label: 'Starting price', us: US.price, them: 'Platform plans from $599.95/year; desktop licenses priced separately' },
      { label: 'How you pay', us: US.perStatement, them: 'Bundles of conversions; one conversion is one monthly statement' },
      { label: 'Free use', us: US.free, them: 'Free trial on request through MoneyThumb' },
      { label: 'Export formats', us: US.exports, them: 'QBO, OFX, QFX, QIF, CSV, Excel, JSON/API' },
      { label: 'Reconciliation', us: US.balance, them: 'Reconciles transactions against the account summary' },
      { label: 'Runs', us: 'In the browser, nothing to install', them: 'Online platform or desktop software (some editions Windows-only)' },
      { label: 'Security', us: US.data, them: 'SOC 2 Type II; report available under NDA' },
    ],
    tableNote: 'MoneyThumb prices are from its pricing page in USD and may have changed.',
    sections: [
      {
        heading: 'Where MoneyThumb is stronger',
        bullets: [
          'Automatic reconciliation against the statement’s printed summary.',
          'Direct QuickBooks, Quicken, and OFX formats.',
          'SOC 2 Type II, which some firms require from vendors.',
          'Repeat conversions of the same document are free, and statements with fewer than 5 transactions aren’t charged.',
        ],
      },
    ],
    fit: {
      us: ['You want to start today without a sales call', 'You convert a few statements a month', 'CSV or Excel is enough', 'You don’t want to install software'],
      them: ['You need QBO, QFX, or QIF files', 'You need SOC 2 Type II from vendors', 'You want automatic reconciliation', 'You process statements at volume and want an API'],
    },
    faqs: [
      { q: 'How much does MoneyThumb cost?', a: 'Its platform plans start at $599.95 a year. Desktop license prices aren’t listed on the same page.' },
      { q: 'Is there a MoneyThumb free trial?', a: 'Yes, but you contact MoneyThumb to set it up. Bank Statement Scanner’s 3 free statements need no card or call.' },
      QB_FAQ,
    ],
    sources: [{ label: 'MoneyThumb pricing', url: 'https://www.moneythumb.com/pricing' }],
    checked: CHECKED,
  },
  {
    slug: 'rocket-statements-alternative',
    category: 'Statement converters',
    card: 'Yearly page allowances with team portals, vs pay-per-statement with no plan to pick.',
    seoTitle: 'Rocket Statements Alternative: Bank Statement Scanner vs Rocket Statements',
    description: 'Bank Statement Scanner vs Rocket Statements: pricing, page limits, exports, and team features compared. 3 statements free, then $10 a month.',
    crumb: 'Rocket Statements alternative',
    eyebrow: 'Rocket Statements alternative',
    h1: 'Bank Statement Scanner vs Rocket Statements',
    intro: [
      'Rocket Statements sells page allowances from $8 a month on yearly billing, with Google Sheets and Excel add-ins, bank sync, and client portals on higher plans. It’s built for firms and teams.',
      'Bank Statement Scanner is simpler: one $10 monthly credit, used per statement, with no page allowance to track. Here’s how they compare.',
    ],
    themName: 'Rocket Statements',
    rows: [
      { label: 'Starting price', us: US.price, them: 'Basic from $8/month billed yearly or $15 monthly, 1,200 pages a year' },
      { label: 'Free use', us: US.free, them: '7-day trial with 20 pages, no card' },
      { label: 'Export formats', us: US.exports, them: 'Excel, CSV, JSON, ZIP' },
      { label: 'Categorization', us: 'Included on every statement', them: 'Business plan and up' },
      { label: 'Teams', us: 'Single user', them: 'Multi-seat, shared workspaces, and client portals on higher plans' },
      { label: 'Integrations', us: 'None', them: 'Google Sheets and Excel add-ins; QuickBooks and Xero listed' },
      { label: 'Data', us: US.data, them: 'Encrypted in transit and at rest; no retention period stated' },
    ],
    tableNote: 'Rocket Statements prices are from its homepage in USD and may have changed.',
    sections: [
      {
        heading: 'Which costs less',
        paras: [
          'If you pay yearly and use most of your pages, Rocket Statements’ Basic plan is good value. If your volume is uneven, a page allowance can go unused, and the monthly price is $15.',
          'Bank Statement Scanner only uses credit when you convert, and every statement is categorized at no extra cost.',
        ],
      },
    ],
    fit: {
      us: ['You want categorization without upgrading', 'Your volume is uneven month to month', 'You want to try 3 statements before paying', 'You want an incognito mode that saves nothing'],
      them: ['You run a firm and want client portals', 'You want Sheets or Excel add-ins', 'You need several seats', 'You convert steadily and can pay yearly'],
    },
    faqs: [
      { q: 'Does Rocket Statements have a free trial?', a: 'Yes, 7 days with 20 pages and no card. Bank Statement Scanner gives you 3 statements free with no card.' },
      { q: 'Does Bank Statement Scanner categorize transactions?', a: 'Yes, on every statement, on every plan.' },
      QB_FAQ,
    ],
    sources: [{ label: 'Rocket Statements homepage and pricing', url: 'https://www.rocketstatements.com/' }],
    checked: CHECKED,
  },

  // ───────────── Desktop & PDF tools ─────────────
  {
    slug: 'able2extract-alternative',
    category: 'Desktop & PDF tools',
    card: 'A $199.95 offline PDF converter for every kind of table, vs a tool built only for statements.',
    seoTitle: 'Able2Extract Alternative for Bank Statements',
    description: 'Able2Extract vs Bank Statement Scanner for converting bank statements to Excel: price, OCR, setup, and output compared.',
    crumb: 'Able2Extract alternative',
    eyebrow: 'Able2Extract alternative',
    h1: 'Able2Extract vs Bank Statement Scanner for bank statements',
    intro: [
      'Able2Extract Professional is a general PDF converter that runs fully offline on Windows, macOS, and Linux. It exports to Excel, Word, and many other formats, with batch OCR for scans.',
      'For bank statements specifically, a general converter gives you the table as it appears on the page. You still clean up headers, split columns, and remove balance lines. Bank Statement Scanner gives you one row per transaction with categories, ready to use.',
    ],
    themName: 'Able2Extract',
    rows: [
      { label: 'Price', us: US.price, them: '$199.95 one-time, or $49.95 for 30 days' },
      { label: 'Free use', us: US.free, them: '7-day trial' },
      { label: 'Runs', us: 'In the browser', them: 'Offline desktop app for Windows, macOS, Linux' },
      { label: 'Output', us: 'One row per transaction: date, description, amount, credit/debit, category', them: 'The PDF’s tables as laid out; Smart Templates help with repeat layouts' },
      { label: 'Export formats', us: US.exports, them: 'Excel, CSV, Word, PowerPoint, HTML, images, and more' },
      { label: 'Scanned statements', us: US.scanned, them: 'Batch OCR in 12 languages' },
    ],
    tableNote: 'Able2Extract prices are from Investintech’s product page and may have changed.',
    sections: [
      {
        heading: 'When a desktop converter makes sense',
        paras: [
          'If you can’t upload financial documents to any web service, or you convert many kinds of PDFs besides statements, Able2Extract is a sensible purchase. It never leaves your machine.',
          'If statements are most of what you convert, the cleanup time adds up. Bank Statement Scanner reads the statement as a statement, not as a table.',
        ],
      },
    ],
    fit: {
      us: ['Statements are most of what you convert', 'You want categorized rows, not raw tables', 'You don’t want to install software', 'You don’t want to pay $199.95 up front'],
      them: ['Your files must never leave your computer', 'You convert invoices, reports, and other PDFs too', 'You want a one-time license', 'You need Word or PowerPoint output'],
    },
    faqs: [
      { q: 'Is Able2Extract a subscription?', a: 'No. It’s a $199.95 one-time license, with a $49.95 30-day option.' },
      { q: 'Does Able2Extract work offline?', a: 'Yes, it’s an offline desktop app. Bank Statement Scanner runs in the browser; use incognito mode if you don’t want anything saved.' },
      TRIAL_FAQ,
    ],
    sources: [{ label: 'Able2Extract Professional product page', url: 'https://www.investintech.com/prod_a2e.htm' }],
    checked: CHECKED,
  },
  {
    slug: 'tabula-alternative',
    category: 'Desktop & PDF tools',
    card: 'Free and open source, but no scanned PDFs and last released in 2018.',
    seoTitle: 'Tabula Alternative for Bank Statements (Scanned PDFs Too)',
    description: 'Tabula vs Bank Statement Scanner for bank statements: Tabula is free but doesn’t read scanned PDFs. See when each one fits.',
    crumb: 'Tabula alternative',
    eyebrow: 'Tabula alternative',
    h1: 'Tabula vs Bank Statement Scanner for bank statements',
    intro: [
      'Tabula is a free, open-source tool that pulls tables out of text-based PDFs. You draw a box around a table and export it to CSV or Excel. For a clean digital statement and a little patience, it works, and it costs nothing.',
      'It doesn’t read scanned PDFs, and its latest release, 1.2.1, is from June 2018. Here’s where Bank Statement Scanner fits instead.',
    ],
    themName: 'Tabula',
    rows: [
      { label: 'Price', us: US.price, them: 'Free, open source' },
      { label: 'Scanned statements', us: US.scanned, them: 'No. Text-based PDFs only' },
      { label: 'Setup', us: US.setup, them: 'Install (Java needed on Windows and Linux), then select each table by hand' },
      { label: 'Output', us: 'One row per transaction with credit/debit and category', them: 'The selected table as laid out on the page' },
      { label: 'Export formats', us: US.exports, them: 'CSV, Excel, JSON' },
      { label: 'Runs', us: 'In the browser', them: 'Locally, in your browser at localhost' },
    ],
    sections: [
      {
        heading: 'What you’ll fix by hand with Tabula',
        bullets: [
          'Multi-line descriptions split across rows.',
          'Debit and credit columns that need merging into one signed amount.',
          'Header, footer, and balance-forward lines mixed into the data.',
          'Each page selected separately when the layout shifts.',
        ],
      },
    ],
    fit: {
      us: ['Your statements are scanned or photographed', 'You want transactions ready to use, not raw tables', 'You convert more than the odd statement', 'You want categories added'],
      them: ['You want something free', 'Your statements are clean digital PDFs', 'Your files must stay on your computer', 'You don’t mind cleanup in Excel'],
    },
    faqs: [
      { q: 'Can Tabula read scanned bank statements?', a: 'No. Its site says it only works on text-based PDFs. Bank Statement Scanner reads scans, with an accurate mode for poor ones.' },
      { q: 'Is Tabula still maintained?', a: 'Its website lists version 1.2.1, released June 4, 2018, as the latest.' },
      TRIAL_FAQ,
    ],
    sources: [{ label: 'Tabula homepage', url: 'https://tabula.technology/' }],
    checked: CHECKED,
  },
  {
    slug: 'pdftables-alternative',
    category: 'Desktop & PDF tools',
    card: 'Prepaid page credits for any PDF table, vs per-statement pricing built for bank statements.',
    seoTitle: 'PDFTables Alternative for Bank Statements',
    description: 'PDFTables vs Bank Statement Scanner for converting bank statements: pricing, output, and scanned PDF support compared.',
    crumb: 'PDFTables alternative',
    eyebrow: 'PDFTables alternative',
    h1: 'PDFTables vs Bank Statement Scanner for bank statements',
    intro: [
      'PDFTables converts tables in any PDF to Excel, CSV, XML, or HTML, with an API on every plan. You buy page credits up front, starting at $50 for 1,000, and they expire after a year.',
      'It’s a general table extractor, so a bank statement comes out as the page’s table. Bank Statement Scanner gives you transactions, with signs and categories.',
    ],
    themName: 'PDFTables',
    rows: [
      { label: 'Price', us: US.price, them: '$50 for 1,000 page credits; $150 for 5,000; $250 for 10,000' },
      { label: 'Credits expire', us: 'Monthly credit with your subscription', them: 'After one year' },
      { label: 'Output', us: 'One row per transaction with credit/debit and category', them: 'The PDF’s tables' },
      { label: 'Export formats', us: US.exports, them: 'XLSX, CSV, XML, HTML' },
      { label: 'Scanned statements', us: US.scanned, them: 'Not stated on its pricing page' },
      { label: 'API', us: 'No', them: 'Included with every plan' },
    ],
    tableNote: 'PDFTables prices are from its pricing page in USD and may have changed.',
    sections: [
      {
        heading: 'Which one to use',
        paras: [
          'If you’re a developer pulling tables from many kinds of PDFs, PDFTables’ API and low per-page price are a good fit.',
          'If you want a finished transaction list from a bank statement without writing cleanup code, use a statement converter.',
        ],
      },
    ],
    fit: {
      us: ['You want transactions, not raw tables', 'Your statements are scanned', 'You don’t want to prepay', 'You want categories'],
      them: ['You need an API', 'You convert many kinds of PDF tables', 'You’ll write your own cleanup', 'You convert thousands of pages'],
    },
    faqs: [
      { q: 'Do PDFTables credits expire?', a: 'Yes, one year after purchase, per its pricing page.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [{ label: 'PDFTables pricing', url: 'https://pdftables.com/pricing' }],
    checked: CHECKED,
  },
  {
    slug: 'zamzar-alternative',
    category: 'Desktop & PDF tools',
    card: 'A general file converter that handles PDF to XLS, vs a converter that reads statements as transactions.',
    seoTitle: 'Zamzar Alternative for Bank Statement PDF to Excel',
    description: 'Zamzar vs Bank Statement Scanner for converting a bank statement PDF to Excel or CSV: output quality, limits, and file retention compared.',
    crumb: 'Zamzar alternative',
    eyebrow: 'Zamzar alternative',
    h1: 'Zamzar vs Bank Statement Scanner for bank statements',
    intro: [
      'Zamzar converts files between hundreds of formats, including PDF to XLS and PDF to CSV. It’s quick for one-off files and free for small ones.',
      'A general converter turns the PDF’s layout into a spreadsheet. On a bank statement, that usually means merged cells, split descriptions, and balance lines in the data. Bank Statement Scanner reads each transaction instead.',
    ],
    themName: 'Zamzar',
    rows: [
      { label: 'Price', us: US.price, them: 'Free for small files; paid plans for larger files' },
      { label: 'Built for', us: 'Bank and card statements', them: 'Any file format conversion' },
      { label: 'Output', us: 'One row per transaction with credit/debit and category', them: 'The PDF’s layout as a spreadsheet' },
      { label: 'Export formats', us: US.exports, them: 'XLS, CSV, and many others' },
      { label: 'File retention', us: 'Incognito mode stores no transaction data', them: 'Free conversions kept up to 24 hours; paid files kept until you delete them' },
      { label: 'Scanned statements', us: US.scanned, them: 'Not stated on its PDF to XLS page' },
    ],
    sections: [
      {
        heading: 'When Zamzar is fine',
        paras: [
          'For a short, simple statement where you only need the numbers once, a general converter may do. Check the totals afterwards.',
          'For statements you’ll import, reconcile, or hand to a client, you want one clean row per transaction.',
        ],
      },
    ],
    fit: {
      us: ['You need clean transaction rows', 'Your statements are scanned', 'You want categories', 'You want nothing stored'],
      them: ['You convert many file types', 'You need one quick conversion', 'The statement is short and simple', 'You don’t need categories'],
    },
    faqs: [
      { q: 'How long does Zamzar keep my files?', a: 'Its site says free converted files are stored for up to 24 hours, and paid users’ files are kept until they delete them.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [
      { label: 'Zamzar homepage', url: 'https://www.zamzar.com/' },
      { label: 'Zamzar PDF to XLS', url: 'https://www.zamzar.com/convert/pdf-to-xls/' },
    ],
    checked: CHECKED,
  },

  // ───────────── Document AI & parsers ─────────────
  {
    slug: 'nanonets-alternative',
    category: 'Document AI & parsers',
    card: 'An enterprise document AI platform priced by workflow block, vs a simple statement converter.',
    seoTitle: 'Nanonets Alternative for Bank Statements',
    description: 'Nanonets vs Bank Statement Scanner for bank statement conversion: pricing, setup, exports, and security compared.',
    crumb: 'Nanonets alternative',
    eyebrow: 'Nanonets alternative',
    h1: 'Nanonets vs Bank Statement Scanner for bank statements',
    intro: [
      'Nanonets is a document AI platform for building extraction workflows across invoices, statements, and more, with ERP integrations and SOC 2, HIPAA, and GDPR compliance. It gives new accounts $50 in credits.',
      'If you want to automate a document pipeline, it’s a serious option. If you want to turn statements into a spreadsheet, it’s more platform than you need.',
    ],
    themName: 'Nanonets',
    rows: [
      { label: 'Price', us: US.price, them: '$50 free credits, then Starter $100/month for 100 credits; Growth and Enterprise by quote' },
      { label: 'How you pay', us: US.perStatement, them: 'Per workflow block run: $0.02 simple, $0.10 standard AI, $0.30 complex AI' },
      { label: 'Setup', us: US.setup, them: 'Build or pick a workflow' },
      { label: 'Export formats', us: US.exports, them: 'Excel, CSV, JSON, API' },
      { label: 'Integrations', us: 'None', them: 'API, email, cloud storage; ERP connectors on higher plans' },
      { label: 'Security', us: US.data, them: 'SOC 2, HIPAA, GDPR' },
    ],
    tableNote: 'Nanonets prices are from its pricing page in USD and may have changed.',
    sections: [
      {
        heading: 'Where Nanonets is stronger',
        bullets: [
          'Workflows across many document types, not just statements.',
          'Links each extracted transaction to its place on the original statement.',
          'Enterprise security, data residency, and on-prem options.',
        ],
      },
    ],
    fit: {
      us: ['You just need statements in Excel or CSV', 'You don’t want to build a workflow', 'You want a low monthly cost', 'You convert a few statements a month'],
      them: ['You’re automating a document pipeline', 'You need ERP or SAP connectors', 'You need SOC 2 or HIPAA', 'You process many document types'],
    },
    faqs: [
      { q: 'How much does Nanonets cost?', a: 'New accounts get $50 in credits. Starter is then $100 a month for 100 credits, charged per workflow block run.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [
      { label: 'Nanonets pricing', url: 'https://nanonets.com/pricing' },
      { label: 'Nanonets bank statement converter', url: 'https://nanonets.com/bank-statement-converter' },
    ],
    checked: CHECKED,
  },
  {
    slug: 'docparser-alternative',
    category: 'Document AI & parsers',
    card: 'Rule-based parsers you build and maintain, vs upload-and-go statement conversion.',
    seoTitle: 'Docparser Alternative for Bank Statements',
    description: 'Docparser vs Bank Statement Scanner for parsing bank statements: setup, pricing, and output compared. No parser rules to build.',
    crumb: 'Docparser alternative',
    eyebrow: 'Docparser alternative',
    h1: 'Docparser vs Bank Statement Scanner for bank statements',
    intro: [
      'Docparser lets you build parsing rules for recurring documents and send the results to Google Sheets and hundreds of integrations. Plans start at $39 a month, with a 14-day trial.',
      'Rules work well when every document looks the same. Bank statements from different banks don’t, so each layout can mean another parser. Bank Statement Scanner reads statements from 100+ banks without setup.',
    ],
    themName: 'Docparser',
    rows: [
      { label: 'Price', us: US.price, them: 'Starter $39/month (100 credits); Professional $74; Business $159; about 20% less billed yearly' },
      { label: 'How you pay', us: US.perStatement, them: 'One credit per document of up to 5 pages' },
      { label: 'Free use', us: US.free, them: '14-day trial, no card' },
      { label: 'Setup', us: US.setup, them: 'Build a parser per layout; one free setup session included' },
      { label: 'Export formats', us: US.exports, them: 'Excel, CSV, JSON, XML, Google Sheets, integrations' },
      { label: 'Data retention', us: 'Incognito mode stores no transaction data', them: 'Extended retention (120 or 360 days) is a paid add-on' },
    ],
    tableNote: 'Docparser prices are from its pricing page in USD and may have changed.',
    sections: [
      {
        heading: 'Credits and long statements',
        paras: [
          'A Docparser credit covers a document up to 5 pages. A 12-page statement uses more than one credit. Bank Statement Scanner charges per statement, whatever its length.',
        ],
      },
    ],
    fit: {
      us: ['Your statements come from many banks', 'You don’t want to build parsers', 'Your statements are long', 'You want categories added'],
      them: ['You process the same layouts every month', 'You need Zapier-style integrations', 'You parse invoices and forms too', 'You want results pushed to Google Sheets'],
    },
    faqs: [
      { q: 'Do I need to set up Docparser for each bank?', a: 'Docparser is built around parsers you configure for a document type, and different layouts may need different parsers. Bank Statement Scanner needs no setup.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [{ label: 'Docparser pricing', url: 'https://docparser.com/pricing/' }],
    checked: CHECKED,
  },
  {
    slug: 'parsio-alternative',
    category: 'Document AI & parsers',
    card: 'A multi-engine parser with automation integrations, vs a converter built only for statements.',
    seoTitle: 'Parsio Alternative for Bank Statements',
    description: 'Parsio vs Bank Statement Scanner for converting bank statements: pricing, credits, retention, and output compared.',
    crumb: 'Parsio alternative',
    eyebrow: 'Parsio alternative',
    h1: 'Parsio vs Bank Statement Scanner for bank statements',
    intro: [
      'Parsio is a document parser with template, OCR, AI, and GPT engines, a free plan of 30 credits a month, and integrations with Zapier, Make, and n8n. Bank statements are one of the document types it supports.',
      'If you’re wiring documents into automations, it’s a good choice. If you want statements in a spreadsheet, Bank Statement Scanner is simpler.',
    ],
    themName: 'Parsio',
    rows: [
      { label: 'Price', us: US.price, them: 'Free (30 credits/month); paid plans from about $24–29/month for 100 credits' },
      { label: 'How you pay', us: US.perStatement, them: 'Credits per page; AI and GPT engines use more credits per page than templates' },
      { label: 'Setup', us: US.setup, them: 'Choose an engine and set up a mailbox or parser' },
      { label: 'Export formats', us: US.exports, them: 'Excel, CSV, JSON, Google Sheets, webhooks, API' },
      { label: 'Integrations', us: 'None', them: 'Zapier, Make, Pabbly Connect, n8n, Integrately' },
      { label: 'Data retention', us: 'Incognito mode stores no transaction data', them: '30 days on Free, 90 on Starter and Growth, 180 on Business' },
    ],
    tableNote: 'Parsio’s pricing page shows more than one monthly price for some plans; check it for current amounts.',
    sections: [
      {
        heading: 'Pages add up',
        paras: [
          'On Parsio’s free plan, 30 credits cover about 10 pages with the AI engine. A single long statement can use that up. Bank Statement Scanner gives you 3 full statements free.',
        ],
      },
    ],
    fit: {
      us: ['You want statements in a spreadsheet, nothing more', 'Your statements are long', 'You want categories added', 'You want nothing stored'],
      them: ['You’re building automations in Zapier or Make', 'You parse emails and other documents', 'You want a permanent free tier', 'You need webhooks or an API'],
    },
    faqs: [
      { q: 'Does Parsio support bank statements?', a: 'Yes, bank statements are a listed document type for its AI parser.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [{ label: 'Parsio pricing', url: 'https://parsio.io/pricing/' }],
    checked: CHECKED,
  },

  // ───────────── Accounting data capture ─────────────
  {
    slug: 'dext-alternative',
    category: 'Accounting data capture',
    card: 'Receipt and bill capture with bank statement extraction as an add-on, vs statements only.',
    seoTitle: 'Dext Alternative for Bank Statement Conversion',
    description: 'Dext vs Bank Statement Scanner for bank statements: Dext includes 10 statement sheets, then an add-on. Compare pricing and fit.',
    crumb: 'Dext alternative',
    eyebrow: 'Dext alternative',
    h1: 'Dext vs Bank Statement Scanner for bank statements',
    intro: [
      'Dext is a bookkeeping capture tool for receipts, bills, and invoices that publishes into 36+ accounting platforms. Its business plan includes 10 sheets of bank statement extraction, with more as an add-on.',
      'If you need receipt capture and accounting sync, Dext covers far more than we do. If you only need statements converted, you’re paying for a lot you won’t use.',
    ],
    themName: 'Dext',
    rows: [
      { label: 'Price', us: US.price, them: 'Business from $25.21/month or $302.50/year, 250 documents and 5 users' },
      { label: 'Bank statements', us: 'Every conversion', them: '10 sheets included; add-on from $13/month or from $0.32/document' },
      { label: 'Free use', us: US.free, them: '14-day trial, no card' },
      { label: 'Captures', us: 'Bank and card statements', them: 'Receipts, bills, invoices, and statements' },
      { label: 'Integrations', us: 'CSV or Excel export', them: 'QuickBooks Online, Xero, Sage, Zoho, and 30+ more' },
      { label: 'Users', us: 'Single user', them: '5 users on the business plan' },
    ],
    tableNote: 'Dext prices are from its business pricing page in USD, excluding VAT, and may have changed.',
    sections: [
      {
        heading: 'Using both',
        paras: [
          'Some bookkeepers use Dext for receipts and a separate converter for historical bank statements, such as a catch-up job where the bank feed doesn’t go back far enough. That’s where Bank Statement Scanner fits.',
        ],
      },
    ],
    fit: {
      us: ['You only need bank statements converted', 'You’re catching up on old statements', 'You want a low monthly cost', 'CSV or Excel is enough'],
      them: ['You need receipt and bill capture', 'You want direct publishing to accounting software', 'Several people need access', 'You want bank feeds alongside capture'],
    },
    faqs: [
      { q: 'Does Dext convert bank statements?', a: 'Yes. Its business plan includes 10 free sheets of bank statement extraction, with an add-on from $13 a month or pay-as-you-go from $0.32 a document.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [
      { label: 'Dext business pricing', url: 'https://dext.com/en/business/pricing' },
      { label: 'Dext homepage', url: 'https://dext.com/en/' },
    ],
    checked: CHECKED,
  },
  {
    slug: 'autoentry-alternative',
    category: 'Accounting data capture',
    card: 'Credit plans where a statement page costs 3 credits, vs one price per statement.',
    seoTitle: 'AutoEntry Alternative for Bank Statements',
    description: 'AutoEntry vs Bank Statement Scanner for bank statement conversion: credit costs, integrations, and fit compared.',
    crumb: 'AutoEntry alternative',
    eyebrow: 'AutoEntry alternative',
    h1: 'AutoEntry vs Bank Statement Scanner for bank statements',
    intro: [
      'AutoEntry automates data entry for invoices, receipts, and bank statements, and publishes into Sage, Xero, QuickBooks, and more. You buy monthly credits, from 50 credits for $13.',
      'Each bank statement page costs 3 credits, so long statements use credits quickly. Bank Statement Scanner charges per statement, not per page.',
    ],
    themName: 'AutoEntry',
    rows: [
      { label: 'Price', us: US.price, them: 'Bronze $13/month for 50 credits, up to Sapphire $469 for 2,500' },
      { label: 'Bank statements', us: US.perStatement, them: '3 credits per page (about $0.60–0.78 per page)' },
      { label: 'Free use', us: US.free, them: '25 free credits, no card' },
      { label: 'Unused credit', us: 'Added each billing cycle', them: 'Rolls over for 90 days' },
      { label: 'Integrations', us: 'CSV or Excel export', them: 'Sage, Xero, QuickBooks, FreeAgent, and more' },
      { label: 'Captures', us: 'Bank and card statements', them: 'Invoices, receipts, and bank statements' },
    ],
    tableNote: 'AutoEntry prices are from its pricing page in USD, excluding VAT, and may have changed.',
    sections: [
      {
        heading: 'A 10-page statement',
        paras: [
          'On AutoEntry, a 10-page statement uses 30 credits, which is most of the 50-credit Bronze plan. On Bank Statement Scanner, it costs $1 in balanced mode or $1.50 in accurate mode.',
        ],
      },
    ],
    fit: {
      us: ['Your statements are long', 'You only need statements converted', 'CSV or Excel is enough', 'You want categories added'],
      them: ['You also capture invoices and receipts', 'You want direct publishing to Sage, Xero, or QuickBooks', 'You work across many clients', 'You want credits that roll over'],
    },
    faqs: [
      { q: 'How many AutoEntry credits does a bank statement use?', a: 'Its pricing page says 3 credits per bank statement page.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [{ label: 'AutoEntry pricing', url: 'https://www.autoentry.com/pricing' }],
    checked: CHECKED,
  },
  {
    slug: 'hubdoc-alternative',
    category: 'Accounting data capture',
    card: 'Document capture that syncs to Xero and QuickBooks Online, vs a spreadsheet of transactions.',
    seoTitle: 'Hubdoc Alternative for Bank Statements to Excel',
    description: 'Hubdoc vs Bank Statement Scanner: Hubdoc captures documents for Xero and QuickBooks Online. Compare it for getting bank statements into Excel or CSV.',
    crumb: 'Hubdoc alternative',
    eyebrow: 'Hubdoc alternative',
    h1: 'Hubdoc vs Bank Statement Scanner for bank statements',
    intro: [
      'Hubdoc collects bills, receipts, and statements, extracts key data, and creates transactions in Xero or QuickBooks Online with the document attached. It’s $12 a month after a 30-day trial.',
      'It’s built to feed accounting software. If you want a spreadsheet of every transaction on a statement, to review, analyze, or send to someone, a statement converter is the better tool.',
    ],
    themName: 'Hubdoc',
    rows: [
      { label: 'Price', us: US.price, them: '$12/month after the trial' },
      { label: 'Free use', us: US.free, them: '30-day trial, no card' },
      { label: 'Built for', us: 'Turning statements into transaction spreadsheets', them: 'Capturing documents into Xero or QuickBooks Online' },
      { label: 'Output', us: 'Every transaction as a row in CSV or Excel', them: 'Key data and the source document, synced to accounting software' },
      { label: 'Captures', us: 'Bank and card statements', them: 'Bills, receipts, invoices, and statements, by upload, email, or phone' },
    ],
    tableNote: 'Hubdoc’s price is from its pricing page in USD. If you use Xero, check whether Hubdoc is included in your plan.',
    sections: [],
    fit: {
      us: ['You want every transaction in a spreadsheet', 'You don’t use Xero or QuickBooks Online', 'You’re analyzing statements, not filing them', 'You want categories added'],
      them: ['You use Xero or QuickBooks Online', 'You want bills and receipts captured too', 'You want documents attached to transactions', 'You snap receipts on your phone'],
    },
    faqs: [
      { q: 'How much is Hubdoc?', a: 'Its pricing page lists $12 a month after a 30-day free trial.' },
      TRIAL_FAQ,
      QB_FAQ,
    ],
    sources: [
      { label: 'Hubdoc pricing', url: 'https://www.hubdoc.com/pricing' },
      { label: 'Hubdoc homepage', url: 'https://www.hubdoc.com/' },
    ],
    checked: CHECKED,
  },
];

export const competitorBySlug = (slug: string) => competitors.find((c) => c.slug === slug);
