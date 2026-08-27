# AI CAPTCHA — Visual Design Proposal

**Goal:** make the UI feel like a polished, premium AI/dev-tool product (Linear / Vercel / Anthropic tier) instead of "dark theme with gradients."

**Constraint honored:** no external dependencies — everything below is CSS + a few lines of vanilla JS. Fonts stay on a system stack (optional self-host noted).

**Research inputs:** live review of Linear's homepage (premium dark, product-UI-in-hero, figure-caption framing) and Vercel's Geist design system (semantic 10-step gray scale, high-contrast text, radii 6/12/16px, sans+mono pairing), plus the current 2025 AI-product canon (Anthropic's restraint, OpenAI's minimalism, Perplexity's single-accent cleanliness, Linear/Vercel glow + grid backgrounds, bento grids, noise textures, conic-border cards, status pills, micro-interactions).

---

## 1. Diagnosis — why it reads as "basic"

| Problem | Current state | Why it feels cheap |
|---|---|---|
| 3-color gradient everywhere | `#38bdf8 → #818cf8 → #f472b6` on logo, h1, buttons, eyebrow | The sky-indigo-pink triad is the default "AI startup" gradient of 2021. Premium products use **one** accent and let typography carry the identity. |
| Background is static | Two fixed radial gradients | No depth, no motion, no texture. Premium dark pages layer aurora + grid + grain. |
| Feature grid is uniform | 6 identical cards, emoji icons | Uniform tiles read as template. Bento (mixed-size) grids read as designed. |
| No product-in-hero | Hero is text-only | Linear/Stripe/Vercel all show the product UI inside the hero. It's the single biggest "real product" signal. |
| Details missing | No noise, no glow shadows, no focus rings, flat code blocks, timer is just text | Micro-detail is what separates "dark mode" from "premium." |

---

## 2. Design Tokens (paste-ready)

### 2.1 Color palette

Strategy: **one dominant accent (cyan)**, a restrained indigo secondary reserved for gradients/backgrounds only, high-contrast neutral scale. Drop pink from UI chrome (keep it only as a faint aurora tint).

```css
:root {
  /* Neutrals — deeper + higher contrast than current */
  --bg:        #05070d;   /* page — near-black, slight blue */
  --bg-2:      #0a0e17;   /* raised bg / inputs */
  --surface:   #0d1322;   /* cards */
  --surface-2: #131b2e;   /* card hover, th, nested */
  --border:    #1b2540;   /* default hairline */
  --border-2:  #2b3a5e;   /* hover border */

  /* Text — bump contrast up */
  --text:       #f2f6fc;  /* was #e6ecf7 */
  --text-dim:   #9aa8c0;
  --text-faint: #5d6e8c;

  /* Accent — single dominant hue */
  --accent:      #22d3ee;  /* cyan-400: links, focus, highlights */
  --accent-deep: #0891b2;  /* pressed/active */
  --accent-soft: rgba(34, 211, 238, 0.10);
  --accent-2:    #818cf8;  /* indigo — gradients/backgrounds ONLY */

  /* Gradient — 2 stops now, used sparingly (logo tile, hero word, primary CTA) */
  --grad: linear-gradient(135deg, #22d3ee 0%, #818cf8 100%);
  --grad-soft: linear-gradient(135deg, rgba(34,211,238,.10), rgba(129,140,248,.10));

  /* Semantic */
  --green: #34d399;  --green-soft: rgba(52,211,153,.12);
  --red:   #f87171;  --red-soft:   rgba(248,113,113,.12);
  --amber: #fbbf24;

  /* Glow shadows — the "premium" signal */
  --glow-sm:  0 0 20px rgba(34,211,238,.25);
  --glow-md:  0 0 40px -8px rgba(34,211,238,.35);
  --shadow:   0 1px 2px rgba(0,0,0,.4), 0 8px 24px rgba(0,0,0,.35);
  --shadow-lg: 0 1px 2px rgba(0,0,0,.4), 0 24px 60px -12px rgba(0,0,0,.6);

  /* Radii — aligns with Geist (6/12/16) */
  --radius-xs: 6px;  /* badges, code chips */
  --radius-sm: 8px;  /* inputs, buttons */
  --radius:    12px; /* cards */
  --radius-lg: 16px; /* hero panel, modals */

  /* Spacing — 4px base scale */
  --s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 24px;
  --s6: 32px; --s7: 48px; --s8: 64px; --s9: 96px;
}
```

**Key change:** `box-shadow: 0 4px 14px rgba(56,189,248,.35)` (colored blur on everything) → `--glow-sm/--glow-md` used **only** on the primary CTA, logo tile, and result badges. Colored glow loses impact when it's on six elements at once.

### 2.2 Typography

```css
--font: "Inter", "SF Pro Display", -apple-system, BlinkMacSystemFont,
        "Segoe UI", Roboto, sans-serif;
--mono: "JetBrains Mono", ui-monospace, "SF Mono", "Cascadia Code",
        Menlo, monospace;
```

- **Optional zero-dependency upgrade:** download Inter var + JetBrains Mono woff2 (OFL license) into `static/fonts/`, `@font-face` with `font-display: swap`. This alone noticeably lifts perceived quality. If skipped, the system stack above is fine.

| Role | Spec |
|---|---|
| Hero H1 | 56–64px desktop (`clamp(2.75rem, 6vw, 4rem)`), weight **750**, `letter-spacing: -0.03em`, `line-height: 1.05` |
| Section H2 | 28–32px, weight 700, `letter-spacing: -0.02em` |
| Card H3 | 17px, weight 650, `letter-spacing: -0.01em` |
| Body / lead | 16px / 18px, `line-height: 1.65`, `color: var(--text-dim)` |
| **Eyebrow / labels** | **11px, weight 600, uppercase, `letter-spacing: 0.08em`, color accent** |
| Buttons / nav | 14px, weight 600, `letter-spacing: 0` (drop the current .2px) |
| Code, timer, stats | `--mono`, `font-variant-numeric: tabular-nums` |
| Small / meta | 13px, `--text-faint` |

**Key change:** negative tracking on display type (-0.02/-0.03em) + mono for data (timer, stats, badges, eyebrows on terminal-flavored elements). Tight type is the #1 "designed" tell; the current `1.15rem/800` everywhere with default tracking reads generic.

### 2.3 Component specs

**Nav (topbar)**
- Height 60px; `background: rgba(5,7,13,.72); backdrop-filter: blur(16px) saturate(1.4)`.
- Add bottom border **only after scroll**: tiny JS toggles `.scrolled` → `border-bottom-color: var(--border)`.
- Links: 14px/500 dim → hover text; **active page link** gets a pill: `background: var(--surface-2); border: 1px solid var(--border); padding: 6px 12px; border-radius: 999px`.
- CTA: solid `var(--accent)` at **90% saturation with dark text** (`color: #04141a; font-weight: 650`) — light-on-dark buttons with dark text are the current Linear/Vercel pattern and contrast better than white-on-gradient.

**Buttons**

```css
.btn { padding: 10px 20px; border-radius: 10px; font-size: 14px; font-weight: 600;
       transition: transform .15s ease, box-shadow .2s ease, background .2s ease; }

.btn-primary {
  background: var(--grad); color: #fff;
  box-shadow: var(--glow-md), inset 0 1px 0 rgba(255,255,255,.18); /* inset = bevel hint */
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: var(--glow-md), inset 0 1px 0 rgba(255,255,255,.18), 0 0 0 1px rgba(255,255,255,.08); }
.btn-primary:active { transform: translateY(0); filter: brightness(.92); }

.btn-ghost { background: var(--surface); border: 1px solid var(--border-2); color: var(--text); }
.btn-ghost:hover { border-color: var(--accent); background: var(--accent-soft); }
```
Add a **focus-visible ring everywhere**: `:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }` (currently missing entirely).

**Cards**
- `background: linear-gradient(180deg, rgba(255,255,255,.03), transparent 40%), var(--surface);` — a 3% top sheen makes flat cards feel lit.
- `border: 1px solid var(--border); border-radius: var(--radius); box-shadow: var(--shadow);`
- Hover: `border-color: var(--border-2); box-shadow: var(--shadow-lg); transform: translateY(-2px);` with `transition: .25s ease`.
- Badge/pill: `background: var(--surface-2); border: 1px solid var(--border); border-radius: 999px; padding: 4px 12px; font-size: 12px; font-weight: 600; color: var(--text-dim);` with an 8px status dot.

**Inputs**
- `background: var(--bg-2); border: 1px solid var(--border); border-radius: var(--radius-sm);`
- Focus: `border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft);` (already close — keep).
- Labels: 12px/600/dim, **no uppercase** for form labels (uppercase + uppercase eyebrow = noisy); reserve caps for the hero eyebrow and stat labels.

**Code blocks**
- Header bar: 36px, `var(--surface-2)`, bottom border, three 10px traffic dots (`#f87171 #fbbf24 #34d399` at 60% opacity), language label in mono 11px dim, right-aligned "copy" ghost button.
- Body: `background: #080b12; padding: 16px; font-size: 13px; line-height: 1.7; color: #c4d0e4;` — slightly dimmer than card surface so cards and code don't merge.

---

## 3. Five concrete visual improvements

### 3.1 Ambient background system (aurora + grid + grain) — biggest single upgrade

Replace the static body background with three stacked fixed layers:

```css
body { background: var(--bg); }

/* Layer 1: aurora blobs — slow drift */
body::before {
  content: ""; position: fixed; inset: -20%; z-index: -2; pointer-events: none;
  background:
    radial-gradient(600px 420px at 22% 8%,  rgba(34,211,238,.13), transparent 60%),
    radial-gradient(700px 480px at 78% 18%, rgba(129,140,248,.11), transparent 60%),
    radial-gradient(520px 380px at 50% 92%, rgba(244,114,182,.05), transparent 60%);
  animation: drift 26s ease-in-out infinite alternate;
  filter: blur(40px);
}
@keyframes drift {
  from { transform: translate3d(0,0,0) scale(1); }
  to   { transform: translate3d(-3%, 2%, 0) scale(1.06); }
}

/* Layer 2: hairline grid, faded at edges */
body::after {
  content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background:
    linear-gradient(rgba(148,163,184,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148,163,184,.05) 1px, transparent 1px);
  background-size: 44px 44px;
  -webkit-mask-image: radial-gradient(ellipse 90% 60% at 50% 0%, #000 30%, transparent 75%);
          mask-image: radial-gradient(ellipse 90% 60% at 50% 0%, #000 30%, transparent 75%);
}
```

Plus a **grain overlay** div (`.grain`, one `<div class="grain">` in `base.html`) with an inline SVG feTurbulence data-URI at `opacity: .035; mix-blend-mode: overlay; position: fixed; inset: 0; z-index: -1; pointer-events: none;`. Grain kills the "flat gradient" look instantly. All of it is GPU-cheap and wrapped in `@media (prefers-reduced-motion: reduce) { body::before { animation: none; } }`.

### 3.2 Hero rebuild: badge pill + display type + live "terminal card"

Restructure the hero (index.html) as:

1. **Status pill** (not uppercase eyebrow): `● Benchmark oracle — live` — 12px pill, `--accent-soft` bg, 8px pulsing dot (`@keyframes pulse-dot { 50% { opacity:.4 } }`, 2s).
2. **H1 at 64px/-0.03em**: "Prove you're an AI, not a human." — gradient text on the single word **"AI"** only, using the 2-stop `--grad`. (Gradient-on-the-whole-headline reads template; one accented word reads intentional.)
3. **Lead** at 18px, then CTAs: primary "Start Challenge →" (arrow slides 3px right on hover via `.btn-primary:hover .arr { transform: translateX(3px) }`) + ghost "Read the docs".
4. **The product shot** — the big one. Below the CTAs, a terminal-style card showing a live puzzle transcript:

```
┌──────────────────────────────────────────────┐
│ ● ● ●   ai-captcha · tier: hard · ⏱ 07s      │
├──────────────────────────────────────────────┤
│ > Decode this ROT13 string:                  │
│   'uryyb jbeyq'                              │
│                                              │
│ > _                                          │  ← blinking caret
└──────────────────────────────────────────────┘
```

- Wrap it in an **animated conic gradient border** (the 2025 premium-card signature):

```css
.hero-shot { position: relative; border-radius: var(--radius-lg); padding: 1px; overflow: hidden; }
.hero-shot::before {
  content: ""; position: absolute; inset: -100%;
  background: conic-gradient(from 0deg, transparent 0 330deg, var(--accent) 345deg, var(--accent-2) 360deg);
  animation: spin 6s linear infinite;
}
@keyframes spin { to { transform: rotate(1turn); } }
.hero-shot > .terminal { position: relative; border-radius: 15px; background: #080b12; }
```

- Add a cyan glow behind it: `.hero-shot { box-shadow: var(--glow-md); }` and a soft ellipse under it. Type the transcript lines in with a staggered `@keyframes type-in { from { opacity: 0; transform: translateY(6px); } }` (`animation-delay: .2/.5/.8s`). CSS-only; no JS needed.

### 3.3 Bento feature grid + hover spotlight

Convert the uniform 6-card grid to a **bento** (desktop `grid-template-columns: repeat(3, 1fr)`; make "Signed Verification" span 2 columns and carry a mini inline illustration — the JWT header/payload as tiny mono text). On mobile it collapses to 1 column automatically.

**Mouse-tracking spotlight** (Linear's signature hover) — ~6 lines of JS in `base.html`:

```js
document.addEventListener('pointermove', e => {
  for (const c of document.querySelectorAll('.feature, .card')) {
    const r = c.getBoundingClientRect();
    if (e.clientX > r.left - 60 && e.clientX < r.right + 60 &&
        e.clientY > r.top - 60 && e.clientY < r.bottom + 60) {
      c.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      c.style.setProperty('--my', (e.clientY - r.top) + 'px');
    }
  }
});
```

```css
.feature { position: relative; overflow: hidden; }
.feature::before {
  content: ""; position: absolute; inset: 0; opacity: 0; transition: opacity .3s;
  background: radial-gradient(240px circle at var(--mx) 50%, rgba(34,211,238,.08), transparent 65%);
  pointer-events: none;
}
.feature:hover::before { opacity: 1; }
```

**Icons:** replace bare emoji with **40px tiles** — `border-radius: 10px; background: var(--accent-soft); border: 1px solid rgba(34,211,238,.2); display: grid; place-items: center; font-size: 18px; margin-bottom: 14px;`. The container turns random emoji into a designed icon system.

### 3.4 Micro-interactions & motion polish

| Element | Change |
|---|---|
| Nav links | Underline grows from left: `background: linear-gradient(var(--accent), var(--accent)) bottom left / 0 2px no-repeat;` → `background-size: 100% 2px` on hover (replaces color-flicker) |
| Timer | Render as a **conic-gradient progress ring**: 44px circle, `background: conic-gradient(var(--accent) calc(var(--p)*1%), var(--surface-2) 0)`; `--p` set from JS each tick. Warn/danger swap the ring color to amber/red. Turns a text counter into the app's signature interactive moment |
| Feedback (✅/❌) | Spring-in: `@keyframes pop { from { transform: scale(.85); opacity: 0 } 60% { transform: scale(1.05) } to { transform: scale(1) } }` — `animation: pop .25s ease` |
| Result badges | Add glow: pass = `box-shadow: var(--glow-sm)` with green; fail = red variant. Add a subtle animated shine sweep across the "Verified Robot" badge (`::after` skewed white gradient, `animation: sweep 2.5s ease infinite`) |
| Stat cards | On results page, stagger entrance: `.stat { animation: rise .4s ease backwards } .stat:nth-child(2){animation-delay:.08s} …` |
| Scroll reveal | Sections fade-up once: `.reveal { opacity:0; transform: translateY(14px); transition: .5s ease } .reveal.in { opacity:1; transform:none }` + 3-line IntersectionObserver. Subtle — don't overdo |
| All of it | Wrapped in `@media (prefers-reduced-motion: reduce)` disable block |

### 3.5 Docs & challenge page polish (the "real product" details)

- **Docs ToC → sticky sidebar**: at ≥1024px, docs become `display: grid; grid-template-columns: 220px 1fr; gap: 48px`; ToC is `position: sticky; top: 88px`, 13px links, active section highlighted cyan (scroll-spy optional — even without it, sticky sidebar = instant docs-site feel).
- **Section headers**: add mono index prefixes (`01 · Quickstart`) in cyan above each H2 — cheap, very "technical brand."
- **Challenge page**: replace the floating disclaimer card with a **footer strip inside the main card**: 12px, `--text-faint`, top hairline, lock icon — "🔒 Timer is server-authoritative. Client display is cosmetic." Removes the odd second card.
- **Results page**: pass state gets a full-card treatment — radial green glow from the top edge of the card (`.card.pass-glow { background: radial-gradient(600px 200px at 50% 0%, rgba(52,211,153,.10), transparent 70%), var(--surface); }`), fail gets the red equivalent. The verification token block gets a label bar + copy button like code blocks.
- **Footer**: upgrade to 3-column (brand + tagline / links / "Built for the benchmark · MIT") with the gradient restricted to the logo tile; add `© 2026` line.

---

## 4. Implementation checklist (ordered by impact ÷ effort)

| # | Change | Files | Effort | Impact |
|---|---|---|---|---|
| 1 | New design tokens (palette, glow, radii) | `style.css` `:root` | 15 min | ⭐⭐⭐ |
| 2 | Ambient background (aurora + grid + grain) | `style.css`, `base.html` | 30 min | ⭐⭐⭐ |
| 3 | Hero rebuild + terminal card w/ conic border | `index.html`, `style.css` | 60–90 min | ⭐⭐⭐ |
| 4 | Button/card/nav component restyle + focus rings | `style.css` | 45 min | ⭐⭐ |
| 5 | Bento grid + spotlight + icon tiles | `index.html`, `style.css`, `base.html` (JS) | 45 min | ⭐⭐ |
| 6 | Timer progress ring + feedback pop | `challenge.html`, `style.css` | 30 min | ⭐⭐ |
| 7 | Docs sticky sidebar + mono section indexes | `docs.html`, `style.css` | 40 min | ⭐⭐ |
| 8 | Results pass/fail glow + stat stagger | `results.html`, `style.css` | 20 min | ⭐ |
| 9 | Code block chrome (dots, label, copy) | `index.html`, `docs.html`, `style.css` | 30 min | ⭐ |
| 10 | Footer + nav scrolled-border + active pill | `base.html`, `style.css` | 25 min | ⭐ |

**Suggested shipping order:** 1 → 2 → 4 (tokens + atmosphere + components ≈ 70% of the perceived upgrade for ~90 min), then hero (3), then the rest incrementally. Every item is independently shippable; nothing breaks the existing templates since `results.html`/`challenge.html` already reference classes that get restyled in CSS.

**Anti-scope guard:** do **not** add pink back to chrome, do not glow more than ~4 elements per page, do not animate more than 2 things at once above the fold, and keep every animation under `prefers-reduced-motion` protection.