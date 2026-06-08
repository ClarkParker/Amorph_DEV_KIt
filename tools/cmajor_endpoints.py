#!/usr/bin/env python3
"""
cmajor_endpoints.py — parse a Cmajor (.cmajor) file and extract its endpoints.

This is the "source of truth" reader the other tools build on. It pulls out:
  - parameters (event/value): id, display name, min/max/init/step/unit
  - audio input streams, in declaration order (first = MAIN, rest = sidechains)
  - audio output streams
  - MIDI in/out endpoints
  - other output events (meters, spectra, etc.)
and infers the Amorph plugin type (Audio FX / Audio Instrument / MIDI Instrument).

Pure standard library. Heuristic regex parsing — good enough for well-formed
plugin code, not a full Cmajor parser. Adapt the regexes below if your style differs.

Usage:
    python3 cmajor_endpoints.py MyPluginDSP.cmajor            # human summary
    python3 cmajor_endpoints.py MyPluginDSP.cmajor --json     # machine-readable
"""
from __future__ import annotations
import argparse
import json
import re
import sys
from pathlib import Path

# --- regexes (adapt here if your declaration style differs) ------------------

# input event/value <type> <name> [[ ...annotation... ]] ;
RE_PARAM = re.compile(
    r"\binput\s+(?P<kind>event|value)\s+(?P<type>[\w:]+(?:<\d+>)?)\s+"
    r"(?P<name>\w+)\s*(?:\[\[(?P<ann>.*?)\]\])?\s*;",
    re.DOTALL,
)
# input/output stream <type> <name> ;
RE_STREAM = re.compile(
    r"\b(?P<dir>input|output)\s+stream\s+(?P<type>[\w]+(?:<\d+>)?)\s+(?P<name>\w+)\s*;"
)
# input/output event std::midi::Message <name> ;
RE_MIDI = re.compile(
    r"\b(?P<dir>input|output)\s+event\s+std::midi::Message\s+(?P<name>\w+)\s*;"
)
# output event <type> <name> ;   (meters, spectra — non-midi)
RE_OUT_EVENT = re.compile(
    r"\boutput\s+event\s+(?P<type>[\w:]+(?:<\d+>)?)\s+(?P<name>\w+)\s*;"
)
# key: value  (value may be quoted, numeric, or a bare word like `true`)
RE_ANN_KV = re.compile(r"(\w+)\s*:\s*(\"[^\"]*\"|[-\w.]+)")


def channels_of(type_str: str) -> int:
    """float -> 1, float<2> -> 2, float<N> -> N."""
    m = re.search(r"<(\d+)>", type_str)
    return int(m.group(1)) if m else 1


def _num(v: str):
    try:
        return int(v) if re.fullmatch(r"-?\d+", v) else float(v)
    except ValueError:
        return v


def parse_annotation(ann: str | None) -> dict:
    if not ann:
        return {}
    out = {}
    for k, v in RE_ANN_KV.findall(ann):
        if v.startswith('"'):
            out[k] = v[1:-1]
        else:
            out[k] = _num(v)
    return out


def strip_comments(text: str) -> str:
    """Remove // line and /* */ block comments, preserving newlines/length so that
    reported line numbers (used by linters sharing this helper) stay accurate."""
    text = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), text)
    return text


def extract_main_block(text: str) -> str | None:
    """Return the body of the `[[ main ]]` processor/graph (brace-balanced), or None.
    The plugin's host-visible endpoints live on the main node; sub-processors
    (e.g. an internal metering processor) must not be counted as plugin I/O."""
    m = re.search(r"\b(?:processor|graph)\s+\w+\s*\[\[\s*main\s*\]\]", text)
    if not m:
        return None
    brace = text.find("{", m.end())
    if brace < 0:
        return None
    depth, i = 0, brace
    while i < len(text):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1:i]
        i += 1
    return text[brace + 1:]  # unbalanced — return the rest


