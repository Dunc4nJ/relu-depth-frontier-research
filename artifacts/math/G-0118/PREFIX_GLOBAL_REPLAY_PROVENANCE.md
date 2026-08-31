# G-0118 prefix member — discovery global replay provenance

## Outcome

The preregistered prefix-exact solver returned an exact member of the fixed
313-row system.  Its 99 nonzero denominator-cleared terms were then replayed
over the complete ordered-cone normal form.  The candidate is **globally
refuted**: the first canonical nonzero hinge direction was

```text
(0,0,0,0,0,0,0,0,1,-4,3)
```

with residues

```text
mod 1,000,000,007: 282,521,085
mod 1,000,000,009: 222,337,686
```

Either nonzero residue is already a characteristic-zero refutation of this
integer-scaled candidate.  Both linear residual vectors were zero.  The replay
processed all 99 terms, 3,951,763,200 labelled permutations, and found 170,545
hinge directions nonzero modulo at least one prime.

## Discovery adapter boundary

`prefix_global_modular_adapter_v1.json` copies `target_scale` and `terms`
verbatim from `prefix_exact_cegis_v1.json` into the already supported G-0117 v2
wire shape.  Its embedded v2 `source_exact_postprocess` object is a parser
compatibility device and is **not** provenance for the G-0118 coefficients.
Accordingly this adapter is admissible only for discovery replay.  The actual
G-0118 result, preregistration, correction, runner, adapter, replay, replayer
source, semantic kernel, uniqueness lemma, and executable are separately
hashed below.  A binding-clean G-0118 consumer remains required for promotion
beyond candidate refutation.

## Reproduction

```bash
artifacts/math/G-0117/target/release/global_modular_replay \
  artifacts/math/G-0113/panel_solver_input_v1.json \
  artifacts/math/G-0118/prefix_global_modular_adapter_v1.json \
  /tmp/g0118-prefix-global-modular-replay.json
```

The committed output was produced by the same command with a temporary output
path and copied byte-for-byte after completion.

## SHA-256 bindings

```text
bad55cb45134cfdab3be86b3d3c676807acb402d69b6d37d0af59767152e531c  prefix_exact_cegis_v1.json
3292a64a7ee811a03bef2b0d41b3df9c809d11ebd931af1351ff5f68ccd18107  PREFIX_EXACT_CEGIS_PREREGISTRATION.md
a6f82b9f0d17e05d8cfb8a82d726d0a5cc163c540c89ddfa160e839e01a0d850  IMPLEMENTATION_BINDING_CORRECTION.md
6a152c1fbfe72101affeff05aea35367a0ae14d293c633c13f51ec7b260d14bf  prefix_exact_cegis.py
6bfad51485000162f43ea7f67dfe0ad48430058bec110ff0b95d608076187cee  prefix_global_modular_adapter_v1.json
ee7ccc77c34454845b59e709507b901d814263242d8ff9b66e4257f06e0e90d4  prefix_global_modular_replay_v1.json
dda43de29d0ecfa4274fb1e7622c3dba662444a84a5c72b75f1a3c921be77de4  ../G-0117/src/bin/global_modular_replay.rs
84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa  ../G-0117/src/lib.rs
39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17  ../G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md
77ce14e0f9820c4c5164494d418db41d4d7ed775c6d4eb2547a336634b2eb7cd  ../G-0117/target/release/global_modular_replay
```

## Claim boundary

This proves only that the displayed 99-term rational candidate is not a global
ordered-cone identity.  It does not refute the 163,740-column family, prove a
two-hidden-layer lower bound, or settle MAX11.  The direction above is the next
exact CEGIS row.
