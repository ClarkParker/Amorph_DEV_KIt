# 09 · Pitfalls & Checklists

Quick lookup when something doesn't work, plus a pre-flight and a test checklist.

## DSP pitfalls (Cmajor)

| Symptom | Cause | Fix |
|---|---|---|
| Silent output | missing `advance()` or `out <-` | write both, every loop iteration, unconditionally |
| `Forbidden identifier 'output'` | reserved name used | rename (`output_`, `outSignal`) |
| `Unknown type 'double'` | C++ type | use `float64` |
| Compile error on a helper | function defined inside `main()`/`event` | move to processor scope |
| Goes silent after ~30 s | denormals in feedback path | add a tiny anti-denormal floor |
| Noise when turning a knob | NaN from `log(0)`/`sqrt(-x)`/divide-by-0 | clamp input: `max(x, 1e-10f)` |
| Filter explodes | cutoff above Nyquist | clamp to `sr * 0.45f` |
| Aliasing / harsh highs on distortion | non-linear stage at host rate | oversample the core (`* N`) |
| Wrong pitch/time after sample-rate change | hardcoded 48000 | use `processor.frequency`/`period` |
| Preset recalls wrong values | a parameter was renumbered/reused | never renumber; append new params |

## UI pitfalls (Web Component)

| Symptom | Cause | Fix |
|---|---|---|
| UI never appears | no/!wrong default export | `export default fn(pc)` returning the element |
| Controls show stale defaults | no `requestParameterValue` after listener | call it after every `addParameterListener` |
| Knob jitters while dragging | DSP echo fights the drag | echo-loop protection (ring buffer) |
| Overlays mispositioned | scaling with `transform: scale()` | use CSS `zoom` (`07_SCALING.md`) |
| Scrollbars at the plugin edge | host wrapper `overflow:auto` | scrollbar suppression + JS walk-up |
| Dark box around the chassis | opaque host-element background | `background: transparent` |
| Whole UI crashes (syntax error) | unescaped backtick / backslash in a template literal | escape `` \` `` and double `\\` |
| Sluggish UI | CSS animations running on hidden elements | pause with `animation-play-state` |
| Leak/double-register on reload | no cleanup / unguarded define | tear down in `disconnectedCallback`; guard `customElements.define` |
| Drag breaks when cursor leaves element | mouse events | pointer events + `setPointerCapture` |
| Blank where a library should be | tried to `import`/CDN | inline everything; single file only |

## Pre-flight checklist (before coding)

- [ ] Plugin type decided: effect (`isInstrument: false`) or instrument (`true`).
- [ ] **Full parameter list fixed** with numbers `param1..paramN` — this is the
      contract; do it before the UI.
- [ ] For each parameter: type (`event`/`value`), `min`/`max`/`init`/`unit`,
      and whether it's a toggle/enum (`step`/`text`).
- [ ] Which stages are non-linear → which need oversampling.
- [ ] Meters/scopes needed → which `output event` endpoints.
- [ ] Design size chosen (chassis px) and mirrored in `view.width`/`height`.

## DSP checklist

- [ ] One top-level `processor`/`graph`; `[[ main ]]` if multiple nodes.
- [ ] No reserved identifiers (`input`/`output`/`stream`) as names.
- [ ] No `double`/`unsigned`/`size_t`/`constexpr`/`static`; `float64` for precision.
- [ ] `float(...)` casts on all `sin`/`cos`/`pow`/`exp`/`sqrt`/`tanh` results.
- [ ] Every parameter: endpoint → state var → `event` handler.
- [ ] `out <-` and `advance()` every loop iteration, unconditionally.
- [ ] Sample rate from `processor.frequency`/`period`; all time scaled by `dt`.
- [ ] All float state initialised; cutoffs clamped `< sr*0.45`; feedback `< 1.0`.
- [ ] Non-linear core oversampled (`* N`); analysis nodes kept at host rate.
- [ ] Bypass parameter short-circuits the loop.

## UI checklist

- [ ] One self-contained `.js` file — no `import`/`require`/CDN/external libs.
- [ ] `export default function createPatchView(pc)` returns the element; guarded
      `customElements.define`.
- [ ] Two-way bind every control with echo-loop protection.
- [ ] `requestParameterValue` after every `addParameterListener`.
- [ ] Scale with CSS `zoom` on a fixed chassis; clamp + 0.05 raster.
- [ ] Host-wrapper scrollbar suppression + transparent background.
- [ ] No `vw`/`vh` for critical sizing; no `backdrop-filter`.
- [ ] Pointer events + `setPointerCapture` for drags.
- [ ] CSS animations paused when hidden; RAF loops only while visible.
- [ ] Everything torn down in `disconnectedCallback`.
- [ ] Template literals: backticks escaped, backslashes doubled.

## Test checklist

- [ ] Load: all parameters at correct defaults; knobs move the sound; meters react.
- [ ] Automate each parameter from the host: UI reflects it (no jitter).
- [ ] Bypass on/off: no level jump, no silence on reload.
- [ ] A/B against the reference (original plugin or formula).
- [ ] Pink-noise unity check: no unexpected gain difference between modes.
- [ ] Resize the window: layout holds, centred, no scrollbars, no box, text sharp.
- [ ] Open/close overlays: correct positions, no animation lag afterwards.
- [ ] Reload the plugin in the DAW: no leaks, no double-registration.
