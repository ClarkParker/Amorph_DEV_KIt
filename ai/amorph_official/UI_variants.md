# Official Amorph IDE prompt — UI (per-variant parts)

> The UI prompt body is shared (see [`UI_common.md`](UI_common.md)). Only the
> **intro line, host-bridge table, MIDI section (E), and manifest** differ per
> variant. Those are captured **verbatim** below, followed by reconciliation notes
> where the tested host capability differs from the (not-yet-updated) prompt.

---

## Audio FX (Amorph_FX)

**Intro:** *You are writing the JavaScript UI for the **Amorph_FX** plugin variant.*

**Host bridges (as stated by the official prompt):**

| Bridge | Available (per prompt) |
|---|---|
| `window.__amorphProcessMidi` | [NO] No -- FX has no MIDI |
| `window.__amorphProcessMidiOut` | [NO] No |
| `patchConnection.sendEventOrValue(paramX, v)` | [OK] Yes |
| `patchConnection.addEndpointListener(id, fn)` | [OK] Yes |
| Spectrum output (`spectrumOut`, `spectrumPreOut`) | [OK] If patch emits it |

**MIDI section:** none (the FX prompt has no section E MIDI block).

> ⚠️ **Reconciliation — [tested by maintainer]:** Audio FX **does** receive **MIDI
> input** in the actual Amorph host — the prompt's "FX has no MIDI" line is simply
> **not yet updated**. So `window.__amorphProcessMidi` **is** usable for an FX UI to
> visualise incoming MIDI. FX has **MIDI in only** (no MIDI out). Use the MIDI-input
> snippet from the Audio Instrument variant below if your FX reacts to MIDI.

---

## Audio Instrument (Amorph_Instrument)

**Intro:** *You are writing the JavaScript UI for the **Amorph_Instrument** plugin variant.*

**Host bridges:**

| Bridge | Available |
|---|---|
| `window.__amorphProcessMidi` (MIDI INPUT) | [OK] Yes |
| `window.__amorphProcessMidiOut` | [NO] No -- Instrument has no MIDI output |
| `patchConnection.sendEventOrValue(paramX, v)` | [OK] Yes |
| `patchConnection.addEndpointListener(id, fn)` | [OK] Yes |
| Spectrum output (`spectrumOut`) | [OK] If patch emits it |

### E) MIDI VISUALIZATION (Amorph Feature)

**MIDI INPUT -- highlights incoming notes/CCs**

    window.__amorphProcessMidi = (messages) => {
        messages.forEach(msg => {
            const { s, d1, d2 } = msg;
            const type = s & 0xF0;
            if      (type === 0x90 && d2 > 0)                      highlightKey(d1, "input",  d2 / 127);
            else if (type === 0x80 || (type === 0x90 && d2 === 0)) unhighlightKey(d1, "input");
            else if (type === 0xB0)                                 updateCC(d1, d2);
        });
    };

> [NO] `window.__amorphProcessMidiOut` does **not** exist on Amorph_Instrument -- never add it.

**Sending MIDI TO the patch from JS (trigger notes from UI elements):**

    // Endpoint ID is always "midiIn" for Amorph patches
    // Pack: (status << 16) | (data1 << 8) | data2
    patchConnection.sendMIDIInputEvent("midiIn", (0x90 << 16) | (note << 8) | velocity); // note on
    patchConnection.sendMIDIInputEvent("midiIn", (0x80 << 16) | (note << 8) | 0);        // note off
    patchConnection.sendMIDIInputEvent("midiIn", (0xB0 << 16) | (cc   << 8) | value);    // CC

> The patch's `event midiIn` handler receives this exactly as if from a keyboard.
> `__amorphProcessMidi` will also fire back -- use it to drive pad/key highlight state.
> [NO] `patchConnection.sendMIDI(...)` does NOT exist -- always use `sendMIDIInputEvent`.

**Cleanup in `disconnectedCallback()`:**

    delete window.__amorphProcessMidi;

Messages arrive batched at ~60 Hz. No DSP or C++ changes needed.

---

## MIDI Instrument (Amorph_MIDI)

