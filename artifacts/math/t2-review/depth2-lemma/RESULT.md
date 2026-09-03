# T2 referee review — depth-2 realization lemma

**Bottom line: T2 PASS WITH EDITS.** The proof is correct and the statement is
exactly the bridge that claim C-0002 needs. One sentence in the note is false as
written (the claimed weight set `{0, ±1, ±1/2}`); it is a decorative aside that
neither the lemma statement nor the rationality claim depends on, but it is
wrong for 15,894 of the 15,896 terms of the n = 11 certificate and must be
corrected. A second, minor edit is needed: the symmetry of the left-hand side is
asserted without its one-line justification. The two required edits are spelled
out verbatim in §5.

- **Reviewer lineage:** Claude (Opus 5, 1M context), fresh context, no shared
  state with the author of the note under review.
- **Review date:** 2026-09-03.
- **Object under review:** `artifacts/math/n11-ledger-recording/DEPTH2_REALIZATION_LEMMA.md`
  - commit `bbdb991e3af2505c08296b1f526d71b69334ef23`
  - SHA-256 `08e1889b130ce35c7c95d3ac54b208d4add9eed9c646ea1a0b9b8f3235f6312e`
  - The working-tree copy is byte-identical to the committed blob (checked; repo
    HEAD had moved to `36b27abcf85c1ec5454ce25269bc56c2b0e21b69` by review time,
    with no change to this file).
- **Upstream semantics taken from:** `artifacts/math/t2-review/n11-run7/RESULT.md` §1.1.
- **Certificate consulted:** `artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_upstream.json`
  (15,896 terms, all coefficients nonzero, every branch of length 5, **no loop
  edges at all**).
- **Literature cross-check:** `literature/papers/2607.21651.pdf`
  (SHA-256 `0a4def828040e0c17cf02e654b3ea76e85d17da14c207589ed0fee8a1c8ecd56`),
  Rueß, Averkov, Brunck, Grillo, Hertrich, Loho, Stade, Stargalla, Sun, Winter,
  *Shallower ReLU Network Representations via Exact Linear Algebra*. Present in
  the repo; read §1 (network convention), §3 (symmetrization), §4.1 (the ansatz)
  and §4.3 (Theorem 1.1 and the "Width of the construction" paragraph).

