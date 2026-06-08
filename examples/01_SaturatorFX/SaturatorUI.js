// Saturator UI — single-file Web Component for the Amorph_FX example.
// WINDOW SIZE: 720x360
//
// Demonstrates: drag knobs (pointer events + setPointerCapture), a discrete toggle,
// echo-safe two-way binding via addAllParameterListener({endpointID,value}), and a
// canvas in/out level meter driven by DSP output events (addEndpointListener).
// Single file, no imports, light DOM, full cleanup.

const KNOBS = [
  { id: "param1", label: "Drive",  min: 0,   max: 1, init: 0.3, fmt: v => Math.round(v * 100) + "%" },
  { id: "param2", label: "Tone",   min: 0,   max: 1, init: 0.5, fmt: v => Math.round(v * 100) + "%" },
  { id: "param3", label: "Mix",    min: 0,   max: 1, init: 1.0, fmt: v => Math.round(v * 100) + "%" },
  { id: "param4", label: "Output", min: -24, max: 6, init: 0.0, fmt: v => v.toFixed(1) + " dB" },
];
const BYPASS = { id: "param5", label: "Bypass", init: 0 };

class SaturatorUI extends HTMLElement {
  constructor(pc) {
    super();
    this.pc = pc;
    this._set = new Map();      // id -> setValue(v, notify)
    this._listener = null;
    this._meterListeners = [];
    this._raf = null;
    this._levels = { in: 0, out: 0 };
  }

  connectedCallback() {
    this.innerHTML = this.getHTML();

    KNOBS.forEach(k => this._wireKnob(k));
    this._wireBypass(BYPASS);

    // host -> UI (Amorph payload is one object). setValue(notify=false) avoids echo.
    this._listener = ({ endpointID, value }) => this._set.get(endpointID)?.(value, false);
    this.pc.addAllParameterListener(this._listener);
    this._set.forEach((_, id) => this.pc.requestParameterValue(id));

    // DSP output meters
    const onIn  = v => { this._levels.in  = v; };
    const onOut = v => { this._levels.out = v; };
    this.pc.addEndpointListener("meterIn", onIn);
    this.pc.addEndpointListener("meterOut", onOut);
    this._meterListeners = [["meterIn", onIn], ["meterOut", onOut]];

    // size the meter canvas ONCE (never inside the rAF loop)
    this._canvas = this.querySelector(".meter canvas");
    this._canvas.width = this._canvas.offsetWidth || 200;
    this._canvas.height = this._canvas.offsetHeight || 120;

    const draw = () => { this._drawMeter(); this._raf = requestAnimationFrame(draw); };
    this._raf = requestAnimationFrame(draw);
  }

  disconnectedCallback() {
    if (this._listener) this.pc.removeAllParameterListener(this._listener);
    this._meterListeners.forEach(([id, fn]) => this.pc.removeEndpointListener(id, fn));
    if (this._raf) cancelAnimationFrame(this._raf);
  }

  _wireKnob(k) {
    const el = this.querySelector(`.knob[data-param="${k.id}"]`);
    const dial = el.querySelector(".dial");
    const val = el.querySelector(".val");
    const span = k.max - k.min;
    let dragging = false, startY = 0, startVal = k.init;

    const setValue = (v, notify) => {
      v = Math.min(k.max, Math.max(k.min, v));
      const norm = (v - k.min) / span;
      dial.style.setProperty("--norm", norm);
      val.textContent = k.fmt(v);
      this._current = this._current || {};
      this._current[k.id] = v;
      if (notify) this.pc.sendEventOrValue(k.id, v);
    };
    this._set.set(k.id, setValue);

    dial.addEventListener("pointerdown", e => {
      dragging = true; startY = e.clientY; startVal = (this._current || {})[k.id] ?? k.init;
      dial.setPointerCapture(e.pointerId);
      e.preventDefault();
    });
    dial.addEventListener("pointermove", e => {
      if (!dragging) return;
      const fine = e.shiftKey ? 0.25 : 1;
      setValue(startVal + ((startY - e.clientY) / 180) * span * fine, true);
    });
    const end = e => { dragging = false; dial.releasePointerCapture?.(e.pointerId); };
    dial.addEventListener("pointerup", end);
    dial.addEventListener("pointercancel", end);
    dial.addEventListener("dblclick", () => setValue(k.init, true));

    setValue(k.init, false);   // immediate first paint
  }

