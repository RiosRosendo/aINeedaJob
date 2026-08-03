# Handoff: Applications screen (Scout / aiNeedJob)

## Overview
Third screen in the warm/organic redesign (Dashboard, Profile done). Same "Design Inside" pressed-in visual language and shared Scout sidebar — this doc only covers what's new/specific to Applications. Recreate inside the real frontend (`frontend/` in `aINeedaJob`) wired to the real `Application` data and existing actions in `frontend/app/applications/page.tsx` — this is a UI-only reskin, every button must keep doing exactly what it already does.

## Fidelity
High-fidelity for colors, type, spacing, radii, shadows, and the pressed-in component style. Sample copy/companies/dates are illustrative only — real data and real status values drive this screen.

## Shared chrome
Reuse the Sidebar component and design tokens from the Dashboard/Profile handoffs unchanged. Active nav row here is "Applications".

## Layout
Single column, `main` max-width 980px, centered, `padding: 44px 50px 70px`.

## Sections (top to bottom)

### 1. Header
"Where things stand" (Caprasimo 34px) title. Below it, a row: left side shows "`{visible}` of `{total}` applications" (14px muted) +, if present, "Last email check: `{time}`" (12px, fainter); right side is the **Check emails** button — inset pill, accent-700 text, darkens on hover. This maps to the existing "check emails for replies" action in the repo — while in flight it should read "Checking…" and be disabled/non-interactive (same style, muted text, no pointer cursor), then update the last-checked timestamp on completion. Surface the existing error state (if the check fails) as an inset rounded banner in accent-700 text just below the header.

### 2. Filter row
"FILTER BY STATUS" eyebrow label (11px uppercase, tracked, muted) on the left; on the right, only when there are any ignored applications, a toggle pill "Show ignored (`n`)" / "Hide ignored (`n`)" — wires to the existing show/hide-ignored toggle.

### 3. Status tabs
A wrapped row of pill tabs — reproduce every status filter the real page supports (not just a fixed set): All, Pending review, Pending apply, Applied, Interview, Offer, Rejected, etc., each labeled "`{Status}` · `{count}`" where the count reflects the currently visible set (respecting the ignored toggle). Active tab: bold text, accent-700 color, deeper inset shadow (`inset 0 2px 5px rgba(32,30,29,.2)`). Inactive tabs: normal weight, muted color, lighter inset shadow (`inset 0 1px 3px rgba(32,30,29,.15)`). Clicking a tab sets the active filter — same filtering logic as today, just restyled.

### 4. Empty state
When the current filter/search yields zero rows: a centered inset panel, "No applications found" (16px) + "Try adjusting your filters" (13px muted).

### 5. Application rows
List of inset rounded cards (`border-radius: 20px`), one per application, staggered fade-up entrance on load (`ainFadeUp`, ~0.04s stagger, capped at 0.4s).

Each row:
- **Left (flexible):** role title (Caprasimo 16px) · company + location (12px muted) · "Found `{date}`" (11px, fainter) if a discovery date exists.
- **Right (fixed 110px column, so every ring lines up regardless of status-label text length):** a 44px circular fit-score progress ring (same SVG-stroke ring used on Dashboard/Jobs — track color `--dtrack`, progress stroke colored per status, score number centered) with the status label as a small pill directly underneath it (not beside it — this was explicitly requested: no "92% — Interview" side-by-side, the ring visually IS the score and the status name reads as its caption).
- **Status → color mapping** (reuse across ring stroke + label text + label's inset shadow tint): pending/awaiting-action states in accent-700 (terracotta), positive-progress states (applied, interview, offer) in accent-2-800 (sage), rejected/ignored/dead states in faint muted gray. Map this to whatever the real status enum in `types.ts`/the API actually uses — the point is 3 semantic buckets (needs action / progressing / closed-out), not literal string matching against this prototype's sample statuses.
- **Action row below (only the buttons relevant to that row's real status — do not show actions that don't apply):**
  - Pending-apply-type statuses (the applicant needs to apply manually): **"Apply now"** (accent-700, inset, opens the job's URL — same behavior as today) + **"Mark applied"** (muted, inset, flips status to Applied — same handler as today).
  - Pending-approval-type statuses: **"Approve"** (sage/accent-2-800, inset) + **"Dismiss"** (muted, inset) — same approve/dismiss handlers already wired on this screen today.
  - All other statuses (applied, interview, offer, rejected, ignored, etc.): no action row — the card is just informational.
- Rows with a closed-out/negative status (rejected, ignored) render at slightly reduced opacity (~0.65) to visually recede.

## Interaction & behavior notes — reuse, don't reinvent
This is explicitly a **restyle, not a rebuild of logic**. Every control here (Check emails, show/hide ignored, status tabs, Apply now, Mark applied, Approve, Dismiss) must call the exact same handlers/API endpoints the current `applications/page.tsx` already uses — only the visual treatment (inset/pressed shadows, pill shapes, ring instead of raw percentage text, colors/type from the tokens below) is new.

## Design tokens
Same as Dashboard/Profile handoffs — full light/dark tables, type scale, radius/shadow scale live there. Reused here:
- Inset panel/card shadow: `inset 0 3px 10px rgba(32,30,29,.16), inset 0 -1px 0 rgba(255,255,255,.4)`.
- Inset chip/button shadow: `inset 0 1-2px 3-5px rgba(32,30,29,.15-.18)`; deeper `inset 0 2px 5px rgba(32,30,29,.2)` for the emphasized/active state (active tab, Apply now, Approve, Check emails).
- Progress ring: same SVG recipe as Dashboard job cards — `viewBox 0 0 64 64`, `r=26`, `stroke-width=6`, rotated -90deg, `stroke-dasharray: 163.36`, `stroke-dashoffset = 163.36 * (1 - score/100)`.

## Files
- `applications.design.html` — prototype source (view source for exact markup/inline styles). Exported from a design tool; references a `support.js` runtime not included, so treat as a markup/CSS reference, not a page to run standalone.
- `organic-styles.css` — the Organic design-system token sheet.
- See the Dashboard handoff for the Sidebar/Scout mascot spec and full shared tokens.
