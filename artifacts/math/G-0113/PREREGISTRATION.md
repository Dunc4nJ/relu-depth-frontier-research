# G-0113 preregistration — incidence-slot double-star lifts

Registered before writing or executing the outcome-producing G-0113 program.
The consumer is the unrestricted-normal-form gap `G-0006`.  This experiment
gates further work on one new pairwise degree-six route.  It is justified by
the observed lower-arity potency failure of the one-edge/star family in
G-0094.  This preregistration retires when the frozen G-0113 result is handed
to the research lead; it is not a new campaign ledger.

## Exact family

For a source graphical pair `(L,R)` of degree `k` in dimension `n`, put
`w=n+1`.  On either ordered branch, whose edge occurrences are
`e_j=(u_j,v_j)` with `u_j <= v_j`, define the following `3k+1` two-edge
attachments:

```text
P(j,0) = ((u_j,w),(u_j,w))
P(j,1) = ((v_j,w),(v_j,w))
E(j)   = ((u_j,w),(v_j,w))
Z      = ((w,w),(w,w)).
```

Occurrences and duplicates are retained.  For every left choice `a` and
right choice `b`, the lifted atom is the full symmetric graphical-pair atom

```text
Phi(T,a,b) = Sym_{n+1} max(h_{L + a}, h_{R + b}).
```

This is called the **incidence-slot double-star family**.  The degree is four
for the MAX6-to-MAX7 control and six for the MAX10-to-MAX11 subject.  It is
genuinely outside the one-edge/star family: each branch receives two edge
occurrences, including parallel and edge-supported triangle attachments.

Two coefficient freedoms are frozen:

1. `RAW`: every `Phi(T,a,b)` has an independent rational coefficient;
2. `TIED`: for each `(a,b)`, one column is the exact source-certificate
   combination `sum_T c_T Phi(T,a,b)`.

The raw counts must be `4*7^2=196` for MAX6-to-MAX7 and
`402*13^2=67,938` for MAX10-to-MAX11.  The tied counts must be 49 and 169.
No term, attachment, duplicate, zero column, or failed trial may be filtered
after inspecting a target residual.

## Preregistered stage order

### Stage 0 — exact negative and positive controls

Using complete dominant-ordered-cone normal forms (all linear coordinates and
all projective interior hinge directions), independently replay the public
MAX6, MAX7, and MAX10 certificates.  A one-unit change to the first source
coefficient must fail.  Branch swapping every atom must preserve its normal
form.  The already-known one-edge MAX6-to-MAX7 RAW family is recomputed and
must have ranks 64 and 65 with MAX7 adjoined; disagreement freezes the run.

### Stage 1 — lower-arity potency

Compute complete exact characteristic-zero normal forms for all 196 RAW and
49 TIED MAX6-to-MAX7 incidence-slot double-star columns.  Compute exact ranks
over `Q`, with MAX7 target-last.

Potency passes only if the RAW span contains MAX7.  On a pass, extract the
lexicographic target-last basic solution and replay every linear and hinge
coordinate exactly.  On a failure, stop before MAX11 and extract a primitive
integer row dual.  Report the shortest prefix of the lexicographically sorted
complete normal-form row order for which the augmented rank first exceeds the
family rank; this is prefix-minimal in that frozen order, not globally
support-minimal.

The TIED result is a separately reported transport diagnostic.  A TIED miss
does not negate RAW potency and a RAW pass does not prove that the MAX11
analogue is potent.

### Stage 2 — frozen MAX11 finite discriminator

This stage runs only after RAW lower-arity potency passes.  Evaluate every one
of the 67,938 RAW columns and all 169 TIED columns exactly on the following
66 full-symmetry assignment-sum rows, in this order:

1. the eleven Boolean profiles `(0^(11-h),1^h)`, `h=1,...,11`;
2. the fifty-five sparse three-level profiles
   `(0^9,a,b)` for `1 <= a < b <= 11`, lexicographic in `(a,b)`.

Each row is the unnormalised sum over all distinct assignments of its multiset
to the eleven labels; the target entry is the same assignment count times
`max(profile)`.  Evaluate by exact integers.  The implementation may exploit
vectorisation but must cross-check predeclared columns and rows by literal
multiset-permutation enumeration.

For TIED and RAW separately, compute every prefix rank exactly over `Q`.
If a target first leaves the span, extract and replay a primitive integer dual
against every column of that family, and report that prefix as the smallest
exact separating witness in the frozen schedule.  This is finite-row
nonmembership only.

### Stage 3 — complete global check of frozen finite-row candidates

If a family contains MAX11 on all 66 rows, select the unique target-last
lexicographic basic solution: scan columns in frozen order, retain a column
iff it increases rank, then solve on the resulting pivot columns without
coefficient-size selection.  For RAW this uses original atom columns.  For
TIED, expand every selected operator column with the pinned MAX10 source
coefficients.

Compute the candidate's complete ordered-cone normal form exactly.  Accept a
global certificate only if every interior hinge coefficient cancels and the
linear vector is exactly `(0,...,0,1)`.  Otherwise report the first nonzero
coordinate in the frozen order (linear coordinates first, then primitive
hinge directions lexicographically), its exact residual, and no family-wide
global conclusion.  Finite agreement never implies global identity.

## Frozen stop rules and claim boundaries

- A lower-arity RAW miss stops the run and excludes only the complete 196-
  column MAX6-to-MAX7 incidence-slot family.
- A MAX11 finite-row dual excludes only the displayed 67,938-column RAW or
  169-column TIED family on the displayed rows.  It is a valid obstruction to
  a global identity in that family, because a global identity would agree on
  those rows, but it is not an unrestricted depth lower bound.
- Failure of one canonical 66-row solution globally does not exclude another
  solution in the same family.
- A surviving exact global candidate is only an explicit isolated MAX11
  representation after a separate network-compilation/architecture audit; it
  does not prove the all-`n` target.
- No floating residual, modular rank, sampled point agreement, finite
  dictionary result, or G-0108 separator price is promoted to a global claim.

Resource stop: no paid/external compute; stop unresolved rather than changing
the family or row schedule if the local run exceeds the campaign's existing
resource authorization.  Every executed arm, including controls and aborted
arms, is reported in the single result artifact.
