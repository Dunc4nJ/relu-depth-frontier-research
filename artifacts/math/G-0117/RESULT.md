# G-0117 — exact global residual machinery

## Result

The missing computational bridge from a finite G-0113 panel seed to global
ordered-cone CEGIS is operational.

For a fixed primitive active direction `d`, the subset-DP implementation
computes `h_d(W)` for every one of the 163,740 frozen G-0113 atoms, together
with every atom's 11 exact linear coordinates.  On the registered benchmark
direction the first bounded run completed in 13.30 seconds.  After an
adversarially found public-API overflow was repaired, the current-source rerun
completed in 21.95 seconds under heavier concurrent load, used at most 110,992
KiB RSS, and reproduced the same scientific hashes exactly:

```text
hinge row:   6d4e03e0f16ab19d0d16810aa7e5e47ca9d87548b9c6f03a2229ad91ba334816
linear rows: 84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51
```

There were 125,562 nonzero entries in that hinge row and the maximum entry was
777,168.  The current bound benchmark report is
`coordinate_pricer_benchmark_v2.json`; v1 is retained as the pre-fix
superseded execution record.

The companion factorial-orbit kernel aggregates a sparse rational
certificate's complete ordered-cone normal form modulo two fresh primes.  A
nonzero modular residual rigorously refutes that rational seed as a global
identity; a two-prime zero remains pending an exact magnitude bound or exact
replay.

## Exact checks completed

- Four release unit tests pass, including complete equality between the
  subset DP and literal permutation enumeration on a nontrivial atom.
- The clean-room reviewer supplied the valid direction
  `(0,1,-26,25,0,0,0,0,0,0,0)`, which exposed `i8` multiplication overflow
  outside the mass-five generated direction universe.  The comparison now
  uses `i16`; that direction is accepted and returns exact coefficient zero.
- The explicit frozen G-0109 integration test matches all supported hinge
  coefficients and the complete linear vector on loopless records, including
  the active-11 sequence `6,972,321`; 16 directions absent from that atom's
  frozen support price to exact zero.
- Full normal forms for G-0113 control sequences 0 and 3 evaluate on all 301
  formal-profile rows to the independently frozen hashes
  `f09264...3c58` and `475f46...2099` exactly.  Sequence 3 is cyclic and
  active on all 11 vertices.
- Branch swap and vertex relabelling preserve hinge prices; a changed edge
  changes the complete semantics; malformed direction orientations are
  rejected.
- On the planted rational certificate
  `1/2 * F_0 - 3/7 * F_1`, the factorial-orbit route selected direction
  `(0,0,0,0,0,0,0,0,1,-2,1)`.  Independent subset-DP prices were
  `h_0=123,648` and `h_1=33,792`, giving exact residual
  `331,392/7`.  Its residues matched both modular replay fields exactly.
- `cargo test --release` and clippy with `-D warnings` pass.  The two
  full-artifact checks are explicit ignored tests and both pass when invoked.

An independent clean-room review is still completing its post-fix replay.
These remain same-family checks and do not satisfy the campaign's unavailable
T2 promotion requirement.

## Why this changes the search

The previous exact panel evaluator takes roughly an hour to traverse the full
family.  Once one failed global replay exposes a hinge direction, G-0117 can
price the corresponding new exact CEGIS row family-wide in seconds.  The
expensive global normal-form enumeration is needed only on the current sparse
certificate, not on all 163,740 candidates.

## Claim boundary

This is verified research machinery, not a MAX11 result.  It proves neither
that the live 301-row scan has a rational seed nor that repeated residual rows
will converge.  A negative result remains restricted to the fixed G-0113
family unless a separate completeness theorem is proved.  A positive panel
seed is not global until the complete normal-form residual is zero over `Q`.