def parse_cmajor(text: str) -> dict:
    """Parse Cmajor source text into an endpoints dict. If a `[[ main ]]` node
    exists, only its endpoints are considered (sub-processor I/O is internal).
    Names are de-duplicated; commented-out declarations are ignored."""
    text = strip_comments(text)
    text = extract_main_block(text) or text
    params, seen_p = [], set()
    for m in RE_PARAM.finditer(text):
        name = m.group("name")
        # MIDI message endpoints are event endpoints but NOT parameters — skip them.
        if "midi::Message" in m.group("type"):
            continue
        if name in seen_p:
            continue
        seen_p.add(name)
        ann = parse_annotation(m.group("ann"))
        params.append({
            "id": name,
            "kind": m.group("kind"),
            "type": m.group("type"),
            "name": ann.get("name", name),
            "min": ann.get("min"),
            "max": ann.get("max"),
            "init": ann.get("init"),
            "step": ann.get("step"),
            "unit": ann.get("unit"),
        })

    midi_in, midi_out = [], []
    for m in RE_MIDI.finditer(text):
        (midi_in if m.group("dir") == "input" else midi_out).append(m.group("name"))

    audio_in, audio_out, seen_s = [], [], set()
    for m in RE_STREAM.finditer(text):
        name, dir_ = m.group("name"), m.group("dir")
        if name in seen_s:
            continue
        seen_s.add(name)
        entry = {"name": name, "type": m.group("type"),
                 "channels": channels_of(m.group("type"))}
        (audio_in if dir_ == "input" else audio_out).append(entry)
    for i, a in enumerate(audio_in):
        a["index"] = i
        a["role"] = "main" if i == 0 else "sidechain"

    out_events, seen_e = [], set()
    midi_names = set(midi_in) | set(midi_out)
    for m in RE_OUT_EVENT.finditer(text):
        name = m.group("name")
        if name in seen_e or name in midi_names:
            continue
        seen_e.add(name)
        out_events.append({"name": name, "type": m.group("type")})

    info = {
        "params": params,
        "audioInputs": audio_in,
        "audioOutputs": audio_out,
        "midiIn": list(dict.fromkeys(midi_in)),
        "midiOut": list(dict.fromkeys(midi_out)),
        "outputEvents": out_events,
    }
    info["pluginType"] = infer_type(info)
    return info


def infer_type(info: dict) -> str:
    has_audio_in = len(info["audioInputs"]) > 0
    has_audio_out = len(info["audioOutputs"]) > 0
    has_midi_out = len(info["midiOut"]) > 0
    if has_midi_out and not has_audio_out:
        return "MIDI Instrument (Amorph_MIDI)"
    if has_midi_out and has_audio_out:
        return "MIDI Instrument (Amorph_MIDI, with audio out)"
    if not has_audio_in and has_audio_out:
        return "Audio Instrument (Amorph_Instrument)"
    if has_audio_in:
        return "Audio FX (Amorph_FX)"
    return "unknown"


def parse_file(path: str | Path) -> dict:
    return parse_cmajor(Path(path).read_text(encoding="utf-8", errors="ignore"))


def _print_summary(info: dict) -> None:
    print(f"Plugin type (inferred): {info['pluginType']}")
    print(f"\nParameters ({len(info['params'])}):")
    for p in info["params"]:
        rng = f"[{p['min']}..{p['max']}]" if p["min"] is not None else ""
        extra = " ".join(f"{k}={p[k]}" for k in ("init", "step", "unit") if p[k] is not None)
        print(f"  {p['id']:<14} {p['kind']:<6} \"{p['name']}\" {rng} {extra}".rstrip())

    if info["audioInputs"]:
        print("\nAudio inputs:")
        for a in info["audioInputs"]:
            print(f"  [{a['index']}] {a['name']:<10} {a['channels']}ch  ({a['role']})")
    if info["audioOutputs"]:
        print("\nAudio outputs:")
        for a in info["audioOutputs"]:
            print(f"  {a['name']:<10} {a['channels']}ch")
    if info["midiIn"] or info["midiOut"]:
        print(f"\nMIDI: in={info['midiIn'] or '-'}  out={info['midiOut'] or '-'}")
    if info["outputEvents"]:
        print("\nOutput events (meters/scopes):")
        for e in info["outputEvents"]:
            print(f"  {e['name']:<18} {e['type']}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Extract endpoints from a Cmajor file.")
    ap.add_argument("file", help="path to a .cmajor file")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON")
    args = ap.parse_args(argv)
    info = parse_file(args.file)
    if args.json:
        print(json.dumps(info, indent=2))
    else:
        _print_summary(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
