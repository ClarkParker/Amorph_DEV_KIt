# Verification Log & Provenance

This kit was assembled from several generations of notes, some of them outdated or
contradictory. This file records **where each claim comes from** and **how it was
checked**. The standard:

- **[verified]** — confirmed against the official Cmajor source/docs. Citation given.
- **[field-tested]** — repeatedly observed in real Amorph plugins; not in the official spec.
- **[unverified]** — plausible but unconfirmed.

Reference checkout used for verification: `github.com/cmajor-lang/cmajor` (cloned
fresh). Line numbers below refer to that checkout and may drift across versions —
treat them as pointers, not guarantees.

---

## Contradictions found and resolved

### 1. Oversampling — "ignored by the host" vs. "works"

- **Old claim (superseded):** Amorph ignores `[[oversampling: N]]` and the
  `oversampleFactor` manifest key; the DSP always runs at host rate; oversampling
  must be done manually.
- **Resolution — [verified]:** Per-*node* oversampling is a real Cmajor language
  feature and works: `node core = MyProcessor * 4;` upsamples in and downsamples
  out with **sinc interpolation** by default (alias-free). `/ N` undersamples
  (`latch` in, `linear` out). Only scalar streams interpolate.
  - Source: `docs/Cmaj Language Guide.md`, the "Oversampling and undersampling
    processors" section (≈ lines 1621–1696): `node myOversampledNode = MyProcessor * 4;`,
    and the policy override syntax `connection [sinc] / [linear] / [latch] ...`.
  - The two superseded annotation/manifest mechanisms (`[[oversampling: N]]`,
    `oversampleFactor`) are **not** the supported method — the supported method is
    the `* N` graph node. If you tried only the annotation and saw no effect, that
    matches: it was never the right lever.
  - **[field-tested]** in a production reverb: the non-linear core is wrapped as
    `node core = AbyssifyReverbCore * 4;` and analysis (DFT) runs on a *separate*
    node at host rate — confirming both that `* N` works and that you keep
    rate-sensitive analysis off the oversampled node.
- See [`docs/06_OVERSAMPLING.md`](docs/06_OVERSAMPLING.md).

### 2. UI → DSP bridge mechanism

- **Old claim (superseded):** the UI accesses an injected
  `this.__amorph_paramController` and calls `pc.sendEventOrValue(...)` /
  `pc.addParameterListener(...)` on it; the element must avoid Shadow DOM, etc.
- **Resolution — [verified]:** The host loads the UI module and calls its
  **default export** with the connection: `const patchView = await
  viewModule.default(patchConnection);`. The connection object exposes the methods
  directly (see table below). There is no `__amorph_paramController`. The common
  pattern is `export default function createPatchView(pc) { ... return element; }`,
  with the element keeping the connection as a property (e.g. `el.pc = pc`).
  - Source: `javascript/cmaj_api/cmaj-patch-view.js` (`createPatchView`,
    `viewModule?.default(patchConnection)`); method names in
    `javascript/cmaj_api/cmaj-patch-connection.js`.

### 3. UI scaling — `transform: scale()` vs. CSS `zoom`

- **Old approach (superseded):** scale the chassis with
  `transform: translate(-50%,-50%) scale(s)`.
- **Resolution — [field-tested]:** Use CSS **`zoom`** instead. `zoom` scales the
  *layout box*, so `getBoundingClientRect()` is zoom-aware and `position: fixed`
  stays viewport-relative — eliminating the dual-coordinate math that `transform`
  forces. `transform: scale()` only scales painting, which causes overlay
  misplacement, host-wrapper scrollbars, and subpixel blur.
  - Not part of the official Cmajor spec; this is a host-behaviour lesson. See
    [`docs/07_SCALING.md`](docs/07_SCALING.md) for the full method including the
    host-wrapper scrollbar fix and the transparent-background fix.

---

## Bridge API — verified method surface

All confirmed in `javascript/cmaj_api/cmaj-patch-connection.js`. **[verified]**

