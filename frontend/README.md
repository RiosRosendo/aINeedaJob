# Handoff: aINeedJob — Agent Dashboard

## Overview
A dashboard for **aINeedJob**, an AI job-search agent that autonomously scans, applies to, and queues roles for a user's approval. The dashboard surface shows agent activity, key stats, and a queue of jobs awaiting the user's decision. The aesthetic is a clean, calm, Apple/Linear-inspired system with restrained color and professional micro-animations. Supports **dark (default)** and **light** themes.

## About the Design Files
The file in this bundle (`aINeedJob Dashboard.dc.html`) is a **design reference created in HTML** — a working prototype showing the intended look, motion, and behavior. It is **not production code to ship directly**. The task is to **recreate this design in the target codebase's existing environment** (React, Vue, SwiftUI, etc.) using its established component library, theming, and patterns. If no front-end environment exists yet, pick the most appropriate framework for the project and implement there.

> Note: the prototype is authored as a "Design Component" and references a runtime helper (`support.js`) that is part of the prototyping tool only. Ignore it — it is irrelevant to a real implementation. Read the HTML for structure/styling/copy.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, motion, and interactions are specified below. Recreate the UI pixel-accurately using the codebase's libraries, mapping the tokens below onto the existing theme system where one exists.

---

## Layout

Two-column app shell, full viewport height, no page scroll on the shell (the main column scrolls internally).

```
┌──────────┬───────────────────────────────────────────────┐
│ SIDEBAR  │ MAIN (scrolls)                                 │
│ 240px    │  max-width 1080px content, centered            │
│ fixed    │  padding: 42px 48px 64px                       │
│          │  ┌ Header (greeting + theme toggle + scan chip)│
│          │  ├ Stats strip (4 metrics)                     │
│          │  ├ Agent Activity (vertical timeline)          │
│          │  └ Jobs Queue (3 cards, grid)                  │
└──────────┴───────────────────────────────────────────────┘
```

- Shell: `display:flex; height:100vh; overflow:hidden`.
- Sidebar: `width:240px; flex:0 0 240px; border-right:1px solid var(--border-soft); display:flex; flex-direction:column`.
- Main: `flex:1; height:100%; overflow-y:auto`. Inner container `max-width:1080px; margin:0 auto; padding:42px 48px 64px`.

---

## Design Tokens

Implemented as CSS custom properties, swapped by theme class on the root. **Dark is default.**

### Dark theme
| Token | Value | Use |
|---|---|---|
| `--bg` | `#09090B` | App background |
| `--card` | `#141417` | Card / chip surfaces |
| `--card-shadow` | `0 1px 2px rgba(0,0,0,.5), 0 10px 30px -12px rgba(0,0,0,.7)` | Resting card elevation |
| `--card-shadow-hover` | `0 2px 8px rgba(0,0,0,.55), 0 22px 60px -18px rgba(0,0,0,.9)` | Hovered card elevation |
| `--sidebar-active` | `#1C1C20` | Active nav row / ghost-button hover |
| `--border` | `rgba(255,255,255,.09)` | Standard 1px borders |
| `--border-soft` | `rgba(255,255,255,.055)` | Dividers, timeline line |
| `--border-strong` | `rgba(255,255,255,.16)` | Emphasized borders, timeline nodes |
| `--text` | `#F5F5F7` | Primary text |
| `--muted` | `#9A9AA2` | Secondary text |
| `--faint` | `#6E6E78` | Tertiary text / labels / timestamps |
| `--accent` | `#0A84FF` | Links, active-nav underline accent, badge, status ring, "Needs Approval" dot |
| `--accent-bg` | `rgba(10,132,255,.14)` | Badge background, timeline latest-node ring |
| `--primary-bg` | `#F5F5F7` | Primary button fill (neutral, high-contrast) |
| `--primary-text` | `#0A0A0C` | Primary button text |
| `--primary-hover` | `#E3E3E7` | Primary button hover |
| `--track` | `rgba(255,255,255,.1)` | Fit-score ring track |
| `--ring` | `#E8E8EC` | Fit-score ring progress (monochrome) |
| `--green` | `#30D158` | (reserved; activity check marks) |
| `--skel` / `--skel2` | `#1E1E22` / `#161619` | Skeleton blocks |
| `--logo-border` | `#3A3A42` | Logo mark border |

