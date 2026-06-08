# Examples — one worked plugin per Amorph type

Three complete, copy-to-study plugins covering all three Amorph plugin types. Each
is real, self-contained (DSP + single-file UI + manifest) and passes the kit's own
checks (`tools/preflight.py` → DSP lint + UI lint + DSP↔UI sync, all clean).

| Folder | Type | What it shows |
|---|---|---|
| [`01_SaturatorFX/`](01_SaturatorFX/) | Audio FX | **Oversampling done right.** A non-linear core wrapped as `node core = SaturatorCore * 4`, with metering kept on a **separate host-rate** processor; drive/tone/mix/output/bypass; a canvas in/out level meter driven by DSP `output event`s. |
| [`02_PolySynth/`](02_PolySynth/) | Audio Instrument | **MIDI → audio.** 16-voice subtractive synth: voice allocation + stealing, note-off matched by `int` note number, per-voice saw + AR envelope + one-pole filter. UI has a playable on-screen keyboard (`sendMIDIInputEvent`) with incoming-MIDI highlight (`__amorphProcessMidi`). |
| [`03_MidiChord/`](03_MidiChord/) | MIDI Instrument | **MIDI → MIDI.** A harmonizer: emits a chord per note with transpose, velocity scale and RNG humanize — all in `event midiIn`, `main()` only advances. UI shows dual-colour input vs generated notes (`__amorphProcessMidi` + `__amorphProcessMidiOut`) and an enum (segmented) control. |

## Run the checks

```bash
python3 tools/preflight.py examples/01_SaturatorFX/
python3 tools/preflight.py examples/02_PolySynth/
python3 tools/preflight.py examples/03_MidiChord/
```

## How these map to the docs

- Oversampling topology & host-rate analysis → [`../docs/06_OVERSAMPLING.md`](../docs/06_OVERSAMPLING.md)
- Plugin types & endpoints (main vs sidechain, MIDI in/out) → [`../docs/10_PLUGIN_TYPES.md`](../docs/10_PLUGIN_TYPES.md)
- DSP rules & stdlib (RNG, MIDI, oscillators, casts) → [`../docs/02_DSP_CMAJOR.md`](../docs/02_DSP_CMAJOR.md)
- UI bridge, lifecycle, MIDI hooks → [`../docs/03_UI_WEBCOMPONENT.md`](../docs/03_UI_WEBCOMPONENT.md)
- The verbatim official prompts these follow → [`../ai/amorph_official/`](../ai/amorph_official/)

## Caveats

These compile against the documented Cmajor rules and pass the static checks, but the
kit's tools are heuristic — **load each patch in Amorph and listen** before relying on
it. The MidiChord harmonizer is a *transformer* (fits the "main() only advances" rule);
a time-based MIDI tool (arpeggiator) would need a sample clock in `main()`, which goes
beyond the default MIDI template.
