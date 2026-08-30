# G-0072 — direct global span gate for the asymmetric loop–edge family

## Decision this experiment makes

G-0071 showed that the labelled loop–edge lift has the intended MAX10 face,
and also that ordered-ridge commutators cancel tautologically after full
`S_11` symmetrization.  Local face bookkeeping therefore cannot decide the
construction.  This gate asks the global question directly:

> Does the exact MAX11 normal form lie in the span of the 3,754 full-`S_11`
> orbit classes induced by the 5,040 G-0071 seeds, after adjoining the two
> pure degree-five linear carriers?

The first registered pass uses a direction-keyed signed CountSketch on every
hinge produced by the complete exact normal form, while retaining all eleven
linear coordinates without sketching.  It is a kill-first gate:

- if the target is outside the sketched span, the corresponding modular full
  system cannot contain it at that prime;
- if the target is inside at both primes, the emitted coefficient vectors are
  candidates and immediately require a complete all-hinge replay.

Modular failure, even at two primes, is not an exact rational no-go.  Modular
success is not a MAX11 certificate.

## Frozen family

For every one of the 252 pinned full-support two-component MAX10 terms, every
anchor `k in {1,...,10}`, and both orientations, add `loop(k,k)` to one branch
and `edge(k,11)` to the other.  The 5,040 labelled pairs quotient to exactly
3,754 coordinate-relabeling/global-branch-swap classes.  One representative
of each class is a graph column.  The final two columns are:

- five common nonloop generators (`5E`);
- five common loop generators (`5L`).

The script reconstructs this subject independently and cross-checks G-0071's
raw-seed, orbit-sequence, and orbit-class-manifest hashes.

## Exact semantics and the loop trap

For a signed pair adjacency `W = B-A` and an ordering of the labels, the rank
word entry when vertex `v` is inserted is

```text
W[v,v] + sum(W[v,u] for u already inserted).
```

The diagonal term is essential: these are loop-inclusive atoms.  The shipped
self-test compares the subset dynamic program with brute-force permutations
on a loop-containing toy, checks branch-swap and coordinate-relabel
invariance, and rejects a loop-omission mutant.  This deliberately does not
reuse G-0049's loopless-only global replay path.

## Registered design

- Hinge map: 4,096 buckets, seed
  `max11-g0072-loop-edge-orbit-span-v1`, direction-keyed SHA-256 signs.
- Linear rows: all 11 retained exactly.
- Columns: 3,754 graph orbits plus `5E` and `5L`.
- Target: zero on every hinge bucket and
  `(0,...,0,11!)` on the ordered-cone linear coordinates.
- Fields: `1,000,003` and `1,000,033`.
- Failure condition: augmented rank exceeds column rank at either registered
  prime.  This kills that modular sketched construction but is not promoted
  to an exact-Q theorem.
- Escalation condition: target membership at both primes.  Freeze the two
  modular vectors, replay every complete primitive hinge and linear
  coordinate, align additional primes, then attempt exact-Q reconstruction
  and network compilation.

The CountSketch is only a left linear map.  Therefore a true full-system
solution must survive it; the converse is intentionally not asserted.

## Commands before registration

```bash
.venv/bin/python -B artifacts/math/G-0072/asymmetric_loop_edge_span_gate.py \
  --self-test

.venv/bin/python -B artifacts/math/G-0072/asymmetric_loop_edge_span_gate.py \
  --preflight-only --workers 8 --buckets 4096 --minimum-available-gib 12
```

The registered run additionally requires the exact committed script hash:

```bash
.venv/bin/python -B artifacts/math/G-0072/asymmetric_loop_edge_span_gate.py \
  --run --workers 8 --buckets 4096 \
  --seed max11-g0072-loop-edge-orbit-span-v1 \
  --primes 1000003,1000033 --minimum-available-gib 12 \
  --expected-script-sha256 <PREREGISTERED_SHA256> \
  --output artifacts/math/G-0072/asymmetric_loop_edge_span_gate_v1.json.gz
```

Pre-registration controls on script SHA-256
`59981f53d5c7ddbeef7cbd1d82b7b0df1289f692f593aca49aea2c925592521f`
pass, including literal full-permutation evaluation of loop-containing atoms,
exact recovery of the pinned MAX5 certificate, both carrier formulas, a
loop-omission mutant, modular member/nonmember controls, and a planted sketch
collision demonstrating that collisions can create false membership but not
false nonmembership.  The frozen matrix shape is `4107 x 3756` and the orbit
representative manifest is
`8780a36cb0630eea8211bec1f1d54f06361b22a49272379f8d8bc49b1bfebcbc`.

An exploratory predecessor check is frozen in
`inherited_weight_boolean_probe_v1.json`: simply copying each source MAX10
coefficient to all anchors and orientations already fails on the exact Boolean
Hamming layers.  This kills only that obvious weighting, not the arbitrary
3,754-variable span tested here.

## Claim boundary

This is a finite fully symmetrized pair-atom family.  It is not complete for
all degree-five graphical atoms, asymmetric nonsymmetrized blocks, arbitrary
real inner weights, or unrestricted two-hidden-layer networks.  A sketched
pass is not a full normal-form pass.  No outcome from this gate alone proves
or disproves the campaign target.
