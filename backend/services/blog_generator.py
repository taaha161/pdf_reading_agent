"""Daily SEO blog generator.

Pipeline (all server-side, no local checkout needed):
  1. Pick the next TOPICS entry that isn't published and isn't covered by an\n     existing page (similarity guard); skip the day if none is left.
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

# One entry per search intent. Each topic owns a fixed slug, so a topic can be
# published at most once: if its slug exists, it's covered. Synonyms belong in
# `secondary`, never as separate topics; that is what used to produce near-copies.
# Topics are tried in order; add new ones at the end. Bank-specific and
# competitor topics live on /convert and /compare, not the blog.
TOPICS: list[dict] = [
    # Already published (kept so the registry documents what's covered).
    {"slug": "convert-bank-statements-to-csv", "keyword": "convert bank statements to csv",
     "secondary": ["bank statement to csv", "how to convert bank statement to csv"]},
    {"slug": "convert-bank-statement-pdf-to-excel", "keyword": "convert bank statement pdf to excel",
     "secondary": ["bank statement to excel", "bank statement pdf to excel", "how to export bank statement to excel"]},
    {"slug": "bank-statement-converter-guide", "keyword": "bank statement converter",
     "secondary": ["bank statement scanner", "pdf bank statement converter"]},
    {"slug": "free-bank-statement-converter", "keyword": "free bank statement converter",
     "secondary": ["bank statement extraction software free"]},
    {"slug": "bank-statement-extraction-software-guide", "keyword": "bank statement extraction software",
     "secondary": ["bank statement capture tool", "bank statement software", "bank statement to excel software"]},
    {"slug": "best-bank-statement-analysis-software", "keyword": "bank statement analysis software", "secondary": []},
    {"slug": "financial-data-extraction-software", "keyword": "financial data extraction software", "secondary": []},
    {"slug": "convert-scanned-bank-statement-ocr", "keyword": "bank statement ocr",
     "secondary": ["scan bank statements", "ocr bank statements to excel"]},
    {"slug": "bank-statement-organizer", "keyword": "bank statement organizer", "secondary": []},
    {"slug": "bank-statement-automation", "keyword": "bank statement automation", "secondary": []},
    {"slug": "convert-credit-card-statement-to-excel", "keyword": "convert credit card statement to excel",
     "secondary": ["credit card statement converter", "credit card statement to excel"]},
    {"slug": "bookkeeping-made-easy-for-accountants", "keyword": "bookkeeping for accountants", "secondary": []},
    {"slug": "complete-guide-to-bookkeeping-software", "keyword": "bookkeeping software", "secondary": []},
    # Queue, in publish order (one every second day). Ideas come from the Oct 2026 business
    # report: small bookkeeping/tax practices, billing-fairness and accuracy pains,
    # ChatGPT-vs-converter, per-bank search demand, lending/visa/tax use cases.
    #   kind "bank":       how to get statements from one bank; links its /convert page.
    #   kind "comparison": methods and categories only; named competitors stay on
    #                      hand-sourced /compare pages (no invented vendor facts).
    # Head terms the overlap guard would block (their words appear in many posts);
    # `allow_overlap` lets them through because no page targets the exact query.
    {"slug": "bank-statement-pdf", "keyword": "bank statement pdf",
     "secondary": ["download bank statement pdf", "bank statement pdf format", "edit bank statement pdf"],
     "allow_overlap": True,
     "angle": "a hub for the head term: how to get an official PDF from online banking, what a genuine one "
              "contains, why PDFs can't be edited legitimately, opening password-protected files, and getting "
              "the data out into a spreadsheet"},
    {"slug": "bank-statement-generator", "keyword": "bank statement generator",
     "secondary": ["fake bank statement", "bank statement template", "proof of address bank statement"],
     "allow_overlap": True,
     "angle": "answer the searcher honestly: generated or edited statements presented as real are document "
              "fraud and lenders, landlords, and consulates verify them; then cover the legitimate needs behind "
              "the search (official statements, bank letters, proof of address or funds, sample data for "
              "testing software) and how to get each"},
    {"slug": "reconcile-bank-statement-in-excel", "keyword": "how to reconcile a bank statement in excel",
     "secondary": ["bank reconciliation excel"], "angle": "a hands-on reconciliation walkthrough with formulas"},
    {"slug": "pay-as-you-go-vs-subscription-bank-statement-converter", "keyword": "bank statement converter no subscription",
     "secondary": ["pay as you go bank statement converter", "per page vs per statement pricing"], "kind": "comparison",
     "angle": "pricing models compared: annual page plans, monthly plans, per-statement credits, free tiers; who each suits"},
    {"slug": "how-to-download-bank-of-america-statements", "keyword": "how to download bank of america statements",
     "secondary": ["bank of america statement pdf"], "kind": "bank", "bank": "Bank of America", "convert_path": "/convert/bank-of-america-statement-to-excel"},
    {"slug": "catch-up-bookkeeping-bank-statements", "keyword": "catch-up bookkeeping",
     "secondary": ["behind on bookkeeping"], "angle": "rebuilding months or years of books from statements"},
    {"slug": "manual-data-entry-vs-bank-statement-converter", "keyword": "manual data entry vs bank statement converter",
     "secondary": ["retyping bank statements"], "kind": "comparison",
     "angle": "time, error rates in practice, cost, and when manual entry is still fine"},
    {"slug": "how-to-download-wells-fargo-statements", "keyword": "how to download wells fargo statements",
     "secondary": ["wells fargo statement pdf"], "kind": "bank", "bank": "Wells Fargo", "convert_path": "/convert/wells-fargo-statement-to-excel"},
    {"slug": "tax-season-checklist-bank-statements", "keyword": "tax preparation bank statements",
     "secondary": ["tax season checklist"], "angle": "a checklist for gathering and organizing statements for taxes"},
    {"slug": "bank-feeds-vs-bank-statement-imports", "keyword": "bank feeds vs bank statements",
     "secondary": ["bank feed missing transactions"], "kind": "comparison",
     "angle": "live bank feeds vs statement imports for bookkeeping: gaps, history limits, and when you need statements"},
    {"slug": "how-to-download-citi-statements", "keyword": "how to download citi statements",
     "secondary": ["citi statement pdf"], "kind": "bank", "bank": "Citi", "convert_path": "/convert/citibank-statement-to-excel"},
    {"slug": "check-converted-bank-statement-for-errors", "keyword": "check converted bank statement for errors",
     "secondary": ["bank statement tie out"], "angle": "verifying any converter or AI output: balance tie-out, row counts, sign checks"},
    {"slug": "how-to-download-capital-one-statements", "keyword": "how to download capital one statements",
     "secondary": ["capital one statement pdf"], "kind": "bank", "bank": "Capital One", "convert_path": "/convert/capital-one-statement-to-excel"},
    {"slug": "bank-statements-for-mortgage-application", "keyword": "bank statements for mortgage application",
     "secondary": [], "angle": "what lenders check and how to prepare statements"},
    {"slug": "desktop-vs-online-bank-statement-converter", "keyword": "desktop vs online bank statement converter",
     "secondary": ["offline bank statement converter"], "kind": "comparison",
     "angle": "installed software vs web tools: privacy, scanned PDFs, updates, cost"},
    {"slug": "how-to-download-amex-statements", "keyword": "how to download american express statements",
     "secondary": ["american express statement pdf"], "kind": "bank", "bank": "American Express", "convert_path": "/convert/amex-statement-to-excel"},
    {"slug": "bank-statements-for-small-business-loan", "keyword": "bank statements for small business loan",
     "secondary": ["loan application bank statements"], "angle": "what lenders and brokers look for and how to prepare a clean file"},
    {"slug": "how-to-download-us-bank-statements", "keyword": "how to download u.s. bank statements",
     "secondary": ["u.s. bank statement pdf"], "kind": "bank", "bank": "U.S. Bank"},
    {"slug": "ocr-vs-ai-bank-statement-extraction", "keyword": "ocr vs ai bank statement extraction",
     "secondary": ["template vs ai extraction"], "kind": "comparison",
     "angle": "template OCR, generic chatbots, and purpose-built AI pipelines compared"},
    {"slug": "how-to-download-pnc-statements", "keyword": "how to download pnc statements",
     "secondary": ["pnc statement pdf"], "kind": "bank", "bank": "PNC"},
    {"slug": "bank-statement-for-visa-application", "keyword": "bank statement for visa application",
     "secondary": ["proof of funds"], "angle": "proof-of-funds documents: what consulates usually ask for and how to present them"},
    {"slug": "how-to-download-truist-statements", "keyword": "how to download truist statements",
     "secondary": ["truist statement pdf"], "kind": "bank", "bank": "Truist"},
    {"slug": "bank-statements-and-ai-privacy", "keyword": "upload bank statements to ai safely",
     "secondary": ["chatgpt bank statement privacy"], "angle": "training settings, redaction, retention; questions to ask any AI tool"},
    {"slug": "how-to-download-td-bank-statements", "keyword": "how to download td bank statements",
     "secondary": ["td bank statement pdf"], "kind": "bank", "bank": "TD Bank"},
    {"slug": "find-duplicate-transactions-in-excel", "keyword": "find duplicate transactions in excel",
     "secondary": [], "angle": "spotting and removing double-counted rows"},
    {"slug": "categorize-business-expenses-from-bank-statements", "keyword": "categorize business expenses",
     "secondary": ["expense categories for small business"], "angle": "building a category list and applying it to transactions"},
    {"slug": "how-to-download-ally-statements", "keyword": "how to download ally statements",
     "secondary": ["ally statement pdf"], "kind": "bank", "bank": "Ally"},
    {"slug": "excel-vs-google-sheets-for-bookkeeping", "keyword": "excel vs google sheets for bookkeeping",
     "secondary": [], "kind": "comparison", "angle": "formulas, collaboration, imports, and limits for small-business books"},
    {"slug": "qbo-ofx-qfx-csv-file-formats-explained", "keyword": "qbo vs ofx vs qfx",
     "secondary": ["bank file formats"], "kind": "comparison", "angle": "which import format each accounting tool expects"},
    {"slug": "how-to-download-navy-federal-statements", "keyword": "how to download navy federal statements",
     "secondary": ["navy federal statement pdf"], "kind": "bank", "bank": "Navy Federal"},
    {"slug": "how-long-to-keep-bank-statements", "keyword": "how long to keep bank statements",
     "secondary": ["bank statement retention"], "angle": "personal and business record retention"},
    {"slug": "proof-of-income-from-bank-statements", "keyword": "proof of income bank statements",
     "secondary": ["self-employed proof of income"], "angle": "self-employed and freelance income documentation"},
    {"slug": "how-to-download-chime-statements", "keyword": "how to download chime statements",
     "secondary": ["chime statement pdf"], "kind": "bank", "bank": "Chime"},
    {"slug": "prepare-bank-statements-for-your-accountant", "keyword": "what to send your accountant",
     "secondary": ["documents for cpa"], "angle": "what to hand over and in what format"},
    {"slug": "bank-statements-for-schedule-c", "keyword": "schedule c expenses from bank statements",
     "secondary": [], "angle": "sole-proprietor expense tracking for the US Schedule C"},
    {"slug": "how-to-download-sofi-statements", "keyword": "how to download sofi statements",
     "secondary": ["sofi statement pdf"], "kind": "bank", "bank": "SoFi"},
    {"slug": "separate-personal-and-business-transactions", "keyword": "separate personal and business expenses",
     "secondary": ["mixed bank account bookkeeping"], "angle": "untangling a mixed-use account"},
    {"slug": "map-bank-transactions-to-chart-of-accounts", "keyword": "chart of accounts for small business",
     "secondary": [], "angle": "mapping exported transactions to accounts"},
    {"slug": "how-to-download-charles-schwab-statements", "keyword": "how to download charles schwab statements",
     "secondary": ["charles schwab statement pdf"], "kind": "bank", "bank": "Charles Schwab"},
    {"slug": "find-recurring-subscriptions-in-bank-statement", "keyword": "find subscriptions on bank statement",
     "secondary": ["recurring charges"], "angle": "finding and cancelling recurring charges"},
    {"slug": "budget-from-bank-statements-google-sheets", "keyword": "budget from bank statements",
     "secondary": ["google sheets budget"], "angle": "building a monthly budget in Google Sheets from exported transactions"},
    {"slug": "what-is-on-a-bank-statement", "keyword": "what is a bank statement",
     "secondary": ["how to read a bank statement"], "angle": "a plain-language explainer of each part of a statement"},
    {"slug": "bank-statement-vs-transaction-history", "keyword": "bank statement vs transaction history",
     "secondary": [], "kind": "comparison", "angle": "when each document is accepted and why they differ"},
    {"slug": "how-to-read-a-credit-card-statement", "keyword": "how to read a credit card statement",
     "secondary": [], "angle": "billing cycles, minimum payments, interest, and fees"},
    {"slug": "open-password-protected-pdf-bank-statement", "keyword": "password protected bank statement pdf",
     "secondary": [], "angle": "why statements are protected and how to work with them safely"},
    {"slug": "cash-flow-report-from-bank-transactions", "keyword": "cash flow from bank transactions excel",
     "secondary": [], "angle": "a simple monthly cash-flow view built from transactions"},
    {"slug": "pivot-tables-for-bank-transactions", "keyword": "pivot table bank transactions",
     "secondary": [], "angle": "summarizing spending by category and month"},
    {"slug": "clean-transaction-descriptions-in-excel", "keyword": "clean up bank transaction descriptions",
     "secondary": [], "angle": "normalizing merchant names with formulas"},
    {"slug": "analyze-bank-statements-for-divorce-or-litigation", "keyword": "forensic bank statement analysis",
     "secondary": [], "angle": "tracing transactions for legal matters"},
]

# Non-blog pages that already own a search intent. The similarity guard checks
# against these too, and they are offered as internal-link targets.
STATIC_PAGES: dict[str, str] = {
    "/": "Bank Statement Scanner: upload a PDF, export CSV or Excel",
    "/convert": "Supported banks",
    "/convert/chase-bank-statement-to-excel": "Convert Chase bank statements to Excel",
    "/convert/bank-of-america-statement-to-excel": "Convert Bank of America statements to Excel",
    "/convert/wells-fargo-statement-to-excel": "Convert Wells Fargo statements to Excel",
    "/convert/citibank-statement-to-excel": "Convert Citibank statements to Excel",
    "/convert/capital-one-statement-to-excel": "Convert Capital One statements to Excel",
    "/convert/amex-statement-to-excel": "Convert Amex statements to Excel",
    "/compare/docuclipper-alternative": "DocuClipper alternative",
    "/compare/chatgpt-for-bank-statements": "ChatGPT for bank statements",
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


def _parse_frontmatter(text: str) -> dict:
    """Pull the few scalar fields we need from a post's YAML frontmatter."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    out: dict = {}
    for key in ("title", "seoTitle", "keyword"):
        fm = re.search(rf'^{key}:\s*"?(.*?)"?\s*$', m.group(1) if m else "", re.M)
        if fm:
            out[key] = fm.group(1).replace('\\"', '"')
    return out