  _wireBypass(b) {
    const btn = this.querySelector(`.bypass[data-param="${b.id}"]`);
    let on = b.init >= 0.5;
    const setValue = (v, notify) => {
      on = v >= 0.5;
      btn.classList.toggle("on", on);
      btn.textContent = on ? "BYPASSED" : "ACTIVE";
      if (notify) this.pc.sendEventOrValue(b.id, on ? 1 : 0);
    };
    this._set.set(b.id, setValue);
    btn.addEventListener("click", () => setValue(on ? 0 : 1, true));
    setValue(b.init, false);
  }

  _drawMeter() {
    const c = this._canvas, ctx = c.getContext("2d");
    const W = c.width, H = c.height;
    ctx.clearRect(0, 0, W, H);
    const bar = (x, level, color) => {
      const h = Math.min(1, level * 1.6) * (H - 16);
      ctx.fillStyle = "#1a2030";
      ctx.fillRect(x, 8, 26, H - 16);
      ctx.fillStyle = color;
      ctx.fillRect(x, 8 + (H - 16 - h), 26, h);
    };
    bar(W / 2 - 34, this._levels.in, "#3a7bd5");
    bar(W / 2 + 8, this._levels.out, "#e0613a");
    ctx.fillStyle = "#67748a";
    ctx.font = "9px system-ui, sans-serif";
    ctx.fillText("IN", W / 2 - 30, H - 2);
    ctx.fillText("OUT", W / 2 + 8, H - 2);
  }

  getHTML() {
    const knob = k => `
      <div class="knob" data-param="${k.id}">
        <div class="dial"></div>
        <span class="val">--</span>
        <span class="lbl">${k.label}</span>
      </div>`;
    return `
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { overflow: hidden; margin: 0; }
  saturator-ui { display: block; width: 100%; height: 100%; overflow: hidden;
    background: radial-gradient(120% 120% at 50% 0%, #1b2030 0%, #0c0e15 100%);
    color: #cdd6e0; font-family: system-ui, sans-serif; user-select: none; -webkit-user-select: none; }
  saturator-ui .chassis { width: 100%; height: 100%; display: flex; flex-direction: column; padding: 18px 22px; }
  saturator-ui .hdr { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 14px; }
  saturator-ui .name { font-size: 17px; font-weight: 800; letter-spacing: 3px; }
  saturator-ui .sub { font-size: 8px; letter-spacing: 2px; opacity: .45; text-transform: uppercase; }
  saturator-ui .row { flex: 1; display: flex; align-items: center; gap: 26px; }
  saturator-ui .knobs { display: flex; gap: 22px; }
  saturator-ui .knob { display: flex; flex-direction: column; align-items: center; gap: 7px; }
  saturator-ui .dial { width: 58px; height: 58px; border-radius: 50%; cursor: ns-resize;
    background: conic-gradient(#e0613a calc(var(--norm,0) * 1turn), #232a3a 0);
    -webkit-mask: radial-gradient(circle at center, transparent 40%, #000 42%);
            mask: radial-gradient(circle at center, transparent 40%, #000 42%); }
  saturator-ui .val { font-size: 11px; font-variant-numeric: tabular-nums; }
  saturator-ui .lbl { font-size: 9px; letter-spacing: 1.5px; text-transform: uppercase; opacity: .6; }
  saturator-ui .meter { width: 150px; height: 130px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
  saturator-ui .meter canvas { width: 130px; height: 110px; background: #0b0e15; border-radius: 6px; border: 1px solid #1c2433; }
  saturator-ui .bypass { margin-left: auto; padding: 9px 16px; border-radius: 6px; cursor: pointer;
    font-size: 9px; font-weight: 800; letter-spacing: 1.5px; background: #141a26; border: 1px solid #243049; color: #5b6a85; }
  saturator-ui .bypass.on { color: #e0613a; border-color: #e0613a; box-shadow: 0 0 10px rgba(224,97,58,.3); }
</style>
<div class="chassis">
  <div class="hdr">
    <div class="name">SATURATOR</div>
    <div class="sub">4&times; oversampled &middot; dev-kit example</div>
  </div>
  <div class="row">
    <div class="knobs">${KNOBS.map(knob).join("")}</div>
    <div class="meter"><canvas></canvas></div>
    <div class="bypass" data-param="${BYPASS.id}">ACTIVE</div>
  </div>
</div>`;
  }
}

const TAG = "saturator-ui";
if (!customElements.get(TAG)) customElements.define(TAG, SaturatorUI);

export default function createPatchView(patchConnection) {
  return new SaturatorUI(patchConnection);
}
