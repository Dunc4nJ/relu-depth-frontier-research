# Lean formalization rail

This Lake project is pinned to Lean 4.33.1 and Mathlib v4.33.1. It begins with a known-answer identity only; it does not formalize or prove the MAX_n target.

From the campaign root:

    source scripts/activate-toolchain.sh
    cd formalization
    lake exe cache get
    lake build

Any later theorem promotion must bind the exact target statement, import closure, Lean/Mathlib commits, trust scan, and a separate statement-match review. Kernel acceptance alone does not show that the formal theorem is the intended informal one.
