# 02 · DSP in Cmajor

Everything here is generic and applies to any plugin. Cmajor is a young language
with little public training data, so AI assistants frequently invent stdlib
functions or fall back to C++ idioms — these rules keep output compilable.

## Processor skeleton

```cmajor
processor MyEffect
{
    input  stream float<2> in;     // stereo in   (use `float` for mono)
    output stream float<2> out;    // stereo out

    // parameters (see below) ...

    float state = 0.0f;            // persistent across samples; always initialise

    void main()
    {
        let sr = float (processor.frequency);   // sample rate
        let dt = float (processor.period);      // 1 / sr

        loop
        {
            let l = in[0];
            let r = in[1];
            // ... DSP ...
            out <- float<2> (l, r);
            advance();                           // MANDATORY every iteration
        }
    }
}
```

A `graph` instead of a `processor` lets you wire sub-processors together (see
[`06_OVERSAMPLING.md`](06_OVERSAMPLING.md) and the synth pattern). Mark the
top-level node with `[[ main ]]` when the file declares more than one node.

## Hard rules

1. **Reserved identifiers:** never name a variable, field, parameter or helper
   `input`, `output`, or `stream`. Use `output_`, `outSignal`, etc.
2. **Helpers at processor scope only** — never define a function inside `main()`
   or inside an `event` handler.
3. **Stereo I/O:** index a stereo frame with `in[0]` / `in[1]`; write a frame with
   `out <- float<2>(l, r);`.
4. **Types:** there is no `double` — use `float64` for phase accumulators and
   precise math; everything audio-rate is `float`. No C++ tokens: `unsigned`,
   `uint32_t`, `size_t`, `constexpr`, `static`.
5. **Math casts:** `sin/cos/tan/tanh/sqrt/pow/exp/log` return `float64`. Wrap the
   result with `float(...)` when assigning to a `float`.
6. **Audio loop:** every iteration of the `main()` loop must write `out <- ...` and
   then call `advance();` — unconditionally, never inside an `if`.
7. **Numerical hygiene:** initialise every float field (`float x = 0.0f;`); clamp
   filter cutoff to `< sr * 0.45`; guard `log`/`sqrt`/division with `max(x, 1e-10f)`;
   keep feedback gains `< 1.0`; add a tiny anti-denormal floor in long feedback
   paths if you hear dropouts after silence.

## Parameters — the 3-step pattern

```cmajor
input event float param1 [[ name: "Mix", min: 0.0, max: 1.0, init: 0.5 ]];  // 1. endpoint
float mix = 0.5f;                                                           // 2. state
event param1 (float v) { mix = clamp (v, 0.0f, 1.0f); }                     // 3. handler
```

- **Name parameters `param1..paramN`, sequentially.** The number is the DSP↔UI
  contract — never renumber after wiring (it breaks presets). `name:` is a label
  only; never branch on it.
- `input event` fires once per change (toggles, discrete steps, or when you smooth
  manually). `input value` is read continuously and is smoothed by the host — ideal
  for a swept knob; read it directly in `main()` or multiply a stream by it in a
  graph connection. Add `rampFrames: N` to a `value` to set its smoothing window.
- Annotation keys: `min`, `max`, `init`, `unit: "Hz"`, `step: 1.0` (discrete/toggle),
  `text: "A|B|C"` (enumerated). See [`04_PARAMETERS.md`](04_PARAMETERS.md).

## Sample rate & time

`processor.frequency` (sample rate) and `processor.period` (seconds/sample) are
`float64`; cast with `float(...)`. Cache them once per `main()`, then scale every
time-based quantity by `dt` so the DSP is sample-rate independent — **never hardcode
48000**.

```cmajor
let alpha = clamp (cutoffHz * float (twoPi) * dt, 0.0f, 0.99f);   // one-pole coeff
```

Inside an oversampled node, `processor.frequency`/`period` already report the
oversampled rate, so this math stays correct without changes.

## Reliable building blocks

**Manual one-pole low-pass** (always works, full control):
```cmajor
float lpL = 0.0f, lpR = 0.0f;
// inside main():
let hz    = clamp (cutoffHz, 20.0f, sr * 0.45f);
let alpha = clamp (hz * float (twoPi) * dt, 0.0f, 0.99f);
lpL += alpha * (in[0] - lpL);
lpR += alpha * (in[1] - lpR);
```

**Soft saturation with make-up:**
```cmajor
float saturate (float x, float amount)
{
    let d = 1.0f + amount * 9.0f;
    return float (tanh (float64 (x * d))) / float (tanh (float64 (d)));
}
```

**Delay buffer** (static array; keep the index non-negative):
```cmajor
float[65536] buf;
int writeHead = 0;
// write: buf.at(writeHead) = sample; writeHead = (writeHead + 1) % 65536;
// read : buf.at((writeHead - delaySamples + 65536) % 65536)
```

The standard library is also available and usable — e.g.
`std::filters::svf::Processor` and `std::filters::tpt::onepole` (runtime
`frequency`/`q` event inputs), `std::oscillators::PolyblepOscillator`,
`std::envelopes::FixedASR`, `std::voices::VoiceAllocator`,
`std::midi::MPEConverter`, `std::notes::noteToFrequency`. Choose stdlib for
convenience or a manual implementation for maximum portability.

## Circular-buffer wrap (from Airwindows porting)

