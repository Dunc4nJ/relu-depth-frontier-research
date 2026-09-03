# T2 referee review — n = 11 run7 certificate

**Bottom line: T2 PASS.** An independently built binary and a separately written
independent implementation both confirm, in exact rational arithmetic, that the
15,896-term certificate at
`artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json`
satisfies the pinned upstream verifier's identity for `n = 11`.

- **Reviewer lineage:** Claude (Opus 5, 1M context), fresh context, no shared
  state with the GPT-lineage authors of the artifacts under review.
- **Review date:** 2026-09-03.
- **Repository HEAD at review start:** `2c2b2aef009357ccd6978503bf9f708a81bd63f1`
  (other agents committed concurrently; HEAD moved during the review, but every
  file this review depends on was byte-identical to its committed version
  throughout — see §7).

**No-claim line.** This review certifies the finite algebraic identity encoded in
the pinned upstream certificate format, and nothing beyond the upstream
verifier's semantics. It does not by itself assert any lower bound, any claim
about depth-2 *necessity*, any statement about `n > 11`, or the correctness of
the exact-lift pipeline that produced the witness.

---

## 1. Semantics audit — what a PASS certifies

### 1.1 The pinned upstream verifier

Source: `literature/repos/max-relu-certificates/verify_certificate.py`,
SHA-256 `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`,
which matches that repository's `SOURCE_MANIFEST.sha256` exactly (checked).

A certificate is `{"n": int, "terms": [{"coefficient": str, "pair": [left, right]}]}`.
Each branch is a list of endpoint pairs `[a, b]` with `1 <= a <= b <= n`
(one-based; converted to zero-based internally). Loops `a == b`, repeated edges,
and edges common to both branches are all legal. The two branches must have
equal length.

**Atom.** For a term with branches `left` and `right`,

```
atom(x) = max( sum_{(a,b) in left}  max(x_a, x_b),
               sum_{(a,b) in right} max(x_a, x_b) )
```

**Symmetrization.** `symmetrized_pair` loops over `itertools.permutations(range(n))`,
i.e. all `n!` permutations, with **no** normalizing constant and no deduplication:

```
Sym_t(x) = sum_{sigma in S_n} atom_t(x_sigma(1), ..., x_sigma(n))
```

**Normal form.** Both sides being symmetric, the check is done on the sorted cone
`x_1 <= ... <= x_n`, where `sum_{(a,b) in side} max(x_a, x_b) = side_form . y`
with `side_form[rank]` counting the edges whose higher-ranked endpoint sits at
that rank. Writing `base = lexicographic min(left_form, right_form)`,
`other = lexicographic max`, and `direction = other - base`, we have
`atom = base . y + max(0, direction . y)`. The linear parts accumulate; a
direction is **dropped** when `direction . y <= 0` everywhere on the cone, which
(given `sum(direction) == 0`, guaranteed by equal branch lengths) holds exactly
when every proper prefix sum of `direction` is non-negative. Retained directions
are normalized by their positive gcd, and the gcd is folded into the coefficient.

**Target.** `total_linear[-1] -= 1`. A PASS requires every accumulated linear
coefficient and every accumulated hinge coefficient to be exactly zero. The
certified statement is therefore

```
sum_t coefficient_t * Sym_t(x)  ==  max(x_1, ..., x_n)      for all x in R^n
```

with target coefficient exactly `1`.

**Soundness direction.** Requiring each primitive direction's coefficient to
vanish individually is *sufficient* for the identity, not necessary: if all
hinge coefficients are zero the sum equals the linear part, and the linear part
is `y_n = max(x)` on the cone; symmetry of both sides extends it to all of `R^n`.
So a PASS cannot be a false positive from an incomplete cancellation rule. The
rule could in principle produce a false *negative*, which is the harmless
direction for a referee.

### 1.2 `tools/verify11` implements the same identity

Read in full: `tools/verify11/src/lib.rs` (1439 lines) and `src/main.rs` (526
lines). Findings:

