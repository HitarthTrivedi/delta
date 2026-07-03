---
name: Delta
description: The AI career operating system — a warm, editorial workspace for a weekly career loop.
colors:
  bone: "#f7f5f0"
  paper: "#ffffff"
  ink: "#1a1918"
  ink-soft: "#66645e"
  oxblood: "#7d252b"
  rule: "#e6e4df"
  accent-surface: "#f0ede5"
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "clamp(2rem, 5vw, 3.4rem)"
    fontWeight: 500
    lineHeight: 1.1
    letterSpacing: "0"
  body:
    fontFamily: "Manrope, system-ui, -apple-system, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.65
  label:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "0.6875rem"
    fontWeight: 500
    lineHeight: 1.4
    letterSpacing: "0.18em"
rounded:
  none: "0px"
  sm: "6px"
  full: "9999px"
spacing:
  xs: "8px"
  sm: "12px"
  md: "20px"
  lg: "32px"
components:
  button-primary:
    backgroundColor: "{colors.oxblood}"
    textColor: "{colors.bone}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "12px 28px"
  button-primary-hover:
    backgroundColor: "{colors.ink}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "12px 28px"
  button-secondary-hover:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.bone}"
  card-paper:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.none}"
    padding: "{spacing.lg}"
  input-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.none}"
    padding: "12px 14px"
---

# Design System: Delta

## 1. Overview

**Creative North Star: "The Weekly Memorandum"**

Delta reads like a well-kept paper file, not a SaaS dashboard: warm bone/paper surfaces, a single serif display face for anything that deserves weight, a plain sans for reading, and a small mono label style reserved for state and metadata (week numbers, kickers, button labels). The one saturated color, oxblood, is spent deliberately — primary actions, active states, and the handful of headings that should carry authority — never as generic decoration.

The system explicitly rejects the earlier cyberpunk-dark, neon-accent dashboard aesthetic this product used before: no glassmorphic panels, no glowing borders, no gradient-filled stat tiles. Warmth here comes from tone of voice and generous whitespace, not from color noise or motion flourish.

**Key Characteristics:**
- Square corners everywhere (0px radius) — the one deliberate geometric rule of the system.
- Serif display type for anything that should read as a heading; sans for body; mono-uppercase for labels and buttons only.
- Oxblood is spent on interaction and hierarchy signals (buttons, active nav, key numerals), not on backgrounds or large fills.
- Hairline rule borders (`--rule`) do the separating work that shadows or heavy borders would otherwise do.

## 2. Colors

A warm paper palette with one saturated accent; a parallel dark "ink" variant exists (charcoal paper, bone text, muted rose accent) toggled via the `.dark` class.

### Primary
- **Oxblood** (`#7d252b`): primary buttons, active nav/tab states, links, key numerals and stats, focus rings. Used sparingly — most surfaces carry none of it at rest.

### Neutral
- **Bone** (`#f7f5f0`): page background.
- **Paper** (`#ffffff`): card and panel surfaces, raised just barely above bone.
- **Ink** (`#1a1918`): primary text, headings, filled button backgrounds.
- **Ink Soft** (`#66645e`): secondary text, captions, placeholders, disabled states.
- **Rule** (`#e6e4df`): all hairline borders and dividers.
- **Accent Surface** (`#f0ede5`): subtle fills for filled chips/badges and hover backgrounds — one step warmer than bone, one step quieter than paper.

### Named Rules
**The One Accent Rule.** Oxblood is the only saturated color in the system. If a screen needs a second meaning-bearing color (success/warning), desaturate it toward the neutral ramp rather than introducing a new hue family.

## 3. Typography

**Display Font:** Cormorant Garamond (with Georgia, serif fallback)
**Body Font:** Manrope (with system-ui, -apple-system, sans-serif fallback)
**Label/Mono Font:** IBM Plex Mono (with ui-monospace fallback)

**Character:** A classic serif for weight and warmth, paired with a plain geometric-humanist sans for legibility, with monospace reserved entirely for small structural labels — the pairing reads as "memorandum," not "marketing site."