**No-claim line.** This review adjudicates one implication: certified identity ⇒
two-hidden-layer network. It does not re-verify the n = 11 certificate (that is
the run7 review's job and is taken as given), and it asserts nothing about
minimality of depth or width, about n ≥ 12, or about any lower bound.

---

## 1. Checked steps

Numbering follows the note. Line numbers refer to the reviewed file.

1. **(F1), line 21 — `max(u,v) = (u+v)/2 + (ReLU(u-v) + ReLU(v-u))/2`. OK.**
   `ReLU(w) + ReLU(-w) = |w|` for every real `w` including `w = 0`, and
   `max(u,v) = (u+v)/2 + |u-v|/2` is an identity on all of `R^2`. No case split,
   no boundary exception.

2. **(F2), line 23 — `w = ReLU(w) - ReLU(-w)`, and the "no skip connections"
   conclusion. OK.** True for every real `w`, including `w = 0` and `w < 0`, which
   is the case the note needs: the linear part `(x_a + x_b)/2` and the sum
   `L_A + L_B` both take negative values, so they cannot be routed through a
   single ReLU. The two-unit pass-through is the correct fix. Applied to an
   affine function `w + b` the same identity gives `ReLU(w+b) - ReLU(-(w+b))`, so
   biased pre-activations are handled too. Because every layer-2 pre-activation
   is a linear form in layer-1 outputs and the output is a linear form in
   layer-2 outputs, the resulting graph is strictly layered: no edge skips a
   layer. **The claim is proved, not merely asserted.**

3. **Layer-1 unit list and width, line 25. OK.** `ReLU(x_i - x_j)` and
   `ReLU(x_j - x_i)` for each unordered pair `{i,j}` with `i ≠ j` is
   `2·C(n,2) = n(n-1)` units, exactly as stated (the parenthetical correctly
   deduplicates `(i,j)` against `(j,i)`), plus `2n` units `ReLU(±x_k)`. Total
   `n(n-1) + 2n = n(n+1)`, matching line 47. All pre-activations linear in `x`.

4. **Loop handling, line 25 and line 29. OK.** For `(k,k) ∈ E` the summand is
   `max(x_k, x_k) = x_k`, realized as `ReLU(x_{σ(k)}) - ReLU(-x_{σ(k)})` using
   layer-1 units that already exist for the linear part. No extra unit is needed
   and the claim that none is needed is correct. Note the atom's pairs are
   unordered with `a ≤ b`, so `a = b` is the only loop form. (The n = 11
   certificate contains no loops, so this branch of the argument is exercised
   only in generality, not by the consumer.)

5. **Repeated edges, line 29. OK.** `E` is a multiset and the sum in line 29 runs
   over `E` with multiplicity, so an edge of multiplicity `m` contributes `m/2`
   to each of the two difference units and `m/2` to each endpoint's
   pass-through pair. This is still a linear form in the layer-1 outputs, which
   is all the proof requires. The n = 11 certificate does contain repeated edges
   (maximum multiplicity 2 within a branch), and they are handled correctly.

6. **`L_{E,σ}` is a bias-free linear form in the layer-1 outputs, line 31. OK.**
   For a non-loop `(i,j) ∈ E`, `σ(i) ≠ σ(j)` because `σ` is a bijection, so the
   required difference units exist in layer 1. Every contribution is linear with
   no constant term, so `L_{E,σ}` has zero bias as claimed. The identity
   `L_{E,σ}(h_1(x)) = f_E(σx)` holds pointwise for all `x ∈ R^n`.

7. **Permutation convention matches the verifier. OK.** The note sets
   `(σx)_i = x_{σ(i)}`, so `Φ_{A,B}(σx)` equals the verifier's
   `atom(x_{σ(1)}, …, x_{σ(n)})` term for term. Both the note and the upstream
   verifier sum over all `n!` permutations with **no** normalizing constant and
   no deduplication (run7 RESULT.md §1.1; paper §4.1, which explicitly drops the
   `1/n!`). The hypothesis of the lemma is therefore literally the certified
   identity, not a rescaled cousin of it.

8. **Layer-2 unit list and width, lines 33–37. OK.** Four units per `(t, σ)`:
   `ReLU(L_A - L_B)`, `ReLU(L_B - L_A)`, `ReLU(L_A + L_B)`, `ReLU(-(L_A + L_B))`.
   All pre-activations are linear forms in layer-1 outputs, so layer 2 is fed
   only by layer 1. Width `4·|T|·n!` is the honest count of the units the
   construction actually instantiates (some are redundant; no minimality is
   claimed, and the note says so).

9. **The layer-2 identity, line 41. OK.**
   `(1/2)[ReLU(S) - ReLU(-S)] + (1/2)[ReLU(D) + ReLU(-D)]` with `S = L_A + L_B`
   and `D = L_A - L_B` equals `S/2 + |D|/2 = max(L_A, L_B)` by (F2) and (F1),
   and `L_A, L_B` evaluate to `f_{A_t}(σx), f_{B_t}(σx)`. So the expression
   equals `Φ_{A_t,B_t}(σx)` for every `x`. Correct.

10. **Output layer, line 45. OK.** The output is the linear combination
    `Σ_t c_t Σ_σ Φ_{A_t,B_t}(σx)` of layer-2 outputs with zero bias, which by
    hypothesis equals `max(x_1,…,x_n)` on all of `R^n`. The output reads only
    layer 2. Depth is exactly two hidden layers under the convention of the
    upstream paper §1 (`f = T^{(D+1)} ∘ ReLU ∘ … ∘ ReLU ∘ T^{(1)}`), which is the
    convention the ledger claim should be read in.

11. **End-to-end executable check of the whole construction. OK.** I did not
    take the algebra on faith. I implemented the note's network verbatim —
    layer-1 unit list from line 25, `L_{E,σ}` from line 29, the four layer-2
    units from lines 33–37, the output from line 45 — in exact rational
    arithmetic, and ran it on the n = 6 certificate printed in the upstream
    paper §4.3 (coefficients `1/720, 1/360, -1/1440, -1/360`). Layer widths came
    out at 42 = `n(n-1) + 2n` and 11,520 = `4·|T|·n!` as the note predicts, and
    the network returned exactly `max(x)` on 30 out of 30 test points, including
    all-equal coordinates, all-negative coordinates, the origin, and points with
    ties. **The construction does what the note says it does.**

12. **Rationality claim, line 13 and line 47. OK as a claim, ISSUE in its
    justification.** All layer-1 weights are `±1`, all layer-2 weights are
    half-integers, all output weights are `±c_t/2`, and every bias is zero, so
    rational `c_t` do give an entirely rational network. The *conclusion* is
    correct. The *supporting sentence* is false — see §2.

13. **Bridging sentence, line 15 — the certified identity holds on all of
    `R^n`. OK, with a one-line gap.** The argument is sound: each `Sym_t` is a
    symmetric function, `max` is symmetric, every point of `R^n` is carried into
    the sorted cone by a coordinate permutation, and two symmetric functions
    agreeing on the cone agree everywhere. This is precisely the upstream
    paper's Proposition 3.1 ("every point of `R^n` is carried into `C` by a
    coordinate permutation") and it is echoed in run7 RESULT.md §1.1 under
    "Soundness direction". The gap is that the note *asserts* "both sides are
    symmetric functions" and never justifies the left-hand side, which is the
    only non-obvious half and which fails if the symmetrization ever ran over a
    proper subgroup or a deduplicated orbit. See required edit E2.

14. **"Checked on the sorted cone in a normal form", line 15. OK.** Strictly the
    verifier checks that every accumulated linear and hinge coefficient in a
    normal form vanishes, which is *sufficient* but not *necessary* for the cone
    identity. The note's looser phrasing errs in the sound direction: a PASS
    still implies the identity, which is the only direction the lemma consumes.
    No edit required.

15. **Scope discipline of the Remarks, lines 51–53. OK.** Minimality of width is
    explicitly disclaimed; `n ≥ 12` and lower bounds are explicitly disclaimed;
    the `|T| = 15,896` figure matches the certificate exactly. Depth minimality
    is not claimed anywhere, which is correct — one-hidden-layer impossibility
    for `n ≥ 3` is a separate result (upstream Remark 4.4, citing [11, Prop. 2.2])
    and the note rightly does not lean on it.

## 2. ISSUE — the weight-set claim is false

Line 47 states:

> all weights in {0, +-1, +-1/2} except the output weights c_t/2 and -c_t/2

This is wrong, and not marginally so.

The layer-2 pre-activations are linear forms in the layer-1 outputs whose
coefficients are *accumulated* over the edges of a multiset. An edge of
multiplicity `m` puts `m/2` on a difference unit, and a vertex of degree `d`
puts `d/2` on its pass-through pair. Half-integers of unbounded size therefore
appear as soon as a branch has a vertex of degree 3 or more.

**Concrete counterexample inside the n = 11 certificate.** Term index 6763 has

```
A = [[1,6],[1,7],[1,8],[1,9],[1,10]]
B = [[1,2],[1,3],[1,2],[1,4],[1,5]]
```

Vertex 1 has degree 5 in each branch, so the coefficient of the layer-1 unit
`ReLU(-x_{σ(1)})` in the pass-through pre-activation `L_A + L_B` is
`-(5/2 + 5/2) = -5`, which is not in `{0, ±1, ±1/2}`.

**This is the rule, not the exception.** Sweeping all 15,896 terms:

| quantity | value |
| --- | --- |
| terms with a layer-2 weight outside `{0, ±1, ±1/2}` | 15,894 of 15,896 |
| largest layer-2 weight magnitude | 5 |

It is not even an artifact of n = 11: the upstream paper's own four-term n = 6
certificate already produces layer-2 weights of `±3/2` under this construction.

**Severity: cosmetic but must be fixed.** Nothing in the lemma statement, the
depth claim, the no-skip claim, or the rationality claim depends on the weight
set — half-integers are rational, so line 13 survives untouched. But the note is
a ledger artifact whose sentences are meant to be citable, and this one is false
on 99.99% of the certificate it was written for.

## 3. Cross-check against the upstream paper's own realization

The paper performs the same conversion and states it explicitly (§4.3, "Width of
the construction"): *"The construction can also be converted directly into a
standard ReLU network without skip connections. This yields first-layer width at
most `C(n,2) + 2n` and second-layer width at most `3Q ≤ 3sn!`."* The note's
remark that its reduction "is the standard one used by the upstream authors" is
therefore **accurate**, and the paper's network convention (§1) matches the
note's "two hidden layers, affine output, no skips" exactly.

The note's widths are larger than the paper's by a factor 2 in layer 1 and 4/3
in layer 2, for a reason a reader should not have to reconstruct: the note uses
the symmetric identity `max(u,v) = (u+v)/2 + (ReLU(u-v) + ReLU(v-u))/2`, costing
two hinge units per maximum, whereas the paper's counts correspond to the
one-sided `max(u,v) = v + ReLU(u-v)`, costing one hinge unit plus a
pass-through. Neither is wrong; the note's counts are correct for the note's own
construction, and no minimality is claimed. This is an optional clarification,
not a required edit.

## 4. Sufficiency for claim C-0002

Asked directly: is this statement exactly what is needed to get from the
verifier's PASS to "MAX_11 is computed by a two-hidden-layer ReLU network with
real weights"? **Yes.**

- The hypothesis is the verifier's certified identity verbatim, including the
  unnormalized full-group symmetrization, the unordered pairs with loops and
  repeats permitted, and the target coefficient 1 (run7 RESULT.md §1.1).
- The lemma is strictly more general than needed in one harmless direction: it
  does not require `|A_t| = |B_t|`, which the verifier does require.
- The conclusion is stated in the upstream paper's own network convention.
- The `for all x ∈ R^n` hypothesis is discharged from the cone-only check by the
  symmetry argument, which is correct.

No further step is hidden between the two. Nothing in the note is claimed
without proof except the two items in §5.

## 5. Required edits

**E1 (required).** Replace the clause on line 47

> all weights in {0, +-1, +-1/2} except the output weights c_t/2 and -c_t/2

with a correct statement, for example:

> all layer-1 weights in {0, +-1}; every layer-2 weight is a half-integer (each
> is a sum of edge multiplicities and vertex degrees of A_t and B_t, divided by
> 2), bounded in absolute value by |A_t| + |B_t|; the output weights are
> +-c_t/2; all biases are zero.

If a concrete figure is wanted, add: for the n = 11 certificate the largest
layer-2 weight magnitude is 5.

**E2 (required).** On line 15, after "both sides are symmetric functions", insert
the justification for the left-hand side, for example:

> (each symmetrized atom is symmetric because the sum runs over the full group:
> substituting pi x and using sigma(pi x) = (pi sigma) x reindexes the sum by
> the bijection sigma -> pi sigma of S_n, and the upstream verifier likewise
> sums over all n! permutations with no deduplication and no normalizing
> constant)

**E3 (optional).** In the Remarks, record that the note's widths exceed the
upstream paper's stated conversion widths (`C(n,2) + 2n` and `3sn!`, §4.3)
because the note uses the two-unit symmetric hinge identity rather than the
one-sided `max(u,v) = v + ReLU(u-v)`.

**E4 (optional).** Record that the n = 11 certificate contains no loop edges and
has all branches of length 5, so the loop case of the lemma is present for
generality and is not exercised by the consumer.

## 6. Bottom line

**T2 PASS WITH EDITS**, the edits being E1 and E2 of §5.

The proof is correct at every step, the construction was executed in exact
arithmetic against the upstream paper's own published n = 6 certificate and
reproduced `max` exactly on 30 of 30 points, and the statement is precisely the
bridge from the certified identity to "MAX_11 is in ReLU_2". After E1 and E2 the
note is fit to be recorded as PROVED_HERE for that step. E1 is not optional: as
written, the note contains a false sentence about 15,894 of the 15,896 terms of
the certificate it exists to support.

---

## 7. Revision 2 re-review (2026-09-03)

**Bottom line for revision 2: T2 PASS WITH EDITS — one clause remains false.**
Both required edits are applied and their mathematical content is correct. The
replacement weight sentence, however, introduced one new false clause of exactly
the class it was written to remove: it accumulates coefficients correctly over
vertices but not over edges. Nothing load-bearing depends on it. After the
one-line fix E1b below, the note is fit to be recorded as PROVED_HERE.

- **Object:** `artifacts/math/n11-ledger-recording/DEPTH2_REALIZATION_LEMMA.md`
  - commit `fcc53e7`, SHA-256 `ab1145cfb52f7e0ba3346cd78ea4f69ab3e4086a22f194cdd5732dd2f04dceed`
  - Working-tree copy byte-identical to the committed blob (checked).
- **Diff reviewed:** `git diff bbdb991 fcc53e7` on that path — three hunks, no
  change to the Lemma statement itself, nothing else touched.

### 7.1 E2 (symmetry of the left-hand side) — **RESOLVED, correct.**

The inserted argument reads: with `(σx)_i = x_{σ(i)}`, for `τ ∈ S_n` we get
`(σ(τx))_i = (τx)_{σ(i)} = x_{τ(σ(i))}`, hence `σ(τx) = (τ∘σ)x`, and `τ∘σ` runs
over `S_n` as `σ` does.

Checked directly: `((τ∘σ)x)_i = x_{(τ∘σ)(i)} = x_{τ(σ(i))}`, which is the same
expression, so the composition identity is right, and left translation by `τ` is
a bijection of `S_n`. The conclusion `Sym_t(τx) = Sym_t(x)` follows. This is
exactly the argument requested in E2 and it is stated in the note's own
convention. It also correctly closes the only gap that mattered: the step fails
for a proper subgroup or a deduplicated orbit, and the note now shows the sum is
over the full group.

### 7.2 E1 (weight claim) — **substantially resolved; one clause still false.**

Correct in the new sentence, each item checked:

| new claim | verdict |
| --- | --- |
| layer-1 weights in `{0, ±1}` | OK |
| layer-2 weights are half-integers | OK |
| coefficient of `ReLU(x_k)` in `L_{E,σ}` is `deg_E(σ^{-1}(k))/2` | OK |
| a loop counts 2 toward the degree | OK — a loop at `v` contributes coefficient `1 = 2/2`, matching the note's own line 25 treatment |
| every layer-2 weight has magnitude at most `|A_t| + |B_t|` | OK |
| equality only when one vertex carries every edge of both branches as loops | OK — needs `deg_A(v) = 2|A_t|` and `deg_B(v) = 2|B_t|` simultaneously |
| n = 11 certificate has no loops, five edges per branch, largest magnitude 5 | OK — reconfirmed on all 15,896 terms; the maximum 5 is attained at term index 6763 on a pass-through unit |
| output weights `±c_t/2` | OK |

**ISSUE (new, introduced by the fix).** The clause

> and the coefficient of each difference unit is +-1/2

is false whenever an edge repeats. The coefficient of the layer-1 unit
`ReLU(x_a - x_b)` in `L_{E,σ}` is `m/2`, where `m` is the multiplicity of
`{σ^{-1}(a), σ^{-1}(b)}` in the multiset `E`. The sentence accumulates over
vertices (the degree rule, correctly) but silently declines to accumulate over
edges, which is the same slip as the original `{0, ±1, ±1/2}` claim.

Counterexample from term index 0 of the certificate under review:

```
B = [[1,2], [1,2], [3,4], [1,3], [2,5]]
```

The edge `{1,2}` has multiplicity 2, so the coefficient of
`ReLU(x_{σ(1)} - x_{σ(2)})` in `L_{B,σ}` is `1`, not `±1/2`.

| quantity | value |
| --- | --- |
| terms with a difference-unit coefficient in some `L_E` outside `{0, ±1/2}` | 14,361 of 15,896 |
| largest difference-unit coefficient magnitude, in `L_E` and in `L_A ± L_B` | 1 |

**Severity: cosmetic, no propagation.** Difference-unit coefficients are `m/2`
with `m ≤ |E|`, so they are half-integers bounded by `|E|/2`, and the sentence's
own bound `|A_t| + |B_t|` and its "largest magnitude 5" figure both survive
unchanged (the maximum 5 comes from a pass-through unit, and difference units
top out at 1 on this certificate). The half-integer claim, the rationality
claim, the depth claim and the no-skip claim are all unaffected.

**Secondary omission, same sentence.** The rule is given for `ReLU(x_k)` but not
for `ReLU(-x_k)`, whose coefficient is `-deg_E(σ^{-1}(k))/2`. The magnitude
bound covers it, so this is incompleteness rather than error; folding it into
E1b costs nothing.

### 7.3 Optional edits E3 and E4 — applied, with one nit

**E4 (no loops) — OK.** Reconfirmed: zero loop edges across all 15,896 terms of
`member_upstream.json`, and every branch has exactly 5 edges. One scoping nit:
the note says "the n = 11 certificates" in the plural; I verified only the run7
certificate under review here.

**E3 (width comparison) — correct in substance, loose in one figure.** The
one-sided identity `max(u,v) = u + ReLU(v - u)` is correct and is indeed what
the upstream paper's counts (`C(n,2) + 2n` and `3Q`, §4.3) correspond to. The
layer-2 factor `4/3` is exact. The layer-1 factor is not exactly 2: the note's
`n(n-1) + 2n` over the paper's `C(n,2) + 2n` is `2(n+1)/(n+3)`, i.e. `132/77`
(about 1.71) at `n = 11`, approaching 2 only as `n` grows. My own §3 used the
same loose phrasing, so this is a shared nit, not a regression. It sits in a
remark explicitly flagged "not part of the claim" and needs no fix; if the
author wants precision, say "by a factor 2 on the pairwise-difference block and
4/3 in layer 2".

**Revision provenance line — OK.** It cites this review at the correct path and
commit `53da770` and describes the two changes accurately.

### 7.4 Remaining edit

**E1b (required).** In the weight sentence, replace

> and the coefficient of each difference unit is +-1/2

with

> the coefficient of ReLU(-x_k) is -deg_E(sigma^{-1}(k))/2, and the coefficient
> of the difference unit ReLU(x_a - x_b) is m/2, where m is the multiplicity of
> {sigma^{-1}(a), sigma^{-1}(b)} in E (at most |E|/2; on the n = 11 certificate
> the largest such coefficient is 1, from a doubled edge)

Everything else in revision 2 stands as written.

### 7.5 Final bottom line

**T2 PASS WITH EDITS**, the edit being E1b of §7.4 and nothing else.

The lemma, its proof, and every claim the ledger consumes are correct as of
revision 2: the construction is valid, the depth, no-skip, width, half-integer
and rationality claims all hold, the hypothesis is the certified identity
verbatim, and the extension from the sorted cone to `R^n` is now fully argued.
The single remaining defect is one descriptive clause about a per-unit
coefficient, false on 14,361 of 15,896 terms, carrying no mathematical weight.
Fix E1b and this step is ready to be recorded as PROVED_HERE; no further review
round is needed on my account, since E1b is a substitution I have already
checked against the certificate.

## 8. Revision 2b confirmation (2026-09-03)

Revision 2b (commit `a1a70ba`, SHA-256 `dedd94b2e85cd282e6da6eed64200ae354a4cbf290c1d92dd2979d97609b6007`, working tree byte-identical) applies E1b: the difference-unit coefficient now reads `mult_E(sigma^{-1}{a,b})/2`, which I confirm is the correct rule, and the added figure "a doubled edge gives a difference-unit coefficient of 1" matches my measurement over all 15,896 terms; the run7 scoping, the "roughly 2 / exactly 4/3" width wording, and the loopless-universe attribution are all now accurate, and the diff `fcc53e7..a1a70ba` touches nothing else.

**Final bottom line: T2 PASS.** Every claim in the note is correct and the lemma is exactly the bridge from the certified identity to "MAX_11 is in ReLU_2"; the one surviving nit is that the coefficient of `ReLU(-x_k)`, namely `-deg_E(sigma^{-1}(k))/2`, is left implicit rather than stated, which the magnitude bound already covers and which blocks nothing. Fit to record as PROVED_HERE.
