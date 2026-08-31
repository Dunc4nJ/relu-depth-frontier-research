# G-0130 model-boundary audit — outcome-blind W2 verdict

**MATERIAL INCREMENT: the exact implication boundary is narrower on MEMBER and stronger inside the frozen dictionary on NONMEMBER than a casual reading suggests.**

- Skill / route / domain: `frontier-research-with-epistemic-humility` v1.0.0-rc.1 / W2 read-only audit / mathematics
- Generated: 2026-08-31T03:50:27Z
- Evidence snapshot: Git `2269652fc689519220ecfcef028519b8ac6283e5`
- Auditor: SwiftBridge (Codex / GPT-5; fresh context, same model family; T1 only)
- Preregistration commit: `df56dc6`
- Custody: `ATTESTED_READ_ONLY_W2` toward G-0128. No G-0128 source or result was edited, built, run, or replayed. `full_family_master_result_v2.json` and every outcome-bearing later artifact were not inspected.
- Standing boundary: this is a statement-match and dependency audit, not a scientific replay, T2 review, or promotion of either possible outcome.

## Bottom line

Let \(\mathcal N^{(2)}_{11}\) be the functions represented by the charter's standard ReLU architecture with **two hidden ReLU layers**, finite but unrestricted widths, and real weights and biases. Let \(\mathcal V_{11,5}\) be the full symmetrized degree-five pair-max space, and let \(\mathcal U_{163740}\) be the real span of the 163,740 frozen G-0113/G-0128 columns. The proved/specified inclusion is

\[
   \mathcal U_{163740}\subseteq \mathcal V_{11,5}\subseteq
   \mathcal N^{(2)}_{11}.
\]

No reverse inclusion is established. In particular, the 163,740 columns are neither all two-hidden-layer networks nor the complete degree-five pair-max dictionary. They are a source-derived, loopless, signed-\(W\) quotient subfamily.

G-0128 decides only whether the restriction of \(11!\,\mathrm{MAX}_{11}\) to 380 fixed exact linear coordinates belongs to the restriction of \(\mathcal U_{163740}\):

\[
  R_{380}(11!\,\mathrm{MAX}_{11})
  \stackrel{?}{\in}
  R_{380}(\mathcal U_{163740}).
\]

Consequently:

| Possible G-0128 outcome | What it establishes | What it does not establish |
|---|---|---|
| `MEMBER` | An exact rational combination of actual two-hidden-layer pair-max functions whose 301 panel coordinates, all 11 ordered-chamber linear coordinates, and 68 selected hinge coordinates equal the target's. Equivalently, the global residual lies in `ker R_380`. | It does not show that the residual is the zero function, that all omitted hinge coefficients vanish, or that this is a MAX11 network. The earlier 348-row member was refuted by complete global replay. |
| `NONMEMBER` | An exact integer functional on the 380 coordinates that kills every frozen column and not the target. This rules out a global MAX11 identity in the **real as well as rational** span of the 163,740 frozen functions. | It does not rule out the rest of the degree-five pair-max dictionary, another degree, arbitrary virtual-polytope atoms, or unrestricted two-hidden-layer networks. It is not an all-\(n\) lower bound. |

A positive global replay of a MEMBER needs only sound architecture compilation; it needs no family-completeness theorem. Promoting a NONMEMBER to an unrestricted depth lower bound would require a target-specific completeness theorem that is presently missing.

## 1. Exact reconstruction of the frozen family

For an unordered coordinate pair \(e=(p,q)\), put

\[
 m_e(x)=\max(x_p,x_q),\qquad
 S_A(x)=\sum_{e\in A}m_e(x)
\]

for an edge multiset \(A\). A degree-five pair-max block and its full labelled orbit sum are

\[
 \Phi_{A,B}(x)=\max\{S_A(x),S_B(x)\},\qquad
 F_{A,B}(x)=\sum_{\sigma\in S_{11}}\Phi_{A,B}(\sigma x).
\]

The frozen generator set is constructed as follows.

