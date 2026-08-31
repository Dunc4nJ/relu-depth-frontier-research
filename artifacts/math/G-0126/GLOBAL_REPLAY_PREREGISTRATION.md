# G-0126 preregistration — complete global replay of the 348-row family member

## Registration boundary

This protocol is frozen before any global residual of the G-0121 candidate is
computed or inspected.  The only admitted scientific input is the exact
finite-row result

```text
artifacts/math/G-0121/full_family_master_result_v1.json
sha256 = 53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036
schema = max11-g0121-full-family-master-result-v1
result = FULL_FAMILY_EXACT_Q_MEMBER
rows = 348
records = 163740
nonzero terms = 131
target_scale =
  264010886084977103415797420761461511057729096350532822171032655262573576673600959905395014217297467347581921316792637811198651042601200900728134005150
```

The result has 156 basis slots but exactly 131 serialized nonzero `terms`.
This replay consumes those 131 terms, not the zero-padded basis slots.  Their
sequences must be unique, in range, strictly increasing as serialized, equal
to the nonzero projection of `(support_sequences, integer_coefficients)`, and
all at most 141.  No prefix pattern is evidence and no coefficient or term may
be selected after this replay begins.

Frozen supporting inputs are

```text
panel/record input:
  artifacts/math/G-0113/panel_solver_input_v1.json
  sha256 = 093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8

normal-form kernel:
  artifacts/math/G-0117/src/lib.rs
  sha256 = 2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6

normal-form uniqueness lemma:
  artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md
  sha256 = 39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17
```

The producer source, its Cargo manifest/lockfile, this preregistration, the
candidate, panel input, kernel, uniqueness lemma, and running executable must
all be hash-bound in the output.  The executable must embed the producer,
preregistration, candidate, kernel, and uniqueness-lemma bytes at build time
and refuse source-on-disk drift.  The final producer and executable hashes are
necessarily recorded only after implementation; they may not alter this
scientific protocol.

## Exact target and cousin boundary

For record `s`, let `F_s` be the full labelled `S_11` orbit sum of the
loopless degree-five max atom represented by record `s`, with exactly the
semantics of the bound normal-form kernel.  Let `a_s` be the candidate's
serialized integer coefficient and let `L` be its positive integer
`target_scale`.  The candidate statement is

```text
sum_s a_s F_s(x) = L * 11! * max(x_0,...,x_10)       for every x in R^11.
```

On the open ordered chamber `x_0 < ... < x_10`, the target is the hinge-free
linear function `L * 11! * x_10`.  Every `F_s` is permutation invariant, so
an exact ordered-chamber identity extends globally by continuity and symmetry.

This is not yet a two-hidden-layer network certificate: architecture
compilation, coefficient normalization, and independent statement-matched
replay remain separate obligations.  It is not a family-completeness theorem,
an unrestricted lower bound, an induction in arity, or a statement about any
other candidate.  A nonzero residual refutes this 131-term candidate only.

## Complete ordered-cone normal form

For every one of the 131 terms, regenerate from its bound record the exact
full-orbit normal form

```text
F_s(x) = sum_d h_d(s) ReLU(d.x) + sum_(r=0)^10 ell_r(s) x_r.
```

The computation must enumerate all `11! = 39,916,800` labelled permutations
for each term through the existing exact normal-form kernel, for a required
total census of

```text
131 * 11! = 5,229,100,800 labelled permutations.
```

Every retained direction is a primitive zero-sum integer 11-tuple, oriented
so its first nonzero coordinate is positive, and retained exactly when a
proper prefix sum is negative.  Equal directions are aggregated completely;
zero entries are not silently dropped before the support and entry censuses
are recorded.  Subtract `L * 11!` from linear coordinate 10 and zero from the
other ten coordinates.  The output records the complete 11-coordinate linear
residual, total generated hinge-entry census, aggregate direction census, and
the count of nonzero hinge directions.

By the bound uniqueness lemma, any nonzero retained hinge coefficient, or a
nonzero linear residual after all hinges vanish, refutes equality to the
linear target on the ordered chamber.  The producer must validate every
generated direction against the kernel's stated normal-form invariants.

## Frozen modular screen and 36-row carry-forward gate

The ordered screening primes are

```text
p0 = 1,000,000,007
p1 = 1,000,000,009.
```

All 131 integer coefficients and the exact target scale are reduced
independently into each field only after canonical-decimal validation.  A
residue nonzero in either field proves the corresponding integer residual is
nonzero.  Zero in both fields is only a screen and cannot be reported as an
identity.

