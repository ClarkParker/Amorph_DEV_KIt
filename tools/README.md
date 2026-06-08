# Tools

Reusable, dependency-free **Python 3** tools for Amorph/Cmajor plugin work. Pure
standard library — no `pip install`, runs anywhere Python 3.8+ runs. Each tool is a
single file, usable from the CLI **and** importable as a module. They're built to be
**adapted**: the rules and regexes live in clearly marked lists near the top.

## The tools

| Tool | What it does |
|---|---|
| [`cmajor_endpoints.py`](cmajor_endpoints.py) | Parse a `.cmajor` file → parameters, audio I/O (main/sidechain by order), MIDI, meters; infer the plugin type. The "source of truth" reader the others build on. |
| [`cmajor_lint.py`](cmajor_lint.py) | Static checks for the Cmajor hard rules (no `double`, `out <-`+`advance()`, fixed-size arrays, reserved names, missing event handlers, hardcoded sample rate, …). |
| [`ui_lint.py`](ui_lint.py) | Static checks for the Amorph UI footguns (`import`/`attachShadow`, canvas resize in rAF, `window` pointer listeners, `vw/vh`, `backdrop-filter`, missing `// WINDOW SIZE` / cleanup / `requestParameterValue`, …). |
| [`check_sync.py`](check_sync.py) | Cross-check the DSP↔UI parameter contract: IDs present on both sides, ranges agree. |
| [`new_plugin.py`](new_plugin.py) | Scaffold a new plugin (DSP + UI + manifest) from a small JSON param spec. Generated code passes the linters out of the box. |
| [`params_from_dsp.py`](params_from_dsp.py) | The reverse of the scaffolder: emit a param-spec JSON **from** an existing DSP (to regenerate/migrate a UI or document a plugin). |
| [`manifest_check.py`](manifest_check.py) | Validate a `.cmajorpatch`: JSON, required keys, ID format, files exist, `view` size vs UI `// WINDOW SIZE`, `isInstrument`/`category` vs the DSP-inferred type. |
| [`preflight.py`](preflight.py) | Run the endpoint summary + both linters + sync check on a patch folder, with one verdict. |
| [`hooks/pre-commit`](hooks/pre-commit) | Git hook: run `preflight.py --strict` + `manifest_check.py` on every plugin touched by a commit. Install with [`hooks/install.sh`](hooks/install.sh). |

## Quick start

```bash
# 1. Scaffold a new FX plugin from a parameter spec
python3 tools/new_plugin.py tools/examples/params.example.json --out ./ExampleDrive

# 2. Run every check before compiling
python3 tools/preflight.py ./ExampleDrive

# Individual tools
python3 tools/cmajor_endpoints.py MyDSP.cmajor          # human summary
python3 tools/cmajor_endpoints.py MyDSP.cmajor --json   # feed other tools
python3 tools/cmajor_lint.py MyDSP.cmajor --strict
python3 tools/ui_lint.py MyUI.js
python3 tools/check_sync.py MyDSP.cmajor MyUI.js
```

`new_plugin.py` also works without a spec file:
```bash
python3 tools/new_plugin.py --type instrument --name "My Synth" --out ./MySynth
python3 tools/new_plugin.py --type midi       --name "My Arp"   --out ./MyArp
```

Reverse direction (regenerate a UI from an existing DSP):
```bash
python3 tools/params_from_dsp.py MyDSP.cmajor --out spec.json
python3 tools/new_plugin.py spec.json --out ./Regen --force
```

Validate a manifest, and install the pre-commit gate:
```bash
python3 tools/manifest_check.py path/to/Plugin.cmajorpatch
bash tools/hooks/install.sh        # runs the checks automatically on each commit
```

Exit codes: `0` = clean/consistent, `1` = findings. With `--strict`, warnings also
fail — handy for CI or a pre-commit hook.

## The param spec (single source of truth)

`new_plugin.py` reads a small JSON describing the plugin. The parameter list is the
DSP↔UI contract, so writing it once and generating both sides keeps them in sync:

```json
{
  "name": "My Drive", "id": "com.you.mydrive", "manufacturer": "You",
  "type": "fx",                          // fx | instrument | midi
  "width": 800, "height": 400,
  "params": [
    { "name": "Drive", "min": 0.0, "max": 1.0, "init": 0.3 },
    { "name": "Mix",   "min": 0.0, "max": 1.0, "init": 0.5, "unit": "%" }
  ]
}
```

See [`examples/params.example.json`](examples/params.example.json).

## How to adapt

- **Add/loosen a DSP rule:** edit `PATTERN_RULES` (and the `check_*` functions) in
  `cmajor_lint.py`. Each rule is `(id, severity, regex, message)`.
- **Add/loosen a UI rule:** edit `PATTERN_RULES` (present ⇒ flag) or `PRESENCE_RULES`
  (absent ⇒ flag) in `ui_lint.py`.
- **Match your declaration style:** the endpoint regexes are at the top of
  `cmajor_endpoints.py`.
- **Change generated code:** the DSP/UI/manifest templates are the `gen_*` functions
  in `new_plugin.py` — restyle the UI CSS, change the default layout, etc.

## Caveats

These are **heuristic** regex tools, not a Cmajor compiler or a JS parser. A clean run
means none of the *known* traps were detected — it is not proof of correctness. Always
compile and listen. False positives are possible; tune the rules to your codebase.

## Roadmap

- [x] `manifest_check.py`, `params_from_dsp.py`, and a pre-commit hook (done).
- [ ] A CI workflow that runs `preflight.py --strict` on `examples/` on every push.
- [ ] Optional `midi_preview.py` that packs/unpacks `(status<<16)|(d1<<8)|d2` short
  codes for quick UI testing.
