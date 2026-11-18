import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';
import type { APIContext } from 'astro';
import { SITE_NAME, SITE_URL } from '../consts';

export async function GET(context: APIContext) {
  const posts = (await getCollection('blog')).sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf()
  );
  return rss({
    title: `${SITE_NAME} Blog`,
    description:
      'Guides on converting bank statement PDFs to Excel and CSV, bookkeeping workflows, and statement data extraction.',
    site: context.site ?? SITE_URL,
    items: posts.map((p) => ({
      title: p.data.title,
      description: p.data.excerpt,
      pubDate: p.data.date,
      link: `/blog/${p.id}`,
      categories: [p.data.category, ...(p.data.tags ?? [])],
    })),
    customData: '<language>en-us</language>',
    trailingSlash: false,
  });
}
