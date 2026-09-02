# `max11-verify11`

Exact independent-semantics verifier for the MAX11 campaign certificate JSON
format. It implements the pinned upstream verifier's ordered-cone normal form:
lexicographic `base/other`, `direction = other - base`, cone pruning, positive
gcd normalization, and target linear form `x_n`.

The main evaluator uses a subset dynamic program over vertex placements. Its
state is the complete back-degree word of `right - left`; loops, repeated
edges, common edges, and arbitrary equal branch sizes are supported. The
fully symmetrized left branch is computed analytically. A separate literal
mode enumerates every permutation and evaluates the two sides directly for
`n <= 8`.

```bash
cargo build --release
cargo test --release

target/release/max11-verify11 verify \
  --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_8_3.json \
  --threads 4 --literal-check --output n8-report.json

target/release/max11-verify11 analyze \
  --certificate synthetic-n11.json --threads 16 --output timing.json
```

`verify` writes its report and exits nonzero when the identity fails. `analyze`
writes the same exact report but returns success for intentionally failing
negative controls and timing inputs. Outputs are create-new and never silently
overwritten. Rational coefficients are denominator-cleared exactly; the
accumulator uses checked `i128` values with automatic `BigInt` promotion. No
floating tolerance or modular prime is used.

This tool checks one supplied finite certificate. A positive exact MAX11
certificate would settle existence, but a failed or synthetic input says
nothing about MAX11 membership or any unrestricted lower bound.
