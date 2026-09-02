# GMP.6 result: the claimed original-network 25-neuron 3-cover does not follow

## Verdict

**REFUTED as a derivation from Safran, arXiv:2601.01417v1.** The paper does not
establish that every two-hidden-layer representation of `MAX_11` has at least
25 *original* first-layer neurons whose actual supports have cardinality 2 or
3 and form a 3-cover of all 165/165 coordinate triples.

There is a clean **conditional wall** inside the intended proof: if a depth-3
network is in the transformed form used in Proposition A.4—global computation,
zero first-layer biases, and no first-layer weight supported on fewer than two
coordinates—then one selected pair from each first-layer support must cover
all 165/165 triples. Such a pair cover has at least

```text
C(11,2) - floor(11^2/4) = 55 - 30 = 25
```

distinct pairs, so that transformed network has at least 25 first-layer
neurons. This conditional statement places no upper bound of 3 on the actual
support cardinalities. The paper's attempted passage from an arbitrary biased
network on the cube to that transformed network both permits a factor-2 width
increase and contains an unclosed support-one case. Consequently it does not
prove the claimed 25-neuron condition for the original network.

This refutes the stated inference, not the mathematical possibility that some
different argument could prove a 25-neuron condition.

## Exact source and locators

Reviewed inputs:

- `literature/papers/2601.01417.pdf`, SHA-256
  `22ca802e8b66cb087899cd52ec0089cf456295a28b9c2ac2fa0f22ad39fb64c8`.
- `literature/papers/2601.01417.txt`, SHA-256
  `05222fe630d1c6248ac90f02d7bcc6fb0f1e6460dde5eda17e3d2a31228aa742`.

Line locators below refer to the hashed text extraction.

| Locator | What it says | Consequence |
|---|---|---|
| 210-217 | Depth is the number of hidden layers plus one. | “Depth 3” is exactly two hidden layers. |
| 237-258 | Theorem 2.1 states the depth-3 width bound `floor((1/8-1/(4d)-1/(2d^2))d^2)`. | At `d=11`, the displayed theorem gives `floor(95/8)=11`, not 25. It is a largest-hidden-layer width statement. |
| 336-346 | For each first-layer weight with at least two nonzero entries, delete the edge joining its two smallest nonzero indices; each neuron deletes at most one edge. | The construction selects one pair from a support; it does not show that the support itself has cardinality 2 or 3. |
| 373-392 and 387-389 | A clique is used only after asserting that every neuron has a nonzero coordinate outside it. | This is the input to the dimensional-collapse step. |
| 655-689 | Proposition A.2 rules out a depth-2 network for `MAX_3` on the cube. | This supplies the contradiction after a first-layer collapse. |
| 695-705 | Lemma A.3 claims homogenization, at most twice the width, and first-layer support cardinality at least two. | Both the factor 2 and the support claim matter. |
| 730-742 | A negative shifted bias deletes its neuron; a positive shifted bias replaces it with two zero-bias neurons having weights `w` and `-w`. | A positive-bias support-one neuron becomes two support-one neurons. |
| 753-761 | The proof says `b+c w_j` is nonzero with probability one and concludes that homogenization leaves no support-one neurons. | This conclusion does not follow: “nonzero” includes the positive branch above. |
| 764-783 | Proposition A.4 imports the support-at-least-two conclusion from Lemma A.3 and allows at most twice the width. | The later graph argument relies on the unsupported lemma conclusion. |
| 827-844 | Theorem 2.1 applies Proposition A.4, constructs the graph, and uses a triangle. | The proof operates on the transformed network, not directly on the original network. |
| 845-918 | Negative coordinate assignment fixes every first-layer activation and collapses the layer, contradicting Proposition A.2. | This part works conditional on every first-layer support meeting the triangle complement. |

## Reconstruction of the valid conditional combinatorics

Let a network in the transformed form above have first-layer supports `S_i`,
with `|S_i| >= 2`. Select one pair `e_i` from each `S_i` (the paper takes the
two smallest indices) and delete the distinct selected pairs from `K_d`.

