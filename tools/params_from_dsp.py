#!/usr/bin/env python3
"""
params_from_dsp.py — reverse of new_plugin.py: emit a param-spec JSON from a DSP.

Reads an existing .cmajor file and writes the spec format that new_plugin.py
consumes (name, type, params). Use it to:
  - regenerate or migrate a UI from the DSP that is the source of truth
  - document an existing plugin's parameter surface
  - seed a fresh scaffold from a hand-written DSP

Usage:
    python3 params_from_dsp.py MyPluginDSP.cmajor                 # spec to stdout
    python3 params_from_dsp.py MyPluginDSP.cmajor --out spec.json
    python3 params_from_dsp.py MyPluginDSP.cmajor | python3 new_plugin.py /dev/stdin --out ./Regen
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cmajor_endpoints import parse_file, strip_comments  # noqa: E402

TYPE_KEYWORD = {
    "Audio FX": "fx",
    "Audio Instrument": "instrument",
    "MIDI Instrument": "midi",
}


def type_keyword(plugin_type: str) -> str:
    for prefix, kw in TYPE_KEYWORD.items():
        if plugin_type.startswith(prefix):
            return kw
    return "fx"


def main_node_name(text: str) -> str | None:
    m = re.search(r"\b(?:processor|graph)\s+(\w+)\s*\[\[\s*main\s*\]\]", strip_comments(text))
    if m:
        return m.group(1)
    m = re.search(r"\b(?:processor|graph)\s+(\w+)", strip_comments(text))
    return m.group(1) if m else None


def build_spec(path: str) -> dict:
    info = parse_file(path)
    text = Path(path).read_text(encoding="utf-8", errors="ignore")
    name = main_node_name(text) or Path(path).stem
    # split CamelCase into words for a friendlier display name
    pretty = re.sub(r"(?<!^)(?=[A-Z])", " ", name).strip()

    params = []
    for p in info["params"]:
        entry = {"name": p["name"]}
        for k in ("min", "max", "init", "unit"):
            if p.get(k) is not None and p.get(k) != "":
                entry[k] = p[k]
        params.append(entry)

    return {
        "name": pretty,
        "id": "com.yourcompany." + re.sub(r"\W+", "", name.lower()),
        "type": type_keyword(info["pluginType"]),
        "width": 800,
        "height": 400,
        "params": params,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Emit a param-spec JSON from a DSP.")
    ap.add_argument("file", help=".cmajor file")
    ap.add_argument("--out", help="write to this file instead of stdout")
    args = ap.parse_args(argv)

    spec = build_spec(args.file)
    text = json.dumps(spec, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"✓ wrote {args.out}  ({len(spec['params'])} params, type '{spec['type']}')")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
