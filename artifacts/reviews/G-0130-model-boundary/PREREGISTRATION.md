# G-0130 model-boundary audit preregistration

- Registered: 2026-08-31 (Europe/Berlin)
- Reviewer: SwiftBridge (Codex, GPT-5; fresh context)
- Mode / route / domain: audit / W2 / mathematics
- Target: reconstruct exactly what the committed, frozen 163,740-column family denotes relative to MAX11 and depth-2 (two-hidden-layer) ReLU networks, then state the strongest logically valid consequences of either G-0128 outcome.

## Blind boundary

This review is registered before inspecting project evidence. I will inspect committed preregistrations, definitions, normal-form/compilation documents, code that fixes the column semantics, and pre-result verification artifacts needed to identify the tested object. I will not inspect any G-0128 result, outcome, verdict, generated witness/nonwitness, result log, or later artifact that reveals that outcome. I will not edit G-0128 source or result material.

## Questions fixed in advance

1. What mathematical object does one column encode, what coefficients/combinations are allowed, and over which input domain is equality or realization tested?
2. Is the 163,740-column family asserted merely as a finite candidate dictionary, or proved sound and complete for every depth-2/two-hidden-layer ReLU representation relevant to MAX11?
3. Which quantifiers and resource bounds separate “membership in the frozen family” from “MAX11 is representable by an arbitrary network of the named depth”?
4. What does MEMBER establish without importing any unstated compilation lemma? What does NONMEMBER establish?
5. What explicit soundness, normalization, or completeness lemma is missing, if any, for the global depth-separation goal?
6. What single next proof/experiment has maximum information gain after each possible outcome?

## Adversarial hypotheses and falsifiers

- H1 (finite-family boundary): the frozen columns cover only a chosen normal-form subfamily. Falsifier: a committed theorem, with proof obligations discharged, mapping every relevant arbitrary depth-2 network realizing MAX11 into the frozen coefficient system without increasing forbidden resources or changing the target domain.
- H2 (soundness gap): a column or allowed combination may be only a formal feature rather than an executable network of the claimed architecture. Falsifier: a checked construction from every admissible coefficient vector/witness to an actual network, preserving the stated width/depth/sign/bias constraints and equality notion.
- H3 (sample-versus-function gap): membership may concern values on a finite test set rather than equality on the full continuous domain. Falsifier: a proved extension/identifiability lemma or an experiment whose domain is explicitly the entire target domain in an exact representation.
- H4 (resource-bound gap): NONMEMBER may exclude only one fixed width, coefficient class, symmetry class, or knot arrangement. Falsifier: a theorem showing those restrictions are without loss of generality for all networks at the global goal's quantifiers.
- H5 (terminology gap): “depth-2” may count hidden layers differently across artifacts. Falsifier: an explicit architecture convention and a layer-by-layer compilation tying the frozen family to that convention.

## Precommitted inference rules

- MEMBER can imply at most the existence of the exact object whose columns and admissible coefficients encode. It implies an actual network representation only through a soundness/realization lemma whose hypotheses match the witness.
- NONMEMBER can imply at most nonexistence inside the frozen family. It implies a global lower bound for arbitrary depth-2/two-hidden-layer ReLU networks only through a completeness/normal-form lemma whose quantifiers and resource accounting cover that entire class.
- Finite-point equality will not be promoted to functional equality without an extension theorem.
- A width-bounded conclusion will not be promoted to an unbounded-width depth separation.
- Computation, even exact and independently replayed, remains a bounded claim unless the finite reduction itself is proved complete.

## Deliverable and decision standard

The review will give (i) a theorem-level definition of the frozen family, (ii) a two-branch implication table listing what MEMBER/NONMEMBER do and do not prove, (iii) concrete countermodels to every invalid inference that remains possible, (iv) the exact missing lemma and its required statement, and (v) one highest-leverage next experiment/proof for each branch. Every bottom-line sentence will cite primary committed artifacts; uncertainty or absent proof will be reported as an obligation, not filled by interpretation.
