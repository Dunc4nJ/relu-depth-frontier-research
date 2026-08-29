# G-0046 — full held-out Schur update

The G-0033 relation fit rows `0:256` but fails 681 of the frozen rows
`256:1024` at each registered prime.  Exact-Q lifting is therefore ineligible.

`full_heldout_schur.py` reuses the valid rank-6,883 prefix basis and projects
only the 768 unseen rows through 22,265 columns: all 22,263
registered-plus-all-tree graph atoms and the explicit zero-signed-graph bases
`5E` (five common nonloops) and `5L` (five common loops).
It fails closed on input drift, checks the old refutation and the registered
denominator's absence of identical branches before starting the large solve,
reports the separate modular rank effects of `5E` and `5L`, and blockwise
replays any relation or separator it emits.

```bash
.venv/bin/python -B artifacts/math/G-0046/full_heldout_schur.py --self-test
.venv/bin/python -B artifacts/math/G-0046/full_heldout_schur.py --preflight-only
.venv/bin/python -B artifacts/math/G-0046/full_heldout_schur.py \
  --block-width 256 --minimum-available-gib 12 \
  --output artifacts/math/G-0046/heldout768_all_tree_schur_v1.json.gz
```

The large run is expected to use roughly 6–12 GiB RSS and 20–45 minutes on
the current host; those are planning bounds, not observations.  The completed
report records actual wall time and peak RSS.  A favorable two-prime result
still requires complete semantic replay, then an exact rational lift and exact
all-coordinate replay before it can support a MAX11 identity.