1. Start with each of the 402 nonzero degree-four pair templates in the public exact MAX10 certificate.
2. Embed it on 11 labels and append one unordered **nonloop** edge \(e_L\) to the left branch and one unordered nonloop edge \(e_R\) to the right branch.
3. Retain only \(e_L\ne e_R\) in the two search-priority relations: DISJOINT endpoints or exactly one shared endpoint. Identical added edges and loops were explicitly excluded as a search choice, not by theorem.
4. This gives 795,960 DISJOINT plus 397,980 SHARED_DISTINCT raw extensions.
5. Cancel common branch edges and quotient the signed multigraph \(W=B'-A'\) by simultaneous \(S_{11}\) relabelling and global sign/branch reversal. The union contains 133,449 DISJOINT records followed by 30,291 new SHARED_DISTINCT-only records: 163,740 total.
6. Every raw edge is nonloop. The common-nonloop transfer identity
   \(\max(S_{C+A'},S_{C+B'})=S_C+\max(S_{A'},S_{B'})\), followed by full symmetrization, makes a signed-\(W\) record a sound representative of the complete loopless degree-five atom function. Distinct signed-\(W\) records were not proved to be linearly independent or even functionally distinct; this is harmless for span membership.

The master gives every record an arbitrary rational coefficient. The inherited MAX10 coefficients and relation-fibre weights are enumeration provenance, not coefficient tying in G-0128.

This family is a proper **generator-set restriction** of the advertised degree-five ansatz:

- the complete loopless degree-five signed-\(W\) denominator has 754,017 classes, leaving 590,277 loopless classes outside the frozen generator set;
- the complete loop-inclusive degree-five span is represented locally by 7,015,841 signed-\(W\) records plus the `5E` and `5L` bases; and
- the raw symmetry-template count for the full degree-five Rueß ansatz is 12,179,657.

Those census inequalities do not alone prove strict inequality of the resulting vector spaces—different generators can collide or be linearly redundant. They do prove that “all 163,740 records” means all records of this selected subfamily, not all degree-five atoms.

Primary locators: `artifacts/math/G-0113/DEGREE5_QUOTIENT_PREREGISTRATION.md:8-30,32-57,93-96`; `artifacts/math/G-0113/PANEL_SOLVER_PREREGISTRATION.md:21-33,43-50`; `artifacts/math/G-0027/README.md` §Exact collapse and §Executed census; `artifacts/math/G-0044/README.md` §§3-5; `literature/papers/2607.21651.txt` §4.1.

## 2. What the 380 columns actually record

On the open ordered chamber \(C^\circ=\{x_0<\cdots<x_{10}\}\), every frozen orbit function has an exact normal form

\[
 F_s(x)=\ell_s\cdot x+\sum_d h_{s,d}\,\rho(d\cdot x),
\]

where each retained \(d\) is a primitive, zero-sum integer vector, first-nonzero oriented, whose hyperplane meets the chamber interior. The delivered uniqueness lemma proves these hinge functions are linearly independent modulo linear functions on \(C^\circ\). Symmetry and continuity then extend a zero complete normal-form residual from the chamber to all of \(\mathbb R^{11}\).

G-0128 does **not** store this complete normal form. Its restriction map is the ordered tuple

\[
 R_{380}(f)=
 (\underbrace{301\text{ panel functionals}}_{\text{finite formal-colour assignment sums}},
  \underbrace{11\text{ linear coefficients}}_{\ell_0,\ldots,\ell_{10}},
  \underbrace{68\text{ selected hinge coefficients}}_{4+32+32}).
\]

The target vector is the 301 panel target, then \((0,\ldots,0,11!)\), then 68 zeros. Thus a MEMBER has already matched the entire linear part but can retain a nonzero coefficient on an unqueried active hinge direction. The complete direction universe for arbitrary degree-five blocks has 657,822 active hinge rows, illustrating the size of the kernel that 68 selected hinge rows do not by themselves eliminate.

Primary locators: `artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md:99-117`; `artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md` §§Statement, Symmetry consequence, Scope; `artifacts/math/G-0044/README.md` §3.

