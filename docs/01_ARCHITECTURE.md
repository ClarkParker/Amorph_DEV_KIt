# 01 · Architecture

A plugin has three layers that communicate through a strict interface. The DSP and
the UI are completely decoupled: they never share memory and never call each other
directly. Everything crosses the **parameter bridge**.

```
+-----------------------------+        +-----------------------------+
|  DSP  (Cmajor, .cmajor)     |        |  UI  (JavaScript, .js)      |
|  one processor / graph      |        |  one self-contained module  |
|  param1..paramN endpoints   |        |  custom HTMLElement         |
+--------------+--------------+        +--------------+--------------+
               |                                      |
               |        parameter bridge              |
               |   sendEventOrValue   (UI -> DSP)     |
               |   addParameterListener (DSP -> UI)   |
               |   addEndpointListener  (meters etc.) |
               |   sendMIDIInputEvent   (notes)       |
               +-------------------+------------------+
                                   |
                       +-----------+-----------+
                       |  Manifest (.cmajorpatch)|
                       |  links DSP + UI + size  |
                       +-------------------------+
```

## The manifest (`.cmajorpatch`)

A small JSON file the host loads first. Generic shape:

```json
{
  "CmajorVersion": 1,
  "ID":           "com.yourcompany.plugin",
  "version":      "1.0.0",
  "name":         "Plugin",
  "description":  "What it does.",
  "category":     "effect",
  "manufacturer": "Your Company",
  "isInstrument": false,
  "source":       "PluginDSP.cmajor",
  "view": { "src": "PluginUI.js", "width": 800, "height": 400, "resizable": true }
}
```

- `source` — the DSP file (or an array of files, all linked together).
- `isInstrument` — `true` for a MIDI-driven instrument, `false` for an effect.
- `view.src` — the UI module. `view.width`/`height` are the **design size**; keep
  them in sync with the fixed chassis size in the UI (see `07_SCALING.md`).
- `view.resizable` — whether the host allows the window to be resized.

## The DSP layer (Cmajor)

One top-level `processor` or `graph`. It declares:

- **Audio I/O** as streams: `input stream float<2> in;` / `output stream float<2> out;`
  for stereo (use `float` for mono). An instrument typically has
  `output stream float<2> out;` and a MIDI input
  `input event std::midi::Message midiIn;`. The exact I/O set depends on the plugin
  type (Audio FX / Audio Instrument / MIDI Instrument) — see
  [`10_PLUGIN_TYPES.md`](10_PLUGIN_TYPES.md).
- **Parameters** as `input event`/`input value` endpoints named `param1..paramN`,
  each with a `[[ name: ... ]]` annotation.
- **Meters / scopes** as `output event` endpoints the UI listens to.

Details and the parameter pattern: [`02_DSP_CMAJOR.md`](02_DSP_CMAJOR.md).

## The UI layer (JavaScript Web Component)

One self-contained `.js` file — **no imports, no external libraries**. The host
imports the module and calls its **default export** with the connection: **[verified]**

```javascript
// host side (cmaj-patch-view.js), for reference only:
const viewModule = await import(viewModuleURL);
const patchView  = await viewModule.default(patchConnection);   // your default export
```

So your file's job is:

```javascript
export default function createPatchView(patchConnection) {
  const el = document.createElement('plugin-ui');
  el.pc = patchConnection;          // keep the bridge on the element
  return el;                        // the host inserts this into the WebView
}
```

The element reads/writes parameters through `el.pc` (the `patchConnection`).
Details, the full bridge API, and lifecycle: [`03_UI_WEBCOMPONENT.md`](03_UI_WEBCOMPONENT.md).

## The parameter bridge

| Direction | Call | Use |
|---|---|---|
| UI → DSP | `pc.sendEventOrValue(id, value)` | set a parameter |
| DSP → UI | `pc.addParameterListener(id, fn)` then `pc.requestParameterValue(id)` | reflect automation / preset recall |
| DSP → UI | `pc.addEndpointListener(id, fn)` | meters, spectra, custom events |
| UI → DSP | `pc.sendMIDIInputEvent(endpoint, code)` | play notes (instruments) |

The single most important rule that spans both layers: **parameters are named
`param1..paramN` and the number is the contract.** Decide the parameter list on the
DSP side first, then build the UI against those numbers. Renumbering later breaks
every saved preset. When you add a parameter to an existing plugin, **append it at
the next free number** — never reuse or shift old numbers (a real production plugin
visibly does this: new params land at the end even when they belong, logically, in
the middle).
