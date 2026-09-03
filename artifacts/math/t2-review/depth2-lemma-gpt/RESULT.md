# GPT-lineage T2 referee report: depth-2 realization lemma

Reviewer: `IndigoCarp`  
Model family: `openai-gpt`  
Review date: 2026-09-03  
Bead/thread: `relu-depth-frontier-research-330`

## Bottom line

**T2 PASS.** Revision 2b proves the stated realization lemma. I found no open load-bearing gap in the transport from the verifier-certified symmetrized atom identity to a finite feed-forward ReLU network with exactly two hidden layers, affine output, and no skip connections. The rational-parameter conclusion also follows.

This verdict was written before reading `artifacts/math/t2-review/depth2-lemma/`; that same-lineage Opus review was kept sealed during the proof audit and exact control below.

## Object and independence binding

- Reviewed file: `artifacts/math/n11-ledger-recording/DEPTH2_REALIZATION_LEMMA.md`.
- Reviewed revision: 2b.
- Author: AmberBluff, Claude lineage.
- Reviewed commit: `a1a70ba9412922b34b8bccb3eeeebab68b31b85e`.
- Reviewed-file SHA-256 in the working tree: `dedd94b2e85cd282e6da6eed64200ae354a4cbf290c1d92dd2979d97609b6007`.
- SHA-256 of the same path extracted with `git show a1a70ba:...`: `dedd94b2e85cd282e6da6eed64200ae354a4cbf290c1d92dd2979d97609b6007`.
- Pinned upstream verifier: `literature/repos/max-relu-certificates/verify_certificate.py`, SHA-256 `d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7`; its manifest contains the same hash.
- Pinned n=6 certificate: `literature/repos/max-relu-certificates/certificates/certificate_6_2.json`, SHA-256 `026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83`; its manifest contains the same hash.
- Independence: the author is Claude lineage and this referee is OpenAI GPT lineage. I did not read the Opus depth-2 review before reaching and writing the verdict.

## Numbered adversarial checks

1. **OK — statement and quantifiers.** The lemma fixes every integer `n >= 2`, finite edge multisets allowing loops and repeats, a finite list `T`, real coefficients, and an identity holding for every `x in R^n`. The conclusion is existence of one finite network for that fixed data. No quantifier is exchanged: network parameters may depend on `n` and `T`, but not on `x`.

2. **OK — first ReLU identity (F1).** For arbitrary real `u,v`, including `u=v` and either or both negative,
   `ReLU(u-v)+ReLU(v-u)=|u-v|`, hence
   `(u+v)/2 + [ReLU(u-v)+ReLU(v-u)]/2 = (u+v+|u-v|)/2 = max(u,v)`.
   No sign restriction is used.

3. **OK — signed pass-through identity (F2).** `ReLU(w)-ReLU(-w)=w` for every real `w`. In particular, `L_A+L_B` may be negative: the two second-layer units with preactivations `L_A+L_B` and `-(L_A+L_B)` pass it to the affine output exactly. This is the load-bearing device that removes a layer-1-to-output skip.

4. **OK — layer-1 realization, including loops.** For each unordered pair `{a,b}`, `a != b`, the construction has the two oriented units `ReLU(x_a-x_b)` and `ReLU(x_b-x_a)`. For each coordinate it has `ReLU(x_k)` and `ReLU(-x_k)`. Applying F1 reconstructs each nonloop `max(x_a,x_b)`. A loop contributes `(x_k+x_k)/2=x_k`; its two formal difference terms are `ReLU(0)=0`, so no loop-specific unit is needed. The coordinate split supplies `x_k` even when it is negative.

5. **OK — multisets, repeats, and shared edges.** The layer-1 units are shared features, not one unit per edge occurrence. Repeating an edge adds another `1/2` to each relevant feature coefficient, so a nonloop edge of multiplicity `m` has difference-feature coefficient `m/2`. A loop of multiplicity `m` contributes degree `2m`, hence coordinate-feature coefficient `m`. An edge appearing in both `A` and `B` is included in both `L_A` and `L_B`; it cancels in `L_A-L_B` and doubles in `L_A+L_B`, exactly as the two branch sums require.

6. **OK — first-layer width.** There are two oriented difference units for each of `n(n-1)/2` unordered distinct pairs, giving `n(n-1)` units, plus `2n` signed-coordinate units. Width 1 is therefore exactly `n(n-1)+2n`. The wording “for every ordered pair ... the same pair of units” is slightly compressed, but the sharing parenthesis and stated count make the intended construction unambiguous.

