# G-0075 universal four-level arrangement audit

## Verdict

The finite-arrangement reduction passes this independent exact audit. Every
frozen G-0075 positive-profile column is affine on each of 2,774 open cells
cut out by a universal 150-line arrangement in the normalized triangle
`0 < a < b < D`. This is an overarrangement: the audit does not claim that
every enumerated line is active for a frozen column.

The statement that the first 64 and all 128 panels occupy 62 and 122 cells is
not literally correct. Those numbers count weak positive/nonpositive
signature buckets. Eight of the first 64 panels and 17 of all 128 panels lie
on a universal wall, so they occupy no open two-dimensional cell. The literal
open-cell counts are 56 and 108, respectively.

## Why the line set is complete for the frozen semantics

Fix one assignment of the coordinates to levels `(0,a,b,D)`. Strict ordering
makes every graphical edge maximum select a fixed level. Thus each four-edge
sum `L` or `R` has a nonnegative level-coefficient vector of mass four. The
two Y-spoke orientations flatten to

```text
max(L+2k, R+2k, R+l+n)
max(L+2k, R+2k, L+l+n).
```

Every branch therefore has a nonnegative coefficient vector of mass six. A
pairwise switch difference `d` satisfies `sum(d)=0` and
`sum(max(d_i,0)) <= 6`. Primitive enumeration of all such differences, then
retaining only walls that cut the open normalized triangle, gives 150 lines.
The carrier `C_Y` is the mass-two subcase; `C_L`, assignment-fixed `C_E`, and
the target introduce no omitted internal walls. Summing assignments is
linear, so profile symmetrization cannot introduce a wall outside their
common refinement.

Two constructions agree exactly: the direct mass-six difference enumeration
and a separate enumeration through `p`, `q`, `p-q`, and `p+q`. The latter has
35 four-edge sums, 309 `p` forms, 37 `q` forms, 923 switch forms, and 361
primitive lines before clipping to the triangle.

## Exact census and bindings

- Producer: `four_level_arrangement_audit.py`
- Producer SHA-256:
  `b2bbfa13ee98f03170eaa5fc01a55238c7ca9e69f01a31e8c4476dbb10823000`
- Frozen G-0075 panel-manifest SHA-256:
  `b44d1542dfc96fa8180ace56dbefdede9cf30a6fbb0882c71075c04660b2e124`
- Universal line-manifest SHA-256:
  `eda2cd19ab89cb47fb58221070311b040ae5061c220b5477cdb11d1980c287a7`
- Interior vertices: 1,539
- Interior incidence-manifest SHA-256:
  `f667e3252fca70bb8586b02298be31357ecdc153cfbb0e8664ec7d76e1174440`
- Incidence sum `sum_v(r_v-1)`: 2,623
- Open cells: `1 + 150 + 2,623 = 2,774`
- Cell-signature-manifest SHA-256:
  `0586843f364698c2b2d086889cfec81ef73466535e62234df0022f9b217c4609`
- Exact polygon-manifest SHA-256:
  `0525df30ae6f0db393865c947b1722f5a1506ec67293affc2be111408c150785`
- First-64 weak-signature-set SHA-256:
  `22d8a9b07adc3fdb291351105f9dfd357f1de90bb170d5cce39e8e18b9883ba9`
- All-128 weak-signature-set SHA-256:
  `23d30f4ab4e148381fb55f37b16f92d21db64debccb20c10a0868f0218469c48`

The cell count was obtained in two ways: exact intersection-incidence
counting and exact rational polygon splitting. Polygon splitting produced
2,774 distinct sign vectors as well as 2,774 polygons.

## Complete finite test: use vertices, not three fresh probes per cell

Three non-collinear rational probes inside every cell are sufficient: for a
fixed positive profile, the residual is affine there, and three zeros force
that affine form to vanish. Continuity then extends the equality to walls.

They are not necessary. The arrangement has only 1,575 distinct polygon
vertices: 1,539 interior vertices and 36 boundary vertices. An affine
function on a cell polygon is determined by its vertex values, and the audit
checks that the union of polygon vertices is exactly this 1,575-point set.
Thus all vertices and all 120 positive profiles require 189,000 rows, rather
than `2,774 * 3 * 120 = 998,640`. The 1,539 interior vertices primitive-normalize
to levels `(0,A,B,D)` with `D <= 36`; their integer-level manifest SHA-256 is
`d6d430560e27739225c1e9273194b014ea89499dd89d952a3d44be30f2ae68e3`.

Using only the 184,680 interior-profile rows is sufficient only when the
boundary continuum is independently enforced. The selected 460 G-0074 rows
have not been proved to span every G-0074 row over the rationals or reals, so
they alone must not be substituted for a complete boundary condition.

## No-claim boundary

This audit validates the universal finite-arrangement reduction for the
frozen G-0075 columns and profile semantics. It does not compute the rank of
the 189,000-row system, produce a shared coefficient vector, construct a
MAX11 network, prove frozen-family membership or nonmembership, or establish
an unrestricted ReLU lower bound.
