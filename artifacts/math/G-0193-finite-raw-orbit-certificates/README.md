# G-0193 — finite raw-orbit certificates for the 17 mass-four identities

## Result

The 17 frozen support-six relations certified globally in G-0189 admit exact
proofs before primitive-direction normalization.

- For columns `12,17,21,24,68,72,75,82,90,91,108,117,121,122`, the three
  positive atoms and three negative atoms have identical multisets of raw
  back-degree words over all `11!` vertex orders.  In every raw-word fiber,
  send the `k`-th positive occurrence in lexicographic `(q_sequence, pi)` order
  to the `k`-th negative occurrence.  This gives an explicit bijection of
  `3 * 11! = 119,750,400` occurrences on each side.
- For columns `15,28,87`, first cancel occurrences with the same raw word on
  opposite sides.  The remaining signed multiplicity `R` satisfies
  `R(-w)=-R(w)` exactly.  The map
  `I(w,k,sign)=(-w,k,-sign)` is therefore a fixed-point-free sign-reversing
  involution.  Pairing `rho(w.x)-rho(-w.x)=w.x` leaves a linear moment; that
  moment and the independent base-linear residual are both exactly zero in
  all 11 coordinates.

All 17 controls formed by deleting the least-numbered positive atom fail the
required raw symmetry.

## Raw word

For a signed adjacency matrix `W`, extended by zero inactive vertices, and a
vertex order `pi`, the unnormalized word is

```text
w_r = W[pi_r,pi_r] + sum_{s<r} W[pi_r,pi_s].
```

The census applies no sign orientation, gcd division, primitive-direction
quotient, activity test, or ReLU normal-form folding.

## Reproduce

From this directory:

```bash
cargo build --release
target/release/g0109-normal-form-probe \
  ../G-0189-sparse-kernel-full-nf-scan/audit/g0109_92_input.json \
  /tmp/g0193_g0109_92_raw_output.json
python build_orbit_certificates.py \
  --raw-output /tmp/g0193_g0109_92_raw_output.json
```

Expected SHA-256 values:

```text
raw output   ff8dc580fdb49d9664b7437d4f5647ccecf072b7a62b42fee46b7a897ff3e8aa
certificate  17723714febbd841a923588577e6aaae680314ba7d4b35be098b14c5487a4768
probe source 7ca4718cbcf926e19c8463a55e4608d1aab9288de63d7e997f88c87fb4c5b06f
builder      7da42458ef7dec98792d10fea053114d96d299469b4f51c4ac85466c732e3313
```

The 132,265,318-byte raw output is deliberately regenerated rather than
committed.  The compact certificate is in
`results/orbit_level_certificate_v1.json`.

## Claim boundary

This is an exact finite proof for the frozen `n=11` relations.  The common
fiber-rank construction is census-defined; it is not a local graph bijection,
a parameterized theorem, a novelty claim, or a MAX11 result.
