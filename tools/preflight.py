#!/usr/bin/env python3
"""
preflight.py — run all checks on a plugin before compiling.

Given a patch directory (or explicit files), it finds the .cmajor DSP and .js UI,
prints an endpoint summary, then runs the DSP linter, UI linter, and DSP↔UI sync
check. One command, one verdict.

Usage:
    python3 preflight.py path/to/MyPlugin/        # a folder
    python3 preflight.py MyDSP.cmajor MyUI.js     # explicit files
    python3 preflight.py path/ --strict           # warnings also fail
Exit code: 0 = all clear, 1 = any error (or any warning with --strict).
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cmajor_endpoints import parse_file, _print_summary  # noqa: E402
import cmajor_lint  # noqa: E402
import ui_lint      # noqa: E402
import check_sync   # noqa: E402


def collect(paths):
    cmajor, js = [], []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            cmajor += sorted(str(x) for x in path.rglob("*.cmajor"))
            js += sorted(str(x) for x in path.rglob("*.js"))
        elif path.suffix == ".cmajor":
            cmajor.append(str(path))
        elif path.suffix == ".js":
            js.append(str(path))
    return cmajor, js


def hr(title):
    print("\n" + "=" * 60 + f"\n{title}\n" + "=" * 60)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Run all plugin pre-flight checks.")
    ap.add_argument("paths", nargs="+", help="patch folder(s) or explicit files")
    ap.add_argument("--strict", action="store_true", help="warnings also fail")
    args = ap.parse_args(argv)

    cmajor, js = collect(args.paths)
    if not cmajor and not js:
        print("No .cmajor or .js files found.")
        return 1

    rc = 0

    for c in cmajor:
        hr(f"ENDPOINTS · {c}")
        try:
            _print_summary(parse_file(c))
        except Exception as e:  # noqa: BLE001
            print(f"(could not parse: {e})")

    if cmajor:
        hr("DSP LINT")
        rc |= cmajor_lint.run(cmajor, strict=args.strict)
    if js:
        hr("UI LINT")
        rc |= ui_lint.run(js, strict=args.strict)
    if cmajor and js:
        hr("DSP ↔ UI SYNC")
        # pair the first DSP with the first UI (typical single-plugin layout)
        rc |= check_sync.main([cmajor[0], js[0]])

    hr("VERDICT")
    print("✓ All clear." if rc == 0 else "✗ Issues found — see above.")
    return rc


if __name__ == "__main__":
    sys.exit(main())
