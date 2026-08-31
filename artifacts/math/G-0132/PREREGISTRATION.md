# G-0132 preregistration — outcome-blind branch continuation after G-0128

## Registration boundary and decision

Frozen on 2026-08-31 without reading, hashing, statting, or otherwise learning the contents or terminal branch of

```text
artifacts/math/G-0128/full_family_master_result_v2.json
```

Whether that path already exists is intentionally unknown to this author. No G-0132 producer exists yet and none may be implemented until this protocol is committed and pushed.

G-0132 has one mechanical branch selector and one study per branch:

- `FULL_FAMILY_380ROW_EXACT_Q_MEMBER` -> complete exact global normal-form replay of that exact member;
- `FULL_FAMILY_380ROW_EXACT_Q_NONMEMBER` -> exact pricing of that exact separator on the complete loop-inclusive degree-five signed-`W` denominator and both span bases.

Any other G-0128 result, invalid binding, or branch ambiguity stops `INVALID`. The unselected arm is not run. Result contents may supply only the frozen member or separator; they may not change algorithms, ordering, controls, thresholds, or interpretations below.

## Frozen prior bindings

```text
ed33f3349780c1e73d64b1a9a75e2a070ae554bd1313dc081187a8d2554e5a9f  artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md
cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8  artifacts/math/G-0128/full_family_master_v2.py
049a0a85bfec5b3ab053208da825a173dbd16302af72004c47f54a906a2ae4ed  artifacts/reviews/G-0128-round2-master/AUDIT_VERDICT.md
53f90bacf3271ffb94174eb1a7e6bc5a525b36d86bb722ef2c595f111043bfdf  artifacts/reviews/G-0130-model-boundary/AUDIT_VERDICT.md
39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17  artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md
2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6  artifacts/math/G-0117/src/lib.rs
5652b1136a56294ef6fdbba164e66dd489c86a66675901b45e9a2ed5ab0cc40c  artifacts/math/G-0028/LOOP_INCLUSIVE_SIGNED_W_SCHEMA.md
7a7b763dbfba826b2366139176f6b26611c8f1eac0df8f26fd68fa1b928730cb  artifacts/math/G-0044/README.md
c22c29072f1b046a76c6d3767f7054efa44852fbdb88ae506ba561c5781a1acf  artifacts/math/G-0038/stream_loop_inclusive_denominator.py
1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640  artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json
e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd  artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz
16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb  artifacts/cleanroom/G-0038/independent_loop_inclusive_census.py
98469e1cdaaaeac411db16439bbc7f2226b9416ee32d9df1e78f214c2cda0078  artifacts/cleanroom/G-0038/independent_loop_inclusive_census_v1.json
215e7eb359d01078131e3266487f35658cf922f1285d33dec972f51f9e33d165  artifacts/cleanroom/G-0038/verify_loop_inclusive_denominator_stream.py
8379177a8597fcfca9e291fd354289af4950976b32d8238b44caa4a2035cf542  artifacts/cleanroom/G-0038/loop_inclusive_signed_degree5_stream_verification_v1.json
```

The G-0038 stream contract is fixed at 7,015,841 records, 46 declared strata, and this order:

```text
signed_mass, active_vertices, nauty-genbg canonical output,
minimum signing mask under automorphisms and global sign
```

Its frozen digests are:

```text
canonical header             96405e67250c9e91722c143d78d7761266e6614aa9a56715641c384eaf01437c
canonical framed JSONL       89ffe6d0f8aec9fb0ef8d91c5f15b75c89a6bd0d5bdd5b554c155f5c18e177cd
canonical orbit-only JSONL   e49035b2700272f6edc1d1792bbceb0d5811a870820dd982d67a243b79423ef5
compressed bytes             78,769,863
```

The G-0038 header must state `n=11`, five edge occurrences per branch, loops allowed, canonical zero-common-loop/nonloop-padding semantics, and span bases `five-common-nonloops` (`5E`) and `five-common-loops` (`5L`). Every header field, record sequence, stratum count/digest, stream digest, gzip trailer, manifest binding, and independent-verification binding is scientific input.

## Future G-0128 result admission

The sole admitted future result has path above and schema

```text
max11-g0128-full-family-master-result-v2
```

Before branch selection, the consumer must independently:

