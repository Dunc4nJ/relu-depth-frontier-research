# G-0131 preregistration — fresh-context T1 audit of the G-0128 terminal result

## Freeze, identity, and blind boundary

- Registered: `2026-08-31T03:52:47Z`, before any G-0128 scientific result existed or was disclosed to this reviewer.
- Reviewer: `LavenderCreek` (Codex / GPT-5; fresh context, same model family; T1 only).
- Campaign binding: mathematics, W1 dual prove/refute. This is a bounded adversarial result audit inside that campaign, not an independent proof campaign and not T2 review.
- Scientific source: `artifacts/math/G-0128/full_family_master_v2.py`, frozen SHA-256 `cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8`.
- Cleared source-audit anchor: commit `2269652fc689519220ecfcef028519b8ac6283e5` (`2269652`). The source audit does not predetermine this result audit.
- Sealed manifest: `artifacts/math/G-0128/full_family_master_manifest_v2.json`, SHA-256 `79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec`, committed at `3676d68e14815296c9c424837625993ea4d0c3d2`.
- Forbidden before this document is committed, pushed, and reported to the orchestrator: any G-0128 scientific result, result log, branch label, witness, separator, coefficients, support, transcript, digest derived from the result, or prose that reveals the outcome.

At freeze time the reviewer had inspected campaign operating documents and earlier review preregistrations, but had not opened, parsed, hashed, listed the fields of, or inferred the branch of any G-0128 scientific result. No G-0128 scientific computation will be run by this reviewer. After the preregistration commit is reported, work remains paused until the orchestrator explicitly states that the result exists and releases its path and custody anchor.

## Exact bounded question

Does the delivered G-0128 result, when checked independently from the frozen manifest and inputs, establish exactly one of these two finite-system conclusions?

1. `MEMBER`: the frozen target is an exact rational/integer-normalized linear combination of the frozen 163,740-column family on every one of the 380 registered rows; or
2. `NONMEMBER`: a primitive exact separator annihilates or has the required orientation on every one of the 163,740 frozen columns while pairing nontrivially with the independently reconstructed 380-row target.

No audit outcome may be read as a global functional identity or obstruction, a MAX11 settlement, an unrestricted two-hidden-layer ReLU theorem, family completeness, or a Lean-checked theorem.

## Common custody and schema obligations

Before interpreting either branch, the audit will fail closed unless all of the following are established independently:

1. Rehash the result, manifest, scientific source, preregistration, and every transitive input actually consumed. Check every manifest path, byte size, lowercase SHA-256, type, count, dimension, and order assertion.
2. Confirm the scientific source bytes equal the frozen source SHA above and descend from the source-audit anchor. Any source or manifest drift, uncommitted substitution, symlink/path escape, missing input, duplicate record, malformed integer, or ambiguous serialization is a hard custody failure.
3. Require one unambiguous terminal branch and reject mixed, incomplete, unknown, or internally contradictory branch payloads.
4. Parse all decision-bearing numbers as exact canonical integers/rationals. Reject floats, modular-only equality, lossy coercions, booleans accepted as integers, noncanonical decimal spellings, and denominator/sign ambiguity.
5. Reconstruct the 380-row order and target from frozen inputs without importing the result's target vector, result support, result coefficients, or result separator.
6. Recompute every claimed digest from its documented canonical byte serialization. A digest whose serialization is not preregistered or unambiguous is `CANNOT_VERIFY`, never guessed.
7. Verify transcript continuity, uniqueness, in-range indices, and correspondence between transcript order, support order, selected columns, coefficients, and any basis/rank metadata. No top-level receipt may stand in for mutable transitive payloads.
8. Use an independently written checker that does not import or execute the G-0128 scientific source. The checker will have deterministic positive and must-fail self-tests and will create its own audit receipt exclusively.

## Branch A — MEMBER audit fixed in advance

If and only if the delivered branch is `MEMBER`, the reviewer will independently reconstruct the frozen target and every supported family column and replay the claimed identity on **all 380 rows** in exact arithmetic. The audit will require:

