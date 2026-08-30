# G-0078 result — exact 230-row obstruction for the frozen Y-spoke family

## The exact theorem

Let `A` be the frozen `16,738 × 8,107` integer evaluation matrix of the
8,104 full-`S_11` Y-spoke orbit columns and the three carriers `C_L`, `C_E`,
and `C_Y`.  Let `b` be the MAX11 target column in the same normalization.
The complete augmented matrix `[A | b]` has raw-int64 SHA-256

```text
41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095
```

The preregistered adaptive exact lift produced a rational row vector `y`,
supported on only 230 of the 16,738 rows, for which

```text
y^T A = 0      on all 8,107 construction columns,
y^T b != 0.
```

Consequently `b` is outside the column span of `A` over both `Q` and `R`.
Thus the complete frozen Y-spoke-plus-carrier family cannot represent MAX11,
even with arbitrary real output coefficients, on this bound row system.

This is an exact finite-family theorem.  It is not an unrestricted
two-hidden-layer ReLU lower bound.

## Certificate and proof

G-0077's modular computation adaptively selected 229 primitive basis rows and
the first target-mismatch row `s = 2410`.  G-0078 selected a nonsingular
`229 × 229` subsystem, solved its transpose over `Q`, and serialized integer
weights `U_1,...,U_229,d`.  If `r_i` is a selected raw row and `g_i` is the
gcd of all 8,108 entries in that augmented row, the raw rational functional is

```text
y[r_i] = U_i / g_i,
y[2410] = d / g_2410,
y[r] = 0 otherwise.
```

The exact production verifier recomputed every row gcd and division from the
immutable full matrix, then established

```text
sum_i U_i A[r_i,:]/g_i + d A[2410,:]/g_2410 = 0
```

entry by entry across all 8,107 columns.  The corresponding target pairing is

```text
-133983976591838155692739468995654488385375268983412555455167208022395819866232233253671595525158820759909165251604480000
```

and is nonzero.  If `b = A c` for any real vector `c`, applying the real
functional `y` would give both `y^T b = y^T A c = 0` and `y^T b != 0`, a
contradiction.

The certificate has gcd one, all 229 selected numerators are nonzero, its
largest numerator has 417 bits, and its common failing-row weight has 390
bits.  All support rows occur among the first 21 genuinely-four-valued panels:
the selected rows are at most 2407 and the mismatch row 2410 is panel 20,
levels `(0,120,183,257)`, count profile `(1,2,3,5)`.  The obstruction is
therefore already visible on 230 four-level profile evaluations; the remaining
rows make the family binding complete but are not needed by this separator.

## Independent clean-room replay

The standalone verifier in `artifacts/cleanroom/G-0078/` does not import or
call the G-0077 or G-0078 producers.  With Python arbitrary-precision integers
and `fractions.Fraction`, it independently:

- bound the exact artifact and full matrix bytes;
- recomputed all 230 augmented-row gcds and exact divisions;
- replayed all 8,107 construction-column residuals as exact zero;
- reproduced the exact nonzero target pairing and modular lineage; and
- rejected every one-unit mutation of all 229 selected numerators and the
  failing-row weight.

Bindings:

```text
G-0078 producer SHA-256:       6aec90e28318b45680d3ee94254ff491d5eab89df9eec112fe9b5e66ce4f5229
G-0078 exact artifact SHA-256: 8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96
scientific payload SHA-256:    0bb1a524503359529bb592030f220be86d88756b797e55c4be04c031852bd573
clean-room verifier SHA-256:   39fd3b6f0a74ef22b264e16bb184eed2d5094a32c08ab018124182dd10ff5d52
clean-room receipt SHA-256:    d5149c9e6495e97549ffb43d5a2f1d75cd4ca71929dec6fc6e09c5d613f42119
clean-room payload SHA-256:    b5c469436e99485b7f3adfdf272af543f95926aee653aa45ace7fa2081bb3f50
```

## Claim boundary

The theorem excludes exactly the hash-bound 8,107-column family on the
hash-bound 16,738-row system.  It does not show that this family is complete
for arbitrary two-hidden-layer networks; it excludes neither other graphical
atoms, other facet-gluing templates, nonsymmetric blocks, arbitrary real inner
directions, nor unrestricted architectures.  The clean-room replay is
fresh-context same-model-lineage T1 evidence, not different-family or human
review, and novelty is not claimed.

## Forest-level consequence

Further exact solving inside the 8,107-column family is finished.  The useful
new object is the separator itself.  For any proposed new orbit column `phi`,
the exact scalar

```text
price(phi) = y^T phi
```

is a decisive first-stage test.  If every column in an enlarged family has
zero price, the theorem extends immediately to their combined span.  A
nonzero price identifies a direction that crosses this obstruction, although
it does not by itself produce a MAX11 identity.

The next discriminator is therefore to price the complete certified
7,015,841-record loop-inclusive signed-degree-five universe from G-0038 (plus
its `5E` and `5L` bases) on these 230 rows.  This creates a high-value fork:
either an exact much broader degree-five obstruction, or a concrete ranked
set of missing atoms for target-aware column generation.  Only after that
finite but broad test should effort return to a general normal-form bridge or
to more elaborate full-dimensional facet-gluing blocks.
