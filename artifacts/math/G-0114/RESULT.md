# G-0114 result — G-0112 is potency, not a reusable degree-raising law

## Bottom line

The exact MAX6 -> MAX7 discovery survives as a useful dictionary-design clue:
the share-one and disjoint nonloop slices each contain MAX7 when individual
lifted atoms receive untied rational coefficients.  It does **not** reveal a
simple operator that transports the public source certificate.

The strongest exact conclusion in this track is the following bounded no-go.

Let

```text
M8 = sum_t c_t Phi(P_t) = MAX8
```

be the public 69-term degree-three certificate.  Let `L` be the frozen
148-weight local-incidence operator obtained as one exact joint solution of
the complete MAX5 -> MAX6 and MAX6 -> MAX7 systems.  On nine labels define

```text
F       = sum_t c_t sum_(unequal nonloop e,f)
                    w(signature(P_t,e,f)) Phi(P_t+e,f),
U_R     = sum_t c_t sum_((e,f) in R) Phi(P_t+e,f),
```

where absent frozen signatures have weight zero and

```text
R in {common nonloop, share-one nonloop,
      disjoint nonloop, at-least-one-loop}.
```

Then, over characteristic zero,

```text
MAX9 notin span_Q(F, U_common, U_share, U_disjoint, U_loop).
```

This is not inferred from samples.  The complete ordered-cone normal form has
17,257 rows; the five-column matrix has exact rank 5 and adjoining `MAX9`
raises the rank to 6.  The output contains a primitive six-row integer dual
that annihilates all five columns and pairs with MAX9 as

```text
711865266352114359877106400 != 0.
```

The decisive confirmatory artifact is `small_correction_span_v2.json`
(SHA-256
`aa7e753905606ef191563a2a2e24f13db8125d425d6c4aadb0ce9c6a2272c4cd`).
It freezes the six-by-five rational row matrix, the primitive weights, five
exact zero column pairings, and the nonzero target pairing.  Its frozen matrix
has SHA-256
`5177dddaa5a5c87e3dbbb2537989970a5154acb8c0d5caa60d5634fc48e09b8b`.

## What was learned before that no-go

### 1. Untied slice potency is real

The bound G-0112 result gives exact membership separately for:

- share-one nonloops: 156 unique semantic columns, rank = augmented rank =
  90, one 70-term exact solution;
- disjoint nonloops: 162 unique semantic columns, rank = augmented rank = 97,
  one 72-term exact solution.

Thus disjointness is useful but not uniquely load-bearing; either relation
class has enough atom-level freedom at 6 -> 7.

### 2. Tying coefficients destroys the easy lift

For the public MAX6 certificate `sum_t c_t Phi(P_t)=MAX6`, define the six
raw-multiplicity relation averages

```text
A_R = sum_t c_t sum_((e,f) in R) Phi(P_t+e,f).
```

Their exact span has rank 4, while adjoining MAX7 gives rank 5.  Therefore no
coefficient rule depending only on added-edge relation can produce MAX7.

Even allowing one scalar per public source term does not rescue either
successful slice:

```text
MAX7 notin span_Q{sum_(share e,f) Phi(P_t+e,f) : t=1,...,4},
MAX7 notin span_Q{sum_(disjoint e,f) Phi(P_t+e,f) : t=1,...,4}.
```

Both four-column matrices have rank 4 and augmented rank 5.  Hence the G-0112
solutions require variation *within* a source stratum, not merely the original
source coefficient or a source-specific rescaling.

### 3. A flexible local model fits small arities but does not transport

Weights indexed by a branch/endpoint-swap invariant local signature (added
edge relation plus endpoint degree profiles in the two source branches) give:

- MAX6 -> MAX7 membership with 400 signatures, rank 220, one 120-weight
  solution;
- a joint MAX5 -> MAX6 and MAX6 -> MAX7 membership system with 556 signatures,
  rank 319, one 148-weight solution.

The coefficients are large unrelated rationals, so this is already a
compressed linear solve rather than a short identity.  Freezing those 148
weights and applying them without refitting to the genuine second degree raise
MAX8 -> MAX9 fails exactly: all nine linear residuals and 15,605 hinge
residuals are nonzero.  The first residual is

```text
linear coordinate 1:
1054999133599884059 / 83920696726507200.
```

The residual digest is
`4782a870702cbd13c01c0d4b19d914ba42d9c1384cb1f380702f31a9b88e8b9a`.

### 4. Literal target-certificate recurrence also fails

Lossless full-atom colored-incidence quotienting shows:

- at 6 -> 7, none of the 57 nonzero target certificate graph classes is a
  literal share/disjoint one-edge lift;
- at 8 -> 9, the union covers 286 of 337 target classes and misses 51.

This rejects atom-by-atom inheritance of the known target certificates.  It
does not contradict G-0112, whose success uses nontrivial functional linear
relations among graph-distinct atoms.

## Decision for MAX10 -> MAX11

Do not use G-0112 as a closed-form recurrence or tie MAX10 coefficients by
relation averages.  Its justified use is narrower and still valuable:

- prioritize the source-derived degree-five share/disjoint dictionary as a
  column pool;
- allow coefficients to vary at the semantic-orbit level;
- solve/price on the actual MAX11 normal-form constraints rather than assuming
  transport from the MAX10 certificate.

Expanding the signature family again would be unconstrained refitting: the
small-arity systems already have hundreds of free weights, and the first
genuine out-of-sample degree raise rejected the frozen solution.

## Claim boundary

This track does **not** show that the full source-derived MAX10 -> MAX11
dictionary fails, that the complete degree-five ansatz fails, or that an
unrestricted two-hidden-layer representation is impossible.  It rejects the
explicit relation-tied, source-scalar, frozen-local-law, literal-recurrence,
and four-relation-repair mechanisms stated above.

## Reproduction

From the repository root:

```text
.venv/bin/python -B artifacts/math/G-0114/degree_raising_identity.py --self-test
.venv/bin/python -B artifacts/math/G-0114/graph_recurrence.py --self-test
.venv/bin/python -B artifacts/math/G-0114/frozen_law_max9.py --self-test
.venv/bin/python -B artifacts/math/G-0114/small_correction_span.py --self-test
```

The confirmatory commands require unused output paths; exact commands and
input hashes are frozen in the four preregistration files.  Root review should
re-execute at least the final `small_correction_span.py --run` producer rather
than treating this report as independent evidence.