- support indices that are unique, strictly increasing in canonical family order, in `[0, 163740)`, and exactly equal to the nonzero coefficient positions;
- exact support/column pairing, with no hidden zero coefficients, omitted terms, reordered indices, duplicate cancellation, or result-supplied column values trusted as inputs;
- a positive target scale, canonical denominator clearing, and primitive normalization: the gcd across the target scale and all nonzero integer coefficients is exactly one, with the prescribed sign orientation;
- independent reconstruction and equality of every declared support, coefficient, selected-basis/transcript digest, target digest, and result-level scientific-payload digest whose serialization is specified;
- exact coordinate-by-coordinate equality on rows `0..379`, with the first mismatch reported and no sampled substitute described as a 380-row replay;
- exact validation of any reported rank/basis transcript needed to justify how the member was obtained, including strict pivot growth and a final exact solve when those fields are part of the result contract; and
- a precommitted equality-destroying mutant, minimally the first nonzero coefficient changed by `+1` (or an equally explicit deterministic mutation if the schema forbids that edit), which must be rejected on the actual terminal replay path and record its first failing row.

A consistent finite-row member is only a candidate for a separate global check. The audit will explicitly require a **new, separately committed preregistration** for an independent complete global replay before any global identity language is permitted. That replay must be independent of this 380-row checker and must bind the compiled functional semantics, full domain/chamber coverage, exact architecture conversion, and its own hostile mutant. This G-0131 audit will not silently turn the required later replay into a post hoc extension of the present plan.

## Branch B — NONMEMBER audit fixed in advance

If and only if the delivered branch is `NONMEMBER`, the reviewer will independently reconstruct the exact 380-row target and separator and will independently reprice **all 163,740 columns** in canonical family order. The audit will require:

- a separator of length exactly 380, parsed independently and paired with the independently reconstructed target rather than a result-supplied copy;
- exact primitive normalization of the separator, including gcd one, canonical overall sign, no all-zero vector, and any registered denominator clearing;
- exact nonzero target pairing with the preregistered orientation and magnitude, recomputed from the 380 independently reconstructed target entries;
- exact price recomputation for column indices `0..163739`, including the first and final columns, with generated/visited totals equal to 163,740 and no skipped, duplicated, cached-as-authoritative, exception-swallowed, or short-circuited column;
- the required exact sign/zero condition on every repriced column, with the first violating index, reconstructed column identity, and exact price reported if one exists;
- transcript continuity and canonical pairing among family indices, family records, reconstructed columns, prices, separator entries, and every reported scan/basis digest;
- recomputation of the target, separator, pricing-transcript, normalization, and scientific-payload digests from documented canonical serializations; and
- deterministic hostile controls on the actual terminal decision path: at minimum a primitive separator/target-pairing mutation and a column/transcript mutation, each of which must force rejection rather than merely alter a digest.

Any inability to independently reconstruct even one row or price even one declared column prevents a `CONSISTENT_NONMEMBER` verdict. A partial or sampled scan is not all-column separation.

## Adversarial lenses and stopping rules

The audit will attack, in consequence order:

- result/manifest/source/input custody drift after the frozen anchors;
- a 379-row replay or 163,739-column scan presented as complete;
- target copied from the result rather than independently derived;
- support/coefficient or separator/row-order mispairing;
- nonprimitive normalization, sign reversal, or denominator-clearing mistakes;
- transcript indices that refer to a different canonical family ordering;
- digests over summaries rather than the decision-bearing bytes;
- cached prices or columns trusted instead of independently reconstructed;
- hostile mutants that bypass the terminal acceptance predicate;
- an exception, early exit, or duplicate silently reconciled into a complete count; and
- prose that promotes a finite exact result across the finite-row/global, frozen-family/unrestricted, MAX11, or informal/Lean boundaries.

One `BLOCKER` in a decision-bearing path ends the corresponding consistency verdict. Resource exhaustion, undocumented serialization, or unavailable transitive input yields `CANNOT_VERIFY` with the exact first unmet obligation; it never licenses sampling or a weaker claim under the same label.

## Verdict vocabulary and promotion refusal

- `CONSISTENT_MEMBER`: every common and MEMBER obligation above passed exactly.
- `CONSISTENT_NONMEMBER`: every common and NONMEMBER obligation above passed exactly.
- `INCONSISTENT`: at least one reconstructed fact contradicts the delivered terminal result or a hostile mutant reaches acceptance.
- `CANNOT_VERIFY`: custody, specification, resources, or missing artifacts prevent completion of a precommitted obligation.

Findings will be graded `BLOCKER`, `MAJOR`, `MINOR`, or `NOTE` by consequence. Byte-identical reproduction is not correctness. Same-family fresh-context agreement is at most T1 and cannot promote any claim to `REFEREED` or `FORMALIZED`. Regardless of branch, G-0131 refuses promotion to global equality/nonmembership, MAX11 settlement, unrestricted two-hidden-layer representability/nonrepresentability, family completeness, or Lean theorem status.
