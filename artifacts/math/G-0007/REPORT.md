# G-0007 research report

## Executive result

This study extracted graph-theoretic structure from the public MAX9 and
MAX10 pair-atom certificates, tested several natural lift hypotheses, and
produced one exact MAX9 calibration certificate.

The result hierarchy is:

1. **Human proof:** no linear combination of maxima on proper subsets can
   equal MAX_N. See PROPER_SUBSET_NO_GO.md.
2. **Exact computation over Q:** the rational span of all 739 full-support
   two-colored tree atoms for MAX9 has rank 360; appending the MAX9 target
   raises the rank to 361. Tree atoms alone therefore cannot represent
   MAX9 in this atom model.
3. **Exact computation over Q:** a family of 710 bridge-generated tree
   atoms plus 186 published non-tree correction atoms has rank 505 and
   contains the MAX9 target. Exact solving yields the included 391-term
   certificate.
4. **Exploratory inference:** for MAX11, begin with all 12,459 full-support
   two-colored trees and add loopless correction strata in increasing
   cycle rank beta through beta=4.

Items 1–3 concern MAX9 calibration. Item 4 is a search proposal, not a
MAX11 theorem or certificate.

## Exact atom and graph definitions

A degree-k pair atom is an ordered pair (A,B), where A and B are multisets
of k unordered coordinate pairs. Its function is the symmetrization of

    max(
      sum_{(a,b) in A} max(x_a,x_b),
      sum_{(a,b) in B} max(x_a,x_b)
    ).

The quotient used for templates allows:

- one common relabeling of coordinate vertices;
- arbitrary ordering of edges inside each side;
- one global swap A <-> B.

It does not identify colors edge-by-edge.

For a term (A,B), define the colored union multigraph G(A,B) as follows.
Its active vertices are exactly labels incident to an edge; ambient
isolated labels are excluded. Every occurrence in A and every occurrence
in B is a distinct colored edge. Repeated edges count with multiplicity,
including an edge occurring on both sides. A loop is one edge and
contributes one to the standard multigraph cycle rank. If

    e = |A| + |B|,
    r = number of active vertices,
    c = number of connected components on active vertices,

then

    beta(G) = e - r + c.

Ambient isolated coordinates affect unnormalized symmetrization
multiplicity through (n-r)! but do not affect beta.

## Frozen inputs and kernel

The study pins the following upstream files:

| File | SHA-256 |
|---|---|
| verify_certificate.py | d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7 |
| certificate_8_3.json | 68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3 |
| certificate_9_4.json | 4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88 |
| certificate_10_4.json | 10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4 |

Repository HEAD observed at freeze time:

    91b8a96958d19f6709ccf6c1d4526c32996ff6b6

The exact expansion kernel is the pinned upstream verifier. It expands each
symmetrized atom on the ordered cone into:

- a length-n integer linear vector; and
- integer coefficients of primitive hinge directions.

Candidate matrices use one row per atom and one column per hinge or linear
coordinate. Rank is invariant under transposition, so the target belongs
to the atom span exactly when appending its row does not increase rank.

## Structural census

Both public degree-four certificates are loopless.

| n | terms | active-vertex histogram | beta histogram |
|---|---:|---|---|
| 9 | 337 | 5:1, 6:6, 7:31, 8:44, 9:255 | 0:151, 1:123, 2:53, 3:9, 4:1 |
| 10 | 402 | 5:1, 6:5, 7:15, 8:37, 9:63, 10:281 | 0:252, 1:104, 2:37, 3:8, 4:1 |

Thus every published MAX9/MAX10 support term lies in the analogous
loopless beta<=4 family.

Full-support strata have a useful parity geometry:

- MAX9 has e=8 on nine active vertices, so a connected full-support term
  can be a tree. The certificate has 151 such trees.
- MAX10 has e=8 on ten active vertices, so full support requires at least
  two components. It has 252 full-support two-component forests.
- MAX11 has e=10 on eleven vertices, so full-support trees become possible
  again.

## What does not lift simply

Exact colored-multigraph matching found 119 MAX9 template types recurring
in MAX10, with no ambiguous matches. Their coefficient behavior is not a
single recurrence:

- 71 distinct raw ratios lambda_10/lambda_9;
- 77 distinct ratios after multiplying each coefficient by (n-r)!;
- substantial variation remains within fixed (r,beta) strata.

Therefore neither a single scalar lift nor the obvious injection-factorial
normalization explains the coefficients.

Adding one edge of each color to every source support term is also not a
complete recurrence. A completed exploratory run reported coverage of 19
of 57 public MAX7 target terms and 290 of 337 public MAX9 target terms.
The corresponding NetworkX replay is slow and was not rerun to completion
during artifact freeze, so this observation is not a certification anchor.

The proper-subset linear lift is impossible by the triangular argument in
PROPER_SUBSET_NO_GO.md.

## Tree closure and its calibration value

The script colored_tree_closure.py canonically enumerates edge-colored
trees modulo vertex relabeling and global color swap. It reports:

| target | all colored tree types | bridge closure | closure fraction |
|---|---:|---:|---:|
| MAX9 | 739 | 710 | 96.08% |
| MAX11 | 12,459 | 11,072 | 88.87% |

For MAX9, the bridge closure covers 149 of the 151 published full-support
tree terms. This overlap should not be overinterpreted: the closure already
covers 710 of the 739 possible tree types. It is mostly a combinatorial
prior, not strong evidence of a coefficient recurrence.

