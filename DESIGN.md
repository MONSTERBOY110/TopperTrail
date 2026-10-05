---
name: TopperTrail
description: One rank. Many claims. Follow the trail. A counting-day results board for coaching institutes' topper claims.
colors:
  navy-shell: "#13213c"
  navy-shell-2: "#1d2f52"
  shell-text: "#c9d3e6"
  ground: "#f3f5f8"
  surface: "#ffffff"
  ink: "#13213c"
  ink-2: "#3d4963"
  muted: "#5b667d"
  rule: "#d9dee7"
  rule-strong: "#b9c1cf"
  row-hover: "#e9eef6"
  alert-magenta: "#c2185b"
  mark-yellow: "#fde7a8"
  series-1-blue: "#2a78d6"
  series-2-orange: "#eb6834"
  series-3-green: "#1baf7a"
  series-4-amber: "#eda100"
  series-5-field-green: "#008300"
  series-6-violet: "#4a3aa7"
  series-other-slate: "#8a94a6"
typography:
  rank-display:
    fontFamily: "Martel, Noto Serif Devanagari, Georgia, serif"
    fontSize: "clamp(3.5rem, 2rem + 6vw, 5.75rem)"
    fontWeight: 800
    lineHeight: 0.9
    letterSpacing: "-0.04em"
  finding:
    fontFamily: "Mukta, Noto Sans Devanagari, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(1.4rem, 1rem + 1.6vw, 2.1rem)"
    fontWeight: 500
    lineHeight: 1.3
  headline:
    fontFamily: "Martel, Noto Serif Devanagari, Georgia, serif"
    fontSize: "clamp(1.6rem, 1.2rem + 1.6vw, 2.4rem)"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Martel, Noto Serif Devanagari, Georgia, serif"
    fontSize: "1.25rem"
    fontWeight: 700
    lineHeight: 1.2
  rank-figure:
    fontFamily: "Martel, Noto Serif Devanagari, Georgia, serif"
    fontSize: "2.1rem"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.03em"
  tally-figure:
    fontFamily: "Martel, Noto Serif Devanagari, Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: 800
    lineHeight: 1
  body:
    fontFamily: "Mukta, Noto Sans Devanagari, Segoe UI, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.55
    fontFeature: "tnum"
  chip-label:
    fontFamily: "Mukta, Noto Sans Devanagari, Segoe UI, system-ui, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 500
    lineHeight: 1.2
  column-label:
    fontFamily: "Mukta, Noto Sans Devanagari, Segoe UI, system-ui, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 700
    lineHeight: 1.2
rounded:
  hairline: "2px"
  swatch: "3px"
  r: "4px"
spacing:
  cell: "8px"
  cell-2: "16px"
  cell-3: "24px"
  cell-4: "32px"
  cell-6: "48px"
  cell-8: "64px"
components:
  shell:
    backgroundColor: "{colors.navy-shell}"
    textColor: "{colors.shell-text}"
    height: "56px"
  claimant-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.chip-label}"
    rounded: "{rounded.r}"
    height: "32px"
    padding: "0 10px 0 0"
  claimant-chip-hover:
    backgroundColor: "{colors.row-hover}"
  rank-row:
    backgroundColor: "{colors.surface}"
    padding: "12px 16px"
    height: "64px"
  rank-row-hover:
    backgroundColor: "{colors.row-hover}"
  claim-group:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.r}"
    padding: "16px 20px"
  gap-tag:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.ink-2}"
    rounded: "{rounded.r}"
    padding: "3px 8px"
  course-mark:
    backgroundColor: "{colors.mark-yellow}"
    textColor: "{colors.ink}"
    rounded: "{rounded.hairline}"
    padding: "0 2px"
---

# Design System: TopperTrail

## Overview

**Creative North Star: "The Counting-Day Board"**

TopperTrail reads like an election counting-day results page: a navy bar across the top, a cool daylight ground, and one row per seat. Every official rank is a seat; every institute that claims that topper sits on the row as a coloured claimant chip. Hue says which institute, fill says what it disclosed, and a single magenta says there is something to check. The finding is read out as one sentence before any chart, and every number on the page leads down to a claim and its source.