## 3. Theorem-level branch implications

### Proposition A — sound inclusion in the network class

Every \(F_s\), and therefore every finite real linear combination in \(\mathcal U_{163740}\), is representable by a standard two-hidden-layer ReLU network.

**Reason.** Each first branch sum is a linear combination of pairwise maxima. A shared first layer can realize each pairwise maximum using ReLUs and linear coordinates. The outer binary maximum is a rank-2 maxout gate and can be replaced by three ordinary ReLUs. All labelled orbit copies and all support terms are finite, and block-diagonal parallelization followed by the output linear form closes the class under finite linear combinations. Rueß et al. give the no-skip compilation and the bounds `first width <= binom(n,2)+2n`, `second width <= 3 s n!` for `s` supported templates.

This is a **soundness** direction only: \(\mathcal U_{163740}\to\mathcal N^{(2)}_{11}\).

### Proposition B — exact meaning of MEMBER

Let \(A\in\mathbb Z^{380\times163740}\) be the frozen column matrix and \(b=R_{380}(11!\,\mathrm{MAX}_{11})\). `MEMBER` supplies \(q\in\mathbb Q^{163740}\) with \(Aq=b\). For

\[
  r(x)=\sum_s q_sF_s(x)-11!\,\mathrm{MAX}_{11}(x)
\]

it proves exactly \(R_{380}(r)=0\). Proposition A compiles \(\sum_s q_sF_s\) to a genuine two-hidden-layer function, but it does not prove that this function is MAX11.

The inference `MEMBER => global identity` is concretely falsified inside this campaign: G-0128's own preregistration records that the G-0121 348-row exact member was refuted by the G-0126 complete global replay (`G-0128` lines 5-6). That is not merely a hypothetical sampling objection; it is the immediate ancestor of this experiment.

If a separately preregistered complete replay establishes that every active hinge coefficient and every linear residual of this same candidate is exactly zero, the normal-form uniqueness lemma plus symmetry gives

\[
  \sum_s q_sF_s(x)=11!\,\mathrm{MAX}_{11}(x)
  \quad\text{for every }x\in\mathbb R^{11}.
\]

After the record-to-network compilation is instantiated and independently replayed, that is an explicit two-hidden-layer MAX11 network and settles the charter's **first rung**. No completeness of the dictionary is needed for this positive implication.

Even that positive does not establish the charter's quantifier `for every n`: MAX11 is one instance, and no induction preserving exactly two hidden layers follows from it.

### Proposition C — exact meaning of NONMEMBER

`NONMEMBER` supplies a primitive integer \(y\in\mathbb Z^{380}\) such that

\[
  y^TA=0,\qquad y^Tb\ne0.
\]

Suppose, for contradiction, that some real coefficients \(c_s\) gave the global identity \(\sum_sc_sF_s=11!\,\mathrm{MAX}_{11}\). Every component of \(R_{380}\) is a legitimate linear functional on the delivered atom semantics, so applying \(R_{380}\) and then \(y^T\) would give \(0=y^Tb\), a contradiction. Therefore

\[
  11!\,\mathrm{MAX}_{11}\notin\mathcal U_{163740}
\]

over **real** coefficients, not merely rational coefficients. Equivalently, because \(A,b\) are rational, consistency over \(\mathbb R\) would imply consistency over \(\mathbb Q\) by rational row reduction.

This is a valid global obstruction for this fixed function span even though its certificate uses finitely many coordinates. It remains a bounded claim because the generator family—not the input domain of the excluded identity—is bounded.

The inference `NONMEMBER => MAX11 not in N^(2)_11` is invalid without a reverse reduction \(\mathcal N^{(2)}_{11}\to\mathcal U_{163740}\). G-0128 supplies no such reduction.

## 4. Concrete counterexample to the missing reverse reduction

The delivered G-0084 document gives an exact, checkable counterexample to every proposed reverse reduction based only on symmetry, positive homogeneity, translation covariance, or pair-max structure:

\[
 G(x)=\frac1{5940}\sum_{i,j,\ell\text{ pairwise distinct}}
       \max\{6x_i,5x_j+x_\ell\}.
\]

It is convex, positively homogeneous, \(S_{11}\)-invariant, satisfies \(G(x+t\mathbf1)=G(x)+t\), and has an explicit one-hidden-layer realization (hence an exactly two-hidden-layer realization by identity ReLUs). It lies in the degree-six pair-max space \(\mathcal V_{11,6}\).

Nevertheless, on the ordered chamber it has a genuine hinge with primitive normal

\[
 v=6e_2-5e_1-e_3,
\]

whose signed mass is six. Every degree-five pair-max block has only primitive hinge normals of signed mass at most five. At a generic point of \(v^\perp\cap C^\circ\), the gradient jump of \(G\) is nonzero while every degree-five combination is locally affine. Hence

\[
 G\notin\mathcal V_{11,5}+\operatorname{Aff}(\mathbb R^{11}),
\]

and a fortiori \(G\notin\mathcal U_{163740}+\operatorname{Aff}\).

This does **not** show MAX11 is outside either space; \(G\ne\mathrm{MAX}_{11}\). It does show that the missing completeness lemma must use a MAX11-specific, hinge-free property. Symmetry and the target's translation law are not enough.

Primary locator: `artifacts/math/G-0084/SYMMETRIZATION_COMPLETENESS_BOUNDARY.md:251-398`. The derivation is same-family/T1 and not formalized; this audit checked the displayed gradient-jump argument but does not promote its standing.

## 5. Exact missing lemmas

### 5.1 Positive branch: compilation obligation, not completeness

For a globally zero normal-form MEMBER, the remaining local obligation is:

> **COMP-SOUND.** From every serialized frozen record and rational coefficient, construct matrices and biases in the charter's no-skip two-hidden-layer architecture, prove the network equals the corresponding full labelled orbit sum with the campaign's normalization, and show block parallelization equals the certificate sum.

The generic mathematics is already in Rueß et al. §4.1/§4.3 and its width paragraph. What is missing from G-0128 itself is a binding-clean instantiation: record semantics, orbit multiplicities, coefficient/target normalization, matrices, and an independent statement-matched replay. This obligation is sufficient after a global zero. It is not needed to interpret a finite-row MEMBER as only a candidate.

### 5.2 Negative branch: minimal target-specific completeness

The logically minimal theorem needed to turn a frozen-family NONMEMBER into an unrestricted two-hidden-layer lower bound is

\[
 \boxed{
 \mathrm{MAX}_{11}\in\mathcal N^{(2)}_{11}
 \Longrightarrow
 11!\,\mathrm{MAX}_{11}\in\mathcal U_{163740}.}
 \tag{COMP-163740-MAX}
\]

No committed artifact proves this implication. It is useful to factor it into three independently falsifiable obligations.

1. **GNF (arbitrary network to graphical-pair normal form).** Any two-hidden-layer MAX11 identity can, after all virtual cancellations and symmetrization, be rewritten as a finite signed sum of equal-branch-degree pair-max orbit blocks, with arbitrary finite degree. Symmetrization alone yields orbit averages of general virtual atoms with arbitrary real generator directions and widths; it does not yield coordinate segments, integer multiplicities, or equal branch degrees.
2. **DR5-MAX (target-fibre degree reduction).** If exact hinge cancellation at arbitrary pair-max degrees leaves the ordered-chamber target vector \(e_{11}\), then some degree-five combination also cancels every hinge and leaves \(e_{11}\). The stronger claim \(\mathcal V_{11,6}\subseteq\mathcal V_{11,5}\) is refuted by \(G\); only this hinge-free target fibre remains logically possible.
3. **FROZEN-FIBRE (full degree five to the 163,740 subset).** If \(e_{11}\) lies in the linear projection of the complete hinge-free degree-five space, then it lies in the corresponding projection of \(\mathcal U_{163740}\). The loop/identical-edge exclusions, 754,017-class loopless denominator, and 7,015,841-record loop-inclusive denominator show that this is a substantive extra step, not a synonym for DR5-MAX.

