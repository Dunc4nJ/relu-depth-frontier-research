# G-0187 freeze — exact sparse basis for the retained STAR kernel

Frozen at `2026-09-01T10:45:33Z`, after exploratory multi-prime reconstruction
and exact replay had produced the candidate, but before a fresh independent
promotion replay. This is a post-discovery verification freeze.

## Candidate

The frozen candidate is
`candidate/exact_sparse_left_kernel_basis_v1.jsonl`, SHA-256
`24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe`.
It contains 478 primitive integer vectors in 5,769 output coordinates.

Exploratory work observed 115,540 total nonzero coefficients, support range
4 through 2,372, median support 16, and a 4,174-row support union. It also
observed exact annihilation of the frozen 5,769 by 6,795 matrix and rank 478
at four primes. Those observations are not the promotion gate.

## Frozen inputs

| object | SHA-256 |
|---|---|
| sparse candidate | `24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe` |
| G-0180 matrix | `d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd` |
| G-0179 STAR census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0181 exact-rank receipt | `98796b66b0ee1775be900d6e186dd3af7caae3c7ee522261c52c396c0e501934` |
| G-0181 canonical exact basis | `56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232` |

## Fresh promotion gate

A verifier written after this freeze must:

1. bind every frozen hash, matrix shape, candidate schema, row-to-STAR sequence
   mapping, relation order, support count, primitive gcd, and nonzero decimal
   coefficient encoding;
2. recompute the complete support histogram, total 115,540 terms, median 16,
   and 4,174-row union rather than trusting serialized summaries;
3. stream all 3,248,010 entries of \(C^T A\) with exact arithmetic and require
   zero residual, with an explicit arithmetic-safety argument;
4. independently require coefficient-matrix rank 478 modulo each of
   1,000,003, 1,000,033, 1,000,099, and 1,000,037; one full-rank modular minor
   gives rational independence, while the other primes are redundant controls;
5. bind the G-0181 exact rank theorem, apply rank directions correctly, and
   conclude that the 478 independent exact null vectors span the complete
   retained left kernel over \(\mathbb Q\);
6. compare exact bookkeeping with the canonical basis: total terms 115,540
   versus 228,692 and median support 16 versus 32;
7. justify the 4,174-row union as basis-invariant: a coordinate appears in the
   support union of a basis exactly when its coordinate projection is nonzero
   on the kernel subspace;
8. reject a one-unit coefficient mutation by exact full-matrix replay; and
9. re-hash all inputs at exit and refuse to overwrite an output.

## Claim boundary

Success would certify a smaller exact basis for the already known
478-dimensional frozen restriction kernel. It would improve the relation
bookkeeping and expose more local circuits. It would not prove that any new
kernel vector belongs to the old-primary span \(O\), classify complete
normal-form residuals, prove the STAR quarantine, decide MAX11, establish
ansatz completeness, or imply an unrestricted ReLU lower bound.
