"""Daily SEO blog generator.

Pipeline (all server-side, no local checkout needed):
  1. Pick a target keyword (rotated by day, skipping slugs already in the repo).
  2. Fetch a random finance photo from the Pixabay API.
  3. Ask Gemini for a 1500-2500 word, internally-linked, SEO-optimized post as JSON.
  4. Commit the image + markdown to the marketing content collection via the
     GitHub contents API. Vercel auto-rebuilds the Astro site on push.

Env vars:
  GOOGLE_GEMINI_API_KEY  (already used elsewhere)
  PIXABAY_API_KEY        free key from https://pixabay.com/api/docs/
  GITHUB_TOKEN           PAT with `contents:write` on the repo
  GITHUB_REPO            e.g. "taaha161/pdf_reading_agent"
  GITHUB_BRANCH          default "main"
  GEMINI_BLOG_MODEL      default "gemini-flash-latest"
  SITE_URL               default "https://bankstatementscanner.com"
"""
from __future__ import annotations

import base64
import json
import logging
import os
import random
import re
from datetime import date, datetime, timezone

import httpx
from google import genai
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel, Field

logger = logging.getLogger("blog_generator")

# --- Config ------------------------------------------------------------------

CONTENT_DIR = "marketing/src/content/blog"
IMAGE_DIR = "marketing/public/blog/images"

# Target keywords, ordered so day-of-year rotation gives even coverage.
KEYWORDS: list[str] = [
    "bank statement scanner",
    "bank statement to csv",
    "bank statement converter",
    "bank statement to excel",
    "convert bank statements to csv",
    "scan bank statements",
    "bank statement software",
    "bank statement ocr",
    "bank statement organizer",
    "bank statement capture tool",
    "bank statement extraction software",
    "bank statement automation",
    "best bank statement analysis software",
    "financial data extraction software",
    "bank statement extraction software free",
    "bank statement pdf to excel",
    "convert bank statement pdf to excel",
    "credit card statement converter",
    "how to export bank statement to excel",
    "bank statement to excel software",
    "ocr bank statements to excel",
    "free bank statement converter",
    "convert bank statements to excel",
    "convert credit card statement to excel",
    "credit card statement to excel",
    "bookkeeping software",
    "bookkeeping made easy for accountants",
]

# Internal-link targets the model may reference (published posts + product pages).
# Kept in sync manually; new posts add themselves once merged.
INTERNAL_LINKS: dict[str, str] = {
    "/blog/bank-statement-converter-pdf-to-excel": "Bank statement converter: PDF to Excel or CSV",
    "/blog/pdf-bank-statement-to-csv-or-excel": "From PDF bank statement to CSV or Excel",
    "/blog/convert-scanned-bank-statement-ocr": "Convert scanned/photographed statements with OCR",
    "/blog/convert-multiple-bank-statements-in-bulk": "Convert multiple bank statements in bulk",
    "/blog/convert-bank-statement-pdf-to-quickbooks": "Convert a statement for QuickBooks & Xero",
    "/blog/are-bank-statement-converters-safe-accurate": "Are bank statement converters safe & accurate?",
    "/blog/bank-statement-scanner-for-accountants": "Bank statement scanner for accountants",
    "/blog/bank-statement-scanner-for-small-businesses": "Small business bookkeeping without the headache",
    "/blog/bank-statement-scanner-for-personal-finance": "Bank statement scanner for personal finance",
    "/blog/speed-up-month-end-with-bank-statement-automation": "Speed up month-end with automation",
    "/blog/bank-statement-pdf-layouts-and-extraction": "Why bank statement PDFs look different",
    "/blog/how-to-download-chase-bank-statements": "How to download Chase bank statements",
    "/": "Bank Statement Scanner — upload a PDF, export CSV/Excel",
}

CATEGORIES = ["Guides", "How-to", "Bookkeeping", "OCR & Extraction", "Comparisons"]


# --- Small helpers ------------------------------------------------------------

def _env(name: str, default: str | None = None, required: bool = False) -> str:
    val = (os.environ.get(name) or "").strip()
    if not val:
        if required:
            raise ValueError(f"{name} is not set")
        return default or ""
    return val


def _slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:80]


def _read_time(word_count: int) -> str:
    return f"{max(1, round(word_count / 200))} min read"


# --- GitHub -------------------------------------------------------------------

