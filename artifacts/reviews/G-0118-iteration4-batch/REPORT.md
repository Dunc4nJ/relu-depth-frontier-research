# G-0118 iteration-4 Batch32 adversarial review

## Verdict

`CONSISTENT_WITH_PROVENANCE_LIMITS`.

This fresh-context, same-lineage T1 review found no arithmetic, ordering, binding,
or schema discrepancy in the sealed candidate-4 global replay or its Batch32
exact-price artifact.  The evidence strongly supports the producer's narrow
claim: candidate 4 satisfies the frozen 316-row finite system but is refuted by
the first globally discovered direction, and every one of the 32 selected batch
directions has a nonzero exact residual.

This is not T2 independence and is not a MAX11 theorem, lower bound, global
identity, novelty claim, or proof that the frozen 163,740 records exhaust the
intended family.

## Independent checks

The reviewer did not import or execute the producer Rust.  A fresh C++20
implementation used an active-vertex rank-injection dynamic program for prices
and a separate labelled-permutation subset-histogram replay for the global
search.  Python arbitrary-precision dot products supplied the exact bridge.

- Recomputed all 36 frozen hinge-price rows on all 163,740 records:
  5,894,640 entrywise comparisons, all equal.
- Recomputed all 11 linear prices on all 163,740 records:
  1,801,140 entrywise comparisons, all equal.
- Replayed all 316 finite candidate constraints exactly: 301 panel rows, four
  accumulated rows, and 11 linear rows.  Every residual is zero.
- Recomputed the four accumulated-direction residuals exactly; all are zero.
- Recomputed all 32 selected residuals as arbitrary-precision integers; every
  residual is nonzero.  All 64 reductions modulo the two frozen primes agree
  with the producer.  The LF residual stream has 3,431 bytes and SHA-256
  `98f507b0d4277018a7d704c951c1e6b3cac10243b59c3df407b5a195d0e9686b`.
- Independently replayed 4,071,513,600 labelled permutations.  The replay
  processed 3,585,323 hinge entries, found aggregate support 172,454 and
  172,430 nonzero hinge directions, and reproduced the producer's first 32
  normalized directions and both residues.
- Validated 163,740 unique ordered record digests, stage and active-vertex
  censuses, sequence numbers, cache prefix, principal artifact hashes, and the
  candidate/recheck core-field equality.

The review implementation first passed a literal small-instance differential:
55,440 explicitly enumerated injections agreed with both targeted hinge and
linear dynamic programs.  Coefficient, direction, record, row-order,
selected-order, and one-byte payload mutations were rejected.  A valid unseen
direction changed both its price row and candidate residual relative to the
first selected row.

## Interpretation

This closes a serious failure mode: the Batch32 refutation is not merely a
self-report from the producer executable.  A disjoint semantic implementation
reproduces the global counters, exact price matrix, and exact candidate
residuals.  Candidate 4 should therefore be treated as genuinely refuted within
the frozen record universe.

The scientific value is negative but material.  It eliminates a plausible
finite-panel solution and demonstrates that the global separator can find many
violations invisible to the 316-row system.  It also identifies the next
high-leverage direction: improve the master/search representation or derive a
structural obstruction, rather than spending more effort rechecking candidate
4.

## Provenance and claim limits

- The review is same-lineage T1.  A different model lineage or human referee is
  still required for T2.
- The frozen record set and order were exhaustively checked, but the upstream
  assertion that these 163,740 records are the complete intended family was not
  independently regenerated.
- Candidate-bound
  `artifacts/math/G-0118/iteration3_residual_coordinate_v1.json` is currently
  untracked in Git.
- Historical producer executable hashes cannot be rehashed because those
  binaries were not archived.
- The 788,571,840-byte cache payload is intentionally untracked; its current
  bytes match the committed manifest SHA-256
  `da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b`.
- After preregistration, commit `52c1e2c` corrected only handoff prose from 305
  rows to 316.  Neither sealed scientific JSON payload changed.

## Receipt

Machine-readable evidence is in `review_v1.json`.  The review preregistration,
source, compiled binary, C++ output, input descriptor, and both producer payloads
are SHA-256 bound there.  The sealed producer payload hashes are:

- replay: `c402c0c9e89c2d8a95fc8b40c44346f9eaeae3c2ade5a7662d97cda04680ad80`
- exact prices: `349e63a7a2f254a2b0d4c05a4ce4c088afa7ff859675876e2b8c3bac05b6547b`

A second full run produced a byte-identical receipt, SHA-256
`e7905d258ed05e004c51b449494c9cd7094e967cdf3c29380646f55caaf2b569`.
