# 🧠 NOUS — Design System (use these exact values everywhere)

Calm, light, Percept-style. White cards on soft mint. Big rounded corners,
soft shadows, pill buttons. **Never use pure black or pure gray** — everything
tints toward teal.

## 1. Color tokens (copy this CSS block verbatim)

```css
:root{
  /* base */
  --bg:#edf4f2;        /* page background — soft mint */
  --card:#ffffff;      /* all cards/panels */
  --line:#dbe8e4;      /* borders/dividers */
  --ink:#16342f;       /* headings — dark teal, NOT black */
  --body:#42605a;      /* body text */
  --mut:#7b938d;       /* secondary text */
  --faint:#a9bcb7;     /* placeholders/disabled */
  /* brand */
  --sage:#5ea99d;      /* accent — links, highlights, brain nodes */
  --sage-soft:#9ccac1; /* primary pill button fill */
  --sage-bg:#dcedea;   /* tinted chip/backgrounds */
  --deep:#17433c;      /* dark buttons + emphasis */
  /* semantic states — each = text color + bg + border */
  --amber:#b7791f;  --amber-bg:#fdf3df;  --amber-line:#ecd9ae;  /* PROMISE */
  --red:#b54a40;    --red-bg:#fdecea;    --red-line:#f0c9c4;    /* REFUSAL */
  --purple:#6d55c8; --purple-bg:#f1edfd; --purple-line:#d9d0f5; /* LEARNING */
  --green:#2e7d5b;  --green-bg:#e7f5ee;  --green-line:#c4e5d4;  /* DONE/KEPT */
}
```

Rule: a state card ALWAYS uses its trio together (bg + line as border + color
for the kicker text). Don't mix trios.

## 2. Typography

- Font: system stack — `-apple-system, "Segoe UI", Inter, sans-serif`
- Hero H1: 64px / weight 800 / letter-spacing −2.5px / line-height 1.04.
  One key word colored `var(--sage)`.
- Section H2: 34px / 800 / −1.2px, centered, with an EYEBROW above it:
  12px, uppercase, letter-spacing 2.2px, weight 800, color `var(--sage)`
- Panel titles: 11.5px UPPERCASE, letter-spacing 1.8px, 800, color `var(--mut)`
- Card "kicker" labels: 10.5px UPPERCASE, spacing 1.8px, 850, state color
- Body: 15px / 1.55 · card text 13–14px · log/monospace: `ui-monospace, Menlo` 11.6px `#849993`

## 3. Buttons (exact CSS)

```css
/* pill base — ALL buttons are pills or 13–16px radius rounds */
.pill{border-radius:999px;padding:12px 24px;font-size:14.5px;font-weight:700;
  cursor:pointer;border:1px solid transparent;transition:.18s;}
.pill.sage {background:#9ccac1;color:#17433c;}          /* primary CTA */
.pill.dark {background:#17433c;color:#eaf5f2;}          /* strong action */
.pill.ghost{background:#fff;color:#16342f;border-color:#dbe8e4;} /* secondary */
/* hover: translateY(-1px) + slight brighten. Never underline. */

/* in-card action buttons */
.btn-book{background:linear-gradient(160deg,#e8a33d,#cf8a1f);color:#fff;
  border:none;border-radius:13px;padding:13px;font-weight:800;width:100%;
  box-shadow:0 8px 20px rgba(183,121,31,.25);}          /* amber = promise CTA */
.btn-approve{background:#17433c;color:#eaf5f2;border:none;border-radius:11px;
  padding:10px;font-weight:800;width:100%;}             /* deep = arm/approve */
```

Button meanings — keep consistent: **sage pill** = navigation/primary CTA ·
**dark pill/deep** = commit an action (approve, open graph) · **amber
gradient** = the Book-It promise moment only · **ghost** = secondary.

## 4. Surfaces

- Cards/panels: `background:#fff; border:1px solid var(--line);
  border-radius:24px; box-shadow:0 10px 30px rgba(23,67,60,.06); padding:18px`
- Hero feature card: radius **34px**, shadow `0 30px 70px rgba(23,67,60,.13)`
- Small items inside panels: radius 15px, bg `#fbfdfc`
- Inputs: bg `#f4faf8`, 2px border `var(--line)`, radius 16px, 17px text;
  focus → border `var(--sage)` + `box-shadow:0 0 0 5px rgba(94,169,157,.13)`
- Status chips: pill, 9.5px UPPERCASE 850;
  BOOKED/ARMED → green trio · PROPOSED/PENDING → amber trio · neutral → sage-bg
- Radial page glow (top of body): two soft radial-gradients of
  `rgba(94,169,157,.10–.14)` — never flat background

## 5. Motion

- Cards enter: `pop .4s cubic-bezier(.2,.9,.3,1)` (fade + 12px rise + scale .98→1)
- List items: `slide .3s` (fade + 8px drop)
- Hover on buttons: `translateY(-1px)`, 150–180ms
- The brain: nodes pulse on sin waves; teal signals travel edges; fires harder
  on activity (call `window.excite()` on any state change)

## 6. Voice (microcopy)

Calm, first-person-ish, warm. "I won't let this one slip." · "Nous never runs
a protocol you haven't approved." · "quiet so far — tell Nous something".
Emojis only as card icons: 🤝 ✋ 🧠 ⚡ 📌 📅 — never in body text.

**Reference implementation: `frontend/index.html` on main — when unsure, copy
from it.**
