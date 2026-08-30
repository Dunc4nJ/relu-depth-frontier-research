# G-0071 — bounded loop–edge face-gluing audit

## Bottom line

This artifact audits one sharply defined asymmetric lift family and stops
before any semantic-column or rank computation.

Starting from each of the 252 full-support, two-component, loopless MAX10 base
terms selected by the pinned G-0006 rule, it chooses an anchor `k in {1,...,10}`
and an orientation, then appends

```text
loop(k,k) to one branch, edge(k,11) to the other.
```

There are exactly `252*10*2 = 5,040` labelled seeds.  Every one passes the
intended facet-11 identity: both added generators expose the same point `e_k`,
so the restricted outer block is the original MAX10 block plus a common point
carrier.

That local success does **not** make the construction automatically compatible
on ridges.  The exhaustive ordered-face control finds:

```text
unordered seed/ridge tests                         277,200
generator projections commuting                    554,400 / 554,400
outer-block ordered faces commuting                268,128 / 277,200
outer-block ordered faces noncommuting               9,072 / 277,200
noncommuting cases with exact support witness         9,072 / 9,072
```

The 9,072 noncommuting cases split exactly as follows:

```text
delete {anchor,11}                                  5,040
delete {anchor,another old vertex}                  4,032
```

This is a useful negative result about the **strong, term-by-term gluing
interpretation**.  It is not a no-go theorem for the weighted family or for
MAX11.  Different atom-level ordered faces can still cancel after the 252
certificate terms and their signed coefficients are aggregated.

For the standard interpretation in which a candidate atom is summed over its
full `S_11` coordinate orbit, the audit goes one step further: all 277,200
seed/ridge cases satisfy the exact transposition involution

```text
path(i,j) of P = path(j,i) of swap(i,j)P.
```

Consequently, the ordered-face residual is exactly zero inside **each full
coordinate orbit**, before applying any of the 252 rational coefficients.  It
is therefore also zero for their weighted sum.  This does not turn the local
facet identity into a lift theorem.  It says that ordered-ridge commutation is
automatic after full symmetrization and hence is not the discriminating global
test.

## Exact face calculus used by the audit

Each generator is the segment `[e_a,e_b]`; a loop `(a,a)` is the point `e_a`.
For a deleted set `D` in an `n`-coordinate simplex, use the exact direction

```text
|D|*mu - sum_{i in D} e_i.
```

For a branch with `m` generators its support, multiplied by `n`, is

```text
m*|D| - n*(number of generators with both endpoints in D).
```

Projection is also exact:

- neither endpoint deleted: retain the segment;
- exactly one endpoint deleted: retain the other endpoint as a loop/point;
- both endpoints deleted: retain the zero point, represented by omitting the
  generator.

The outer block `conv(P union Q)` retains both projected branches on a support
tie and only the higher branch on a strict inequality.  The implementation
checks the support formula independently by maximizing over both endpoints.

Two different codimension-two notions are kept separate:

1. **Direct equal-weight deleted-set face:** expose once in the displayed
   `D` direction.
2. **Ordered iterated face:** expose a facet, then expose the second facet in
   the resulting simplex.  This is the exact lexicographic face operation.

Generator projection commutes between the two deletion orders.  The outer
`max` between branches need not, because a strict first step irreversibly
discards one branch.  The script compares exact canonical branch descriptors;
for every descriptor mismatch it additionally supplies an integer direction
on which the two block support functions differ.  Thus all 9,072 listed cases
are geometric mismatches, not merely different presentations of one polytope.

The simplest mandatory mismatch is the ridge `{k,11}`.  Deleting `k` first
makes the branch containing `loop(k,k)` strict-lower and discards it.  Deleting
`11` first ties `loop(k,k)` with `edge(k,11)` at the common point `e_k`, so both
base branches survive into the second step.

The raw mismatch remains a real obstruction to any nonsymmetrized construction
that demands atom-by-atom face compatibility.  In a full orbit sum, however,
the coordinate transposition exchanging the two deleted labels pairs it with
the opposite residual while fixing all surviving coordinates.  The script
checks that descriptor identity exhaustively rather than inferring it only
from symmetry.

## Canonical descriptors and frozen inputs

The seed orbit descriptor is the `pynauty` canonical certificate of a typed
incidence graph with three colour classes:

