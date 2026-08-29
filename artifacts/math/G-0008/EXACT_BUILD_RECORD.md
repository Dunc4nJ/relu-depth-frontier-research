# G-0008 exact cut rounds 1--3 build record

Date: 2026-08-29

This record freezes the exact-integer/rational build before the finite-field
accelerator is hardened further.  Generator SHA-256:

```text
a1471bf2dd5fe9bdf42b3062e7cdf96d1eaaee5eac88b13f0d93fd657d3edc3a  build_cut_matrix.py
```

Environment: CPython 3.13.7, NumPy 2.5.2, python-flint 0.9.0.  The frozen
G-0006 inputs are committed at `c4e9f60` and independently audited there.

## Round 1

```text
9896742748036aefb4014102631661e595f3bc1cd663980c1bcf7444b2dae476  cut_selection.json
b05bc038774244da3c55f8ba275f8015a9a540116b749900bd7025bff05ff000  cut_matrix.npz
c0194d5c51f0edfb5a1060b02f67318ceb2b2f7bf7535fb34e4561176ffdf204  cut_solution_p1000003.json
be10a20430b4ead07475f32533d856d3624d565fc081bd50d94bed14703c681c  cut_solution_residual.json.gz
```

The 512 selected hinge rows plus 11 linear rows raise the 364-orbit system to
rank 688 modulo 1,000,003.  An exact 678-term rational solution replays all 887
constraints, but its complete residual has 112,659 nonzero hinge directions.
An independent evaluator reproduced every residual row and coefficient.  The
original execution did not bind its then-current source bytes; its mathematical
content passed, while self-contained custody failed.  The current generator
replays the artifacts but is not falsely presented as their original producer.

## Round 2

```text
1dea9dca3708c158114684c363d6b2ddbc158db186e95334873b796f0926a231  cut_selection_02.json
18fb7105c0fb29035f1447f4b26f3d687bc59ab22dda5e56d6866fce04087b91  cut_matrix_02.npz
e727b2e8b6b2bd97cd6a76cb4975cb462e32495d4c529f5965844d5ae75de1c4  cut_selection_01_02.json
a84aab8e273e8470fd07828bb527d0ef326854c5de39cff849e7f751846290b4  cut_matrix_01_02.npz
98035cdce4421307a36c129622b8258ce42fb87d5e1164f8b30e2475f3901108  cut_solution_01_02_p1000003.json
91baa09d73539af08a933794b0ce2f4b2cd30b5dbc0537b962c0e8772e801f23  cut_solution_01_02_residual.json.gz
```

The second residual supplied 511 new primitive active directions, disjoint from
round 1.  The 1,398-by-9,804 accumulated system has rank and augmented rank
1,183 modulo 1,000,003.  Its 1,169-term exact rational solution replays every
selected equation.  Complete replay gives zero linear residual and zero on all
1,023 selected hinge rows, but 114,916 other hinge directions remain nonzero.
Thus only this candidate is falsified.

## Round 3 build (no solution in this record)

```text
4759eb0fd1f11e18fc949b2f4940a0a3a37c2e98efc6ea2d91a5938fb005a76d  cut_selection_03.json
caf28121667aeeeaa774a83fce27813144bfcc0b44591e610336ac80bde07ac2  cut_matrix_03.npz
5affe0a1fffdb953f2ce67692038a237d496531f41d4025b9a1c8f404a3a4ef9  cut_selection_01_02_03.json
d751b9b1b4e61dc3d24b47bb9c34ae6779934a8b1c07e88516236b2d7394c69f  cut_matrix_01_02_03.npz
```

Round 3 adds 2,041 new primitive active directions, for 3,064 distinct hinge
cuts total.  All 16 shards were assembled in exact class order.  The merged cut
block has shape 3,075-by-9,804 (3,064 hinge plus 11 linear rows).  Any modular
or rational solution is a later artifact and must carry its own source and
environment bindings.

## Claim boundary

Every result here concerns one frozen 9,804-class rational pair-atom family.
Finite cut-system feasibility is necessary but not sufficient for a global
identity.  Candidate residuals do not decide full-family feasibility.  No
result here implies either a construction or lower bound for unrestricted
two-hidden-layer arbitrary-real-weight MAX11 networks.