def _existing_posts(repo: str, branch: str) -> dict[str, dict]:
    """slug -> frontmatter for every post on `branch`.

    Raises on failure: without the corpus we can't rule out duplicates, so it's
    safer to skip a day than to publish blind.
    """
    listing = httpx.get(
        f"https://api.github.com/repos/{repo}/contents/{CONTENT_DIR}",
        headers=_gh_headers(), params={"ref": branch}, timeout=20,
    )
    listing.raise_for_status()
    posts: dict[str, dict] = {}
    with httpx.Client(headers=_gh_headers(), timeout=20) as client:
        for item in listing.json():
            name = item.get("name", "")
            if item.get("type") != "file" or not name.endswith(".md"):
                continue
            raw = client.get(item["download_url"])
            raw.raise_for_status()
            posts[name[:-3]] = _parse_frontmatter(raw.text)
    return posts


def local_posts(content_dir: str) -> dict[str, dict]:
    """Same as _existing_posts but from a local checkout (used by the dry-run driver)."""
    posts = {}
    for name in os.listdir(content_dir):
        if name.endswith(".md"):
            with open(os.path.join(content_dir, name)) as f:
                posts[name[:-3]] = _parse_frontmatter(f.read())
    return posts


# --- Duplicate guard ----------------------------------------------------------

