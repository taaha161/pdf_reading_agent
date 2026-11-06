// Post-build fix for @astrojs/vercel's /_astro cache rule.
//
// The adapter emits `^/_astro/(.*)$ -> cache-control: immutable` *after* `handle: filesystem`,
// so Vercel applies it only when the file is missing. Result: real hashed chunks are served with
// max-age=0, and a 404 for a chunk (e.g. a page loaded mid-deploy) is cached by the browser for
// a year. The page's script then never runs again for that visitor (this broke the hero
// dropzone's "Upload PDF for free" button).
//
// Move the rule into the `hit` phase so it only applies to files that exist.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';

const path = new URL('../.vercel/output/config.json', import.meta.url);
if (!existsSync(path)) {
  console.warn('[fix-vercel-cache-headers] no .vercel/output/config.json, skipping');
  process.exit(0);
}

const config = JSON.parse(readFileSync(path, 'utf8'));
const routes = config.routes ?? [];
const isAstroCacheRule = (r) => r.src === '^/_astro/(.*)$' && r.headers?.['cache-control'] && r.continue;
const rule = routes.find(isAstroCacheRule);
if (!rule) {
  console.warn('[fix-vercel-cache-headers] /_astro cache rule not found, nothing to fix');
  process.exit(0);
}

const rest = routes.filter((r) => r !== rule);
let hitIdx = rest.findIndex((r) => r.handle === 'hit');
if (hitIdx === -1) {
  rest.push({ handle: 'hit' });
  hitIdx = rest.length - 1;
}
rest.splice(hitIdx + 1, 0, rule);
config.routes = rest;

writeFileSync(path, JSON.stringify(config, null, '\t'));
console.log('[fix-vercel-cache-headers] moved /_astro immutable rule to the hit phase');
