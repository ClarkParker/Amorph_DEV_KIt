#!/usr/bin/env python3
"""
ui_lint.py — static checks for an Amorph plugin UI (single-file JS Web Component).

Catches the Amorph WebView footguns documented in docs/03_UI_WEBCOMPONENT.md,
docs/05_AMORPH_NOTES.md, docs/07_SCALING.md and the official Amorph UI prompt.
Heuristic and conservative; a clean run is not proof of correctness.

Rules are in PATTERN_RULES (present = flagged) and PRESENCE_RULES (absent = flagged).
Adapt freely. Severities: "error" / "warn".

Usage:
    python3 ui_lint.py MyPluginUI.js
    python3 ui_lint.py ui/*.js --strict
Exit code: 0 = clean, 1 = findings (errors always; warnings only with --strict).
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

# present in the file => flag it
PATTERN_RULES = [
    ("no-import", "error", re.compile(r"^\s*import\s.+from\s|require\s*\("),
     "Single-file rule: no `import`/`require`. Inline everything."),
    ("no-shadow-dom", "error", re.compile(r"\battachShadow\s*\("),
     "Do not use Shadow DOM — build with `this.innerHTML` (light DOM)."),
    ("canvas-resize-client", "warn",
     re.compile(r"\.(width|height)\s*=\s*[\w.]*\.(clientWidth|clientHeight)\b"),
     "Sizing a canvas from client size can cause an infinite layout-growth loop in a rAF — size once via offsetWidth/offsetHeight or ResizeObserver."),
    ("window-pointer-listener", "warn",
     re.compile(r"window\.addEventListener\s*\(\s*['\"](pointermove|pointerup)['\"]"),
     "Don't attach pointermove/up to window — use element + setPointerCapture (and it can't be cleaned up)."),
    ("no-backdrop-filter", "warn", re.compile(r"backdrop-filter"),
     "`backdrop-filter` glitches in Amorph's WebView."),
    ("no-vw-vh", "warn", re.compile(r"\b\d+(?:\.\d+)?v[wh]\b"),
     "`vw`/`vh` don't reliably track the plugin window — use % or px."),
    ("transform-scale", "warn", re.compile(r"transform[^;]*scale\s*\("),
     "Scaling with transform:scale() misplaces overlays — prefer CSS `zoom` (docs/07)."),
    ("sendMIDI-missing", "error", re.compile(r"\.sendMIDI\s*\("),
     "`sendMIDI(...)` does not exist — use `sendMIDIInputEvent('midiIn', code)`."),
]

# absent from the file => flag it. (id, severity, regex, message, guard)
# guard: only check the rule when this regex IS present (None = always).
PRESENCE_RULES = [
    ("has-default-export", "error", re.compile(r"export\s+default\b"),
     "Missing `export default` — the host calls the module's default export.", None),
    ("has-window-size", "warn", re.compile(r"//\s*WINDOW\s*SIZE", re.IGNORECASE),
     "Missing `// WINDOW SIZE: WxH` comment on line 2 (Amorph convention).", None),
    ("has-disconnected", "warn", re.compile(r"disconnectedCallback\s*\("),
     "Has connectedCallback but no disconnectedCallback — listeners/RAF will leak.",
     re.compile(r"connectedCallback\s*\(")),
    ("has-request-value", "warn", re.compile(r"requestParameterValue\s*\("),
     "Adds a parameter listener but never calls requestParameterValue — controls show stale defaults.",
     re.compile(r"add(All)?ParameterListener\s*\(")),
    ("has-overflow-hidden", "warn", re.compile(r"overflow\s*:\s*hidden"),
     "No `overflow: hidden` on html/body — WebView default body margin causes a scrollbar.", None),
]


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def lint_text(text: str) -> list[tuple]:
    findings = []
    for rid, sev, rx, msg in PATTERN_RULES:
        for m in rx.finditer(text):
            findings.append((sev, _line_of(text, m.start()), rid, msg))
    for rid, sev, rx, msg, guard in PRESENCE_RULES:
        if guard is not None and not guard.search(text):
            continue
        if not rx.search(text):
            findings.append((sev, 0, rid, msg))
    findings.sort(key=lambda f: (f[1], f[2]))
    return findings


def run(paths, strict=False) -> int:
    total_err = total_warn = 0
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        findings = lint_text(text)
        if not findings:
            print(f"✓ {path}: clean")
            continue
        print(f"\n{path}:")
        for sev, line, rid, msg in findings:
            where = f":{line}" if line else ""
            mark = "ERROR" if sev == "error" else "warn "
            print(f"  {mark} {path}{where}  [{rid}] {msg}")
            total_err += sev == "error"
            total_warn += sev == "warn"
    print(f"\n{total_err} error(s), {total_warn} warning(s)")
    return 1 if (total_err or (strict and total_warn)) else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lint an Amorph plugin UI (.js).")
    ap.add_argument("files", nargs="+", help="UI .js file(s)")
    ap.add_argument("--strict", action="store_true", help="warnings also fail (exit 1)")
    args = ap.parse_args(argv)
    return run(args.files, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
