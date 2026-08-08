---
name: run-blog-generator
description: Run, test, or debug the daily SEO blog generator — generate a bank-statement SEO blog post with Gemini + a Pixabay image and commit it to the Astro marketing site. Use when asked to run the blog generator, test blog generation, generate a post, add the daily blog cron, or debug /admin/generate-blog.
---

# Daily SEO Blog Generator

Generates one 1500–2500 word, internally-linked, SEO-optimized blog post per day for
**bankstatementscanner.com** and publishes it with zero human steps.

**Pipeline:** GitHub Actions cron (`.github/workflows/daily-blog.yml`) → `POST
/admin/generate-blog` on the FastAPI backend → `backend/services/blog_generator.py`:
pick a target keyword (rotated by day) → **Gemini** writes the post as structured JSON →
**Pixabay API** supplies a finance photo → both files committed to
`marketing/src/content/blog/` + `marketing/public/blog/images/` via the **GitHub
contents API** → Vercel auto-rebuilds the Astro site.

Paths below are relative to the repo root. The driver is
`.claude/skills/run-blog-generator/driver.py`.

## Prerequisites

Backend deps are already pinned in `backend/requirements.txt` (`google-genai`, `httpx`,
`pydantic`, `python-dotenv` — all used here). Install once:

```bash
pip install -r backend/requirements.txt
```

Env vars (see `backend/.env.example`). `GOOGLE_GEMINI_API_KEY` already exists; add:

- `PIXABAY_API_KEY` — free key from https://pixabay.com/api/docs/
- `GITHUB_TOKEN` — fine-grained PAT with **Contents: Read and write** on the repo
- `GITHUB_REPO` — `taaha161/pdf_reading_agent`
- `GITHUB_BRANCH` (default `main`), `GEMINI_BLOG_MODEL` (default `gemini-flash-latest`),
  `SITE_URL` (default `https://bankstatementscanner.com`) — all optional
- `API_AUTH_SECRET` — already set; guards the admin endpoint

## Run (agent path) — dry-run the generator

Fastest inner loop when changing prompts, keywords, internal links, or frontmatter.
Calls Gemini for real, writes markdown to the scratchpad, and does **NOT** commit.
Run from `backend/` so `backend/.env` loads:

```bash
cd backend
python3 ../.claude/skills/run-blog-generator/driver.py dry-run
```

Output reports title, word count (flags OUT OF RANGE if <1500 or >2600), tags, and the
internal links found — warning on any link outside the allow-list. A real run looks like:

```
→ keyword: 'convert bank statements to csv'  model: gemini-flash-latest
✓ wrote .../scratchpad/convert-bank-statements-to-csv.md
  words:    1840  (OK)
  internal links (7): ['/', '/blog/are-bank-statement-converters-safe-accurate', ...]
```

Override the model to compare quality:

```bash
GEMINI_BLOG_MODEL=gemini-3.6-flash python3 ../.claude/skills/run-blog-generator/driver.py dry-run
```

## Run (live endpoint) — smoke against a running backend

This **does** generate and commit a real post. Boot the backend, then hit it:

```bash
cd backend
uvicorn main:app --port 8123
```

```bash
python3 ../.claude/skills/run-blog-generator/driver.py smoke http://localhost:8123 "$API_AUTH_SECRET"
```

Auth is a shared secret in the `Authorization: Bearer` header. Verify the guard:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8123/admin/generate-blog          # 401
curl -s -o /dev/null -w '%{http_code}\n' -X POST localhost:8123/admin/generate-blog -H 'Authorization: Bearer wrong'  # 401
```

With a valid secret but missing `GITHUB_REPO`/`PIXABAY_API_KEY`, the endpoint returns
`502` with the exact missing-var message — that confirms wiring even without publish creds.

## Validate the published format

Generated frontmatter must satisfy the Astro schema in `marketing/src/content.config.ts`
(this skill added an optional `tags` array there). To prove a generated file builds, copy
a dry-run output into the content dir and build:

```bash
cd marketing
npx astro build      # content sync validates every post's frontmatter
```

A clean build ends with `[build] Complete!` and renders `/blog/<slug>/index.html`.

## Schedule (production)

`.github/workflows/daily-blog.yml` runs at 09:00 UTC daily and on manual dispatch. It
`curl`s the endpoint. Set repo **Actions secrets**: `BACKEND_URL` (e.g.
`https://pdf-statement-api.onrender.com`) and `API_AUTH_SECRET` (matching the backend).

## Gotchas

- **Model choice is load-bearing.** `gemini-2.5-flash` under-delivered badly (≈600–900
  words, **zero** internal links even when required). `gemini-pro-latest` hit length but
  still dropped all internal links. `gemini-flash-latest` was the only one that hit both
  length **and** internal linking — hence the default. `gemini-2.5-pro` and
  `gemini-3-pro-preview` return `404 no longer available` on this key. Re-run the dry-run
  and check the `internal links` count before trusting a new model.
- **Structured output is required.** Plain `response_mime_type="application/json"` returned
  markdown with raw unescaped newlines → `JSONDecodeError`. The fix is a Pydantic
  `response_schema` (`_BlogPost`) so the SDK hydrates `resp.parsed`.
- **Length retry.** `_generate_post` regenerates once with an "expand" nudge if the draft
  is under 1300 words. Flash models still occasionally land ~1470; treat 1300+ as passing.
- **Internal links are allow-listed.** The model may only link paths in
  `INTERNAL_LINKS`. When you publish a new post, add its slug there so future posts can
  link to it.
- **Keyword rotation, not dedup.** Posts rotate by day-of-year over `KEYWORDS`; the job
  lists existing repo slugs and appends the date to a slug on collision. It does not
  guarantee topical uniqueness over long horizons.
- **Two commits per post.** Image first, then markdown — so a post never references a
  missing image mid-rebuild.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `502 ... GITHUB_REPO is not set` | Set `GITHUB_REPO`/`GITHUB_TOKEN`/`PIXABAY_API_KEY` in backend env. |
| `404 ... model ... no longer available` | Pick a live model; `python3 -c "from google import genai,os; [print(m.name) for m in genai.Client(api_key=os.environ['GOOGLE_GEMINI_API_KEY']).models.list()]"`. |
| `JSONDecodeError` | Model ignored the schema; confirm `response_schema=_BlogPost` and `resp.parsed`. |
| Dry-run prints `OUT OF RANGE` / few links | Wrong/weak model — use `gemini-flash-latest`. |
| Astro build fails on a post | Frontmatter violates `content.config.ts`; check required keys + `tags` is an array. |
| `401` on the endpoint | `Authorization: Bearer <API_AUTH_SECRET>` missing or mismatched. |
