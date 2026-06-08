# 07 · UI Scaling (CSS `zoom`) and Host-Wrapper Fixes

**Status: [field-tested]** — distilled from a real refactor of a production Cmajor
plugin UI. Not part of the official Cmajor spec; this is host-behaviour knowledge.

## Two legitimate approaches — pick one

Amorph supports two UI layout philosophies; they are mutually exclusive per plugin:

1. **Fluid layout (the official prompt default).** `:host { width:100%; height:100%;
   overflow:hidden }`, internal layout in `%`/`fr`/`flex`/`grid`, **no fixed px on
   the host**, window declared via `// WINDOW SIZE: WxH` on line 2 and
   `view.resizable`. Best when the design naturally reflows.
2. **Fixed chassis + CSS `zoom` (this chapter).** Compose on a fixed pixel grid and
   scale the whole chassis with `zoom`. Best for skeuomorphic, pixel-exact designs
   where knobs sit on a raster. A real shipped reverb uses exactly this
   (`chassis.style.zoom = s`).

The rest of this chapter documents approach 2. If you go fluid, follow the official
UI prompt instead ([`../ai/amorph_official/UI_common.md`](../ai/amorph_official/UI_common.md),
section A.13).

## The design-grid premise

A plugin UI is typically composed on a **fixed pixel grid** (e.g. 800×400 or
1200×640). Knobs sit on a raster; module widths and label typography are exactly
tuned. This is **not** responsive layout and should not be rebuilt as fluid
(`rem`/`%`/`clamp`) layout — that would destroy the skeuomorphic, pixel-exact design.
Instead, keep the fixed chassis and **scale the whole thing** to fit the window.

## Use CSS `zoom`, not `transform: scale()`

`zoom` is Baseline (Chrome, Safari, Firefox 126+); all of Amorph's WebViews support
it, no polyfill needed. The crucial difference:

| | `transform: scale()` | `zoom` |
|---|---|---|
| Scales the **layout box** | no (paint only) | **yes** |
| `getBoundingClientRect()` | viewport px *after* scale (needs `/ scale` math) | **zoom-aware**, directly usable |
| `position: fixed` | becomes ancestor-relative | **stays viewport-relative** |
| Subpixel blur on hairlines | yes at fractional scales | mitigated by rastering the scale |

`transform: scale()` only scales painting, which forces a dual coordinate system
(see [`05_AMORPH_NOTES.md`](05_AMORPH_NOTES.md)), causes host-wrapper scrollbars, and
blurs hairline borders.

> Caveat: `offsetWidth`/`offsetHeight`/`clientWidth`/`clientHeight` do **not**
> include zoom. If you use them, reconcile with `Element.currentCSSZoom`. Most code
> uses `getBoundingClientRect()` (zoom-aware), so this rarely bites.

## CSS

```css
/* Host element fills the WebView and centres the chassis */
plugin-ui {
  display: flex; justify-content: center; align-items: center;
  width: 100%; height: 100vh;
  min-width: 0; min-height: 0; overflow: hidden;
  background: transparent;          /* see host-wrapper §, avoids a visible box */
}

/* Fixed design grid; scaled via zoom in JS */
plugin-ui .chassis {
  width: 1200px; height: 640px;     /* keep in sync with view.width/height */
  flex-shrink: 0; flex-grow: 0;
  position: relative;               /* NOT absolute; no transform/top/left here */
  overflow: hidden;
  /* + your background, border, shadow */
}
```

Watch for **duplicate `position` declarations** in the `.chassis` rule — older code
often had both `position: relative` and a later `position: absolute` (the later
wins). Consolidate to a single `position: relative`.

## `_doResize`

```javascript
_doResize() {
  const ch = this.querySelector('.chassis');
  if (!ch) return;
  // fit-to-window, clamped so it never gets unreadably small or absurdly large
  let s = Math.min(window.innerWidth / 1200, window.innerHeight / 640);
  s = Math.max(0.5, Math.min(2.0, s));
  s = Math.round(s * 20) / 20;        // raster to 0.05 steps -> avoids subpixel blur
  ch.style.zoom = s;
  ch.style.transform = '';            // defensive: clear any stale transform on reload
  this._chassisScale = s;             // keep for any code path that reads it
}
```

Wire it once and clean it up:

```javascript
connectedCallback() {
  // ...
  this._chassisScale = 1;
  this._resizeFn = () => this._doResize();
  window.addEventListener('resize', this._resizeFn);
  setTimeout(() => this._doResize(), 0);            // first frame
  if (typeof ResizeObserver !== 'undefined') {
    this._ro = new ResizeObserver(() => this._doResize());
    this._ro.observe(this);                          // observe the host element
  }
}
disconnectedCallback() {
  window.removeEventListener('resize', this._resizeFn);
  this._ro?.disconnect();
  // + cancel any RAF/timers
}
```

> Variant: some implementations observe `this.parentElement` (the host's holder) and
> schedule the resize through `requestAnimationFrame`. Both work; the key points are
> a synchronous first resize and full cleanup.

## Overlay coordinate math under `zoom`

Under `transform`, overlay/popover code had to divide by the scale:
```javascript
const cr = chassis.getBoundingClientRect();
const scale = cr.width / 1200;
const x = (anchorRect.left - cr.left) / scale;   // the pain
```
Under `zoom`, `getBoundingClientRect()` is zoom-aware, so it reduces to direct
subtraction:
```javascript
const cr = chassis.getBoundingClientRect();
const x = anchorRect.left - cr.left;             // chassis-internal CSS px
const y = anchorRect.top  - cr.top;
```
Do this as a **separate follow-up pass**, not in the same change as the zoom switch —
the old `/ scale` math keeps working as a no-op division under zoom (`cr.width/1200 ≈
1.0`), so the switch itself is low-risk and the cleanup can come later.

## Host-wrapper cleanup (two real fixes)

### Scrollbars in host wrappers

Amorph inserts wrapper DIVs (with `overflow: auto`) between `body` and your element.
Fix in two parts:

```css
/* Unscoped — must reach host wrappers outside your element's scope */
::-webkit-scrollbar { width: 0 !important; height: 0 !important; display: none !important; }
* { scrollbar-width: none; }
```
```javascript
// In connectedCallback: walk up to body, force overflow hidden on every wrapper
let p = this.parentElement;
while (p && p !== document.body) {
  p.style.overflow = 'hidden';
  p.style.margin = '0';
  p.style.padding = '0';
  p = p.parentElement;
}
```
You need **both**: CSS alone misses wrappers re-rendered by the host; the JS walk-up
alone can be undone by a re-render. (Anti-patterns that *don't* work:
`scrollbar-width: none` only on `body`; `html, body { overflow: hidden }` alone.)

### Visible background box at off-aspect sizes

With an aspect-locked chassis, an off-aspect window leaves unused area around it. If
your host element has its own dark `background`, that area shows as a box. Fix:

```css
plugin-ui { background: transparent; }   /* not #000 — black is still a visible box */
```
The DAW background shows through and the unused area becomes invisible. Note: with a
transparent background, the chassis `box-shadow` becomes more visible on light DAW
themes — tune it if needed.

## Test checklist after a scaling change

1. Default size: chassis centred, no scrollbars.
2. Shrink horizontally / vertically: chassis scales proportionally, stays centred.
3. Enlarge: chassis grows but not past the clamp.
4. Open overlays/popovers: they sit on the right anchors at every scale.
5. Drag a knob: hit-detection works across all scales.
6. Text sharp at default size.
7. Off-aspect window (e.g. 1300×950): no visible box around the chassis, no
   scrollbars.