| Call | Purpose |
|---|---|
| `sendEventOrValue(endpointID, value, rampFrames?, timeoutMillisecs?)` | UI → DSP: set a parameter (optional ramp) |
| `addParameterListener(endpointID, fn)` | DSP → UI: parameter changed (automation/preset) |
| `requestParameterValue(endpointID)` | ask for the current value (call **after** adding the listener) |
| `removeParameterListener(endpointID, fn)` | detach |
| `addAllParameterListener(fn)` / `removeAllParameterListener(fn)` | listen to every parameter |
| `addEndpointListener(endpointID, fn, granularity?, sendFullAudioData?)` | DSP output events: meters, scopes, spectra |
| `removeEndpointListener(endpointID, fn)` | detach |
| `sendMIDIInputEvent(endpointID, shortMIDICode)` | play notes (instruments) — wraps `sendEventOrValue` with `{ message }` |
| `sendParameterGestureStart(endpointID)` / `sendParameterGestureEnd(endpointID)` | automation gesture grouping |
| `requestStoredStateValue(key)` / `sendStoredStateValue(key, value)` | UI-only persisted state (round-trips with the host project) |
| `addStoredStateValueListener(fn)` / `removeStoredStateValueListener(fn)` | listen for stored-state changes |
| `clearAllStoredStateValues()` | clear stored UI state |
| `sendFullStoredState(state)` / `requestFullStoredState(cb)` | full state snapshot |
| `getResourceAddress(path)` | resolve a patch resource URL |

MIDI short codes (helper-free): note-on `0x900000 | (note << 8) | velocity`,
note-off `0x800000 | (note << 8) | velocity`.

---

## Cmajor language facts — verified

From `docs/Cmaj Language Guide.md` unless noted. **[verified]**

- `processor.frequency` and `processor.period` give sample rate / seconds-per-sample.
- Per-node oversampling/undersampling with `* N` / `/ N` (see contradiction #1).
- Interpolation policies `[sinc]`, `[linear]`, `[latch]` overridable per connection.
- Only scalar streams interpolate across an oversampled boundary (a compile error
  otherwise). *Note:* a `float<2>` stereo stream across `* N` is **[field-tested]**
  as working in practice — confirm in your toolchain if you depend on it.

---

## Source inventory

| Source document | Status | Notes |
|---|---|---|
| Official `cmajor-lang/cmajor` repo (docs + `cmaj_api`) | **authoritative** | Ground truth for language + bridge. |
| `cmajor-amorph-framework` notes | current, mostly correct | Right bridge contract; right oversampling. Folded in. |
| `CMAJOR_OVERSAMPLING_GUIDE` | correct | Matches the official guide. Version/date stamps removed as project-specific. |
| `Cmajor_Plugin_Dev_Toolkit` | mixed | Good DSP/GUI reference + Airwindows pointer; some German; de-duplicated. |
| `AmorphPluginFramework.docx` | **outdated** | Wrong `__amorph_paramController`; wrong "oversampling ignored". Superseded above; kept only where still accurate (Airwindows porting rules, template-literal escaping, pan law). |
| `SCALING_BRIEF_V2` | field-tested | Source for `docs/07_SCALING.md`. Project names generalised. |
| `WebAudioPlugin_UI_Design.docx` | aspirational | Procedural-UI research. **Caveat:** several techniques (three.js, React, Houdini paint *worklets as separate modules*, `AudioWorkletNode`) conflict with Amorph's single-file/no-import rule and bridge model. Captured with compatibility flags in `docs/08_UI_RENDERING.md`. |

Project-specific material (a real reverb plugin's full DSP/UI, `(c)` notices,
internal version stamps, plugin names) was used only to *extract anonymised,
reusable patterns* and is **not** included in this public kit.

---

## Open questions / still unverified

- Exact sinc-resampling **latency** introduced by `* N` (FIR kernel length) — not
  specified in the docs. Report `processor.latency` if you need a number.
- Whether `float<2>` across an oversampled node is guaranteed by the spec or an
  implementation detail (see above).
- Amorph's `getScaleFactorLimits()` support — observed unreliable; manual `zoom`
  scaling is the working path. Re-check per Amorph version.

Found something wrong or newly true? Update this file in the same PR as the fix.