Before selecting a new violation, require the candidate's 36 serialized
`hinge_directions`, in exactly their existing order, to have residue zero in
both fields.  These are the four earlier accumulated directions followed by
the 32 Batch32 directions.  Any failure is serialized as
`CARRY_FORWARD_REPLAY_DEFECT` with the first failing index/direction/residues;
it refutes the claimed 348-row replay and stops before any new CEGIS batch is
presented.

If all 36 checks pass, freeze the failure handoff as follows:

1. retain every aggregate hinge direction nonzero in either field;
2. sort by the signed integer 11-tuple in ascending lexicographic order;
3. set `K = 32`;
4. select the first `min(32, nonzero_count)` directions;
5. serialize each direction and its ordered residue pair, plus a digest of
   the exact signed-i8-direction/u64-little-endian-residue stream.

If there are no nonzero hinge directions but a linear residue is nonzero,
serialize the first nonzero linear coordinate in index order.  There is no
post-result choice of violations.

## Exact pricing and exact-zero continuation

For every selected modular hinge violation, price the exact integer residual
using the independent subset-DP coordinate evaluator from the bound kernel:

```text
sum_s a_s h_d(s).
```

The exact value must reduce to both recorded field residues.  Emit a complete
selected-row exact-price list and its deterministic decimal-LF stream digest.
If a linear violation is selected instead, compute its exact integer residual
from all 131 exact linear vectors and require the same two modular reductions.

If and only if every hinge and linear residual is zero in both fields, the
same invocation must automatically perform a binding-clean arbitrary-
precision replay of the complete normal forms.  It must aggregate every hinge
and all 11 linear coordinates over `Z`, subtract the exact target, remove only
mathematically exact zeros, and return exactly one of:

- `EXACT_GLOBAL_NORMAL_FORM_ZERO`; or
- `EXACT_GLOBAL_NORMAL_FORM_RESIDUAL`, with the signed-lexicographically first
  exact nonzero hinge, or the first exact nonzero linear coordinate if all
  hinges vanish.

The producer may never emit a terminal two-prime-zero result.  Exact zero is
necessary for the candidate identity but still leaves the architecture and
independent-replay obligations above.

## Frozen controls

- **Input/projection:** require exactly 131 nonzero canonical integer terms,
  unique in-range sequences, exact term projection, positive canonical target
  scale, 163,740 ordered records, the exact candidate identity, and all bound
  hashes.  Unknown candidate or panel fields are rejected.
- **Census:** require exactly 5,229,100,800 labelled permutations and an exact
  term count of 131.  Any partial or skipped term is fatal.
- **Carry-forward:** require all 36 old hinge rows to replay to zero in both
  fields before selecting new directions.
- **Coefficient mutant:** add one to the first serialized coefficient in
  memory and require the complete modular receipt to change: at least one
  carry-forward row, linear residual, aggregate nonzero census, or selected
  prefix/digest must differ.  A surviving `+1` mutant is fatal.
- **Known-answer/self-tests:** before the scientific run, test canonical
  integer refusal, signed lexicographic selection, target subtraction,
  modular reduction of negative integers, direction invariants, exact-price
  reduction to both primes, synthetic exact cancellation, independent hinge
  and linear mutants, and at least one literal low-active normal form against
  the kernel's existing known-answer tests.
- **Structural negatives:** malformed/zero coefficients, duplicate or
  out-of-range sequences, a zero-padded term projection, record-order drift,
  reordered old directions, altered target scale, source drift, executable
  drift, census mismatch, and an existing output path are fatal.
- **Custody:** the scientific output is opened with exclusive creation
  (`O_EXCL`/`create_new`) only after every binding and pre-computation control
  passes.  No partial scientific output is retained on failure.

## Frozen output and stop rules

The sole scientific output path is

```text
artifacts/math/G-0126/global_replay_v1.json
```

The producer refuses to overwrite it.  The run stops and reports `INVALID`
without a scientific output on any binding, schema, projection, control,
census, arithmetic-bridge, or source/executable disagreement.

- `CARRY_FORWARD_REPLAY_DEFECT` refutes the input's claimed old-row replay and
  triggers audit of G-0121 before further CEGIS.
- `GLOBAL_MODULAR_RESIDUAL` with a nonzero residue exactly refutes this
  candidate.  Its first-32 rows are deterministic next-master inputs, not a
  refutation of the 163,740-record family.
- `EXACT_GLOBAL_NORMAL_FORM_RESIDUAL` after a two-prime-zero screen also
  refutes this candidate and records the prime-collision residual.
- `EXACT_GLOBAL_NORMAL_FORM_ZERO` establishes the exact frozen orbit identity
  only.  It immediately triggers clean-room replay, architecture compilation,
  and then statement-matched Lean formalization; none may be skipped or
  inferred from this producer's own output.

No finite-row membership, modular zero, prefix pattern, or successful control
is promoted to MAX11.
