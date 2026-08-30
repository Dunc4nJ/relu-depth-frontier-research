# G-0075 — nested four-level augmented-rank gate

## Why this is the immediate critical path

G-0074 supplies one shared rational coefficient vector for every input whose
eleven coordinates assume at most three distinct real values.  That is a
genuine continuum result, but it leaves a large coefficient space and does not
reach a generic point of `R^11`.

The next cheapest coordinates that can change the answer are the genuinely
four-valued profiles.  Normalize four distinct levels by translation and
positive homogeneity to

```text
0 < a < b < D.
```

For each spacing pair `(a,b)` there are exactly
`C(10,3) = 120` count profiles in which all four levels occur.  The other 244
four-colour count profiles physically use at most three levels and therefore
lie in the full exact G-0074 row span; retaining them would add cost and
apparent row count, but no new constraint beyond that full system.

G-0075 freezes 128 deterministic interior spacing pairs at the prime
denominator `D = 257`, split into nested tranches of 64 and 128 panels.  It
evaluates the 8,104 frozen Y-spoke orbit columns and the three carriers on all
120 genuinely-four-valued profiles at every selected panel.  The first tranche
has 7,680 new source rows; the full tranche has 15,360.

## Why 64, not 32, is the first meaningful direct tranche

The G-0074 matrix has a registered exact nonzero 460-row minor, and G-0075
retains exactly those 460 old rows.  A four-level panel adds at most 120 new
row dimensions.  Since the augmented matrix has 8,108 columns,

```text
ceil((8108 - 460) / 120) = 64.
```

Thus 32 panels cannot possibly yield the decisive full augmented rank in this
frozen direct gate.  This is not a universal minimum for four-level
testing.  Even 64 panels leave only 32 source-row dimensions of slack, so the
128-panel extension is frozen before either outcome is viewed.

## Direct rows and exact decision rule

Every new panel row is retained exactly.  The 460 independently selected
G-0074 pivot rows are appended unchanged.  The 64-panel integer matrix has
8,140 rows and 8,108 augmented columns; the 128-panel matrix has 15,820 rows
and the same 8,108 columns.  The last column is the exact MAX11 target.

Only one outcome is theorem-bearing:

> If a direct augmented matrix has rank 8,108 modulo any registered prime,
> an emitted 8,108 by 8,108 minor has determinant nonzero modulo that prime.
> Its determinant is therefore a nonzero integer, so that same direct matrix
> has rank 8,108 over Q and R.  Consequently the target is not in the real span
> of the complete frozen 8,107-column family.

This argument has no exceptional-denominator loophole: modular full column
rank is a one-sided lower bound on the characteristic-zero rank of the same
integer matrix.  No compression or collision argument is needed.

Any rank below 8,108 is **inconclusive**.  It is retained only as a constraint
space for the constructive path; it is not membership evidence and is not a
MAX11 network.  In particular, deficiency does not show that the 460 selected
old rows span the entire G-0074 row space over Q or R; no exact full-matrix
rank upper bound of 460 has been established.

## Frozen preflight

No four-level rank outcome was viewed while freezing these bindings:

```text
preflight artifact SHA-256:  bbe4e8410e2d042deea2844aa7099f2601feaa201d903557ca09d5f16f2514e0
scientific payload SHA-256:  74aca0d8898174800df31576d311122b930a77ea708dd1fdc1241ca34b2598e4
panel manifest SHA-256:      b44d1542dfc96fa8180ace56dbefdede9cf30a6fbb0882c71075c04660b2e124
G-0074 pivot list SHA-256:   ae2c251e791268b1fe42107cf82e44442dbd8e050eb368e35e19115d644cd8e2
environment manifest SHA-256:12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c
registered producer SHA-256: ba169bb9b3734c14d30afebba925a358e6f68a0cdd9734a30d78390438567bab
```

The registered producer refuses an existing output path, requires its exact
preregistered SHA-256, replays the preflight, and checks producer and upstream
bindings again before writing an outcome.

## Missing-colour reduction

If a nominal four-colour profile omits a colour, its occupied levels are
`u < v < w` (or fewer).  Translation by `-u` and positive scaling by
`1/(w-u)` reduce the row to a three-level spacing `t=(v-u)/(w-u)`.  On every
fixed assignment, each frozen atom is affine between consecutive F6 switch
nodes.  The registered G-0074 rows at those adjacent nodes, together with the
verified shift degrees (six for a Y-spoke column, one for `C_L` and `C_E`, two
for `C_Y`, and one for MAX11), therefore reconstruct the omitted row exactly.
The preflight mechanically checks this reduction on deterministic panels and
all missing-colour profile types.

## Boundary

A full-rank outcome rejects only the frozen Y-spoke-plus-carriers family, even
with arbitrary real output coefficients.  It is not a lower bound for all
two-hidden-layer ReLU networks.  A deficient outcome is not a construction.
If the family survives, the next positive-path verifier is the complete gated
facet normal form; those coordinates must retain oriented gate boundaries and
collapse collinear three-branch gradients before hashing.