Airwindows code uses a specific wrap that is **not** equivalent to `% (len+1)`:
```cmajor
count += 1;
count -= (count > maxLen) ? maxLen + 1 : 0;   // correct wrap
// NOT: count = count % (maxLen + 1);          // off by one
```

## Stdlib cheatsheet

| Symbol | Meaning |
|---|---|
| `processor.frequency` / `processor.period` | sample rate / period (`float64`) |
| `clamp`, `abs`, `floor`, `ceil`, `min`, `max`, `lerp` | built-in math |
| `twoPi` | constant; use `float(twoPi)` in a float context |
| `int(x)` / `float(x)` / `float64(x)` | explicit casts |
| `std::levels::toDecibels(x)` / `dBtoGain(x)` | level conversions |
| `wrap<N>` | power-of-two modular integer |

## More verified stdlib (from the official Amorph prompts)

**[verified-official]** — see [`../ai/amorph_official/`](../ai/amorph_official/) for the
full cheatsheets.

- **RNG:** `std::random` is a *namespace*, not a function — `std::random(lo,hi)` does
  **not** exist. Declare a field `std::random::RNG rng;` then call `rng.getUnipolar()`
  (0..1), `rng.getBipolar()` (−1..1), `rng.getFloat(max)`, `rng.seed(int64)`
  (seed with `processor.id` or `processor.session`).
- **Notes:** `std::notes::noteToFrequency(n)` and `frequencyToNote(hz)` return
  **float32** (not float64).
- **MIDI:** `std::midi::Message` with `isNoteOn()/isNoteOff()/getNoteNumber()`(int)`/
  getVelocity()`(int)`/getFloatVelocity()`(0..1)`/isController()/isControllerNumber(n)/
  getControllerValue()/getChannel0to15()/isPitchWheel()`; build messages to emit with
  `std::midi::createMessage(status, d1, d2)`. **Match note-off by stored `int`
  note number, never by float frequency.**
- **Oscillators:** `std::oscillators::waveshape(float32)::sine/square/triangle/
  sawtoothUp(phase)` and antialiased `polyblep_sawtooth/polyblep_square(phase, inc)`.
- **Noise processors:** `std::noise::White / Brown / Pink`.
- **FFT:** `std::frequency::realOnlyForwardFFT()` works (output `[0..N/2]` real bins,
  `[N/2+1..N-1]` imaginary).
- **Processor props:** `processor.id` (stable int32 per instance), `processor.session`
  (changes each run).

### Two clarifications that override older notes

- **Custom parameter names work.** `param1..paramN` is the recommended convention, but
  `paramDrive`, `paramMix`, etc. bind fine. (The old "custom names break binding"
  claim is false.) The `param1..paramN` convention is still recommended so the UI/DSP
  contract stays obvious.
- **Arrays are fixed-size only.** No unsized `float[] buf`, no runtime `.wrap(size)`,
  no `.size` property — sizes must be compile-time constants. Index with `.at(i)`.
- **Avoid prefix `++`/`--`** (`x += 1`). The prompts' own `for` headers use `++i`,
  which compiles; the stated rule is the safe default.

## Top-level structs

Only `namespace`, `processor`, `graph` may appear at file scope. Wrap a bare
`struct`:
```cmajor
namespace Types { struct Frame { float[512] bins; } }
```

## What does NOT exist in Cmajor

Heap allocation (arrays are static, compile-time sized), threads/async, STL
containers/algorithms, templates/generics, `#include`/imports (share code via
`namespace`), strings beyond parameter labels, and the C++ types `double` /
`unsigned` / `size_t` / `constexpr` / `static`.

## Common DSP failures (quick list)

| Symptom | Cause | Fix |
|---|---|---|
| Silent output | missing `advance()` or `out <-` | write both, every loop iteration, unconditionally |
| `Forbidden identifier 'output'` | reserved name | rename (`output_`) |
| `Unknown type 'double'` | C++ type | use `float64` |
| Goes silent after ~30 s | denormals in feedback | add a tiny anti-denormal floor |
| Noise when turning a knob | NaN from `log(0)`/`sqrt(-x)` | clamp input: `max(x, 1e-10f)` |
| Filter explodes | cutoff above Nyquist | clamp to `sr * 0.45f` |
| Helper "not found" | defined inside `main()`/`event` | move to processor scope |

## Porting Airwindows algorithms (C++ → Cmajor)

When porting, **port exactly** — do not simplify, optimise, or invent DSP math.

| C++ pattern | Cmajor equivalent |
|---|---|
| `fabs(x)` | `abs(x)` |
| `>>>` (unsigned right shift) | does not exist — mask instead, e.g. `(int(x) & 0x7FFFFFFF)` |
| `pow(x, n)` | `float64(pow(x, n))` — always cast the result |
| `sin()`, `cos()` | `float64(sin(x))` then `float(...)` back |
| dither block (double/32-bit) | remove entirely — not needed |
| `fpdL ^= fpdL << 13; ...` (noise) | remove — handle noise floor differently |
| `while (--sampleFrames >= 0)` | `loop { /* one sample */ advance(); }` |
| `inputSampleL = *in1++` | `let inL = in[0];` (frame access) |

Map **every** parameter — hardcoding one silently changes the algorithm (gain
offsets, broken normalisation, unexpected saturation). Check the original source to
understand each parameter before adapting. See
[`reference/airwindows/README.md`](../reference/airwindows/README.md).
