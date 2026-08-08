#!/usr/bin/env python3
"""Driver for the daily SEO blog generator.

Two modes:

  dry-run   Generate ONE post with Gemini (+ Pixabay if PIXABAY_API_KEY is set)
            and write the markdown to disk. Does NOT commit to GitHub. This is
            the fast inner-loop check when you change prompts, keywords, links,
            or frontmatter — it exercises services/blog_generator.py directly.

  smoke     POST the live backend endpoint (this DOES generate + commit a real
            post). Needs BACKEND_URL and API_AUTH_SECRET.

Run from the backend/ dir so backend/.env (GOOGLE_GEMINI_API_KEY) loads:
    cd backend
    python3 ../.claude/skills/run-blog-generator/driver.py dry-run
    python3 ../.claude/skills/run-blog-generator/driver.py smoke https://api.example.com SECRET
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Make backend/ importable and load backend/.env regardless of CWD.
BACKEND = Path(__file__).resolve().parents[3] / "backend"
sys.path.insert(0, str(BACKEND))
try:
    from dotenv import load_dotenv

    load_dotenv(BACKEND / ".env")
except Exception:
    pass

OUT = Path(
    os.environ.get("BLOG_DRY_RUN_DIR")
    or "/private/tmp/claude-501/-Users-taaharauf-Documents-Documents-Documents-Dev-projects-pdf-reading-agent"
    "/0c9efcaa-3085-450c-a1a1-7a3a4061bd3b/scratchpad"
)


def dry_run() -> int:
    import services.blog_generator as b

    if not os.environ.get("GOOGLE_GEMINI_API_KEY"):
        print("GOOGLE_GEMINI_API_KEY not set; run from backend/ with .env present.")
        return 1

    today = datetime.now(timezone.utc).date()
    kw = b.KEYWORDS[today.timetuple().tm_yday % len(b.KEYWORDS)]
    model = os.environ.get("GEMINI_BLOG_MODEL", "gemini-2.5-flash")
    print(f"→ keyword: {kw!r}  model: {model}")

    data = b._generate_post(kw, "https://bankstatementscanner.com", model)
    slug = b._slugify(data["slug"]) or b._slugify(kw)
    md = b._build_markdown(data, f"/blog/images/{slug}.jpg", today)

    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / f"{slug}.md"
    dest.write_text(md)

    words = len(re.findall(r"\w+", data["body_markdown"]))
    links = sorted(set(re.findall(r"\]\((/[^)]*)\)", data["body_markdown"])))
    print(f"✓ wrote {dest}")
    print(f"  title:    {data['title']}")
    print(f"  seoTitle: {data.get('seoTitle')}")
    print(f"  words:    {words}  ({'OK' if 1500 <= words <= 2600 else 'OUT OF RANGE'})")
    print(f"  tags:     {data.get('tags')}")
    print(f"  internal links ({len(links)}): {links}")
    bad = [l for l in links if l not in b.INTERNAL_LINKS]
    if bad:
        print(f"  ⚠ links not in allow-list: {bad}")
    if not os.environ.get("PIXABAY_API_KEY"):
        print("  (PIXABAY_API_KEY unset — image fetch skipped in dry-run)")
    return 0


def smoke(url: str, secret: str) -> int:
    import httpx

    print(f"→ POST {url}/admin/generate-blog")
    r = httpx.post(
        f"{url.rstrip('/')}/admin/generate-blog",
        headers={"Authorization": f"Bearer {secret}"},
        timeout=300,
    )
    print(f"HTTP {r.status_code}")
    print(r.text)
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    args = sys.argv[1:]
    mode = args[0] if args else "dry-run"
    if mode == "dry-run":
        sys.exit(dry_run())
    if mode == "smoke":
        if len(args) < 3:
            print("usage: driver.py smoke <BACKEND_URL> <API_AUTH_SECRET>")
            sys.exit(2)
        sys.exit(smoke(args[1], args[2]))
    print(f"unknown mode {mode!r}; use 'dry-run' or 'smoke'")
    sys.exit(2)
