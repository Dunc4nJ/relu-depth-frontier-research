# G-0083 — bounded literature audit for the two-hidden-layer hinge-rank obstruction

Audit date: 2026-08-30 (Europe/Berlin)

Search cutoff: 2026-08-30

Evidence policy: theorem-level claims below are based on primary papers or publisher records. Discovery indexes were used only to find candidates. This is a bounded audit, not an exhaustive novelty opinion.

## Question audited

The candidate statement is:

> Let `P` be a full-dimensional `d`-polytope that is not a zero-summand. If its support function `h_P` has a two-hidden-layer ReLU representation, then, after recession/affine separation, the common span `U` of the projected first-layer hinge (segment) directions has `dim U >= d - 1`.

The proposed proof normal form assigns to each second-layer atom

`h_conv(t + Z_+, Z_-) - h_Z_-`,

where `Z_+, Z_-` are zonotopes parallel to `U`. If `r = dim U`, the two constituent polytopes have dimensions at most `r + 1` and `r`. Thus `r <= d - 2` would express `P` as a signed Minkowski combination of lower-dimensional polytopes, making `P` a zero-summand.

## Bounded finding

I did **not** locate a primary source that explicitly states the shared-first-layer-span conclusion `dim U >= d - 1`, either for arbitrary non-zero-summand polytopes or in an equivalent network formulation.

The result nevertheless should **not** be presented as a strong standalone novelty claim. The closest prior, Grillo–Hofmann (2025), already publishes the virtual-polytope/network correspondence and the common-affine-span “plus one” dimension calculation. Hertrich–Basu–Di Summa–Skutella (2021/2023) supplies the exact ReLU difference-of-support-functions identity, and Koutschan–Moser–Ponomarchuk–Schicho (2023/2025) supplies the zero-summand obstruction. The candidate theorem is therefore best described as an **apparently unstated, narrow two-hidden-layer specialization/synthesis of existing machinery**.

The defensible distinction is its parameter: it bounds the dimension of the **single global span of projected first-layer hinge directions**, rather than maxout indegree, atom degree, virtual-polytope dimension, minimal max arity, or unrestricted network depth.

## Closest prior and exact overlap

### 1. Grillo–Hofmann, *On the expressivity of sparse maxout networks*

