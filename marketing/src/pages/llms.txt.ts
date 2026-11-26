// /llms.txt: a plain-text map of the site for AI assistants and answer engines.
// Generated at build time so new banks, comparisons, personas and posts are never missing.
import { getCollection } from 'astro:content';
import { SITE_URL, SITE_NAME, SUPPORT_EMAIL, LEGAL_ENTITY, PRICING_SUMMARY } from '../consts';
import { PERSONAS } from '../personas';
import { comparePages } from '../comparePages';

const link = (title: string, path: string, note?: string) =>
  `- [${title}](${SITE_URL}${path})${note ? `: ${note}` : ''}`;

export async function GET() {
  const banks = (await getCollection('banks')).sort((a, b) => a.data.name.localeCompare(b.data.name));
  const posts = (await getCollection('blog')).sort((a, b) => b.data.date.valueOf() - a.data.date.valueOf());

  const body = [
    `# ${SITE_NAME}`,
    '',
    `> ${SITE_NAME} converts bank and credit card statement PDFs (digital, scanned or password-protected) into clean, categorized transactions in Excel or CSV. Every converted statement is checked against its own printed running balances and summary totals. Users can then ask the statement questions in plain English ("every payment to John in March") and export just those rows. Built for bookkeepers, accountants, tax preparers, small businesses and individuals in the US.`,
    '',
    '## Key facts',
    '',
    '- Input: PDF bank and credit card statements from US banks and card issuers. Digital, scanned (OCR) and password-protected PDFs. PDF only.',
    '- Output: CSV and Excel (XLSX). Columns: date, description, amount, type, category. Excel downloads include a Reconciliation sheet.',
    '- QuickBooks and Xero: one-click import-ready CSVs for QuickBooks Online (Date, Description, Amount) and Xero (Date, Amount, Payee, Description, Reference), with signed amounts and every date rewritten to one full format (MM/DD/YYYY or DD/MM/YYYY). Also available for a whole bulk batch as one file. Guides: /bank-statement-to-quickbooks, /bank-statement-to-xero.',
    '- Checks: running balances and the summary box (opening balance, total in, total out, closing balance) are checked against the extracted rows. Statements that print no balances are shown as "can\'t check".',
    '- Bulk upload: signed-in users can upload up to 50 statement PDFs at once and download one combined Excel workbook (an "All statements" sheet with a Statement column, plus a sheet per statement) or one combined CSV. Same per-page price as single uploads.',
    '- Not offered: .QBO/OFX/QFX/IIF files (QuickBooks Desktop, Quicken), direct QuickBooks or Xero sync, book-to-bank ledger reconciliation.',
    `- Pricing: ${PRICING_SUMMARY}`,
    '- Privacy: uploads encrypted in transit; incognito mode converts without saving the data; saved statements can be deleted any time.',
    `- Company: ${LEGAL_ENTITY}. Contact: ${SUPPORT_EMAIL}.`,
    '',
    '## Main pages',
    '',
    link('Home', '/', 'product overview, pricing and FAQ'),
    link('Scanner (app)', '/scanner', 'upload a statement PDF and export structured data'),
    link('Bulk bank statement converter', '/bulk-bank-statement-converter', 'convert up to 50 statement PDFs at once into one combined workbook'),
    link('Bank statement PDF to QuickBooks', '/bank-statement-to-quickbooks', 'import-ready QuickBooks Online CSV (Date, Description, Amount) from a statement PDF'),
    link('Bank statement PDF to Xero', '/bank-statement-to-xero', 'import-ready Xero statement CSV (Date, Amount, Payee, Description, Reference) from a statement PDF'),
    link('Supported banks', '/convert', 'per-bank conversion guides'),
    link('Comparisons', '/compare', 'honest comparisons with other converters and tools'),
    link('Security', '/security', 'how financial data is handled'),
    link('About', '/about'),
    link('Blog', '/blog', `guides; RSS at ${SITE_URL}/rss.xml`),
    link('Contact', '/contact'),
    '',
    '## Who it is for',
    '',
    ...PERSONAS.map((p) => link(p.seoTitle, `/for/${p.slug}`, p.description)),
    '',
    '## Bank-specific conversion guides',
    '',
    ...banks.map((b) => link(b.data.seoTitle, `/convert/${b.data.slug}`, b.data.description)),
    '',
    '## Comparisons',
    '',
    ...comparePages.map((c) => link(c.title, c.href, c.body)),
    '',
    '## Guides',
    '',
    ...posts.map((p) => link(p.data.title, `/blog/${p.id}`, p.data.excerpt)),
    '',
    '## Legal',
    '',
    link('Privacy Policy', '/privacy-policy'),
    link('Terms of Service', '/terms-of-service'),
    '',
  ].join('\n');

  return new Response(body, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
}