1. hash the result and record that hash in a one-shot G-0132 manifest;
2. require its exact G-0128 preregistration, source, source-audit, and `full_family_master_manifest_v2.json` bindings;
3. rehash every transitive G-0128 manifest input and reconstruct the exact `301 + 11 + 4 + 32 + 32 = 380` row order and unscaled target;
4. require `records=163740`, the complete terminal transcript, and the exact terminal certificate shape fixed by G-0128;
5. independently replay the 380-row member or separator certificate before using it; and
6. rehash the result and all inputs immediately before G-0132 publication.

The G-0132 manifest binds this preregistration, its Git commit, the future G-0128 result hash, every prior binding above, the eventual G-0132 source/Cargo/executable hashes, the selected branch, output path, environment, and exact algorithm parameters. It is created once with no-overwrite semantics after branch admission and before scientific computation.

## MEMBER arm — complete global normal-form replay

### Exact question

For the exact primitive nonzero terms and positive target scale `L` serialized by G-0128, is

```text
sum_s a_s F_s(x) = L * 11! * max(x_0,...,x_10)
```

an identity for every `x in R^11`, where `F_s` is the full labelled `S_11` orbit function of frozen record `s`?

### Frozen computation

The producer must reconstruct every term from the G-0128-bound record inputs, not from cached 380-row columns. For every supported term it computes the **complete** ordered-chamber normal form

```text
F_s(x) = sum_d h_d(s) ReLU(d.x) + sum_(r=0)^10 ell_r(s) x_r
```

with arbitrary-precision integers. It must cover every labelled orbit contribution (whether by literal enumeration or an exactly reconciled DP), aggregate every primitive active zero-sum direction after the G-0117 orientation/gcd rules, retain all 11 linear coordinates, and subtract `L*11!` only from coordinate 10. No finite row list, modular screen, sampled direction set, previous support pattern, tolerance, or floating arithmetic may decide the result.

The complete aggregate has exactly two outcomes:

- `MEMBER_EXACT_GLOBAL_NORMAL_FORM_ZERO`: zero on every hinge direction and all 11 linear residuals;
- `MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL`: the signed-lexicographically first nonzero primitive hinge and coefficient, or the first nonzero linear coordinate if all hinges vanish.

An exact zero establishes only this frozen orbit identity, using the pinned normal-form uniqueness lemma and symmetry. It stops before architecture compilation. A residual refutes only this member vector; it does not prove frozen-family nonmembership. Any new residual-row CEGIS, matrix compilation, independent network replay, or Lean work is a separately preregistered study.

The sole MEMBER output is

```text
artifacts/math/G-0132/member_global_normal_form_replay_v1.json
```

## NONMEMBER arm — complete degree-five separator pricing

### Exact question

Let `y in Z^380` be the primitive separator admitted from G-0128, and let `R_380` be the exact frozen row operator. For every canonical generator `g` of the complete loop-inclusive degree-five pair-max span, compute

```text
price(g) = y^T R_380(g)
```

over arbitrary-precision integers.

The producer must first re-establish `y^T b != 0` and exact zero prices on all 163,740 frozen G-0128 columns. It then independently evaluates all 301 formal-colour panel functionals, all 11 ordered-chamber linear coordinates, and all 68 frozen hinge coordinates on each full-family generator. It may reuse the frozen row descriptions and denominator bytes, but may not import or call the G-0128 master or G-0040 pricing implementation. Exact batching and parallelism may change throughput only; each scalar decision remains an integer dot product.

### Complete generator order and semantics

The scientific order is:

1. G-0038 stream sequences `0,1,...,7,015,840`, with every record validated in byte and semantic order;
2. explicit `5E` (`five-common-nonloops`);
3. explicit `5L` (`five-common-loops`).

Thus the result contains exactly 7,015,843 price decisions. The signed-mass-zero stream record uses canonical nonloop padding and must price identically to the separately evaluated `5E`; retaining both evaluations is an intentional semantic control.

For a signed record `W=B'-A'` of mass `s`, the canonical stream column is the full orbit atom with `5-s` common nonloop pads and zero common-loop pads. Hinge coordinates come from `W`; the linear coordinates include its exact base and orientation correction. The explicit `5E` and `5L` columns are hinge-free. The G-0028/G-0044 transfer

```text
column(W,c) = column(W,0) + c*(L-E),   0 <= c <= 5-s
```

is the reason canonical records plus both bases span every loop-inclusive degree-five padding choice. This is a span statement over characteristic zero, not a cone statement.