1. If the remaining graph contains a triangle `T`, no selected `e_i` lies in
   `T`.
2. If some `S_i` were contained in `T`, then its selected pair would lie in
   `T`, a contradiction. Thus every `S_i` meets the complement of `T`.
3. The coordinate assignment in section 2.4 then fixes every first-layer
   activation on the `T` cube. Collapsing that layer would give a depth-2
   representation of `MAX_3`, contradicting Proposition A.2.
4. Hence the remaining graph is triangle-free. Equivalently, the selected
   pairs meet every 3-subset: they form a pair 3-cover.
5. Mantel's bound gives at most `floor(d^2/4)` remaining edges, so the number
   of distinct selected pairs is at least
   `C(d,2)-floor(d^2/4)`. For `d=11`, this is 25 pairs covering 165/165
   triples.

One neuron selects at most one pair, so the *transformed* first layer has at
least 25 neurons. Even if Proposition A.4 were repaired with its advertised
factor 2, its construction creates at most two transformed first-layer neurons
per original first-layer neuron. It would therefore transport only the
conditional original-layer bound `ceil(25/2)=13` neurons, not 25. To get 25
for the original layer would require a no-doubling transformation or an
additional hypothesis that the original network is already in the required
global, zero-first-bias, support-at-least-two form.

## Where the derivation fails

There are three separate mismatches.

1. **No support upper bound.** Lines 338-341 and 771-772 require only at least
   two nonzero coordinates. A selected 2-subset of an arbitrary large support
   is not proof that the neuron's actual support has size 2 or 3.
2. **Wrong network and lost factor 2.** The 25-pair wall applies to the
   transformed network. Proposition A.4 allows it to have at most twice the
   original width. The direct 25-neuron conclusion does not transport back.
3. **Support-one cleanup is incomplete.** For a support-one weight `w_j`,
   lines 753-761 establish only that the shifted bias `b+c w_j` is nonzero for
   almost every `c`. If it is positive, lines 735-742 replace the neuron by
   weights `w` and `-w`, preserving support cardinality one. For example,
   `b=0` and `w_j>0` make the shifted bias positive for every
   `c in [0.4,0.6]`. The asserted absence of support-one neurons therefore
   needs a new argument. Since Proposition A.4 imports that assertion, its
   use in the graph proof is not established by the v1 text.

This identifies a proof gap; it does not prove Proposition A.4 false.

## Planted positive: upstream certificates for `n=5..10`

`check_certificate_3cover.py` parses all 6/6 certificate JSON files using
exact `Fraction` coefficients. Each non-loop inner maximum has the exact
first-layer realization
`max(x_a,x_b)=x_b+[x_a-x_b]_+`: if `x_a >= x_b` the right side is `x_a`, and
otherwise it is `x_b`. Its nonlinear neuron has pair support `{a,b}`. Because each
certificate term is fully symmetrized over coordinates, the orbit of any one
non-loop seed pair is all `C(n,2)` pair supports. The script constructs that
orbit without expanding `n!` permutations and directly checks every triple.

| `n` | non-loop / all raw inner-pair occurrences | distinct pair supports / `C(n,2)` | covered triples / `C(n,3)` | Mantel minimum pair-cover size |
|---:|---:|---:|---:|---:|
| 5 | 9/12 | 10/10 | 10/10 | 4 |
| 6 | 16/16 | 15/15 | 20/20 | 6 |
| 7 | 226/342 | 21/21 | 35/35 | 9 |
| 8 | 317/414 | 28/28 | 56/56 | 12 |
| 9 | 2696/2696 | 36/36 | 84/84 | 16 |
| 10 | 3216/3216 | 45/45 | 120/120 | 20 |

Thus the planted property holds for 6/6 explicit upstream constructions. It
holds very redundantly: their fully symmetrized nonlinear pair supports are
the complete pair set, not merely a minimum cover. This is a property of these
constructions and does not transfer to arbitrary networks.

Certificate SHA-256 values, in the table order:

- `n=5`: `698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694`
- `n=6`: `026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83`
- `n=7`: `b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be`
- `n=8`: `68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3`
- `n=9`: `4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88`
- `n=10`: `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`