| Upstream behaviour | `verify11` | Verdict |
| --- | --- | --- |
| endpoint validation `1 <= a <= b <= n` | `parsed_sides`, same bounds | same |
| equal branch lengths | `parsed_sides`, `ensure!` | same |
| `side_form[max(pos a, pos b)] += 1`, loops included | signed adjacency matrix + subset DP; `word[rank]` is the back-degree of `right - left` at that rank, loops contributing at their own rank | same |
| linear part `= sum over S_n of base` | `analytic_left_base` gives `sum over S_n of left_form` in closed form (`loops*(n-1)! + nonloops*2*rank*(n-2)!`), then `accumulate_oriented_word` adds `count*(right-left)` exactly on the states where `right <lex left` | same (verified algebraically and by differential test, §4) |
| lexicographic `base`/`other`, `direction = other - base` | orientation by sign of the first nonzero entry of `right - left` | same |
| drop cone-nonpositive directions | prefix-sum test on the normalized direction | same |
| positive gcd normalization, gcd folded into the coefficient | `divisor = gcd(|word|)`, contribution `count * divisor` | same |
| `total_linear[-1] -= 1` | `total.linear[n-1] += -common_denominator` after clearing denominators | same |
| exact rational arithmetic | exact LCM denominator clearing, then integer accumulation with an `i128` fast path and automatic `BigInt` promotion; no float, no modular prime | same |
| nonzero exit on failure | `verify` = `command_analyze(require_ok=true)` -> `bail!` -> `exit(1)` | same (exercised, §6) |

**Divergences found (all benign, none affecting this certificate):**

1. `dynamic_column` hard-errors if a `right - left` word is not zero-sum, where
   the Python would have kept it as a hinge. Unreachable: equal branch lengths
   force zero sum.
2. `literal_accumulate` skips a hinge whenever all proper prefix sums are
   non-negative without separately checking `sum == 0`, where the Python's
   `nonpositive_on_ordered_cone` returns `False` on a nonzero sum. Unreachable
   for the same reason.
3. `verify11` requires `n` to appear before `terms` in the JSON object (a
   streaming-parser constraint) and caps `n <= 16`; the Python has neither
   restriction. Not a semantic difference for a valid certificate.
4. `verify11` validates every term's branches during pass one even when the
   coefficient is zero; the Python skips a zero-coefficient term before
   validating its pair. Strictly stricter, so it cannot turn a FAIL into a PASS.
5. **Potential silent overflow, not triggered here.** `ExactInt::add_mul` has a
   branch `(Big target, Small coefficient)` computing `value * i128::from(factor)`
   in `i128` with no checked multiply. Release builds do not trap on overflow, so
   a coefficient with `|value|` above `i128::MAX / |factor|` would wrap silently.
   I checked reachability directly: after clearing to the common denominator,
   the smallest scaled coefficient in this certificate has 207 decimal digits, so
   **all 15,896 scaled coefficients are `BigInt`, never `Small`**, and this branch
   is never taken. It remains a latent hazard for a future certificate with mixed
   coefficient magnitudes and should be a checked multiply.

---

## 2. Translation audit — universe/witness to upstream format

The task asked for a 20-term spot check. I did better: I re-derived the **entire**
certificate independently.

**Full reconstruction (15,896 / 15,896 terms).** Working from the G-0027 universe
schema and the upstream atom definition, without importing
`tools/exactlift/universe_to_upstream.py`, I rebuilt the file
(`scripts/t2_reconstruct_translation.py`) and hashed the result:

```
independent reconstruction sha256: 8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5
pinned certificate        sha256: 8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5
```

Byte-for-byte identical. The translation is therefore not merely spot-checked; it
is reproduced.

**Translation rule, as read from the code and confirmed against the upstream atom
definition.** For witness entry with universe column `c`:

- record `c` supplies `negative_edges` (call it `A`) and `positive_edges` (`B`),
  each of length `signed_mass = m`;
- the carrier is `5 - m` copies of the single loopless edge `[0,1]` (one-based
  `[1,2]`), appended to **both** branches;
- `left = A + carrier`, `right = B + carrier`, converted to one-based.

