# Handoff: Profile screen (Scout / aiNeedJob)

## Overview
Second screen in the warm/organic redesign (Dashboard was first). Same "Design Inside" visual language and shared Scout sidebar — this doc only covers what's new/specific to Profile. Recreate inside the real frontend (`frontend/` in `aINeedaJob`, Next.js/React/Tailwind) using real user data from `UserProfile`, not the hardcoded sample values shown here.

## Fidelity
High-fidelity for colors, type, spacing, radii, shadows, and the "pressed-in" component style — implement close, not just "inspired by." Sample copy/values (name, email, skills, salary) are illustrative only.

## Shared chrome (already delivered in the Dashboard handoff — don't rebuild, reuse)
Sidebar (collapsible, Scout mascot with breathing/blinking/eye-drift/talking-mouth animations, nav list, logout, theme toggle next to the logo), the pressed-in vs. popped-out design language, and all color/type/shadow tokens are identical to the Dashboard handoff. If that component isn't built yet, build it once and share it — Profile just marks "Profile" as the active nav row (solid inset background + bold text, vs. plain/hover-only for the others).

## Layout
Single column, `main` max-width 900px, centered, `padding: 44px 50px 70px`. Sections stack vertically with `20-32px` gaps, each its own inset-shadowed rounded panel (`border-radius: 24px`, same inset shadow recipe as Dashboard: `inset 0 3-4px 10-14px rgba(32,30,29,.16-.2), inset 0 -1px 0 rgba(255,255,255,.4)`).

## Sections (top to bottom)

### 1. Header row
Avatar (68px, blob-shaped like the mascot's face shape but a plain gradient fill + initial letter, no eyes/mouth), name (Caprasimo 32px) + email (13.5px muted) stacked next to it, and a "Save changes" pill button (inset, accent-700 text) pinned right.

### 2. Résumé card
Small mascot-face icon (44px, same gradient/eyes/mouth language as the sidebar mascot but static, no animation) + "Résumé on file" title + a line naming the file and upload date + an inset "Upload new CV" button on the right.

### 3. Gmail connection card
Mail icon (sage/accent-2 colored, NOT the primary terracotta accent — this got explicitly called out and changed from accent to accent-2 green) + "Gmail connected" + the connected address + an inset "Disconnect" button.

### 4. Target roles card
Wrapped pill list of role tags, colored `--color-accent-700` text (no fill, just inset shadow + colored text), plus a dashed-border "+ Add role" pill in muted color at the end.

### 5. Skills card
Same wrapped-pill pattern as Target roles, but colored sage/green: text `--color-accent-2-800` on a `--color-accent-2-100` **fill** (not just colored text like Target roles — Skills got an explicit green background treatment). Each pill has a staggered fade-up entrance animation (`ainFadeUp`, 0.5s, delayed ~0.05s per item) and scales up slightly on hover (`transform: scale(1.06)`, springy `cubic-bezier(.34,1.56,.64,1)` timing). Same dashed "+ Add skill" pill at the end, no fill.

### 6. Languages + Nationality (2-column grid, 20px gap)
**Languages card:** one row per language — label on the left (13px), a real `<select>` dropdown on the right showing proficiency (Native/Fluent/Intermediate/Basic). **Nationality card:** a single `<select>` dropdown (Mexican/American/Canadian/Spanish/etc.).

**All dropdowns on this screen share one style** — this is a deliberate, explicit design decision (the user asked for "the same style" across every select on the page): native `<select>`, `appearance: none`, pill-shaped (`border-radius: 999px`), background `var(--dbg)` (NOT `--dcard` — one step darker than the card it sits in, to read as inset), `box-shadow: inset 0 2px 5px rgba(32,30,29,.18)` (no outer shadow at all — it must look pressed IN, not raised), a chevron-down SVG icon absolutely positioned inside on the right (`pointer-events: none`, colored `--dfaint` normally or the row's accent color for emphasized selects), font weight 600-700, small sizes (12-13px). Wrap each select in a `position: relative` container so the chevron can be absolutely positioned over it.

### 7. "Where you'll work" card
- Row 1: "Modality" label + a select (Remote/Hybrid/On-site) styled like the others but emphasized — bigger padding, bold accent-700 colored text/chevron, deeper inset shadow (`inset 0 2px 5px rgba(32,30,29,.2)`) since this is the primary preference.
- Row 2: "Priority country" label + a plain-style select (México/United States/Canada).
- Row 3, below both: "Also searching in" (12px muted label) + a wrapped pill list of the other countries the user is open to — this list is INTENTIONALLY SEPARATE from the Priority country dropdown above it (they show different things: one primary choice vs. a broader list) — don't collapse them into one control or duplicate the same countries in both places. First pill (priority match) can carry a 🥇 emoji + solid text color; the rest are muted; a dashed "+ Add country" pill closes the list.

### 8. Minimum salary + Links (2-column grid, 20px gap)
**Minimum salary card:** label + a large Caprasimo number (26px), e.g. "$120,000" — read-only display here, but should be an editable number input in the real build.
**Links card:** GitHub and LinkedIn URLs as plain accent-colored links, stacked, no icons.

## Interaction notes
- Selects should look and behave like normal native `<select>` elements (full keyboard/native picker support) — the custom look is achieved via `appearance: none` + wrapper + fake chevron icon, not a custom-built dropdown widget.
- "Save changes" should persist edits to the real user profile.
- Skills/Target roles "+ Add" pills should open an input or tag-picker in the real implementation.

## Design tokens
Same as the Dashboard handoff — see that README for the full light/dark color tables, type scale, and radius/shadow scale. Key colors used here specifically:
- Target roles pills: text `--color-accent-700`, muted "+Add" in `--faint`.
- Skills pills: text `--color-accent-2-800` on fill `--color-accent-2-100` (note the ramp step change from Target roles — this is deliberate, not a mistake to "fix" back to matching).
- Gmail icon: `--color-accent-2` (sage), not `--color-accent` (terracotta) — this was explicitly corrected from an earlier orange version.
- Select dropdown backgrounds: `--dbg`, not `--dcard`.

## Files
- `profile.design.html` — prototype source (view source for exact markup/inline styles — every value above was taken directly from it). Exported from a design tool; references a `support.js` runtime not included here, so treat as a markup/CSS reference rather than a page to run standalone.
- `organic-styles.css` — the Organic design-system token sheet this design draws from.
- See the Dashboard handoff package for the Sidebar/Scout mascot spec, shared tokens, and the world-globe build recipe (all reused here unchanged).