Density is a working results board, not a marketing page: rows of figures and chips on a strict 8px cell, rules instead of cards where a list will do, and surfaces that are flat white panels on the cool ground. Martel carries the figures that a reader scans (rank numbers, claimant counts, tallies), Mukta carries everything read as language, and both render Devanagari. The world is light only, because it is read in daylight offices and newsrooms, and it rejects the category default of metric tiles over a neutral table.

**Key Characteristics:**
- Navy counting-day shell over a cool ground; white flat panels; no shadows.
- Hue is the institute (six fixed series slots plus slate), fill is the disclosure (solid, 135 degree hatch, hollow).
- One alert magenta, reserved for rank or own-words checks.
- Martel figures, Mukta text, tabular numerals everywhere.
- Strict 8px cell module; 32px chips with a full-height 16px colour cell.
- Links are ink with an underline; colour never marks an action on its own.

## Colors

A restrained navy and cool-grey board where colour is data: institute hues and disclosure fills carry meaning, and nothing else is coloured.

### Primary
- **Counting-Day Navy** (navy-shell): the sticky top bar behind the brand and exam tabs, the focus ring, the text selection background, and the underline colour of the topper's name in claim text. The same value doubles as ink.
- **Navy Shell Deep** (navy-shell-2): reserved second navy step for the shell family.
- **Shell Text** (shell-text): resting tab and Methodology link text on navy; active and hovered shell links go white with a 3px white underline bar.

### Secondary: the institute series
Six validated counting-day hues, assigned per ledger, plus slate for the rest.
- **Slot 1 Results Blue** (series-1-blue), **Slot 2 Saffron Orange** (series-2-orange), **Slot 3 Jade** (series-3-green), **Slot 4 Turmeric Amber** (series-4-amber), **Slot 5 Field Green** (series-5-field-green), **Slot 6 Ink Violet** (series-6-violet): one hue per top-six institute, used in chips, the tally strip, legend keys, table keys and claim-group headings.
- **Other Slate** (series-other-slate): every institute outside the top six.

### Tertiary: signals
- **Check Magenta** (alert-magenta): only for a rank check or a denied own-words check. Appears as an 8px dot and a magenta border on the chip, the bold label of an alert flag, and alert text. Never decoration, never a link.
- **Course Highlighter** (mark-yellow): the background of course words marked inside claim text.

### Neutral
- **Daylight Ground** (ground): page background, sticky board head, gap tag fill.
- **Surface White** (surface): board, tables, claim groups, quotes, source panels; also the blank in hatches and the inside of hollow swatches.
- **Ink** (ink): headings, body, links, rank figures, the 2px rule under column heads.
- **Ink 2** (ink-2): secondary text, guide words, flag details, and the 1px ring on every swatch.
- **Muted** (muted): meta, column labels, empty rows, sources line.
- **Rule** (rule): 1px row and panel borders. **Rule Strong** (rule-strong): footer rule, dashed preview borders, scrollbar thumb.
- **Row Hover** (row-hover): hovered or focused rank row and hovered chip.

### Named Rules
**The Hue Is the Institute Rule.** Series hues identify institutes and nothing else. Slots go to the top six institutes by claim count within one ledger (ties broken by institute id), fixed across every page of that exam; everyone else is slate. Never assign a series hue to a UI state.

**The Fill Is the Disclosure Rule.** Solid cell = a course is named next to the claim; 135 degree hatch = only an interview programme is named; hollow ring = no course named. The same three fills appear in the strip, chips and legend, and every swatch carries a 1px ink-2 ring so the low-contrast hues stay distinct (WCAG 1.4.11).

**The One Magenta Rule.** Check Magenta marks checks only. If it is not a rank or own-words check, it is not magenta.

**The Ink Link Rule.** Links are ink with a 1px underline (2px on hover, offset 3px). Blue is institute slot 1, so colour never marks an action on its own.

