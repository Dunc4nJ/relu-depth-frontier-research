# G-0120 result — rooted Reynolds gap recurrence

## Outcome

The preregistered joint lower-transition gate is an exact null:

```text
result                         EXACT_Q_NONMEMBERSHIP
stacked rows                   21,331
frozen orbit-weight columns    17
rank_Q(A)                      13
rank_Q([A | b])                14
```

Therefore no single arity-independent rational assignment to the frozen 17
root-stabilizer edge-pair orbits satisfies both complete identities

```text
R_gamma(GapCert_6) = x_(7) - x_(6),
R_gamma(GapCert_8) = x_(9) - x_(8).
```

This is characteristic-zero nonmembership in the complete global
ordered-cone normal form.  It is not a sampled, hinge-only, floating-point, or
modular rejection.

Per the preregistered stop rule, `GapCert_10 -> Gap_11` and MAX11 were **not**
evaluated.

## Frozen route tested

The exact semantic reduction was

```text
Gap_n = n MAX_n - Ind_n(MAX_(n-1)) = x_(n) - x_(n-1).
```

Every source term was lifted by adjoining one distinguished root and one edge
to each branch.  The raw-sum weight depended only on the unordered appended
edge-pair orbit under the old-label stabilizer of the root.  The 17 weights
were constant across arity and had no source-graph, signature, degree,
residual-class, support, or hash dependence.

The source representations were fixed before the computation:

```text
GapCert_6  =  6 public-C6  - Ind_6(public-C5),
GapCert_8  =  8 public-C8  - Ind_8(public-C7),
GapCert_10 = 10 public-C10 - Ind_10(G-0115 395-term C9).
```

## Complete exact systems

| Transition | Raw lifts | Exact signed-W classes | Hinge rows | Linear rows |
|---|---:|---:|---:|---:|
| `Gap6 -> Gap7` | 5,488 | 909 | 630 | 7 |
| `Gap8 -> Gap9` | 255,150 | 35,327 | 20,685 | 9 |

Both raw counts reconcile independently through the raw-descriptor, orbit,
and signed-class-fiber totals.  Their deterministic matrix digests are:

```text
Gap6 -> Gap7  3ff706343b5c47c1a811bf13350c1ca5963c1a2db4279b7fb2adbb16b6793332
Gap8 -> Gap9  c2c88bc0740d7fbfe8ef7e1718c314596000e8a976b196468647aa2fd61721f2
stacked matrix 9261eefc7a1ef15dce5e43bb2fd97a683670671b8a88be3821a3fe5338f1c51d
stacked target c324b6a1eb38cba6045c890864a3930da3c6fefc2af77d45559488ad9d9581ed
```

## Exact witness and independent replay

The producer serialized 14 rows of the stacked integer system with

```text
rank_Q(A_witness)       = 13
rank_Q([A_witness|b])   = 14
witness canonical SHA256
  fb2100573ae3c72ddbea628834ac5f575ef9a96ece8d35efb70614bd5bcfe07c
```

The independent verifier imports neither the producer nor the normal-form DP.
It binds the result artifact, reconstructs integer matrices from the
serialized witness, and recomputes the ranks with FLINT.  It also observes
that the first 13 witness rows already give the tighter subwitness

```text
rank_Q(A_reduced)       = 12
rank_Q([A_reduced|b])   = 13
reduced canonical SHA256
  13872427b0db636f8d7d47f5620ef564018b5cd2e09149ae5c1311c229ab5cd7
```

Replacing the serialized target by zero collapses augmented rank back to the
matrix rank, providing a planted negative control.

## Controls that passed

- Public C5, C6, C7, C8, and C10 replay exactly as MAX; the frozen G-0115
  395-term C9 certificate also replays exactly.  A one-numerator-unit mutation
  of the first nonzero coefficient in each certificate is rejected.
- `GapCert_6`, `GapCert_8`, and `GapCert_10` have zero hinge residual and exact
  linear vectors `e_n-e_(n-1)`.  Their termwise induced lower certificates
  replay as `(n-1)x_(n)+x_(n-1)`.
- The rooted classifier has exactly the preregistered 17 orbit names and
  reconciles every ordered appended-edge pair at target arities 7, 9, and 11.
  Two fixed old-label relabellings and branch-edge swap preserve it.
- Moving the planted root, collapsing to an unrooted classifier, and mutating
  a planted branch edge are all detected.
- Literal permutation enumeration agrees with the exact DP on frozen degree-2
  and degree-3 rooted atoms.
- Before the scientific run, a synthetic 225-descriptor raw sum agreed
  entry-for-entry with the signed-W quotient matrix, while exercising both
  common-loop and common-nonloop corrections.  Its shared matrix digest is
  `585b3918b4b6202c96e3f054d75853234a64c341dc9ba80c5b850c88697d2647`.

## Artifact bindings

```text
PREREGISTRATION.md
  1f43bc85f8124e3147499527e6bd522e901c91d391b14d1d9c4fe12416ef8b79
rooted_reynolds_gap.py
  988a354bf797e138c720c24694b0c2f3c6da31874b7ca3dab027dbb937469846
rooted_reynolds_gap_result.json
  918de947cd2fb0bbc49849cbe76253b28f282c4f553c46525c73d6e98a6c9754
verify_rooted_reynolds_gap_result.py
  29d7c922dd917832d32c55c26ba8aa5f0056f3be78c8b18d1a9676f468009cd7
```

Verification command:

```bash
.venv/bin/python -B artifacts/math/G-0120/verify_rooted_reynolds_gap_result.py
```

Expected verdict: `VERIFIED_EXACT_Q_NONMEMBERSHIP`.

## Claim boundary

This null rejects exactly the frozen 17-orbit, arity-independent rooted
raw-sum gap kernel.  It does not reject degree-dependent rooted laws, richer
rooted flag algebras, other gap representations, source-dependent operators,
the unrestricted MAX10 lift span, the complete degree-5 graphical dictionary,
or MAX11 representability.  It supplies no MAX11 certificate and no
all-`n` theorem.
