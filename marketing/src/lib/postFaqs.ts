/**
 * The "## Frequently asked questions" section of a post's markdown as [{ q, a }],
 * for FAQPage JSON-LD. Questions are the ### headings; each answer is the text up
 * to the next heading, with markdown stripped. Empty when the post has no FAQ section.
 */
export function postFaqs(markdown: string | undefined): { q: string; a: string }[] {
  if (!markdown) return [];
  const lines = markdown.split('\n');
  const start = lines.findIndex((l) => /^##\s+(frequently asked questions|faqs?)\b/i.test(l));
  if (start < 0) return [];
  const faqs: { q: string; a: string }[] = [];
  let current: { q: string; a: string[] } | null = null;
  const flush = () => {
    if (!current) return;
    const a = plain(current.a.join(' '));
    if (current.q && a) faqs.push({ q: plain(current.q), a });
  };
  for (const line of lines.slice(start + 1)) {
    if (/^##\s/.test(line)) break; // next H2 ends the section
    const h3 = /^###\s+(.*)$/.exec(line);
    if (h3) {
      flush();
      current = { q: h3[1], a: [] };
    } else if (current) {
      current.a.push(line);
    }
  }
  flush();
  return faqs;
}

function plain(md: string): string {
  return md
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/[*_`]+/g, '')
    .replace(/^\s*[-+]\s+/gm, '')
    .replace(/\s+/g, ' ')
    .trim();
}
