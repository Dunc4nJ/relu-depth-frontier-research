# G-0134 fresh-context T1 audit of the G-0132 residual

- Completed: `2026-08-31T06:15:39Z`
- Reviewer: `BlackIbis` (Codex / GPT-5; fresh context, same lineage; T1 only)
- Preregistration: commit `64866f6dac08a0be897b8decc80d40d76b0046c8`, SHA-256
  `5f0ec755c8aa96bccde392be97e3189f6eb1fc9dfbff508a5ced13ecd9fca6d2`
- Admitted source audit: commit `c0d2442ee3fb083c9267380cf40c81417fa0ae02`, SHA-256
  `8027f630749c3b4ce5611945d63cc526c09042c0b8f66baee1d1e9fc2c61efca`
- Admitted manifest: commit `441fd60884c23f4ede7a0689be736fb0fcb37b5d`, SHA-256
  `b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732`
- Admitted result: commit `5d84d6080eabcd833f4f96364ae02d7aeb7d72a3`, SHA-256
  `d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50`

## Verdict

`PASS — CONSISTENT_RESIDUAL`.

The independent exact coefficient at

```text
[0,0,0,0,0,0,1,-3,-2,1,3]
```

is

```text
363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360
```

It is nonzero and exactly equals the delivered G-0132 coefficient. Therefore
the frozen 132-term coefficient vector is false as a global orbit identity.
This refutes only that vector.

## Independent replay

The clean-room checker does not import, execute, or copy the G-0132 producer.
It reconstructs each selected signed graph from the frozen 163,740-record
input, independently projects the 176 coefficient slots to exactly 132
ordered nonzero terms (44 zeros), builds signed cut-increment tables, and uses
a separately written subset dynamic program to count every labelled
permutation whose word is an integer multiple of the audited primitive
direction. The reconciled census is exactly
`132 * 11! = 5,269,017,600` labelled contributions.

The independent check also covers lexicographic firstness. Because a degree-five cut
increment lies in `[-5,5]`, every canonical direction before the reported one
has six leading zeros. Exhaustive enumeration of the remaining five entries,
followed by zero-sum, primitive, first-positive, ordered-chamber-active, and
lexicographic filters, gives 336 possible earlier directions. The independent
aggregate is exactly zero on all 336. All 68 frozen carried directions also
reprice to exact zero.

An independent negative-first-word DP recomputed every term's 11-coordinate
linear vector. It recovered the exact target scale

```text
2289393005496338240468982655090335335732668690900751540287809289663720291914849699943112917639850352050294840444775090516901570116753181129941246082620
```

and subtracted exactly `target_scale * 11!` once from coordinate 10:

```text
91385242721796234277152286846709897529373789600947119083360425853648790148306672502689249710846378532721209087065998333145056594036413380527638731630726016000
```

All 11 resulting linear residuals are zero. No hinge receives a target
subtraction.

## Custody and controls

The checker rehashed 72 distinct bound files at entry and exit, including the
source-audit artifacts, exact source/Cargo/executable, G-0128 result and
transitive inputs, manifest, result, and preregistration. Both censuses are
identical. Git ancestry is strictly G-0134 preregistration → frozen source →
G-0133 `PASS` → one-path manifest commit → one-path result commit. The result
was absent at the manifest commit; the manifest was absent at its parent.

The exact terminal path detected/rejected:

- `+1` to the first and final coefficients, yielding independently the same
  first mutant hinge coefficients `123648` and `11648`;
- omission of the final term, yielding the independently exact earlier
  residual recorded in the receipt;
- `+1` to target scale or target coordinate 10, giving linear residuals
  `-39916800` and `-1` at coordinate 10;
- `+1` to the reported residual, noncanonical sign, nonprimitive direction,
  record omission/reorder, and census drift; and
- branch swap and active-vertex relabelling as exact invariances.

The first full-pass attempt stopped before a verdict because the audit
incorrectly assumed the 68 carried directions were lexicographically ordered;
their frozen order is provenance order. The assertion was narrowed to exact
order preservation plus uniqueness, no receipt was written, and the complete
mathematical pass was rerun. This audit-side correction did not change the
formula, subject, direction, coefficient, or scientific comparison.

## Artifacts and boundary

- Checker: `artifacts/reviews/G-0134-g0132-result/cleanroom_residual_reprice.py`,
  SHA-256 `40109063ed2210b3a9ba11d52618d28e55eac9e5da7146d4bb0377b8da6fa9ee`
- Receipt: `artifacts/reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json`,
  SHA-256 `a00aaca7aeb8f960d6fa5a264b72a13c797ae30a75c4eec5eaa90a5a455e2f56`

This T1 result does **not** prove frozen-family nonmembership, family
completeness, a compiled two-hidden-layer architecture, MAX11
nonrepresentability, an unrestricted lower bound, `REFEREED` or `FORMALIZED`
standing, or a Lean theorem. No architecture/MAX11/Lean promotion is permitted
without the separately preregistered compilation and independent
compiled-network replay required by G-0134.