def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_env('GITHUB_TOKEN', required=True)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _existing_slugs(repo: str, branch: str) -> set[str]:
    """Slugs already present in the content dir (best-effort; empty on error)."""
    url = f"https://api.github.com/repos/{repo}/contents/{CONTENT_DIR}"
    try:
        r = httpx.get(url, headers=_gh_headers(), params={"ref": branch}, timeout=20)
        r.raise_for_status()
        return {
            item["name"][:-3]
            for item in r.json()
            if item.get("type") == "file" and item.get("name", "").endswith(".md")
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("Could not list existing posts: %s", e)
        return set()


def _gh_api(method: str, repo: str, path: str, **kwargs) -> dict:
    url = f"https://api.github.com/repos/{repo}/{path}"
    r = httpx.request(method, url, headers=_gh_headers(), timeout=30, **kwargs)
    if r.status_code not in (200, 201):
        raise RuntimeError(f"GitHub {method} {path} failed: {r.status_code} {r.text[:300]}")
    return r.json()


def _gh_commit_files(
    repo: str, branch: str, files: list[tuple[str, bytes]], message: str
) -> dict:
    """Commit multiple files as ONE commit via the Git Data API.

    A single commit to `branch` means Vercel rebuilds once per post, and the site
    never sees an intermediate state (e.g. markdown pushed before its image).
    """
    # 1. Current tip of the branch and its tree.
    ref = _gh_api("GET", repo, f"git/ref/heads/{branch}")
    base_commit_sha = ref["object"]["sha"]
    base_commit = _gh_api("GET", repo, f"git/commits/{base_commit_sha}")
    base_tree_sha = base_commit["tree"]["sha"]

    # 2. Upload each file as a blob (base64 handles binary + text uniformly).
    tree_entries = []
    for path, content in files:
        blob = _gh_api(
            "POST", repo, "git/blobs",
            json={"content": base64.b64encode(content).decode(), "encoding": "base64"},
        )
        tree_entries.append(
            {"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]}
        )

    # 3. New tree, new commit, then move the branch ref to it.
    tree = _gh_api(
        "POST", repo, "git/trees",
        json={"base_tree": base_tree_sha, "tree": tree_entries},
    )
    commit = _gh_api(
        "POST", repo, "git/commits",
        json={"message": message, "tree": tree["sha"], "parents": [base_commit_sha]},
    )
    _gh_api(
        "PATCH", repo, f"git/refs/heads/{branch}",
        json={"sha": commit["sha"], "force": False},
    )
    return commit


# --- Pixabay ------------------------------------------------------------------

def _fetch_finance_image() -> bytes:
    """Random finance photo from the Pixabay API. Returns JPEG bytes."""
    key = _env("PIXABAY_API_KEY", required=True)
    r = httpx.get(
        "https://pixabay.com/api/",
        params={
            "key": key,
            "q": "finance",
            "image_type": "photo",
            "orientation": "horizontal",
            "safesearch": "true",
            "per_page": 100,
            "page": random.randint(1, 3),
        },
        timeout=30,
    )
    r.raise_for_status()
    hits = r.json().get("hits", [])
    if not hits:
        raise RuntimeError("Pixabay returned no finance images")
    hit = random.choice(hits)
    img_url = hit.get("largeImageURL") or hit.get("webformatURL")
    img = httpx.get(img_url, timeout=60)
    img.raise_for_status()
    return img.content


# --- Gemini -------------------------------------------------------------------

def _get_client() -> genai.Client:
    return genai.Client(api_key=_env("GOOGLE_GEMINI_API_KEY", required=True))


_SYSTEM = (
    "You are a senior SEO content writer for Bank Statement Scanner, a tool that "
    "converts bank and credit-card statement PDFs into clean CSV/Excel. Write "
    "original, genuinely useful, non-fluffy articles that rank. Prioritise search "
    "intent, natural keyword usage, scannable structure, and internal linking. "
    "Never invent statistics or fake sources."
)


def _build_prompt(primary_kw: str, site_url: str) -> str:
    links = "\n".join(f"- {path} — {label}" for path, label in INTERNAL_LINKS.items())
    secondary = ", ".join(k for k in KEYWORDS if k != primary_kw)
    return f"""Write ONE in-depth SEO blog post targeting the primary keyword: "{primary_kw}".

LENGTH IS A HARD REQUIREMENT: body_markdown MUST be 1500-2500 words. A short post
is a failure. Reach the length by being genuinely thorough, not by padding: cover
the topic from multiple angles with concrete detail, examples, and edge cases.

Structure (aim for 7-10 ## H2 sections, each 2-4 paragraphs, plus lists):
- Short intro (2-3 sentences) that leads with the answer and uses the primary keyword.
- What it is / how it works.
- Step-by-step how-to (numbered list).
- Formats, options, or comparisons relevant to the keyword.
- Common problems / mistakes and how to avoid them.
- Accuracy, security, or best-practice considerations where relevant.
- A short closing that positions Bank Statement Scanner as the tool for the job.

SEO rules:
- Use the primary keyword in the first paragraph and in at least two H2 headings;
  use it naturally throughout (no stuffing). Weave in secondary keywords where they fit.
- You MUST include 3-6 INTERNAL links, using ONLY these exact relative paths, each at
  most once, with natural in-sentence anchor text (not "click here"):
{links}
- Do NOT add a markdown H1 ('# ...') — the site renders the title separately. Start
  with the intro paragraph, then use ## for sections.
- Do NOT invent external URLs, statistics, or citations.

Secondary keywords to draw from where relevant: {secondary}

Return the structured object. body_markdown is the full 1500-2500 word article body
(markdown, no frontmatter, no H1)."""


class _BlogPost(BaseModel):
    """Structured schema so Gemini returns valid, parseable JSON."""

    title: str = Field(description="On-page H1, <=70 chars, contains the keyword idea")
    seoTitle: str = Field(description="<title> tag, <=60 chars, keyword-first")
    excerpt: str = Field(description="Meta description, 140-160 chars, includes keyword")
    slug: str = Field(description="kebab-case, <=60 chars")
    category: str = Field(description=f"one of {CATEGORIES}")
    tags: list[str] = Field(description="4-8 short lowercase SEO keyword tags")
    body_markdown: str = Field(description="Full 1500-2500 word article body, markdown, no frontmatter")


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def _generate_post(primary_kw: str, site_url: str, model: str) -> dict:
    client = _get_client()
    prompt = _build_prompt(primary_kw, site_url)
    data: dict = {}
    for attempt in range(2):
        contents = prompt
        if attempt == 1:
            contents = (
                prompt
                + f"\n\nYour previous draft was only {_word_count(data.get('body_markdown', ''))} "
                "words — too short. Rewrite it much longer (1500-2500 words) by adding more "
                "sections, detail, and examples, and make sure the required internal links are present."
            )
        resp = client.models.generate_content(
            model=model,
            contents=contents,
            config=GenerateContentConfig(
                system_instruction=_SYSTEM,
                temperature=0.8,
                max_output_tokens=8192,
                response_mime_type="application/json",
                response_schema=_BlogPost,
            ),
        )
        parsed = getattr(resp, "parsed", None)
        if isinstance(parsed, _BlogPost):
            data = parsed.model_dump()
        else:  # Fallback: parse raw text if SDK didn't hydrate .parsed.
            data = json.loads((resp.text or "").strip())
        for req in ("title", "excerpt", "slug", "body_markdown"):
            if not data.get(req):
                raise ValueError(f"Gemini output missing '{req}'")
        if _word_count(data["body_markdown"]) >= 1300:
            break
    return data


# --- Frontmatter --------------------------------------------------------------

def _yaml_escape(s: str) -> str:
    return s.replace('"', '\\"')


def _build_markdown(data: dict, image_path: str, today: date) -> str:
    words = len(re.findall(r"\w+", data["body_markdown"]))
    tags = data.get("tags") or []
    tags_yaml = "\n".join(f'  - "{_yaml_escape(t)}"' for t in tags)
    category = data.get("category") if data.get("category") in CATEGORIES else "Guides"
    fm = [
        "---",
        f'title: "{_yaml_escape(data["title"])}"',
        f'seoTitle: "{_yaml_escape(data.get("seoTitle") or data["title"])}"',
        f'excerpt: "{_yaml_escape(data["excerpt"])}"',
        f"date: {today.isoformat()}",
        f'category: "{category}"',
        f'readTime: "{_read_time(words)}"',
        f'image: "{image_path}"',
    ]
    if tags_yaml:
        fm.append("tags:")
        fm.append(tags_yaml)
    fm.append("---")
    return "\n".join(fm) + "\n\n" + data["body_markdown"].strip() + "\n"


# --- Public entrypoint --------------------------------------------------------

def generate_and_publish() -> dict:
    """Generate one post and commit it. Returns a summary dict."""
    repo = _env("GITHUB_REPO", required=True)
    branch = _env("GITHUB_BRANCH", "main")
    site_url = _env("SITE_URL", "https://bankstatementscanner.com")
    model = _env("GEMINI_BLOG_MODEL", "gemini-flash-latest")
    today = datetime.now(timezone.utc).date()

    existing = _existing_slugs(repo, branch)

    # Rotate keyword by day-of-year; skip ones whose obvious slug already exists.
    start = today.timetuple().tm_yday % len(KEYWORDS)
    order = KEYWORDS[start:] + KEYWORDS[:start]

    last_err: Exception | None = None
    for primary_kw in order:
        try:
            data = _generate_post(primary_kw, site_url, model)
        except Exception as e:  # noqa: BLE001 — retry next keyword on model/parse error
            logger.warning("Generation failed for '%s': %s", primary_kw, e)
            last_err = e
            continue

        slug = _slugify(data["slug"]) or _slugify(primary_kw)
        if slug in existing:
            slug = f"{slug}-{today.isoformat()}"
        if slug in existing:
            continue  # extremely unlikely; move on

        image_path = f"/blog/images/{slug}.jpg"
        img_bytes = _fetch_finance_image()
        md = _build_markdown(data, image_path, today)

        # One atomic commit (markdown + image) => a single Vercel rebuild.
        commit = _gh_commit_files(
            repo,
            branch,
            [
                (f"{CONTENT_DIR}/{slug}.md", md.encode()),
                (f"{IMAGE_DIR}/{slug}.jpg", img_bytes),
            ],
            f"blog: {data['title']}",
        )

        words = len(re.findall(r"\w+", data["body_markdown"]))
        logger.info("Published blog '%s' (%d words) targeting '%s'", slug, words, primary_kw)
        return {
            "slug": slug,
            "title": data["title"],
            "keyword": primary_kw,
            "word_count": words,
            "tags": data.get("tags") or [],
            "url": f"{site_url}/blog/{slug}",
            "commit_url": commit.get("html_url"),
        }

    raise RuntimeError(f"All keywords failed to generate. Last error: {last_err}")
