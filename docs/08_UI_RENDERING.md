# 08 · Procedural / Photorealistic UI Techniques

This chapter catalogs techniques for rendering tactile, photorealistic controls
**procedurally** (no bitmap sprite-strips), so the UI scales cleanly to Retina/4K
and stays small.

> **Read the compatibility flags first.** Amorph UIs are **one self-contained `.js`
> file with no `import`/`require` and no external libraries**, and they talk to the
> DSP through the `patchConnection` bridge — **not** the Web Audio API. Several
> popular web-audio-UI techniques assume a bundler, npm packages, or
> `AudioWorkletNode`, and **do not apply** here. Each technique below is tagged:
>
> - ✅ **usable** — pure CSS/SVG/Canvas/vanilla JS, inline-able in one file.
> - ⚠️ **adapt** — usable only if you inline a vanilla implementation yourself.
> - ❌ **incompatible** — requires imports/bundler/external runtime or the Web Audio
>   graph; does not fit the Amorph single-file/bridge model.

## Techniques

### ✅ CSS conic-gradients for knob tracks and rings

`conic-gradient()` is a native, performant way to draw rotating potentiometer tracks,
LED rings, and radial value indicators. Drive it from a CSS custom property
(`--knob-value`) updated in JS. No dependencies.

### ✅ SVG filter lighting for switches/buttons/trimmers

Declarative 2D shading using the alpha channel as a bump map:
`<feSpecularLighting>` (with `surfaceScale`, `specularExponent` — high = chrome, low
= matte plastic), `<fePointLight>` for curved caps, `<feDistantLight>` for global
panel light, composited with `<feComposite operator="arithmetic">`. Animate with CSS
`transform: rotate()` while the light stays static. All inline SVG — no deps.

### ✅ Canvas 2D for meters / scopes / spectra

VU meters, vectorscopes, spectrum analysers: render on `<canvas>` in a
`requestAnimationFrame` loop. Analog-phosphor look via
`globalCompositeOperation = 'lighter'` (additive blending) + `shadowBlur`. Separate
static background layers from dynamic traces.
**Data source in Amorph:** a DSP `output event` endpoint via
`pc.addEndpointListener(...)` — **not** `AnalyserNode`/`AudioWorklet`. Run a DFT as a
host-rate DSP node (see [`06_OVERSAMPLING.md`](06_OVERSAMPLING.md)).

### ✅ Vanilla precision-input interaction model

The good interaction standards, implementable in plain JS:
- vertical/horizontal dragging only (no radial mouse tracking),
- modifier keys (Shift/Ctrl) for fine adjustment,
- mouse-wheel support and double-click reset,
- logarithmic scaling for frequency/dB parameters,
- `setPointerCapture` so a drag survives leaving the element.

### ⚠️ CSS Houdini Paint API (`conic`/metal simulation)

`CSS.paintWorklet.addModule(...)` runs paint logic off the main thread, which is
attractive for high-frequency knob repaints. **But** a paint worklet is loaded as a
*separate module URL* — which conflicts with the single-file/no-external-file rule
and may not be available in all of Amorph's WebViews. Treat as **adapt/avoid**:
prefer `conic-gradient` + Canvas. Only pursue worklets if you confirm your Amorph
build serves the worklet module and you accept a second file.

### ❌ WebGL / three.js / React Three Fiber PBR knobs

`MeshPhysicalMaterial` (metalness/roughness/anisotropy), IBL/HDR environment maps,
etc. give the most photorealistic large knobs — but require importing three.js and a
build step. **Incompatible** with the single-file/no-import rule. If you want a
metallic look, approximate it with layered `conic-gradient` + SVG specular lighting.

### ❌ React / headless knob libraries (`react-knob-headless`, etc.)

These assume React + npm + a bundler. **Incompatible.** Reimplement the *headless
idea* (separate event math from rendering) in vanilla JS inside your single file.

### ❌ `AudioWorkletNode` / Web Audio API metering

Sample-accurate ballistics inside an `AudioWorkletProcessor` is the standard
*browser* approach — but in Amorph the audio runs in the **Cmajor DSP**, not the Web
Audio graph. **Incompatible.** Compute RMS/peak in the DSP and emit via an
`output event`; render in Canvas.

## Layout metrics (universal, dependency-free)

- **8-point grid:** margins/padding/dimensions in multiples of 8px for clean scaling.
- **Golden ratio / Fibonacci** for panel segmentation and spacing hierarchy.

## Bottom line

Build photorealistic Amorph UIs from **CSS gradients + inline SVG filters + Canvas 2D
+ vanilla JS**, fed by the `patchConnection` bridge, all in one file. Reserve WebGL,
React, Houdini worklets, and Web Audio metering for environments without the
single-file constraint.