## Controls and verification

Positive controls:

- 6/6 certificate support orbits cover all their triples.
- 6/6 independently constructed balanced-partition pair covers have size
  `C(n,2)-floor(n^2/4)` and cover all triples.
- The `n=11` balanced-partition known answer has 25 pairs and covers 165/165
  triples.
- 2/2 reviewed Safran inputs match their pinned hashes.

Negative controls:

- For each of 6/6 certificate dimensions, deleting exactly the 3/3 pairs
  inside `{1,2,3}` makes exactly 1/`C(n,3)` triple uncovered, namely
  `{1,2,3}`.
- For each of 6/6 dimensions, the empty support family misses
  `C(n,3)`/`C(n,3)` triples.
- The output verifier rejects 1/1 planted mutation of a saved coverage count.
- The standalone self-test deletes 1/9 supports from an `n=7` minimum cover
  and detects at least 1/35 missing triples.

The upstream functional certificate verifier was **not** rerun: it enumerates
all permutations and is unnecessary for this support-orbit check. Therefore
this bead does not independently re-establish the six certificate identities.

Peak RSS for the final verifier was 20,188 KiB (`20,188 KiB / 2 GiB` cap),
with 0.09 seconds wall time.

## Exact commands and trial record

Environment:

```sh
source scripts/activate-toolchain.sh
```

Compilation and standalone controls:

```sh
python -m py_compile \
  artifacts/math/refute-3cover/check_certificate_3cover.py \
  artifacts/math/refute-3cover/verify_outputs.py
python artifacts/math/refute-3cover/check_certificate_3cover.py --self-test
```

The first audit invocation failed its expected-dimensions gate because the
harness sorted filenames lexicographically (`certificate_10_4.json` preceded
`certificate_5_2.json`). No mathematical output was accepted. The harness was
changed to sort parsed records by `n`, and the same command then passed:

```sh
python artifacts/math/refute-3cover/check_certificate_3cover.py \
  --certificates literature/repos/max-relu-certificates/certificates \
  --output artifacts/math/refute-3cover/certificate_3cover_audit.json
```

Final independent recomputation, fixed known-answer checks, hash checks, and
mutation rejection:

```sh
/usr/bin/time -v python artifacts/math/refute-3cover/verify_outputs.py \
  --audit artifacts/math/refute-3cover/certificate_3cover_audit.json \
  --checker artifacts/math/refute-3cover/check_certificate_3cover.py \
  --certificates literature/repos/max-relu-certificates/certificates \
  --paper-text literature/papers/2601.01417.txt \
  --paper-pdf literature/papers/2601.01417.pdf
```

Final output:

```text
GMP6_VERIFY_PASS certificates=6/6 covers=6/6 destructive_mutations=7/7 empty_nulls=6/6 paper_hashes=2/2
```

Artifact hashes before adding this report:

- `check_certificate_3cover.py`:
  `545f9ee95b98d7638c84bcbfd97b851a2b1f59797c75ac16a6777093e3cd93d8`
- `verify_outputs.py`:
  `6db4695574e1d309700385752426278914e9948f4ee7a72007bc5215c42ade41`
- `certificate_3cover_audit.json`:
  `9a10affa43679df5d69ee27cc1c2f8968853ff81f2e11a43d471ce3c01e83159`

## Retry predicate

The conditional wall can be promoted only after a proof repairs the positive
shifted-bias support-one case in Lemma A.3 (within a stated width factor), or
replaces that lemma. A 25-neuron wall for the *original* first layer further
requires eliminating the factor-2 transport loss. A claim specifically about
actual supports of cardinality 2 or 3 requires an additional support-size
reduction argument not present in this source.

## No-claim line

**NO CLAIM:** This result is not an impossibility result for `MAX_11`, not an
unrestricted depth lower bound, not a counterexample network, not a proof that
Proposition A.4 is false, and not an exact re-verification of the upstream
certificate identities. Even if repaired, the 3-cover condition is a **WALL**
(a necessary constraint for witness search), never by itself an impossibility
result.
