# G-0073 fresh-context clean-room outcome audit

**Verdict:** `PASS_BOUNDED_CLEANROOM_SEMANTIC_REPLAY`

**Auditor:** SapphireCrane, fresh-context clean-room auditor, Codex/GPT-5.
This is a same-lineage T1 review using a disjoint implementation; it is not
T2 or human review. The research lead did not author this audit.

## Object audited

The audited object is
`artifacts/math/G-0073/y_spoke_profile_gate_v1.json.gz`.

| Object | SHA-256 |
|---|---|
| registered outcome gzip | `59b81312f44e98ae61481fcac2e61075d60d187c4bf5b4201a821c44ec3b60bb` |
| outcome scientific payload | `6c006df13c7e010128b8f2ce71b5a2eb9e599581d575f262ef8084637ef92f56` |
| emitted sparse witness | `aa28b03000d18c1471ed7806614fb33f824e63343a7753f39f872905d31b2309` |
| frozen producer, hashed but never imported or executed | `333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67` |
| preflight gzip | `05908cba9a9ea47ccda0d07f2fa5af630c38c7031986ede57cb6a78dad611e1d` |
| preflight scientific payload | `d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8` |
| pinned MAX10 certificate | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| clean-room selected-column materialization | `2464581cc6aea5d50b242fdaaf5d841e58535efefba6f1ee74303ad0436bd480` |

All 17 outcome input/backend bindings existed and matched their recorded byte
sizes and hashes.

## Independent method and result

The replay script in this directory does not import or call
`y_spoke_profile_gate.py`. It reconstructs the selected columns directly from
the frozen output descriptors and certificate:

1. Independently filter the certificate to 252 eligible full-support,
   two-component forest bases. The topology census is `2+8: 168`, `3+7: 39`,
   `4+6: 32`, and `5+5: 13`.
2. Independently enumerate the 18,400 labelled cross-component seeds in
   certificate/base, anchor, auxiliary, orientation order.
3. Bind every one of the 256 selected Y-spoke descriptors to its certificate
   term, base position, raw index, branch pair, cross-component endpoints, and
   orientation. There were zero descriptor discrepancies.
4. Enumerate the 364 weak compositions of 11 into the four frozen levels
   `{0,1,2,3}`. Their distinct-assignment multiplicities sum to
   `4^11 = 4,194,304`. The materialized profile and target hashes match the
   outcome:
   - profiles: `4a310e81ec054d031bb7438e64f8885939bc0565c05af789f3217741516fd9de`
   - target: `a3d3be16df8de6f25b40e318f656efbee4607806413e72a48b2d276d7f21f4d7`
5. Materialize every selected expression column by a clean-room dynamic
   program on the two typed forest components. This is structurally different
   from the producer's profile-sharded NumPy evaluation.
6. Independently derive the averaged carriers from ordered-coordinate
   hypergeometric counts. The sparse witness uses exactly
   `C_E = Sym_avg(max(x_1,x_2))`, at original column 8,105 with coefficient
   one. `C_L` has zero coefficient and is omitted from the sparse support;
   `C_Y` is unused.
7. Replay the 257 emitted rational coefficients against all 364 rows using
   only stdlib `fractions.Fraction` arithmetic.

The exact residual is zero on all 364 rows. This independently verifies the
semantic content of the emitted profile witness.

The registered 258 pivot columns are the first 256 Y-spoke columns followed
by `C_L` and `C_E`; their index-list hash is
`d5365b6312f4929c91f7c97ffdba05f125abc63770623af9d09e1cf08e509ed7`.
The independent column-echelon implementation found rank 258 at both
registered primes and one extra prime:

| Prime | Rank | clean-room pivot-row digest |
|---:|---:|---|
| 1,000,003 | 258 | `da754b0732654b245e986b7571b8db6be2761986e2f923cea0697b075cb5e801` |
| 1,000,033 | 258 | `da754b0732654b245e986b7571b8db6be2761986e2f923cea0697b075cb5e801` |
| 1,000,037 | 258 | `da754b0732654b245e986b7571b8db6be2761986e2f923cea0697b075cb5e801` |

Consequently these 258 integer columns have exact rational rank 258: a
full-rank modular minor is a nonzero integer minor over the rationals.

## Limitations and discrepancies

No mathematical discrepancy was found in the emitted witness.

- The audit did not reconstruct all 8,104 orbit representatives or the full
  8,107-column matrix. Therefore it independently proves a 258-dimensional
  lower bound from the selected pivot columns, not the producer's full-matrix
  rank upper bound.
- The artifact does not materialize its claimed exact pivot-row list. The
  clean-room elimination chose a different valid row basis with digest
  `da754b07...`, rather than the stored `d0610f12...`. Row bases are
  nonunique; this is not a semantic contradiction, but the producer's
  particular pivot-row list is not independently checkable from the outcome
  alone.
- The 8,104-orbit census and 10,296 VF2 checks remain preflight-bound evidence,
  not clean-room-rederived evidence in this audit.
- Reproduction here is a fresh same-model-lineage T1 check. Agreement must not
  be presented as T2 confirmation or human refereeing.

## Exact claim boundary

The evidence establishes exact equality of the emitted 257-term rational
combination to the MAX11 target on the 364 frozen symmetric profiles over
levels `{0,1,2,3}` under the stated `Sym_avg` convention.

It does **not** establish a global CPWL identity, a two-hidden-layer MAX11
network certificate, an unrestricted lower/upper bound, or correctness away
from the frozen profiles. Failure of this particular basic interpolant on a
future generic point would also not reject the full 8,107-column family.

The substantive next experiment is off-grid/generic-slice constraint
generation in the full coefficient space, not another profile-only replay.

## Replay

From the repository root:

```bash
.venv/bin/python -B artifacts/cleanroom/G-0073/replay_cleanroom.py
```

The standalone replay script has SHA-256
`f67a0adcba1b273cec38266b52f27908a27e5c6e0b6a5a2fecbcbda70191c54b`.
SapphireCrane executed that exact file once after persistence. It returned
`PASS_BOUNDED_CLEANROOM_SEMANTIC_REPLAY` in 90.449 seconds, with zero nonzero
`Fraction` residual rows and rank 258 at all three primes listed above.

The script is fail-closed on the outcome, certificate, producer, preflight,
binding, descriptor, census, profile, target, selected-column, witness, and
pivot-rank hashes listed above.

## Honesty inventory

No producer, ledger, gate, test, fixture, golden, or specification was edited
for this audit. No producer code was imported or executed. The full-rank upper
bound, orbit-census, pivot-row, and independence-tier limitations are stated
explicitly. The strongest evidence is the independently materialized
257-column exact `Fraction` replay; it is re-executable with the standalone
script above.
