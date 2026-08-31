# G-0135 preregistration — exact Batch32 CEGIS generation after G-0132

## Decision target

This study asks one bounded question about the frozen 163,740-record degree-five
family used by G-0128:

> After adjoining the signed-lexicographically first 32 exact nonzero global
> hinge residual directions of the G-0128 380-row member, is MAX11 in the exact
> rational span of all 163,740 frozen columns; and, if so, does the resulting
> member have identically zero ordered-chamber normal form over the complete
> labelled `S_11` replay?

The generation is deterministic.  No modulus, magnitude, sparsity, apparent
rank, or post-result judgment may choose or discard a row.

## Prior-result admission gate

No scientific stage may run unless the preregistered G-0134 clean-room result
audit independently recomputes the G-0132 first residual and publishes `PASS`
for the exact direction, coefficient, candidate, census, and custody chain.
The future generation manifest must pin the audit path, SHA-256, and Git commit
before any scientific output exists.  A failed or incomplete audit terminates
this study with no scientific result.

Already observed and therefore declared rather than hidden:

- G-0132 result path:
  `artifacts/math/G-0132/member_global_normal_form_replay_v1.json`
- G-0132 result SHA-256:
  `d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50`
- result: `MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL`
- terms: 132
- complete labelled permutations: 5,269,017,600
- aggregate hinge support: 163,036
- nonzero hinge directions: 162,929
- first signed-lexicographic nonzero direction:
  `[0,0,0,0,0,0,1,-3,-2,1,3]`
- first exact coefficient:
  `363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360`

The known first residual motivates this continuation but does not determine the
other 31 rows.  Their selection rule is frozen below before they are emitted.

## Frozen ancestors

- G-0128 member result:
  `artifacts/math/G-0128/full_family_master_result_v2.json`, SHA-256
  `17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838`
- G-0128 master manifest:
  `artifacts/math/G-0128/full_family_master_manifest_v2.json`, SHA-256
  `79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec`
- G-0132 replay manifest:
  `artifacts/math/G-0132/member_global_normal_form_manifest_v1.json`, SHA-256
  `b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732`
- G-0132 source:
  `artifacts/math/G-0132/src/main.rs`, SHA-256
  `27400fe972986ea29ff245059f6011bbf1a146511d30cfecbdfdd834c3a5115e`
- G-0133 source-audit receipt:
  `artifacts/reviews/G-0133-g0132-source/SOURCE_AUDIT_RECEIPT.json`, SHA-256
  `8027f630749c3b4ce5611945d63cc526c09042c0b8f66baee1d1e9fc2c61efca`
- G-0127 pricer source ancestor:
  `artifacts/math/G-0127/src/main.rs`, SHA-256
  `68a9062fa28a5ad5da614634066685cc7e66f709fe6309f553317b483ba23cd8`
- G-0128 exact-master source ancestor:
  `artifacts/math/G-0128/full_family_master_v2.py`, SHA-256
  `cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8`

All remaining transitive inputs must be rehashed and recorded by the future
one-shot generation manifest.  The manifest, frozen stage sources, source-audit
receipt, and executables must be committed before the first scientific stage.

## Stage A — complete exact replay and Batch32 selection

Reimplement only the generic exact arithmetic path already exercised in G-0132;
do not modify G-0132 in place.  Project the G-0128 member to its 132 nonzero
terms, compute each term's complete labelled-orbit ordered-chamber normal form,
sum with arbitrary-precision integers, and subtract the target in the pinned
linear coordinate.

The replay must reconcile exactly:

- 132 accepted terms;
- 5,269,017,600 labelled permutations;
- all per-term generated/visited/accepted counts;
- zero skipped, failed, or unclassified cases;
- all 68 previously accumulated hinge directions equal zero;
- all 11 linear residuals equal zero;
- aggregate hinge support 163,036;
- nonzero hinge count 162,929;
- the G-0132 aggregate and nonzero residual stream digests;
- the G-0132 first direction and coefficient above.

Any disagreement is `INVALID_NO_SCIENTIFIC_RESULT`, not a new mathematical
outcome.

For selection, collect every primitive active hinge direction with nonzero
exact `BigInt` coefficient after target subtraction.  Sort the eleven signed
`i8` coordinates by ordinary tuple lexicographic order and take the first 32.
Each emitted row is exactly
`{direction:[i8;11], exact_residual:canonical_signed_decimal}`.
The receipt separately hashes:

1. the concatenated 11 signed bytes per direction in receipt order; and
2. each canonical signed decimal coefficient followed by LF.

