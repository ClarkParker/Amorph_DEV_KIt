# 03 · UI — JavaScript Web Component

The UI is a single, self-contained JavaScript file that defines a custom element
and renders inside Amorph's WebView (WKWebView on macOS, WebView2 on Windows,
WebKitGTK on Linux).

## The single-file contract

- **One `.js` file. No `import`/`require`, no ES-module dependencies, no CDN, no
  external libraries.** Inline all CSS, HTML and logic. (The file is itself a module
  with a default export, but it must not import anything.) If you want a reusable
  helper, inline it as a function/IIFE in the same file.
- The **default export** builds the element and returns it. The host calls it with
  the connection: **[verified]** `await viewModule.default(patchConnection)`.

```javascript
export default function createPatchView(patchConnection) {
  const el = document.createElement('plugin-ui');
  el.pc = patchConnection;          // keep the bridge on the element
  return el;
}
```

- Define a custom element extending `HTMLElement`, register it with
  `customElements.define('plugin-ui', PluginUI)` — **guard with
  `customElements.get`** so a reload doesn't double-register. Build the UI in
  `connectedCallback`; tear everything down in `disconnectedCallback`.

```javascript
class PluginUI extends HTMLElement {
  constructor(pc) { super(); this.pc = pc; }
  connectedCallback() { /* build DOM, wire bridge, start resize observers */ }
  disconnectedCallback() { /* remove every listener / observer / RAF / timer */ }
}
const TAG = 'plugin-ui';
if (!customElements.get(TAG)) customElements.define(TAG, PluginUI);
export default function createPatchView(pc) { return new PluginUI(pc); }
```

## The bridge API (patchConnection) — [verified]

```javascript
// Write a parameter (UI -> DSP). Optional ramp + timeout.
pc.sendEventOrValue('param1', value /*, rampFrames, timeoutMillisecs */);

// Read a parameter (DSP -> UI). Always requestParameterValue AFTER adding the
// listener, or the control shows a stale default until the user moves it.
pc.addParameterListener('param1', v => { ... });
pc.requestParameterValue('param1');
pc.removeParameterListener('param1', fn);

// DSP output events (meters, spectra, scopes). granularity/sendFullAudioData optional.
pc.addEndpointListener('rmsOut', v => { ... });
pc.removeEndpointListener('rmsOut', fn);

// MIDI for instruments
pc.sendMIDIInputEvent('midiIn', 0x900000 | (note << 8) | velocity);   // note on
pc.sendMIDIInputEvent('midiIn', 0x800000 | (note << 8) | velocity);   // note off

// Optional: automation gesture grouping (so a drag is one undo step)
pc.sendParameterGestureStart('param1');
pc.sendParameterGestureEnd('param1');

// Optional: stored UI-state (persists with the host project; UI-only state)
pc.sendStoredStateValue('key', anyJSON);
pc.requestStoredStateValue('key');
pc.addStoredStateValueListener(msg => { /* msg.key, msg.value */ });
```

The full verified method surface is tabulated in [`../STATUS.md`](../STATUS.md).

## Echo-loop protection (mandatory for any control)

A drag sends a value; the DSP echoes it back; the listener would then re-set the
control mid-drag, causing jitter. Keep a ring buffer of recently sent values and
ignore matching echoes. Wrap `sendEventOrValue` so the buffer stays in sync:

```javascript
const sent = [];
const send = (id, v) => {
  sent.push({ id, v });
  if (sent.length > 32) sent.shift();
  pc.sendEventOrValue(id, v);
};
pc.addParameterListener(id, v => {
  for (const p of sent) if (p.id === id && Math.abs(p.v - v) < 1e-4) return; // own echo
  setControl(v);                                                            // real external change
});
pc.requestParameterValue(id);                                              // initial state
```

## Mandatory patterns

1. **Echo-loop protection** on every two-way control (above).
2. **CSS `zoom`, never `transform: scale()`** for scaling. Keep a fixed-size
   `.chassis` and scale it with `zoom`. Full method (with host-wrapper fixes) in
   [`07_SCALING.md`](07_SCALING.md).
3. **Unscoped universal reset** so the host wrappers also get `box-sizing` and no
   scrollbars appear. This selector is **deliberately not scoped** — it must reach
   the host's wrapper elements:
   ```css
   * { box-sizing: border-box; outline: none; -webkit-tap-highlight-color: transparent; }
   html, body { margin: 0; padding: 0; overflow: hidden; }
   ```
4. **`setPointerCapture` for drags** so the gesture survives the cursor leaving the
   element. Use `pointerdown`/`pointermove`/`pointerup`, never mouse events.
5. **Clean up in `disconnectedCallback`** — remove every listener, disconnect every
   observer, cancel every RAF/timer. Otherwise you leak on plugin reload.
6. **Don't store DOM handles across an `innerHTML` write** — they vanish. Keep them
   in a `Map`, or query again after rebuilding.

## Visualisers (meters / scopes / spectra)

Drive them from DSP `output event` endpoints via `addEndpointListener`, render on a
`<canvas>` inside a `requestAnimationFrame` loop, and **only run the loop when the
visualiser is visible** — cancel the RAF when its module collapses, restart when it
opens, and `cancelAnimationFrame` in `disconnectedCallback`. For a spectrum, run the
analysis (e.g. a DFT) as a **separate DSP node at host rate**, not on an oversampled
node — see [`06_OVERSAMPLING.md`](06_OVERSAMPLING.md).

## Output contract

Return one complete, runnable `.js` file: inline CSS template literal, inline HTML
template literal, optional PARAM registry, the class, the guarded
`customElements.define`, and `export default createPatchView`. No `import`
statements.
