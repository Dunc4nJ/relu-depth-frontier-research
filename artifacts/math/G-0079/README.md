# G-0079 — same-component Y-spoke closure

This experiment closes the most immediate combinatorial hole exposed by the
exact G-0078 separator.  G-0073 required the auxiliary leaf of
`max(2*x_k, x_l+x_11)` to lie in the component opposite `k`.  G-0079 instead
enumerates every distinct `l` in the same MAX10 forest component as `k`, with
both outer orientations.

The registered subject is expected to contain 26,960 labelled new seeds and
18,582 new full-`S_11` orbit classes.  These must be disjoint from the 8,104
G-0073 classes, yielding 26,686 Y-spoke classes and three existing carrier
columns.  The family is evaluated on the already frozen 16,738-row system.

The first commit is intentionally preflight-only.  It reconstructs the old
and new orbit families, checks every proposed orbit merge by an independent
NetworkX VF2 path, binds all upstream raw bytes, crosses sampled old columns
against the frozen matrix, and exact-prices 60 old columns using the G-0078
rational separator.  The old controls must price to zero; 60 predeclared
synthetic row mutations must price nonzero.  Preflight evaluates **zero actual
new-family prices**.  Registered execution prices and logs all 18,582 new
columns before applying its frozen lexicographic selection rule.

The preflight also runs host-local inverse, bulk-price, quotient-batch
multiply, and large rectangular-rank benchmarks.  It records the exact operation counts that reject a naive dense
Schur matrix (about `1.26e12` multiply-adds before dense RREF) and projects the
rank-adaptive loop.  Timings are diagnostic rather than scientific payload
because they are host-dependent.  The registered path must stop if its actual
frozen-minor benchmark exceeds the preregistered wall/RAM gate.

The registered algorithm is batched quotient-row constraint generation, not
a growing-column inverse and not a dense fallback.  With the frozen old basis
`P,R` and `B=A[R,P]`, raw row `s` contributes
`q_s=C[s,:]-A[s,P]B^-1 C[R,:]` and
`t_s=b[s]-A[s,P]B^-1 b[R]`.  Each round chooses the target-last,
lexicographic free-zero basic solution, replays raw rows, collects the first
64 mismatches, and greedily retains only augmented-rank-increasing rows.  It
stops unresolved at 1,024 quotient rows, 16 batches, or six hours.  A dense
Schur fallback would be a separate preregistered experiment.

Modes:

```bash
.venv/bin/python -B artifacts/math/G-0079/same_component_y_spoke_closure.py \
  --self-test

.venv/bin/python -B artifacts/math/G-0079/same_component_y_spoke_closure.py \
  --preflight-only \
  --output artifacts/math/G-0079/same_component_y_spoke_preflight_v1.json.gz
```

`--run` is fail-closed until four independent pins are frozen in source and
also supplied explicitly: the final source hash, live preregistration-artifact
hash, preflight receipt hash, and preflight scientific-payload hash.  It hashes
and parses the preregistration artifact rather than trusting a CLI echo, and
requires an explicit unused output path.  The registered modular result will
be discovery-only under either branch; exact rational replay is a separate
experiment.