The carrier cancels in `right - left`, so the signed graph seen by the verifier is
exactly `B - A`, which is the record's signed graph. The carrier does affect the
linear part, but only through the count of non-loop edges (see
`analytic_left_base`), so any loopless carrier of the same multiplicity gives the
same fully symmetrized atom — this is G-0027's `function_collapse` claim, and it
is consistent with the closed form in `verify11`.

Column `len(records) = 754017` is the synthetic **5L** column, translated as five
common self-loops `[1,1]` on both branches: the word is identically zero, so no
hinges, and the linear part is `5*(n-1)! = 18,144,000` in every coordinate, i.e.
the all-ones linear column. Record `0` is the **5E** carrier column (empty signed
graph, five copies of the common loopless edge), giving `5*2*rank*(n-2)!` and no
hinges.

**Neither special column is used by this certificate.** Witness columns run
`525143 .. 708196`, so column `0` and column `754017` are both absent. Moreover
**all 15,896 used columns have `signed_mass = 5`**, so the carrier padding is
`5 - 5 = 0` for every term: every branch is literally the record's five negative
or five positive edges. The carrier-invariance argument is therefore not
load-bearing for this certificate at all.

**Seeded 20-term spot check** (seed `20260903`, positions
`[2032, 2194, 2554, 3467, 3828, 4017, 4428, 5465, 5693, 7281, 7632, 7901, 8270,
8446, 10533, 11130, 11944, 12802, 12979, 14316]`; full table in
`translation_spotcheck_seed20260903.txt`). For each I checked, by my own reading
of the record and the upstream atom definition:

1. branch sizes are 5/5 and endpoints satisfy `1 <= a <= b <= 11`;
2. the carrier is identical on both branches, is loopless, and has the right
   multiplicity;
3. `left minus carrier == negative_edges` and `right minus carrier == positive_edges`
   as multisets;
4. `right - left == positive_edges - negative_edges` as a signed multiset;
5. `active_vertices` equals the number of distinct vertices in the record;
6. no record edge is a loop;
7. the term coefficient equals the witness coefficient, both as an exact string
   and as an exact `Fraction`.

**Result: 20 / 20 OK, 0 MISMATCH.** Active-vertex counts were 10 or 11, signed
mass 5 throughout, coefficient numerators 60 to 439 characters.

---

## 3. Independent execution of `verify11 verify`

**Build.** I exported `tools/verify11` from the committed tree with
`git archive HEAD tools/verify11` into a scratch directory and built it there
with a fresh target directory:

```
cd <scratch>/tools/verify11 && cargo build --release --locked
cargo test --release --locked      # 5 passed, 0 failed
```

- `rustc 1.95.0-nightly (5c49c4f7c 2026-01-20)`, `cargo 1.95.0-nightly`
- `tools/verify11` commit: `a9f386948d75b07acccbf83f365da71788e2e651`
- Committed sources, SHA-256:
  `src/lib.rs 5bc9a14f1df11fd027ff9f0e4bf3ac005e7f0d16364bd1f2c83cd1663a1667c5`,
  `src/main.rs 5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203`,
  `Cargo.toml 82cdb92f855686d46173472b863914dc8ef2529fc1a5f15f0479921784accdc8`,
  `Cargo.lock e5e66cc67a27970449c516b5193f23a74ac31afb839e5c2e275f78d4ae217288`.
  These matched the working tree exactly, so the in-tree source is unmodified.
- **Resulting binary SHA-256:
  `bab4ab22fa0acaa2c49c5c91bc6fa5fb006afd7ed843f6a008049bc65d4d1eb9`** — bit-identical
  to the pre-existing in-tree binary used by T1, i.e. the build is reproducible.

