# G-0076 — target-aware kernel resolver

G-0075 found modular augmented rank 6,877 on 15,360 genuinely
four-valued rows plus 460 selected G-0074 rows, leaving 1,231 augmented
kernel dimensions.  That rank alone does not say whether the MAX11 target is
inside or outside the sampled column span.

G-0076 answers the missing target-aware question.  It regenerates all 128
registered four-level panels, appends **all 1,378** G-0074 rows, and computes a
canonical RREF basis of the right kernel of `N = [A | b]` modulo 1,000,003.
The projection of this kernel onto its final target coordinate determines

```text
epsilon = rank(N) - rank(A).
```

- `epsilon = 0` gives a canonical modular target relation for exact lifting.
- `epsilon = 1` selects the exact left-dual route.

Neither branch is a rational result by itself; exceptional primes can lie in
both directions.  The producer therefore labels both outcomes unresolved and
exports the canonical kernel only as a reusable Schur quotient.  A later exact
all-row right replay or exact all-column left-dual replay is required before
promoting a bounded-family claim.

Large deterministic `.npy` checkpoints live in `cache/` and are ignored by
Git.  Every cached panel is rechecked against its registered separate matrix
and target hashes, and the full prefix is checked against the G-0075 direct
and selected-460 hashes before algebra begins. The registered run also emits
a deterministic compressed copy of canonical `H_N` outside the ignored cache;
that quotient artifact is retained with the small outcome receipt.
