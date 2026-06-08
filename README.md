# Amorph / Cmajor Plugin Dev Kit

A practical, **verified** reference for building audio and instrument plugins for the
**Amorph** host with **Cmajor** DSP and a single-file **JavaScript Web Component** UI.

This kit is a public, project-independent knowledge base. It collects hard-won
lessons from real plugin development and checks every claim against the official
Cmajor sources. Older, contradictory notes have been reconciled — see
[`STATUS.md`](STATUS.md) for what was verified, what was corrected, and what is
still marked *unverified*.

> **Scope note.** This is a *documentation-first* kit (the scaffold). Runnable
> templates and worked examples are being added incrementally — see the roadmap
> at the bottom.

---

## The architecture in one paragraph

An Amorph plugin has three decoupled layers. The **DSP** is one Cmajor
`processor`/`graph`. The **UI** is a single self-contained `.js` Web Component.
A small **manifest** (`.cmajorpatch`) links them and sets the window size. DSP and
UI never share memory and never call each other — they communicate only through
the **parameter bridge** (`patchConnection`): the UI writes with
`sendEventOrValue`, reads with `addParameterListener` + `requestParameterValue`,
and receives meters/scopes with `addEndpointListener`. The contract between the two
sides is the parameter list: parameters are named `param1..paramN` and the
**number is the contract** — renaming or renumbering after wiring breaks saved
presets.

---

## What's in the kit

```
STATUS.md                  Verification log: sources, what was confirmed/corrected, open questions.
docs/
  01_ARCHITECTURE.md       The three layers, the manifest, the bridge.
  02_DSP_CMAJOR.md         Writing the DSP: skeleton, parameters, sample rate, building blocks.
  03_UI_WEBCOMPONENT.md    Writing the UI: the single-file contract, the bridge, lifecycle, cleanup.
  04_PARAMETERS.md         Parameter design: ranges, naming, formatting, pan law, bypass.
  05_AMORPH_NOTES.md       Amorph-specific WebView behaviour you must know.
  06_OVERSAMPLING.md       Per-node oversampling in Cmajor (verified) and when to use it.
  07_SCALING.md            The CSS-`zoom` scaling method + host-wrapper fixes (battle-tested).
  08_UI_RENDERING.md       Procedural/photoreal UI techniques — with Amorph compatibility caveats.
  09_PITFALLS_CHECKLIST.md Quick pitfalls lookup + pre-flight and test checklists.
ai/
  DSP_SYSTEM_PROMPT.md     System prompt to hand an AI assistant before DSP coding.
  UI_SYSTEM_PROMPT.md      System prompt to hand an AI assistant before UI coding.
reference/
  airwindows/README.md     How to use the Airwindows plugins as a DSP reference (clone, don't vendor).
templates/                 (roadmap) Copy-to-start plugin template: DSP + UI + manifest.
```

---

## Golden rules (the short list)

**DSP (Cmajor)**
- One top-level `processor`/`graph`. Parameters are `input event`/`input value`
  endpoints named `param1..paramN`, each with a `[[ name: ... ]]` annotation and the
  3-step pattern (endpoint → state variable → `event` handler).
- Never use the reserved identifiers `input`, `output`, `stream` as names.
- There is no `double` — use `float64`. `sin`/`cos`/`pow`/`exp`/`sqrt`/`tanh` return
  `float64`; cast back with `float(...)`.
- Every `main()` loop iteration must write `out <-` and then call `advance()`,
  unconditionally.
- Read the sample rate from `processor.frequency` / `processor.period` — never hardcode.
- Initialise all float state; clamp filter cutoffs below Nyquist.
- **Oversampling works** via graph-node oversampling: `node core = MyCore * 4;`
  (sinc resampling is automatic). See [`docs/06_OVERSAMPLING.md`](docs/06_OVERSAMPLING.md).

**UI (JavaScript Web Component)**
- One self-contained `.js` file. **No `import`/`require`, no ES-module
  dependencies, no CDN, no external libraries.** Inline all CSS, HTML and logic.
- `export default function createPatchView(patchConnection)` → create the element,
  hand it the connection, return it. Register with `customElements.define` (guarded).
- Two-way bind every control and add **echo-loop protection** so the DSP's echo
  doesn't fight a live drag.
- Scale with CSS **`zoom`** on a fixed-size chassis — never `transform: scale()`.
  See [`docs/07_SCALING.md`](docs/07_SCALING.md).
- Avoid `backdrop-filter` and `vw`/`vh` in Amorph. Clean up every listener /
  observer / RAF in `disconnectedCallback`.

---

## Working with the Cmajor source

Amorph runs without general web access — the reliable way to pull in external
material is `git clone`. To study the bridge API or the language in depth, clone
the official repository and read `javascript/cmaj_api/` and `docs/`:

```
git clone https://github.com/cmajor-lang/cmajor
```

Do **not** import those files into an Amorph UI (the single-file rule) — they are
for reference only.

---

## Verification standard

Every factual claim in this kit is tagged where it matters:

- **[verified]** — confirmed against the official Cmajor source or docs (file/line cited in `STATUS.md`).
- **[field-tested]** — observed repeatedly in real Amorph plugins, not in the official spec.
- **[unverified]** — plausible but not yet confirmed; treat with care.

If you find a claim that no longer holds, open an issue or PR and update `STATUS.md`.

---

## Roadmap

- [x] Scaffold: verified core documentation, AI prompts, Airwindows reference.
- [ ] `templates/Plugin/` — minimal copy-to-start DSP + UI + manifest.
- [ ] `examples/` — a stereo saturator (oversampled) and a small synth.
- [ ] A spectrum/meter output-event pattern with a Canvas visualiser.
- [ ] CI sanity check that documented Cmajor snippets compile.

## License

MIT — see [`LICENSE`](LICENSE). Third-party references (e.g. Airwindows) keep their
own licenses; this kit only points to them, it does not vendor their source.
