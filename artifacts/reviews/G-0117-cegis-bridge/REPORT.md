MATERIAL_INCREMENT

# G-0113 -> G-0117 exact-global CEGIS bridge audit

## Typed verdict

**Overall: `PASS_WITH_OBLIGATIONS` — the exact replay and normal-form uniqueness seam now pass
bounded adversarial review, but no real G-0113 member has entered the bridge and the full cache /
fresh-Q CEGIS loop is not yet operational.**

Sub-verdicts:

- `PASS_BOUNDED`: denominator clearing, exact BigInt aggregation, exact-zero / hinge / linear
  branching, nonzero-modular-residual logic, panel/global normalization, the normal-form uniqueness
  lemma, and the proposed full-column exact-Q residual-row loop.
- `RESOLVED_EXECUTED`: the former stale-binary and permissive-schema defects.  Rebuilt standalone
  binaries reject unknown fields, mismatched receipts, stale source, stale kernel/lemma inputs, and
  old forged certificates without writing scientific output; emitted results bind the executable,
  source, kernel, and uniqueness lemma.
- `PASS_WITH_OBLIGATIONS` for provenance: the production converter now rehashes the real artifact
  chain and cleanly reruns the exact postprocessor, but the replay layer checks only the receipt's
  syntax and self-consistency.  A real subject and its source artifacts remain necessary.
- `INDETERMINATE` for a scientific MAX11 result: the machinery can now decide a supplied sparse
  certificate exactly, but the planted controls are deliberately non-identities and no live exact-Q
  panel member has yet been handed to it.

This is fresh-context, same-model-family T1 review.  It cannot satisfy the campaign's unavailable
T2 promotion gate.

## Post-fix review update (current cut)

The post-fix tests were frozen in `POSTFIX_PREREGISTRATION.md` before the new exact implementation
was inspected.  `postfix_checker.py` is an independent Python control; its passing receipt is
`postfix_controls.json` (`82656d3a...017b`).

Current bound objects:

```text
global_exact_replay executable:    3dcb3b43c4075f1206ecda874bd9013dd9328eb67e1b9a2f59b21391882c4574
global_exact_replay source:        1232548952fee91827f8dfddf26dd01eacfc49c57a448f6d258add9b778f414a
global_modular_replay executable:  7c8c83b668026e1e15be89a1459c8e23c79937582d245464ce0a6b5e49b9925b
global_modular_replay source:      d27ece785362d84aea134e04893449f4bca926243aba29ec4fef377fb7a7003e
normal-form kernel:                84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa
normal-form uniqueness lemma:      39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17
exact-replay preregistration:      a76f3ee0bf77f8c5a2180830b2879cf9b1b75fbac797a166a19fb605706a0a12
```

Fresh executions against these exact binaries established:

- the planted certificate's first exact hinge residual is `662784`; changing its first coefficient
  from 7 to 8 gives the preregistered `786432` mutant;
- an independent targeted subset DP gives `h_0=123648` and `h_1=33792`, hence
  `7 h_0 - 6 h_1=662784` and `8 h_0 - 6 h_1=786432`; independent linear DPs reproduce every one of
  the 11 emitted exact linear coordinates;
- sequence 5341 has zero hinge support under independent literal active-rank enumeration and reaches
  the genuine linear fallback, whose first residual is coordinate 1 with coefficient `2903040`;
- a 79-digit coefficient, larger than `2^256`, produces exactly `123648` times that coefficient at
  the first hinge, with all hinge and linear values agreeing with their reductions modulo both
  replay primes;
- the production exact accumulator's synthetic cancellation reaches exact zero, while independent
  hinge and linear mutants remain nonzero.  This is a unit-level zero control, not a claim that a
  real zero certificate has been found;
- `cargo test --release --all-targets` passes 8 executed tests (the two expensive frozen-artifact
  tests remain explicitly ignored in this command), and `cargo clippy --release --all-targets --
  -D warnings` passes.

The hostile controls also pass.  Unknown-field certificates, the old forged certificate, and an
internally mismatched recomputation receipt all exit nonzero without creating their requested output.
The repaired converter self-test rejects seven mutants, and a forged postprocess supplied with fake
report/retained artifacts is stopped by the actual-hash comparison.  Finally, an isolated copy was
built and then mutated: the exact binary rejected changed producer source, while the modular binary
rejected a changed uniqueness lemma.  Thus the stale-input checks were executed, not inferred from
source inspection.

