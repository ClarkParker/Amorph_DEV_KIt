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

## Running a TTS / heavy engine "inside" the plugin (LALAFY Session 29 — verified + open)

The Cmajor **DSP is real-time-pure** — it cannot run JS, WASM, neural inference, or an
external engine. Anything like that must live in the **JS view** (Amorph WebView) or a
Cmajor **patch worker** (`--worker=webview|quickjs`), and feed the DSP.

- **Verified:** `cmaj generate --target=javascript` compiles a patch's DSP to a JS/WASM
  class (so JS *could* host the DSP outside a plugin host — not applicable inside Amorph,
  where Amorph is the host and the DSP is the audio engine).
- **Verified (build quirk):** `cmaj render --input=*.mid` exited 1 in cmaj 1.0.3159 (CLI
  limitation, reproduced on a baseline patch — not a patch bug). Verify MIDI in the host.
- **Verified (sandbox network):** the dev container's egress allowlist **blocks
  huggingface.co**; GitHub is allowed. Fetch model/WASM assets from GitHub mirrors.
- **OPEN — verify before building** a "view generates audio → DSP plays it" design:
  1. Does **WASM** run in Amorph's WebView (WKWebView/WebView2/webkit2gtk)? (Very likely;
     embed the .wasm in the single-file UI like other assets — Amorph has no web access.)
  2. **View→DSP transfer of a multi-second audio buffer** (~1 MB of floats): the view API
     in `03_UI_WEBCOMPONENT.md` is `pc.sendEventOrValue` (params/small events). For a big
     buffer you need a Cmajor `external`/array endpoint the view can write — confirm Amorph
     supports writing it at runtime. If not: render the audio offline and feed the plugin's
     **audio input** (vocoder/Reuse path) instead.
