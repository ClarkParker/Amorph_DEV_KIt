# 10 · Amorph Plugin Types & Endpoint Structure

Amorph offers three plugin categories. In the IDE's DSP browser they appear as
`Amorph_FX` (under "Other"), `Amorph_Instrument`, and `Amorph_MIDI`.

> **Two sources, reconciled.** The official Amorph IDE prompts (captured verbatim in
> [`../ai/amorph_official/`](../ai/amorph_official/)) describe a **minimal default
> template** per type. The **actual tested host capability** is broader. This doc
> uses the **tested capability as authoritative** and flags where the default
> templates are narrower. Status of the matrix: **[tested by maintainer]**.

## I/O matrix (tested capability)

| Type | Audio In | Sidechain In | MIDI In | MIDI Out | Audio Out |
|---|:---:|:---:|:---:|:---:|:---:|
| **Audio FX** (`Amorph_FX`) | ✅ | ✅ | ✅ (in only) | — | ✅ |
| **Audio Instrument** (`Amorph_Instrument`) | — | ✅ | ✅ | — | ✅ |
| **MIDI Instrument** (`Amorph_MIDI`) | — | ✅ | ✅ | ✅ | ✅ |

- **Audio FX** processes incoming audio. It also has a sidechain bus and **MIDI in**
  (input only — no MIDI out).
- **Audio Instrument** generates audio from MIDI (a synth). No main audio input.
- **MIDI Instrument** generates/transforms MIDI (arpeggiator, sequencer, chord tool…).
  Amorph's product guide describes it as "MIDI out **+ silent audio**" — i.e. it
  always carries an audio output (silent by default), which is why an audio stream on
  a MIDI plugin is valid.
- All three have a **sidechain input**.

> All variants share the **50-parameter limit** (see
> [`13_AMORPH_IDE.md`](13_AMORPH_IDE.md) and [`04_PARAMETERS.md`](04_PARAMETERS.md)).

### Where the default prompt templates are narrower

| Default template says… | Tested reality |
|---|---|
| FX prompt: "no MIDI" | FX **has MIDI in** (no MIDI out). |
| MIDI prompt: "pure MIDI, NO `output stream`" | MIDI Instrument **can also output audio**. |
| No prompt mentions sidechain | All types **have a sidechain input** (`scIn`). |

These are not contradictions in the host — the prompt text is simply not yet updated.
If you only need the minimal template, follow the prompt; if you need MIDI on an FX,
audio on a MIDI tool, or a sidechain, declare the endpoint and it works.

## Endpoint declarations

Endpoint *names* below (`in`, `scIn`, `midiIn`, `midiOut`, `out`) are conventions;
what the type needs is the *presence* of each endpoint. `scIn` is the field-tested
sidechain name.

### Audio FX
```cmajor
processor MyFX
{
    input  stream float<2> in;                       // main audio
    input  stream float<2> scIn;                     // sidechain bus (optional)
    input  event  std::midi::Message midiIn;         // MIDI in (optional; in only)
    output stream float<2> out;                      // audio out
    // optional host transport: input event std::timeline::Tempo/Position/TransportState (see 05_AMORPH_NOTES)
    // ... param1..paramN, meter output events ...
}
```
The minimal FX template (per the official prompt) is just `in` + `out`. Add `scIn`
and/or `midiIn` only if you use them.

### Audio Instrument
```cmajor
processor MyInstrument
{
    input  event  std::midi::Message midiIn;         // notes in
    input  stream float<2> scIn;                     // sidechain bus (optional)
    output stream float out;                         // audio out (float or float<2>)
    // ... param1..paramN, meter output events ...
}
```

### MIDI Instrument
```cmajor
processor MyMidiTool
{
    input  event  std::midi::Message midiIn;         // MIDI in
    output event  std::midi::Message midiOut;        // MIDI out
    input  stream float<2> scIn;                     // sidechain bus (optional)
    output stream float<2> out;                      // audio out (optional)
    // ... param1..paramN ...
}
```
The minimal MIDI template is `midiIn` + `midiOut` only (no audio). For a pure MIDI
processor, `main()` is just `loop { advance(); }` — all work happens in
`event midiIn`.

## Sidechain & multiple audio inputs — how it works

**Status: [verified]** against the Cmajor CLAP wrapper source
(`modules/plugin/include/clap/cmaj_CLAPPlugin.h`). Amorph follows the same
order-based convention (matches field observation).

- **Endpoint names are free.** There is **no fixed name** like `scIn` — the bus name
  the host shows is simply the endpoint's ID (`endpoint.endpointID`). Name it
  `sidechain`, `scIn`, `aux`, whatever; what matters is the **declaration order**.
- **Each audio input `stream` endpoint becomes its own audio bus**, in declaration
  order.
- **The first audio input endpoint (index 0) is implicitly the MAIN input; every
  later one is a sidechain.** From the source comment: *"first endpoint is implicitly
  main … there can only be one, and it must be index 0."* So there must be a main in
  before any sidechain — exactly as observed in Amorph.
- **Channel count = the stream's vector width:** `float` → mono (1), `float<2>` →
  stereo (2). Wider vectors (`float<N>`) set the channel count but have no standard
  mono/stereo port type (1 and 2 map to `CLAP_PORT_MONO`/`CLAP_PORT_STEREO`).
- **No hard maximum** on the number of sidechain buses in the wrapper — it loops over
  all audio input endpoints. The **DAW/host** decides how many sidechain routes it
  actually supports.

```cmajor
processor MyFX
{
    input  stream float<2> in;       // index 0 -> MAIN input (must come first)
    input  stream float<2> scIn;     // index 1 -> sidechain bus (name is free)
    // input stream float<2> scIn2;  // index 2 -> a second sidechain, etc.
    output stream float<2> out;
}
```

> Only the **main** input must exist for an effect. Sidechain endpoints are optional;
> declare one (or more) only when you use them. Note `addEndpointListener`'s
> audio-shaped callback also gives per-channel min/max (or full data) — useful for
> metering a sidechain in the UI.

## Manifest

`category` and `isInstrument` reflect the type, but **do not fully distinguish the
two instrument types**:

| Type | `category` | `isInstrument` |
|---|---|---|
| Audio FX | `"effect"` | `false` |
| Audio Instrument | `"instrument"` | `true` |
| MIDI Instrument | `"instrument"` | `true` |

Audio Instrument and MIDI Instrument share the same manifest fields — the difference
is the **endpoints** (a MIDI Instrument has a `midiOut` event endpoint). **[verified-official]**

## Bridge implications (UI side)

- **MIDI in:** Amorph exposes `window.__amorphProcessMidi` (batched at ~60 Hz) to
  visualise incoming MIDI; to inject notes, use
  `patchConnection.sendMIDIInputEvent("midiIn", (status << 16)|(d1 << 8)|d2)`.
- **MIDI out (MIDI Instrument):** `window.__amorphProcessMidiOut` fires for generated
  notes — use it to highlight output (e.g. dual-colour keys: input vs generated).
- **Sidechain:** routed by the host; the DSP just reads `scIn`. Nothing special in
  the UI beyond any sidechain-related parameters you expose.
- Details and verbatim snippets: [`../ai/amorph_official/UI_variants.md`](../ai/amorph_official/UI_variants.md).
