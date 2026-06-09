# 11 · DSP Cookbook

Reusable building blocks for the DSP jobs that come up in almost every plugin.

> **The canonical, tested version lives in
> [`../cookbook/Cookbook.cmajor`](../cookbook/Cookbook.cmajor)** — a dependency-free
> `namespace cookbook` you copy into your plugin (Cmajor has no cross-patch imports).
> Every recipe is **[compiler-verified]** and covered by unit tests in
> [`../tests/Cookbook.cmajtest`](../tests/Cookbook.cmajtest) (`cmaj test`, all
> passing). This page excerpts the most-used recipes and explains when to reach for
> each; trust the `.cmajor` file over the page if they ever drift.

## What's in the box

| # | Recipe | Use it for |
|---|---|---|
| 1 | `Smoother` | zipper-free parameter changes (gain, cutoff) |
| 2 | `OnePole` LP/HP | tone controls, control-signal smoothing |
| 3 | `SVF` (TPT/Zavalishin) | swept filters — stable under fast modulation |
| 4 | `Biquad` (RBJ peak) | EQ bands with dB gain and Q |
| 5 | `readDelay` | fractional (interpolated) delay reads — chorus, echo |
| 6 | `LFO` (sine/triangle) | modulation sources |
| 7 | `Follower` | envelope following with attack/release ballistics |
| 8 | `compressorGain` | dynamics gain computer (hard knee, dB domain) |
| 9 | `clipTanh` / `clipCubic` | saturation / soft limiting (oversample these!) |
| 10 | `DCBlocker` | removing DC offset after asymmetric waveshaping |
| 11 | `xfadeA/B` | equal-power dry/wet crossfades |
| 12 | `stereoWidth` | mid/side width control |
| 13 | `NoiseLCG` | cheap deterministic white noise |
| 14 | `flushDenormal` | long feedback paths that fade to silence |

## The four you will use in every plugin

**Parameter smoother** — run once per sample toward the target set by the `event`
handler:

```cmajor
cookbook::Smoother gainSmoother;            // field; .value defaults to 0
// in main():  let g = cookbook::smooth (gainSmoother, targetGain, 0.005f);
```

**One-pole low-pass** (tone control, envelope smoothing):

```cmajor
cookbook::OnePole lp;
let alpha = cookbook::onePoleAlpha (cutoffHz, sr);   // clamps below Nyquist
let y     = cookbook::processLP (lp, x, alpha);
```

**Equal-power dry/wet** — a linear crossfade dips −3 dB at the centre; equal-power
does not:

```cmajor
let outSample = dry * cookbook::xfadeA (mix) + wet * cookbook::xfadeB (mix);
```

**Soft clip with constant make-up** (wrap the processor in `* 4` — see
[`06_OVERSAMPLING.md`](06_OVERSAMPLING.md)):

```cmajor
let shaped = cookbook::clipTanh (x, driveAmount);    // drive 0..1, unity at x = 1
```

## Stateful recipes — the struct-by-reference pattern

Cmajor has no classes with hidden state; the cookbook uses a plain struct plus a
process function taking it by reference. Declare the struct as a **processor field**
(so the state persists across samples), call the function per sample:

```cmajor
processor MyFX
{
    // ...
    cookbook::SVF filter;        // state lives here

    void main()
    {
        let sr = float (processor.frequency);
        loop
        {
            let bands = cookbook::processSVF (filter, in[0], cutoffHz, 0.707f, sr);
            out <- float<2> (bands.lp, bands.lp);
            advance();
        }
    }
}
```

Member-call syntax also works (`filter.processSVF (x, ...)` ≡
`processSVF (filter, x, ...)`) — both are **[compiler-verified]**.

## Choosing a filter

- **`OnePole`** — 6 dB/oct, cheapest, never rings. Tone tilts, smoothing.
- **`SVF`** — 12 dB/oct with LP/BP/HP from one tick; the TPT structure stays stable
  when the cutoff moves fast (auto-wahs, envelope filters, LFO sweeps).
- **`Biquad`** — when you need dB-gain bell curves (EQ). Recompute coefficients only
  when a parameter changes, not per sample.
- The stdlib also has `std::filters::svf` / `tpt::onepole` with event inputs —
  equally fine; the cookbook versions give you the math under your own control.

## Performance notes — [compiler-verified]

- **Index arrays with `.at(i)`** (or a `wrap<N>`/`clamp<N>` index type). A plain
  `int` index compiles but emits a *per-access runtime range-check* performance
  warning — measurable in tight voice loops.
- **`wrap<N>` beats `%` for power-of-two ring buffers** — the modulo is free in the
  type. For arbitrary sizes, `(i + len) % len` is fine; prefer power-of-two lengths.
- **Hoist per-sample invariants.** Compute filter coefficients when a parameter
  changes (or once per `main()` iteration block), not per sample — `tan`/`sin`
  per sample dominates small DSP kernels.
- **`float64` only where it matters**: phase accumulators and coefficient math.
  Audio paths stay `float`.
- **Branchless `select()` requires vector arguments** — scalar `select` is a compile
  error; for scalars a plain `if`/ternary is idiomatic and fast.
- **Denormals**: long feedback tails (reverb, analog-style filters) can hit denormal
  range and burn CPU after the input stops — apply `flushDenormal` inside feedback
  loops.

## Testing your own recipes

Every block here has a matching test in
[`../tests/Cookbook.cmajtest`](../tests/Cookbook.cmajtest). When you add a recipe,
add a `bool` test next to it and run `cmaj test tests/` — the format is documented in
[`12_TESTING.md`](12_TESTING.md).