The bridge operator used here starts from each full-support,
two-component forest term present in the public even-n certificate. It
adds one A edge and one B edge while introducing vertex n+1, and retains
candidates whose union is a tree. The closure counts therefore depend on
the public MAX8/MAX10 source supports; they are not closures of every
abstract forest orbit.

## Exact all-tree obstruction at MAX9

All 739 MAX9 colored tree atoms were expanded into 3,029 primitive hinge
coordinates and nine linear coordinates. Using python-flint exact integer
rank:

    rank_Q(tree atoms) = 360
    rank_Q(tree atoms plus MAX9 target) = 361

Therefore the target is not in the rational span of all tree atoms. The
extra 29 tree types outside the bridge closure do not increase the rank:
the 710 bridge trees already have ranks 360 and 361 before and after target
augmentation.

This is a reported exact-arithmetic obstruction for the matrix generated by
the frozen scripts. Its universal-family interpretation is conditional on
the correctness and completeness of the single-route enumeration and
expansion code. It is not an independently enumerated or proof-assistant
theorem.

## Exact MAX9 hybrid certificate

The calibration family contains:

- 710 bridge-generated tree atoms;
- 186 published MAX9 atoms that are not full-support trees;
- 896 candidates total.

Its exact rational rank is 505, unchanged after appending the target. An
exact 505-by-505 rational solve, followed by verification of every one of
4,722 coordinates, yields:

- 391 nonzero terms;
- 336 bridge trees;
- 55 published non-tree corrections.

Frozen outputs:

| File | SHA-256 |
|---|---|
| data/n9_hybrid_solution.json | 834bacdf69a1b19ba65f27d85df1947aa2c99221db59e202278f4b52a6a49d2c |
| data/n9_hybrid_certificate.json | 308378e362201f6ef97d5963f107af14748e38dc21556c31134f936eaa58ed42 |
| data/replay_attestation.json | 0b4aeb0e9929fc4528827fc4a513f6e285e56c615d5f4884e53eda8420b0e9a8 |

The solve is exact, not floating point. A modular rank at prime 1,000,003
is used only to select an independent square subsystem. The selected
subsystem is then solved over Q and every coordinate is checked exactly.
The included certificate also passes the pinned upstream verifier.

Intermediate column caches are created inside one fresh, caller-owned 0700
run directory. Producer scripts always regenerate them. Provenance-keyed
filenames and embedded metadata bind the cache schema, producer script,
cache-contract script, upstream expansion kernel, source certificate or
representative set, representative generator, and expected column count.
An atomically written cache index records byte hashes before downstream
loading; loaders securely read and hash bytes before unpickling. Tree
representatives have a separate manifest bound to the generator, public
MAX8/MAX9/MAX10 inputs, output hashes, byte sizes, and orbit counts. A
frozen replay attestation records the final cache-index hash, cache hashes,
script hashes, result records, and generated certificate hashes.

This design protects the recorded replay from accidental stale-cache reuse
and ordinary cross-run contamination. It is not a claim that Python pickle
is safe for inputs supplied by a hostile process with the same Unix user;
only use a fresh run directory created for this replay.

This alternative certificate is a calibration result. It should not be
described as progress on the minimal depth of MAX11.

As a supporting exact finite-field check, the 337 published MAX9 support
rows have full row rank modulo 1,000,003, hence also full row rank over Q.
Removing either of the two public tree terms missed by the bridge closure
and then appending the target raises the rank by one. Thus each missed term
is necessary if one insists on using only the remaining published support.
The hybrid certificate succeeds by introducing additional bridge-tree
atoms together with correction terms; it is not a coefficient-only rewrite
inside the original reduced support.

## MAX11 candidate ansatz

The evidence-grounded bounded family is

    A_11^(<=4, loopless)
      = {(A,B): |A|=|B|=5, no diagonal pairs, beta(G(A,B))<=4}
        / (S_11 x global color swap).

Recommended search order:

1. beta=0: all 12,459 full-support colored trees, not only the 11,072
   bridge-generated trees;
2. beta=1 corrections;
3. beta=2 corrections;
4. beta=3 corrections;
5. beta=4 corrections.

The MAX9 all-tree obstruction makes correction strata mandatory as a
calibration lesson. It does not prove that the analogous MAX11 tree span
misses the target; that must be computed.

Use streamed template generation, modular screening, exact rational
reconstruction, and exact post-verification. Do not materialize an
unnecessarily dense global matrix.

If an exact dual obstruction is found for the whole loopless beta<=4
family, widen in this preregistered order:

1. permit loops while retaining beta<=4;
2. add loopless beta=5;
3. only then widen further.

An UNSAT result before widening is a bounded null for the tested family,
not a theorem that no degree-five pair-atom MAX11 certificate exists.

## Epistemic limits and failure modes

- The expansion code is imported from the same upstream repository that
  supplies the certificates. This is a shared-kernel check, not an
  independent clean-room replay.
- The graph enumeration and canonicalization use NetworkX. Counts were
  replayed, but a second independent enumerator is still needed before
  promoting them to campaign evidence.
- Exact rank certifies the matrices actually constructed. A generator
  omission or quotient bug could invalidate a universal-family statement.
- The MAX11 ansatz is selected from only two neighboring certificates and
  is therefore vulnerable to retrospective overfitting.
- No claim in this artifact has been entered into the campaign evidence
  ledger.

## Next falsification step

Before a large MAX11 solve, implement an independent generator and an
independent atom evaluator, then reproduce:

1. 739 MAX9 colored tree orbits;
2. the exact MAX9 tree rank jump 360 -> 361;
3. the 391-term hybrid certificate;
4. the MAX10 structural census.

Only after those controls pass should the MAX11 beta-stratified search be
treated as evidentially informative.