## Typography

**Display Font:** Martel (with Noto Serif Devanagari, Georgia, serif), self-hosted at 400, 700, 800 incl. Devanagari
**Body Font:** Mukta (with Noto Sans Devanagari, Segoe UI, system-ui, sans-serif), self-hosted at 400, 500, 700 incl. Devanagari
**Label/Mono Font:** system monospace (ui-monospace, Cascadia Mono, Consolas) for hashes and JSON only

**Character:** a sturdy Indian-press serif for the figures a reader scans down the board, against a plain humanist sans for the words they read; both speak Hindi as well as English.

### Hierarchy
- **Rank Display** (Martel 800, clamp 3.5 to 5.75rem, 0.9, -0.04em): the AIR figure at the head of a topper ledger, with a small Mukta 700 rank label set top-aligned beside it.
- **Finding** (Mukta 500, clamp 1.4 to 2.1rem, 1.3, max 34ch, balanced): the headline result read as one sentence; its figures switch to Martel 800 at 1.25em. A small variant (clamp 1.15 to 1.5rem, 44ch) serves secondary pages.
- **Headline** (Martel 800, clamp 1.6 to 2.4rem, -0.02em): topper and institute names; the index intro steps up to clamp 1.8 to 3rem, reading pages to clamp 1.7 to 2.5rem.
- **Title** (Martel 700, 1.25rem): section heads; h3 at 1.05rem.
- **Rank Figure / Tally Figure** (Martel 800, 2.1rem and 1.5rem): rank numbers and claimant counts on the board; 1.5rem and 1.1rem below 720px.
- **Body** (Mukta 400, 17px, 1.55; 16px below 720px): all reading text; claim text and AI text cap at 75ch, lede at 64ch.
- **Chip Label** (Mukta 500, 0.85rem): chip names. **Column Label** (Mukta 700, 0.8rem, muted, sentence case): board and table column heads. **Meta** (0.875rem, muted).

### Named Rules
**The Figures in Martel Rule.** Any number a reader compares (rank, claimant count, tally, finding figure, timestamp stamp) is Martel; prose is Mukta.

**The Tabular Rule.** Tabular figures are on for the whole body so columns of counts align.

## Layout

The page is a single centred column, min(1180px, 100% minus 32px), under a sticky 56px navy shell. Every spacing value is a multiple of the 8px cell (half steps of 12px and 20px appear inside panels); sections sit 48px apart (24px below 720px), main has 32px above and 64px below.

The ranks board is a four-column grid: 64px rank figure, name column minmax(170px, 1.1fr), 88px claimant count, and a 3fr chip field, with 16px gutters and rows at least 64px tall. The board head (title and guide words naming the span in view) is sticky under the shell on the ground colour. Column labels sit above a 2px ink rule. The whole row is the link to the topper's ledger; chips stay separately clickable above it.

The tally strip is a full-width 36px flex bar (28px below 720px), one segment per institute sized by claims with 2px gaps, each split into stated, interview and none parts. Inline legends follow: institute keys with counts, then the fill legend.

At 720px and below the board folds each rank into two lines (figure, name, count on the first; chips spanning the second), column labels hide, legends become a two-column grid, the topper head stacks, and data tables scroll sideways with a sticky first column and a visible scroll cue.

## Elevation & Depth

Flat. There are no drop shadows anywhere; depth comes from white surfaces on the cool ground, 1px rules, and the 2px ink rule under column heads. The only box-shadows are inset rings that draw swatch fills and hollow strip parts, which are encoding, not elevation. Stacking is limited to the sticky shell and sticky board head.

### Named Rules
**The Flat Board Rule.** Surfaces never lift. State is shown by row-hover tint, border colour, underline weight or the focus ring, never by a shadow.

## Shapes

Gently squared corners: 4px on chips, panels, tables and tags; 3px on swatches; 2px on strip segments, legend keys and marks. Circles appear only as the 8px magenta check dot. Borders are 1px rule by default, dashed rule-strong for preview and provisional notes. The recurring silhouette is the chip: a rectangle whose left edge is a full-height colour cell.

