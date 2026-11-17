---
name: Bank Statement Scanner
description: A printed bank statement mid-review on a bookkeeper's desk; asking a question highlights the rows that answer it.
colors:
  desk: "#e6e7e4"
  desk-deep: "#d9dbd7"
  paper: "#ffffff"
  ink: "#141414"
  ink-soft: "#4d4d4d"
  graphite: "#555a5f"
  rule: "#d4d5d1"
  hi: "#ffe34d"
  hi-soft: "#fff3a6"
  hi-pink: "#ff9ccb"
  neutral-tint: "#f1f1ee"
  success: "#1f7a3a"
  error: "#b3261e"
typography:
  display:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(34px, 3vw, 44px)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.03em"
    fontVariation: "'wdth' 112"
  display-close:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(38px, 5vw, 68px)"
    fontWeight: 800
    lineHeight: 1.02
    letterSpacing: "-0.035em"
    fontVariation: "'wdth' 112"
  headline:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "clamp(30px, 3.6vw, 44px)"
    fontWeight: 800
    lineHeight: 1.08
    letterSpacing: "-0.02em"
    fontVariation: "'wdth' 112"
  title:
    fontFamily: "Archivo Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "20px"
    fontWeight: 800
    lineHeight: 1.08
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' 112"
  body:
    fontFamily: "Public Sans Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "'tnum' 1"
  body-lead:
    fontFamily: "Public Sans Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.6
    fontFeature: "'tnum' 1"
  label:
    fontFamily: "Public Sans Variable, Helvetica Neue, Arial, sans-serif"
    fontSize: "12px"
    fontWeight: 700
    lineHeight: 1.2
    letterSpacing: "0.06em"
  pencil:
    fontFamily: "Kalam, Bradley Hand, cursive"
    fontSize: "20px"
    fontWeight: 400
    lineHeight: 1.15
rounded:
  sm: "2px"
  md: "3px"
  lg: "4px"
  pill: "999px"
spacing:
  gutter-mobile: "16px"
  gutter: "24px"
  sheet-pad-mobile: "18px"
  sheet-pad: "44px 48px"
  section-mobile: "72px"
  section: "104px"
  container: "1200px"
components:
  button-ink:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "12px 22px"
    height: "48px"
  button-ink-hover:
    backgroundColor: "#000000"
    textColor: "{colors.hi}"
  button-line:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "12px 20px"
    height: "48px"
  button-line-hover:
    backgroundColor: "{colors.hi}"
    textColor: "{colors.ink}"
  question-chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "4px 12px"
    height: "36px"
  question-chip-active:
    backgroundColor: "{colors.hi-pink}"
    textColor: "{colors.ink}"
  sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "0px"
    padding: "{spacing.sheet-pad}"
  drop-zone:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
    padding: "24px"
  drop-zone-hover:
    backgroundColor: "{colors.hi-soft}"
  nav-bar:
    backgroundColor: "{colors.desk}"
    textColor: "{colors.ink}"
    height: "68px"
---

# Design System: Bank Statement Scanner

## Overview

**Creative North Star: "The Marked-Up Statement"**

Every surface is a printed bank statement lying on a bookkeeper's desk, mid-review. The page ground is a neutral grey desk; content sits on white laser-printed sheets that lift off it with a soft shadow; type is black print with tabular figures. Review marks are the only colour: a yellow highlighter swipes the rows and words that answer, a pink highlighter marks the question, and a graphite pencil writes ticks and running totals in the margin. The product's core promise, ask a question and the rows that answer it light up, is the visual system itself, not an illustration of it.

Density is that of a real statement: identical ruled rows, right-aligned amounts, small uppercase column heads, headings set like statement letterhead in an expanded heavy grotesque. Nothing glows, floats in gradient space, or sits in a tinted feature card. Sheets are slightly turned, never perfectly square to the viewport, because paper on a desk never is.

This world replaced the earlier blue SaaS look across the marketing site and the app; legacy `--color-*` names are remapped into it so older templates inherit the world rather than fight it.

**Key Characteristics:**
- Grey desk ground, white sheets, black ink. Colour comes only from highlighter and pencil.
- Yellow means "this is the answer"; pink means "this is the question".
- Expanded heavy grotesque headings (Archivo at 112% width) over a tabular sans (Public Sans).
- Statement anatomy everywhere: ruled rows, a 2px ink rule under every sheet head, uppercase column labels.
- One motion: a left-to-right highlighter swipe, static under reduced motion.

## Colors

A near-achromatic paper-and-ink palette with three review-mark colours that carry all meaning.

### Primary
- **Statement Ink** (ink): all body print, headings, the 2px rules under sheet heads, and the solid black ink-block buttons. Also the legacy `--color-primary`, so every "primary" action in older templates renders as ink.

### Secondary
- **Answer Highlighter Yellow** (hi): the highlighter swipe behind answer rows, the emphasised words of a headline, text selection, the focus halo, and the hover text/fill of ink and line buttons. It marks what the reader is looking for.
- **Soft Highlighter** (hi-soft): a paler wash for hover on drop zones and unpressed question chips; a preview of the mark, not the mark.

