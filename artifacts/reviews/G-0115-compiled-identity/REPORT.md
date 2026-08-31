# Fresh-context adversarial review of G-0115

**Correctness verdict: HOLDS, within the stated MAX9 boundary (T1).**

**Promotion verdict: do not call this a new MAX9 theorem or a transport
breakthrough.** The strongest artifact is a genuine exact 395-term,
degree-four identity for `MAX9` inside the 22,666-class family obtained by
adding one edge to each branch of the public degree-three `MAX8` certificate.
That is a strong arity-specific calibration of the lift span. It is not a
coefficient-transport law, an induction theorem, a `MAX10`/`MAX11` result, a
lower bound, or an efficiency result.

I found no mathematical defect in the promoted 395-term identity. I did find
one material evidence-label defect: the author's two Python reports described
as independent both import the same `semantic_repair.py`, which in turn uses
the same G-0094 ordered-cone normal-form implementation. They are independent
of the solve matrices, caches, checkpoints, and compilers, but not of the
semantic kernel. This review closes that gap with a literal C++ orbit replay
that imports none of those modules.

This is a fresh-context review by the same model family. It is T1 evidence,
not T2 external or human refereeing, and it does not adjudicate novelty.

## Claims adjudicated

| Claim | Verdict | Exact boundary |
|---|---|---|
| Corrected coefficient-frozen residual repair | Holds as an intermediate identity | Exact hinge repair plus rational `Lambda`; not by itself the full nine-coordinate target |
| 1,217-term mixed-degree `MAX9` identity | Holds | Exact degrees 1--4 identity, but scientifically dominated by the degree-four-only certificate |
| 395-term degree-four-only `MAX9` identity | Holds | Exact identity in the G-0115 one-edge lift span |
| Every serialized term is a genuine member of the frozen lift family | Holds | All 395 terms match the independently reconstructed 22,666-class family |
| The lift support reveals a transport law or induction mechanism | Not established | Coefficients were refit at `MAX9`; no frozen cross-arity rule was proved |
| Novel `MAX9` representability theorem | False as stated | Exact two-hidden-layer `MAX9` was already public in Rueß et al. |
| Novel restricted-span containment result | Plausible, not adjudicated | Requires a dedicated literature search and expert comparison before promotion |

## Independent literal replay

The verifier in this directory reads only a serialized certificate. For each
term it:

1. parses its exact rational coefficient and its two edge multisets;
2. enumerates every injective assignment of active labels to the nine ordered
   ranks, multiplying by the inactive-label factorial to represent all `9!`
   permutations;
3. evaluates both branch sums literally from the pairwise maxima;
4. canonically orients the branch difference and aggregates the exact
   common-denominator hinge and linear normal form; and
5. requires zero hinge residual and linear vector `e9`.

It does not import G-0115 or G-0094 Python, and it reads no generated semantic
field, matrix, cache, solver, basis, checkpoint, compiler report, or CEGIS
report. The C++ implementation was compiled with warnings as errors. A known
public `MAX9` certificate is the positive control. For each promoted target,
the helper also rejects a `+1` coefficient mutation, a first-edge mutation,
and a target-linear mutation.

### Results

| Input | Terms | Degrees | Full permutation terms represented | Exact result |
|---|---:|---|---:|---|
| Public Rueß et al. `MAX9` control | 337 | 4 | 122,290,560 | zero hinges, linear `e9`, all mutants rejected |
| G-0115 mixed identity | 1,217 | 1: 4; 2: 7; 3: 126; 4: 1,080 | 441,624,960 | zero hinges, linear `e9`, all mutants rejected |
| G-0115 unrestricted lift identity | 395 | 4 | 143,337,600 | zero hinges, linear `e9`, all mutants rejected |

The degree-four replay uses common denominator `65,318,400`, evaluates
127,707,057 injection leaves, and returns the scaled linear vector

```text
(0,0,0,0,0,0,0,0,65318400).
```

The mixed replay uses common denominator `1,213,173,100,339,200,000` and
returns the corresponding exact scaled `e9`. Integer arithmetic is used
throughout the C++ replay.

### Evidence bindings

```text
628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e  unrestricted_full_semantic_certificate_v1.json
93ffa8bb00c6b774619f840b1de767c15ff98eb7b7c3f9a77ad73471f61bce32  compiled_full_max9_identity_v1.json
4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88  public certificate_9_4.json
2c42c7601eeeab5d964ee72780b99b477acd0f3448d8c5bfdc455ae5216bb2a4  literal_orbit_replay.cpp
50fa4734933b92d82696868bd5c0253bc06c1ae54e5a92395a6589042f846b32  run_literal_orbit_replay.py
5bb5ad8296814bb92e354d1e0da3feb29743131ad4a2ebdc933d64040c499289  audited helper binary
b67f84ebfdcbce91e3e37b6aca909510e86e2fd9ac67d22274494ce36bffb78b  literal_public_max9_control_v1.json
606ac34aae84048943e19e0ca1d0f072eed8ee72e5fdfdf356060e8a347cbd38  literal_mixed_degree_replay_v1.json
604bdde08ca138a0df078be7ba63b6e3bc07f119d24375dd328e98e1e4c016f4  literal_unrestricted_degree4_replay_v1.json
```