7. **OK — layer-2 atom realization.** For each `(t,sigma)`, the four preactivations are `L_A-L_B`, `L_B-L_A`, `L_A+L_B`, and `-(L_A+L_B)`. Their ReLUs enter the output with respective weights `c_t/2, c_t/2, c_t/2, -c_t/2`. The latter pair equals `c_t(L_A+L_B)/2`; the former pair equals `c_t|L_A-L_B|/2`. Their sum is exactly `c_t max(L_A,L_B)=c_t Phi_{A_t,B_t}(sigma x)`.

8. **OK — no skip connections and exactly two hidden layers.** Inputs feed only layer 1; every layer-2 preactivation is a linear combination of layer-1 outputs; the output is affine in layer-2 outputs only. The possibly negative affine part is carried by the F2 pair, so there is no hidden direct connection from inputs or layer 1 to the output. All biases may be zero. The hypothesis forces `T` nonempty for `n>=2` because the right side is not the zero function, so both displayed hidden widths are positive.

9. **OK — second-layer width and finiteness.** Four units are allocated for every list entry `t` and every one of the `n!` permutations, including duplicate or zero preactivations if present. Width 2 is exactly `4|T|n!`. Since `n` and `T` are finite, this width is finite; no minimal-width claim is needed.

10. **OK — half-integer rule.** In `L_{E,sigma}`, the coefficient on `ReLU(x_k)` is `deg_E(sigma^{-1}(k))/2` and the coefficient on `ReLU(-x_k)` is its negative, with loops contributing two to the degree. The coefficient on either oriented difference unit belonging to `{a,b}` is `mult_E(sigma^{-1}{a,b})/2`. These are half-integers. Sums and differences used in the four layer-2 preactivations remain half-integers.

11. **OK — `|A|+|B|` weight bound.** A coordinate-feature coefficient in `L_A +/- L_B` has magnitude at most `(deg_A(v)+deg_B(v))/2 <= |A|+|B|`, because each multiset edge contributes at most two to a vertex degree and only a loop contributes two. A difference-feature coefficient has magnitude at most `(mult_A(e)+mult_B(e))/2 <= (|A|+|B|)/2`, which is stronger than the claimed bound. Thus every layer-2 weight obeys the stated coarse bound. Equality in the coordinate sum bound requires all edges of both branches to be loops at the same vertex. A doubled nonloop edge contributes `2/2=1` to each associated difference feature in `L_E`, as revision 2b states.

12. **OK — rationality.** Layer-1 weights are integers; layer-2 weights are half-integers; all hidden biases and the output bias are zero. Output weights are one of `c_t/2` or `-c_t/2`. Therefore rational `c_t` give rational parameters. For merely real `c_t`, the stated real-weight network is still valid.

13. **OK — symmetry and reindexing.** With `(sigma x)_i=x_{sigma(i)}`, one has `sigma(tau x)=(tau o sigma)x`. Left multiplication by fixed `tau` bijects `S_n`, so the unnormalized sum over every `sigma` is invariant. No `1/n!` factor is introduced. The target `max_i x_i` is also invariant.

14. **OK — sorted-cone extension.** Every `x in R^n` can be permuted into the sorted cone. Equality there between two symmetric functions therefore gives equality everywhere. Ties cause no ambiguity because any sorting permutation gives the same vector values and symmetry handles every choice.

15. **OK — exact match to the upstream-certified hypothesis.** The pinned verifier parses each term as a rational coefficient times
   `max(sum_{(a,b) in A} max(x_a,x_b), sum_{(a,b) in B} max(x_a,x_b))`, permits loops and repeated/common edges, requires equal branch cardinalities, and sums over all `n!` permutations without normalization. On the sorted cone it writes each atom as `base.linear + ReLU(direction.linear)`, drops only hinges identically nonpositive there, primitive-normalizes the rest, and requires all retained hinge coefficients to vanish and the linear part to equal the last sorted coordinate. Those conditions are sufficient for exactly the displayed identity. They may reject some identities because the normal form is not claimed necessary, but a verifier PASS supplies precisely the semantic identity the lemma consumes. The lemma does not need the verifier's extra equal-cardinality restriction.

16. **OK — circularity and imported results.** The proof uses only the two explicitly proved scalar ReLU identities, finite enumeration, and elementary permutation reindexing. It neither assumes the target network nor imports an unstated theorem.

