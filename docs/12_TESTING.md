# 12 · Testing & Debugging

Cmajor ships a real unit-test runner (`cmaj test`) and a scripted test-file format.
This kit uses it — [`../tests/Cookbook.cmajtest`](../tests/Cookbook.cmajtest) is a
working, passing example. Everything below is **[compiler-verified]** against
`cmaj 1.0.3159` unless noted.

## Running tests

```bash
cmaj test tests/Cookbook.cmajtest    # one file
cmaj test tests/                     # a folder (recursive)
```

Useful switches: `--threads=n`, `--testToRun=n`, `--iterations=n`,
`--xmlOutput=file` (JUnit XML — for CI).

## The `.cmajtest` format in 60 seconds

A test file is split into blocks by lines starting with `##`, each naming a test
function that receives the block below it. Anything before the first `##` is plain
JavaScript (for custom test helpers).

```text
## global ("../cookbook/Cookbook.cmajor")   <- prepend a file/folder to every test

## testFunction()
bool myTest()   { return 1 + 1 == 2; }      <- every no-arg bool function runs;
                                               any `false` fails the test

## testCompile()
processor P { ... }                          <- just has to compile

## expectError ("2:9: error: Cannot find symbol 'XX'")
void f (XX& x) {}                            <- passes only if THIS error occurs

## testProcessor()
processor P                                  <- runs the processor; it emits
{                                               1 = pass, 0 = fail, -1 = done
    output stream int out;
    void main() { out <- 1; advance(); out <- -1; advance(); }
}
```

- `## global` makes a shared chunk (or an external `.cmajor` file) visible to every
  test in the file — that is how the kit tests the cookbook without copying it.
- `## disabled testFunction()` skips a test but counts it as disabled.
- `## runScript()` renders a processor against golden-data files (`.json` for
  events/values, `.wav` for streams) — for regression-testing full effects. Options:
  `frequency`, `samplesToRender`, `blockSize`, optional `patch`/`mainProcessor`/
  `maxDiffDb`. **[verified-official]** (documented in the Cmajor repo; not exercised
  in this kit yet).

## What to test (pragmatically)

You cannot unit-test "sounds good", but you can pin down the math that silently
breaks:

| Property | Example (see `Cookbook.cmajtest`) |
|---|---|
| Fixed points | `clipTanh(0) == 0`, unity gain at nominal level |
| Bounds | output of a clipper never exceeds ±1; noise stays in −1..1 |
| Convergence | a low-pass fed DC reaches the input value; smoother reaches target |
| Conservation | equal-power crossfade: `a² + b² == 1` across the sweep |
| Identity cases | EQ band at 0 dB passes the signal unchanged; width 1.0 is identity |
| Ballistics | envelope follower rises under signal, falls in silence |
| Known errors | `expectError` for things that must NOT compile |

Write tests as plain `bool` functions — one property each, named after the property.

## Debugging inside a running plugin

There is no debugger in the host, but three patterns cover most cases:

1. **`console <-` tracing** (development only): `console <- "x = " <- x;` prints to
   the host log. Remove before release — it allocates host-side attention per event.
2. **Probe output events.** Add a temporary `output event float dbgOut;` and emit a
   value a few times per second (throttle with a sample counter — see the meter
   pattern in [`06_OVERSAMPLING.md`](06_OVERSAMPLING.md) §self-verification). Watch
   it in the UI with `addEndpointListener`. This is how you verify oversampling
   ratios, envelope behaviour, or gain staging *in situ*.
3. **A/B against a reference.** Render pink noise / impulses through your plugin and
   the reference (original C++ plugin, known-good build), null-test the difference.
   The pre-flight checklist in [`09_PITFALLS_CHECKLIST.md`](09_PITFALLS_CHECKLIST.md)
   has the listening checklist.

## Static checks (this kit's tools)

Before any of the above, run the kit's static gate — it catches the known traps in
seconds:

```bash
python3 tools/preflight.py path/to/MyPlugin/     # endpoints + DSP lint + UI lint + sync
python3 tools/manifest_check.py path/to/MyPlugin/
bash tools/hooks/install.sh                      # make it automatic per commit
```

## Compile-checking headlessly (CI)

The release `cmaj` binary wants WebKitGTK/JACK for GUI/audio features it never uses
during `generate`/`test`. The stub recipe lives in [`../STATUS.md`](../STATUS.md)
§"Reproducing the compile check" and is what the kit's CI workflow uses.

## `cmaj render` quirks (auralising a patch headlessly)  [field-tested]

To actually render audio (not just compile), `cmaj render --length=N --rate=R --output=out.wav`
works headless once the WebKit/JACK stubs above are in place. Two gotchas:

- It renders a `.cmajorpatch`, not a bare `.cmajor`. To sweep parameter values, `sed` the
  `init:` annotation on a temp copy and render that.
- **Leading-silence latency:** the output WAV begins with **~20480 samples of silence** before
  the patch's real output — constant even for a trivial constant-output patch, so it's a
  render-tool latency, **not** a DSP bug. Analyse a **mid/late** window; for timed events,
  file-time = process-time + (latency / rate) ≈ +0.43 s at 48 kHz.
