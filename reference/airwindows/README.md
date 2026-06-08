# Airwindows as a DSP Reference

[Airwindows](https://github.com/airwindows/airwindows) is Chris Johnson's large
collection of open-source audio plugins (MIT licensed). The C++ source is a
goldmine of compact, musical DSP algorithms — saturation, console emulation,
dithering, reverbs, EQs, and many one-off effects — and it ports well to Cmajor.

> **We do not vendor Airwindows here.** The source is large and changes
> continuously, and it has its own license. This kit only points to it. Clone it
> yourself when you want to study or port an algorithm:
>
> ```
> git clone https://github.com/airwindows/airwindows
> ```
>
> Amorph has no general web access, so `git clone` is the reliable way to bring the
> source into your environment for reference.

## License & attribution

Airwindows is **MIT licensed** (© Chris Johnson). If you ship a port, keep the
attribution and comply with the MIT terms. The "Airwindopedia" plain-text catalog
(one paragraph per plugin, describing what each does and why) lives in the Airwindows
project and its mirrors — read it there rather than copying it into your repo.

## How to port (summary)

Porting rules live in [`../../docs/02_DSP_CMAJOR.md`](../../docs/02_DSP_CMAJOR.md)
("Porting Airwindows algorithms"). The essentials:

- **Port exactly.** Don't simplify, optimise, or invent DSP math.
- **Map every parameter.** Hardcoding one silently changes the algorithm (gain
  offsets, broken normalisation, unexpected saturation).
- Translate idioms: `fabs`→`abs`; cast all `pow`/`sin`/`cos` results with
  `float(float64(...))`; remove dither and noise-shaping blocks; convert
  `while (--sampleFrames >= 0)` to `loop { ... advance(); }`; use the Airwindows
  circular-buffer wrap (`count -= (count > maxLen) ? maxLen+1 : 0;`), **not** `%`.
- Read the original's parameter list (the "Airwindopedia" entry plus the source) to
  understand each control before adapting.

## Workflow

1. Pick a plugin; read its Airwindopedia paragraph for intent.
2. Open its C++ source; identify parameters, state, and the per-sample math.
3. Port the per-sample block into a Cmajor `processor` `main()` loop.
4. Wire parameters with the 3-step pattern; map **all** of them.
5. If the algorithm is non-linear (saturation, clipping, folding), wrap the core in
   a `* N` oversampled graph node (see
   [`../../docs/06_OVERSAMPLING.md`](../../docs/06_OVERSAMPLING.md)).
6. A/B against the original to confirm the port.