`GNF + DR5-MAX` would at most make the **complete** degree-five pair-max space target-complete. `FROZEN-FIBRE` is additionally required for G-0128's particular dictionary. Conversely, the combined boxed implication is enough for the negative branch but nearly restates the desired lower-bound bridge; it cannot be inferred from census size or symmetry.

Primary locators: `artifacts/math/G-0084/SYMMETRIZATION_COMPLETENESS_BOUNDARY.md:84-149,400-488`; `artifacts/math/G-0113/DEGREE5_QUOTIENT_PREREGISTRATION.md:27-30,93-96`.

### 5.3 Actual global charter after MAX11

The charter target is \(\forall n\ge1\), not merely \(n=11\). A compiled global MEMBER settles the first rung only. Completing the positive global goal still requires an all-\(n\) construction or induction that keeps the hidden-layer count at exactly two. Completing the negative global goal needs only one explicit \(n\) with an unconditional unrestricted lower bound, but G-0128 NONMEMBER becomes such a result only after `COMP-163740-MAX`.

## 6. Highest-leverage next action in each branch

### If G-0128 is MEMBER

**Preregister and run one complete arbitrary-precision global normal-form replay of that exact member.** Regenerate every supported orbit atom, aggregate every active hinge coefficient and all 11 linear coefficients, subtract the exact scaled target, and require either exact all-coordinate zero or the first exact nonzero residual. Include coefficient mutation and a clean-room implementation.

Why this dominates: it tests the only implication MEMBER lacks, and the immediately preceding 348-row member failed at exactly this gate. If zero, instantiate `COMP-SOUND` and independently replay the compiled matrices. If nonzero, it refutes only that coefficient vector; append the residual row and reopen all 163,740 columns rather than declaring family nonmembership.

### If G-0128 is NONMEMBER

**Preregister an exact price of the 380-row separator over the complete degree-five denominator: all 7,015,841 loop-inclusive signed-\(W\) records plus `5E` and `5L`.** Re-derive the denominator/evaluator independently enough to meet the claim's standing, scan in frozen order, and report the first nonzero price or a complete zero census.

Why this dominates: adding more rows inside \(\mathcal U_{163740}\) cannot undo an existing nonmembership certificate; only enlarging the generator space or proving a completeness bridge can move the global question. A nonzero price supplies a concrete omitted escape column and falsifies extension of this separator to the full degree-five ansatz. A complete zero price with nonzero target pairing upgrades the obstruction to \(\mathcal V_{11,5}\), after which `GNF/DR5-MAX`—not more frozen-family linear algebra—is the named wall.

The existing 7,015,841 transfer/census is same-family bounded evidence and must not silently substitute for an independent subject-bound sweep.

## 7. Claim verdicts and obligations

| Claim | Verdict | Weakest link / exact boundary |
|---|---|---|
| “The 163,740 columns are a sound two-hidden-layer construction family.” | **Holds as a mathematical inclusion; local compilation still uninstantiated.** | `COMP-SOUND` for serialized record-to-matrix statement match. |
| “A G-0128 MEMBER is a MAX11 network.” | **Refuted as stated.** | Only `R_380` equality; complete normal-form replay absent. |
| “A globally replayed zero MEMBER can yield a MAX11 network.” | **Holds conditionally.** | Complete exact zero, then `COMP-SOUND` and independent replay. |
| “A G-0128 NONMEMBER excludes MAX11 from the frozen real function span.” | **Holds conditionally on the delivered row semantics/evaluator soundness.** | Exact integer separator and all-column census; it is not rational-only. |
| “A G-0128 NONMEMBER proves no two-hidden-layer MAX11 network exists.” | **Cannot verify / unsupported.** | `COMP-163740-MAX` is absent. |
| “Either G-0128 outcome settles the charter's all-n target.” | **Refuted as stated.** | MAX11 is explicitly the first rung. |

Obligations:

