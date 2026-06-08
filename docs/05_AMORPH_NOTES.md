# 05 · Amorph-Specific Notes

Amorph is a Cmajor-based host that renders the UI in an embedded WebView. Its
behaviour is **not** identical to vanilla Cmajor tooling. These are non-obvious
behaviours discovered through testing — violating them causes rendering bugs that
are hard to diagnose. Status: **[field-tested]** unless noted.

## No general web access

Amorph runs without general web access. The reliable way to bring in external
material is `git clone`. Consequence: your UI must be fully self-contained (the
single-file, no-import rule) and depend on nothing external — no CDN, no web fonts,
no runtime fetches.

## `position: fixed` inside a CSS transform

If any ancestor has a CSS `transform`, `position: fixed` children use that
transformed ancestor as their containing block — **not the viewport**. Overlays then
land in the wrong place. This is the main reason to scale with `zoom` rather than
`transform` (see [`07_SCALING.md`](07_SCALING.md)). If you must keep a transform,
append overlays to the chassis and use `position: absolute; inset: 0` on a chassis
that is `position: relative`.

## `vw` / `vh` units are unreliable

`vw`/`vh` do not reliably reference the plugin window in Amorph — they may resolve
against a smaller sub-context. Don't use them for critical sizing. Use `%` or `px`
against a known container size.

## `backdrop-filter` is unsupported

`backdrop-filter` glitches in Amorph's WebView. Don't use it for blurs or
frosted-glass effects.

## Oversampling — use the language feature, not the annotation

`[[oversampling: N]]` in source and `oversampleFactor` in the manifest are **not**
the mechanism. The working method is per-node oversampling in Cmajor:
`node core = MyCore * 4;`. This is **[verified]** against the Cmajor Language Guide.
Full details: [`06_OVERSAMPLING.md`](06_OVERSAMPLING.md).

## Template-literal backslash escaping

Inside a JS template literal (backtick string), backslashes are escape sequences:
`\n` → newline, `\\` → one backslash, `\_` → underscore (backslash dropped),
`` \` `` → backtick. If your content contains literal backslashes (e.g. ASCII art),
write each as `\\`. A stray unescaped backtick terminates the template literal and
crashes the whole UI with a syntax error.

## Pause CSS animations when hidden

CSS keyframe animations keep running on `opacity: 0` elements, burning GPU. Pause
them when a container is hidden:

```css
#overlay:not(.visible) * { animation-play-state: paused !important; }
```

## Overlays

Append overlays to the chassis (not `document.body`), give the chassis
`position: relative`, and use `position: absolute; inset: 0; z-index: 9999`. Show/hide
with `opacity` + `pointer-events`, not `display: none`, so CSS transitions run.

## localStorage

`localStorage` works in Amorph's WebView on macOS and Windows for **UI-only** state
(e.g. which tab is open). Never use it for anything that must round-trip through the
DAW preset system — that goes through parameters or `sendStoredStateValue`.

## Host-wrapper scrollbars and background

Amorph inserts wrapper DIVs between `body` and your custom element; some have
`overflow: auto` and show scrollbars when the window isn't exactly the design size.
And your element's own background can show as a visible box around the chassis at
off-aspect window sizes. Both have concrete fixes in [`07_SCALING.md`](07_SCALING.md)
(§ host-wrapper cleanup).

## `getScaleFactorLimits()` is unreliable in Amorph

The official Cmajor `getScaleFactorLimits()` view API is not reliably respected in
Amorph; manual `zoom` scaling is the working path. Re-check per Amorph version.
