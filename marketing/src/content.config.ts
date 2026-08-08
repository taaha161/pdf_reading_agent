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
    /** SEO keyword tags for the post; optional so hand-written posts stay valid. */
    tags: z.array(z.string()).optional(),
  }),
});

export const collections = { blog };