### Light theme
| Token | Value |
|---|---|
| `--bg` | `#FAFAFA` |
| `--card` | `#FFFFFF` |
| `--card-shadow` | `0 1px 2px rgba(0,0,0,.04), 0 6px 20px -10px rgba(0,0,0,.12)` |
| `--card-shadow-hover` | `0 4px 12px rgba(0,0,0,.08), 0 24px 50px -18px rgba(0,0,0,.24)` |
| `--sidebar-active` | `#F0F0F2` |
| `--border` | `rgba(0,0,0,.09)` |
| `--border-soft` | `rgba(0,0,0,.05)` |
| `--border-strong` | `rgba(0,0,0,.18)` |
| `--text` | `#1D1D1F` |
| `--muted` | `#6E6E73` |
| `--faint` | `#86868B` |
| `--accent` | `#0071E3` |
| `--accent-bg` | `rgba(0,113,227,.1)` |
| `--primary-bg` | `#1D1D1F` |
| `--primary-text` | `#FFFFFF` |
| `--primary-hover` | `#000000` |
| `--track` | `rgba(0,0,0,.08)` |
| `--ring` | `#1D1D1F` |
| `--green` | `#34C759` |
| `--skel` / `--skel2` | `#ECECEE` / `#F3F3F5` |
| `--logo-border` | `#1D1D1F` |

### Typography
- Font stack: `-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', 'Inter', system-ui, sans-serif`. (Inter loaded as web-font fallback; native SF on Apple platforms.)
- Global: `-webkit-font-smoothing:antialiased; letter-spacing:-.005em`.
- Scale used:
  - Page title (greeting): 27px / 600 / `-.03em`
  - Section headers ("Agent Activity", "Jobs Queue"): 13px / 600 / `.05em` / UPPERCASE / `--muted`
  - Stat number: 30px / 600 / `-.03em`
  - Stat label: 11px / 600 / `.06em` / UPPERCASE / `--faint`
  - Card role title: 15px / 600 / `-.02em`
  - Card company: 12px / 500 / `--faint`
  - Body / activity text: 13.5px (emphasis spans 500, latest event 600)
  - Timestamps / meta: 11.5px / `--faint`
  - Buttons: 12.5px (ghost 500, primary 600)
  - Status chip: 12.5px / 550 title, 10.5px / 450 subtext

### Radius
- Stat strip: none (borderless). Cards: 14px. Chips/buttons/toggle: 9–10px. Badge: 6px. Pills (Remote/On-site): 999px. Timeline highlight node ring & dots: 50%.

### Spacing
- Section gaps: stats→activity 40px, activity→jobs 44px, header→stats 38px.
- Grid gaps: stats 16px, jobs 16px.
- Card padding: 22px. Stat item padding: `4px 0` (first) / `4px 0 4px 24px` (rest).

---

## Screens / Views

There is one screen: **Dashboard**. Components below.

### 1. Sidebar
- **Logo block** (top, 64px tall, `border-bottom:1px solid var(--border-soft)`): 22px rounded-square mark (`1.5px solid var(--logo-border)`, radius 7px) containing a 7px `var(--text)` square; wordmark "aINeedJob" 15px / 600 / `-.02em`.
- **Nav** (`padding:16px 0`): rows `Dashboard` (active), `Jobs`, `Approvals` (badge **5**), `Applications`, `Profile`.
  - Row: `padding:9px 22px; cursor:pointer`. Active row bg `var(--sidebar-active)`, label `var(--text)` / 600. Inactive label `var(--muted)` / 450.
  - **Hover underline**: a 1.5px `var(--text)` bar pinned at the row's bottom (`left:22px; bottom:5px`) that animates `width: 0 → calc(100% - 44px)` on hover (and is full-width while active). Transition `width .28s cubic-bezier(.2,.8,.2,1)`. Label color transitions `.18s`.
  - **Badge** (Approvals): `var(--accent)` text on `var(--accent-bg)`, 11px / 600, `padding:2px 7px`, radius 6px, pushed right (`margin-left:auto`).
- **Agent status chip** (bottom, above a `border-top:1px solid var(--border-soft)`, block padding `14px 16px`): a bordered chip (`1px solid var(--border)`, radius 11px, bg `var(--card)`, padding `9px 12px`) containing:
  - **Animated equalizer** (see Interactions): three 2.5px-wide bars, `height:14px`, radius 2px, `transform-origin:center bottom`, aligned to baseline (`display:flex; align-items:flex-end; gap:2.5px`).
  - Two-line label: title `var(--text)` 12.5px/550 = "Agent running"; subtext `var(--faint)` 10.5px = "Active · scanning roles". Paused state → "Agent paused" / "Paused · idle".

