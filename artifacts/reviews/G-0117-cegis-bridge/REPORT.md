MATERIAL_INCREMENT

# G-0113 -> G-0117 exact-global CEGIS bridge audit

## Typed verdict

**Overall: `PASS_WITH_OBLIGATIONS` — the algebraic CEGIS design is sound, but the current bridge is
not binding-clean and is not yet capable of certifying exact global success.**

Sub-verdicts:

- `PASS_BOUNDED`: denominator clearing, nonzero-modular-residual logic, panel/global normalization,
  and the proposed full-column exact-Q residual-row loop.
- `FAIL_INVALID` for the live *binding-clean handoff* executable at the audit cut: the stale replay
  binary accepted unknown/bogus provenance fields while self-attesting the hash of newer source.
  An initially accepted fabricated postprocess exposed a second gap; the author repaired that gap
  in source during review, but no real G-0113 member artifact yet exists for an end-to-end replay.
- `INDETERMINATE` for exact global success: at the audit cut, exact-integer replay exists as a
  preregistration and new dependencies, not as a frozen passing executable.  The available replay
  can refute a seed on a nonzero modular residual but cannot promote two-prime zero.

This is fresh-context, same-model-family T1 review.  It cannot satisfy the campaign's unavailable
T2 promotion gate.

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

## Concrete hostile findings

### 1. Live stale executable self-attested newer source (`FAIL_INVALID`, repairable)

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

### 3. Exact success path not yet executable (`INDETERMINATE`)

The modular replay's nonzero result is sound: if cleared integer/rational residual were exactly
zero, reduction modulo every prime at which the rational is defined would be zero.  One nonzero
residue therefore refutes that seed.

The converse is false.  The nonzero integer

```text
1,000,000,007 * 1,000,000,009 = 1,000,000,016,000,000,063
```

vanishes modulo both replay primes.  The current result name
`TWO_PRIME_ZERO_PENDING_EXACT_BOUND` is therefore correct and must remain non-promotional.
`EXACT_GLOBAL_REPLAY_PREREGISTRATION.md` specifies the appropriate arbitrary-precision replay, but
no frozen outcome-producing exact binary was present at this audit cut.

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

1. Rebuild and freeze the standalone replay binary from the embedded-source-checking code; show the
   hostile unknown-field and stale-source controls fail before scientific output.
2. Make G-0113 provenance real rather than syntactic, or demote the handoff wording explicitly.
3. Implement and independently replay exact BigInt global aggregation, including exact-zero,
   hinge-residual, linear-residual, coefficient mutation, and stale-binary controls.
4. Freeze the cache schema and run full-census reconciliation against the corrected G-0113 scan.
5. Implement fresh-Q, full-family residual-row re-solving and exact all-row replay.
6. Pin/review the normal-form uniqueness lemma above.
7. If exact global zero occurs, audit the algebraic compilation into the declared two-hidden-layer
   network before beginning Lean formalization.

Until those obligations are discharged, the honest statement is: **the bridge now has a sound
mathematical design and a fast exact coordinate oracle, but it has not yet earned an exact global
MAX11 result or a bounded full-family obstruction.**
