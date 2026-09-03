# Novelty gate — MAX_11 in ReLU_2 — 2026-09-03

Searcher: literature agent (Claude Fable 5.1), autonomous run.
Window: 2026-09-03T03:01:05Z – 2026-09-03T03:13:43Z (all timestamps UTC).
Scope: dated novelty gate for the campaign's unpublished claim that `max_11` is exactly
representable by a ReLU network with two hidden layers and real weights, witnessed by exact
rational certificates in the pairwise-max ("rank-2 maxout") ansatz of Rueß et al.

No content of the campaign's certificates was transmitted to any service. Queries described the
public topic only. Nothing was posted, uploaded, or submitted anywhere.

---

## HEADLINE: the claim is not novel. We were scooped by two days.

`arXiv:2607.21651v2`, submitted **2026-09-01T17:59:31Z**, replaces the v1 result `n ≤ 10` with:

> **Theorem 1.1.** For every integer $3\leq n\leq 12$, two hidden layers are necessary and
> sufficient to represent $\max\nolimits_{n}$ exactly by a ReLU network. Moreover, such a
> representation exists with rational weights.

The exact rational certificates for `n = 11` and `n = 12` were pushed to the paper's public
repository on **2026-09-02T07:49:55Z** (commit `20d231c987e9cc43defd02006f81ccd8088422a7`,
message `feat: add certificates for n=11,12`).

This covers both the theorem and the artifact type our campaign produced. It also goes one arity
further than we did.

---

## Search log

Engines used: arXiv abstract pages and full-text HTML (`arxiv.org/abs`, `arxiv.org/html`), the
arXiv search UI (`arxiv.org/search`), the arXiv Atom API, the Semantic Scholar Graph API, the
GitHub REST API, the OpenReview API, and a general web search index.

### A. Primary sources and version histories

| # | time (UTC) | engine / URL | query or target | result |
|---|---|---|---|---|
| A1 | 03:01 | arxiv.org/abs/2607.21651 | version history + abstract | **v1 2026-07-22T16:58:02Z; v2 2026-09-01T17:59:31Z.** v2 abstract: "We prove that max_n(x)=max{x_1,...,x_n} is exactly representable with two hidden layers for every n≤12." Depth recursion improved to ⌈log_6(n/2)⌉+1. cs.LG, cross-list cs.NE, math.CO. No v3. |
| A2 | 03:01 | arxiv.org/abs/2608.25221 | version history + abstract | Wang & Basu, **v1 only**, 2026-08-25T23:22:33Z. Still reports MAX_5–MAX_8 and cites Rueß et al. at "N ≤ 10". No update since. |
| A3 | 03:03 | arxiv.org/abs/2607.21651v1 | contrast check | v1 Theorem 1.1: "For every $n\leq 10$…"; depth base 5. Confirms the n≤12 claim is new in v2. |
| A4 | 03:03 | arxiv.org/abs/2607.21651v2 | confirm | n ≤ 12, base 6, dated 2026-09-01. |
| A5 | 03:04 | api.github.com/repos/kilianar/max-relu-certificates/commits | full commit list | 4 commits. Three on 2026-07-21. Fourth: `20d231c9…`, kilianar, **2026-09-02T07:49:55Z**, "feat: add certificates for n=11,12". |
| A6 | 03:04 | api.github.com/…/contents/certificates | file listing | `certificate_11_5.json` (10,959,392 B) and `certificate_12_5.json` (3,687,188 B) now present alongside n=5..10. |
| A7 | 03:06 | arxiv.org/html/2607.21651v2 (full text, 401 KB, parsed locally) | Theorem 1.1, Cor B.2, Table 3, §5 | See quotes below. |
| A8 | 03:12 | arxiv.org/html/2607.21651v1 (full text, parsed locally) | Corollary 4.3 | `k ≥ k_min := ⌊(n−1)/2⌋` was **already in v1** (Cor 4.3, 2026-07-22), later renumbered Cor B.2 in v2. |
| A9 | 03:13 | arxiv.org/abs/2607.21651 | re-check for v3 | Still exactly v1, v2. |

### B. Follow-ups and citation sweep

