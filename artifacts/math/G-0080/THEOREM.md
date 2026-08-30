# G-0080 — frozen theorem for the surviving three-wall arrangement

## Definitions

Let `P^2` be the Minkowski-sum closure of polytopes

```text
conv(Z0 union Z1),
```

where `Z0,Z1` are zonotopes; points and lower-dimensional zonotopes are
allowed.  Let

```text
J_2 = Delta_2 * square subset R^5
```

with vertex order `(T0,T1,T2,S00,S10,S01,S11)` as in G-0035.

Consider the three affine walls determined by their values on these vertices:

```text
h1=(-1,-1, 1 ; -1, 1, 1, 3),
h2=(-1,-1, 1 ;  3, 1, 1,-1),
h3=(-1, 1,-1 ;  1,-1, 3, 1).                    (1)
```

## Theorem

The arrangement (1) has eight full-dimensional maximal cells.  Every one of
the eight cells is outside `P^2`.  Consequently (1) is not a `P^2`
subdivision of `J_2`.

## Lemma 1 — complete two-ray summand cones

For each maximal cell `P`, the cone of nonnegative Minkowski edge scalings,
modulo translations, is

```text
K(P)=cone(r0,r1),                                 (2)
```

and the all-one scaling of `P` has exact coordinates

```text
(alpha0,alpha1),  alpha0>0, alpha1>0.             (3)
```

The coordinates, by chamber in the order used by the exact artifact, are

```text
(-,+,-): (1/3,1/3)     (+,-,-): (1/3,1/3)
(+,+,-): (1/4,1/4)     (-,+,+): (1/9,1/9)
(+,+,+): (1/6,1/6)     (+,-,+): (1/9,1/9)
(-,-,-): (1/3,1/3)     (-,-,+): (1/3,1/3).
```

### Proof

Give each edge `uv` of `P` a scalar `lambda_uv>=0`.  A weak Minkowski
summand has edge difference

```text
q_v-q_u=lambda_uv(v-u).
```

The scaled oriented differences close around each polygonal two-face.  The
two-face boundaries generate the graph cycle space of a convex polytope, so
these equations are sufficient to integrate the edge differences to a
global vertex map, unique up to translation.  They are therefore the
complete linear equations for the deformation/type cone.

The exact rational row reductions in the artifact give nullity two in all
eight cells.  Intersecting each two-dimensional nullspace with the
nonnegative orthant gives exactly the two recorded extreme rays in (2).
Direct exact substitution reconstructs every target vertex from (3).  QED.

## Lemma 2 — primitive blocks imply two-center feasibility

Let `Q=conv(Z0 union Z1)` with zonotopes `Z0,Z1`.  Then the extreme vertices
of `Q` admit a coloring by two centers `c0,c1` such that an extreme vertex
`v` colored `i` satisfies

```text
2 ci-v in Q.                                      (4)
```

### Proof

Every extreme vertex of the convex hull of two compact sets belongs to their
union: otherwise its expression as a convex combination of union points
would contradict extremality.  Assign `v` to a zonotope containing it.
A zonotope is centrally symmetric about its center, hence `2ci-v` is in the
same zonotope and therefore in `Q`.  QED.

Lemma 2 is only a necessary condition.  No converse is asserted or needed.

## Lemma 3 — exact primitive-ray classification

For six cells, neither endpoint of (2) nor any point in its positive
projective interior satisfies (4).  For chamber `(+,+,-)`, ray zero is the
genuine segment block, while ray one and the entire positive interior fail
(4).  For chamber `(+,+,+)`, ray zero is the genuine triangle
`conv(point union segment)` block, while ray one and the entire positive
interior fail (4).

### Proof

The endpoint polytopes are reconstructed exactly from the two edge-scaling
rays.  The segment and triangle have the explicit zonotope partitions stored
in the artifact.

Every other full-dimensional endpoint is independently faceted over
`Fraction`, and exact `QF_LIRA` returns `UNSAT` for (4).  For the positive
interior normalize one ray coefficient to one and write the other as
`theta>0`.  A positive Minkowski sum has the common refinement of the active
ray normal fans, independently of coefficient magnitude.  Its facet normals
are fixed and its support numbers are affine rational functions of `theta`.
The artifact independently re-facets the unit-support representative, checks
that every exact facet is inherited, and verifies active-normal rank five at
every retained image.  One symbolic query then returns `UNSAT` for all real
`theta>0` in each of the eight cells.

The 22 exact Z3 proofs are stored in the hash-bound gzip proof bundle.  With
one point-center per extreme vertex the same eight positive-support queries
are `SAT`.  The segment and triangle endpoint necessary queries are also
`SAT`, while their explicit partitions supply the sufficient certificates.
QED.

## Proof of the theorem

Suppose one maximal cell `P` belonged to `P^2`, so

```text
P = Q1+...+Qm
```

with every `Qj` a primitive block.  Type-cone coordinates are nonnegative
and additive under Minkowski sum.  Choose the obstructed ray recorded for
`P`: ray one in the two chambers with a genuine ray-zero block, and ray zero
in the other six chambers.  By (3), `P` has positive coordinate on that ray,
so some `Qj` must also have positive coordinate there.

By (2), `Qj` is either on that endpoint or in the positive projective
interior.  Lemma 3 says both possibilities violate the necessary condition
of Lemma 2.  This contradiction proves `P` is outside `P^2`.  The argument
applies to all eight cells, so (1) is not a `P^2` subdivision.  QED.

## Scope

This theorem is about the exact arrangement (1).  It is not a theorem about
arbitrary three-wall or multi-wall subdivisions of `J_2`; it does not decide
`J_2` itself, `W_2`, virtual `S_2` cancellation, or unrestricted `MAX11`.

