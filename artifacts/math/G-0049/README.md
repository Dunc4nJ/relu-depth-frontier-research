# G-0049 — clean-room verification of the G-0046 candidate

G-0046 found a rank-7,302 modular relation on all 8,427 registered rows at
both primes.  That is only a sampled finite-field result.  This directory
contains an independent verifier with two separate gates:

1. a direct modular replay of every frozen row from the persisted
   baseline, cross, missing-tree, witness, old-batch, and 1,024-row matrices;
2. a fresh complete primitive ordered-cone normal-form reconstruction of
   every active support atom using subset dynamic programming over all
   `11!` coordinate orderings.

The verifier does not import the G-0046 or G-0033 semantic implementations.
It independently reconstructs the 16,000 same-family and 9,200 cross-family
raw candidates from the pinned MAX10 certificate, applies the frozen quotient
representative maps, binds the missing all-tree representatives, and checks
every serialized support descriptor against those sources.  It also computes
the explicit `5E` and `5L` linear vectors directly.

The frozen candidate is registered-only: its 7,100-position active union
contains no missing-tree or base column.  All 35 serialized missing-tree
positions have zero coefficients at both primes, and no `5E`/`5L` position
was pivoted.  The verifier checks those facts before using them to avoid
unnecessary semantic reconstruction.

```bash
.venv/bin/python -B artifacts/math/G-0049/verify_g0046_relation.py --self-test
.venv/bin/python -B artifacts/math/G-0049/verify_g0046_relation.py --preflight-only
.venv/bin/python -B artifacts/math/G-0049/verify_g0046_relation.py \
  --workers 8 \
  --output artifacts/math/G-0049/g0046_relation_cleanroom_verification_v1.json.gz
```

The verifier rejects duplicate JSON keys, coefficient-plus-one mutations,
target-row misindexing, endpoint mutations, and constant-`5E` /
rank-scaled-`5L` semantic mutants.  It writes a refutation report if the
sampled relation has any nonzero global primitive hinge or linear residual.

## Executed result

The sampled gate passed and the global gate refuted the candidate:

| gate | mod 1,000,003 | mod 1,000,033 |
|---|---:|---:|
| nonzero residuals on 8,427 frozen rows | 0 | 0 |
| nonzero complete primitive-hinge residuals | 74,500 | 74,500 |
| nonzero linear residuals | 0 | 0 |

The 74,500 residual hinges are 11.3253% of the independently reconstructed
657,822-direction degree-five MAX11 primitive-hinge universe.  The
lexicographically first residual direction is

```text
(0,0,0,0,1,-2,-3,0,0,1,3)
```

with residues `907816 mod 1000003` and `502464 mod 1000033`.  This is a broad
failure, not a sparse near miss.  No rational lift and no further CEGIS repair
is licensed by this artifact.

Frozen verification report:

- `g0046_relation_cleanroom_verification_v1.json.gz`, SHA-256
  `77f3d68c022b752e7725537278d3cc4a658df183214992626b469ca4ab6dece1`;
- verifier revision used by that report, SHA-256
  `0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04`.

Residual implementation doubt: the verifier's generic histogram helper does
not implement diagonal loops.  This cannot affect this result because every
serialized graph support descriptor is parsed fail-closed as loopless and all
7,100 active atoms passed that check.  The helper must be hardened before it
is reused for a loop-inclusive subject.

## Claim boundary

Even a two-prime global-normal-form pass is not an exact rational identity.
It licenses attempting an exact-Q lift; it does not establish one.  It also
does not establish completeness of the registered family or a result about
arbitrary two-hidden-layer networks.  Conversely, a global normal-form
failure refutes this candidate despite its success on all 8,427 sampled rows.