### Tertiary
- **Question Pink** (hi-pink): the pressed question chip and inline pink highlights (`hl-pink`) on the question being asked. Never used on answers.

### Neutral
- **Desk Grey** (desk): page ground, sticky header and mobile sticky CTA bar.
- **Desk Shadow** (desk-deep): a deeper desk tone for recessed areas.
- **Paper White** (paper): every sheet, the drop zone, the close band and security strip.
- **Secondary Print** (ink-soft): dates, categories, captions, supporting copy (8.6:1 on paper).
- **Graphite** (graphite): pencil notes, drawn ticks, security icons (6.9:1 on paper).
- **Statement Rule** (rule): the 1px rule between rows and between fee columns.
- **Neutral Tint** (neutral-tint): row hover in the app results table and quiet panels such as the chat sign-up gate; the legacy `--color-primary-subtle`.
- **Success / Error** (success, error): form and upload status text only, with a 1px border on paper for errors.

### Named Rules
**The Highlighter Means Answer Rule.** Yellow is applied only to answers and the one emphasised phrase of a headline. If nothing on the screen answers a question, nothing on the screen is yellow except hover and focus feedback.

**The Pink Asks Rule.** Pink marks the question, and only the question. Never use pink for status, decoration, or a second accent.

**The No-Blue Rule.** No blue, no purple, no glow, and no decorative gradient fills. (The highlighter is drawn with a hard-stopped `linear-gradient` to fake a marker band; that is the only sanctioned use of a gradient.)

## Typography

**Display Font:** Archivo Variable, width axis, set at `font-stretch: 112%` (fallback Helvetica Neue, Arial)
**Body Font:** Public Sans Variable with tabular figures on by default (fallback Helvetica Neue, Arial)
**Hand Font:** Kalam 400 (fallback Bradley Hand, cursive)

**Character:** Archivo's expanded heavy cut reads as statement letterhead and sets punctuation tight; Public Sans is plain print with figures that line up in columns. Kalam is the pencil in the margin. All three are self-hosted through Fontsource in both the marketing layout and the app entry.

### Hierarchy
- **Display** (800, clamp(34px, 3vw, 44px), 1.02): the hero headline beside the hero sheet. The close section uses a larger display (800, clamp(38px, 5vw, 68px), 1.02).
- **Headline** (800, clamp(30px, 3.6vw, 44px), 1.08): section heads on the homepage.
- **Title** (800, 18 to 22px): sheet heads, bank names, step and audience heads, FAQ questions (700 at 18px), drop-zone title (22px).
- **Body** (400, 16px, 1.6): running copy; lead copy beside a section head at 17px, capped near 46 to 62ch.
- **Label** (700, 12px, 0.06em tracking, uppercase): statement column heads and balance labels only, the way a printed statement labels its columns. Fee tier names use the same voice at 15px, 0.08em.
- **Pencil** (Kalam 400, 19 to 22px, graphite, turned -1.5deg to -4deg): margin totals, the "Ask the statement for" prompt, short notes beside figures.

### Named Rules
**The Tabular Everything Rule.** `tabular-nums` is set on the root; amounts are right-aligned under right-aligned heads, so a column reads in one sweep.

**The Pencil Writes Numbers Rule.** Kalam is for handwritten annotations about the data (totals, counts, "new", a nudge to try it). It never sets a heading, a button, or body copy.

## Layout

A 1200px container with a 24px gutter (16px under 600px). The homepage is a stack of sheets on the desk: hero (sheet left at ~1.55fr, copy right at 1fr, 48px gap), then sections spaced 104px apart (72px under 600px). Lower sections pair a narrow head column with a wider body (0.8fr / 1.6 to 2fr), or put the whole section on a single sheet with a two-column head above a 2px ink rule.

Sheets pad 44px 48px on desktop and 18 to 28px on mobile. Statement rows have identical height (33px on the hero sheet, 2.6rem in the app) and 1px rules. At 1080px the hero stacks copy first, then sheet, and sheet rotations are removed; at 860px all multi-column sections collapse to one column and fee columns divide with ink rules instead of vertical rules. On phones a sticky ink CTA bar sits on the desk at the bottom of the viewport.

**The Rows Line Up Rule.** Every repeating list of facts (summary, fees, FAQ, steps, results) is a ruled list on paper, not a grid of cards.

## Elevation & Depth

Depth is physical and has one source: paper lifting off the desk. Sheets carry a two-layer soft shadow; everything on a sheet is flat, separated by rules. Cards inside sheets, nested shadows, and hover lift do not exist.

### Shadow Vocabulary
- **Sheet lift** (`box-shadow: 0 1px 1px rgba(20,20,20,0.06), 0 14px 32px -12px rgba(20,20,20,0.28)`): every sheet, the drop zone, app result panels. The legacy `--shadow-md` and `--shadow-lg` both resolve to it.
- **Hairline** (`box-shadow: 0 1px 2px rgba(20,20,20,0.06)`): the legacy `--shadow-sm` for small app controls.

