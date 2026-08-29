# G-0049 verifier adversarial audit

## Verdict

`PASS` for the frozen G-0046 candidate's declared scope, conditional on the
separate full replay completing.  There is one concrete `FAIL` outside that
scope: the nominally generic semantic routines mishandle signed loops.  That
bug cannot affect this relation because all 7,100 active graph pairs are
validated as loopless five-edge/five-edge pairs, and the two pure common-base
loop/nonloop vectors are handled explicitly.

This audit does **not** claim that the serialized relation passes the long
global replay.  It audits false-pass risk in the verifier.  A successful run
would establish two modular normal-form identities for the displayed support,
not a rational or real identity.

Pinned subject SHA-256:

```text
0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04
```

## Required checks

| check | verdict | reason |
|---|---|---|
| subset-DP permutation semantics | `PASS` for loopless inputs; `FAIL` for loops | For a loopless signed graph, appending vertex `v` after lower set `S` emits exactly `sum_(u in S) W[v,u]`, the coefficient of the coordinate receiving `v`. Literal permutations agreed on 523 exhaustive small pairs and 172 random pairs through `n=7`. Lines 1064--1089 omit `W[v,v]`, so loop directions are wrong. |
| orientation / inactive ordered-cone hinges | `PASS` | With `sum h=0`, `h.x=-sum_k prefix_k(h)(x_(k+1)-x_k)`. First-nonzero-positive orientation makes all-nonnegative prefixes exactly the vanishing-ReLU case. Otherwise the hyperplane meets the chamber interior. Negative raw words receive the correct `ReLU(-g h)=ReLU(g h)-g h` linear correction. |
| exact-labelled signed-W cache | `PASS` in fixed five-loopless-edge scope | `Phi(A,B)=U_5^E+sum_sigma ReLU((B-A)_sigma.x)`. `U_5^E` is universal, so common loopless edges may cancel from `W` without losing the linear part. Replacing `W` by `-W` changes the ReLU sum by the fully symmetrized branch difference, which is zero. Independently, the frozen active set has 7,100 distinct keys for 7,100 pairs, so no cache merge is load-bearing in this run. |
| CRT aggregation / projection | `PASS` | Coordinatewise CRT is a ring isomorphism because the primes are distinct. Aggregating modulo their product and then projecting is exactly separate aggregation modulo each prime. 10,000 randomized weighted-coordinate checks passed. |
| complete normal form on all `R^11` | `PASS` for the displayed fully symmetrized loopless pair atoms | Full symmetrization makes every atom invariant under coordinate permutations, so the ordered chamber suffices. Every retained primitive hinge has a hyperplane meeting the chamber interior; a generic point on it isolates its gradient jump from every other primitive hyperplane. Hence hinge coefficients and then the linear vector are complete coordinates. Continuity extends equality from chamber interiors/boundaries, and symmetry extends it globally. |

## Concrete loop counterexample

Take `n=3`, left branch `{(1,1)}`, right branch `{(2,2)}`, and ordered
`x=(0,1,3)`.

- Literal right-minus-left words over `S_3` are the six permutations of one
  `-1`, one `+1`, and one zero.
- `direction_histogram` instead returns `{(0,0,0): 6}` because line 1087 uses
  only the lower-set sum; its own literal reference at line 1110 separately
  adds `weights[v][v]`.
- The resulting verifier normal-form value is `8`; literal symmetrized atom
  evaluation is `14`.

The signed-W cache is also not valid across differing loop/nonloop common
bases without recording the base type.  At the same probe, a zero-W common
loop atom evaluates to `8`, while a zero-W common nonloop atom evaluates to
`14`.  G-0049's support parser excludes loops and its `5E`/`5L` bases remain
separate, so neither counterexample reaches the frozen candidate.

## Independent evidence

`tiny_n_differential.py` uses literal coordinate permutations rather than the
campaign's subset DP.

- 523 exhaustive loopless ordered pairs (`n=2..4`, branch sizes one/two):
  exact histogram, complete normal form, and signed-W cache groups all agree.
- 172 deterministic random loopless pairs: 120 at `n=5`, 40 at `n=6`, and 12
  at `n=7`, with branch sizes through five: all agree with literal evaluation.
- 230 zero-sum directions: ordered-cone inactivity classification agrees with
  the independent prefix-sum derivation.
- 10,000 randomized CRT weighted coordinates: all projections agree.
- G-0049 `--self-test` and `--preflight-only` both exit zero.
- Independent frozen-support scan: 7,100 active pairs, all `(5,5)`, zero loop
  occurrences, 167 pairs with one common loopless edge, no repeated edge within
  a side, and zero exact-labelled signed-W cache collisions.

Audit harness SHA-256:

```text
ed705eb4159dd280679127f0b59046f907a2971c7c74b34994f97e0211919e97
```

## Claim boundary

The residual target used by the code is `11! * x_(11)` on the ordered
chamber, i.e. `11! * MAX11`, not literally coefficient-one `MAX11`.  Since
both primes and `Q` make `11!` invertible, this normalization does not change
span membership, but it should be named precisely.

A two-prime global pass is still only congruence of every integer primitive
hinge and linear coordinate at the two selected primes.  It does not imply an
exact `Q`/`R` relation; it does not prove the all-tree family complete; and it
does not address arbitrary two-hidden-layer networks.  The verifier's own
top-level claim boundary states these limitations correctly.
