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
`n <= 11`; use it on a sampled certificate at large `n` because its work is
factorial.

```bash
cargo build --release
cargo test --release

target/release/max11-verify11 verify \
  --certificate ../../literature/repos/max-relu-certificates/certificates/certificate_8_3.json \
  --threads 4 --literal-check --output n8-report.json

target/release/max11-verify11 analyze \
  --certificate synthetic-n11.json --threads 16 --output timing.json

target/release/max11-verify11 sample \
  --certificate certificate-n11.json --terms 20 --seed 20260902 \
  --output certificate-n11-sample20.json
target/release/max11-verify11 analyze \
  --certificate certificate-n11-sample20.json --threads 4 --literal-check \
  --output certificate-n11-sample20-literal-dp.json
```

`verify` writes its report and exits nonzero when the identity fails. `analyze`
writes the same exact report but returns success for intentionally failing
negative controls and timing inputs. Outputs are create-new and never silently
overwritten.

Certificate verification is input-memory bounded. It streams the file twice:
the first pass validates every term and fixes one exact common denominator; the
second holds at most `--threads` terms, computes those columns in parallel, and
merges them into one exact accumulator. When every coefficient repeats the same
textual denominator (the dense-lift case), that denominator is parsed only once
and each second-pass numerator is already its denominator-cleared integer. The
root object must use the canonical project order, with `n` before `terms`.
Sampling is streaming as well, so it does not load a multi-gigabyte source.

For a deterministic large-coefficient stress input:

```bash
target/release/max11-verify11 generate-synthetic \
  --n 11 --terms 2000 --branch-edges 5 --loopless --seed 20260903 \
  --coefficient-digits 100000 --structure-pool 1 \
  --output synthetic-n11-bigcoef.json
```

This produces independently random signed 100,000-digit numerators over one
random shared 100,000-digit denominator. `--structure-pool` bounds the number of
distinct structural columns while still evaluating every term. General rational
inputs use an exact common multiple of all denominators. Accumulators use
checked `i128` values with automatic `BigInt` promotion. No floating tolerance
or modular prime is used.

This tool checks one supplied finite certificate. A positive exact MAX11
certificate would settle existence, but a failed or synthetic input says
nothing about MAX11 membership or any unrestricted lower bound.
