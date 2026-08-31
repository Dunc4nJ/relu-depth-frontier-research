# G-0113e frozen rank-consumer core

Frozen after the deterministic rank addendum and before any all-record panel
scan or rank outcome was observed.

## Bindings

- addendum SHA-256:
  `ae4effe084ac0408c3d107a5c0437cff0c88792a3a1218cf9d3866efaf8962b3`;
- Rust library entry SHA-256:
  `1c35b9457dc2f7376b2aedfdc158ceef4c6a3368201d5bdb0b983e4f865e5e3c`;
- Rust rank core SHA-256:
  `006968bbf4f428e4fa492d06b61b43d64b25e5febcc0751ec81c07d90a399994`;
- Cargo manifest SHA-256:
  `b89e54aa1bcd20118083b52141851d7932949368724d81d561d5cba4a2234eba`;
- Cargo lockfile SHA-256:
  `9b894dc043760a1f9bf8e27a598a0e72169302638ae08f4d992e0a31ad130d14`.

The implementation admits only the two preregistered primes, checks the
301-dimensional dot-product accumulator bound, preserves annihilator-row
order, chooses the first nonzero annihilator coordinate, and retains exactly
the sequences that increase rank.

## Frozen controls

Command:

```text
cargo test --release
```

Result: `2 passed; 0 failed`.  At both primes, prefix-by-prefix decisions agree
with direct modular Gaussian elimination for zero, duplicate, rank-growing,
full-rank, rank-deficient-member, and rank-deficient-nonmember controls.

This freezes only the modular rank primitive.  It contains no G-0113 panel
vectors and makes no target-membership, global-identity, completeness, or
MAX11 claim.
