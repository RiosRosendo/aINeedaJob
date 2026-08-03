# Handoff: Jobs screen (Scout / aiNeedJob)

## Overview
Warm/organic restyle of the Jobs list screen. Same "Design Inside" pressed-in visual language and shared Scout sidebar as Dashboard/Profile/Applications. This is a **UI-only reskin** — every control (search, Decision filter, Modality filter, show-ignored toggle, View Details) must call the exact same logic/handlers as `frontend/app/jobs/page.tsx` today.

## Shared chrome
Reuse the Sidebar component and design tokens from the Dashboard handoff unchanged. Active nav row here is "Jobs".

## Layout
Single column, `main` max-width 980px, centered, `padding: 44px 50px 70px`.

## Sections

### Header
"All the roles Scout has found" (Caprasimo 34px) + "`{shown}` of `{scored}` scored jobs · `{scored}` of `{total}` total discovered" (14px muted) — same counts as today's `sortedJobs.length / jobs.length / totalJobs`. Error state (if job loading fails) renders as an inset rounded banner in accent-700 text.

### Search bar
Full-width inset pill (`border-radius: 999px`, `box-shadow: inset 0 2px 5px rgba(32,30,29,.16)`), search icon + a plain text input with placeholder "Search by title or company…" — wires to the same `searchQuery` state/filter as today (matches title OR company, case-insensitive).

### Filters row
Three groups side by side, each with an 11px uppercase muted eyebrow label above a row of pill tabs:
- **Decision**: All / Apply / Review / Ignore — mirrors the existing `getDecision()` bucketing (fit_score ≥85 → Apply, ≥60 → Review, else → Ignore). Each pill shows a live count for the current data+other filters, e.g. "Apply · 3".
- **Modality**: All / Remote / Hybrid / On-site — same modality filter as today.
- **Show ignored**: a single toggle pill with a ○/✓ mark, same behavior as today's "Show ignored" checkbox-button (when off, jobs with no/zero fit_score are hidden by default).

**Pill states (important, explicitly requested):** inactive pills are transparent background, muted text, light inset shadow. The **active/selected** pill in each group has a **persistent white background** (`background: #fff`), bold accent-700 text, and a deeper inset shadow — not just a hover/press flash, it stays white for as long as it's selected. Any pill also gets a brief white background flash on `:active` (press) for tactile feedback, but the selected state is the persistent one.

### Job rows
List of inset rounded cards, one per job, staggered fade-up entrance. Each row: title (Caprasimo 16px) + company (12px muted), a wrapped row of chip tags (modality, location, status, discovered date — all same inset-shadow chip style, no fill), a 44px fit-score progress ring (only rendered if the job has a score) with the decision label (Apply/Review/Ignore) beneath it, and a "View Details" button (inset, muted → darker text on hover) that opens the job detail modal.

### Job details modal
Centered overlay (dark scrim behind, click-to-close), inset rounded modal (`border-radius: 24px`), a close (✕) button. Contents, in order: title + company, a meta row (Location / Modality / Salary / Fit score-if-present), a Strengths (✓, sage-colored heading) / Gaps (✗, terracotta-colored heading) section if present, a Required Skills chip list if present, and the full Description text. All identical data to what `JobDetailsModal` in the repo already renders — this is styling only.

## Design tokens
Same as other handoffs. Score/decision color mapping: Apply-tier (≥85) → sage (`--color-accent-2-700`), Review-tier (≥60) → terracotta (`--color-accent-700`), Ignore-tier/no-score → muted/faint gray. Progress ring: same SVG recipe as Dashboard/Applications (`viewBox 0 0 64 64`, `r=26`, `stroke-width=6`, rotated -90deg, `dasharray 163.36`, `dashoffset = 163.36 * (1 - score/100)`).

## Files
- `jobs.design.html` — prototype source (view source for exact markup/inline styles). Exported from a design tool; references a `support.js` runtime not included — treat as a markup/CSS reference, not a page to run standalone.
- `organic-styles.css` — the Organic design-system token sheet.
- See the Dashboard handoff for the Sidebar/Scout mascot spec and full shared tokens.