### Normal-form uniqueness statement match (`PASS_BOUNDED`)

`active_direction` returns true exactly when a proper prefix sum is negative.  The generator's raw
word has sum zero because the positive and negative edge masses agree; division by its coordinate
gcd makes it primitive; orienting by the first nonzero coordinate makes it first-positive.  These
are conditions 1--3 of the lemma, while `active_direction` is condition 4.  When condition 4 fails,
all proper prefix sums are nonnegative and summation by parts makes `d.x<0` on the open ordered
chamber, so omitting that ReLU is correct.  For a negative-first raw word, the implementation uses
`ReLU(-z)=ReLU(z)-z`; its added raw-word linear correction has the correct sign.

For retained directions, the first nonzero prefix is positive and an active prefix is negative, so
the hinge hyperplane meets the chamber interior.  Primitive first-positive directions give distinct
hyperplanes.  At a generic point of one such hyperplane, the gradient jump is exactly `c_d d`, which
forces `c_d=0` in any linear identity.  The written proof is therefore sufficient: one nonzero exact
hinge coefficient refutes equality on the ordered chamber; after all hinges vanish, the explicit
linear vector decides equality.  The replay outputs now embed and bind this lemma's hash.

This does **not** promote a fixed-family residual into an unrestricted lower bound.  A negative
certificate excludes only that coefficient vector; a completed all-column separator would exclude
only the frozen 163,740-atom family.  A positive exact zero would still need the separately audited
atom-to-two-hidden-layer compilation.

### Remaining provenance caveat

The replay parser intentionally accepts the planted receipt's syntactically valid placeholder
hashes; it cannot establish from the certificate alone that those external artifacts existed or
were recomputed.  The production converter is the external trust boundary: it rehashes the actual
input, rows, report, retained columns, postprocessor, and preregistration and performs a clean exact
postprocess rerun.  Publication-grade evidence must ship those artifacts and rerun that converter.
Because no real G-0113 member artifact exists yet, this remains an explicit obligation rather than a
defect in the exact residual arithmetic.

## Scope adjudication

The proposed loop concerns the fixed 163,740-column signed-`W` family.  A surviving exact identity,
followed by an audited atom-to-network compilation, would be an explicit MAX11 construction and
would settle the positive existential statement for `n=11`; it would not prove all arities.  A
finite-coordinate or global-normal-form obstruction would exclude only this family.  It would not
be an unrestricted two-hidden-layer lower bound without a separate completeness theorem.

The same coefficient vector is valid across the two row systems.  A G-0113 panel coordinate is
`F_W(x_r)/m_r`, and its target is `11! max(x_r)/m_r`; a G-0117 hinge or linear coordinate is a
coefficient of the same full-orbit function `F_W`.  Dividing some equations and their targets by
known nonzero stabilizers does not rescale the unknown atom coefficients.

## Historical hostile findings and their repairs

### 1. Live stale executable self-attested newer source (historical `FAIL_INVALID`, now resolved)

At the audit cut:

```text
current producer source:
95d5d9e03d8760a86563c691d5c5100421c30da10c1e87deda1051fde674a6b0

live standalone executable:
b8aef423540d8e79941acafed6e1683513e2d467bf1f0eb4625c61c622b3b422
```

The standalone executable was still the pre-fix binary.  It accepted
`hostile_certificate_v2.json`, including unknown top-level and term fields and bogus source
provenance, and wrote `hostile_replay_should_not_exist_v2.json`.  That output claimed producer hash
`95d5d9...` by hashing the newer source at runtime, even though the executing binary predated and did
not implement that source.  It omitted an executable binding.

The currently inspected source contains the right repair: `deny_unknown_fields`, frozen input
hashing, embedded-at-build producer/kernel bytes, runtime equality checks, and executable hashing.
But `cargo test --bin` builds the test harness, not necessarily the standalone
`target/release/global_modular_replay`; the repair is not evidence until that binary is explicitly
rebuilt, frozen, and hostile-replayed.  Source labels do not retroactively repair old outputs.

### 2. Fabricated postprocess provenance was accepted; repaired in source during review

`forged_postprocess.json` was written from scratch.  It contains the expected input and producer
strings, arbitrary 64-hex placeholders for rows/report/retained/preregistration, asserted green
booleans, and invented coefficients.  It was not produced by `exact_panel_postprocess.py` and its
coefficients were not replayed on the 301 rows.

Nevertheless:

```text
python3 artifacts/math/G-0117/advance_panel_seed.py \
  artifacts/reviews/G-0117-cegis-bridge/forged_postprocess.json \
  artifacts/reviews/G-0117-cegis-bridge/forged_certificate_v2.json
```

succeeded against the initially inspected converter and emitted a document whose claim boundary
calls it a denominator-cleared exact-Q finite-panel seed.

After this counterexample was sent to the author, the production CLI was changed to require the
actual scan-report and retained-column paths.  The current source rehashes the frozen input, rows,
postprocessor, postprocessor preregistration, report, and retained file; then it runs the frozen
exact postprocessor in the pinned project Python environment and compares every decision-bearing
field, excluding only wall time and peak RSS.  The certificate carries this recomputation receipt,
and the newer replay source requires its self-consistency.  This is the correct source-level
repair.

The repaired source snapshot inspected here is bound by:

```text
advance_panel_seed.py:       934912aac2c89d25223725d3ff4510275b67f13a781f37e94b5ee165949e8e1e
global_modular_replay.rs:    8ddc2ade4588f38f2486a0a42c61a3166fc475fb59dd81f8234a570b27aa8e73
handoff preregistration:     fd9704da88a7b4a21d82e5589b722078d8335786c47b2c87db3e488f0842a923
```

The historical forged artifacts are retained because they are the falsifier that caused the
repair.  They no longer satisfy the current production CLI.  The repair cannot be exercised on a
real subject until the live G-0113 scan and exact postprocess finish; therefore this subfinding is
`RESOLVED_IN_SOURCE_PENDING_SUBJECT_REPLAY`, not silently upgraded to a passing executed control.
In any event, a bogus seed could not forge a global identity once exact global replay independently
recomputes every selected atom; provenance and mathematical truth remain separate obligations.

### 3. Exact success path absent at the original audit cut (historical; now resolved)

The modular replay's nonzero result is sound: if cleared integer/rational residual were exactly
zero, reduction modulo every prime at which the rational is defined would be zero.  One nonzero
residue therefore refutes that seed.

The converse is false.  The nonzero integer

```text
1,000,000,007 * 1,000,000,009 = 1,000,000,016,000,000,063
```

vanishes modulo both replay primes.  The current result name
`TWO_PRIME_ZERO_PENDING_EXACT_BOUND` is therefore correct and must remain non-promotional.
`EXACT_GLOBAL_REPLAY_PREREGISTRATION.md` specified the appropriate arbitrary-precision replay, but
no frozen outcome-producing exact binary was present at the original audit cut.  The post-fix update
above supersedes that historical limitation.

The v2 integer form makes completion straightforward.  For `S=sum_j |a_j|` and target scale `L`,
the following conservative bounds follow directly from the full `S_11` census:

```text
|one atom's hinge coefficient| <= 5 * 11! = 199,584,000
|one atom's linear coefficient| <= 10*10*9! + 5*11! = 235,872,000
```

Hence every aggregate hinge residual is bounded by `199584000*S`; every nonfinal linear residual
by `235872000*S`; and the final linear residual by
`235872000*S + 39916800*L`.  Exact BigInt aggregation is simplest.  Alternatively, zero residues
over distinct primes whose product exceeds the applicable absolute bound prove exact zero.

## Independent controls

`checker.py` is a stdlib-only independent implementation.  Its bound output is
`controls_v1.json`.

### Panel/global normalization

For sequence 5341 (active 3) and multiedge sequence 73165 (active 4), the checker independently:

1. summed the labelled atom directly over formal-colour assignments;
2. summed the signed-graph residual over all active-rank injections, restored the inactive
   factorial, and added the closed-form degree-five nonloop base;
3. checked divisibility by the formal stabilizer and equality of both routes on all 301 rows.

All 602 identities held.  Sequence 5341 reproduced the independently frozen G-0113 i128 stream
hash exactly:

```text
2edd9faf75a4960c4c1e03338710c46257fa57469a828aaa4a3831661bedba39
```

### Exact-Q CEGIS algebra

A planted two-column system had panel seed `(1,0)`, hidden-coordinate residual `-2`, and repaired
full-family solution `(-1,2)`.  Re-solving only the original support incorrectly reported
nonmembership.  A second plant had a valid solution `(1,1/2)` after a new row; holding the previous
integer target scale fixed would incorrectly reject it.  Thus every residual round must:

- preserve all accumulated rows;
- reopen the complete column family (or use exact column generation with a full-column separator
  replay);
- solve over `Q` afresh; and
- only then clear the new denominators for global replay.