| # | time (UTC) | engine | query | result |
|---|---|---|---|---|
| B1 | 03:04 | Semantic Scholar Graph API, citations of arXiv:2607.21651 | — | **Exactly 2 citing papers**: Wang & Basu 2608.25221 (2026-08-25) and Safran 2608.23877 (2026-08-24). No third party has built on it. |
| B2 | 03:05 | web search | `"max_n" ReLU "two hidden layers" exact representation n=12 arXiv 2026` | Returned 2607.21651 and 2608.25221. Index was still serving the v1 abstract ("n ≤ 10") at this time; a later query returned the n≤12 text. Web index lag noted. |
| B3 | 03:07 | arXiv search UI | `ReLU "maximum" "two hidden layers"` | 4 hits: 2608.25221, 2607.21651 (listed 1 Sep 2026), 2505.14338, plus one off-topic (2402.05696). |
| B4 | 03:08 | arXiv search UI | `ReLU depth "maximum of n"` | 2505.14338, 2505.06169, 2302.12553. Nothing new. |
| B5 | 03:08 | arXiv search UI | `"depth" "ReLU" "max" lower bound 2026` | 0 results. |
| B6 | 03:08 | arXiv search UI | `neural network depth maximum function lower bound polytope` | 2505.14338, 2302.12553. Nothing new. |
| B7 | 03:12 | arXiv search UI | `ReLU network depth exact representation` | 2607.21651 top hit; remainder off-topic. |
| B8 | 03:09 | arXiv author search | Hertrich, Loho, Basu, Yehudayoff | No submission on this topic after 2607.21651v2. Yehudayoff's most recent is 2608.26996 (Poisson races, 27 Aug). |
| B9 | 03:10 | arXiv author search | Averkov, Safran, Grillo, Brunck | Same. Safran's newest (2608.23877, 30 Aug) is an L2 approximation hierarchy, not exact `max_n`. |
| B10 | 03:12 | OpenReview API `notes/search` | `two-hidden-layer ReLU maximum` | No submission corresponding to this line of work. Nothing newer than the arXiv record. |
| B11 | 03:11 | web search | `"Shallower ReLU Network Representations" Rueß openreview OR blog OR talk max_12` | Only arXiv mirrors. No blog, talk, or slide deck found. |
| B12 | 03:11 | web search | `mathoverflow OR reddit OR blog "max" ReLU "two hidden layers" 11 numbers depth conjecture 2026` | Only arXiv/OpenReview mirrors. No MathOverflow thread on the exact question. |
| B13 | 03:13 | web search | `"max_11" OR "MAX 11" ReLU two hidden layers certificate rational September 2026` | Only the two arXiv papers. No independent MAX_11 announcement. |
| B14 | 03:12 | neuralpolytopes.gitlab.io/workshop2026 | community venue check | Workshop on Polyhedral Geometry for Neural Networks, Nuremberg, 16–20 Mar 2026; talks by Haase, Averkov, Yehudayoff, Safran, Brunck, Grillo on exactly this depth question. Predates the n≥11 work. No public Zulip archive reachable. |

### C. Independent structural audit of the published n=11 certificate

Downloaded `certificate_11_5.json` at 03:09 UTC.
SHA-256 `d291790e467629c3653175f86a516f51904a1db4741caf53935e9fbcb73a3966`, 10,959,392 bytes.

| property | value |
|---|---|
| declared `n` | 11 |
| number of terms | 39,042 |
| Table 3 "support size" for n=11 | 39,042 (matches) |
| side sizes (k_left, k_right) | (5,5) for 38,167 terms; also (4,4), (3,3), (2,2), (1,1) — all ≤ 5 |
| terms containing a loop (i,i) | 29,121 of 39,042 |
| terms with a repeated edge inside one side | 45 |
| terms with A ∩ B = ∅ | 38,858 of 39,042 |
| terms with both sides forests | 9,628 of 39,042 |
| denominator prime factors (partial factorisation) | 2, 3, 5, 7, 11, 13, 29, 31, plus a large unfactored cofactor |

I did **not** run the full exact verifier: it symmetrises over all 11! = 39,916,800 permutations per
term across 39,042 terms, which is far beyond this session's budget. The structural audit and the
match to Table 3 are what I can attest to. The upstream reproducibility statement supplies the
verifier for anyone who wants the exact check.

Note for the campaign: the published n=11 certificate is **loop-inclusive** (75% of its terms carry
a loop `(i,i)`) and is **not** forest-restricted, unlike the n=9 and n=10 certificates the campaign
audited as loop-free. Remark 3.2 of v2 says the tighter loop-free/forest restriction is observed to
remain solvable, but the shipped n=11 artifact does not use it.

---

## Verdicts

### Q1. Has anyone published MAX_n ∈ ReLU_2 for some n ≥ 11? — **NOT NOVEL**

Strongest evidence: `arXiv:2607.21651v2` (2026-09-01T17:59:31Z), Theorem 1.1, verbatim:

> For every integer $3\leq n\leq 12$, two hidden layers are necessary and sufficient to represent
> $\max\nolimits_{n}$ exactly by a ReLU network. Moreover, such a representation exists with
> rational weights.