# Words every post here shares, or that carry no topic meaning. Dropping them
# makes overlap reflect what a page is actually about.
_STOP = set(
    "a an the to and or for of in on with your you how what why when is are from into by vs "
    "guide complete step steps best easy fast quick quickly accurate accurately ultimate modern "
    "top tool tools way ways using use 2024 2025 2026 bank statement statements".split()
)

# A candidate counts as covered when this share of its topic words already
# appear in one existing page's slug/title/keyword.
COVERED_THRESHOLD = 0.75
# A generated title is rejected when it overlaps an existing title this much (Jaccard).
TITLE_JACCARD_THRESHOLD = 0.6


# Word forms and near-synonyms that signal the same intent.
_NORMALIZE = {
    "converter": "convert", "conversion": "convert", "converting": "convert", "converted": "convert",
    "extraction": "extract", "extracting": "extract", "extractor": "extract", "capture": "extract",
    "scanner": "scan", "scanning": "scan", "scanned": "scan",
    "spreadsheet": "excel", "xlsx": "excel",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = set()
    for w in words:
        if w in _STOP:
            continue
        w = _NORMALIZE.get(w, w)
        out.add(w[:-1] if len(w) > 3 and w.endswith("s") else w)
    return out


def _page_tokens(slug_or_path: str, meta: dict) -> set[str]:
    parts = [slug_or_path.replace("/", " ").replace("-", " ")]
    parts += [meta.get(k, "") for k in ("title", "seoTitle", "keyword")]
    return _tokens(" ".join(parts))


def _corpus_tokens(posts: dict[str, dict]) -> dict[str, set[str]]:
    docs = {f"/blog/{slug}": _page_tokens(slug, meta) for slug, meta in posts.items()}
    docs.update({path: _page_tokens(path, {"title": title}) for path, title in STATIC_PAGES.items()})
    return docs


def find_overlap(text: str, docs: dict[str, set[str]]) -> str | None:
    """Path of an existing page that already covers `text`, else None."""
    want = _tokens(text)
    if not want:
        return None
    for path, have in docs.items():
        if len(want & have) / len(want) >= COVERED_THRESHOLD:
            return path
    return None


def _title_clash(title: str, posts: dict[str, dict]) -> str | None:
    new = _tokens(title)
    for slug, meta in posts.items():
        old = _tokens(meta.get("title", ""))
        if new and old and len(new & old) / len(new | old) >= TITLE_JACCARD_THRESHOLD:
            return slug
    return None


def pick_topic(posts: dict[str, dict]) -> tuple[dict | None, list[str]]:
    """First registry topic that isn't published and isn't covered by another page.

    Returns (topic or None, human-readable reasons for each skipped topic).
    """
    docs = _corpus_tokens(posts)
    skipped = []
    for topic in TOPICS:
        if topic["slug"] in posts:
            continue
        clash = None if topic.get("allow_overlap") else find_overlap(topic["keyword"], docs)
        if clash:
            skipped.append(f"{topic['slug']}: covered by {clash}")
            continue
        return topic, skipped
    return None, skipped


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


def _internal_links(posts: dict[str, dict]) -> dict[str, str]:
    links = dict(STATIC_PAGES)
    for slug, meta in sorted(posts.items()):
        links[f"/blog/{slug}"] = meta.get("title") or slug
    return links


_KIND_RULES = {
    "bank": """
This is a guide to getting statements out of {bank}. Accuracy rules: describe online
banking navigation only in general terms (sign in, open the account, find the
statements or documents section) and say that menu labels change. Do NOT state
{bank}-specific menu names, how many months or years are available, download limits,
fees, phone numbers, or app features: you cannot verify them. Do not imply any
affiliation with {bank}. You MUST link {convert_path} with anchor text about converting
{bank} statements to Excel or CSV.
""",
    "comparison": """
This is a comparison of methods or product categories, not of named companies. Do NOT
name, price, rate, or describe specific competing products. For named comparisons,
link /compare/docuclipper-alternative or /compare/chatgpt-for-bank-statements instead.
Include a comparison table in markdown, present trade-offs fairly, and say plainly
when Bank Statement Scanner is not the right choice.
""",
}


def _build_prompt(topic: dict, posts: dict[str, dict]) -> str:
    links = "\n".join(f"- {path} — {label}" for path, label in _internal_links(posts).items())
    existing = "\n".join(f"- {m.get('title') or s}" for s, m in sorted(posts.items()))
    secondary = ", ".join(topic.get("secondary") or []) or "none"
    angle = topic.get("angle") or "the most useful practical angle for this keyword"
    kind_rules = _KIND_RULES.get(topic.get("kind", ""), "").format(
        bank=topic.get("bank", ""), convert_path=topic.get("convert_path") or "/convert"
    )
    return f"""Write ONE in-depth SEO blog post targeting the primary keyword: "{topic['keyword']}".
Angle: {angle}.
{kind_rules}

The site ALREADY has the articles below. Do not repeat their scope. This post must
answer a different question; where a reader needs background they cover, link to
them instead of re-explaining (e.g. don't write another general "how to convert a
bank statement to Excel/CSV" walkthrough):
{existing}

LENGTH IS A HARD REQUIREMENT: body_markdown MUST be 1500-2500 words. Reach the length
by being genuinely thorough on THIS topic: concrete detail, worked examples, edge
cases. No padding and no generic converter boilerplate.

Structure (aim for 7-10 ## H2 sections, each 2-4 paragraphs, plus lists):
- Short intro (2-3 sentences) that leads with the answer and uses the primary keyword.
- The core explanation, then a numbered step-by-step section.
- Common problems / mistakes and how to avoid them.
- A "## Frequently asked questions" section with 3-5 ### questions real searchers ask,
  each answered directly in 2-4 sentences.
- A short closing; mention Bank Statement Scanner only where it genuinely helps.

Quality rules (Google's helpful-content standard: written for people, not rankings):
- Every section must teach something specific: a concrete step, a decision rule, a
  pitfall with its fix, or a worked example. Cut any sentence a reader could skip
  without losing information.
- Include at least one worked example the reader can follow: a small markdown table of
  sample transactions (clearly labeled as sample data), a formula, or a checklist.
- Answer the reader's likely follow-up questions inside the article.
- Plain, direct language. Never use: "in today's fast-paced world", "delve", "navigate
  the complexities", "unlock", "game-changer", "seamless", "look no further",
  "in conclusion", "it's important to note", "whether you're a".

Product facts (do not claim anything beyond these): Bank Statement Scanner converts
one PDF bank or credit card statement at a time (digital, scanned, or
password-protected) into CSV or Excel with columns date, description, amount,
credit/debit type, and an AI category. It has an incognito mode that stores no
transaction data. It does NOT export QBO/OFX/Xero files, does NOT reconcile
balances automatically, and does NOT batch-upload multiple files.

SEO rules:
- Use the primary keyword in the first paragraph and in at least two H2 headings;
  use it naturally (no stuffing). Secondary keywords where they fit: {secondary}
- You MUST include 3-6 INTERNAL links, using ONLY these exact relative paths, each at
  most once, with natural in-sentence anchor text (not "click here"):
{links}
- Do NOT add a markdown H1 ('# ...'). Start with the intro paragraph, then ## sections.
- Do NOT invent external URLs, statistics, percentages, citations, or the current year, and
  never write "research shows" or "studies show". Plain-number examples must be
  labeled as hypothetical ("for example, a statement with 200 rows...").

Return the structured object. body_markdown is the full 1500-2500 word article body
(markdown, no frontmatter, no H1)."""


class _BlogPost(BaseModel):
    """Structured schema so Gemini returns valid, parseable JSON."""

    title: str = Field(description="On-page H1, <=70 chars, contains the keyword idea")
    seoTitle: str = Field(description="<title> tag, <=60 chars, keyword-first")
    excerpt: str = Field(description="Meta description, 140-160 chars, includes keyword")
    category: str = Field(description=f"one of {CATEGORIES}")
    tags: list[str] = Field(description="4-8 short lowercase SEO keyword tags")
    body_markdown: str = Field(description="Full 1500-2500 word article body, markdown, no frontmatter")


def _word_count(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


# Statistics the model can't source: percentages, and attributions to unnamed
# research. Worked examples with plain numbers ("if a statement has 220 rows") are fine.
_UNSOURCED = re.compile(
    r"\d+(?:\.\d+)?\s?%|\bper ?cent\b|"
    r"\b(?:research|studies|study|surveys?|experts?|industry reports?)\s+"
    r"(?:\w+\s+){0,2}(?:shows?|suggests?|finds?|found|indicates?|estimates?)\b|"
    r"\baccording to\b",
    re.I,
)


# Stock phrasing that marks text as generic AI filler; the prompt bans these too.
_FILLER = re.compile(
    r"in today's fast-paced|\bdelve|navigat\w* the complexit|\bunlock\w*|game[- ]changer|"
    r"\bseamless\w*|look no further|\bin conclusion\b|it's important to note|whether you're an? ",
    re.I,
)


def filler_phrases(body: str) -> list[str]:
    """Banned filler phrases found in the draft, lowercased and deduplicated."""
    return sorted({m.group(0).lower() for m in _FILLER.finditer(body or "")})


def unsourced_claims(body: str) -> list[str]:
    """Sentences containing statistics or research claims we can't back up."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", body or "")
    return [s.strip() for s in sentences if _UNSOURCED.search(s)]


class UnsourcedClaimsError(ValueError):
    """The model kept unsupported statistics after being asked to remove them."""


def _generate_post(topic: dict, posts: dict[str, dict], model: str) -> dict:
    client = _get_client()
    prompt = _build_prompt(topic, posts)
    data: dict = {}
    problems: list[str] = []
    for attempt in range(3):
        contents = prompt
        if problems:
            contents = prompt + "\n\nYour previous draft had problems. Rewrite the whole post and fix them:\n" + "\n".join(
                f"- {p}" for p in problems
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
        for req in ("title", "excerpt", "body_markdown"):
            if not data.get(req):
                raise ValueError(f"Gemini output missing '{req}'")

        problems = []
        words = _word_count(data["body_markdown"])
        if words < 1300:
            problems.append(
                f"It was only {words} words. Make it 1500-2500 words with more sections, detail, "
                "and examples, and keep the required internal links."
            )
        claims = unsourced_claims(data["body_markdown"] + "\n" + data["excerpt"])
        if claims:
            problems.append(
                "It contained statistics or research claims with no source. Remove every percentage "
                "and every 'research/studies/data shows' or 'according to' claim; describe the point "
                "qualitatively or as a clearly labeled hypothetical example instead. Offending sentences: "
                + " | ".join(c[:160] for c in claims[:6])
            )
        filler = filler_phrases(data["body_markdown"])
        if filler:
            problems.append("It used banned filler phrases; rewrite those sentences plainly: " + ", ".join(filler))
        if "frequently asked questions" not in data["body_markdown"].lower():
            problems.append('It had no "## Frequently asked questions" section; add one with 3-5 ### questions.')
        if not problems:
            return data
    if unsourced_claims(data["body_markdown"] + "\n" + data["excerpt"]):
        raise UnsourcedClaimsError("draft still contains unsourced statistics after retries")
    return data  # Short but clean: same tolerance as before.


# --- Frontmatter --------------------------------------------------------------

def _yaml_escape(s: str) -> str:
    return s.replace('"', '\\"')


def _build_markdown(data: dict, image_path: str, today: date, keyword: str) -> str:
    words = len(re.findall(r"\w+", data["body_markdown"]))
    tags = data.get("tags") or []
    tags_yaml = "\n".join(f'  - "{_yaml_escape(t)}"' for t in tags)
    category = data.get("category") if data.get("category") in CATEGORIES else "Guides"
    fm = [
        "---",
        f'title: "{_yaml_escape(data["title"])}"',
        f'seoTitle: "{_yaml_escape(data.get("seoTitle") or data["title"])}"',
        f'excerpt: "{_yaml_escape(data["excerpt"])}"',
        f'keyword: "{_yaml_escape(keyword)}"',
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

def _ensure_bank_link(topic: dict, data: dict) -> None:
    """Bank guides must point readers at the matching /convert page; add it if the model didn't."""
    if topic.get("kind") != "bank":
        return
    path = topic.get("convert_path") or "/convert"
    if f"]({path})" not in data["body_markdown"]:
        data["body_markdown"] = (
            data["body_markdown"].rstrip()
            + f"\n\nReady to turn your statements into a spreadsheet? "
            f"[Convert {topic['bank']} statements to Excel or CSV]({path}).\n"
        )


def generate_and_publish() -> dict:
    """Generate one post for the next uncovered topic and commit it.

    Returns a summary dict. When every registry topic is covered it returns
    {"status": "skipped", ...} rather than writing a near-duplicate.
    """
    repo = _env("GITHUB_REPO", required=True)
    branch = _env("GITHUB_BRANCH", "main")
    site_url = _env("SITE_URL", "https://bankstatementscanner.com")
    model = _env("GEMINI_BLOG_MODEL", "gemini-flash-latest")
    today = datetime.now(timezone.utc).date()

    posts = _existing_posts(repo, branch)
    topic, skipped = pick_topic(posts)
    for reason in skipped:
        logger.info("Topic skipped, %s", reason)
    if topic is None:
        logger.info("No uncovered topics left; add entries to TOPICS")
        return {"status": "skipped", "reason": "all topics covered", "skipped": skipped}

    slug = topic["slug"]
    try:
        data = _generate_post(topic, posts, model)
    except UnsourcedClaimsError as e:
        logger.warning("Not publishing '%s': %s", slug, e)
        return {"status": "skipped", "reason": str(e), "slug": slug}

    clash = _title_clash(data["title"], posts)
    if clash:
        # The model drifted onto an existing post's subject; don't publish it.
        logger.warning("Generated title %r too close to /blog/%s; not publishing", data["title"], clash)
        return {"status": "skipped", "reason": f"title too close to /blog/{clash}", "slug": slug}

    _ensure_bank_link(topic, data)
    image_path = f"/blog/images/{slug}.jpg"
    img_bytes = _fetch_finance_image()
    md = _build_markdown(data, image_path, today, topic["keyword"])

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

    words = _word_count(data["body_markdown"])
    logger.info("Published blog '%s' (%d words) targeting '%s'", slug, words, topic["keyword"])
    return {
        "status": "published",
        "slug": slug,
        "title": data["title"],
        "keyword": topic["keyword"],
        "word_count": words,
        "tags": data.get("tags") or [],
        "url": f"{site_url}/blog/{slug}",
        "commit_url": commit.get("html_url"),
    }