## Independent support audit

I also rebuilt the structural claim without using the producer's pynauty
certificate:

- all 22,666 raw representatives reconstruct exactly as a public `MAX8`
  source pair plus one added edge on each branch;
- the frozen order independently hashes to
  `a8563f4c2d187dd2a4a6714d5f6fb00c12c738ff7cf025f77e4b0898a46e9a82`;
- all 395 certificate terms select unique genuine columns;
- all 328 `retained` terms are color-preserving signed-graph isomorphic to
  public `MAX9` support classes after common-edge cancellation; and
- all 67 `repair` terms have no such public signed-support match.

The public-support comparison uses independently constructed colored
incidence graphs and NetworkX isomorphism, including branch-color exchange.
A mutation of a raw lift edge is rejected. The report is
`lift_support_audit_v1.json`, SHA-256
`41f70c5fc22a35dca8e85ce8df024f757f4e9d8aedf0f70bcfa4eaf0e3b45aee`;
the verifier source hash is
`23c2df360f772e50365d2a5078b684674f3db903bd414caa6eb5b7bc86328ccb`.

This establishes a sharper structural statement than mere `MAX9`
representability:

> `MAX9` lies in the degree-four orbit span generated by adding one edge to
> each branch of the public degree-three `MAX8` support, and a 395-class
> witness exists using 328 public-support classes plus 67 additional lift
> classes.

It does **not** establish that this lift family is complete among degree-four
identities or that the 67 repairs arise from a low-description rule.

## Rational-`Lambda` defect audit

The original residual experiment applied `int` coordinatewise inside a
linear functional after rational coefficients had been introduced. It
therefore truncated fractions and solved a malformed target. The campaign
correctly quarantined this result before the corrected solve.

Exact reconstruction gives:

```text
Lambda(retained base)        = 2071/100
Lambda(required correction)  = -1971/100
Lambda(combined)             = 1
```

The corrected code uses exact `Fraction` arithmetic. More importantly, the
two final literal replays above do not invoke `Lambda` at all: they recompute
the complete hinge normal form and all nine linear coordinates directly.
The truncation bug therefore cannot support either final identity.

## ReLU-network meaning

The certificate is an algebraic two-hidden-layer ReLU construction, not just
a formal orbit equality. Each first-branch quantity is a sum of pairwise
maxima. Without skip connections,

```text
max(x_i,x_j) = ReLU(x_i-x_j) + ReLU(x_j) - ReLU(-x_j).
```

For two such first-layer linear combinations `A` and `B`, the second layer
can express

```text
max(A,B) = ReLU(A-B) + ReLU(B) - ReLU(-B).
```

The output layer takes the exact rational orbit sum. Thus the finite
certificate compiles directly to a bias-free two-hidden-layer network. The
literal expansion is enormous and no width, training, conditioning, or
practical inference advantage is claimed.

## Literature and significance

The locally certified primary sources fix the current boundary:

- Rueß et al., arXiv:2607.21651, Theorem 1.1, state and certify exact
  two-hidden-layer representations for every `n <= 10`; the public `MAX9`
  certificate has 337 terms. See `literature/papers/2607.21651.txt`, lines
  488--518.
- Wang and Basu, arXiv:2608.25221, explicitly acknowledge the Rueß `MAX9`
  and `MAX10` results. Their different degree-four `MAX9` system has 51,984
  constraints and 210,540 variables and was computationally inaccessible to
  their resources. See `literature/papers/2608.25221.txt`, lines 351--377.

Therefore G-0115 is not a new representability theorem and is not more compact
than the public 337-term certificate. Its possible contribution is the
restricted inherited-support statement and the much smaller derived candidate
family. Comparing family sizes across the two papers is only suggestive,
because their quotienting and semantic systems differ.

My calibrated assessment is:

- **Correctness confidence:** high for the exact bounded identity.
- **Novelty confidence:** low-to-moderate until an expert literature audit
  checks whether inherited-support/lift-span containment is already explicit.
- **Generalization confidence:** low. There is one positive arity transition
  and no frozen coefficient law.
- **MAX11 progress:** indirect only. The result keeps the lift route alive but
  does not yet reduce the unresolved `MAX10 -> MAX11` coefficient problem.

## Findings and obligations

### F1 — Overstated semantic independence (material evidence defect)