### Hierarchy
- **Display** (500 weight, `clamp(2rem, 5vw, 3.4rem)`, 1.1 line-height): Page titles and hero headlines — Cormorant Garamond only, never for body copy.
- **Headline** (600 weight, 1.25–1.5rem): Section and card titles, still serif.
- **Body** (400 weight, 0.9375rem, 1.65 line-height): All reading copy; cap measure around 65–75ch.
- **Label** (500 weight, 0.6875rem, uppercase, 0.18em tracking, IBM Plex Mono): Buttons, kickers, nav items, status badges. Never used for more than a few words.

### Named Rules
**The Serif-Only-For-Weight Rule.** Cormorant Garamond appears only on headings and the occasional italic emphasis line — never on body paragraphs, buttons, or labels.

## 4. Elevation

Flat by default. Depth is conveyed by paper-on-bone contrast and hairline `--rule` borders, not shadows — there is no shadow vocabulary in the system. Hover/active states shift border or fill color rather than lifting with a shadow.

### Named Rules
**The No-Shadow Rule.** Structure comes from a 1px `--rule` border and a background-color step (bone → paper → accent-surface), never from `box-shadow`.

## 5. Components

### Buttons
- **Shape:** Square corners (0px radius) always.
- **Primary:** Oxblood fill, bone text, oxblood border; hover shifts fill+border to ink. Mono label typography, uppercase, 0.14–0.18em tracking.
- **Secondary / Ghost:** Transparent fill, ink border and text; hover fills to ink with bone text.
- **Nav link (active):** No fill; ink or oxblood text with a 2px bottom border in the same color.

### Cards / Containers
- **Corner Style:** 0px radius, always square.
- **Background:** Paper on a bone page, or accent-surface for a quieter/filled variant (e.g. selected chips, filled badges).
- **Shadow Strategy:** None — see Elevation.
- **Border:** 1px solid rule.
- **Internal Padding:** 24–32px generous padding; density comes from typography scale, not tight padding.

### Inputs / Fields
- **Style:** Paper background, 1px rule border, square corners, ink text, ink-soft placeholder.
- **Focus:** Border color shifts to oxblood; no glow/shadow.

### Navigation
- Serif "Delta" wordmark + mono "by Alpha.Kore" subhead on marketing pages; mono uppercase links throughout (10–11px, 0.18–0.22em tracking). Active state is a colored underline/border, not a filled pill.

### Chat bubbles & markdown (signature component)
Agent 2's chat renders markdown through a components map (not raw HTML): paragraphs, lists, and inline code use body/mono type at reduced size; tables get a rule-bordered, horizontally-scrollable wrapper with an accent-surface header row instead of unstyled browser-default tables; math renders through KaTeX rather than as literal `$...$` text.

## 6. Do's and Don'ts

### Do:
- **Do** keep corners square (0px) everywhere — buttons, cards, inputs, chips.
- **Do** spend oxblood only on the interactive/hierarchy-bearing element (primary button, active tab, a key stat) — most of a screen should have none of it.
- **Do** use Cormorant Garamond exclusively for headings; Manrope for everything read at length; IBM Plex Mono only for short uppercase labels.
- **Do** separate content with a 1px `--rule` border rather than a shadow or heavy divider.
- **Do** keep read-only views (loading a dashboard, opening a progress page) free of side effects on the user's underlying data.

### Don't:
- **Don't** reintroduce the earlier dark cyberpunk/neon dashboard look (glassmorphic panels, glowing borders, gradient stat tiles) as a default for new screens.
- **Don't** use gradient text or `background-clip: text` for emphasis — use weight or the oxblood accent instead.
- **Don't** use `border-left`/`border-right` as a colored accent stripe on cards or list rows.
- **Don't** add drop shadows for elevation — this system is flat by design.
- **Don't** round any corner — a single rounded button or card breaks the square-corner rule immediately.
