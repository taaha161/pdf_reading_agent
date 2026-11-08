// Comparison pages, listed on /compare and the landing page.
import { competitors, type CompareCategory } from './competitors';

export interface ComparePageLink {
  href: string;
  title: string;
  body: string;
  category: CompareCategory;
  /** Shown in the landing page's "How we compare" list. */
  featured?: boolean;
}

export const compareCategories: CompareCategory[] = [
  'Statement converters',
  'Accounting data capture',
  'Document AI & parsers',
  'Desktop & PDF tools',
  'General AI',
];

const FEATURED = new Set(['moneythumb-alternative', 'dext-alternative']);

export const comparePages: ComparePageLink[] = [
  {
    href: '/compare/docuclipper-alternative',
    title: 'Bank Statement Scanner vs DocuClipper',
    body: 'Pay per statement with no annual contract, and when DocuClipper is the better fit.',
    category: 'Statement converters',
    featured: true,
  },
  {
    href: '/compare/chatgpt-for-bank-statements',
    title: 'Bank Statement Scanner vs ChatGPT',
    body: 'Can ChatGPT convert bank statements to Excel? Where it goes wrong and how to check it.',
    category: 'General AI',
    featured: true,
  },
  ...competitors.map((c) => ({
    href: `/compare/${c.slug}`,
    title: `Bank Statement Scanner vs ${c.themName}`,
    body: c.card,
    category: c.category,
    featured: FEATURED.has(c.slug),
  })),
];