The existing `verify_compiled_full_max9.py` and
`verify_unrestricted_degree4_max9.py` avoid solve artifacts but share the
producer's semantic kernel. Their reports should say “matrix/solver/compiler
independent replay using the bound semantic kernel,” not “clean-room semantic
verification.” The literal replay in this review is the countermeasure.

### F2 — Easy novelty overread (claim-boundary defect)

The 395-term result can sound like a new `MAX9` solution, but `MAX9` and even
`MAX10` were already solved. Any public claim must lead with the restricted
MAX8-lift-span containment and say that novelty is unadjudicated.

### Required before stronger promotion

1. Obtain T2 or human mathematical review of the certificate semantics and
   the support-family statement.
2. Run a focused primary-literature novelty search on inherited-support,
   one-edge lift spans, and certificate transport before claiming novelty.
3. Produce a source-local, relabel-equivariant coefficient rule frozen before
   evaluation at another arity. Refitting another linear system is not
   transport evidence.
4. Require an exact held-out cross-arity positive—ultimately `MAX10 -> MAX11`
   for the campaign goal—before using “mechanism,” “recursion,” or “induction.”

## Reproduction commands

```bash
g++ -std=c++20 -O3 -march=native -fopenmp -Wall -Wextra -Werror \
  artifacts/reviews/G-0115-compiled-identity/literal_orbit_replay.cpp \
  -o /tmp/g0115-literal-orbit-replay

python artifacts/reviews/G-0115-compiled-identity/run_literal_orbit_replay.py \
  --certificate artifacts/math/G-0115/unrestricted_full_semantic_certificate_v1.json \
  --helper /tmp/g0115-literal-orbit-replay \
  --expected-helper-sha256 5bb5ad8296814bb92e354d1e0da3feb29743131ad4a2ebdc933d64040c499289 \
  --report /tmp/g0115-literal-degree4.json \
  --claim-boundary 'Exact degree-four MAX9 identity in the G-0115 lift span only.'

python artifacts/reviews/G-0115-compiled-identity/verify_lift_support.py \
  --report /tmp/g0115-lift-support.json
```

## Audit integrity and anti-ceremony disposition

The review report is a process artifact, but it passes the creation gate: the
consumer is the root research lead; it gates whether G-0115 is promoted; it
addresses the actually observed shared-kernel independence defect and novelty
overread; and it retires from the active decision path when superseded by a T2
or human referee report. The executable verifiers are evidence-producing
enablers, not status machinery.

For the bounded window of this review: `USER=0`, `ENABLER=2`, `PROCESS=1`,
`UNKNOWN=0`. There is no shipped end-user product; the user-visible research
outcome is a defensible exact-identity verdict. Without the process item, the
mathematics would be unchanged but the operator could overpromote it. No plan
or tracker work substituted for the literal replay.

Honesty inventory, checked against this directory's diff, commands, reports,
and the cited author artifacts:

1. No test or gate was weakened (checked: only new verifier/report files).
2. No mock, stub, or fixture was introduced (checked: literal certificate input).
3. No golden was regenerated (checked: new exclusive-write reports only).
4. No validator relaxation or suppression was added (checked: diff and `-Werror`).
5. No demo path or environment branch was added (checked: verifier sources).
6. No zero-run green was used (checked: exact positive counts in all reports).
7. No unrun command is cited as observed (checked: recorded commands in this review turn).
8. No replay is presented as T2/live proof (checked: verdict explicitly says T1).
9. No failure is buried (checked: shared-kernel defect and novelty boundary lead the report).
10. No cited stderr was silenced (checked: compile and verifier invocations).
11. No tracker item was closed or laundered (checked: no `br close` or equivalent).
12. No frozen claim was edited to fit output (checked: author preregistrations unchanged).
13. No swarm item was closed in this review (checked: no tracker mutation).
14. No subagent was dispatched from this review (checked: collaboration state).
15. No agent report was accepted as final evidence (checked: literal re-execution and source audit).
16. No pane farmed refusal/guard work in this bounded review (checked: solo audit scope).
17. No agent agreement was counted as independent confirmation (checked: lineage inspection exposed the opposite).
18. No result denominator was chosen after observation (checked: full serialized terms and all represented permutations).
19. **Yes:** the inherited word “independent” initially concealed a shared
    semantic lineage. It was corrected in this report, disclosed immediately
    to the root lead, and countered by a no-import literal replay. This is the
    catalog's pseudoreplication/proof-class-inflation failure mode (RH-2).
20. The strongest re-executable evidence is the literal degree-four replay,
    paired with the known-answer public control and three planted mutations.

Disposition for item 19: corrected on the record; disclosed to the operator;
and encoded as the concrete countermeasure “semantic independence requires a
separately implemented literal evaluator, not merely a new wrapper around the
same kernel.”
