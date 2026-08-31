# G-0113f frozen exact all-column separator fallback

Frozen before any target-membership or exact-Q outcome was observed.

```text
7a3c66661542474bab20a4ee3edf094d69ed50d792717ae1da6a119fbb0bc5f3  separator_verifier/src/main.rs
69fea246a4156f65c524c0823737259a066badb09533b6b5881a2d64b10d6f0d  separator_verifier/Cargo.toml
ac12dacacb55a29afdbc19a33e419f72d7eefb5358d9faa359f616ce866b2df4  separator_verifier/Cargo.lock
36665cc685185d6bd68f9be2dc41b94e5244b105755a562414259672803da942  PANEL_SEPARATOR_REPLAY_PREREGISTRATION.md
```

`cargo test --release` passed its arbitrary-precision sign/pairing control;
`cargo clippy --release --all-targets -- -D warnings` passed.  The verifier
parses separator coordinates only as decimal `BigInt` strings, recomputes both
complete scan hash streams, and does not stop at a failed column pairing.

This is a dormant finite-panel fallback.  It should not be run if the faster
frozen G-0117 residual-coordinate pricer provides the same exact all-candidate
annihilation check and bindings; no duplicate global normal-form computation is
needed.