- Primary source: [arXiv:2510.14068v1](https://arxiv.org/abs/2510.14068), submitted 2025-10-15T20:18:18Z.
- Campaign reference: `REF-0015`.
- Exact locators: Theorem 7 (PDF p. 9); Definition 8 and Lemma 9 (PDF p. 10); Lemma 10 (PDF p. 11); Theorem 11 (PDF p. 12); Lemma 15 and Theorem 16 (PDF p. 14); lineality discussion (PDF p. 17).
- Repository text locators: `literature/papers/2510.14068.txt:458`, `:514-619`, `:623-647`, `:781-803`, and `:959-971`.

What it proves:

- Theorem 7 gives the sparse-maxout-network/virtual-polytope bijection.
- Definition 8 sets `dim(V) = min{dim(P + Q) : V = P - Q}`.
- Lemma 9 computes the affine hull of a union of translated subspaces.
- In the proof of Lemma 10, before the final subadditivity relaxation, the bound is `dim(U + W) + r - 1`; see repository text lines 571-619, especially lines 610-616. For the convex hull of two polytopes parallel to one common `r`-space, this is precisely the `r + 1` mechanism used by the candidate theorem.
- Theorem 11 iterates the dimension estimate through sparse maxout layers. Lemma 15 and Theorem 16 convert bounded virtual-polytope dimension into a signed combination of small simplices / bounded max arity.
- The discussion identifies virtual-polytope dimension with codimension of lineality.

What it does **not** state:

- no global span `U` formed from projected first-layer ReLU hinge directions;
- no lower bound `dim U >= d - 1` for a prescribed non-zero-summand target;
- no formulation in terms of recession/affine separation of a biased two-hidden-layer ReLU network.

Assessment: this is the closest prior and a material limitation on any novelty claim. The candidate conclusion is not textually present, but its central dimension step is already explicit in Lemmas 9–10.

## Ingredient chain and neighboring results

| Primary source | Exact locator | Published overlap | Gap from candidate |
|---|---|---|---|
| Hertrich, Basu, Di Summa & Skutella, *Towards Lower Bounds on the Depth of ReLU Neural Networks*, [arXiv:2105.14835v5](https://arxiv.org/abs/2105.14835), first submitted 2021-05-31, v5 dated 2024-07-17; [SIAM DOI](https://doi.org/10.1137/22M1489332) | §5, Proposition 5.1; Theorem 5.2; equation (13), printed pp. 28–29 | Network/virtual-polytope recursion and `max{0,g-h} = max{g,h} - h`. Taking `g=h_(t+Z_+)`, `h=h_(Z_-)` gives the candidate atom formula by support-function duality. | No common first-layer direction span or zero-summand rank bound. |
| Koutschan, Moser, Ponomarchuk & Schicho, *Representing Piecewise Linear Functions by Functions with Small Arity*, [arXiv:2305.16933v1](https://arxiv.org/abs/2305.16933), 2023-05-26; [publisher DOI](https://doi.org/10.1007/s00200-023-00627-1) | §5, zero-summand definition; Lemma 5.1; Corollary 5.2; Lemma 5.3; Theorem 5.4, printed pp. 11–13 | Defines a zero-summand exactly as a polytope admitting a signed Minkowski relation with zero-volume polytopes; proves face inheritance and that a simplex is not a zero-summand; derives the max-arity obstruction. | Does not analyze a two-hidden-layer network's shared first-layer span. For an arbitrary target assumed non-zero-summand, the final contradiction is essentially the negation of its definition. |
| Bakaev, Brunck, Hertrich, Stade & Yehudayoff, *Better Neural Network Expressivity: Subdividing the Simplex*, [arXiv:2505.14338v3](https://arxiv.org/abs/2505.14338), first submitted 2025-05-20, v3 dated 2026-02-19; [ACM DOI](https://doi.org/10.1145/3798129.3800768) | §3.1 Lemma 8; §3.2 Lemmas 9–10, printed pp. 7–8 | Support-function/formal-Minkowski-difference characterization and full additivity used to obtain upper constructions from subdivisions. | Construction machinery; no common-span/rank lower bound. |
| Rueß et al., *Shallower ReLU Network Representations via Exact Linear Algebra*, [arXiv:2607.21651v1](https://arxiv.org/abs/2607.21651), submitted 2026-07-22 | §4.1 pairwise-max ansatz; Proposition 4.2 and Corollary 4.3, printed pp. 8–9; repository text `literature/papers/2607.21651.txt:453-486` | The most explicit specialized analogue: each degree-`k` atom is the support function of `conv(Z_A union Z_B)`, dimension at most `2k+1`; Koutschan's simplex obstruction then forces `k >= floor((n-1)/2)`. | Bounds atom degree in a restricted pairwise-coordinate ansatz. It does not exploit a single shared span of all first-layer segment directions and does not cover arbitrary non-zero-summand targets. |
| Wang & Basu, *Representing MAX functions using two-hidden-layer ReLU networks*, [arXiv:2608.25221v1](https://arxiv.org/abs/2608.25221), submitted 2026-08-25 | introduction, equation (1), atom discussion on printed pp. 1–2; conclusion §6 | Uses the same sum-of-pairwise-max / outer-max atoms and explicitly identifies them with convex hulls of two zonotopes; gives constructions for `MAX_5` through `MAX_8`. | No lower bound of the audited kind; the authors explicitly say their linear system is only a sufficient ansatz, not a characterization. |
| Koutschan, Ponomarchuk & Schicho, *Representing Piecewise-Linear Functions by Functions with Minimal Arity*, [arXiv:2406.02421v2](https://arxiv.org/abs/2406.02421), first submitted 2024-06-04, v2 dated 2026-06-17 | §III, Lemma III.3 and Theorem III.5 | Characterizes minimal max arity through lineality/critical flags. | Controls arity of a functional decomposition, not dimension of a shared first-layer direction span. |

### Proof-level comparison

The candidate argument can be reconstructed from the cited ingredients in four short steps:

1. After the stated recession/affine normalization, a first-layer hinge with projected direction `u_j` corresponds to the support function of `[0,u_j]`. Hence all positive- and negative-sign zonotope sums `Z_+`, `Z_-` are parallel to `U = span{u_j}`.
2. Hertrich et al., equation (13), gives
   `ReLU(h_(t+Z_+) - h_(Z_-)) = h_conv(t+Z_+, Z_-) - h_(Z_-)`.
3. Grillo–Hofmann Lemma 9, or the sharper pre-subadditivity line in Lemma 10, gives `dim conv(t+Z_+, Z_-) <= dim U + 1`; also `dim Z_- <= dim U`.
4. The output therefore makes `P` a signed Minkowski combination of polytopes of dimension at most `r+1`. If `r <= d-2`, every constituent has zero `d`-volume, contradicting Koutschan et al.'s definition of `P` being non-zero-summand.

This derivation explains both why the exact statement may be useful and why its conceptual novelty should be described narrowly.

## Citation/reference traversal

The three requested seeds were read at theorem level, not just by abstract:

- `2305.16933`: §5 zero-summand chain and its cited support-function correspondence.
- `2505.14338`: §3 formal Minkowski differences, full additivity, and its Hertrich-thesis dependency.
- `2607.21651`: §4 pairwise-max atom obstruction and its explicit citation of `2305.16933`, Corollary 5.2.

Their backward references led to `2105.14835`, `2302.12553`, and the Newton/virtual-polytope line of work. Sparse-maxout searches found `2510.14068`; that paper in turn cites Hertrich et al., Koutschan et al., Bakaev et al., and related virtual-polytope papers. The post-Rueß search found `2608.25221`, which cites Rueß et al. and uses the same atom family. Forward-citation discovery was also checked by exact-title/arXiv-ID searches; very recent citation indexes are incomplete, so absence of indexed citations was not treated as evidence.

Additional primary papers screened without finding an equivalent theorem: [arXiv:2205.05647](https://arxiv.org/abs/2205.05647), [2302.12553](https://arxiv.org/abs/2302.12553), [2402.15315](https://arxiv.org/abs/2402.15315), [2410.04907](https://arxiv.org/abs/2410.04907), [2411.03006](https://arxiv.org/abs/2411.03006), [2502.06283](https://arxiv.org/abs/2502.06283), [2502.09324](https://arxiv.org/abs/2502.09324), [2505.06169](https://arxiv.org/abs/2505.06169), and [2605.18319](https://arxiv.org/abs/2605.18319).

## Exact query log

Interfaces: arXiv API (`https://export.arxiv.org/api/query`), arXiv full-text/metadata pages, publisher pages, and general web exact-phrase search. OpenAlex was used only as a discovery/citation-index check, never as authority for a theorem claim.

ArXiv API `search_query` strings:

```text
all:"two-hidden-layer" AND all:ReLU
all:"two hidden layers" AND all:ReLU AND all:maximum
all:"support function" AND all:ReLU AND all:polytope
all:"virtual polytopes" AND all:"neural networks"
all:zonotope AND all:ReLU AND all:depth
all:"first hidden layer" AND all:ReLU AND all:polytope
all:"hinge direction" AND all:ReLU
all:"zero summand" AND all:polytope
all:"lower-dimensional polytopes" AND all:ReLU
```

Exact web/full-text query strings:

```text
2305.16933
2505.14338
2607.21651
"zero-summand" polytope ReLU
"virtual polytope" ReLU network support function
"Newton polytope" ReLU network depth
ReLU ridge functions essential variables rank lower bound
zonotopal depth hierarchy ReLU polytopes
site:arxiv.org ReLU "zero summand"
site:arxiv.org ReLU "zero-summand"
site:arxiv.org neural network "signed Minkowski combination" lower-dimensional polytopes
site:arxiv.org "first hidden layer" ReLU "span" polytope dimension
"zero summand" "ReLU"
"zero-summand" "ReLU"
"signed Minkowski combination" "ReLU"
"lower-dimensional polytopes" "two hidden layers" ReLU
site:arxiv.org "hinge directions" ReLU "first layer"
site:arxiv.org "first-layer" "ridge directions" ReLU
site:arxiv.org ReLU "essential variables" ridge function lower bound
site:arxiv.org ReLU "common span" directions network
site:arxiv.org ReLU "span of the first-layer"
site:arxiv.org ReLU "span of first-layer" weights expressivity
site:arxiv.org ReLU network "rank of the first layer" exact representation
site:arxiv.org ReLU "first-layer weight matrix" rank lower bound
site:arxiv.org/abs/2510.14068 "On the expressivity of sparse maxout networks"
site:arxiv.org "sparse maxout networks" virtual polytopes
site:arxiv.org sparse maxout support function dimension rank lower bound
site:arxiv.org maxout network first layer directions rank
"On the expressivity of sparse maxout networks" citation
"2510.14068" ReLU
site:arxiv.org "2510.14068"
```

## Campaign custody record for the closest prior

Repository identity checked before materialization:

```text
git rev-parse --show-toplevel: /data/projects/relu-depth-frontier-research
git remote get-url origin: git@github.com:Dunc4nJ/relu-depth-frontier-research.git
```

Canonical source retrieved 2026-08-30: `https://arxiv.org/pdf/2510.14068` (arXiv v1; 20-page PDF). Text was produced locally with `pdftotext -layout`. The campaign also retains `literature/metadata/2510.14068.atom.xml`, `literature/metadata/2510.14068.pdfinfo.txt`, and `literature/source-cards/REF-0015.md` under its L3 admission convention.

```text
4f3d787ddbabd507619a8d3c6cf6ef76c4b9e8db0c747d8773f6d6b79426f556  literature/papers/2510.14068.pdf
b10477690f301c7718eb55f4d6fb12df37fa9eeb8b4c825485b3306ff000558c  literature/papers/2510.14068.txt
```

All retained literature bytes are recorded in `literature/MANIFEST.sha256`.

## Bottom line

Within the bounded corpus, the exact shared-span theorem was not found. The strongest supportable wording is:

> “We isolate an apparently unstated common-first-layer-span corollary of the published virtual-polytope dimension and zero-summand machinery.”

Avoid “first rank lower bound,” “new polyhedral obstruction,” or an unqualified novelty claim unless a broader expert/citation review rules out equivalent formulations beyond this audit.
