# 13 · The Amorph IDE & Workflow

Amorph is an AI-powered VST3/AU plugin that JIT-compiles Cmajor **inside the DAW** —
no external toolchain. It writes the DSP/UI for you from natural language; this kit
is about understanding and controlling what it produces.

> **Source:** Amorph's own product guide (*Settings → Developer → Copy Agent
> Instructions*), captured verbatim in
> [`../reference/amorph/PRODUCT_GUIDE.md`](../reference/amorph/PRODUCT_GUIDE.md).
> The load-bearing facts are summarised here; volatile details (model list, ports,
> paths) are point-in-time — check the verbatim copy for the snapshot.

## The three variants (and a clarification)

| Variant | Signal path |
|---|---|
| **Amorph FX** | audio in → processed audio out |
| **Amorph Instrument** | MIDI in → audio out |
| **Amorph MIDI** | MIDI in → MIDI out **+ silent audio** |

The product guide states the **MIDI variant outputs silent audio** alongside its MIDI
out — consistent with the tested observation that a MIDI plugin *can* carry an audio
output. The full, tested I/O matrix (including the FX MIDI-in and the sidechain
inputs the product guide doesn't mention) is in
[`10_PLUGIN_TYPES.md`](10_PLUGIN_TYPES.md). Load the correct variant for your use
case — you can't turn an FX into an instrument after the fact.

## Parameter count: 50 documented, more works

> *"Up to 50 dynamic parameters with names, ranges, and units."* — product guide

Parameters declared in the DSP become automatable DAW parameters. 50 is the
**documented, safe** number — but **not a hard cap**: a real shipped plugin runs
**80+** parameters fine (**[field-tested]**). Stay under 50 for guaranteed support;
go higher only if you've verified it in your build. The linter warns (not errors)
above 50. The parameter-number contract still rules — see
[`04_PARAMETERS.md`](04_PARAMETERS.md).

## The three modes

- **Build** — the workspace. Left: code editor with three tabs — **DSP** (Cmajor),
  **UI** (your single-file JS component), **Manifest** (read-only). Right: the AI
  chat/agent panel. Bottom: the **COMPILE** button (instant Cmajor JIT). A **Lock**
  button can password-protect the source.
- **Play** — the performance view: your custom UI (or auto-generated dials if none),
  a preset strip, and an optional AI prompt bar. A black screen here means *no custom
  UI exists yet* — go to Build and ask for one, or drop in a UI from this kit.
- **Explore** — community patches (browse / install / publish / vote); needs a free
  account.

## Settings that change the generated code

When you let Amorph's own AI write DSP, these knobs (Settings → Advanced) matter:

| Setting | Default | Raise it for | Cost of raising |
|---|---|---|---|
| Temperature | 0.20 | creative exploration (0.40–0.60) | more compile errors |
| Max tokens | 4096 | complex graphs / synths (8192+), full UI rewrites (16384+) | slower, pricier |
| Agent turns | 20 | multi-step builds | more tool-call rounds |
| Auto-apply DSP | — | OFF lets you review a diff before it goes live (keep OFF while learning) | — |

For predictable DSP, keep temperature low. The kit's own system prompts
([`../ai/`](../ai/)) push toward compilable output regardless of provider.

## Presets & state

- User presets are **`.amorph`** files in
  `~/Library/Presets/Artists_in_DSP/AMORPH/`. Each preset bundles **DSP code, UI
  code, parameter values, parameter names/ranges, and metadata** — the whole patch,
  not just values.
- **Snapshots** are an in-session undo history (up to 30 states).
- Because a preset stores the *code*, "preset compatibility" in this kit's sense
  (the param-number contract) matters most when you ship a plugin others build on,
  or reload a DAW project that saved parameter automation. See
  [`04_PARAMETERS.md`](04_PARAMETERS.md) → "Presets & state".

## Driving Amorph from an external agent (MCP / CLI / HTTP)

Amorph runs a **local HTTP JSON-RPC server** (`localhost`, port **7331–7399**), so an
external coding agent can read the current code, edit it, compile, and read errors —
the same loop the in-app agent runs, but from your own tools.

- **MCP agents** (Claude Desktop, Claude Code CLI, VS Code Copilot, Cursor, Windsurf,
  Continue.dev): *Settings → Developer → MCP Connection → Copy Config*, paste into the
  agent's config. A bridge script translates MCP stdio ↔ the HTTP server.
- **CLI** (Amorph ships `scripts/amorph_cli.py`):
  ```bash
  python3 scripts/amorph_cli.py tools                       # list available tools
  python3 scripts/amorph_cli.py call read_code '{"target":"dsp"}'
  python3 scripts/amorph_cli.py call get_error '{}'
  python3 scripts/amorph_cli.py --variant fx status
  ```
- **Direct HTTP**: POST JSON-RPC to `http://localhost:<port>/mcp` with the Bearer
  token from the registry file.

This is how you combine **this kit's offline tools** with a **live Amorph session**:
e.g. pull the current DSP with `read_code`, run `tools/cmajor_lint.py` / `preflight.py`
on it locally, and feed fixes back. (The kit's tools work on files; the Amorph bridge
gives you the files from a running instance.)

## Useful AI-panel features

- **Copy Prompt** exports the full structured prompt (system context + request +
  current code) for pasting into an external LLM — pair it with the kit's
  [`ai/amorph_official/`](../ai/amorph_official/) prompts.
- **Copy Agent Instructions** (Developer) is exactly the product guide captured here —
  re-run it after an Amorph update to refresh
  [`../reference/amorph/PRODUCT_GUIDE.md`](../reference/amorph/PRODUCT_GUIDE.md).
- **Voice input** (mic) always needs an **OpenAI key** (Whisper), even when another
  provider generates the code.

## Troubleshooting (from the product guide)

| Symptom | Cause / fix |
|---|---|
| No sound (FX) | needs audio input — check DAW routing |
| No sound (Instrument) | needs MIDI input — add a clip / connect a keyboard |
| Black screen in Play | no custom UI yet — build one (Build mode) |
| Compile error | read the log; fix per [`09_PITFALLS_CHECKLIST.md`](09_PITFALLS_CHECKLIST.md) |
| Voice input dead | needs an OpenAI key regardless of code provider |
| Settings hidden | some DAWs put it behind the main window |