**Memory precheck.** Before starting: `free -g` showed 25 GB free / 26 GB
available; the only running `max11-verify11` (T1's `analyze`) had RSS about
264 MB. Far more than 16 GB would remain free, so no wait was needed.

**Run.**

```
/usr/bin/time -v <scratch>/target/release/max11-verify11 verify \
  --certificate artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json \
  --threads 4 \
  --output artifacts/math/t2-review/n11-run7/verify11_t2_report.json
```

| | |
| --- | --- |
| stderr verdict | `VERIFY11_OK terms=15896/15896 literal=0/0 seconds=2832.516966` |
| exit code | `0` |
| wall clock | `47:12.68` |
| user / system CPU | `6371.18 s` / `317.82 s` |
| max RSS | `448,028 kB` (438 MB) |

Report contents: `result OK`, `input_sha256` matching the expected certificate
hash, `n 11`, `terms_total 15896`, `terms_nonzero 15896`, `dp_columns_checked 15896`,
`linear_rows 11`, `bad_linear_rows 0`, `hinge_rows_union 169166`,
`bad_hinge_rows 0`, `emitted_hinge_entries 681,123,474`, common denominator 215
decimal digits, `repeated_coefficient_denominator false` (there are 1,362 distinct
coefficient denominators, so the dense single-denominator fast path was **not**
taken; the exact LCM path was).

**Wall-time caveat.** T1's run was executing concurrently on the same 16-core
host for the whole duration, and a lattice check and a Python recomputation ran
for part of it. Load average was 13 to 15 throughout. The wall time is therefore
an upper bound under contention, not a clean benchmark.

**Agreement with T1.** T1's report
(`artifacts/math/verify11/n11-run7/full_dp_report.json`, `analyze` mode, same
binary) agrees on every substantive field: `result`, `input_sha256`, `n`,
`terms_total`, `terms_nonzero`, `dp_columns_checked`,
`coefficient_common_denominator`, `linear_rows`, `bad_linear_rows`,
`hinge_rows_union` (169166), `bad_hinge_rows`, `emitted_hinge_entries`,
`first_bad_linear` (null), `first_bad_hinge` (null). This is a second execution
of the same binary, so it is a reproducibility check, not independent evidence.

---

## 4. Independent evidence not requested but performed

Running the campaign's own binary twice does not make the review independent. I
therefore added four checks that do not share evaluator code with `verify11`.

### 4.1 Differential test of the binary against the pinned Python reference

| certificate | pinned `verify_certificate.py` | my `verify11` build |
| --- | --- | --- |
| `certificate_5_2` (n=5) | `OK` | `VERIFY11_OK`, exit 0 |
| `certificate_6_2` (n=6) | `OK` | `VERIFY11_OK`, exit 0 |
| `certificate_7_3` (n=7) | `OK` | `VERIFY11_OK`, exit 0 |
| `certificate_8_3` (n=8) | `OK` | `VERIFY11_OK`, exit 0 |
| `certificate_9_4` (n=9) | not run (too slow in Python) | `VERIFY11_OK`, exit 0 |
| `certificate_10_4` (n=10) | not run (too slow in Python) | `VERIFY11_OK`, exit 0 |
| `certificate_5_2` coefficient-mutated | `Fail` | `VERIFY11_FAIL`, exit 1 |
| `certificate_7_3` coefficient-mutated | `Fail` | `VERIFY11_FAIL`, exit 1 |

### 4.2 An independent implementation, validated against the reference

I wrote my own subset DP (`scripts/t2_independent.py`, `scripts/t2_fastdp.py`)
from the upstream definition and checked it column-for-column — full linear
vector and full hinge map — against the pinned `symmetrized_pair`:

- every term of the upstream certificates at n = 5, 6, 7, 8 (133 columns);
- 120 random loopless five-edge signed pairs at n = 7 and n = 8 (the MAX11 term
  shape);
- 120 random pairs at n = 6 and n = 7 deliberately containing loops, repeated
  edges, and edges common to both branches.

**373 columns, 0 mismatches.**

### 4.3 Full independent recomputation of the n = 11 identity

Using that validated implementation, in exact integer arithmetic over the common
denominator, over all 15,896 terms (`scripts/t2_fullcheck.py`, 4 processes,
2,896 s):

```
verdict            : OK
bad_linear_rows    : 0
bad_hinge_rows     : 0
hinge_rows_union   : 169166      (identical to verify11's count)
```

This is the load-bearing independent result: a separately written implementation,
validated against the pinned reference, reproduces the identity and even the exact
size of the hinge row space.

Recorded at `independent_python_recheck.json`.

### 4.4 Method-disjoint lattice falsifier

`tools/t2-referee/lattice_check.py` evaluates both sides pointwise at lattice
points instead of using the cone/hinge normal form.

```
profiles checked: 90     lattice points: 179,195      ({0,1}^11 and {0,1,2}^11)
{0..1}^n PASS (0 failing profiles)   {0..2}^n PASS (0 failing profiles)
VERDICT: PASS
```

Run twice, because the tool was being edited concurrently by another agent:
version `4e812678c137ecdab34fbe0d75c02fa8aac52d9ca54980b72f460c71bf779b01`
(175.1 s, `lattice_check_t2_report.json`) and version
`e8175f87cc131ce032a185afa7a387ab532608cee606dd21afec15a5ee3ae89b`
(203.2 s, `lattice_check_t2_rerun_report.json`). Both PASS, exit 0.

**Caveat.** As that tool's own README states, agreement on finitely many lattice
points falsifies but does not prove a piecewise-linear identity. It is
corroboration, and its value here is that it is method-disjoint. It is also
**uncommitted** (`tools/t2-referee/` is untracked) and changed on disk during
this review.

---

## 5. Literal cross-check (DP versus permutation enumeration)

```
max11-verify11 sample  --certificate .../member_upstream.json --terms 20 --seed 20260903 \
                       --output artifacts/math/t2-review/n11-run7/sample20_seed20260903.json
max11-verify11 analyze --certificate .../sample20_seed20260903.json --threads 4 --literal-check \
                       --output artifacts/math/t2-review/n11-run7/sample20_literal_dp_report.json
```

Selected zero-based indices:
`[254, 1326, 1376, 2082, 2493, 3231, 3446, 5043, 5879, 6555, 6642, 6893, 8648,
9048, 10380, 10730, 10889, 11566, 12006, 15827]`.

```
VERIFY11_FAIL terms=20/20 literal=20/20 seconds=110.436542
permutations_per_literal_term: 39,916,800     (798,336,000 permutations total)
literal_dp_matches: 20 / 20
```

**Agreement: 20 / 20.** `compare_columns` compares the entire linear vector and
the entire hinge map, not a summary, so this is a full column-level agreement
between the DP and brute-force `S_11` enumeration. The `FAIL` verdict is expected
and correct: a 20-term subset of a 15,896-term certificate is not itself an
identity for `max`.

The sample file is byte-identical to T1's (`acce9323...`), as it must be for the
same seed.

**Independent confirmation of the sample residual.** My own implementation (§4.2)
recomputed the same 20-term residual and agreed with `verify11` on every reported
field, including two 200-plus-digit exact rationals:

| field | mine | verify11 |
| --- | --- | --- |
| `bad_linear_rows` | 9 | 9 |
| `hinge_rows_union` | 152,680 | 152,680 |
| `bad_hinge_rows` | 152,680 | 152,680 |
| `first_bad_linear` rank | 3 | 3 |
| `first_bad_linear` value | identical exact rational | identical |
| `first_bad_hinge` direction | `[0,0,0,0,0,0,0,0,1,-4,3]` | same |
| `first_bad_hinge` value | identical exact rational | identical |

---

## 6. Planted negative

A copy of the certificate was made **outside the repository** (scratchpad) with
`+1` added to the numerator of exactly one coefficient.

- mutated term: **index 7948** (zero-based)
- numerator `-30108481100675602727356588164488429` -> `-30108481100675602727356588164488428`
- denominator: unchanged, 34 decimal digits; the perturbation is exactly
  `+1/denominator`, about `3e-35`
- exactly one term differs from the original (verified by diff)
- mutant SHA-256 `d7287b244f6ac8cae097423207cededc7d8958dd9c10b4ef5476e14ceaa9ed4e`

```
VERIFY11_FAIL terms=15896/15896 seconds=2595.941542
VERIFY11_ERROR: certificate verification failed (report written)
Exit status: 1        wall 43:16.21        max RSS 447,716 kB
```

**Result: FAIL with nonzero exit, as required.** `bad_linear_rows 9`,
`bad_hinge_rows 24777`.

I went further and checked that the residual is not merely nonzero but *exactly
right*. Using my independent implementation I predicted the residual of the
perturbed certificate as `(1/denominator) * column_7948` and compared:

| | predicted | reported |
| --- | --- | --- |
| bad linear rows | 9 | 9 |
| first bad linear rank | 3 | 3 |
| first bad linear value | `1/4555675625349784717808294400` | identical |
| bad hinge rows | 24,777 | 24,777 |
| first bad hinge direction | `[0,0,0,0,0,0,0,0,1,-2,1]` | identical |
| first bad hinge value | `1/313099161160403386060279142400` | identical |

A perturbation of order `1e-35` in one of 15,896 coefficients is detected, and
the resulting residual matches an independent prediction exactly. This is
simultaneously a sensitivity control and a demonstration that the arithmetic is
genuinely exact.

The mutant copy was deleted after the run and was never added to the repository.

---

## 7. What was verified, and what was not

**Independently verified in this review:**

- the certificate file hash equals the expected `8bd2270a...`;
- the pinned upstream verifier source matches its own manifest hash;
- the identity certified by a PASS, stated precisely, and read off the upstream
  source rather than from any campaign narrative (§1.1);
- that `tools/verify11`'s `verify` mode implements that same identity, with every
  divergence enumerated and each shown unreachable or harmless (§1.2);
- that the `i128` overflow hazard in `ExactInt::add_mul` is unreachable for this
  certificate, by direct measurement of all 15,896 scaled coefficients;
- reproducibility of the `verify11` build from committed source (bit-identical
  binary);
- the universe-to-upstream translation, reproduced byte-for-byte for all 15,896
  terms by my own code, plus a 20-term semantic spot check (20/20 OK);
- the identity itself, twice: once by the campaign binary from my own build
  (`OK`, exit 0), and once by a separately written implementation validated
  against the pinned Python reference (`OK`, matching hinge row count);
- DP versus literal `S_11` enumeration on 20 terms (798 million permutations),
  20/20 full-column agreement;
- method-disjoint lattice corroboration on 179,195 points;
- negative controls: a planted `+1/denominator` perturbation on the real
  certificate, and coefficient mutations of two upstream certificates, all
  FAIL with exit 1, with residuals matching independent prediction.

**NOT verified in this review (be explicit):**

- **The exact rational lift was not re-run.** `member_exact_lift_report.json`
  claims PASS over 190,483 rows via CountSketch minor, modular LU and
  arbitrary-precision Dixon. None of that pipeline was re-executed. It does not
  matter for the bottom line: the lift is only a *search* procedure, and its
  output is fully re-checked downstream by the verifier. But no statement in this
  review supports the lift report's own numbers.
- One related discrepancy, noted for the record: the lift report claims
  `union_hinge_rows = 169,250`, while both `verify11` and my independent
  implementation find the certificate emits `169,166` distinct hinge directions.
  The 84-row difference is unexplained by me. It is in the harmless direction
  (the lift verified rows the certificate does not need) but nobody should quote
  169,250 as the certificate's row count.
- **The G-0027 universe was not audited.** Its records were read as data. I did
  not check that the universe is a correct or complete enumeration of loopless
  signed degree-five orbits, nor its `function_collapse` claim in general. For
  this certificate that claim is not load-bearing anyway, because every used
  column has signed mass 5 and no carrier padding is applied.
- **The upstream verifier's semantics were taken as the definition.** I checked
  that the certificate satisfies the pinned verifier's identity. I did not
  independently re-derive that this identity is the right formalization of the
  MAX11 question from the literature, beyond the reasoning in §1.1.
- **Depth-2 realizability is a separate step.** The identity
  `sum_t c_t Sym_t(x) = max(x)` means max of 11 reals is a finite rational
  combination of atoms of the form `max(A(x), B(x))` where `A` and `B` are sums of
  `max(x_a, x_b)`. Turning that into "a ReLU network with two hidden layers" is
  the standard reduction (`max(u,v) = (u+v)/2 + (relu(u-v)+relu(v-u))/2`, inner
  maxes in layer one, outer maxes in layer two, linear output, width growing with
  the term count). That reduction is textbook, but it is **not** what the verifier
  checks, and this review did not formalize it.
- **n = 9 and n = 10 upstream certificates were not cross-checked in Python**
  (only n = 5 through 8), because permutation enumeration at those sizes is too
  slow in the reference implementation.
- **The lattice tool is uncommitted and was changing during the review.** Its two
  PASS results are recorded against specific file hashes, but that tool has not
  itself been audited by me beyond reading its README and its core counting and
  accumulation routines.
- **Wall times are contended** and should not be used as benchmarks (§3).

---

## 8. Artifact inventory

**Inputs (SHA-256):**

```
8bd2270a801f6af679ccbf00aa7357f4e89ebb069d1211671082f3f5f07d25c5  member_upstream.json           (expected, MATCHES)
14ff53ee831a6bc2f5f2aa3a45420376f6676e30f1ca1f90253d26a6f386a238  member_exact_witness.json
76e8661c95b063cea1c47ceee0bc1febb674996a86baf9cbc95b8f6afa106ff0  member_exact_lift_report.json
506ae353e650d99fc7d73925d62b4ba96a2a40f3704c140234e3d86c53beb665  upstream_translation_report.json
8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8  G-0027/loopless_signed_degree5_universe_v1.json.gz
37d25a2ef2eac3c5054b02cfdd690e285dd6508b4c1a83dcdcfe4553e45a7b49  tools/exactlift/universe_to_upstream.py
d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7  literature/repos/max-relu-certificates/verify_certificate.py
5bc9a14f1df11fd027ff9f0e4bf3ac005e7f0d16364bd1f2c83cd1663a1667c5  tools/verify11/src/lib.rs
5d0299374c39288c21393f964a40ef42f26b408dd784cf270eec5b7ae627c203  tools/verify11/src/main.rs
82cdb92f855686d46173472b863914dc8ef2529fc1a5f15f0479921784accdc8  tools/verify11/Cargo.toml
e5e66cc67a27970449c516b5193f23a74ac31afb839e5c2e275f78d4ae217288  tools/verify11/Cargo.lock
bab4ab22fa0acaa2c49c5c91bc6fa5fb006afd7ed843f6a008049bc65d4d1eb9  max11-verify11 binary (my clean build)
4e812678c137ecdab34fbe0d75c02fa8aac52d9ca54980b72f460c71bf779b01  tools/t2-referee/lattice_check.py (first run)
e8175f87cc131ce032a185afa7a387ab532608cee606dd21afec15a5ee3ae89b  tools/t2-referee/lattice_check.py (re-run)
```

**Provenance:** certificate committed in `e7e596da0be415995261ad4d1d21d1e137421130`;
`tools/verify11` last changed in `a9f386948d75b07acccbf83f365da71788e2e651`.

**Environment:** Linux, 16 cores, 62 GB RAM; `rustc 1.95.0-nightly (5c49c4f7c 2026-01-20)`;
CPython 3.13.7 with numpy 2.5.2 from the project venv.

**Outputs produced by this review** (all under
`artifacts/math/t2-review/n11-run7/`): `verify11_t2_report.json`,
`verify11_t2_time.log`, `verify11_t2_stdout.log` (empty by design; the tool logs
to stderr), `sample20_seed20260903.json`, `sample20_literal_dp_report.json`,
`translation_spotcheck_seed20260903.txt`, `lattice_check_t2_report.json`,
`lattice_check_t2_rerun_report.json`, `independent_python_recheck.json`,
`scripts/` (four reproduction scripts), and this file. Output hashes are recorded
in `OUTPUT_SHA256.txt`.

---

## 9. Bottom line

**T2 PASS** — the certificate satisfies the pinned upstream verifier's exact
identity for `n = 11`, confirmed by an independently built binary (`OK`, exit 0)
and by a separately written independent implementation validated against the
pinned Python reference (`OK`, matching row counts), with a method-disjoint
lattice check agreeing and a planted `1e-35` coefficient perturbation correctly
rejected with a residual matching independent prediction.
