# G-0124 result — isolation-aware rooted Reynolds relaxation

## Exact bounded outcome

Both preregistered lower-transition families are inconsistent over `Q` on the
complete 21,331-row ordered-cone system:

| Stage | Frozen law | Columns | `rank_Q(A)` | `rank_Q([A|b])` |
|---|---|---:|---:|---:|
| A | `gamma_o + delta q_n(t)` | 18 | 14 | 15 |
| B | `gamma_o + eta_o q_n(t)` | 34 | 28 | 29 |

Here `q_n(t)` is the number of old labels isolated in both branches of the
source pair before adjoining the new root.  Stage A's exact inconsistency
witness has 15 rows; Stage B's has 29 rows.

The preregistered `Gap10 -> Gap11` holdout was **not evaluated**.  G-0124
therefore supplies no MAX11 candidate and no conclusion about MAX11
representability.

## What the new statistic changed

The old G-0120 reduced witness was not merely carried forward.  Its primitive
left relation has nonzero pairing with the new isolation columns:

```text
Stage A main-effect sensitivity
  -9291200118022368

Stage B
  all 17 orbit-slope sensitivities were serialized;
  at least one is nonzero.
```

Thus the isolation statistic genuinely destroys the old obstruction.  The
complete systems nevertheless contain new obstructions.  This is stronger
negative evidence than observing the same witness under a renamed or rescaled
parameterization.

The source statistic was nonconstant throughout the lower gate:

```text
Gap6 source q distribution:  {0:3, 1:2, 2:1, 3:1}
Gap8 source q distribution:  {0:44, 1:48, 2:22, 3:5, 4:3, 5:1, 6:1, 7:2}
```

## Verification state

The quick verifier imports neither the scientific producer nor the normal-form
DP.  It:

- binds the 25 KiB result artifact by SHA-256;
- recomputes both serialized rank gaps with FLINT;
- checks that zero targets collapse augmented rank to matrix rank;
- independently recomputes both `q` distributions from the bound source
  certificates; and
- checks all 15 shared labelled witness rows: their 17 intercept coordinates
  agree and the Stage A slope equals the sum of the 17 Stage B slopes.

Its verdict is:

```text
VERIFIED_TWO_EXACT_Q_LOWER_NULLS
```

A stronger same-implementation reconstruction was started to rebuild all
21,331 rows and re-extract each witness row from the full matrices.  At
2026-08-31T03:38:00Z the research leader reprioritized the critical path and
ordered it stopped because it imported the frozen producer and therefore could
not count as clean-room evidence.  It was interrupted cleanly at
`14,000 / 35,327` `Gap8 -> Gap9` semantic classes; the process was confirmed
exited and wrote no result artifact.  This incomplete replay has no scientific
verdict and is not counted as a pass or failure.

Verification commands:

```bash
.venv/bin/python -B artifacts/math/G-0124/verify_isolation_aware_result.py --self-test
.venv/bin/python -B artifacts/math/G-0124/verify_isolation_aware_result.py
```

## Exact boundary and structural implication

The null eliminates only the two isolation-affine rooted raw-sum kernels on the
three frozen gap representations.  Together with the G-0120 reduced witness it
also shows why arity dependence, degree dependence, or orbit averaging alone
cannot rescue this construction: the first lower transition is already
inconsistent at one fixed arity, and averaging only rescales its old columns.

It does **not** eliminate a provenance bit, nonlinear source statistics,
several source flags, a different gap representation, richer rooted flag
algebras, the unrestricted MAX10 lift span, the complete degree-five graphical
dictionary, or a two-hidden-layer MAX11 network.  The result lowers confidence
in simple low-dimensional rooted recurrences, not in the unrestricted target
by a comparable amount.

Per the preregistered stop rule, G-0124 does not add a post-outcome feature to
rescue this branch.

## Artifact bindings

```text
PREREGISTRATION.md
  c70d2e3edace6a9148796ec364d3c5b10e5ca285204e0db83beadd490a98134d
isolation_aware_reynolds_gap.py
  a9247ea54b9025fe799a89bbb1ff24cc5949c0c6250c55a994a6d350774517ee
isolation_aware_reynolds_gap_result_v1.json
  63e2e30a42b102c3dea6e8cac781f28532f82573febc103a0ab756362da58142
verify_isolation_aware_result.py
  cc6e1871d675f019586a27edc4744bcfafc1de847d275245d21210e80e28f88a
```

Milestone commits are `ed9e299` (preregistration), `df6fd1c` (frozen
producer), and `fe493fb` (result and verifier).  They are contained in the
current `origin/master` history.
