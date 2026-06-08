// MidiChord UI — single-file Web Component for the Amorph_MIDI example.
// WINDOW SIZE: 760x380
//
// Demonstrates: a segmented (enum) control, knobs, a toggle, and dual-colour MIDI
// highlighting — incoming notes (window.__amorphProcessMidi, purple) vs generated
// output notes (window.__amorphProcessMidiOut, cyan). Single file, light DOM, cleanup.

const KNOBS = [
  { id: "param1", label: "Transpose", min: -24, max: 24, init: 0,   step: 1, fmt: v => (v > 0 ? "+" : "") + v.toFixed(0) + " st" },
  { id: "param3", label: "Velocity",  min: 0.1, max: 2,  init: 1,   step: 0, fmt: v => Math.round(v * 100) + "%" },
  { id: "param4", label: "Humanize",  min: 0,   max: 1,  init: 0,   step: 0, fmt: v => Math.round(v * 100) + "%" },
];
const CHORD = { id: "param2", labels: ["Off", "Octave", "Fifth", "Triad", "Seventh"], init: 3 };
const THRU = { id: "param5", init: 1 };
const LOW_NOTE = 48, N_KEYS = 25, BLACK = new Set([1, 3, 6, 8, 10]);

class MidiChordUI extends HTMLElement {
  constructor(pc) {
    super();
    this.pc = pc;
    this._set = new Map();
    this._cur = {};
    this._listener = null;
  }

  connectedCallback() {
    this.innerHTML = this.getHTML();
    KNOBS.forEach(k => this._wireKnob(k));
    this._wireChord();
    this._wireThru();

    this._listener = ({ endpointID, value }) => this._set.get(endpointID)?.(value, false);
    this.pc.addAllParameterListener(this._listener);
    this._set.forEach((_, id) => this.pc.requestParameterValue(id));

    window.__amorphProcessMidi = (msgs) => msgs.forEach(m => this._light(m, "in"));
    window.__amorphProcessMidiOut = (msgs) => msgs.forEach(m => this._light(m, "out"));
  }

  disconnectedCallback() {
    if (this._listener) this.pc.removeAllParameterListener(this._listener);
    delete window.__amorphProcessMidi;
    delete window.__amorphProcessMidiOut;
  }

  _light({ s, d1, d2 }, cls) {
    const type = s & 0xF0;
    const key = this.querySelector(`.key[data-note="${d1}"]`);
    if (!key) return;
    if (type === 0x90 && d2 > 0) key.classList.add(cls);
    else if (type === 0x80 || (type === 0x90 && d2 === 0)) key.classList.remove(cls);
  }

  _wireKnob(k) {
    const el = this.querySelector(`.knob[data-param="${k.id}"]`);
    const dial = el.querySelector(".dial"), val = el.querySelector(".val");
    const span = k.max - k.min;
    let dragging = false, startY = 0, startVal = k.init;
    const setValue = (v, notify) => {
      v = Math.min(k.max, Math.max(k.min, v));
      if (k.step) v = Math.round(v / k.step) * k.step;
      dial.style.setProperty("--norm", (v - k.min) / span);
      val.textContent = k.fmt(v);
      this._cur[k.id] = v;
      if (notify) this.pc.sendEventOrValue(k.id, v);
    };
    this._set.set(k.id, setValue);
    dial.addEventListener("pointerdown", e => {
      dragging = true; startY = e.clientY; startVal = this._cur[k.id] ?? k.init;
      dial.setPointerCapture(e.pointerId); e.preventDefault();
    });
    dial.addEventListener("pointermove", e => {
      if (dragging) setValue(startVal + ((startY - e.clientY) / 180) * span * (e.shiftKey ? 0.25 : 1), true);
    });
    const end = e => { dragging = false; dial.releasePointerCapture?.(e.pointerId); };
    dial.addEventListener("pointerup", end);
    dial.addEventListener("pointercancel", end);
    dial.addEventListener("dblclick", () => setValue(k.init, true));
    setValue(k.init, false);
  }

  _wireChord() {
    const wrap = this.querySelector(`.seg[data-param="${CHORD.id}"]`);
    const btns = [...wrap.querySelectorAll("button")];
    const setValue = (v, notify) => {
      const idx = Math.round(Math.min(4, Math.max(0, v)));
      btns.forEach((b, i) => b.classList.toggle("on", i === idx));
      if (notify) this.pc.sendEventOrValue(CHORD.id, idx);
    };
    this._set.set(CHORD.id, setValue);
    btns.forEach((b, i) => b.addEventListener("click", () => setValue(i, true)));
    setValue(CHORD.init, false);
  }

  _wireThru() {
    const btn = this.querySelector(`.thru[data-param="${THRU.id}"]`);
    let on = THRU.init >= 0.5;
    const setValue = (v, notify) => {
      on = v >= 0.5;
      btn.classList.toggle("on", on);
      btn.textContent = on ? "THRU ON" : "THRU OFF";
      if (notify) this.pc.sendEventOrValue(THRU.id, on ? 1 : 0);
    };
    this._set.set(THRU.id, setValue);
    btn.addEventListener("click", () => setValue(on ? 0 : 1, true));
    setValue(THRU.init, false);
  }

