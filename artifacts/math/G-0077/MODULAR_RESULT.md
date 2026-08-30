# G-0077 modular result — sparse exact-lift opportunity

The preregistered canonical modular stage completed successfully and remains
explicitly unresolved over characteristic zero.

```text
prime:                       1,000,003
rank(A):                     6,876
canonical basis rows:        6,876
canonical basis columns:     6,876
first target mismatch row:   2,410
mismatch residual mod p:     137,129
modular dual support:        229
target pairing mod p:        862,874
all 8,107 A columns replay:  zero mod p
```

The support size is the actionable result.  The canonical modular left dual
uses only 229 of the selected basis rows, plus mismatch row 2,410.  Therefore
the next exact discriminator should restrict to those 229 rows, select a
canonical 229-column nonsingular subsystem, solve it over the rationals, and
replay the resulting integer dual against every one of the 8,107 columns and
the target.

Sparse exact success would be definitive for the frozen finite family.  Sparse
exact failure would not refute the existence of a dense exact dual: a
coefficient that is zero modulo 1,000,003 may be nonzero over Q.  Failure must
therefore fall back to the registered 6,876-dimensional G-0077 route.

## Bindings

```text
producer SHA-256:           278aabc77cf32ab8fea8e84f80667eeb88ddc29255f646a1616d88bd4664f279
preflight SHA-256:          49e6e9714ef427d461d2940f7ccc7751ebf0b3d06a4a29065779b251429602a6
modular receipt SHA-256:    9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4
full matrix raw SHA-256:    41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095
```

The modular command completed in 506.3 seconds with peak RSS 6.7 GiB.  These
figures are resource diagnostics, not mathematical evidence.
