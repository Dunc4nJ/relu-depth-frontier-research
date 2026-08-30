# G-0117 preregistration — exact global replay and residual-coordinate CEGIS

Registered while the corrected G-0113 two-prime panel scan was still running,
before any DISJOINT-boundary or final target-membership result was available.
The only observed checkpoint was the non-decision-bearing prefix count
`5,000/163,740`, with matching modular ranks `110,110`.

## Question and fixed boundary

If G-0113 returns an exact rational solution on its 301 four-formal-colour
rows, does the same coefficient vector give the global ordered-cone identity

```text
sum_j c_j F_j(x) = 11! x_11                 (x_1 <= ... <= x_11),
```

where `F_j` is the full `S_11` orbit sum of the corresponding loopless
degree-five max atom?  A 301-row solution is only a seed.  Global success
requires every ordered-cone hinge coefficient to vanish and the complete
linear vector to equal `(0,...,0,11!)` over `Q`.

This experiment concerns the fixed 163,740 signed-`W` family from G-0113.  A
negative result is not an unrestricted lower bound.  A positive global
identity is an explicit MAX11 certificate in this family, but is not a proof
for all arities until separately generalized.

## Stage A — exact panel lift

Consume only a completed, binding-clean G-0113 report and retained-column
artifact.  If either prime has rank 301, use its ordered rank-growing support;
otherwise use the union of both retained supports.  Select a nonsingular
minor modulo the guide prime, solve that minor over `Q`, and replay all 301
integer rows exactly.  A modular solution is never reported as rational.

Reject on any target hash, column hash, sequence, binding, or complete-row
replay mismatch.  Reordering equations must preserve the exact solution, and
adding one to a nonzero coefficient must fail replay.

## Stage B — complete ordered-cone replay

For every nonzero certificate atom, independently regenerate the full-orbit
normal form used in G-0109:

```text
F_W(x) = sum_d h_d(W) ReLU(d.x) + sum_r ell_r(W) x_r.
```

Directions are primitive zero-sum integer words, oriented by first nonzero
entry positive, and retained exactly when a proper prefix sum is negative.
The loopless degree-five base is `ell_r^base = 10 r 9!`; a raw word whose
first nonzero entry is negative contributes its entire word to the linear
correction.  The target is hinge-free with linear vector
`(0,...,0,11!)`.

For every selected atom, evaluate the regenerated normal form on all 301
formal-profile rows and require exact agreement with its retained G-0113
panel vector after division by the formal stabilizer.  This check binds the
global and panel semantics rather than trusting a shared name.

The complete rational sum has exactly two possible outcomes:

- `EXACT_GLOBAL_IDENTITY`: zero residual on every generated hinge and all 11
  linear coordinates, followed by coefficient mutation rejection;
- `EXACT_GLOBAL_RESIDUAL`: the lexicographically first nonzero hinge residual,
  or, if none exists, the first nonzero linear residual.  This is a falsifier
  of that seed only.

## Stage C — exact residual-coordinate pricing

For a primitive active direction `d`, compute `h_d(W)` without enumerating
`11!` orders.  For each signed scale
`s in {-5,...,-1,1,...,5}`, a subset DP counts active-vertex rank injections
whose raw back-degree word is exactly `s d`.  If `k` vertices are active,

```text
h_d(W) = (11-k)! * sum_s |s| * count_W(s d).
```

The DP state is `(rank, placed-active-subset)`; inactive vertices have zero
increment and are indistinguishable during the DP, with their `(11-k)!`
label multiplicity restored at the end.  A companion three-state prefix-sign
DP computes all 11 linear corrections exactly.

Before any family-wide price is used, the implementation must pass:

1. equality with literal `11!` enumeration on fixed low-active atoms;
2. equality with the frozen G-0109 normal forms on every available selected
   sample, including an active-11 cyclic record;
3. branch-swap invariance of hinge coefficients;
4. vertex-relabel invariance;
5. rejection of an edge-sign mutant;
6. exact zero on a direction outside a known sample atom's support and exact
   agreement on a supported direction.

If the seed has residual coordinate `r`, scan all 163,740 fixed candidates in
the original order and append the exact `r` row to the CEGIS system.  Preserve
every earlier residual row.  Re-solve over `Q`, replay every accumulated row,
then repeat complete global replay.  No candidate may be filtered using the
desired coefficient or target residual.

## Stop and promotion rules

- Stop and report `INVALID` on any binding/control/census disagreement.
- Stop and report a bounded exact obstruction only if an exact integer left
  separator annihilates every fixed-family column on every accumulated row
  and pairs nontrivially with the target.
- A prime-only miss remains a modular gate, never a `Q` or real claim.
- A global identity must be converted algebraically into the declared
  two-hidden-layer ReLU architecture and independently replayed before it is
  called a MAX11 construction.
- Lean work begins on the decisive identity/compilation lemma only after the
  exact unrestricted-in-`x` certificate survives adversarial replay.  No
  finite-panel theorem is to be formalized as though it were MAX11.
