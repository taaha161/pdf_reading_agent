import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    /** Short, keyword-focused <title> tag; distinct from the on-page h1 (title). */
    seoTitle: z.string().optional(),
    excerpt: z.string(),
    date: z.coerce.date(),
    category: z.string(),
    readTime: z.string(),
    image: z.string(),
    /** Primary keyword (set by the generator; one post per keyword). */
    keyword: z.string().optional(),
    /** SEO keyword tags for the post; optional so hand-written posts stay valid. */
    tags: z.array(z.string()).optional(),
  }),
});

/**
 * One SEO landing page per bank (/convert/<slug>). All bank-specific facts live
 * in frontmatter so every page carries unique, sourced content rather than a
 * name swapped into a template. Keep claims hedged unless a source is official.
 */
const banks = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/banks' }),
  schema: z.object({
    name: z.string(),
    /** Short form used in running copy ("Chase", "BofA"). */
    shortName: z.string(),
    /** URL segment under /convert, e.g. "chase-bank-statement-to-excel". */
    slug: z.string(),
    seoTitle: z.string(),
    description: z.string(),
    country: z.enum(['US', 'PK', 'UK']),
    /** Statement types this page covers, e.g. ["Checking", "Savings", "Credit card"]. */
    statementTypes: z.array(z.string()),
    intro: z.string(),
    /** Why the bank's own export isn't enough (date-window limits etc.). */
    exportLimits: z.string(),
    downloadSteps: z.array(z.string()),
    layoutNotes: z.array(z.object({ title: z.string(), body: z.string() })),
    faqs: z.array(z.object({ q: z.string(), a: z.string() })),
    sources: z.array(z.object({ label: z.string(), url: z.string().url() })),
    /** Optional blog post slug covering the bank in more depth. */
    relatedPost: z.string().optional(),
    reviewed: z.coerce.date(),
  }),
});

export const collections = { blog, banks };
