# 06 · Oversampling in Cmajor

**Status: [verified]** against the Cmajor Language Guide (the "oversampling and
undersampling processors" section). This supersedes any older note claiming
oversampling is "ignored by the host" — see [`../STATUS.md`](../STATUS.md)
contradiction #1.

## TL;DR

- Cmajor has **built-in per-node oversampling**: `node x = MyProc * N;`.
- It applies **sinc interpolation** automatically on the way in and out
  (alias-free).
- `/ N` undersamples (for slow control-rate processing).
- `N` must be a **compile-time integer constant** (`* 4`, not `* someVariable`).
- The two superseded levers — `[[oversampling: N]]` in source and `oversampleFactor`
  in the manifest — are **not** the mechanism. Use `* N`.

## Basic syntax

```cmajor
graph MyDSP [[ main ]]
{
    input  stream float<2> in;
    output stream float<2> out;

    node distortion = Saturator * 4;     // 4x oversampled
    node filter     = LowPass;           // runs at host rate

    connection
    {
        in             -> distortion.in;
        distortion.out -> filter.in;
        filter.out     -> out;
    }
}
```

Undersampling for control-rate work:
```cmajor
node controlRate = SlowEnvelope / 8;     // runs at 1/8 host rate (LFOs, slow mod)
```

## What Cmajor does internally

For `node sat = Saturator * 4;`:

1. **Input upsample** — incoming streams are sinc-interpolated up to 4× rate.
2. **Inner processing** — the processor's `main()` runs 4× per host sample;
   `processor.frequency` inside it reports the 4× rate.
3. **Output downsample** — the output stream is sinc-interpolated back to host rate
   with the anti-aliasing low-pass built in.

From the Cmajor docs:
> *"For an oversampled node, sinc interpolation is used in and out of the processor
> to provide high quality alias free streams."*

Interpolation policy can be overridden per connection:
```cmajor
connection [latch]  node.out -> out;   // repeat last value (cheapest)
connection [linear] node.out -> out;   // low quality, quick
connection [sinc]   node.out -> out;   // highest quality (default for oversampled)
```
For an **undersampled** node the defaults are `latch` on input connections and
`linear` on output connections.

**Only scalar streams interpolate** across the boundary (a compile error otherwise).
A `float<2>` stereo stream across `* N` is **[field-tested]** as working in practice;
if you rely on it, confirm in your toolchain.

### What is NOT resampled

- **Events** are sample-rate independent — they pass through a `* N` node unchanged,
  so parameter updates work normally.
- **Value endpoints** likewise.
- Only **stream** endpoints are interpolated.

### Latency

Sinc filters introduce latency (FIR kernel length). The exact sample count is not
specified in the docs and is **[unverified]**; report `processor.latency` if you need
a number, and budget for it when stacking multiple oversampled stages.

## Production pattern: oversample the non-linear core only

Put the non-linear DSP in a processor, oversample it as a graph node, and **mirror
its parameters** to the graph boundary so the host sees them:

```cmajor
graph MyEffect [[ main ]]
{
    input  stream float<2> in;
    output stream float<2> out;

    input  core.param1;          // hoist the core's parameters to the boundary
    input  core.param2;
    output core.rmsOut;          // hoist meter outputs

    node core = MyCore * 4;       // 4x oversampled; sinc in/out automatic

    connection { in -> core.in; core.out -> out; }
}

processor MyCore { /* the non-linear DSP; processor.frequency reports the 4x rate */ }
```

### Keep rate-sensitive analysis OFF the oversampled node

If you run a spectrum/DFT for a UI analyser, run it on a **separate node at host
rate**, tapped in parallel — not on the oversampled node — so the frequency mapping
stays correct:

```cmajor
node core        = MyCore * 4;          // audio path, oversampled
node spectrumDFT = SpectrumDFT;         // analysis, host rate (NOT * 4)

connection
{
    in            -> core.in;
    core.out      -> out;
    in            -> spectrumDFT.in;     // parallel tap, no intervention in audio
    spectrumDFT.specOut -> spectrumData; // -> UI via addEndpointListener
}
```
This mirrors a real production reverb's topology. **[field-tested]**

## When do you need oversampling?

**Yes** — anything that generates new harmonics: hard clipping, `tanh`/`atan`
saturation at high drive, waveshapers, bit-crushers / sample-rate reducers,
wavefolders, naïvely generated oscillators, high-index FM.

**No** — linear operations create no new harmonics: biquad/SVF/one-pole filters,
plain gain, delays/reverb tails, EQs, mixing/summing. Oversampling these just costs
CPU.

## Self-verification probe

If you're unsure oversampling is active in your host, emit `processor.frequency` from
inside the oversampled node and watch it in the UI:

```cmajor
processor RateReporter
{
    output event float reportedRate;
    int counter = 0;
    void main()
    {
        loop
        {
            counter += 1;
            if (counter >= int (float (processor.frequency) * 0.5f))   // ~every 0.5s
            {
                reportedRate <- float (processor.frequency);
                counter = 0;
            }
            advance();
        }
    }
}
// node probe = RateReporter * 4;   // at 48 kHz host rate this should report 192000
```

If it reports the host rate instead of `N×`, oversampling isn't engaging and you'd
need to oversample manually (polyphase FIR, etc.).