Corroborated by the public certificates `certificate_11_5.json` and `certificate_12_5.json`
(GitHub commit `20d231c9…`, 2026-09-02T07:49:55Z), and by Table 3 of v2 whose n=11 row
(`N_rep = 12,179,657`, `|D| = 657,822`, support 39,042) is the same linear system the campaign
was solving. The campaign's own recorded column count for n=11 is 12,179,657 — an exact match.

The result is theirs, first, publicly, with artifacts. Our independent derivation is at best a
same-week independent confirmation, and it is two days late.

### Q2. Is there a real-weight lower bound that would contradict MAX_11 ∈ ReLU_2? — **NO RED FLAG**

No such bound exists, and none could: v2 exhibits a verified rational certificate, and the same
authors prove the matching lower bound of 2 by restriction to Mukherjee–Basu. The lower-bound
literature remains confined to restricted weight classes and to depth ≥ 3 width bounds:

- Integer weights: `⌈log_2(n)⌉` layers needed (Haase–Hertrich–Loho, arXiv:2302.12553).
- N-ary / decimal-fraction weights: `⌈log_p(n+1)⌉` (Averkov–Hojny–Merkert, arXiv:2502.06283). v2's
  Corollary 3.3 uses exactly this: for `10 ≤ n ≤ 12`, `max_n` has a rational two-layer
  representation but **no** decimal-fraction one.
- Braid-conforming networks: `Ω(log log d)` (Grillo–Hertrich–Loho, arXiv:2502.09324).
- Depth-2 width: `Ω(d²)` (Safran, arXiv:2601.01417).
- Binary inputs: Krishnan–Mossel, arXiv:2606.18540 (v2 2026-06-29), all-depths separation for
  Boolean inputs only — does not touch real-input `max_n` at constant depth. **New to the corpus.**

No lower bound restricted to the pairwise-max ansatz was found beyond Corollary B.2 (the `k` bound,
which is about the parameter, not an impossibility).

### Q3. Current best frontier statement (as of 2026-09-03) — five lines

1. **Upper bound, exact, small n:** `max_n ∈ ReLU_2` for all `3 ≤ n ≤ 12`, with rational weights —
   Rueß et al., arXiv:2607.21651v2 (2026-09-01); certificates public 2026-09-02.
