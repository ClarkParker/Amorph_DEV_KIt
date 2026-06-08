#!/usr/bin/env python3
"""
check_sync.py — verify the DSP↔UI parameter contract.

The parameter list is the contract between DSP and UI (and saved presets). This tool
parses the DSP endpoints and scans the UI .js for the parameter IDs it references,
then reports mismatches:
  - parameters declared in the DSP but never used in the UI
  - parameter IDs used in the UI that don't exist in the DSP
  - (when the UI uses data-min/data-max) ranges that disagree with the DSP

Usage:
    python3 check_sync.py MyPluginDSP.cmajor MyPluginUI.js
Exit code: 0 = consistent, 1 = mismatch.
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

try:
    from cmajor_endpoints import parse_file
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cmajor_endpoints import parse_file

# Where a UI references a parameter id: sendEventOrValue('paramX'), data-param="paramX",
# requestParameterValue('paramX'), addParameterListener('paramX'), data-endpoint-id="paramX"
RE_UI_PARAM = re.compile(
    r"""(?:sendEventOrValue|requestParameterValue|addParameterListener|removeParameterListener)\s*\(\s*['"]([A-Za-z_]\w*)['"]"""
    r"""|data-param\s*=\s*['"]([A-Za-z_]\w*)['"]"""
    r"""|data-endpoint-id\s*=\s*['"]([A-Za-z_]\w*)['"]"""
)
RE_UI_RANGE = re.compile(
    r"""data-param\s*=\s*['"](?P<id>\w+)['"][^>]*?"""
    r"""(?:data-min\s*=\s*['"](?P<min>[-\d.]+)['"])?[^>]*?"""
    r"""(?:data-max\s*=\s*['"](?P<max>[-\d.]+)['"])?""",
    re.DOTALL,
)


# Fallback: any quoted paramN literal anywhere (registry-driven UIs build IDs from
# an array like { id: "param1", ... } rather than calling sendEventOrValue('param1')).
RE_UI_PARAM_LITERAL = re.compile(r"""['"](param\d+)['"]""")


def ui_param_ids(js: str) -> set[str]:
    ids = set()
    for m in RE_UI_PARAM.finditer(js):
        ids.add(next(g for g in m.groups() if g))
    ids |= set(RE_UI_PARAM_LITERAL.findall(js))
    return ids


def ui_ranges(js: str) -> dict:
    out = {}
    for m in RE_UI_RANGE.finditer(js):
        d = m.groupdict()
        if d["min"] is not None or d["max"] is not None:
            out[d["id"]] = (d["min"], d["max"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Check DSP↔UI parameter consistency.")
    ap.add_argument("dsp", help="DSP .cmajor file")
    ap.add_argument("ui", help="UI .js file")
    args = ap.parse_args(argv)

    info = parse_file(args.dsp)
    dsp_ids = {p["id"] for p in info["params"]}
    dsp_by_id = {p["id"]: p for p in info["params"]}
    js = Path(args.ui).read_text(encoding="utf-8", errors="ignore")
    ui_ids = ui_param_ids(js)

    missing_in_ui = sorted(dsp_ids - ui_ids)
    unknown_in_ui = sorted(ui_ids - dsp_ids)

    problems = 0
    print(f"DSP parameters: {len(dsp_ids)}   UI-referenced ids: {len(ui_ids)}")

    if missing_in_ui:
        problems += len(missing_in_ui)
        print("\n⚠ DSP parameters not referenced in the UI:")
        for i in missing_in_ui:
            print(f"   {i}  (\"{dsp_by_id[i]['name']}\")")
    if unknown_in_ui:
        problems += len(unknown_in_ui)
        print("\n✗ UI references parameters that don't exist in the DSP:")
        for i in unknown_in_ui:
            print(f"   {i}")

    # range cross-check (best-effort)
    for pid, (umin, umax) in ui_ranges(js).items():
        p = dsp_by_id.get(pid)
        if not p:
            continue
        if umin is not None and p["min"] is not None and float(umin) != float(p["min"]):
            problems += 1
            print(f"\n✗ Range mismatch on {pid}: DSP min={p['min']} vs UI data-min={umin}")
        if umax is not None and p["max"] is not None and float(umax) != float(p["max"]):
            problems += 1
            print(f"✗ Range mismatch on {pid}: DSP max={p['max']} vs UI data-max={umax}")

    if not problems:
        print("\n✓ DSP and UI parameter lists are consistent.")
        return 0
    print(f"\n{problems} mismatch(es) found.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
