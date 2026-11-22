import type { CollectionEntry } from 'astro:content';

type Post = CollectionEntry<'blog'>;

const STOPWORDS = new Set([
  'the', 'and', 'for', 'with', 'how', 'your', 'you', 'from', 'into', 'what',
  'which', 'that', 'this', 'are', 'can', 'vs', 'guide', 'complete', 'step',
  'by', 'to', 'of', 'in', 'on', 'a', 'an', 'is', 'or', 'it', 'its', 'use',
  'best', 'free', 'online', 'bank', 'statement', 'statements',
]);

function topicTokens(p: Post): Set<string> {
  const text = [p.data.title, p.data.keyword ?? '', ...(p.data.tags ?? [])]
    .join(' ')
    .toLowerCase();
  return new Set(
    text
      .split(/[^a-z0-9]+/)
      .filter((w) => w.length > 2 && !STOPWORDS.has(w)),
  );
}

function similarity(a: Set<string>, b: Set<string>): number {
  if (!a.size || !b.size) return 0;
  let shared = 0;
  for (const t of a) if (b.has(t)) shared++;
  return shared / Math.sqrt(a.size * b.size);
}

/**
 * Pick related posts for `post`: the most topically similar posts (title,
 * keyword and tag overlap, small boost for same category), plus the next-older
 * post in publish order. The chronological neighbour forms a chain through the
 * whole archive, so every post gets at least one inbound link from another
 * post instead of all posts linking to the newest few.
 */
export function relatedPosts(post: Post, all: Post[], topical = 4): Post[] {
  const others = all.filter((p) => p.id !== post.id);
  const mine = topicTokens(post);

  const picks = others
    .map((p) => ({
      p,
      score:
        similarity(mine, topicTokens(p)) +
        (p.data.category === post.data.category ? 0.1 : 0),
    }))
    .sort((a, b) => b.score - a.score || a.p.id.localeCompare(b.p.id))
    .slice(0, topical)
    .map((x) => x.p);

  const byDate = [...all].sort(
    (a, b) => b.data.date.valueOf() - a.data.date.valueOf() || a.id.localeCompare(b.id),
  );
  const i = byDate.findIndex((p) => p.id === post.id);
  const older = byDate[(i + 1) % byDate.length];
  if (older && older.id !== post.id && !picks.some((p) => p.id === older.id)) {
    picks.push(older);
  }
  return picks;
}