Every price is serialized into a canonical generator-tag/signed-decimal-LF digest. The output records the complete census, zero/nonzero counts, exact extrema, per-stratum price digests, the aggregate digest, both base prices, the first nonzero generator in the frozen order when one exists, and enough exact coordinates to replay that first discrepancy. Pricing continues through all generators even after a nonzero price; early exit is forbidden.

Exactly one outcome is allowed:

- `FULL_DEGREE5_SEPARATOR_ESCAPE`: at least one exact nonzero price. This proves only that the G-0128 separator does not extend to the complete degree-five span and supplies an omitted violating column. It does **not** prove that the complete family contains MAX11.
- `FULL_DEGREE5_SEPARATOR_ANNIHILATES`: all 7,015,843 prices are exactly zero while `y^T b != 0`. Subject to the denominator/transfer and row-semantics bindings, this excludes MAX11 from the real span of the complete degree-five pair-max dictionary. It does **not** exclude arbitrary two-hidden-layer networks.

The sole NONMEMBER output is

```text
artifacts/math/G-0132/full_degree5_separator_pricing_v1.json
```

## Mandatory controls and hostile mutants

Before either scientific output, the selected producer must pass both the valid and deliberately broken direction of every applicable control.

### Common custody controls

- Reject wrong/unknown G-0128 schema or result enum, selecting both arms, result/source/preregistration/manifest drift, missing transitive inputs, row-order/target drift, path or symlink escape, duplicate resolved inputs, stale executable, and pre-existing manifest or output.
- Reject malformed canonical integers, duplicate/out-of-range sequences, zero-padded support, omitted final term/row/record, reordered inputs, partial gzip/JSON, serialization failure, and any exception converted into a scientific outcome.
- Recheck the G-0128 `+1` terminal-certificate mutant and require it to fail its 380-row certificate.

### MEMBER controls

- Reproduce one known exact zero aggregate and the planted G-0117 nonzero normal-form certificate by two independent routes.
- A `+1` mutation of the first member coefficient, `L`, the final nonzero term, or target coordinate 10 must produce a nonzero complete residual.
- Omitting the last supported term, the last orbit contribution, one active direction, or one linear coordinate must be detected by reconciled censuses/digests.
- Direction sign, gcd, branch-swap, relabelling, linear-orientation-correction, and exact target-subtraction mutants must disagree.
- If modular screens are used for throughput, a planted nonzero residual divisible by every screening prime must still be found by the mandatory exact pass.

### NONMEMBER controls

- Replay all 163,740 frozen columns at exact zero and the target at exact nonzero before entering the larger stream; a separator or row-binding mutation must break this known answer.
- A zero separator must price every generator at zero but must be rejected because its target pairing is zero.
- A far-tail fixture with its sole violating generator at the final admissible sequence must be recovered by the unchanged scan, while an unchanged registered empty slice returns no violation and all counts reconcile.
- Reject truncation at the gzip trailer or final record, sequence duplication/reorder, stratum count/digest drift, compressed or canonical digest drift, record-sign mutation, and generator/verification binding drift.
- Loop-diagonal omission, treating a loop as a two-endpoint edge, branch swap, relabelling, common-padding mutation, omitting or swapping `5E`/`5L`, and failure of stream-sequence-zero/explicit-`5E` equality must disagree.
- A `+1` mutation of the first serialized price or first nonzero separator entry must be caught by exact replay or aggregate digest/certificate checks.

## Atomic custody and stop rules

The selected result is pre-serialized in memory, written to an exclusively created same-directory temporary file, flushed and fsynced, and published by a no-overwrite atomic hard link followed by directory fsync. Source, executable, preregistration, branch manifest, G-0128 result, denominator, and transitive inputs are rehashed immediately before publication. Any validation, control, arithmetic, census, resource, serialization, or publication failure leaves no final-path result. The unselected output path must remain absent.

Stop after exactly one selected-arm output. Do not automatically add a violating column, rerun a master, compile a network, claim an unrestricted two-hidden-layer theorem, claim the all-`n` charter target, open a Lean development, or formalize a finite-row cousin. In particular:

- MEMBER zero -> frozen global orbit identity only; compilation and independent matrix replay remain open.
- MEMBER residual -> this coefficient vector is false globally; family status remains open.
- NONMEMBER escape -> this separator is subfamily-specific; complete-family membership remains open.
- NONMEMBER annihilation -> complete degree-five real-span obstruction only; `GNF` and `DR5-MAX` remain open before any unrestricted lower bound.