2. **Upper bound, general n:** `⌈log_6(n/2)⌉+1` hidden layers, hence every CPWL function on `R^d`
   is exact in `⌈log_6((d+1)/2)⌉+1` layers, and two layers suffice for `d ≤ 11` — same paper,
   Corollaries 1.2 and 1.3, improving the base-3 bound of Bakaev et al. (STOC'26, arXiv:2505.14338).
3. **Lower bound, unrestricted real weights:** still just **2** (Mukherjee–Basu 2017, Prop. 2.2,
   restricted to `max{0,x_1,x_2}`). No function is known to need three hidden layers.
4. **Lower bounds, restricted models:** `⌈log_2 n⌉` for integer weights (2302.12553);
   `⌈log_p(n+1)⌉` for N-ary weights (2502.06283); `Ω(log log d)` for braid-conforming nets
   (2502.09324); `Ω(d²)` width at depth 2 and super-linear width at depth `k ≥ 3` (2601.01417).
5. **Open:** whether two layers suffice for all `n`. v2, §5: "`n=13` remains unresolved because the
   corresponding computation exceeds our available resources, not because the ansatz is known to
   fail. There is currently no indication that the solutions stop at `n=12`."

### Q4(a). Is "5-edge branches necessary at n = 11, pattern k = ⌊(n−1)/2⌋" novel? — **NOT NOVEL**

Published since **v1, 2026-07-22**, as Corollary 4.3 (renumbered Corollary B.2 in v2), verbatim:

> **Corollary B.2.** The exact systems assembled from the ansatz above can have a solution only if
> $k\geq k_{\min}\coloneqq\left\lfloor\frac{n-1}{2}\right\rfloor$. Thus, $k_{\min}$ is the smallest
> value of $k$ not ruled out by Proposition B.1.

Their proof route is the one the campaign also used: `Φ_{A,B} = h_{conv(Z_A ∪ Z_B)}` has dimension
at most `2k+1`, so `2k+1 ≥ n−1`, contradiction otherwise via Koutschan et al. Corollary 5.2. At
`n = 11` this gives `k = 5` immediately. v2 §3 states they use `k = ⌊(n−1)/2⌋` for every
`5 ≤ n ≤ 12`, and the shipped n=11 certificate has maximum side size 5, as expected.

### Q4(b). Is the S_n-lift recursion (n−1 certificate spans max_n) novel? — **UNCERTAIN, leaning NOVEL as a theorem, but explicitly named as an open direction**

Nobody has stated or proved this recursion. The paper's own recursion, Theorem 4.1, is a different
object: it substitutes a whole low-arity network into the first hidden layer, multiplying arity by
`r = ⌊l/2⌋` per **added** layer. It does not relate the arity-`n` certificate to the arity-`(n−1)`
one at fixed depth 2. Their proof of Theorem 1.1 solves each arity independently.

But the general shape of the idea is explicitly flagged as the wanted next step, in v2 §5:

> A more useful next step is therefore to understand the structure behind the observed solutions. A
> structural description of the corresponding signed Minkowski relations could replace the
> arity-by-arity linear systems by a general argument and thereby extend the construction beyond
> the computational range.

and

> Any $o(\log n)$ bound therefore requires a stronger recursion whose gain grows with arity, or a
> different structural principle relating solutions across arities.

So: the specific S_n-lift statement is unpublished and, as far as these searches reach, unstated by
anyone. It is also the direction a ten-author group has publicly announced it is pursuing, with the
computational infrastructure already built. Treat the window as short. The v2 AI-use statement also
records that they tried LLM-assisted pattern-finding on the solutions and got nothing usable —
which is where the campaign's structural work would land if it holds.

I did not attempt to check whether the campaign's lift claim is *correct*; that is outside a
novelty gate.

---

## What these searches could not see

- **The full exact verification** of the published n=11/n=12 certificates. Out of compute budget
  here; structural audit only.
- **The Neural Polytopes Zulip community**, acknowledged in v2. Not publicly readable without an
  account. This is the single most likely place for an unannounced result, and it is dark to me.
- **arXiv Atom API**: returned HTTP 503 and "Rate exceeded" on every attempt. arXiv coverage rests
  on the abstract pages, full-text HTML, and the search UI, all of which agreed.
- **Google Scholar and MathSciNet/zbMATH**: not used; no reproducible or authenticated endpoint.
  Semantic Scholar's citation graph is the only citation index consulted, and it lags — it had not
  yet indexed v2's change.
- **Web search index lag**: at 03:05Z the general index still returned the v1 "n ≤ 10" abstract for
  2607.21651. Anything posted in the last ~72 hours may be invisible to keyword search. The arXiv
  abstract pages, which I queried directly, do not have this lag.
- **Private drafts, seminar talks, unindexed workshop notes, and non-English venues.**
- **Whether a v3 or a further repository commit lands after 2026-09-03T03:13:43Z.**

A failed search means only "not found by this search."

---

## Bibliography additions

Appended to `literature/bibliography.bib` in this commit (existing entries untouched):

- **REF-0016** — Krishnan & Mossel, *Depth Lower Bounds for ReLU Networks with Binary Inputs*,
  arXiv:2606.18540 (v1 2026-06-16, v2 2026-06-29). Found by this sweep; the only 2026 depth
  lower-bound paper absent from the corpus. Boolean inputs only, so it does not bear on `max_n`
  at constant depth, but it belongs in the lower-bound map.
- **REF-0017** — Bakaev & Yehudayoff, *A simplex-based measure of symmetry*, arXiv:2607.03815
  (v1 2026-07-04). Already relied on by campaign items G-0063/65/66 but never entered in the
  bibliography.
- **REF-0018** — Bakaev, Brunck & Yehudayoff, *Approximation Depth of Convex Polytopes*,
  arXiv:2507.07779 (v1 2025-07-10). Flagged as missing in the 2026-09-02 synthesis; directly
  relevant to the depth upper-bound line.

Also noted, not added (already present as REF-0001, and no duplicate entry should be created):
**REF-0001 is now stale.** Its bibliography entry and source card describe the v1 result `n ≤ 10`.
The live paper is v2 with `n ≤ 12` and base-6 recursion. REF-0001 needs a version field and a
re-read; that edit is left to whoever owns `literature/INDEX.md` and the source cards.

Not added, still absent from the corpus, flagged for the owner: arXiv:2410.04907 (Decomposition
Polyhedra of Piecewise Linear Functions, v 2026-06-04) and arXiv:2509.21286 (Maxout Polytopes).

---

## Commit provenance

The two deliverables of this gate (`literature/novelty-search-2026-09-03.md` and the three new
BibTeX entries in `literature/bibliography.bib`) were staged for a dedicated commit at
2026-09-03T03:14Z. Before that commit ran, a concurrent agent working on
`artifacts/math/n11-sparse-certificate/` staged everything in the tree and committed, sweeping both
files into `5327b61` ("relu-depth-frontier-research-psu: expose fixed-rho ADMM control",
2026-09-03T03:15:30Z). That commit's message does not describe this work.

Shared history was not rewritten, since other agents are committing to `master` concurrently. This
note carries the correct attribution instead; the commit that adds it holds the intended message.