- eleven coordinate vertices;
- two indistinguishable branch vertices, allowing global branch swap;
- ten edge-occurrence vertices, retaining loops and multiplicity.

This gives 3,754 exact coordinate-relabeling/global-branch-swap orbits from the
5,040 raw seeds.  The exact-labelled signed key is independently cross-checked
against the hash-bound G-0049 implementation.  Base selection is independently
recomputed and compared with the hash-bound G-0006 selector.  The complete
loop-inclusive G-0038 census, manifest, and 7,015,841-record stream are bound
by SHA-256 but are not scanned into a semantic or rank subject.

Frozen input SHA-256 values:

```text
certificate_10_4.json
  10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4
G-0006/evaluate_minimal_lifts.py
  a2ed2e6d8749770fb5a0732ab65f84b592d0562c68947f5ae35676237e1f2862
G-0038/independent_loop_inclusive_census.py
  16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb
G-0038/independent_loop_inclusive_census_v1.json
  98469e1cdaaaeac411db16439bbc7f2226b9416ee32d9df1e78f214c2cda0078
G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json
  1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640
G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz
  e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd
G-0049/verify_g0046_relation.py
  0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04
```

Deterministic output anchors from the completed bounded audit:

```text
raw seed manifest
  9cf4430a67623e7ba0698cd90cff271f69a30230d6b4d12da400c99b2594b5b9
orbit class manifest
  aeebb03311dcf7b6862c1444b5eb4df240f0b2dfc544a30d1ca1f6e67200e02a
facet-11 restricted descriptor stream
  7e638def14d35a8c2644de237eb2b61145f50e5e6b261bc2a24b4a300fe1c644
codimension-two comparison stream
  63f0c2d984a23f07249eda6da2d5961ff3c43e020887e2efe13cc38876811b62
codimension-two support-witness stream
  42b2c93e8e5a669e5a03d7b4e63ef2d89d59aebbc52627bbf3c5f4bddec880bc
orbit transposition-pairing stream
  86271e83e2ec0500ce746a3c2a1a06bbac4d09168ceaea5a27351fda9f34a924
scientific payload
  2afdc471e6afdb717e2eb1a5181f43254a424621cc4eb19e49da297d7306e3ef
```

## Reproduction

Both modes are read-only and emit one JSON object to standard output:

```bash
.venv/bin/python -B artifacts/math/G-0071/loop_edge_face_gluing_preflight.py \
  --self-test

.venv/bin/python -B artifacts/math/G-0071/loop_edge_face_gluing_preflight.py \
  --preflight-only
```

The hostile controls reject incident-edge deletion, tie-as-strict selection,
retaining a deleted–deleted segment, a loop-count-changing orbit mutation, a
missing seed, and nondeterministic enumeration.  They also verify coordinate
relabeling and global branch-swap invariance.

## Claim boundary

No registered full semantic/rank subject is created.  No coefficient solve,
exact network compilation, global replay, MAX11 feasibility claim, or
unrestricted depth lower bound follows from this artifact.  In particular,
the 9,072 termwise mismatches do not rule out aggregate cancellation, and the
5,040 facet-11 successes do not establish a global lift.

The next high-leverage gate is not another commutation census.  For the direct
solution search, it is a preregistered **3,754-orbit global span gate**:

1. use this artifact's exact orbit manifest to choose one deterministic
   representative per coordinate-relabeling/global-branch-swap class;
2. reconstruct every complete loop-inclusive degree-five semantic column with
   the hash-bound exact normal-form engine;
3. deduplicate only exact complete semantics, never hashes alone;
4. append the resulting block to the then-current exact baseline/quotient
   state and test target charge together with every hinge and linear row;
5. promote nothing modular without exact-Q lifting, compilation, and global
   replay.

That is a new semantic/rank subject and is intentionally absent here.  The
5,040-to-3,754 orbit reduction, input pins, and hostile canonicalization
controls are the handoff.

If the goal is instead to justify the word “lift” geometrically, a separate
localization audit must construct the exact lower-arity normal form of

```text
F_11(sum_{sigma in S_11} sigma * loop-edge-seed)
```

and compare the 252-term coefficient-weighted result with the pinned
`S_10`-orbit MAX10 normal form, allowing only explicitly tracked linear/common
carriers.  The present program merely binds G-0049 and never invokes its
semantic normal-form engine, so that orbit-localization calculation remains a
separate, preregisterable subject.
