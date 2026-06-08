# 10 · Amorph Plugin Types & Endpoint Structure

**Status: [field-tested]** — taken from the Amorph IDE's own plugin browser and from
a real plugin's endpoints. Endpoint *names* (`scIn`, `midiIn`, …) are conventions;
the *presence* of each I/O per type is what the type definition requires.

Amorph offers three plugin categories. In the IDE's DSP browser they appear as
`Amorph_FX` (under "Other"), `Amorph_Instrument`, and `Amorph_MIDI`.

## I/O matrix

| Type | Audio In | Sidechain In | MIDI In | MIDI Out | Audio Out |
|---|:---:|:---:|:---:|:---:|:---:|
| **Audio FX** | ✅ | ✅ | ✅ | — | ✅ |
| **Audio Instrument** | — | ✅ | ✅ | — | ✅ |
| **MIDI Instrument** | — | ✅ | ✅ | ✅ | ✅ |

- **Audio FX** processes incoming audio. It also gets a sidechain bus and MIDI in
  (e.g. for tempo-synced or note-triggered behaviour).
- **Audio Instrument** generates audio from MIDI (a synth). No main audio input.
- **MIDI Instrument** generates/transforms MIDI (arpeggiator, sequencer, chord
  tool…) and also has an audio output (e.g. for monitoring/auditioning).

All three have a **sidechain input** and a **MIDI input**.

## Endpoint declarations (typical / conventional)

### Audio FX
```cmajor
processor MyFX
{
    input  stream float<2> in;                       // main audio
    input  stream float<2> scIn;                     // sidechain bus
    input  event  std::midi::Message midiIn;         // MIDI in
    output stream float<2> out;                      // audio out
    // optional host transport, e.g.:
    // input event float64 transportIn;
    // ... param1..paramN, meters ...
}
```

### Audio Instrument
```cmajor
processor MyInstrument
{
    input  stream float<2> scIn;                     // sidechain bus
    input  event  std::midi::Message midiIn;         // notes in
    output stream float<2> out;                      // audio out
    // ... param1..paramN, meters ...
}
```

### MIDI Instrument
```cmajor
processor MyMidiTool
{
    input  stream float<2> scIn;                     // sidechain bus
    input  event  std::midi::Message midiIn;         // MIDI in
    output event  std::midi::Message midiOut;        // MIDI out
    output stream float<2> out;                      // audio out (monitor/aux)
    // ... param1..paramN, meters ...
}
```

## Manifest

The category is reflected in the `.cmajorpatch` manifest. `isInstrument: false` for
Audio FX; `isInstrument: true` for the instrument types. (How Amorph distinguishes an
Audio Instrument from a MIDI Instrument in the manifest is **[unverified]** — likely
the presence of a MIDI `output event` endpoint and/or a `category` value. Confirm and
update this note.)

## Bridge implications (UI side)

- **MIDI in (instruments):** the UI sends notes with
  `pc.sendMIDIInputEvent('midiIn', code)` — note-on `0x900000 | (note<<8) | vel`,
  note-off `0x800000 | (note<<8) | vel`. (See `03_UI_WEBCOMPONENT.md`.)
- **Sidechain:** routed by the host; the DSP just reads `scIn`. Nothing special on
  the UI side beyond any sidechain-related parameters you expose.
- **MIDI out (MIDI Instrument):** emitted from the DSP as an `output event
  std::midi::Message`; if you visualise it in the UI, listen via
  `pc.addEndpointListener('midiOut', ...)`.

## Open questions

- Exact endpoint **names** Amorph expects per type (are `in`/`scIn`/`midiIn`/
  `midiOut`/`out` fixed, or free as long as types match?). **[unverified]**
- Whether the sidechain on instrument types is always present or opt-in. **[unverified]**
- The official Amorph IDE AI prompts per type — to be added here once captured.
