# Contributing

This kit aims to be a **verified, project-independent** reference. The bar for
adding or changing a claim is that it is checkable and stays correct.

## The verification standard

Tag factual claims so readers know how much to trust them:

- **[verified]** — confirmed against the official Cmajor source/docs. Cite the file
  (and, if helpful, the section) in [`STATUS.md`](STATUS.md).
- **[field-tested]** — repeatedly observed in real Amorph plugins; not in the
  official spec. Say so.
- **[unverified]** — plausible but unconfirmed. Mark it; don't present it as fact.

When you correct an outdated claim, **update `STATUS.md` in the same change** — note
what the old claim was, what's true now, and where you checked.

## House rules

- **No project-specific material.** No real plugin names, vendor IDs, `(c)` notices,
  internal version stamps, or private paths. Extract anonymised, reusable patterns
  only.
- **English** for all docs and code samples (matches the plugin code rule).
- **Don't vendor third-party source** (Cmajor, Airwindows, …). Link and give clone
  instructions instead; respect their licenses.
- Keep code snippets **complete and runnable** where practical — no `// ...` gaps in
  things meant to compile.
- Prefer small, focused PRs. One topic per change.

## Checking Cmajor claims yourself

```
git clone https://github.com/cmajor-lang/cmajor
```
The two most useful trees:
- `docs/` — the Language Guide, Patch Format, etc.
- `javascript/cmaj_api/` — the real bridge (`cmaj-patch-connection.js`,
  `cmaj-patch-view.js`) that backs every UI claim.

## Roadmap help wanted

See the roadmap in [`README.md`](README.md). High-value additions: a minimal
`templates/Plugin/` (DSP + UI + manifest), worked examples (oversampled saturator;
small synth), and a CI check that documented Cmajor snippets actually compile.