Directions must be unique, valid primitive active directions, strictly ordered,
nonzero, and absent from the 68 accumulated hinge rows.  Exactly 32 must be
emitted.  A nonzero linear residual or fewer than 32 eligible hinge residuals
invalidates this protocol rather than changing it after inspection.

## Stage B — exact all-record coordinate pricing

In one pass over the same 163,740 frozen records, compute the 32 selected hinge
coordinates using the pinned normal-form specification.  Each atomic coordinate
is checked `i64`; every candidate dot product and residual comparison is an
arbitrary-precision integer.  Transpose to 32 direction-major rows, with exactly
`32 * 163740 = 5,239,680` coordinates.

For every row, the exact dot product against the G-0128 132-term member must
equal Stage A's exact residual.  Record order, row order, row digests, signed
extrema, nonzero counts, and the complete direction-major digest are mandatory.
No row is filtered for dependency or apparent usefulness.

## Stage C — exact 412-row full-family master

Use the validated G-0128 380-row system as an immutable prefix and append the 32
Stage B rows in receipt order.  The target is the original unscaled 380-entry
target followed by 32 exact zeros.  A previous member's cleared denominator is
never used as the new target scale.

Warm-start with all 176 G-0128 selected sequences, while reopening all 163,740
columns.  Verify the old 380-row rank and identity, verify that the appended
rows reject the old member, then run the exact-Q all-column algorithm:

1. compute exact matrix and augmented ranks;
2. if the target is outside the current span, derive an exact left separator;
3. scan every frozen column in canonical sequence order for the first nonzero
   separator price;
4. append that column and require an exact unit rank increase;
5. repeat until an exact member is obtained or a separator survives all
   163,740 columns.

No support freeze, zero-price-column deletion, modular terminal decision, row
dependency deletion, or preferred-sparsity search is permitted.  On membership,
replay all 412 rows over `Q`, clear denominators primitively, and replay the
integer identity.  On nonmembership, replay the separator against every column
and require nonzero target pairing, plus sign/coordinate mutants that fail.

## Stage D — global replay of a new member

If and only if Stage C returns an exact-Q member, apply the same complete exact
normal-form replay and controls as Stage A to that new member.  This stage has
only two scientific branches: exact global zero or an exact nonzero residual.
On a residual, emit the next signed-lexicographic Batch32 by the same frozen rule
for a separately checkpointed generation; do not silently continue inside this
study.

## Terminal scientific outcomes

Exactly one of these may be published:

1. `GLOBAL_EXACT_ZERO`: a complete exact ordered-chamber normal-form identity
   for the returned frozen-family member.  This triggers network compilation,
   independent replay, statement-match review, and Lean formalization.
2. `FROZEN_163740_FAMILY_EXACT_Q_NONMEMBER`: an exact 412-row separator that
   annihilates every one of the 163,740 frozen columns and pairs nontrivially
   with the target.
3. `EXACT_RESIDUAL_BATCH_CONTINUE`: an exact 412-row member whose complete
   global replay is nonzero, together with its deterministic next Batch32.

Validation, custody, resource, source-audit, or mutation-control failures are
`INVALID_NO_SCIENTIFIC_RESULT` and carry no mathematical conclusion.

## Controls and independent checks

Before publication, each stage must pass a positive known-answer fixture and
must reject at least: a coefficient-plus-one mutant, an omitted orbit/record,
row and direction reordering, a residual-decimal mutation, a target-scale
carryover, a truncated record census, and a separator mutation.  Inputs are
rehashed at the end of each stage and outputs are atomic/no-overwrite.

The frozen sources receive outcome-blind source review before execution.  Any
terminal scientific outcome receives a clean-room result review that derives
the decisive identity/residual/separator independently rather than rerunning
the author's executable.  Same-lineage agent agreement remains T1 and is not
mislabelled T2.

## Claim boundary

`GLOBAL_EXACT_ZERO` establishes only the explicit frozen symmetric-orbit
functional identity and the concrete two-hidden-layer network compiled from it.
It does not prove completeness of the 163,740-record family, a lower bound,
minimal width, an all-`n` theorem, or an unrestricted classification.

`FROZEN_163740_FAMILY_EXACT_Q_NONMEMBER` excludes only this frozen family under
the exact 412-row separator.  It does not exclude other degree-five records,
asymmetric constructions, deeper networks, or unrestricted two-hidden-layer
ReLU representations.

Lean work begins only after a statement-matched exact zero identity exists.
The Lean theorem must mention the concrete compiled network and prove equality
to MAX11 under the repository's actual network semantics; formalizing a generic
compiler conditional on an unproved identity does not complete the target.