**Intro:** *You are writing the JavaScript UI for the **Amorph_MIDI** plugin variant.*

**Host bridges:**

| Bridge | Available |
|---|---|
| `window.__amorphProcessMidi` (MIDI INPUT to processor) | [OK] Yes |
| `window.__amorphProcessMidiOut` (MIDI OUTPUT from processor) | [OK] Yes |
| `patchConnection.sendEventOrValue(paramX, v)` | [OK] Yes |
| `patchConnection.addEndpointListener(id, fn)` | [OK] Yes |
| Spectrum output (`spectrumOut`) | [OK] If patch emits it |

### E) MIDI VISUALIZATION (Amorph Feature)

**MIDI INPUT -- highlights incoming notes/CCs**

    window.__amorphProcessMidi = (messages) => {
        messages.forEach(msg => {
            const { s, d1, d2 } = msg;
            // s = status byte, d1 = note/CC number, d2 = velocity/value
            const type = s & 0xF0;
            if      (type === 0x90 && d2 > 0)                      highlightKey(d1, "input",  d2 / 127);
            else if (type === 0x80 || (type === 0x90 && d2 === 0)) unhighlightKey(d1, "input");
            else if (type === 0xB0)                                 updateCC(d1, d2);
        });
    };

**MIDI OUTPUT -- Amorph_MIDI ONLY (generated/transformed notes)**

    window.__amorphProcessMidiOut = (messages) => {
        messages.forEach(msg => {
            const type = msg.s & 0xF0;
            if      (type === 0x90 && msg.d2 > 0)                      highlightKey(msg.d1, "output", msg.d2 / 127);
            else if (type === 0x80 || (type === 0x90 && msg.d2 === 0)) unhighlightKey(msg.d1, "output");
        });
    };

**Dual-colour CSS (MIDI variant best practice)**

    .key.input  { background: linear-gradient(to bottom, #8B5CF6, #6D28D9); } /* Purple = played    */
    .key.output { background: linear-gradient(to bottom, #06B6D4, #0891B2); } /* Cyan   = generated */
    .key.both   { background: linear-gradient(135deg,    #8B5CF6, #06B6D4); } /* Both               */

**Sending MIDI TO the patch from JS (inject notes/CCs from UI elements):**

    // Endpoint ID is always "midiIn" for Amorph patches
    // Pack: (status << 16) | (data1 << 8) | data2
    patchConnection.sendMIDIInputEvent("midiIn", (0x90 << 16) | (note << 8) | velocity); // note on
    patchConnection.sendMIDIInputEvent("midiIn", (0x80 << 16) | (note << 8) | 0);        // note off
    patchConnection.sendMIDIInputEvent("midiIn", (0xB0 << 16) | (cc   << 8) | value);    // CC

> `__amorphProcessMidi` fires back confirming the note arrived -- use it for pad highlight.
> `__amorphProcessMidiOut` fires for generated output notes.
> [NO] `patchConnection.sendMIDI(...)` does NOT exist -- always use `sendMIDIInputEvent`.

**Cleanup in `disconnectedCallback()`:**

    delete window.__amorphProcessMidi;
    delete window.__amorphProcessMidiOut;

Messages arrive batched at ~60 Hz. No DSP or C++ changes needed.

---

## DSP → UI wiring contract (identical across variants)

Each UI prompt also includes this contract near the top:

- Create controls **only** for endpoint IDs that exist in the DSP (`param1..paramN`).
- Use the **same ID string** everywhere: `data-param`, Map key, `sendEventOrValue`, `requestParameterValue`.
- Keep labels human-readable in display text only -- never rename endpoint IDs in logic.
- Mirror DSP `min`/`max`/`init` ranges exactly in the control config.

The current-DSP placeholder shown to the model is:

    // Describe what you want in the chat and the AI agent will build it
    // Or write Cmajor code here directly and press COMPILE

## MIDI short-code packing (note)

The official UI prompt packs MIDI as `(status << 16) | (data1 << 8) | data2`.
`0x90 << 16 == 0x900000`, so `(0x90 << 16) | (note << 8) | vel` is identical to the
`0x900000 | (note << 8) | vel` form. Both are correct.