### 2. Header
- Left: greeting `Good morning, Rosendo` (27px/600); below it `Monday, June 23, 2026` (13.5px / `--muted`).
- Right (flex, gap 10px):
  - **Theme toggle button**: 34×34, `1px solid var(--border)`, radius 9px, bg `var(--card)`, icon `var(--muted)`. Shows a **sun** icon in dark mode, **moon** icon in light mode. Hover: bg `var(--sidebar-active)`, border `var(--border-strong)`.
  - **Scan chip** (read-only): `1px solid var(--border)`, radius 9px, bg `var(--card)`, height 34px, 12.5px `--muted`; a 13px refresh/rotate icon (`var(--faint)`) + text `Last scan: 2 minutes ago`.

### 3. Stats strip
Four metrics in a `grid-template-columns:repeat(4,1fr); gap:16px`. **No card backgrounds** — borderless. Items 2–4 carry a `1px solid var(--border-soft)` left divider + `padding-left:24px`.
- Each item: label (UPPERCASE 11px `--faint`) above number (30px/600 `--text`).
- **Needs Approval** label is preceded by a 6px `var(--accent)` dot.
- Values: **Jobs Found 847**, **Applied 23**, **Interviews 2**, **Needs Approval 5**.

### 4. Agent Activity — timeline
Section header `Agent Activity` with a right-aligned link `View all activity →` (12.5px / `var(--accent)` / 500).
- A single **continuous 1px vertical line** (`var(--border)`) at `left:11px`, `top:18px → bottom:18px`, runs behind all nodes.
- Rows (`position:relative; display:flex; padding:11px 0`), content offset `padding-left:40px`:
  1. **Latest** — node is a 13px **filled** dot `var(--text)` with a soft ring `box-shadow:0 0 0 4px var(--accent-bg)` (`left:5px; top:15px`). Text 13.5px/600 `var(--text)`: "Found 12 new roles matching your profile" · "2 minutes ago".
  2. Node = 11px **hollow** dot (`bg var(--bg)`, `1.5px solid var(--border-strong)`, `left:6px; top:16px`). "Submitted application — **Product Designer** at Notion" · "14 minutes ago".
  3. (hollow) "Tailored resume for **Vercel** — Frontend Engineer" · "38 minutes ago".
  4. (hollow) "Flagged **5 roles** for your approval" · "1 hour ago".
  5. (hollow) "Completed daily scan — **847 roles** reviewed" · "2 hours ago".
  - Body text `var(--muted)` with **bold** emphasis spans in `var(--text)` / 500. Hollow nodes are opaque (fill = page bg) so the line reads as passing behind them.

### 5. Jobs Queue
Section header `Jobs Queue` + right meta `3 awaiting review` (12.5px `--faint`). Three cards in `grid-template-columns:repeat(3,1fr); gap:16px`.
- **Card**: `1px solid var(--border)`, radius 14px, `padding:22px`, bg `var(--card)`, `box-shadow:var(--card-shadow)`.
- **Top row**: left = company (12px/500 `--faint`) + role title (15px/600 `-.02em` `--text`); right = **fit-score ring**.
  - Ring: 56×56 SVG, `viewBox 0 0 64 64`, rotated `-90deg`. Track circle `r=26 stroke var(--track) width 5`. Progress circle `r=26 stroke var(--ring) width 5 stroke-linecap:round`, `stroke-dasharray=163.36` (= 2πr). Offset = `163.36 × (1 − score/100)`. Score number centered, 13px/600 `--text`.
- **Tag row**: a fine pill (`1px solid var(--border)`, radius 999px, `padding:3px 10px`, 11px `--muted`) — **Remote** / **On-site** — plus faint label "Fit score".
- **Buttons** (flex, gap 8px, each `flex:1`, radius 10px, `padding:9px 0`, 12.5px):
  - **View Details** (ghost): `var(--muted)` text, bg `var(--card)`, `1px solid var(--border)`. Hover: bg `var(--sidebar-active)`, border `var(--border-strong)`.
  - **Approve** (primary): bg `var(--primary-bg)`, text `var(--primary-text)`, border same. Hover: `var(--primary-hover)`.
