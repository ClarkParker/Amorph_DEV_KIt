#!/usr/bin/env python3
"""
cmajor_lint.py — static checks for Cmajor DSP against the documented hard rules.

Heuristic, regex-based. Catches the common compile-breakers and footguns described
in docs/02_DSP_CMAJOR.md and the official Amorph DSP prompts. It is intentionally
conservative (few false positives), so a clean run is NOT proof of correctness —
it only means none of the known traps were detected.

Rules live in PATTERN_RULES and the structural checks in check_*(); add or tweak
freely. Severities: "error" (will likely not compile / will misbehave) and
"warn" (suspicious / style).

Usage:
    python3 cmajor_lint.py MyPluginDSP.cmajor
    python3 cmajor_lint.py *.cmajor --strict     # warnings also cause exit code 1
Exit code: 0 = clean, 1 = findings (errors always; warnings only with --strict).
"""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

try:
    from cmajor_endpoints import parse_cmajor
except ImportError:  # allow running from another dir
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cmajor_endpoints import parse_cmajor

# --- simple line-pattern rules: (id, severity, regex, message) ---------------
PATTERN_RULES = [
    ("no-double", "error", re.compile(r"\bdouble\b"),
     "`double` does not exist in Cmajor — use `float64`."),
    ("no-cpp-types", "error",
     re.compile(r"\b(unsigned|uint32_t|uint64_t|int32_t|int64_t|size_t|constexpr|static)\b"),
     "C++ type/keyword not available in Cmajor."),
    ("no-prefix-incr", "warn", re.compile(r"(?<![\w)\]])(\+\+|--)\s*\w"),
     "Avoid prefix ++/-- — write `x += 1` (rule per official prompt; ++i in for-headers may compile)."),
    ("no-unsized-array", "error", re.compile(r"\bfloat(?:64)?\s*\[\s*\]"),
     "Arrays must be fixed-size (compile-time). No unsized `float[]`."),
    ("no-wrap-size", "error", re.compile(r"\.wrap\s*\("),
     "No runtime `.wrap(size)` — buffer sizes must be compile-time constants."),
    ("no-size-prop", "warn", re.compile(r"\.size\b"),
     "`.size` property is not available; use a known compile-time length."),
    ("hardcoded-sr", "warn", re.compile(r"\b(48000|44100|96000)\b"),
     "Hardcoded sample rate — use `processor.frequency` / `processor.period`."),
    ("std-random-call", "error", re.compile(r"std::random\s*\("),
     "`std::random(...)` is not a function — declare `std::random::RNG rng;` field."),
    ("reserved-name-decl", "error",
     re.compile(r"\b(?:float|float64|int|bool|var|let)\s+(?:input|output|stream)\b"),
     "`input`/`output`/`stream` are reserved — never use them as identifier names."),
]


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def lint_text(text: str, filename: str = "<text>") -> list[tuple]:
    findings: list[tuple] = []  # (severity, line, rule_id, message)

    # strip // line comments and /* */ blocks for pattern checks (keep length via spaces)
    def blank(m):
        return " " * len(m.group(0))
    code = re.sub(r"//[^\n]*", blank, text)
    code = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), code, flags=re.DOTALL)

    for rid, sev, rx, msg in PATTERN_RULES:
        for m in rx.finditer(code):
            findings.append((sev, _line_of(code, m.start()), rid, msg))

    findings += check_main_loop(code)
    findings += check_param_handlers(text)
    findings.sort(key=lambda f: (f[1], f[2]))
    return findings


def check_main_loop(code: str) -> list[tuple]:
    """Every void main() with a loop must write `out <-` and call `advance()`."""
    out = []
    if re.search(r"\bvoid\s+main\s*\(", code):
        if "advance()" not in code.replace(" ", "") and "advance ()" not in code:
            if re.search(r"advance\s*\(\s*\)", code) is None:
                out.append(("error", 0, "missing-advance",
                            "No `advance()` found — every main() loop iteration must call advance()."))
        # output stream present but no `out <-` ? (only meaningful for audio processors)
        if re.search(r"\boutput\s+stream\b", code) and re.search(r"\bout\s*<-", code) is None \
                and re.search(r"\w+\s*<-", code) is None:
            out.append(("warn", 0, "missing-out-write",
                        "Audio processor but no `out <- ...` write found in the file."))
    return out


def check_param_handlers(text: str) -> list[tuple]:
    """Each declared `input event` parameter should have an `event <id>` handler."""
    out = []
    info = parse_cmajor(text)
    for p in info["params"]:
        if p["kind"] != "event":
            continue  # value endpoints are read directly, no handler required
        if p["id"] in ("midiIn", "midiOut"):
            continue
        if re.search(r"\bevent\s+" + re.escape(p["id"]) + r"\s*\(", text) is None:
            out.append(("warn", 0, "missing-handler",
                        f"Parameter `{p['id']}` has no `event {p['id']} (...)` handler."))
    return out


def run(paths, strict=False) -> int:
    total_err = total_warn = 0
    for path in paths:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        findings = lint_text(text, str(path))
        if not findings:
            print(f"✓ {path}: clean")
            continue
        print(f"\n{path}:")
        for sev, line, rid, msg in findings:
            where = f":{line}" if line else ""
            mark = "ERROR" if sev == "error" else "warn "
            print(f"  {mark} {path}{where}  [{rid}] {msg}")
            if sev == "error":
                total_err += 1
            else:
                total_warn += 1
    print(f"\n{total_err} error(s), {total_warn} warning(s)")
    return 1 if (total_err or (strict and total_warn)) else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Lint Cmajor DSP code.")
    ap.add_argument("files", nargs="+", help=".cmajor file(s)")
    ap.add_argument("--strict", action="store_true", help="warnings also fail (exit 1)")
    args = ap.parse_args(argv)
    return run(args.files, strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
