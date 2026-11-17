---
version: 1
slug: "marketing-src-pages-index-astro"
primary_target: "marketing/src/pages/index.astro"
related_targets: ["frontend/src/pages/ScannerPage.jsx"]
---

# Surface brief: homepage + guest scanner

Scope: marketing homepage (`marketing/src/pages/index.astro`) and the /scanner upload + results surface (`frontend/src/pages/ScannerPage.jsx`). Mode: Persuade (homepage), Operate (scanner). Shared header, footer and HeroDropzone restyle with it; other marketing templates and app screens inherit in later rounds.

Audience/job: bookkeepers, accountants, tax preparers and individuals holding a statement PDF. Action: drop a PDF (working drop zone), or try the sample. Proof: real sample statement rows, a question answered by highlighted rows, the demo video, honest pricing. Constraints: keep URLs, titles, meta, JSON-LD, SEO/FAQ copy. H1 A/B test retired (both texts kept as copy). Logo may be redrawn. Old `frontend/src/pages/Landing.jsx` deleted. Chat answers highlight their rows in the real scanner results table.

## Direction contract

THESIS: The site is a printed bank statement mid-review on a bookkeeper's desk; asking a question highlights the rows that answer it. It refuses the category's split hero of headline beside a floating dashboard screenshot over a row of feature cards.

OWN-WORLD: Neutral grey desk ground, white laser-printed statement sheets with a soft lift shadow, black print type with tabular figures (Public Sans), heavy grotesque headlines (Archivo, expanded to 112% width). Face change cited: Schibsted Grotesk was built first and rejected on render, because its heavy weights set a visible space before commas and periods ("clean ,", "seconds ."), which breaks a headline full of punctuation; Archivo's expanded cut reads as statement letterhead and sets punctuation tight. Yellow highlighter is the answer and primary emphasis, pink highlighter is the question, graphite pencil (Kalam) writes ticks and totals. No blue, no gradients, no purple, no glow. Buttons are black ink blocks.

STORY: The visitor sees their own kind of document already sorted and answered, believes the rows are real and the answer exact, and drops their own statement on the desk.

FIRST VIEWPORT: Desktop: a single statement sheet, turned about one degree, fills the left two-thirds from just under the nav to below the fold, rows from the real sample; a pink-marked question above the table and yellow swipes on its answer rows, pencil total in the right margin. Right third: headline, one sentence, the working drop zone with "Convert a statement free" in black, sample link under it. Mobile: headline, drop zone, then the sheet.

FORM: The Marked-Up Statement, position 1 on the ordered grounded list (taken as the pick over the rolled The Return). seed:a29d2cbddeb64ff4. Signature interaction: question chips re-run the highlighter swipe across the matching rows and rewrite the pencil total; in the scanner, chat answers highlight their rows in the results table. Motion grammar: one left-to-right highlighter swipe, static under reduced motion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
