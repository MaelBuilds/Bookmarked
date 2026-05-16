# Bookmarked — Card top edge (handoff for fresh start)

Copy this whole file into a new chat when revisiting the upload/result card top edge.

---

## Product context

**Bookmarked** — spoiler-free book catch-up. User photographs their page; app identifies the book, anchors to the passage, returns a summary of everything *up to that point*.

**Stack:** Flask (`server.py`) serves `frontend/dist`. UI is React + TypeScript + Panda CSS (Vite). Frosted “paper” cards on an illustrated background.

**Cards that need the edge:** upload card (`UploadCard.tsx`) and result card (`ResultView.tsx`). Same treatment on both.

**Card surface (unchanged):** cream frosted panel `rgba(253, 246, 232, 0.88)` + `backdrop-filter: blur(12px)`, light border, soft shadow, `border-radius: 4px`, `overflow: hidden`.

---

## What we want (outcome, not technique)

### Visual goal

The **top edge of the main frosted card** should feel like **torn or deckled paper** — as if the sheet was ripped from a notebook, not cut with scissors or drawn with a ruler.

| Quality | Target |
|--------|--------|
| **Shape** | Soft **scallops** (rounded dips and peaks), not sharp zigzags or triangle teeth |
| **Scale** | **Small** repeats along the width — “torn paper,” not cartoon waves or a few huge bumps |
| **Depth** | Roughly **10–20px** vertical bite at the deepest point (user first asked ~20px, then ~10px; treat as a tunable band) |
| **Tiling** | Pattern runs **flush edge-to-edge**: no half-scallop clipped at left/right; first and last “valley” at the corners should look intentional |
| **Proportion** | Edge must **not look squashed flat** against the top of the card (common failure when the mask stretches with card height) |
| **Overall read** | Warm, physical, librarian/bookshop — same family as the rest of the UI. Still reads as a **card**, not a gimmick |

### What success is *not*

- A straight top with `border-radius` only  
- Obvious **sawtooth / polygon** tear (reads harsh or digital)  
- **Busy** ripples (too many tight points — “too many ripples”)  
- **Flat** sinusoid that barely reads as depth  
- Different edge on upload vs result  
- A separate decorative strip that **doesn’t match** the card fill/blur (color or blur discontinuity)

### Non-goals for this pass

- Animating the edge  
- Torn bottom or sides (top only unless product asks otherwise)  
- Changing copy, layout inside the card, or global background

---

## Where it lives today (as of pause)

| Piece | Role |
|-------|------|
| `frontend/src/index.css` | Global class `.card-wavy-top` (Panda recipes don’t handle complex masks well) |
| `frontend/src/styles/appStyles.ts` | `uploadCard`, `resultSheet` — surface, padding (`46px` top), `overflow: hidden` |
| `UploadCard.tsx` / `ResultView.tsx` | `className={`${uploadCard} card-wavy-top`}`` (same for result) |

**Removed earlier:** `TornPaperEdge.tsx`, `TORN_TOP_CLIP` polygon in `constants.ts`.

**Preview gotcha:** `http://localhost:3000` serves **`frontend/dist`** — run `cd frontend && npm run build` after CSS changes. Dev HMR: Vite `http://localhost:5173`.

---

## Everything we tried (chronological)

### 1. Polygon clip on a separate strip

- **Idea:** `clip-path: polygon(...)` on an absolute div above the card (`TORN_TOP_CLIP`).  
- **Result:** Jagged, geometric tear; not the soft scalloped paper feel.  
- **Status:** Replaced; files deleted.

### 2. Wavy mask on a separate top strip

- **Idea:** Thin DOM strip with mask only; card body rectangular.  
- **Result:** Moved mask onto the card itself to avoid blur/fill mismatch.  
- **Status:** Strip approach abandoned (may still be valid for a clean restart).

### 3. Two-layer wavy mask on the full card (generator-style)

