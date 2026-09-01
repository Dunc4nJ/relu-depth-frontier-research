# G-0187 — exact sparse basis of the retained STAR restriction kernel

This directory freezes and verifies a materially smaller exact basis for the
478-dimensional left kernel established by G-0181.

- `candidate/exact_sparse_left_kernel_basis_v1.jsonl`: frozen 478-vector basis.
- `PREREGISTRATION.md`: post-discovery promotion gate and claim boundary.
- `cleanroom/verify_sparse_basis.py`: clean replay and theorem composition.
- `cleanroom/exact_sparse_replay.cpp`: signed-128-bit exact matrix replay.
- `cleanroom/rank_rectangular_flint.cpp`: four-prime independence checker.
- `results/clean_replay_v1.json`: promoted replay receipt.
- `RESULT.md`: exact result and strategic interpretation.

The new basis is a computational interface to the already known finite
kernel. It does not itself lift any new relation into the old-primary span.
