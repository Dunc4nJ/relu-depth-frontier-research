# G-0005 adversarial audit

Date: 2026-08-29
Verdict: **PASS**, bounded to balanced, simple, edge-disjoint two-coloured
spanning-tree templates at odd `n >= 5`.  This is not a statement about all
pair atoms or unrestricted two-hidden-layer ReLU networks.

## Independent derivation

Write `k=(n-1)/2`, and for a zero set `R` of size `r` let `A_r` count the
chosen tree edges whose two endpoints lie in `R`.  A colour class contributes
`2(k-e_C(R))`; therefore

```text
S_(0,n-r) = 2 (k * binom(n,r) - A_r).
```

Simplicity and edge-disjointness give `A_2=0`; the tree property gives
`A_3=P`, where `P` is the number of adjacent cross-colour edge pairs.  At the
two-zero/four-complement test point,

```text
S_(2,n-4) = 12 k * binom(n,4) - B_4.
```

If `N_11` and `N_12` are the relevant four-vertex incidence types, direct
counting gives

```text
A_4 = N_11 + N_12,
B_4 = 6 N_11 + 7 N_12,
N_11 + 2 N_12 = k^2 + (n-4) A_3,
```

and hence

```text
B_4 = 5 A_4 + k^2 + (n-4) A_3.
```

Substitution into the proposed functional cancels `A_4` and `A_3` exactly.
After imposing `2k=n-1`, the remaining polynomial is identically zero.  The
resulting raw coefficients are

```text
C_z =  12 n (n-2) (n-3),
C_u =  -5 n (n-2) (n-3),
C_v =  -4 n (n-4) (n-2),
C_w = -(n-3) (3 n^2 - 2 n + 4).
```

Their sum is 12.  `MAX_n` equals 2 at each of the four test points, so the raw
functional takes value 24 on `MAX_n`.  At `n=11` the raw tuple is

```text
(9504, -3960, -2772, -2760).
```

Dividing by 12 yields `(792,-330,-231,-230)`, whose sum is 1; the reduced
functional therefore takes value exactly 2 on `MAX_11` and zero on every
template in the stated family.

Balance is load-bearing: the tree has `n-1=2k` edges, which also explains the
odd-`n` hypothesis.  The four-vertex test requires `n>=5`.

## Independent exhaustion

The supplied checker was replayed on all 750 labelled `n=5` templates and 250
random templates at each of `n=7,9,11`; every in-family value was zero and its
non-tree negative control was nonzero.  A second implementation directly
summed the full `S_5` orbit over all 750 labelled `n=5` templates.

An independent enumeration then exhausted every unlabelled tree shape and
every balanced edge colouring modulo global colour swap:

| n | tree shapes | balanced colourings | maximum absolute separator |
|---:|------------:|--------------------:|---------------------------:|
| 5  | 3           | 9                   | 0 |
| 7  | 11          | 110                 | 0 |
| 9  | 47          | 1,645               | 0 |
| 11 | 235         | 29,610              | 0 |

## Boundary attacks

The reduced `n=11` functional is nonzero on explicit examples obtained by
dropping each load-bearing assumption:

| outside-family example | value |
|---|---:|
| balanced, simple and disjoint but disconnected two-component graph | -79,833,600 |
| simple/disjoint spanning tree with a 4/6 colour imbalance | 1,300,561,920 |
| balanced template with an overlapping edge | 333,849,600 |
| balanced template with a loop | -127,733,760 |

This shows that tree structure, balance, edge-disjointness, and loop-free
simplicity cannot be dropped wholesale.  It is not an iff characterization:
some atoms outside the family may still lie in the kernel.

## Novelty audit

Verdict: **NO_PRIOR_FOUND** under searches run through 2026-08-29, not a proof
of novelty or priority.

Searches covered the exact polynomial `3n^2-2n+4`, the coefficient tuple
`792,-330,-231,-230`, balanced two-coloured tree templates, signed-span/MAX/ReLU
combinations, pairwise-max symmetrization, and arXiv index/full-text searches.
The retained twelve-paper primary corpus was also screened.  No exact or
equivalent separator was found.

Closest non-equivalent antecedents:

- Rueß et al., [arXiv:2607.21651](https://arxiv.org/abs/2607.21651), define the
  same two-edge-coloured multigraph ansatz but give a lower-dimensional
  obstruction below minimal degree, not this tree-family separator.
- Wang and Basu, [arXiv:2608.25221](https://arxiv.org/abs/2608.25221), use the
  same atom family without a tree/forest dual obstruction.
- Koutschan et al., [arXiv:2305.16933](https://arxiv.org/abs/2305.16933), prove
  a simplex zero-summand/low-arity obstruction that does not apply to these
  full-dimensional minimal-degree tree blocks.
- Hertrich et al., [arXiv:2105.14835](https://arxiv.org/abs/2105.14835), use an
  alternating ray-evaluation functional for a different `H`-conforming class.
- Averkov et al., [arXiv:2502.06283](https://arxiv.org/abs/2502.06283), develop
  invariants under rational/decimal restrictions; those restrictions are
  load-bearing and non-equivalent here.

The phrase “minimally cyclic forests” in surrounding exploratory notes is
awkward and should not be read as terminology for this theorem.
