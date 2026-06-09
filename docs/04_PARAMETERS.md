# 04 · Parameter Design

Parameters are the contract between DSP and UI **and** the thing presets save. Get
the list right before building the UI.

## Naming and the contract

- Name parameters `param1..paramN`, **sequentially**. The number — not the label —
  is the identity that links DSP, UI, and saved presets.
- The `[[ name: "..." ]]` annotation is a **display label only**. Never branch on it
  in DSP code.
- **Never renumber or reuse a number** after wiring. To add a parameter to an
  existing plugin, append it at the next free number, even if it logically belongs
  in the middle. (Real production plugins visibly do this — new params accumulate at
  the end so old presets keep loading.)

## Parameter types

| Type | Declaration | Notes |
|---|---|---|
| Continuous knob/slider | `input value float` (host-smoothed) or `input event float` | normalise to 0..1 or use real `min`/`max` |
| Toggle (on/off) | `input event float ... [[ ..., step: 1.0 ]]` with `min:0,max:1` | check `if (v >= 0.5)` |
| Enum / mode | `input event float ... [[ ..., step: 1.0 ]]` or `text: "A|B|C"` | equally spaced values; compare ranges |
| Bypass | dedicated `input event float` | short-circuit the process loop |

Annotation keys seen in practice: `min`, `max`, `init`, `unit` (e.g. `"Hz"`,
`"ms"`, `"dB"`), `step` (discrete steps / toggles), `text` (enumerated labels).

## Normalisation

A common convention is to send everything as 0.0–1.0 and map to the real range on
one side only — pick one and be consistent:

```javascript
// UI formatter example: 0.1–80 Hz display
const fmt = v => (0.1 + v * 79.9).toFixed(1) + ' Hz';
```
```cmajor
// DSP mapping of a normalised rate:
phase += float64(rate) * maxHz * dt;   // maxHz = your range ceiling
```

Alternatively, declare real `min`/`max`/`unit` on the endpoint and let the host
present real units — then the DSP receives real values directly. Either is fine;
mixing them per-parameter is fine too, as long as each parameter is unambiguous.

## Smoothing

For gain or cutoff parameters, smooth to avoid zipper noise on automation. Two
options:

- **Host-smoothed:** declare `input value float` and add `rampFrames: N`.
- **Manual 1-pole slew** in the DSP:
  ```cmajor
  let coeff = 0.001f;                          // tune per parameter
  smoothed += coeff * (target - smoothed);
  ```

## Constant-power pan law (unity at centre)

When you implement pan or stereo modulation, use the constant-power (`sqrt`) law and
**normalise so the centre is unity gain**, not −3 dB — otherwise switching on any
LFO-driven panning causes an audible level jump:

```cmajor
let norm = float (sqrt (2.0));
let panL = float (sqrt (clamp (0.5 + s * depth * 0.5, 0.0, 1.0))) * norm;
let panR = float (sqrt (clamp (0.5 - s * depth * 0.5, 0.0, 1.0))) * norm;
```

## Presets & state — what persists where

Three storage layers exist; choosing the wrong one is a classic source of "my
setting didn't come back" bugs:

| Layer | API | Round-trips with DAW project/preset? | Use for |
|---|---|---|---|
| **Parameters** | `paramN` endpoints | **Yes** — saved, automated, preset-recalled | everything that affects sound |
| **Stored UI state** | `pc.sendStoredStateValue(key, json)` / `requestStoredStateValue` / `addStoredStateValueListener` | **Yes** (saved with the host project) | UI-only state worth keeping per project: selected tab, editor zoom, A/B slot |
| **`localStorage`** | browser API | **No** — per machine, not per project | machine-local conveniences only (e.g. "tooltips seen") |

Rules of thumb:

- If it changes the audio, it **must** be a parameter — never `localStorage`, never
  stored-state. Otherwise presets lie.
- On load, restore *visual-only* state from stored-state/localStorage, but **do not
  push values into the DSP** on load — the host recalls parameters itself. (The
  bypass rule below is the canonical example.)
- Preset compatibility is the parameter-number contract: **append** new parameters
  at the next free number with a sensible `init` so old presets (which lack the new
  param) load with correct defaults. Never renumber, never reuse a number, never
  change a parameter's meaning between versions.

## Bypass

- Dedicate one parameter to global bypass. In the DSP, check it at the top of the
  process loop and output the dry signal directly.
- In the UI, restore only the **visual** bypass indicator from local UI state on
  load — do **not** push a stored bypass value to the DSP on load, or the plugin can
  come up silent after a session that ended bypassed. Anything that must round-trip
  through the DAW preset system goes through parameters, not `localStorage`.
