# Getting Started — your first Amorph plugin in ~15 minutes

This walkthrough takes you from nothing to a compiled, host-loadable plugin, using
only this kit. No prior Cmajor knowledge required — but keep
[`docs/02_DSP_CMAJOR.md`](docs/02_DSP_CMAJOR.md) open as the reference.

**You need:** Python 3.8+, the Amorph host (or the `cmaj` CLI for a quick
compile check), and this repository cloned.

---

## Step 1 — Describe your plugin (one small JSON)

The parameter list is the contract between DSP, UI and saved presets — so you write
it **once** and generate both sides from it. Create `myplugin.json`:

```json
{
  "name": "First Drive",
  "id": "com.yourname.firstdrive",
  "manufacturer": "Your Name",
  "type": "fx",
  "width": 800, "height": 400,
  "params": [
    { "name": "Drive",  "min": 0.0,   "max": 1.0, "init": 0.3 },
    { "name": "Mix",    "min": 0.0,   "max": 1.0, "init": 0.5 },
    { "name": "Output", "min": -24.0, "max": 6.0, "init": 0.0, "unit": "dB" }
  ]
}
```

`type` is one of `fx` (audio in → audio out), `instrument` (MIDI → audio), `midi`
(MIDI → MIDI). The three types and their I/O are explained in
[`docs/10_PLUGIN_TYPES.md`](docs/10_PLUGIN_TYPES.md).

## Step 2 — Scaffold it

```bash
python3 tools/new_plugin.py myplugin.json --out ./FirstDrive
```

You get three files — the whole plugin:

| File | What it is |
|---|---|
| `FirstDriveDSP.cmajor` | the DSP: parameters wired (3-step pattern), audio loop ready |
| `FirstDriveUI.js` | a working single-file UI: sliders, host sync, cleanup |
| `FirstDrive.cmajorpatch` | the manifest linking the two |

## Step 3 — Sanity-check before you touch anything

```bash
python3 tools/preflight.py ./FirstDrive
```

You should see `✓ All clear.` — endpoint summary, DSP lint, UI lint, and the DSP↔UI
parameter sync all pass. Run this again after **every** edit; it catches the known
traps (reserved identifiers, missing `advance()`, Shadow DOM, missing cleanup, …)
in about a second.

## Step 4 — Make it actually do something

Open `FirstDriveDSP.cmajor`. The generated loop passes audio through; add drive and
mix using a recipe from the [cookbook](docs/11_DSP_COOKBOOK.md). Replace the
`// ---- your DSP here ----` block:

```cmajor
// soft saturation with constant make-up (cookbook recipe #9)
let d    = 1.0f + p_drive * 9.0f;
let wetL = float (tanh (float64 (l * d))) / float (tanh (float64 (d)));
let wetR = float (tanh (float64 (r * d))) / float (tanh (float64 (d)));

// dry/wet
l = l + p_mix * (wetL - l);
r = r + p_mix * (wetR - r);

// output trim (dB -> linear)
let g = float (std::levels::dBtoGain (float64 (p_output)));
l *= g;
r *= g;
```

Three rules you must never break (the linter enforces them):

1. Every loop iteration writes `out <-` **and** calls `advance()` —
   unconditionally.
2. No `double` (use `float64`), no C++ tokens, no `input`/`output`/`stream` as
   names.
3. Read the sample rate from `processor.frequency` — never hardcode `48000`.

## Step 5 — Compile

In the **Amorph IDE**: open the `.cmajorpatch`, press COMPILE, play audio through
it, turn the knobs.

Or headless with the **cmaj CLI** (download from
[cmajor-lang/cmajor releases](https://github.com/cmajor-lang/cmajor/releases)):

```bash
cmaj generate --target=cpp --output=/dev/null FirstDrive/FirstDrive.cmajorpatch
```

Exit code 0 = it compiles. (On a headless Linux box see the stub recipe in
[`STATUS.md`](STATUS.md) §"Reproducing the compile check".)

## Step 6 — Make the UI yours

`FirstDriveUI.js` is intentionally plain. Restyle it freely — it's one file, all CSS
inline. The rules that keep it working in Amorph's WebView are in
[`docs/03_UI_WEBCOMPONENT.md`](docs/03_UI_WEBCOMPONENT.md) and
[`docs/05_AMORPH_NOTES.md`](docs/05_AMORPH_NOTES.md); the short version:

- one file, **no `import`**, no external libraries, light DOM (no `attachShadow`)
- every control: echo-safe two-way binding + `requestParameterValue` after the
  listener
- clean up everything in `disconnectedCallback`
- no `backdrop-filter`, no `vw`/`vh`

For knob/meter/keyboard patterns, steal from the worked examples in
[`examples/`](examples/) — all three compile and pass every check.

## Step 7 — Lock it in

```bash
python3 tools/preflight.py ./FirstDrive        # still all clear?
bash tools/hooks/install.sh                    # run the checks on every commit
```

When you later **add** a parameter: append it as the next `paramN` — never renumber
existing ones (it breaks saved presets). That rule is the single most important
convention in the whole kit.

---

## Where to go next

| Want to… | Read |
|---|---|
| understand the three layers properly | [`docs/01_ARCHITECTURE.md`](docs/01_ARCHITECTURE.md) |
| add saturation/filters/compression | [`docs/11_DSP_COOKBOOK.md`](docs/11_DSP_COOKBOOK.md) |
| oversample a distortion stage | [`docs/06_OVERSAMPLING.md`](docs/06_OVERSAMPLING.md) |
| build a synth or MIDI tool | [`examples/02_PolySynth`](examples/02_PolySynth/), [`examples/03_MidiChord`](examples/03_MidiChord/) |
| write unit tests for your DSP | [`docs/12_TESTING.md`](docs/12_TESTING.md) |
| ask an AI to write code for you | [`ai/amorph_official/`](ai/amorph_official/) (paste as system prompt) |
| fix something that broke | [`docs/09_PITFALLS_CHECKLIST.md`](docs/09_PITFALLS_CHECKLIST.md) |
