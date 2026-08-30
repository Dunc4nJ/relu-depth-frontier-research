# G-0074 fresh-context clean-room outcome audit

**Verdict:** `PASS_THREE_LEVEL_CLEANROOM_SEMANTIC_REPLAY`

**Auditor:** AzureHill, fresh-context clean-room auditor, Codex/GPT-5.4.
This is same-lineage T1 evidence from a disjoint implementation; it is not T2
or human review. The research lead did not author this audit.

## Object audited

The audited object is
`artifacts/math/G-0074/farey_three_level_gate_v1.json.gz`.

| Object | SHA-256 |
|---|---|
| registered outcome gzip | `5de36fa1cf39d8524577cdc681b68220c9e807670aef7b14595e8b380bcd4fcb` |
| outcome scientific payload | `1d56ed5afb9cf9dfcc602c43b34a215790066ebb3041087957db955a5476741c` |
| preflight gzip | `a89e5b9a2366fb1d119981a49de2c72b8686255e0e522f7ce2ba0af829c26969` |
| preflight scientific payload | `fc166ac93a268c54c85c9e15f43fcd9c0cfba16b3ebb4d3c3951df39c3c188df` |
| emitted sparse witness | `f40be381b1ab2c8bc406c10a387719e07ebf0bafe07bffb065065048a8388d63` |
| frozen G-0074 producer | `269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d` |
| pinned MAX10 certificate | `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4` |
| row manifest | `53e1766ce236da801ae963b47ee9ce42cdf5a10b978ccd69c9c9152b03ca140f` |

All four published outcome bindings existed and matched their recorded byte
sizes and hashes. The replay independently recomputed both the preflight and
outcome scientific-payload hashes from their canonical field sets. The
producer was not imported or executed. Its source was consulted only to
confirm the published serialization field set and row-descriptor ordering;
none of its evaluation or linear-algebra routines were reused.

## Independent semantic replay

The standalone script in this directory reconstructed the registered witness
as follows:

1. It independently filtered the MAX10 certificate to 252 eligible
   full-support two-component forest bases, with topology census
   `2+8: 168`, `3+7: 39`, `4+6: 32`, and `5+5: 13`, then regenerated the
   18,400 labelled cross-component seeds.
2. It bound all 442 nonzero Y-spoke descriptors to their certificate term,
   base position, raw-seed index, branch pair, anchor, auxiliary vertex, and
   orientation. There were zero discrepancies. The remaining nonzero column
   was exactly `C_E = Sym_avg(max(x_1,x_2))`, at column 8,105 with coefficient
   one.
3. It materialized every expression with a typed-forest dynamic program that
   is structurally disjoint from the producer's profile-sharded evaluator.
   Four-level rows use exact integer branch sums. Three-level rows represent
   every edge sum as an affine form `a*t+b`, so all Farey nodes and midpoints
   are evaluated together without interpolation or floating point.
4. It checked the `Sym_avg` normalization by recovering exactly
   `11!/product(c_i!)` distinct assignments for every profile. The four-level
   multiplicities partition `4^11 = 4,194,304` assignments. Each three-level
   panel partitions `3^11 = 177,147` assignments, including the duplicated
   colour labels at `t=0` and `t=1`.
5. Targets were independently derived from the highest **actual** occupied
   level: `0`, `numerator`, or `denominator`, rather than from a colour label.
   The independently encoded baseline, Farey, combined, and midpoint target
   hashes all matched the registered artifact.
6. One and the same list of 443 rational coefficients was used for every row.
   After conversion to a common 1,614-bit denominator, integer dot products
   gave exactly zero residual on every row; there was no per-node or
   per-profile refitting.

The exact replay covers:

| Panel | Rows | Nonzero exact residuals |
|---|---:|---:|
| frozen `{0,1,2,3}` baseline | 364 | 0 |
| all 13 Farey-F6 nodes, 78 profiles each | 1,014 | 0 |
| all 12 open-interval midpoints, 78 profiles each | 936 | 0 |

The independently materialized selected-column hashes are:

| Materialization | SHA-256 |
|---|---|
| 443 columns on baseline + Farey rows, int64 column-major | `efaf97c58cc2228115be1cba85882fcacc30f4e48966e5e9bb2137f2f38890ba` |
| 443 columns on midpoint rows, int64 column-major | `b02d8c97eddaffd4f10c12c6ed7258f0ba187d3800a455794649205cec842fd8` |

Thus the emitted common vector is independently verified on all registered
nodes and on all twelve unseen midpoint panels. The midpoint replay is a
semantic check independent of the piecewise-affine interpolation argument; it
is not itself needed to infer the continuum once the Farey theorem is valid.

## Rank check and limitation

The 443 materialized support columns are independently linearly independent
modulo each of `1,000,003`, `1,000,033`, and `1,000,037`. Adding the directly
derived linear carrier `C_L` raises the rank to 444 at all three primes. The
same clean-room pivot-row digest appears at each prime:

`8bc2b85ca15d8708cb4aeb5a847d25eb369aa85c6a041ef5caa1204e72df46ab`

The 444-column materialization hash is
`91e52a6b801ccf2d0353cebe1c6ec3612b1b828e3bec254e5203d1f8fa4ac80d`.

The sparse artifact does not expose the 17 zero-coefficient pivot
descriptors. This audit therefore does **not** independently reproduce the
producer's rank-460 lower bound, its pivot lists, the full 8,107-column matrix
hashes, or a rank upper bound. An exploratory capped scan of independently
generated raw family seeds reached rank 453, but it was deliberately omitted
from the durable verdict because it did not reach 460. The full 8,104-orbit
census and orbit-index canonicalization likewise remain frozen-preflight
bindings, although every expression used by the witness is independently
certificate-bound.

## Exact claim boundary

The evidence establishes that the emitted 443-term rational combination equals
MAX11 on the 364 frozen four-level rows and on every three-level profile at all
13 Farey-F6 nodes. Together with the stated continuous piecewise-affine/Farey
argument, translation covariance, and positive homogeneity, this supports the
identity on inputs with at most three distinct coordinate values.

It does **not** establish equality on inputs with four or more distinct values,
a global CPWL identity, a compiled two-hidden-layer MAX11 network, or an
unrestricted depth theorem. This is a strong surviving necessary gate, not the
solution of the original MAX11 problem.

## Replay

From the repository root:

```bash
.venv/bin/python -B artifacts/cleanroom/G-0074/replay_cleanroom.py --workers 8
```

The frozen replay script has SHA-256
`29142b4d905527082efcd0f8001feeec1c93e76e2dada768ee97c7ebbcad0de3`.
AzureHill executed that exact file once after freezing all expected digests.
It returned `PASS_THREE_LEVEL_CLEANROOM_SEMANTIC_REPLAY` in 62.567 seconds,
with zero exact residuals on all 2,314 checked rows and rank 444 at all three
primes above.

No producer, ledger, gate, fixture, golden, or specification was edited for
this audit.