The checker also exercised the two exact termination branches: rank/augmented-rank inconsistency
and a primitive left separator annihilating every planted column while pairing nontrivially with
the target.

### v1/v2 equivalence and mutation

The planted v1 certificate `(1/2)F_0-(3/7)F_1` and v2 certificate
`7F_0-6F_1=14T` selected the same first direction.  The v2 residues were exactly fourteen times
the v1 residues in both fields and equalled `(662784,662784)`.  Changing `7` to `8` changed them to
`(786432,786432)`.

## Why residual-coordinate CEGIS is mathematically sound

Let `A_R` contain all 163,740 atom columns restricted to the accumulated coordinate set `R`, and
let `b_R` be the target.  Suppose `c` solves `A_R c=b_R`, but exact global replay finds coordinate
`r` with `a_r c != b_r`.

- If `(a_r,b_r)` were in the row span of `(A_R,b_R)`, every solution of the old system would
  satisfy it, contradiction.
- Therefore the new augmented row either increases the candidate row rank or exposes an immediate
  rank/augmented-rank inconsistency.
- Because the column family is finite, exact iterations cannot continue forever without either
  finding an identity or producing a finite separating subsystem.  This is a termination fact,
  not a practical iteration-count promise.

A modular guide may select candidate support, but it may not certify nonmembership.  A safe fast
solver may repeatedly solve on a support, derive an exact left separator when that support misses,
price the separator against the cached full family, and add a violating column.  Only a separator
that annihilates every cached column permits the bounded nonmember conclusion.

## Required normal-form uniqueness lemma

The residual row is a necessary identity constraint only after the following elementary lemma is
pinned.

Let `d` be primitive, zero-sum, first-positive, and active.  Put
`P_j=sum_{i<=j} d_i`.  On the chamber interior, with positive gaps
`g_j=x_{j+1}-x_j`,

```text
d.x = -sum_j P_j g_j.
```

The first nonzero `P_j` is positive, and activity supplies a negative `P_j`.  Therefore positive
gaps can be chosen with `sum P_j g_j=0`, so the hyperplane `d.x=0` meets the chamber interior.
Primitive first-positive normalization makes distinct directions define distinct hyperplanes.
At a generic point of this hyperplane avoiding the finitely many others, crossing it changes the
gradient of

```text
linear(x) + sum_e c_e ReLU(e.x)
```

by exactly `c_d d`.  A globally linear target has no such jump; hence `c_d=0`.  Applying this to
every direction proves uniqueness modulo the explicit linear vector.  This establishes both the
soundness of appending a nonzero hinge coordinate and the fact that a nonzero normal-form
coefficient refutes equality on the chamber.  Full-orbit symmetry then extends chamber equality to
all of `R^11`.

## Cache and solver contract required for promotion

The one-time cache is sound if it records, and later verifies:

- exactly 301 rows by 163,740 columns, sequence `0..163739` in the frozen order;
- the frozen panel input, row document, evaluator, target, complete i128 stream, and ordered-column
  digest bindings from the corrected scan;
- an explicit layout, signed width, endianness, value range, and checked narrowing if i64 is used;
- every appended coordinate's canonical kind (`hinge d` or `linear j`), exact target entry, pricer
  source/executable/query hashes, 163,740-value digest, and no duplicate coordinate;
- exact replay of every accumulated row after every solve.

Add all eleven cheap linear rows before the first expensive sparse global replay.  Then each later
failure should expose a hinge direction.  The solver must use the original rational target system;
v2's `target_scale` is an output normalization for one certificate, not a constraint on later
solutions.

## Conditions to lift this verdict

1. Produce a real G-0113 exact-Q member and package the postprocess, report, retained-column, and
   converter-recomputation artifacts so their receipt can be independently replayed.
2. Freeze the cache schema and run full-census reconciliation against the corrected G-0113 scan.
3. Implement fresh-Q, full-family residual-row re-solving and exact all-row replay.
4. Run the exact-zero path end to end on any real surviving certificate; the current zero control is
   necessarily synthetic because no such candidate exists yet.
5. If exact global zero occurs, audit the algebraic compilation into the declared two-hidden-layer
   network before beginning Lean formalization.

Until those obligations are discharged, the honest statement is: **the bridge now has a sound
mathematical design, a fast exact coordinate oracle, an exact BigInt certificate decider, and a
reviewed uniqueness lemma—but it has not yet earned an exact global MAX11 result or a bounded
full-family obstruction.**
