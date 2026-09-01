# G-0181 result — exact rational rank 5,291

The post-discovery candidate passed the prospectively frozen independent gate.
For the exact frozen G-0180 matrix (A\in\mathbb Z^{5769\times6795}),

\[
\operatorname{rank}_{\mathbb Q}(A)=5291,
\qquad
\dim_{\mathbb Q}\ker(A^T)=478.
\]

## Exact upper bound

The frozen candidate contains 478 primitive sparse integer vectors.  The
clean-room verifier checked every field and row-to-record binding, 228,692
nonzero terms, primitive gcds, stored support and coefficient statistics, and
a 478 by 478 free-row restriction that is diagonal with nonzero diagonal.
The vectors are therefore independent over (mathbb Q).

It then computed all 3,248,010 entries of (C^T A).  Every entry was exactly
zero.  The residual byte stream is 25,984,080 zero bytes with SHA-256
`012ac2606487b7e79e0e4e6a39ad4cee0e246ac395e5de26badbb8cb8aa9a77a`.

The verifier's worst possible signed accumulation bound was
8,611,681,743,059,915,520, below (2^{63}-1) by
611,690,293,794,860,287.  Thus its sparse signed-64-bit multiplication was
exact for every product and every partial sum.  These 478 independent left
null vectors give

\[
\operatorname{rank}_{\mathbb Q}(A)\le 5769-478=5291.
\]

## Exact lower bound

The hash-bound G-0180 receipt proves rank 5,291 after reduction modulo
1,000,003.  A nonzero modular 5,291-minor comes from an integer minor that is
nonzero over (mathbb Q), so

\[
\operatorname{rank}_{\mathbb Q}(A)\ge5291.
\]

The two bounds coincide.

## Independent audit and controls

The clean-room verifier imports or calls none of the exploratory reconstruction
or replay code.  It rehashed the matrix, candidate, modular-rank receipt, and
its own source at entry and exit.  Changing the first candidate coefficient
from 1 to 2 produced 629 nonzero equations; the resulting residual was exactly
the added source row.

| object | SHA-256 |
|---|---|
| exact basis | `56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232` |
| clean-room verifier | `b6a733a35b9d7c0938b991977ba656e21d860b54b2e94803cca2addb56319d87` |
| clean-room receipt | `98796b66b0ee1775be900d6e186dd3af7caae3c7ee522261c52c396c0e501934` |
| exploratory reconstruction receipt | `58ffdd9d844db401f36f511115d306ba9b3c33ae133039faaa8c6417b435afe0` |
| exploratory replay receipt | `cec5089d318405e8a25811f2219512172fee45e4c7fde328df027613c2a66100` |

## Claim boundary

This theorem is about one finite restriction matrix.  Matrix-kernel vectors
need not be zero functions.  The result alone does not show that any relation
lies in the old primary span (O), prove the STAR quarantine theorem, decide
MAX11 membership, establish ansatz completeness, or yield an unrestricted
neural-network lower bound.

G-0182 separately certifies that the unique support-four basis vector does lift
to an exact complete-normal-form identity in (O).  The remaining obligation
is to generalize that mechanism to a basis of the other 477 dimensions.