  getHTML() {
    const knob = k => `
      <div class="knob" data-param="${k.id}"><div class="dial"></div>
        <span class="val">--</span><span class="lbl">${k.label}</span></div>`;
    const seg = `<div class="seg" data-param="${CHORD.id}">
      ${CHORD.labels.map(l => `<button>${l}</button>`).join("")}</div>`;
    let keys = "";
    for (let i = 0; i < N_KEYS; i += 1) {
      const note = LOW_NOTE + i, black = BLACK.has(note % 12);
      keys += `<div class="key ${black ? "black" : "white"}" data-note="${note}"></div>`;
    }
    return `
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { overflow: hidden; margin: 0; }
  midi-chord-ui { display: block; width: 100%; height: 100%; overflow: hidden;
    background: linear-gradient(160deg, #1a1626 0%, #0c0a14 100%);
    color: #d2cde0; font-family: system-ui, sans-serif; user-select: none; -webkit-user-select: none; }
  midi-chord-ui .chassis { width: 100%; height: 100%; display: flex; flex-direction: column; padding: 18px 22px; }
  midi-chord-ui .hdr { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
  midi-chord-ui .name { font-size: 17px; font-weight: 800; letter-spacing: 3px; }
  midi-chord-ui .sub { font-size: 8px; letter-spacing: 2px; opacity: .45; text-transform: uppercase; }
  midi-chord-ui .legend { font-size: 8px; opacity: .55; }
  midi-chord-ui .legend b.p { color: #8B5CF6; } midi-chord-ui .legend b.c { color: #06B6D4; }
  midi-chord-ui .row { display: flex; gap: 22px; align-items: center; justify-content: center; flex: 1; }
  midi-chord-ui .knob { display: flex; flex-direction: column; align-items: center; gap: 6px; }
  midi-chord-ui .dial { width: 50px; height: 50px; border-radius: 50%; cursor: ns-resize;
    background: conic-gradient(#8B5CF6 calc(var(--norm,0) * 1turn), #2a2438 0);
    -webkit-mask: radial-gradient(circle at center, transparent 40%, #000 42%);
            mask: radial-gradient(circle at center, transparent 40%, #000 42%); }
  midi-chord-ui .val { font-size: 10px; font-variant-numeric: tabular-nums; }
  midi-chord-ui .lbl { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; opacity: .6; }
  midi-chord-ui .seg { display: flex; flex-direction: column; gap: 4px; }
  midi-chord-ui .seg button { font: inherit; font-size: 9px; letter-spacing: 1px; text-transform: uppercase;
    padding: 5px 12px; background: #181426; border: 1px solid #2e2742; color: #6a6188; border-radius: 4px; cursor: pointer; }
  midi-chord-ui .seg button.on { color: #c4b5fd; border-color: #8B5CF6; box-shadow: 0 0 8px rgba(139,92,246,.3); }
  midi-chord-ui .thru { padding: 8px 14px; font-size: 9px; font-weight: 800; letter-spacing: 1.5px; cursor: pointer;
    background: #141022; border: 1px solid #2e2742; color: #6a6188; border-radius: 6px; }
  midi-chord-ui .thru.on { color: #06B6D4; border-color: #06B6D4; box-shadow: 0 0 8px rgba(6,182,212,.3); }
  midi-chord-ui .keyboard { position: relative; height: 90px; display: flex; margin-top: 12px;
    background: #05060c; border-radius: 6px; padding: 4px; }
  midi-chord-ui .key.white { flex: 1; background: linear-gradient(#eef0f6, #c7cdd9); border-radius: 0 0 4px 4px; margin: 0 1px; }
  midi-chord-ui .key.black { height: 58%; background: linear-gradient(#262030, #100c18); border-radius: 0 0 3px 3px;
    margin: 0 -7px; z-index: 2; box-shadow: 0 0 0 1px #05060c; flex: 0 0 14px; }
  midi-chord-ui .key.in  { background: linear-gradient(#a78bfa, #6D28D9) !important; }
  midi-chord-ui .key.out { background: linear-gradient(#22d3ee, #0891B2) !important; }
  midi-chord-ui .key.in.out { background: linear-gradient(135deg, #8B5CF6, #06B6D4) !important; }
</style>
<div class="chassis">
  <div class="hdr">
    <div class="name">MIDI CHORD</div>
    <div class="legend"><b class="p">&#9632; input</b> &nbsp; <b class="c">&#9632; generated</b></div>
    <div class="sub">harmonizer &middot; dev-kit example</div>
  </div>
  <div class="row">
    ${KNOBS.map(knob).join("")}
    ${seg}
    <div class="thru" data-param="${THRU.id}">THRU ON</div>
  </div>
  <div class="keyboard">${keys}</div>
</div>`;
  }
}

const TAG = "midi-chord-ui";
if (!customElements.get(TAG)) customElements.define(TAG, MidiChordUI);

export default function createPatchView(patchConnection) {
  return new MidiChordUI(patchConnection);
}