- **Card data**: Stripe / Senior Product Designer / **94** / Remote · Notion / Product Manager / **88** / On-site · Vercel / Frontend Engineer / **81** / Remote.

---

## Interactions & Behavior

### Load sequence (skeleton → content)
- On mount, `loading = true` for **850ms**, then flips to content. (If reduced motion, skips straight to final state.)
- During loading: skeleton placeholders animate `opacity 1↔.4` (`@keyframes`, 1.2s ease-in-out, looped), staggered via `animation-delay`. Skeletons exist for stat numbers, three timeline rows, and three job cards.

### Stat counters
- On reveal, each number eases **0 → target** over **1300ms** using easeOutCubic (`1 − (1−t)³`), driven by `requestAnimationFrame`. Targets: 847 / 23 / 2 / 5.

### Timeline entrance
- Each row animates `ain-slideLeft` — `opacity 0→1` + `translateX(-14px)→0`, `.5s cubic-bezier(.2,.8,.2,1)`, `fill-mode: backwards`, staggered delays `.04 / .12 / .2 / .28 / .36s`.

### Job cards entrance + hover
- Entrance: `ain-fadeUp` — `opacity 0→1` + `translateY(12px)→0`, `.55s cubic-bezier(.2,.8,.2,1)`, `fill-mode: backwards`, delays `.06 / .16 / .26s`.
- **Hover lift**: hovered card `transform:translateY(-6px) scale(1.012)`, `box-shadow:var(--card-shadow-hover)`, `border-color:var(--border-strong)`. Transition `transform .24s cubic-bezier(.2,.8,.2,1), box-shadow .24s, border-color .24s`. Non-hovered cards stay put — only the focused one "pops."

### Fit-score rings
- Each ring's progress stroke fills from empty to its target offset via a per-score `@keyframes` (offset 163.36 → 9.8 / 19.6 / 31.04), `1.1s cubic-bezier(.2,.8,.2,1)`, `fill-mode: backwards`, delays `.3 / .4 / .5s`.

### Agent equalizer (status)
- Three bars each run a distinct keyframe scaling `scaleY` between ~0.28 and 1.0, looped, with different durations (1.05s / 1.35s / 0.92s) for an organic, non-synced motion. Bars fill `var(--text)`.
- **Paused** (agent off) or reduced motion: animation removed, bars set to static low `scaleY` (`.3 / .6 / .42`), color `var(--faint)`.

### Sidebar nav hover
- Underline bar grows from width 0 to full on hover (`.28s` ease), label color → `var(--text)`. Active row keeps the underline full.

### Theme toggle
- Clicking the header sun/moon button flips `theme` between `dark` and `light`, swapping the root class and therefore all tokens. Icon swaps accordingly. All surfaces, borders, shadows, rings, and skeletons retheme via tokens — no per-element overrides.

---

## State Management
- `theme`: `'dark' | 'light'` (default `'dark'`). Toggled by header button. In a real app, persist to localStorage / system preference (`prefers-color-scheme`).
- `loading`: boolean; true → false after 850ms; gates skeleton vs. content.
- Animated stat values: `jobs / applied / interviews / approval` (number), tweened on reveal. In production these come from the agent's data source.
- `hoverNav`: index of hovered nav item (drives the underline). Pure UI; CSS `:hover` is sufficient in a real implementation.
- Reduced-motion flag: respect `prefers-reduced-motion` to disable entrance/loop animations and render final states immediately.
- Data to fetch in production: stat totals, activity event feed (timestamp + type + text), job queue items (company, role, fit score, location type, status). "Approve" / "View Details" / "View all activity" / nav items are navigation/action handlers to wire up.

## Assets
- **No raster assets / no logos.** The aINeedJob mark is pure CSS (bordered rounded square + inner square). All icons are inline SVGs drawn from simple primitives (refresh, sun, moon). Recreate icons with the codebase's existing icon set (e.g. Lucide/SF Symbols) — refresh, sun, moon. The fit-score rings and equalizer are CSS/SVG, not images.
- Inter is the only web font (Google Fonts) and is a fallback behind the native system font; use the app's existing font if it has one.

## Files
- `aINeedJob Dashboard.dc.html` — the full hifi prototype (markup, inline styles, theme tokens, keyframes, and the animation logic in a `<script>`-equivalent class). Read it directly for exact structure and values; ignore the `support.js` runtime reference (prototyping tool only).
