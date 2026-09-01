# G-0187 result — an exact basis with half the relation bookkeeping

The frozen candidate is an exact basis of the complete 478-dimensional left
kernel of the G-0180 5,769 by 6,795 integer restriction matrix.

## Exact certificate

The clean verifier reconstructs the 5,769 by 478 integer coefficient matrix,
checks every row-to-STAR binding and primitive coefficient vector, and obtains
coefficient-matrix SHA-256
`01f22fc7c295167b10fe7290bd111935a52dc3805f3661f1e525938b3d6b42c4`.
Its column rank is 478 modulo each of 1,000,003, 1,000,033, 1,000,099, and
1,000,037, so the vectors are independent over \(\mathbb Q\).

A signed-128-bit replay checks all 3,248,010 entries of \(C^T A\) exactly.
Every entry is zero. The worst certified accumulation bound is
29,918,209,040,963,550,720, far below \(2^{127}\). The upstream rank-5,291
minor and these 478 independent null vectors give matching rational rank
bounds, so the candidate spans the entire left kernel. Adding one to the
coefficient at output row 821 produces 368 nonzero equations and exactly the
added frozen matrix row.

## Sparsity gain

| metric | G-0181 canonical basis | G-0187 basis |
|---|---:|---:|
| total nonzero coefficients | 228,692 | 115,540 |
| median support | 32 | 16 |
| support at most 6 | 100 | 124 |
| support at most 20 | 204 | 280 |
| support at most 100 | 302 | 365 |
| maximum support | 2,528 | 2,372 |

The total bookkeeping falls by 49.4779%. All 124 support-at-most-six vectors
have coefficients only in \(\{\!-1,1\}\). The improvement is not uniform:
64 of 478 vectors still have support above 1,000.

The union of output rows used by a full basis is 4,174, leaving 1,595 rows
identically zero on the kernel. This union is basis-invariant: a coordinate
appears in the support union of a basis exactly when its coordinate projection
is nonzero somewhere on the kernel subspace. Therefore no other full basis can
reduce the total distinct STAR normal forms below these 4,174 records, although
it can substantially reduce relation-term bookkeeping or early-stage unions.

| object | SHA-256 |
|---|---|
| frozen basis | `24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe` |
| clean verifier | `a46940aa3c7437fab23c9806a473387ff95b76b4e3b22b9a4cda650f0892b983` |
| exact replay source | `b884768a002285874a0720856ce3830bbf13fa62201940869c57859f0cbe4dc9` |
| four-prime rank source | `d920479efdc0db73f23bb3db29213979adba8c500d8400573d573cca5fef1b35` |
| promoted replay receipt | `7ca63356cd2be226800feada8fb3d9601e217a44752736736ec521923f8241fa` |
| zero exact residual | `0d524e78f6d1bac29604afd200941c59e760e61e121428b9e18b58d66a2bfcdd` |

## Strategic consequence and boundary

This basis exposes 124 local relations suitable for staged complete-normal-form
tests and cuts sparse combination work roughly in half. It does not prove that
any newly exposed vector belongs to the old-primary span \(O\), nor that its
finite restriction is a zero complete function. It does not prove the full
STAR quarantine, decide MAX11 membership, establish ansatz completeness, or
give an unrestricted neural-network lower bound.
