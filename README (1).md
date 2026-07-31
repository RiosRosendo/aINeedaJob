# Handoff: Dashboard (Scout / aiNeedJob)

## Overview
Redesign of the main Dashboard screen for the job-search agent app, moving from the dark tech/AI-slop look to a warm, "organic," friendly aesthetic centered on a mascot ("Scout"). This is the first of several screens (Jobs, Approvals, Applications, Profile follow the same system, to be handed off one at a time as they're finalized).

## About the design files
The file in this bundle (`dashboard.design.html`) is a **design reference built in HTML/CSS** — a high-fidelity prototype of look, layout, and interaction, not production code to import as-is. The task is to **recreate this design inside the actual frontend codebase** (`frontend/` in the `aINeedaJob` repo — Next.js/React/Tailwind) using its existing component structure, data flow, and routing. Reuse the app's real data (job counts, activity feed, applications) instead of the hardcoded sample content shown here.

## Fidelity
**High-fidelity.** Colors, type, spacing, radii, and shadows below are final — implement pixel-close, not just "inspired by." Two things are illustrative and can flex: the exact copy/sample numbers, and the mascot's proportions (get the concept — a soft blob face with moving eyes/mouth — right; exact pixel geometry is not sacred).

## Screens / Views
### Dashboard
**Purpose:** Landing screen after login — shows scan status, headline stats, where jobs are being found (world map), recent agent activity, and jobs awaiting approval.

**Layout:** Full-height flex row: a collapsible left sidebar (`aside`) + a scrollable main content column (`main`, `max-width: 1050px`, centered, `padding: 44px 50px 70px`).

## Design language: "pressed-in" panels, "popped-out" accents
This is the core visual idea, apply it consistently to every screen:
- Structural containers (stat strip, activity panel, globe panel, job cards) use an **inset/pressed shadow** so they read as carved into the page: `box-shadow: inset 0 3px-4px 10-14px rgba(32,30,29,.16-.2), inset 0 -1px 0 rgba(255,255,255,.4)`.
- Small interactive "chips" (status tags like Remote/On-site, the nav's active-row) use a **tighter inset**: `inset 0 1-2px 3-5px rgba(32,30,29,.15-.18)`.
- The two things that should still feel "alive"/tactile are the **mascot** (raised, glossy, drop-shadowed) and the **fit-score progress rings + Approve button hover accent color** (accent-colored text on press, not a filled gradient button — see Components).
- Buttons ("Details", "Approve", "Logout", nav icon buttons) are also inset/pressed, not raised — text color is the differentiator (Approve = accent-700 colored text on hover accent-800; Details = muted).

## Components

### Sidebar (`aside`)
- Width animates between `250px` (open) and `88px` (collapsed) — `transition: width .38s cubic-bezier(.4,0,.2,1)`.
- `border-right: 1px solid var(--border)` (must be visible in BOTH light and dark themes — this was a bug we fixed: don't rely on shadow alone, which disappears on dark backgrounds).
- **Header row:** logo mark (26×26px blob, `border-radius: 38% 62% 55% 45% / 50% 45% 55% 50%`, gradient `linear-gradient(140deg, accent, accent-2)`, gentle rotation animation ±4deg over 5s) + "aiNeedJob" wordmark (Caprasimo, 16px) — click toggles sidebar collapse. A theme-toggle icon button (sun/moon, 30×30px, inset shadow) sits at the right end of this same row, only visible when the sidebar is open.
- **Mascot "Scout"**: circular/blob avatar (120px open / 46px collapsed), gradient fill (3-stop: accent-200 → accent → accent-700), soft drop shadow beneath it (blurred ellipse), a highlight blob top-left, two round eyes and a curved-line mouth (all `var(--bg)` colored cutouts). Animations: gentle breathing scale (3.2s), eyes drift in a small path + blink periodically (~6s loop + ~4.5s blink), mouth subtly resizes as if talking (~3.4s loop). Below it: "Scout" name (Caprasimo 19px) + "on the clock — watching 847 roles" (12px, muted), hidden when collapsed.
- **Nav list**: Dashboard / Jobs / Approvals (with a count badge) / Applications / Profile. Pill rows (`border-radius: 999px`, `padding: 11px 16px`), icons from Lucide at stroke-width 2.75. Active row (Dashboard) has an inset pressed background; inactive rows get the same inset on hover.
- **Logout button** at the bottom: full-width pill, inset shadow (matches nav/embedded language), icon + label.

### Stat strip
One inset-shadowed rounded panel (`border-radius: 24px`) containing 4 columns separated by thin 1px dividers: Jobs found (847), Applied (23), Interviews (2), Needs approval (5, with a small accent dot). Big number in Caprasimo 34px, label 11px uppercase/tracked, colored per-stat (accent-700 for the primary stat, muted for the rest).

### World map panel
Inset-shadowed rounded panel containing a **3D-looking globe**: a circular, raised (drop-shadowed, glossy-highlighted) image of an orthographic-projection world map (accurate country geometry, not hand-drawn) recolored to the theme (warm tan land / cream ocean in light mode, tan land / dark cocoa ocean in dark mode — swap image by theme). Small colored dot markers sit on top at real lat/long-derived positions for the job source countries (México, US, Canada, Spain, Remote); the "current/latest" marker gets a pulsing ring. Below the globe: pill chips listing each country + job count.
- Real geographic data needed here — do not hand-draw country shapes. Use a mapping library (e.g. d3-geo + a topojson world atlas, react-simple-maps, or platform equivalent) with an orthographic/globe projection, recolored via CSS/theme, rather than embedding our flat PNGs directly — the PNGs in `assets/` are references for the intended look/colors only.

### How to actually build the globe (step-by-step for Claude Code)
This is a real rendered map, not an image or an icon — here's the exact recipe used to produce the reference PNGs, so it can be reimplemented as a live, theme-able component:

1. **Get real geometry.** Fetch a world-atlas TopoJSON file (e.g. `world-atlas@2.0.2/countries-110m.json` from a CDN, or install it as an npm package) and convert it to GeoJSON country features with `topojson-client`'s `topojson.feature(topology, topology.objects.countries)`. Do not hand-draw or approximate coastlines.
2. **Project it as a globe, not a flat map.** Use `d3-geo`'s `d3.geoOrthographic()` projection (this is what makes it look like a sphere/globe instead of a rectangle):
   ```js
   const projection = d3.geoOrthographic()
     .scale(radius)              // radius in px, e.g. 229 for a 480px-wide SVG
     .translate([size/2, size/2])
     .rotate([50, -22, 0])       // [longitude, latitude, roll] — picks which side of the globe faces the viewer; rotate() is how you'd "spin" it interactively later
     .clipAngle(90);             // hides the far side of the sphere — critical, without this you get a flat oval instead of a globe
   const path = d3.geoPath(projection);
   ```
3. **Draw three layers into an SVG, in this order:**
   - Sphere/ocean: `path({type: 'Sphere'})` filled with the ocean color — this draws the full circle background.
   - Graticule (faint lat/long grid lines) — optional polish: `d3.geoGraticule()`, stroked very thin and low-contrast.
   - Countries: one `<path>` per GeoJSON feature, `d="{path(feature)}"`, filled with the land color, thin stroke in the ocean color (so borders look clean).
4. **Recolor per theme** — just 3 colors total, swapped by light/dark state (see palette below). Nothing else about the geometry changes.
5. **Add the "pop out" 3D look on TOP of the SVG** (this part is plain CSS, not d3): wrap the SVG in a circular container (`border-radius: 50%; overflow: hidden`) and apply:
   - Drop shadow for lift: `box-shadow: 0 18-22px 34-40px -14px rgba(32,30,29,.35-.4)`
   - Inner highlight + inner shade to fake sphere lighting: `inset 0 4px 10px rgba(255,255,255,.4), inset 0 -8-10px 16-18px rgba(64,35,16,.18-.22)`
   - A soft radial-gradient highlight overlay on top (pointer-events: none): bright glow top-left, subtle dark falloff bottom-right, e.g. `radial-gradient(circle at 30% 26%, rgba(255,255,255,.55), transparent 55%), radial-gradient(circle at 72% 78%, rgba(64,35,16,.4), transparent 55%)`.
6. **Place job-source markers** by projecting real coordinates through the SAME projection function: `const [x, y] = projection([longitude, latitude])`. This returns null/undefined if the point is on the globe's far side (`clipAngle` hides it) — hide the marker in that case. Render each marker as a small absolutely-positioned dot at `(x, y)` in the SVG's coordinate space; give the newest one an extra pulsing ring (`animation: scale+fade-out on loop`).
7. **(Nice-to-have, not required for parity):** since the projection is already set up, `rotate()` can be animated/dragged for an interactive spinning globe later — the current design only needs the static "posed" look above.

**Color palette to use (3 colors per theme):**
- Light theme: ocean `#f6ecd9`, land `#847a5e`, grid `#e6dcc4`.
- Dark theme: ocean `#3a2c1e` (matches card color), land `#c7b59c`, grid `#4a3b28`.
- Marker dots use the brand accent colors (`--color-accent` terracotta / `--color-accent-2` sage), not the map's own palette.

**Reference implementation** (exact code used to generate the PNGs in `assets/`, safe to adapt almost directly for a live component):
```html
<script src="https://unpkg.com/d3@7/dist/d3.min.js"></script>
<script src="https://unpkg.com/topojson-client@3/dist/topojson-client.min.js"></script>
<script>
const size = 480, radius = 229;
const projection = d3.geoOrthographic().scale(radius).translate([size/2, size/2]).rotate([50, -22, 0]).clipAngle(90);
const path = d3.geoPath(projection);
const svg = d3.select('#map'); // <svg id="map" width="480" height="480">
const graticule = d3.geoGraticule();

fetch('https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/countries-110m.json')
  .then(r => r.json())
  .then(topology => {
    const countries = topojson.feature(topology, topology.objects.countries);
    svg.append('path').attr('d', path({type: 'Sphere'})).attr('fill', OCEAN_COLOR);
    svg.append('path').attr('d', path(graticule())).attr('fill', 'none').attr('stroke', GRID_COLOR).attr('stroke-width', 0.5);
    svg.selectAll('path.country').data(countries.features).enter().append('path')
      .attr('d', path).attr('fill', LAND_COLOR).attr('stroke', OCEAN_COLOR).attr('stroke-width', 0.6);

    // Marker example — Stripe/México job source:
    const [mx, my] = projection([-102, 23]) || [];  // [longitude, latitude]
    // if mx/my are defined, render a dot at that pixel position
  });
</script>
```
In React, the equivalent is a `useEffect` that runs this d3 selection logic against an SVG ref, or — cleaner — a library like `react-simple-maps` (which wraps the same d3-geo/topojson approach) with its `Geographies`/`Geography`/`Marker` components and `geoOrthographic` passed as the projection.

## Fixing a first-pass React implementation that looks flat
If an implementation renders the correct map but it still looks "flat"/pasted-on rather than a raised glossy sphere, it's almost always these 4 things:

1. **The container isn't a perfect circle.** Use identical width AND height (e.g. `480px` / `480px`) — a 460×480 box with `border-radius: 100%` renders an oval, not a sphere. `border-radius: 50%` is equivalent and clearer intent than `100%`.
2. **The glossy highlight is on the wrong layer.** The radial-gradient "shine" (`radial-gradient(circle at 30% 26%, rgba(255,255,255,.55), transparent 55%), radial-gradient(circle at 72% 78%, rgba(64,35,16,.4), transparent 55%)`) must sit as its OWN absolutely-positioned `pointer-events: none` div stacked ON TOP of the `<svg>` (higher z-index / later in DOM order). Setting it as the wrapper `<div>`'s own `background` puts it BEHIND the SVG, and since the SVG's ocean fill is opaque, the gradient never shows — that's why it can look flat even though the code is "there."
3. **The shadow is too weak / missing the sphere-lighting inset.** A small flat `0 4px 8px -4px` drop shadow reads as a sticker. Use a bigger, softer lift shadow (`0 18-22px 34-40px -14px rgba(32,30,29,.35-.4)`) plus TWO inset shadows on the same circular wrapper to fake light wrapping around a sphere: a bright inset near the top (`inset 0 4px 10px rgba(255,255,255,.4)`) and a darker inset near the bottom (`inset 0 -8-10px 16-18px rgba(64,35,16,.18-.22)`).
4. **Land color is a shade too light.** Use `#847a5e` for the light-theme land (not a paler tan like `#c9b8a0`) — it's what gives the globe enough contrast against the cream ocean to read as textured land rather than a faint blob.

Corrected wrapper markup (React/inline-style form, drop-in replacement for the "outer circle div" in a component like this):
```jsx
<div style={{
  position: 'relative',
  width: '460px',
  height: '460px',            // match width — was 480 before, mismatched
  borderRadius: '50%',
  overflow: 'hidden',
  boxShadow: `
    0 22px 40px -14px rgba(32,30,29,.4),
    inset 0 4px 10px rgba(255,255,255,.4),
    inset 0 -10px 18px rgba(64,35,16,.2)
  `,
}}>
  <svg ref={svgRef} width="480" height="480" viewBox="0 0 480 480"
    style={{ display: 'block', width: '100%', height: '100%' }} />
  {/* highlight overlay MUST be a sibling on top of the svg, not the wrapper's background */}
  <div style={{
    position: 'absolute', inset: 0, borderRadius: '50%', pointerEvents: 'none',
    background: 'radial-gradient(circle at 30% 26%, rgba(255,255,255,.55), transparent 55%), radial-gradient(circle at 72% 78%, rgba(64,35,16,.4), transparent 55%)',
  }} />
</div>
```
Also swap the light-theme `land` color to `#847a5e` in the `lightTheme` object, and consider only pulsing the single newest/most-recent marker (not all of them) — several markers pulsing at once reads as noisy rather than "alive."

### "Fresh from Scout" card + Agent activity
Two side-by-side inset panels. Left: a small mascot avatar (same face language, smaller) next to a short first-person message from Scout, in quotes. Right: "Agent activity" list — 3-5 rows, each a colored vertical bar (accent = newest/highlighted, neutral = older) + a line of activity copy (bold for entity names) + relative timestamp, with a staggered slide-in-from-left entrance animation.

### Job cards ("Jobs waiting on you")
3-column grid of inset-shadowed rounded cards (`border-radius: 24px`). Each: company (12px muted) + role title (Caprasimo 17px), a circular SVG "fit score" progress ring (stroke-based, colored per job) with the score number centered, a status chip (Remote/On-site — plain text colored by type, sitting on an inset chip, not a filled pill), and two full-width pill buttons: "Details" (muted/inset) and "Approve" (inset, accent-colored text, darkens further on press).

## Interactions & behavior
- **Sidebar collapse**: click the logo/wordmark row → toggles between 250px and 88px; all labels fade via conditional render (not just opacity) so they don't reflow oddly.
- **Theme toggle**: click sun/moon icon → swaps the entire palette (see Design Tokens) including the globe image. Persist the user's choice (e.g. localStorage) in the real app.
- **Card hover**: job cards lighten their inset shadow slightly on hover (feels like the surface is being "pressed less").
- **Button hover/press**: Approve text darkens on hover, shadow deepens further on `:active`.
- Scout's ambient animations (breathe / eyes drift+blink / mouth) all loop continuously and don't require any user action — implement as CSS keyframes, not JS-driven.

## State management
- `sidebarOpen: boolean` — controls sidebar width + conditional rendering of labels.
- `isDark: boolean` — controls theme tokens + globe image src.
- Stat/activity/job data should come from the app's real API/state, not be hardcoded.

## Design tokens

### Colors — Light theme
| Token | Value | Use |
|---|---|---|
| `--bg` | `#f0e4cf` | Page background |
| `--card` | `#fffaf1` | Panel/card fill |
| `--active` | `#ebddc5` | Hover/active fill |
| `--border` | `rgba(32,30,29,.1)` | Dividers (sidebar) |
| `--border-soft` | `rgba(32,30,29,.06)` | Subtle dividers |
| `--text` | `#201e1d` | Primary text |
| `--muted` | `#645c50` | Secondary text |
| `--faint` | `#82796a` | Tertiary text/labels |
| `--track` | `#dcd3c4` | Progress ring track |

### Colors — Dark theme (warm, NOT navy/black)
| Token | Value |
|---|---|
| `--bg` | `#2b2118` |
| `--card` | `#3a2c1e` |
| `--active` | `#463625` |
| `--border` | `rgba(245,234,216,.16)` |
| `--border-soft` | `rgba(245,234,216,.08)` |
| `--text` | `#f7ecd9` |
| `--muted` | `#d1bd9c` |
| `--faint` | `#a68f72` |
| `--track` | `rgba(245,234,216,.16)` |

### Brand accents (from the Organic design system, both themes)
- `--color-accent` (terracotta): base `#c67139`, with a 100–900 tonal ramp available (100/200/300 = light tints, 700/800 = dark/text-safe shades).
- `--color-accent-2` (sage): base `#7a8a5e`, same ramp structure.
- Use light ramp steps (100-300) for tinted fills, base (500-ish) for primary color moments (logo gradient, mascot, progress rings), dark steps (700-800) for text-on-tint.

### Typography
- Headings: **Caprasimo** (display serif-ish, rounded) — sizes used: 44px (page title), 34px (stat numbers), 19px/17px/16px/13px (card/section titles).
- Body: **Figtree** — sizes 14/13/12/11.5/11px, weights 400-700.
- Section eyebrows: 11-12px, uppercase, `letter-spacing: .06-.07em`, muted color.

### Radius & shadow scale
- Large panels: `24px` radius.
- Cards: `24px`.
- Nav rows / buttons / chips: `999px` (full pill).
- Small icon buttons: `10-14px`.
- Inset panel shadow: `inset 0 3-4px 10-14px rgba(32,30,29,.16-.2), inset 0 -1px 0 rgba(255,255,255,.4)`.
- Inset chip/button shadow: `inset 0 1-2px 3-5px rgba(32,30,29,.15-.18)` (deeper, `inset 0 2-3px 5-7px`, for primary actions like Approve).
- Mascot/raised elements: normal (non-inset) drop shadows, e.g. `0 10px 20px -6px rgba(32,30,29,.4)` plus soft inner highlight/shade for a glossy look.

## Assets
- `assets/world-globe-light.png`, `assets/world-globe-dark.png` — reference renders only (orthographic world projection, real country geometry via d3-geo/topojson, recolored). Reimplement as a live map component in the target stack rather than shipping these PNGs, so it can theme, and ideally interact (rotate/pan/zoom) later.
- `assets/organic-styles.css` — the full Organic design-system token sheet (colors, ramps, type, spacing) this design draws from, for exact hex/ramp reference.
- Icons: Lucide icon set, stroke-width 2.75.
- Fonts: Caprasimo, Figtree — both Google Fonts.

## Files
- `dashboard.design.html` — the prototype source (view source for exact markup/inline styles if any measurement above is ambiguous — every value in this doc was taken directly from it). It's exported from a design tool and references a `support.js` runtime that isn't included here, so it won't render standalone by double-clicking — treat it as a markup/CSS reference, not a page to run.