| ID | Obligation | Blocks |
|---|---|---|
| G-0130-O1 | Complete global normal-form replay of an exact MEMBER. | Global MAX11 identity. |
| G-0130-O2 | Binding-clean standard-ReLU compilation and independent matrix replay (`COMP-SOUND`). | Calling a global orbit identity a network certificate. |
| G-0130-O3 | Prove or refute `GNF`. | Arbitrary-network to pair-max reduction. |
| G-0130-O4 | Prove or refute `DR5-MAX` on the hinge-free target fibre. | Arbitrary-degree to full degree-five reduction. |
| G-0130-O5 | Prove or refute `FROZEN-FIBRE`; first exact discriminator is complete-degree-five separator pricing. | Full degree-five to the 163,740 frozen subset. |
| G-0130-O6 | Give an all-\(n\) two-hidden-layer construction, or one unconditional unrestricted counterexample arity. | Charter terminal target. |

## Cousin and no-claim boundary

- Frozen-subfamily span is not full degree-five span.
- Full degree-five pair-max span is not the arbitrary two-hidden-layer class.
- Finite-coordinate membership is not global function equality.
- Fixed-family nonmembership is a valid obstruction for that family but not unrestricted-network nonrepresentability.
- A MAX11 witness is not an all-\(n\) construction.
- An integer separator over this rational matrix excludes real coefficients in this fixed family; describing it as “rational-only” would understate the bounded result.

This audit did not inspect or predict the G-0128 outcome, rerun the master, produce a new certificate, or adjudicate the implementation audit. Its strongest output is the implication boundary and the obligation chain above.

## Subject artifacts examined

- `RESEARCH_CHARTER.md`
- `NEURAL_REPRESENTATION_EPISTEMICS.md`
- `artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md`
- `artifacts/reviews/G-0128-round2-master/REVIEW_PREREGISTRATION.md`
- `artifacts/math/G-0121/FULL_FAMILY_MASTER_PREREGISTRATION.md`
- `artifacts/math/G-0126/GLOBAL_REPLAY_PREREGISTRATION.md`
- `artifacts/math/G-0117/FULL_FAMILY_CEGIS_PREREGISTRATION.md`
- `artifacts/math/G-0117/GLOBAL_CEGIS_PREREGISTRATION.md`
- `artifacts/math/G-0117/EXACT_GLOBAL_REPLAY_PREREGISTRATION.md`
- `artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md`
- `artifacts/math/G-0113/DEGREE5_QUOTIENT_PREREGISTRATION.md`
- `artifacts/math/G-0113/DEGREE5_FULL_ATOM_PREREGISTRATION.md`
- `artifacts/math/G-0113/COMMON_NONLOOP_TRANSFER_PREREGISTRATION.md`
- `artifacts/math/G-0113/PANEL_SOLVER_PREREGISTRATION.md`
- `artifacts/math/G-0113/SIGNED_W_SCOPE_CORRECTION.md`
- `artifacts/math/G-0027/README.md`
- `artifacts/math/G-0044/README.md`
- `artifacts/math/G-0084/SYMMETRIZATION_COMPLETENESS_BOUNDARY.md`
- `imports/target-selection-2026-08-27/max11-ansatz-audit-2026-08-27.md`
- `literature/papers/2607.21651.txt`
- `literature/repos/max-relu-certificates/README.md`

## Residual doubts

1. The 7,015,841 signed-\(W\) transfer and G-0084 counterexample are same-family/local derivations, not T2-refereed or formalized; they are sufficient to name obligations, not to promote a final research result.
2. Census differences establish omitted generators, not strict span separation. `FROZEN-FIBRE` could hold accidentally for the one target even if no general span equality holds.
3. This review did not inspect implementation source or result bytes, so Proposition C is an implication from the preregistered certificate shape plus semantic bindings, not a verdict that any emitted separator satisfies them.
4. The generic no-bias arbitrary-network reduction is imported through a cited primary proposition and the delivered G-0084 derivation; it was not independently reconstructed here because it is not needed for the narrow G-0128 branch logic.
