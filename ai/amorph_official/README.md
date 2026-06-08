# Official Amorph IDE Prompts (captured verbatim)

Amorph ships its own IDE with AI assistance. When you generate a plugin, the IDE
feeds the model a per-variant system prompt. Those prompts are the **most
authoritative source** for how Amorph expects DSP and UI code to be written — so
they are captured here verbatim.

## Files

| File | Variant | Layer |
|---|---|---|
| [`DSP_AudioFX.md`](DSP_AudioFX.md) | Amorph_FX | DSP |
| [`DSP_AudioInstrument.md`](DSP_AudioInstrument.md) | Amorph_Instrument | DSP |
| [`DSP_MIDIInstrument.md`](DSP_MIDIInstrument.md) | Amorph_MIDI | DSP |
| [`UI_common.md`](UI_common.md) | all three (shared body) | UI |
| [`UI_variants.md`](UI_variants.md) | per-variant header + MIDI section | UI |

The three UI prompts are ~95% identical; the IDE concatenates a small variant header
(intro + bridge table + MIDI section + manifest) with the shared body. We store the
body once (`UI_common.md`) and the deltas separately (`UI_variants.md`) to avoid
triplicating ~400 identical lines while keeping every unique line.

## How to use them

These are drop-in system prompts. For a new plugin, paste the matching DSP prompt
before asking for DSP code, and the UI body + the matching variant section before
asking for UI code. The kit's own condensed prompts in [`../`](..) defer to these.

## Reconciliation — where the prompts are outdated or host-specific

The prompts are authoritative on **Cmajor correctness** but a few statements about
**host capabilities** lag behind what the Amorph host actually does. Tested by the
maintainer:

1. **Audio FX MIDI.** The FX prompt says "no MIDI" and its bridge table marks
   `window.__amorphProcessMidi` as unavailable. **Tested:** Audio FX **does receive
   MIDI input** (MIDI **in only**, no MIDI out). The prompt is simply not updated.
   → An FX UI **can** use `window.__amorphProcessMidi`; an FX DSP **can** declare
   `input event std::midi::Message midiIn;`.

2. **MIDI Instrument audio output.** The MIDI prompt says "pure MIDI processor … NO
   `output stream`". **Tested:** a MIDI Instrument **can also have an audio output**.
   The pure-MIDI template is the default, not a hard limit.

3. **Sidechain input.** None of the three prompts mention a sidechain endpoint, but
   all three plugin types have a **sidechain input** in the host (a real FX plugin
   uses `input stream float<2> scIn;`). It's available; the default templates just
   omit it.

The authoritative I/O matrix (tested capability, not the default templates) is in
[`../../docs/10_PLUGIN_TYPES.md`](../../docs/10_PLUGIN_TYPES.md).

Other host-specific notes the prompts establish (all **[verified-official]**):

- **Parameter listener payload:** `addAllParameterListener` fires with **one object**
  `{ endpointID, value }` — not `(id, value)`. (The per-parameter
  `addParameterListener(id, fn)` also works and is used in real plugins; both are
  valid — pick one.)
- **MIDI viz hooks:** `window.__amorphProcessMidi` (in) and
  `window.__amorphProcessMidiOut` (out) are Amorph-specific globals batched at ~60 Hz.
- **Send MIDI from UI:** `patchConnection.sendMIDIInputEvent("midiIn", packedInt)`
  with `(status << 16) | (data1 << 8) | data2`. `patchConnection.sendMIDI(...)` does
  **not** exist.
- **Layout:** light DOM only (no `attachShadow`), `// WINDOW SIZE: WxH` on line 2,
  `data-endpoint-id="paramN"` on each control (enables the IDE's right-click AI
  context). The prompt's default layout is **fluid** (`:host` 100%/100%, %/fr/flex/
  grid) — note that real pixel-perfect plugins instead use a fixed chassis scaled
  with CSS `zoom` (see [`../../docs/07_SCALING.md`](../../docs/07_SCALING.md)).

### Internal quirks to be aware of

- The DSP prompts forbid prefix `++`/`--`, yet their own example `for` loops use
  `++i`. Following the stated rule (`i += 1`) is the safe choice; `++i` in a `for`
  header evidently compiles in practice.
- The spectrum sections say "C++ changes ARE required … PluginProcessor.cpp must
  handle `spectrumOut`." That applies to exporting the patch as a standalone JUCE
  plugin. **In the Amorph host, `addEndpointListener` receives the events directly**
  with no C++ wiring — a real reverb plugin emits `spectrumData`/`resonanceData` and
  reads them straight in JS.
