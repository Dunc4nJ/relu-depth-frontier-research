# `t2-referee` — independent lattice-point falsifier for max certificates

A second, method-disjoint checker for the "max certificate" JSON format, built
for T2 review. It exists to *disagree* with the campaign's own verifier if the
campaign's verifier is wrong, so it shares no evaluator logic with it.

**No-claim line.** Agreement on lattice points falsifies but does not prove the
identity; this tool is a referee-side check, not a certificate verifier.

---

## 1. Pinned semantics

Everything below is read off the pinned upstream verifier at
`literature/repos/max-relu-certificates/verify_certificate.py`
(SHA-256 `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`,
recorded in that repo's `SOURCE_MANIFEST.sha256`).

### Schema

A certificate is a JSON object with `n` (integer) and `terms` (list). Each term
has `coefficient` (a string parsed by `fractions.Fraction`, so `"-11/2177280"`
style rationals) and `pair` (exactly two branches).
`verify_certificate.py:111-126`.

Each branch is a list of endpoint pairs `[a, b]` with `1 <= a <= b <= n`,
1-indexed; the verifier converts to 0-indexed internally
(`verify_certificate.py:28-38`). The two branches of a term must have equal
length (`verify_certificate.py:41-48`). Loops (`a == b`), repeated edges, and
edges common to both branches are all legal, and all occur in the shipped
certificates (for example `certificate_7_3.json` term 0 is
`[[[1,1],[1,1],[1,1]],[[1,1],[1,1],[1,1]]]`).

A term whose coefficient parses to zero is skipped before its `pair` is even
validated (`verify_certificate.py:123-126`). This tool matches that.

### Atom of a term

From the module docstring, `verify_certificate.py:1-10`, and the upstream
`README.md:5-10`:

```
atom(x) = max( sum_{(a,b) in left}  max(x_a, x_b),
               sum_{(a,b) in right} max(x_a, x_b) )
```

Operationally the same thing appears at `verify_certificate.py:51-55`, where
`side_on_ordered_cone` sends each edge `(a, b)` to the sorted coordinate of
higher rank, i.e. `max(x_a, x_b)`, and sums those.

### Symmetrization

`symmetrized_pair` loops over `permutations(range(n))` —
**all `n!` permutations, with no normalizing constant and no deduplication of
equal images** (`verify_certificate.py:79-107`, loop at line 84). A term's
contribution is therefore

```
Sym_t(x) = sum_{sigma in S_n} atom_t(x_{sigma(1)}, ..., x_{sigma(n)})
```

Note this makes the coefficients scale like `1/n!`: `certificate_5_2.json`'s
first coefficient is `1/120 = 1/5!`.

### Target identity

`total_linear[-1] -= 1` at `verify_certificate.py:136` subtracts exactly one
copy of the top sorted coordinate `x_n`, and the check at
`verify_certificate.py:137-143` demands the residue vanish identically. On the
cone `x_1 <= ... <= x_n` the top coordinate *is* `max(x)`, and the upstream
`README.md:12` says so explicitly. The identity being certified is therefore

```
sum_t coefficient_t * Sym_t(x)  ==  max(x_1, ..., x_n)      for all x in R^n
```

with target coefficient exactly `1`, no scaling by `n!` or anything else.

### Independent confirmation of the convention

The reading above was checked, not assumed. A throwaway brute force summed
`atom` over all `5!` (resp. `6!`) permutations at random rational points and
compared against `max(x)`: `certificate_5_2.json` and `certificate_6_2.json`
match on the nose, while the `/n!`-normalized variant is off by exactly `n!`.
The `structure_weights` counting used by this tool is separately checked
against literal `S_n` enumeration in `test_lattice_check.py`.

---

## 2. Method

The upstream verifier and `tools/verify11` both work on the sorted cone: they
build a linear form plus hinge functions per permutation and require the hinge
bookkeeping to cancel. This tool does none of that. It evaluates both sides
pointwise, exactly, at lattice points.

Both sides are symmetric functions, so a point is determined by the multiset of
its coordinate values. `{0,1}^n` therefore has `n+1` distinct value profiles and
`{0,1,2}^n` has `C(n+2,2)`; checking the profiles checks every one of the `2^n`
and `3^n` points.

A term only touches its active vertex set `V` (`v = |V|`), so

```
Sym_t(x) = (n-v)! * sum over injections phi: V -> [n] of atom(x_phi)
```

and, at a profile with value multiplicities `m_0, m_1, m_2`, the number of
injections realizing a given value pattern `p: V -> {0,1,2}` is the product of
falling factorials `prod_j (m_j)_{c_j(p)}`, where `c_j(p)` counts active
vertices sent to value `j`. Patterns are consequently only needed grouped by
their count vector. The implementation:

1. enumerates all `B^v` patterns with numpy (`B` is 2 or 3), chunked;
2. computes each pattern's atom vectorized (`np.maximum` over edges);
3. buckets exactly by `(count vector, atom value)` with `np.bincount`, whose
   unweighted output is exact `int64` — no float weights are ever used;
4. contracts against an exact integer placement matrix, cached per `(n, v, B)`;
5. accumulates numerators as Python integers, grouped by coefficient
   denominator, then merges the groups pairwise onto one exact common
   denominator and compares `numerator == target * denominator`.

No floating point value enters any comparison. Atom tables are cached by a
sound canonical key (active vertices relabelled to `0..v-1`, the unordered
branch pair oriented), so structurally repeated terms are computed once.

### What a PASS does and does not mean

Both sides are continuous piecewise-linear and positively homogeneous. A finite
set of lattice points cannot pin down such a function, so a PASS is evidence,
not proof. A FAIL, by contrast, is conclusive: a single lattice point where the
two sides differ refutes the identity outright.

### Why `{0,1}^n` alone is not enough

The 0/1 cube has a measured blind spot. Enumerating all 26,796 term structures
with two edges per branch at `n = 6` turns up 12,630 pairs of distinct
structures whose fully symmetrized values agree at every `{0,1}^6` profile yet
differ somewhere on `{0,1,2}^6`. Swapping one such structure into
`certificate_6_2.json` produces a corrupted certificate that the 0/1 cube calls
PASS and the 0/1/2 cube calls FAIL; the pinned upstream verifier independently
calls it `Fail`. That mutant is kept as a control
(`certificate_6_2_mutated_zero_one_blind.json`). Run `--profiles both`, which is
the default.

---

## 3. Usage

```bash
# both lattices, 4 worker processes, exact report written create-new
.venv/bin/python tools/t2-referee/lattice_check.py \
    literature/repos/max-relu-certificates/certificates/certificate_10_4.json \
    --profiles both --processes 4 --output report.json

# only the 0/1 cube
.venv/bin/python tools/t2-referee/lattice_check.py CERT.json --profiles 01

# build a synthetic timing input (its verdict is FAIL by construction)
.venv/bin/python tools/t2-referee/make_synthetic.py \
    --n 11 --terms 16000 --branch-edges 5 --min-bits 1000 --max-bits 4000 \
    --denominators shared --seed 20260903 --output synthetic.json
```

Exit codes: `0` PASS, `1` FAIL, `2` refused to overwrite an existing `--output`.
Reports are never overwritten; pick a new path instead.

Tests (the project venv has no pytest, so borrow the system interpreter's):

```bash
PYTHONPATH=.venv/lib/python3.13/site-packages python3 -m pytest \
    tools/t2-referee/test_lattice_check.py -q
```

### Performance

Measured on this 16-core host at `--processes 4`, `--profiles both`:

| input | terms | n | wall seconds |
| --- | --- | --- | --- |
| `certificate_10_4.json` | 402 | 10 | 1.9 |
| `recovered_n10_upstream.json` | 424 | 10 | 2.7 |
| campaign n=11 candidate, 1362 denominators | 15896 | 11 | 175 |
| synthetic, one shared 4000-bit denominator | 16000 | 11 | 103 |

Cost is dominated by `3^v` pattern enumeration per distinct term structure,
with `v` the active-vertex count, so it grows linearly in the number of
structurally distinct terms and as `3^n` in the dimension.

The exact merge is the one place where coefficient shape matters. Real
certificates carry few distinct denominators with a tiny least common multiple
(`certificate_10_4.json`: 50 distinct denominators, 29-bit lcm; the campaign's
n=11 candidate: 1362 distinct denominators, 713-bit lcm). An input with thousands of
pairwise-coprime multi-thousand-bit denominators forces the common denominator
to millions of bits and the merge dominates everything else; the report's
`distinct_coefficient_denominators` and `common_denominator_bits` fields say
when an input is in that regime. See
`artifacts/math/t2-referee/controls-v1/RESULT.md` for measurements.