### Named Rules
**The One Lift Rule.** A surface either lies on the desk with the sheet lift or is printed on a sheet with no shadow at all. No intermediate elevations.

**The Turned Sheet Rule.** Sheets on the desk are turned slightly: the hero sheet about -0.8deg, lower sheets between -0.3deg and +0.35deg. Rotation is removed below 1080px (hero below 860px) so mobile reads square.

## Shapes

Almost square. Paper sheets have sharp corners (0); buttons, the drop zone, and app controls use a barely softened 2px corner (3 to 4px at most). The one round form is the question chip, a full pill, because it reads as a hand-circled word. Borders are ink: 2px for buttons, chips, the drop zone (dashed at rest, solid on drag-over) and the rule under sheet heads; 1px for row rules. Ticks are drawn pencil strokes (an SVG mask in graphite), never a check glyph.

## Components

### Buttons
- **Shape:** near-square (2px).
- **Ink block (primary):** solid ink with white Archivo 700 text at 15 to 19px, 48px minimum height (42px in the header, 56px at the close). The one primary action per view.
- **Hover:** fill deepens to pure black and the label turns highlighter yellow.
- **Line (secondary):** transparent with a 2px ink border; hover fills highlighter yellow.
- **Focus (all interactive):** 2px ink outline at 3px offset plus a 6px yellow halo.

### Question Chips
- **Style:** pill, white paper, 2px ink border, Public Sans 600 15px, 36px minimum height.
- **State:** hover washes soft yellow; the pressed chip (`aria-pressed="true"`) fills question pink.

### Sheets
- **Corner Style:** square.
- **Background:** paper.
- **Shadow Strategy:** sheet lift (see Elevation).
- **Structure:** a head block above a 2px ink rule, then ruled rows; captions in 12px secondary print.
- **Internal Padding:** 44px 48px desktop, 18 to 28px mobile.

### Drop Zone
- **Style:** paper with a 2px dashed ink border, 2px corner, sheet lift; Archivo 800 22px title, 15px hint, full-width ink button, 14px limits line.
- **States:** hover and drag-over wash soft yellow; drag-over turns the border solid; busy shows a progress cursor. Errors print in error red on paper with a 1px error border.

### Navigation
- **Style:** sticky desk-grey bar, 68px tall, 2px ink rule beneath. Wordmark in Archivo 800 19px beside the logo mark; links Public Sans 600 15px in ink, underlined 2px on hover; ink-block CTA at the right.
- **Mobile (under 1000px):** an outlined "Menu" button with drawn bars opens a stacked panel of 18px links and a full-width CTA.

### The Highlighted Statement (signature)
A paper sheet holding a real statement: bank name and period, opening and closing balances, a ruled transaction table. Above it, the pencil prompt "Ask the statement for" and the question chips. Choosing a chip presses it pink, then re-runs a left-to-right yellow swipe (420ms, `cubic-bezier(0.22, 1, 0.36, 1)`, amount delayed 180ms) across the description and amount of each matching row, bolds the description, pencils a tick into the margin, and rewrites the pencil total in the top-right margin. Under reduced motion the marks appear without the swipe. In the app, the same swipe marks the results-table rows a chat answer refers to, with a pencil note and a line "Clear" button beside the table.

### Logo Mark
A white statement sheet outlined in ink with three print lines and one yellow highlighted row. Decorative; the Archivo wordmark carries the name.

## Do's and Don'ts

### Do:
- **Do** put content on paper sheets with the sheet lift over the grey desk, and turn desktop sheets by under one degree.
- **Do** reserve highlighter yellow for answers and the single emphasised phrase of a headline; pink for the question.
- **Do** set headings in Archivo at 112% width, weight 800, with tight negative tracking.
- **Do** keep figures tabular and right-aligned, rows equal-height and ruled.
- **Do** make the primary action a black ink block whose hover turns its label yellow.
- **Do** write numbers and nudges in graphite Kalam in the margin, turned a few degrees.
- **Do** keep the highlighter swipe the only motion, and static under `prefers-reduced-motion`.

### Don't:
- **Don't** use blue, purple, glow, or decorative gradient fills anywhere.
- **Don't** use yellow as a generic accent, badge, or tinted panel background; quiet panels use the neutral tint.
- **Don't** build grids of tinted feature cards or nest cards inside sheets; use ruled lists on paper.
- **Don't** set the pencil face on headings, buttons, or body copy.
- **Don't** put an uppercase eyebrow line above headings; uppercase labels belong to statement column heads and tier names only.
- **Don't** use check-mark or cross glyphs as icons; draw ticks as pencil strokes and icons as SVG. (The FAQ's printed plus and minus toggle signs are type, not icons.)
- **Don't** round sheets, or round controls beyond 4px; the pill is reserved for question chips.
