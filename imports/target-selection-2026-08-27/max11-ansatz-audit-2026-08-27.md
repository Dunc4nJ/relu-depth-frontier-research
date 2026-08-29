# `max_11` ansatz-size audit

Date: 2026-08-27  
Upstream certificate repository: <https://github.com/kilianar/max-relu-certificates>  
Pinned upstream commit: `2343f1213302e3431344595423e69e3395537020`

## Existing certificate sizes

The public exact certificates have the following nonzero template support:

| `n` | paper parameter `k=floor((n-1)/2)` | nonzero certificate terms | JSON bytes |
|---:|---:|---:|---:|
| 5 | 2 | 3 | 290 |
| 6 | 2 | 4 | 381 |
| 7 | 3 | 57 | 5,783 |
| 8 | 3 | 69 | 7,046 |
| 9 | 4 | 337 | 38,703 |
| 10 | 4 | 402 | 46,678 |

These are sparse *solutions*, not the size of the full linear system searched.

## Exact size of the stated full template ansatz

The paper defines `E_n` as all `n(n+1)/2` unordered index pairs including loops, `M_{n,k}` as the size-`k` multisets over `E_n`, and a template as a pair `(A,B)` modulo simultaneous `S_n` relabeling and exchange of `A` and `B`.

`analyze_ansatz_size.py` uses Burnside's lemma to count these template orbits exactly. For a permutation `g`, a `g`-fixed multiset is counted by the degree-`k` coefficient of

\[
\prod_{O\in E_n/\langle g\rangle}(1-x^{|O|})^{-1}.
\]

For the color-swap half of the group action, fixed pairs are in bijection with multisets fixed by `g^2`. Summing by cycle type avoids enumerating the raw pair space.

Observed counts:

| `n` | `k` | edge types | size-`k` multisets | raw unordered multiset pairs | symmetry templates |
|---:|---:|---:|---:|---:|---:|
| 5 | 2 | 15 | 120 | 7,260 | 131 |
| 6 | 2 | 21 | 231 | 26,796 | 144 |
| 7 | 3 | 28 | 4,060 | 8,243,830 | 4,469 |
| 8 | 3 | 36 | 8,436 | 35,587,266 | 4,716 |
| 9 | 4 | 45 | 194,580 | 18,930,785,490 | 210,540 |
| 10 | 4 | 55 | 424,270 | 90,002,728,585 | 216,428 |
| 11 | 5 | 66 | 12,103,014 | 73,241,479,993,605 | 12,179,657 |

Thus the full symmetry-reduced template column set grows by about `56.28x` from `n=10` to `n=11`; the raw unordered pair space grows by about `813.77x`.

The counter script SHA-256 is `fa7d2125ee154f54499cdbf96b84642c45029769f8a85f66b4a764ac2761acf0`. Its Burnside result was independently brute-force checked for every `n=1..4` and `k=1..2`; all eight small cases agreed exactly.

## Exact rows in the explicit full system

The row family can also be derived from the public formulation. On the sorted cone, each side has a coefficient histogram `a in N^n` with `sum(a)=k`. Because `E_n` contains every loop `(i,i)`, every weak composition of `k` is realized by a loop-only side. Consequently the raw hinge differences are exactly the integer vectors `d` satisfying

\[
\sum_i d_i=0,\qquad
s(d):=\sum_i d_i^+=\sum_i d_i^-\le k.
\]

The converse follows by adding the same weak composition of mass `k-s(d)` to `d^-` and `d^+`. Divide by the coordinate gcd, identify `d` with `-d`, and orient the primitive ray so its first nonzero entry is positive. If `S_j=sum_{i<=j}d_i`, summation by parts gives

\[
d\mathbin{\cdot}x=-\sum_{j<n}S_j(x_{j+1}-x_j).
\]

The oriented hinge is therefore inactive throughout the sorted cone exactly when all proper prefix sums are nonnegative. A retained hinge row is a primitive oriented direction whose proper prefix sums take both signs.

`analyze_hinge_rows.py` (SHA-256 `66cb5b25b309b8d5f3c77addc28230fa99a789cf13fccd55385a46d63397956b`) enumerates this finite set exactly. Its counts are:

| `n` | `k` | primitive unoriented rays | inactive fixed-sign rays | retained hinge rows | linear rows | total rows |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 2 | 55 | 40 | 15 | 5 | 20 |
| 6 | 2 | 120 | 85 | 35 | 6 | 41 |
| 7 | 3 | 1,491 | 861 | 630 | 7 | 637 |
| 8 | 3 | 3,262 | 1,834 | 1,428 | 8 | 1,436 |
| 9 | 4 | 38,991 | 18,306 | 20,685 | 9 | 20,694 |
| 10 | 4 | 87,000 | 39,843 | 47,157 | 10 | 47,167 |
| 11 | 5 | 1,088,923 | 431,101 | 657,822 | 11 | 657,833 |

Combining the exact row and column counts gives a `47,167 x 216,428` full matrix for `n=10` and a `657,833 x 12,179,657` full matrix for `n=11`, before any additional undocumented solver reductions. A hypothetical dense `n=11` matrix has about `8.012e12` cells, or about `64.1 TB` at eight bytes per cell; this is only a scale warning, not an implementation estimate for the sparse exact system.

An adversarial same-family reviewer reproduced the column counts with a separate cycle-type orbit formula, reproduced the row counts with an independent coordinate DFS, and exhaustively expanded the raw `n=5,k=2` pairs through the upstream verifier to recover the same 15 hinge directions. This is T1 corroboration, not independent-family or human review.

## What this estimate does not determine

The `657,833 x 12,179,657` shape is the exact matrix dimension for the *explicit full stated ansatz and the public hinge reduction*. It is not yet:

- the rank, sparsity, fill-in, memory footprint, or solve time of the rational system;
- a lower bound on the support of a possible `max_11` certificate;
- evidence that no much smaller selected subfamily contains a solution;
- evidence that the ansatz is complete for all two-hidden-layer ReLU representations;
- evidence for or against existence of an unrestricted representation.

The public repository contains the certificates and a deliberately slow permutation-enumerating checker, but not the optimized system builder/solver described in the paper. The explicit row count is now reproducible from the public formulation; the sparse nonzero count, exact rank, private reductions, and realistic solve budget are not.

## Target-selection implication

`max_11` remains a legitimate experimental rung, but “just run the `n=10` pipeline once more” is misleading. The prescribed `k` jumps from four to five, the full orbit-reduced column family jumps from 216,428 to 12,179,657, and retained hinge rows jump from 47,157 to 657,822. A launch should either obtain the optimized implementation, formulate a principled column-generation/restricted-family strategy, or predeclare a much smaller ansatz and treat failure only as a bounded null.

The fresh paper [Every Layer Counts](https://arxiv.org/abs/2608.23877) proves exponential-width separations between adjacent fixed ReLU depths with unrestricted weights. It makes the general depth-hierarchy lane more active, but it does not decide whether `max_11` has *some finite, unrestricted-width* two-hidden-layer representation.
