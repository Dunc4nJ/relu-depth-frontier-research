# G-0074: complete three-level spacing gate

G-0073 proves that the frozen 8,104-orbit Y-spoke family plus three carriers
fits 364 symmetric profiles on the four levels `{0,1,2,3}`.  That is a weak
necessary condition: the matrix has rank 258 and leaves 7,849 free coefficient
directions.  G-0074 keeps the full coefficient space and adds a qualitatively
stronger infinite-locus test.

For a fixed labelled input with values in `{0,t,1}`, write `p=A-B` for the
difference of the two four-edge base sums and
`q=x_l+x_11-2*x_k`.  The two orientations flatten exactly to

```text
B + 2*x_k + max(0,p,q)
B + 2*x_k + max(0,p,p+q).
```

Consequently all switches occur on `p=0`, `q=0`, or `p-q=0` in the first
orientation and `p=0`, `q=0`, or `p+q=0` in the second.  Their affine
coefficients in `t` have absolute value at most six.  Every breakpoint in
`[0,1]` therefore belongs to

```text
F6 = {0, 1/6, 1/5, 1/4, 1/3, 2/5, 1/2,
      3/5, 2/3, 3/4, 4/5, 5/6, 1}.
```

Every profile residual is continuous and affine between adjacent nodes.
One shared coefficient vector that vanishes on all 78 count profiles at all
13 nodes therefore vanishes for every `t in [0,1]`.  Translation covariance,
positive homogeneity, and the retained all-ones row extend this from normalized
levels to arbitrary real inputs having at most three distinct coordinate
values.

For a count profile `p`, let `X_p` be its distinct labelled assignments.  Each
member of `X_p` occurs exactly `product_i(c_i!)` times in the full `11!`
permutation sum.  Hence

```text
sum_{x in X_p} Phi(x) = |X_p| * Sym_avg(Phi)(x_p).
```

The integer assignment-sum row is therefore a positive scalar multiple of the
pointwise symmetrized equation, not a moment condition that could hide
pointwise errors.  At `t=0` or `t=1`, two colour labels describe the same
physical level; the resulting binomial duplication multiplies both the family
row and target by the same positive factor.  Every endpoint profile is checked
against an independently generated binary row.

The registered system stacks the 364 G-0073 rows and all `13*78=1,014` Farey
rows into one `1,378 by 8,107` integer matrix.  Separate pointwise coefficient
solutions are explicitly forbidden and tested as a negative control.

The preflight derives the bound six mechanically rather than trusting only the
displayed algebra.  It enumerates the complete affine-state superset
`{0,t,1}` for each edge maximum, all four-edge sums, every possible `p` and
`q`, and both `p-q` and `p+q`.  Every resulting switch form has intercept and
slope bounded by six and every root in `[0,1]` lies in `F6`.

The exact resolver never interprets modular ranks as rational conclusions.
It accepts membership only after an exact rational square solve and independent
full-row `Fraction` replay.  It accepts nonmembership only after constructing
an exact rational row dual, replaying it against all 8,107 columns, and
normalizing its target value to one.  Exceptional-prime controls are included.

A member is still not a global MAX11 identity, because inputs with four or
more distinct values remain unchecked.  The next decisive gate would be the
global facet-curvature normal form.  A nonmember rejects this entire frozen
Y-spoke-plus-carrier family over real output coefficients, but is not an
unrestricted two-hidden-layer lower bound.

Frozen preflight identifiers:

- producer SHA-256: `269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d`
- preflight scientific payload: `fc166ac93a268c54c85c9e15f43fcd9c0cfba16b3ebb4d3c3951df39c3c188df`
- preflight artifact SHA-256: `a89e5b9a2366fb1d119981a49de2c72b8686255e0e522f7ce2ba0af829c26969`
- row manifest SHA-256: `53e1766ce236da801ae963b47ee9ce42cdf5a10b978ccd69c9c9152b03ca140f`
- environment manifest SHA-256: `12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c`

```bash
.venv/bin/python -B artifacts/math/G-0074/farey_three_level_gate.py \
  --self-test --skip-full-vf2

.venv/bin/python -B artifacts/math/G-0074/farey_three_level_gate.py \
  --preflight-only \
  --output artifacts/math/G-0074/farey_three_level_preflight_v1.json.gz
```

The registered `--run` command is added to the append-only experiment ledger
only after this frozen subject is committed and pushed.
