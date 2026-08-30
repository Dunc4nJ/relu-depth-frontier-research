# G-0114 preregistration addendum — graph-level recurrence falsifier

Frozen after the first G-0114 run showed that relation-only weights are
impossible, while a 556-parameter incidence system can jointly fit 5 -> 6 and
6 -> 7 but is a compressed solve rather than a formula.  No MAX8/MAX9 lift
census or coefficient comparison had been computed in this track.

## Why this test is discriminative

The public corpus contains a second genuine degree-raising transition:

```text
MAX6 degree 2 -> MAX7 degree 3
MAX8 degree 3 -> MAX9 degree 4.
```

If G-0112 exposed a reusable local identity, it should leave a trace in both.
The test below avoids the factorial ordered-cone evaluator.  It asks the
stronger, cheaper question whether the known target certificates themselves
can be recovered atom-by-atom from one-edge-per-branch lifts.

## Bound new inputs

```text
68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3  certificate_8_3.json
4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88  certificate_9_4.json
e0cb483d383021cba14730a4cac5b3f4c401106291b37f318233158ce3178edd  G-0113/degree5_quotient_census.py
```

The MAX6/MAX7 hashes remain frozen in `PREREGISTRATION.md`.

## Frozen canonical object

For each pair of branch multigraphs, construct a lossless colored incidence
graph containing:

- all coordinate vertices, including isolates, in one color class;
- two branch vertices in one color class (so global branch swap is allowed);
- one occurrence vertex for every edge occurrence, connected to its branch
  and endpoint coordinate(s), in one color class.

No common-edge cancellation is permitted: this census concerns full atoms,
not only their signed hinge parts.  `pynauty.certificate` is the primary
canonicalizer.  Controls must preserve the certificate under an explicit
coordinate relabeling and branch swap, and must reject an edge-multiplicity
mutation.  Sampled equalities are cross-checked by typed NetworkX VF2.

## Frozen region and decisions

For 6 -> 7 and 8 -> 9 separately:

1. append one distinct nonloop edge to each branch of every public source
   term;
2. retain either share-one or vertex-disjoint added-edge pairs; identical
   edges and loops are outside this addendum;
3. enumerate every raw descriptor in lexicographic source/left/right order;
4. quotient by the full-atom incidence certificate;
5. quotient target-certificate terms by the same certificate and sum exact
   rational coefficients within each class.

Primary output is exact target-class coverage.  One absent target class
rejects **atomwise certificate recurrence** for that slice, but does not reject
functional span membership.

If and only if all nonzero target classes are covered, form the exact
coefficient equations

```text
target_coefficient[q]
  = sum_(raw lift r in class q) source_coefficient[source(r)] * w[signature(r)]
```

using the already-frozen local degree/incidence signature from
`PREREGISTRATION.md`.  Solve first per transition and then jointly with one
shared weight vector.  Exact membership requires replay of every target and
zero-target class; a coefficient mutation and deletion of a nonzero weight
must fail.  A high-dimensional solution with large unrelated rationals is a
compressed solve, not a universal identity.

## Boundary

This can prove or reject graph-level recurrence only in the two enumerated
public-certificate transitions.  It cannot reject a different function-level
identity whose lifted atoms cancel into target atoms through nontrivial linear
relations, and it says nothing directly about MAX11.

