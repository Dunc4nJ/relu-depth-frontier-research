# G-0047 induction-obstruction Lean statement match

## What the kernel checks

`Formalization.InductionObstruction` represents the ordered-chamber coefficient vector of

`F_m = sum_{|S|=m} max_{i in S} x_i`

by `choose (r-1) (m-1)` for ranks `r=1,...,11`.  It defines the G-0047 functional

`Lambda_r = (-1)^(11-r) choose(10,r-1)`

and proves, for all ten proper subset sizes, that `Lambda(F_m)=0`, while
`Lambda(MAX11)=1`.  The generic span-separator lemma then proves that the MAX11 coefficient vector
is outside the real span of those ten vectors.

The concrete arithmetic is reduced first to integer equalities by kernel `decide`, then transported
to the reals.  No `native_decide`, `sorry`, `admit`, or project axiom is used.

## Exact scope boundary

This is a coefficient-space obstruction.  The separate mathematical reduction in G-0047 shows
that fully symmetrized lower-MAX induction and common loop/nonloop padding land in this span.  The
Lean file does **not** formalize that reduction, the finite graph censuses, arbitrary signed
multi-orbit hinge cancellation, completeness of the degree-five atom family, or arbitrary
two-hidden-layer ReLU networks.  It is therefore not a MAX11 lower bound or solution.

## Frozen bindings

- Lean source SHA-256: `bd7e358da0b7f7b312fa730967a4dc759842b0e0bd47b4747b5bd15836041282`
- G-0047 script SHA-256: `0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d`
- G-0047 report SHA-256: `47f02e125c4010e50d943c31ef4278f9d8679b0e54d26d86ea5414ac12ebf83a`
- Lean toolchain: `leanprover/lean4:v4.33.1`, commit
  `819816b2e0a3bf405af45ae5c7af2491d8f5bee6`
- Mathlib revision: `0df444a360eaa60ab8c11dca51a86af692955474`
- Worktree base commit during verification: `5c47f4f9b9194406dc39533406dd6d6f12148d31`

## Verification receipt

The following completed successfully:

```text
source scripts/activate-toolchain.sh
cd formalization
lake build
```

An ephemeral import-only audit printed the axioms of all three public theorems.  Each depends only
on the standard Mathlib set `[propext, Classical.choice, Quot.sound]`.  A source scan found no
`sorry`, `admit`, or `axiom` token in the new module.
