# Lean formalization rail

This Lake project is pinned to Lean 4.33.1 and Mathlib v4.33.1. It contains the skip-free compiler
and abstract obstruction lemmas used by the campaign, but it does not formalize or prove the MAX_n
target.

From the campaign root:

    source scripts/activate-toolchain.sh
    cd formalization
    lake exe cache get
    lake build

Any later theorem promotion must bind the exact target statement, import closure, Lean/Mathlib commits, trust scan, and a separate statement-match review. Kernel acceptance alone does not show that the formal theorem is the intended informal one.

`Formalization.Obstruction` proves the common-addend maximum identity (including pointwise-function
and finite-sum forms), a real-span separator theorem for finite generator families, and span
preservation under pointwise replacement. These are statement-matched to abstract inference steps
in G-0015 only. They do not load or verify the 7,146-by-9,804 matrix, the rational dual bytes, the
registered graph enumeration, or the unrestricted MAX11 statement.

`Formalization.InductionObstruction` proves the exact G-0047 coefficient-space obstruction at
MAX11: an alternating-binomial functional annihilates the ordered-chamber coefficient vectors of
all ten proper subset maxima but evaluates to one on MAX11.  This excludes lower-MAX induction and
common loop/nonloop padding after their separate reduction to that span.  It is not a completeness
theorem for degree-five pair atoms or arbitrary two-hidden-layer ReLU networks.
