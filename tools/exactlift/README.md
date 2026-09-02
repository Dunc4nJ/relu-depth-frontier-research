# exactlift

Exact arithmetic tooling for the saved loopless MAX systems. It translates the
pinned Rueß certificates into saved-system column indices, verifies sparse
rational witnesses on the complete saved row universe, emits upstream verifier
JSON, recovers a rational solution from a modular pivot minor, and runs the
known n=9 beta-zero tree-family nonmembership control.

All commands use the project virtual environment:

```bash
source .venv/bin/activate
python tools/exactlift/exactlift.py --help
```

`recover` first computes a full modular column basis, then an independent row
basis, solves the resulting square integer minor over Q with FLINT's Dixon
solver, and replays the result over every saved hinge and linear row. A basis
cache is hash- and prime-bound; it contains indices only, not a witness.

This tool decides only the finite saved system supplied on the command line. A
successful n=9 or n=10 control says nothing about MAX11.

`upstream_parallel.py` is the convention-independent replay path for expensive
n=10 checks. It never reads the saved system or imports `exactlift.py`; its six
workers import the hash-recorded pinned upstream verifier and call that file's
`read_pair` and `symmetrized_pair` functions unchanged. Only the outer term loop
is distributed.

`bind-upstream-verification` reuses such a completed upstream result only when
the candidate certificate is byte-identical to the verified certificate and
the recorded certificate and verifier SHA-256 values still match. A mismatch
returns `FAIL`.

`scale_benchmark.py` is an explicitly synthetic sparse-block exact-solve
control. It plants a denominator-30 rational solution in a full-rank integer
system, solves every block with FLINT Dixon arithmetic, checks every row, and
rejects a `1/30` solution mutation. Its linear scaling is evidence only for the
sparse block fallback, never for a dense n=11 pivot minor.

`support_lift.py` consumes `max11-streamrank-pivots-v1` source indices, reopens
the exact saved columns, selects an independent minor from the real-row support
union, solves it over Q, and then runs the complete saved-system verifier. It is
a pivot reader/lifter; it does not implement another column generator or rank
engine. For n=11 it reads arbitrary-index exact `MCOLGEN1` batches directly,
validates every batch and pivot index, and records each batch SHA-256 in the
exact-leg report.

`sketch_separator.py` handles the dual route for a `NON_MEMBER` sketch. It
replays the named CountSketch exactly, solves for a rational left separator on
sketch buckets, composes that separator back to exact real-row weights, and
checks every column in the named saved-system family. A negative remains only
a bounded null for that finite family.
