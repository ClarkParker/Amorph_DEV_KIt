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
- See [`docs/06_OVERSAMPLING.md`](docs/06_OVERSAMPLING.md). Re-confirmed by the
  official Amorph IDE prompts ("Per-node oversampling: `node x = MyProc * 4;`").

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

### 4. Plugin-type I/O — default templates vs. tested capability

- **Official Amorph IDE prompts say:** FX has "no MIDI"; MIDI Instrument is "pure
  MIDI, NO `output stream`"; none mention a sidechain.
- **Resolution — [tested by maintainer]:** the prompts describe minimal *default
  templates*, not host limits. Tested reality:
  - **Audio FX has MIDI in** (input only — no MIDI out).
  - **MIDI Instrument can also output audio** (not pure-MIDI-only).
  - **All three types have a sidechain input** (`scIn`).
  The prompt text simply lags behind the host. Authoritative matrix:
  [`docs/10_PLUGIN_TYPES.md`](docs/10_PLUGIN_TYPES.md).

### 5. UI parameter-listener payload

- **Resolution — [verified-official]:** Amorph's `addAllParameterListener` fires with
  **one object** `{ endpointID, value }` (not two args). The per-parameter
  `addParameterListener(endpointID, fn)` also works and is used in a real shipped
  plugin — both are valid; pick one. Documented in
  [`docs/03_UI_WEBCOMPONENT.md`](docs/03_UI_WEBCOMPONENT.md).

### 6. Two legitimate UI scaling philosophies

- The official prompt's default UI layout is **fluid** (`:host` 100%/100%, %/fr/
  flex/grid, no fixed px). A real pixel-perfect plugin instead uses a **fixed chassis
  scaled with CSS `zoom`** (confirmed: the reverb UI sets `chassis.style.zoom`). Both
  are legitimate; choose fluid for responsive layouts, zoom-on-fixed-chassis for
  skeuomorphic pixel-exact designs. See [`docs/07_SCALING.md`](docs/07_SCALING.md).

---

## Official Amorph IDE prompts — captured & verified

Amorph's IDE emits a per-variant system prompt for AI codegen. Captured verbatim in
[`ai/amorph_official/`](ai/amorph_official/). They are the most authoritative source
for Cmajor-in-Amorph correctness. Facts established there (**[verified-official]**):

- **Cmajor stdlib:** `std::random::RNG` is a *struct field*, not a function
  (`std::random(lo,hi)` does **not** exist); `std::notes::noteToFrequency` returns
  **float32**; `std::oscillators::waveshape(float32)::sine/square/triangle/
  sawtoothUp/polyblep_*`; `std::noise::White/Brown/Pink`;
  `std::frequency::realOnlyForwardFFT()` works (real bins `[0..N/2]`, imaginary
  `[N/2+1..N-1]`); `std::midi::createMessage(status,d1,d2)`.
- **MIDI message methods:** `isNoteOn/isNoteOff/getNoteNumber/getVelocity/
  getFloatVelocity/isController/isControllerNumber/getControllerValue/
  getChannel0to15/isPitchWheel`.
- **Processor properties:** `processor.id` (stable int32 per instance),
  `processor.session` (changes per run).
- **Array rule:** fixed compile-time sizes only — no unsized `float[]`, no
  `.wrap(size)`, no `.size`. Index with `.at(i)`.
- **No prefix `++`/`--`** (use `x += 1`). *Caveat:* the prompts' own `for` headers use
  `++i`, which evidently compiles; the stated rule is the safe default.
- **Custom parameter names work** (`paramSnap`, etc.) — `param1..paramN` is the
  recommended convention, not a binding requirement. ("Custom names break binding" is
  **false**.)
- **Spectrum pattern:** namespace-wrapped `struct { float[512] bins; }`, emit at
  ~30 Hz (`0.033 s`) via `output event`. In the Amorph host, `addEndpointListener`
  receives these directly — the prompts' "PluginProcessor.cpp must handle it" note
  applies only to a standalone JUCE export.
- **UI host bridges:** `window.__amorphProcessMidi` (in) /
  `window.__amorphProcessMidiOut` (out, MIDI Instrument only), batched ~60 Hz;
  `sendMIDIInputEvent("midiIn", (status<<16)|(d1<<8)|d2)` (note `sendMIDI` does not
  exist); light DOM only (no `attachShadow`); `// WINDOW SIZE: WxH` on line 2;
  `data-endpoint-id="paramN"` enables the IDE's right-click AI context.

---

## Compiler verification (cmaj 1.0.3159, Linux x64)

A full audit pass was run against the **real Cmajor compiler** (release binary
1.0.3159, `cmaj generate --target=cpp`). Tag: **[compiler-verified]**.