No item was marked `ISSUE`.

## Independent exact n=6 construction control

I implemented the note's network directly in Python using only `fractions.Fraction`; I did not import the upstream verifier or verify11. The implementation explicitly constructed both hidden layers as sparse rational weight vectors:

- layer 1: every oriented pairwise difference unit and every signed-coordinate unit;
- layer 2: all four units for every certificate term and each of all 720/720 permutations;
- output: only the four signed `c_t/2` weights per term/permutation;
- biases: 0/11,562 constructed units nonzero;
- skip connections: 0/0 present.

Exact command:

```text
/usr/bin/time -v .venv/bin/python /tmp/depth2_lemma_gpt_test.py literature/repos/max-relu-certificates/certificates/certificate_6_2.json
```

Temporary implementation SHA-256: `769d1e54c1d2dc0e251acaa1c648b987565ad89deb902ff94dadbf2bb2e512b7`. A second deterministic execution's complete canonical JSON stdout had SHA-256 `355a4f06e970b4d98dc09c4f590f76819be117c5daf5794ff13f308c6c07f3bb`.

The point generator used seed `20260903` and exact signed fractions with denominators between 1 and 11. It generated 30/30 points in `Q^6`: 12/30 had coordinate ties, 29/30 had a negative coordinate, and 10/30 were entirely negative.

| check | result |
|---|---:|
| constructed layer-1 width versus formula | 42/42 = `6(6-1)+2*6` |
| constructed layer-2 width versus formula | 11,520/11,520 = `4*4*720` |
| network output = direct certificate sum = `max(x)` | 30/30 points |
| F1 exact checks on coordinate pairs | 450/450 |
| F2 exact checks on signed coordinates | 180/180 |
| separate loop-and-repeat side-form reconstruction checks | 43,200/43,200 (`30*720*2`) |
| layer-1 weights with denominator dividing 1 | all/all |
| layer-2 weights with denominator dividing 2 | all/all |
| maximum absolute layer-2 weight observed | `3/2`, below the per-term `(|A|+|B|)=4` bound |
| maximum absolute output weight observed | `1/720` |

The test also planted an equality-destroying mutation by adding `1/1` to layer-2 output weight index 0. The mutant disagreed with `max(x)` on 14/30 points, while the unmodified network agreed on 30/30. This is a test-potency control, not a proof step.

Runtime: 18.20 seconds/1 construction-and-30-point run, peak RSS 55,884 KiB/process, exit status 0/1 possible success status. The deterministic replay also exited 0/1 possible success status.

The n=6 certificate itself exercises repeated edges: its first term contains two copies of `[1,2]` in one branch and two copies of `[3,4]` in the other. Because it has no loops, the additional 43,200/43,200 side-form checks used a separate multiset pair containing loops and repeated nonloop edges.

## Post-verdict comparison with the Opus review

Only after the bottom line and numbered audit above were written did I read `artifacts/math/t2-review/depth2-lemma/RESULT.md`, SHA-256 `eeafb2a86d5e51bb7591f04601af8da5119df2b41c63385f85b87388dffe97fd`, committed at `393cd5f1a527a7513b1cd7dc3d6af1b143666c7f`.

Agreement: its revision-2b confirmation also reaches `T2 PASS`; it independently confirms F1, F2, the no-skip pass-through, loop/repeat handling, permutation convention, exact widths 42/42 and 11,520/11,520 on the n=6 construction, half-integer weights, the multiplicity-over-two correction, rationality, sorted-cone transport, and the exact match to the upstream identity. Its earlier `PASS WITH EDITS` findings concern superseded revisions: revision 2b contains both the full-group reindexing argument and the corrected difference-feature coefficient `mult_E/2` that it requested.

Disagreement: none on any claim in revision 2b. The Opus report notes that the coefficient of `ReLU(-x_k)` is implicit rather than written alongside that of `ReLU(x_k)`. I agree this is a non-blocking exposition nit: the displayed identity `x_k=ReLU(x_k)-ReLU(-x_k)` makes the negative coefficient exactly `-deg_E/2`, and the proof's magnitude/rationality conclusions already cover it.

## Scope and no-claim

This review establishes the lemma conditional on its displayed all-real-input identity. The independent rational-point test is a known-answer implementation control and does not prove the universal statement; the symbolic argument above carries that burden. This report does not independently reverify either n=11 certificate, claim minimal width, address `n>=12`, prove any depth lower bound, or formalize the lemma in a proof assistant.