- **Idea:** Two `radial-gradient` masks, `repeat-x`, per [css-generators wavy-shapes](https://css-generators.com/wavy-shapes/) (top edge).  
- **Result:** Worked in principle but **`mask-size` height `100%` or `100vmax`** stretched the gradient over the **full card height** → scallops looked **squashed / flat** on tall cards.  
- **Lesson:** Wave tile height must be **decoupled** from card height.

### 4. Three-layer mask (body fill + two radials)

- **Idea:** Layer 1: solid `linear-gradient` for everything below a fixed band; layers 2–3: repeating radials in a **fixed `--mask-h`** band only.  
- **Result:** Restored real depth on tall cards. Edge visible and tiling improved.  
- **Still wrong (user feedback):** Reads **too sharp / sawtooth**, not soft torn paper; still **not convinced** after tuning.

### 5. Parameter tuning (same 3-layer approach)

| Knob | Values tried | User / visual outcome |
|------|----------------|------------------------|
| Period count `N` | 16.5 → **12** → **8** → **6** | Fewer periods = wider bumps; **6** still felt too sharp |
| Depth | **20px** → **10px** → **14px** (generator Border) | Flatter when too shallow; depth alone didn’t fix “sharp” |
| Radius / curvature | **12px → 6px** r; then generator **R/B** ratios | Small r vs wide period → flat ripples; scaled R helped visibility |
| Magic offsets | `7px`, `-3px` on layer 2 | Ad-hoc; replaced by generator **O/B**, **P/B** ratios |
| `mask-size` on tile | `var(--w) var(--mask-h)` not `100%` | **Required** — do not regress |
| Edge alignment | `0 0` + `calc(var(--w)/2) var(--P)` vs `50%` centering | Alignment mattered for corner scallops |
| Padding top | **48px → 38px → 46px** | Must track wave band + content breathing room |
| `mask-composite` | WebKit `source-over` vs standard `add` | Possible Safari delta — not fully validated |

### 6. Implementation bugs found (not aesthetic preferences)

- `calc(14px + 29.16%)` for `--mask-h` → **invalid**, mask silently failed (flat top on `:3000`).  
- `--R` as **% of card width** inside a **tile-sized** gradient → tiny/wrong circles.  
- **`--R` must be px** (or % **of the mask tile**, e.g. ~29% of period width), not % of card.  
- Stale **`frontend/dist`** vs source → looked like “no wave” until rebuild.

### 7. Fresh generator paste (last implementation pass)

- **Idea:** Top edge from css-generators ratios: `O/B=18/48`, `P/B=30/48`, `R/B=34.99/48`, `N=8` then **`N=6`**, `tear-depth=14px`.  
- **Result:** Edge **shows** on build; still described as **sharp / jagged**, not soft scallops. User wants to **start from scratch** with specs first.

---

## Constraints discovered (keep for any approach)

1. **Panda CSS:** Don’t rely on `::before` for mask/clip on recipes — use a **global class** in `index.css` or a plain DOM wrapper.  
2. **Frosted card:** `backdrop-filter` on the **same** element as `mask-image` — works in Chromium for this layout but has known cross-browser quirks; test Safari.  
3. **`overflow: hidden` + `border-radius: 4px`** on the card — may nip extreme mask peaks; usually minor at ~14px depth.  
4. **Tall cards:** Any technique that sizes the wave mask to **100% element height** will **flatten** scallops — band height must be fixed or SVG/viewBox-based.  
5. **Integer period count:** `width / N` for period `w` so left/right edges align (no half-repeat clipped).  
6. **Padding:** Top padding ≈ wave band height + ~16px so eyebrow/headline don’t sit in the scallops.

---

## Current CSS snapshot (for reference only — candidate to replace)

```css
.card-wavy-top {
  --n: 6;
  --tear-depth: 14px;
  --w: calc(100% / var(--n));
  --O: calc(var(--tear-depth) * 18 / 48);
  --P: calc(var(--tear-depth) * 30 / 48);
  --R: calc(var(--tear-depth) * 34.99 / 48);
  --mask-h: calc(var(--tear-depth) + var(--R));
  /* 3 layers: linear body + 2 radial repeat-x, fixed mask-h tile */
}
```

Applied on: `uploadCard` + `resultSheet` with `card-wavy-top`.

---

## Fresh start — outcome-first directions (pick in new chat)

These are **options**, not commitments. Choose based on how the reference should look.

### A. Reference-led SVG (often best for “soft torn”)

- Design **one period** of the top edge as an SVG path (smooth Bézier scallops, slight irregularity).  
- `mask-image` or `clip-path` with `repeat-x` or stretched `viewBox` to card width.  
- **Pros:** Full control over softness; no generator math. **Cons:** Must hand-tune or draw in Figma.

### B. Single raster/SVG asset

- Export a transparent **PNG/SVG strip** (2× for retina) for the top ~24px, repeat or stretch width.  
- **Pros:** WYSIWYG. **Cons:** Less crisp on ultra-wide; asset maintenance.

### C. Pseudo-element “cap” only

- Card body **rectangle**; separate top cap (real `motion.div` or wrapper) with mask/clip **only on the cap** (~24–32px tall), same frosted styles.  
- **Pros:** Avoids 3-layer composite on full card height. **Cons:** Extra DOM; align blur at seam.

### D. Revisit CSS mask only after a locked reference

- Pick a **screenshot or paper photo** → match in generator or code.  
- Do not tune `N`/px in the abstract.

**Recommendation for new chat:** Start with **a reference image** (mockup or photo of real torn paper on cream stock). Implement **A or C** to match the reference; treat current `.card-wavy-top` as **delete-and-replace**, not iterate.

---

## Prompt stub for new chat

```
Bookmarked — card top edge (fresh start)

Read: docs/card-top-edge-handoff.md

Goal: Soft torn-paper / deckled top on frosted upload + result cards — small rounded scallops, ~10–20px depth, edge-to-edge tiling, not sharp zigzags. Outcome-first; current .card-wavy-top is not accepted.

Start from a reference [attach mockup or describe]. Replace current approach; keep frosted card surface and Panda layout. Test on :5173 and rebuild for :3000.

Do not edit the handoff doc unless I ask.
```

---

## Open questions for product

1. **Reference:** Do we have a mockup, Dribbble, or photo of the exact edge we want?  
2. **Irregularity:** Perfectly regular scallops vs slightly **irregular** tear (more “hand torn”)?  
3. **Depth:** Lock **10px**, **14px**, or **20px** as the default?  
4. **Acceptance:** Upload + result only, or header/footer cards later?

---

*Last updated: handoff compiled after user feedback “still not convinced — start from specs / scratch.”*