## Components

### Claimant Chip (signature)
A results-board token for one institute claiming one rank.
- **Anatomy:** 32px tall, white, 1px rule border, 4px radius, overflow hidden; a full-height 16px swatch cell on the left edge (left corners 3px), 8px gap, Mukta 500 0.85rem name, 10px right padding.
- **Fill:** the swatch takes the institute hue and the disclosure fill, ringed 1px ink-2. A screen-reader suffix names the fill and any check.
- **Hover:** border to ink-2, background to row hover.
- **Check:** border turns magenta and an 8px magenta dot trails the name.
- **Order:** slot order, then name.

### Rank Row
- One seat per official rank on the board: Martel rank figure, bold Mukta official name (underline on hover), Martel claimant count, chip field. Empty ranks mute figure and count and read "No claims in the collected sources".
- **Hover / focus-within:** row-hover tint; keyboard focus adds a 3px navy outline inset by 3px.

### Tally Strip and Legends
- Segments of institute hue split by disclosure fill; hatch here is 3px on 6px (2px on 4px in swatches). Segment hover draws a 2px ink outline. The strip is aria-hidden; the institutes table carries the same numbers.
- Legend keys are 12px squares (18px in headings), 2px radius.

### Claim Group and Claim
- A white panel (1px rule, 4px radius, 16px by 20px padding) per institute on a topper ledger, headed by a key, the institute name and a muted count. Claims inside are divided by 1px rules.
- **Claim text:** pre-line, max 75ch. Course words are marked with the yellow highlighter; the topper's name is the **who** style, bold with a 2px navy underline offset 3px.
- **Source line:** 0.85rem muted with the source type bold in ink-2.

### Gap Tags and Flags
- **Gap tags:** small ground-filled tags (0.78rem, 500, ink-2, 1px rule border, 4px radius, 3px by 8px) for disclosure gaps.
- **Flags:** a list of rule results, bold label in ink then detail in ink-2; an alert flag turns only its label magenta.

### Navigation
- Navy shell: Martel 800 brand in white, exam tabs and Methodology in shell text, Mukta 500. Hover goes white; the current page is white with a 3px white bottom bar. Tabs scroll horizontally without a scrollbar. Focus rings inside the shell are white.

### Tables
- White wrap with 1px rule border and 4px radius; 10px by 12px cells, 1px rule rows, column heads in column-label style over a 2px ink rule; numbers right aligned.

### Notices
- The fixed CCPA notice sits in the footer of every page in Mukta 500 ink, max 80ch, above a muted sources line. A preview note (dashed rule-strong border, white, ink-2) labels synthetic data whenever it is shown.

### Focus and Selection
- Focus: 3px solid navy outline, 2px offset, 2px radius (white inside the shell). Selection: navy background, white text.

## Do's and Don'ts

### Do:
- **Do** assign series slots to the top six institutes by claims within each ledger and keep them fixed across that exam's pages; everyone else is slate.
- **Do** show disclosure with fill only: solid for course named, 135 degree hatch for interview programme only, hollow ring for none, with a 1px ink-2 ring on every swatch.
- **Do** keep chips at 32px with a full-height 16px colour cell.
- **Do** set every compared figure in Martel 800 and keep tabular figures on.
- **Do** build spacing from the 8px cell.
- **Do** keep links ink with an underline, and show focus with the 3px navy ring.
- **Do** keep wording neutral ("not stated", "differs", "not mentioned") and carry the fixed CCPA notice on every page.
- **Do** keep the world light only; it is read in daylight offices.

### Don't:
- **Don't** use Check Magenta for anything but rank or own-words checks.
- **Don't** use a series hue, blue included, to mark a link, button or state.
- **Don't** add drop shadows or lifted cards; the board is flat.
- **Don't** replace the board with metric tiles over a neutral table.
- **Don't** use em dashes or en dashes in UI copy, or words like "false", "fake" or "misleading" about a claim.
- **Don't** add a dark theme.
