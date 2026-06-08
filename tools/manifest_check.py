#!/usr/bin/env python3
"""
manifest_check.py — validate a .cmajorpatch manifest and its cross-references.

Checks the JSON itself, that the referenced DSP/UI files exist, that view.width/
height match the UI's `// WINDOW SIZE: WxH` comment, and that
`isInstrument`/`category` agree with the plugin type inferred from the DSP
endpoints (docs/10_PLUGIN_TYPES.md).

Usage:
    python3 manifest_check.py path/to/Plugin.cmajorpatch
    python3 manifest_check.py path/to/Plugin/            # finds the .cmajorpatch
Exit code: 0 = clean, 1 = error (or any warning with --strict).
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cmajor_endpoints import parse_file  # noqa: E402

RE_ID = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9]+)+$")
RE_WINDOW = re.compile(r"//\s*WINDOW\s*SIZE\s*:\s*(\d+)\s*x\s*(\d+)", re.IGNORECASE)
REQUIRED = ["CmajorVersion", "ID", "name", "source", "view"]


def find_manifest(p: Path) -> Path | None:
    if p.is_file():
        return p
    if p.is_dir():
        hits = sorted(p.glob("*.cmajorpatch"))
        return hits[0] if hits else None
    return None


def check(manifest_path: Path):
    findings = []  # (severity, message)

    def err(m):
        findings.append(("error", m))

    def warn(m):
        findings.append(("warn", m))

    try:
        man = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [("error", f"manifest is not valid JSON: {e}")], None

    for key in REQUIRED:
        if key not in man:
            err(f"missing required key: {key!r}")

    pid = man.get("ID", "")
    if pid and not RE_ID.match(pid):
        warn(f"ID {pid!r} is not reverse-DNS style (lowercase, dot-separated).")

    base = manifest_path.parent

    # source DSP file(s)
    sources = man.get("source", [])
    if isinstance(sources, str):
        sources = [sources]
    dsp_path = None
    for s in sources:
        sp = base / s
        if not sp.exists():
            err(f"source file not found: {s}")
        elif sp.suffix == ".cmajor" and dsp_path is None:
            dsp_path = sp

    # view / UI
    view = man.get("view", {})
    ui_path = None
    if not isinstance(view, dict) or "src" not in view:
        err("view.src missing — no UI module referenced.")
    else:
        ui_path = base / view["src"]
        if not ui_path.exists():
            err(f"view.src file not found: {view['src']}")
        w, h = view.get("width"), view.get("height")
        if not isinstance(w, int) or not isinstance(h, int) or w <= 0 or h <= 0:
            warn("view.width/height missing or not positive integers.")
        elif ui_path.exists():
            m = RE_WINDOW.search(ui_path.read_text(encoding="utf-8", errors="ignore"))
            if not m:
                warn(f"UI has no `// WINDOW SIZE: WxH` comment (manifest says {w}x{h}).")
            elif (int(m.group(1)), int(m.group(2))) != (w, h):
                warn(f"size mismatch: manifest {w}x{h} vs UI WINDOW SIZE {m.group(1)}x{m.group(2)}.")

    # category / isInstrument coherence
    cat = man.get("category")
    is_instr = man.get("isInstrument")
    if cat == "effect" and is_instr is True:
        warn('category "effect" but isInstrument is true.')
    if cat == "instrument" and is_instr is False:
        warn('category "instrument" but isInstrument is false.')

    # cross-check with the DSP-inferred type
    if dsp_path is not None:
        try:
            info = parse_file(dsp_path)
        except Exception as e:  # noqa: BLE001
            warn(f"could not parse DSP for type cross-check: {e}")
        else:
            ptype = info["pluginType"]
            inferred_instrument = ptype.startswith(("Audio Instrument", "MIDI Instrument"))
            if is_instr is not None and is_instr != inferred_instrument:
                warn(f"isInstrument={is_instr} but DSP looks like {ptype}.")
            if inferred_instrument and not info["midiIn"]:
                warn("instrument plugin but DSP has no `midiIn` endpoint.")

    return findings, man


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate a .cmajorpatch manifest.")
    ap.add_argument("path", help=".cmajorpatch file or a folder containing one")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    args = ap.parse_args(argv)

    mp = find_manifest(Path(args.path))
    if mp is None:
        print("No .cmajorpatch found.")
        return 1

    findings, man = check(mp)
    if man and not any(s == "error" for s, _ in findings):
        print(f"Manifest: {man.get('name', '?')}  ({man.get('ID', '?')})")
    errs = sum(s == "error" for s, _ in findings)
    warns = sum(s == "warn" for s, _ in findings)
    for sev, msg in findings:
        print(f"  {'ERROR' if sev == 'error' else 'warn '} {mp}: {msg}")
    if not findings:
        print(f"✓ {mp}: clean")
    else:
        print(f"\n{errs} error(s), {warns} warning(s)")
    return 1 if (errs or (args.strict and warns)) else 0


if __name__ == "__main__":
    sys.exit(main())
