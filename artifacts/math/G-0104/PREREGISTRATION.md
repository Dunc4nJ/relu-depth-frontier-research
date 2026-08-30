# G-0104 preregistration — joint semantic and leaf/bridge incidence gate

Registered before any outcome-producing joint solve.

## Exact finite question

Over `F_p`, `p = 1,000,003`, let `A` be the frozen 8,427-row semantic
matrix used by G-0046 for its 22,265 columns, ordered as 13,419 registered
graph-pair columns, 8,844 missing balanced-tree columns, then the explicit
`5E` and `5L` columns.  Let `b` be the frozen MAX11 target.  Let `D` be the
1,387 by 12,459 leaf/bridge incidence matrix from frozen G-0099, with
`D(F,T) = 11 r(T,F)`, aligned bijectively to the balanced-tree columns of
the G-0046 dictionary and zero on every non-tree, `5E`, and `5L` column.
Let `t` be G-0099's exact 1,387-coordinate dominant-c2 projection of the
published MAX10 certificate, reduced modulo `p` from its serialized rational
coefficients.

The registered question is exactly whether

```text
A c = b  and  D c = t
```

has a solution over `F_p`.

## Frozen inputs

| Input | SHA-256 |
|---|---|
| `artifacts/math/G-0099/MANIFEST.json` | `508d4cec92e18da90f889bfbc1e4e34f73db5d56ee66bc0f65d21ee0a1b87121` |
| `artifacts/math/G-0099/leaf_bridge_n10_n11_v1.json` | `a853803b0a59174d497cf9e1f9d6409db9157290a74cd6d56a5156adba36a7d9` |
| `artifacts/math/G-0046/heldout768_all_tree_schur_v1.json.gz` | `924ecdb9dfdbf8e445fa1c46d0e3ac96d0cf2435227a18bd6a635cdda898cf2b` |
| `artifacts/math/G-0033/all_tree_block_schur_prefix256_v1.json.gz` | `c82556e2569bd9618d7328f96c45a8f48e675b00bd2f3e5544962cd687fe8159` |
| `artifacts/math/G-0033/missing_tree_residual_rows_v1.npy` | `879bcbfe596bb6dd0ae3ed7f62396ca180280fbd0d250848a2ecbe0371cb7491` |
| `artifacts/math/G-0033/missing_tree_residual_rows_v1.json` | `be8c4cafd3afd8172d8fb50376470e44bde6bca6107e68557a4a59723165ea6a` |
| `artifacts/math/G-0049/g0046_relation_cleanroom_verification_v1.json.gz` | `77f3d68c022b752e7725537278d3cc4a658df183214992626b469ca4ab6dece1` |

The producer will bind every transitive semantic input reported by G-0046,
plus its own script hash, before and after the run.  Any drift aborts.

## Column-alignment contract

G-0099 tree index `j` is the index in frozen
`artifacts/math/G-0023/all_tree_universe_v1.json`.  A tree representative is
serialized canonically as an unordered globally-colour-swappable pair.  Each
of all 12,459 G-0099 representatives must map exactly once either to a
registered G-0046 pair or to a G-0033 missing-tree column.  There must be no
duplicate canonical keys, no absent trees, and no graph column classified as
a tree unless it has such a key.  The expected split is 3,615 registered and
8,844 missing.  `D` is identically zero on the other 9,804 registered graph
columns and on `5E`,`5L`.

## Computation and decision rule

G-0046 exports a 7,302 by 7,302 nonsingular semantic minor `S` and a
semantic solution `c0` that replays all 8,427 rows.  Eliminate its basis
variables.  For nonbasis columns `N`, compute the incidence Schur system

```text
Delta = D_N - D_C S^{-1} A_RN
error = t - D_C c0_C,
```

where `R,C` are the frozen semantic pivot rows/columns.  Rank `Delta` and
`[Delta|error]` over `F_p`.

- Equal ranks: `MODULAR_JOINT_MEMBER`.  Export one deterministic canonical
  modular candidate, replay every one of the 8,427 semantic and 1,387
  incidence rows, then run the independent G-0049 complete ordered-cone
  normal-form machinery on the candidate.  A global residual refutes that
  candidate.  If resource-safe, append a deterministic small residual batch
  and perform at least one CEGIS repair round.
- Augmented rank larger: `MODULAR_JOINT_NONMEMBER` for exactly this frozen
  22,265-column dictionary and field.  Export/replay a separator if the
  implementation can do so without exceeding the resource bound.
- Any failed control, hash drift, alignment ambiguity, inconsistent ranks,
  or less than 12 GiB available memory: `INVALID_OR_ABORTED`, with no outcome
  claim.

The implementation may first try a deterministic 1,387-column extension
minor selected from nonbasis tree columns.  If its Schur block is singular,
that is not a negative outcome; it must rank the full nonbasis Schur system
or report an honest resource-bounded abort.

## Required controls

Before accepting the joint verdict, the unchanged implementation must:

1. Replay the frozen G-0046 semantic-only solution on all 8,427 rows.
2. Reproduce rank 1,387 and target membership for G-0099 `D` at `p`.
3. Show the frozen registered-only G-0046 solution fails `D c = t`.
4. Reject an incidence-alignment mutation by changing one stored `r` entry
   and observing failure of the independently stored stabilizer-weighted
   direct/reverse identity.
5. After a joint candidate is exported, change one target coordinate by one
   and observe a nonzero incidence residual while the unmutated target has
   zero residual.
6. Replay every joint row, not only pivot rows.

## Resource and custody boundary

Run as one `nice -n 10` process.  Refuse to start or continue a large
allocation when `/proc/meminfo` reports less than 12 GiB available.  Do not
touch G-0081 files or processes.  Do not move Git HEAD, commit, push, or
download.  All writes are direct children of `artifacts/math/G-0104/`.

## Claim boundary

A positive result is one modular candidate inside this finite dictionary.
It is not a rational lift, an exact real identity, a global identity unless
the independent complete normal form passes, completeness of degree five,
necessity of `D`, or an unrestricted two-hidden-layer MAX11 result.  A
negative result excludes only this frozen dictionary over this prime under
the imposed sufficient candidate-generator constraint; because `D` is not
known necessary, it is not a lower bound of any broader kind.