**Everything in the kit compiles:**

| Artifact | Result |
|---|---|
| `examples/01_SaturatorFX` (incl. the `* 4` oversampled graph + `float<2>` streams across the node) | ✓ clean |
| `examples/02_PolySynth` | ✓ clean (after switching `voices[i]` → `voices.at(i)`; `int` indexing compiled but emitted per-access range-check performance warnings) |
| `examples/03_MidiChord` | ✓ clean |
| `tools/new_plugin.py` scaffold output, all three types (fx / instrument / midi) | ✓ clean |
| All UI `.js` files | ✓ valid ES modules (`node --check`, Node 22) |

**Language probes (claims tested directly):**

| Claim | Verdict |
|---|---|
| `double` does not exist | ✓ compile error (`'double' is not a type name in Cmaj — did you mean float64?`) |
| `input`/`output`/`stream` as identifier names | ✓ compile error |
| prefix `++i` in a `for` header | compiles — the no-`++` rule is style, not a compiler rule |
| custom parameter names (`paramFancyName`) | ✓ compile + bindable (prompt claim confirmed) |
| `std::random::RNG` as a processor field | ✓ compiles |
| `lerp`, `processor.id`, `processor.session`, `std::oscillators::waveshape::sine`, `wrap<N>` | ✓ all compile |
| `float<2>` streams across a `* 4` oversampled node | ✓ compiles (upgraded from [field-tested]) |

**Official-prompt inaccuracies found by the probes** (guardrails stated as hard
rules that the compiler does not actually enforce):

1. **Unsized `float[]` compiles** — it is a *slice* type, and even `.at(0) = x` on an
   empty slice compiles. It is still a real bug to use one as a buffer (it's an empty
   view), so the linter keeps flagging it — now as a **warning** with an accurate
   message, not a compile-error claim.
2. **`.size` works** — `float[16] buf; buf.size` compiles fine. The prompt's "NO
   `.size` property" is wrong; the lint rule was removed.
3. **`select()` requires vector arguments** — scalar `select(true, a, b)` is a
   compile error. The prompt's cheatsheet does not mention the restriction.

### Reproducing the compile check (headless CI)

The release `cmaj` binary links WebKitGTK/JACK for its GUI/audio features, which
plain CI containers lack. The compile path never calls them, so stubs suffice:

```bash
curl -sLO https://github.com/cmajor-lang/cmajor/releases/download/1.0.3159/cmajor.linux.x64.zip
unzip -q cmajor.linux.x64.zip -d cmaj-bin
apt-get install -y libsoup2.4-1 libjack-jackd2-0
# stub the webkit sonames (34 symbols, never called during `cmaj generate`):
readelf --dyn-syms -W cmaj-bin/linux/x64/cmaj | awk '$7=="UND"{print $8}' \
  | grep -E '^(webkit_|jsc_|soup_)' | sort -u \
  | sed 's/.*/void* &(void){return 0;}/' > stub.c
gcc -shared -fPIC -o /usr/lib/x86_64-linux-gnu/libwebkit2gtk-4.0.so.37 stub.c
gcc -shared -fPIC -o /usr/lib/x86_64-linux-gnu/libjavascriptcoregtk-4.0.so.18 stub.c
cmaj-bin/linux/x64/cmaj generate --target=cpp --output=/dev/null path/to/My.cmajorpatch
```

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
| Official Amorph IDE prompts (per variant) | **authoritative (host)** | Ground truth for Cmajor-in-Amorph. Captured verbatim in `ai/amorph_official/`. A few host-capability lines are outdated (see contradiction #4). |
| Official `cmajor-lang/cmajor` repo (docs + `cmaj_api`) | **authoritative (language)** | Ground truth for language + bridge. |
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
- ~~Exact sidechain endpoint name/requirement~~ — **resolved [verified]**: names are
  free; each audio input `stream` is a bus; the first (index 0) is the implicit main,
  the rest are sidechains, in declaration order; channels = vector width
  (`float`=mono, `float<2>`=stereo). No hard max on sidechain buses in the wrapper
  (the DAW decides). Source: `modules/plugin/include/clap/cmaj_CLAPPlugin.h`
  (`updateAudioPortInfoCachesFromLoadedPatch`, `index == 0 ? CLAP_AUDIO_PORT_IS_MAIN`).
  See [`docs/10_PLUGIN_TYPES.md`](docs/10_PLUGIN_TYPES.md).
- Whether MIDI on an FX is in-only at the host level or just by convention (tested:
  in works; out not tested on FX).

Found something wrong or newly true? Update this file in the same PR as the fix.
