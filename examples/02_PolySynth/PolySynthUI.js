// PolySynth UI — single-file Web Component for the Amorph_Instrument example.
// WINDOW SIZE: 760x380
//
// Demonstrates: knobs (pointer drag + setPointerCapture), a playable on-screen
// keyboard that injects notes via sendMIDIInputEvent("midiIn", ...), and incoming
// MIDI highlighting via the Amorph window.__amorphProcessMidi hook.
// Single file, no imports, light DOM, full cleanup.

const KNOBS = [
  { id: "param1", label: "Tune",    min: -24, max: 24,   init: 0,    fmt: v => v.toFixed(0) + " st" },
  { id: "param2", label: "Attack",  min: 1,   max: 2000, init: 8,    fmt: v => v.toFixed(0) + " ms" },
  { id: "param3", label: "Release", min: 1,   max: 4000, init: 400,  fmt: v => v.toFixed(0) + " ms" },
  { id: "param4", label: "Cutoff",  min: 0,   max: 1,    init: 0.7,  fmt: v => Math.round(v * 100) + "%" },
  { id: "param5", label: "Drive",   min: 0,   max: 1,    init: 0.15, fmt: v => Math.round(v * 100) + "%" },
  { id: "param6", label: "Level",   min: -24, max: 6,    init: -6,   fmt: v => v.toFixed(1) + " dB" },
];
const LOW_NOTE = 48;     // C3
const N_KEYS = 25;       // two octaves + 1
const BLACK = new Set([1, 3, 6, 8, 10]);

class PolySynthUI extends HTMLElement {
  constructor(pc) {
    super();
    this.pc = pc;
    this._set = new Map();
    this._cur = {};
    this._listener = null;
    this._held = new Set();
  }

  connectedCallback() {
    this.innerHTML = this.getHTML();
    KNOBS.forEach(k => this._wireKnob(k));
    this._wireKeyboard();

    this._listener = ({ endpointID, value }) => this._set.get(endpointID)?.(value, false);
    this.pc.addAllParameterListener(this._listener);
    this._set.forEach((_, id) => this.pc.requestParameterValue(id));

    // incoming MIDI -> highlight keys (Amorph hook; assign our own, clean up later)
    window.__amorphProcessMidi = (messages) => {
      messages.forEach(({ s, d1, d2 }) => {
        const type = s & 0xF0;
        if (type === 0x90 && d2 > 0) this._light(d1, true);
        else if (type === 0x80 || (type === 0x90 && d2 === 0)) this._light(d1, false);
      });
    };
  }

  disconnectedCallback() {
    if (this._listener) this.pc.removeAllParameterListener(this._listener);
    delete window.__amorphProcessMidi;
  }

  _wireKnob(k) {
    const el = this.querySelector(`.knob[data-param="${k.id}"]`);
    const dial = el.querySelector(".dial");
    const val = el.querySelector(".val");
    const span = k.max - k.min;
    let dragging = false, startY = 0, startVal = k.init;

    const setValue = (v, notify) => {
      v = Math.min(k.max, Math.max(k.min, v));
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

  _wireKeyboard() {
    this.querySelectorAll(".key").forEach(key => {
      const note = parseInt(key.dataset.note, 10);
      key.addEventListener("pointerdown", e => {
        key.setPointerCapture(e.pointerId); e.preventDefault();
        this._noteOn(note);
      });
      const off = () => this._noteOff(note);
      key.addEventListener("pointerup", off);
      key.addEventListener("pointercancel", off);
      key.addEventListener("pointerleave", () => { if (this._held.has(note)) this._noteOff(note); });
    });
  }

  _noteOn(note) {
    if (this._held.has(note)) return;
    this._held.add(note);
    this.pc.sendMIDIInputEvent("midiIn", (0x90 << 16) | (note << 8) | 100);
    this._light(note, true);
  }
  _noteOff(note) {
    if (!this._held.has(note)) return;
    this._held.delete(note);
    this.pc.sendMIDIInputEvent("midiIn", (0x80 << 16) | (note << 8) | 0);
    this._light(note, false);
  }
  _light(note, on) {
    const key = this.querySelector(`.key[data-note="${note}"]`);
    if (key) key.classList.toggle("on", on);
  }

  getHTML() {
    const knob = k => `
      <div class="knob" data-param="${k.id}">
        <div class="dial"></div><span class="val">--</span><span class="lbl">${k.label}</span>
      </div>`;
    let keys = "";
    for (let i = 0; i < N_KEYS; i += 1) {
      const note = LOW_NOTE + i;
      const black = BLACK.has(note % 12);
      keys += `<div class="key ${black ? "black" : "white"}" data-note="${note}"></div>`;
    }
    return `
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { overflow: hidden; margin: 0; }
  poly-synth-ui { display: block; width: 100%; height: 100%; overflow: hidden;
    background: linear-gradient(160deg, #161a26 0%, #0b0d14 100%);
    color: #cdd6e0; font-family: system-ui, sans-serif; user-select: none; -webkit-user-select: none; }
  poly-synth-ui .chassis { width: 100%; height: 100%; display: flex; flex-direction: column; padding: 18px 22px; }
  poly-synth-ui .hdr { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
  poly-synth-ui .name { font-size: 17px; font-weight: 800; letter-spacing: 3px; }
  poly-synth-ui .sub { font-size: 8px; letter-spacing: 2px; opacity: .45; text-transform: uppercase; }
  poly-synth-ui .knobs { display: flex; gap: 22px; justify-content: center; flex: 1; align-items: center; }
  poly-synth-ui .knob { display: flex; flex-direction: column; align-items: center; gap: 6px; }
  poly-synth-ui .dial { width: 52px; height: 52px; border-radius: 50%; cursor: ns-resize;
    background: conic-gradient(#5b8def calc(var(--norm,0) * 1turn), #232a3a 0);
    -webkit-mask: radial-gradient(circle at center, transparent 40%, #000 42%);
            mask: radial-gradient(circle at center, transparent 40%, #000 42%); }
  poly-synth-ui .val { font-size: 10px; font-variant-numeric: tabular-nums; }
  poly-synth-ui .lbl { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; opacity: .6; }
  poly-synth-ui .keyboard { position: relative; height: 96px; display: flex; margin-top: 12px;
    background: #05070c; border-radius: 6px; padding: 4px; }
  poly-synth-ui .key.white { flex: 1; background: linear-gradient(#f4f6fb, #cfd6e2); border-radius: 0 0 4px 4px;
    margin: 0 1px; cursor: pointer; }
  poly-synth-ui .key.white.on { background: linear-gradient(#9bd0ff, #5b8def); }
  poly-synth-ui .key.black { width: 0; height: 58%; background: linear-gradient(#2a3040, #11141d);
    border-radius: 0 0 3px 3px; margin: 0 -7px; z-index: 2; position: relative; cursor: pointer;
    box-shadow: 0 0 0 1px #05070c; flex: 0 0 14px; }
  poly-synth-ui .key.black.on { background: linear-gradient(#5b8def, #2a4a8f); }
</style>
<div class="chassis">
  <div class="hdr"><div class="name">POLYSYNTH</div><div class="sub">16-voice &middot; dev-kit example</div></div>
  <div class="knobs">${KNOBS.map(knob).join("")}</div>
  <div class="keyboard">${keys}</div>
</div>`;
  }
}

const TAG = "poly-synth-ui";
if (!customElements.get(TAG)) customElements.define(TAG, PolySynthUI);

export default function createPatchView(patchConnection) {
  return new PolySynthUI(patchConnection);
}
