# G-0116 / G-0113 clean-room audit verdict

## Typed verdict

- **G-0116 frozen evaluator:** `PASS_BOUNDED` for source SHA-256
  `875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd`
  on the exact bound input and row documents.
- **Superseded G-0113 scanner:** `FAIL_INVALID` for source SHA-256
  `89ee08b1b6def2a07b351e6f5a7ba6a8d8819f94d8127fbd9169beb9fdf7e8f8`.
  It could hide a DISJOINT-boundary modular disagreement behind later union
  agreement.  The run was stopped before its first 5,000-record checkpoint
  and wrote neither scientific output.
- **Corrected G-0113 scanner:** `PASS_TO_RESTART` for source SHA-256
  `8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f`.
  Both boundary conjunctions, their four component flags, the hostile
  stage-disagree/final-agree regression, the abort record, and the refreeze
  were independently inspected and replayed.

This permits the corrected finite 301-row scan to run.  It is not evidence of
its eventual rank or membership result.

## Evidence that changed confidence

The preregistered clean-room producer is
`cleanroom_audit.py` (SHA-256
`5177b7235df2f33bddfe10eb9f336a59a123d95b14d16ac19b22262d9c5a8bcf`).
Its retained result `cleanroom_audit_v1.json` has SHA-256
`17ff9504cd4d022cdaf360e192f548f166ffe6c29be2ca87d3190ecaad801e52`.
An immediate independent re-execution produced the identical file hash.

The disjoint evaluator did not use G-0116's signed-q/ReLU rewrite.  It
enumerated active colours, retained both branch edge-count words, and summed

```text
max(S_A', S_B') + (5-s) * E_fixed_nonloop
```

directly.  It reproduced the complete 301-entry little-endian-i128 vector
hashes:

| control | coverage | clean-room = official |
|---|---|---|
| sequence 0 | signed mass 4, active 8, inactive-label fills and one common nonloop | `f09264dc...a3c58` |
| sequence 3 | signed mass 5, cyclic, active 11 | `475f46c4...d2099` |

On rows 0, 150, and 300, a second literal recursion over distinct full formal
assignments (990, 9,240, and 990 assignments) reproduced the corresponding
entries for both controls.  A post-hoc raw-pair check also evaluated the
uncancelled five-edge `representative_pair` for orbit 0 directly and obtained
the same three sequence-0 values (`1,269,724`, `11,443,500`, `1,164,404`).
This separately checks the signed-W/common-nonloop transfer at a nontrivial
common-edge record; it was confirmatory after the primary result and is not
being presented as preregistered evidence.

All 163,740 prepared records were checked independently.  Every record is
compact and loopless, its cancelled sides are disjoint with equal declared
occurrence mass, and its unique absolute support has cycle rank at most four:

```text
beta 0: 36,853   beta 1: 84,826   beta 2: 36,820
beta 3:  5,143   beta 4:     98
```

For every record, choosing one endpoint of each non-tree edge produced a
feedback set no larger than the cycle rank and deletion left a forest.  A
separate exact minimum-FVS enumeration on all eight official controls matched
G-0116's reported sizes entry-for-entry: `0,1,1,1,0,0,2,0`.

All 301 rows have four strict levels beginning at zero, positive formal
profiles summing to 11, and the exact formal stabilizer.  The recomputed target
hash is `19beb89b...f260`, matching the G-0113 preparation.

Official G-0116 semantics were stable under default, 4-thread, and 12-thread
Rayon replays: after deleting timing-only fields, all three reports had the
same SHA-256 `0a5a9b14...d8fd50e`.  The 12-thread run used by G-0113 passed the
10x performance gate in this audit (`21.20x` median).

For corrected G-0113, the independent commands

```text
cargo test --release --manifest-path artifacts/math/G-0113/Cargo.toml
cargo clippy --release --all-targets --manifest-path artifacts/math/G-0113/Cargo.toml -- -D warnings
```

ran 4 tests with 0 failures and passed clippy.  The planted regression gives
different DISJOINT p1/p2 states and identical union states; the combined
predicate correctly remains false.  The corrected refreeze binds the source
above and the abort record SHA-256 `227d11cc...c4c1`; both old output paths
were absent before restart.

## Residual limitations and obligations

1. G-0116's internal “exhaustive” route shares edge parsing, signed-q, state
   packing, and panel folding with its accelerator.  It is an algorithmic
   cross-check, not semantic independence.  The literal audit above supplies
   only two full-vector semantic controls, not 163,740 exhaustive replays.
2. The standalone G-0116 executable records input/source/row hashes but does
   not compare them with hard-coded expected hashes, and it relies on the
   frozen row file for `levels[0] = 0` and strict ordering.  Reuse on arbitrary
   files is not certified.  The corrected G-0113 consumer closes this for the
   intended use by enforcing all three exact SHA-256 bindings before scanning.
3. With `RAYON_NUM_THREADS=1`, every semantic hash remained identical but the
   timing gate failed (`7.627x` median).  Performance is environment-dependent.
   G-0113 explicitly constructs a 12-thread pool; the mathematical values do
   not depend on the thread count.
4. `cargo test` for G-0116 itself ran zero unit tests.  It is not counted as a
   correctness result; the outcome-bearing binary controls and the clean-room
   evaluator are the evidence.  G-0113's corrected test target did run four.
5. This is a fresh-context same-model-family (`T1`) audit.  It is not T2
   independent refereeing and cannot promote a load-bearing theorem claim.

## Claim boundary

The audit supports exact evaluator semantics on two deliberately different
frozen controls, the low-cycle precondition over the complete prepared input,
and correct integration/reporting logic at the two modular boundaries.  It
does **not** establish the all-record rank, finite-panel target membership,
characteristic-zero membership or nonmembership, a global CPWL identity, a
Rueß-family completeness theorem, unrestricted two-hidden-layer behavior, or
MAX11.

The required anti-ceremony creation gate, real-work audit, and honesty
inventory are recorded separately in `HONESTY.md` so this scientific verdict
stays reviewable.
