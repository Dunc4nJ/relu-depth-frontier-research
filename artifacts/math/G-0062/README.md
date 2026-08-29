# G-0062 — cumulative 821-column modular quotient gate

## Exact family tested

Against the frozen 1,358-column G-0057 S1 baseline, the candidate columns are
ordered as follows:

1. sequence `92489`;
2. the 328 proper signed-mass-four atoms induced by the public MAX10
   certificate, in original certificate-term order;
3. the 492 G-0055 scheduled records with nonzero `pairing_numerator` that are
   not already in the 328-column block, preserving G-0055 priority-block
   order.

G-0055 contains 2,058 scheduled records and 524 nonzero-price records.  Its
overlap with the 328-column block is exactly 32 records—the first priority
block `A10-R001-B0001`—so the extension contains `524 - 32 = 492` columns.

- overlap-32 order SHA-256:
  `65aac698e49b796965f0e5fbd067886245d6c97b916e8e0c29d0400a3d8f66c9`
- new-492 order SHA-256:
  `996b1f3a41a363143a6ba1ff61b69bc4e87a2c3f4f76458a2851d9480289a142`
- cumulative-821 order SHA-256:
  `b5950af7c92da6d0eec708c2ba05ab0c8dbec5d7f7b4e9f0084aca86c4a9ba08`

The cumulative test is the primary gate.  The prefix and suffix tests are
diagnostics only: two families can each have augmented gain zero while their
union has gain one.  The executable includes that exact hostile regression.

## Result

The exact integer semantics were regenerated on the complete 99,858-row
direction universe.  The hash-bound G-0059 pivot profiles were reused; the
baseline RREF was not recomputed.  For each prime, the displayed pair is
`rank(R) / rank([R; delta])`.

| Family | Columns | p = 1,000,003 | p = 1,000,033 | Gain |
|---|---:|---:|---:|---:|
| frozen G-0059 prefix | 329 | 323 / 323 | 323 / 323 | 0 / 0 |
| new G-0055 suffix (diagnostic) | 492 | 485 / 485 | 485 / 485 | 0 / 0 |
| **cumulative family (primary)** | **821** | **805 / 805** | **805 / 805** | **0 / 0** |

No modular potent circuit exists in this ordered 821-column family at either
frozen prime.  Consequently there is no witness from this gate to lift over
the rationals.

## Boundary of the null

This is a two-prime finite-field statement about 821 selected proper
signed-mass-four columns.  It is **not** an exact-Q no-gain theorem, not a
census of all 132,728 proper mass-four atoms, and not a lower bound for
arbitrary-real-weight two-hidden-layer MAX11 networks.  Equal ranks at two
primes do not justify any of those inferences.

## Bound artifacts and replay

- G-0059 source commit:
  `0d2d1a4cbb44d326a4984333cffd1a2aa6ea8c1d`
- executable SHA-256:
  `997560bf21296b4c4f4f37e132fc0c263365294898ed6119152517a61f276875`
- gzip report SHA-256:
  `cc34ac9ced428307f43d03b86ba52e7722600a2d3db8e4362708b8831cb2f07d`
- deterministic scientific payload SHA-256:
  `328268979c29bc7c9ac33a9a0d26ca15d6e62a03aada232728a826de580e8d6a`

```bash
.venv/bin/python -B artifacts/math/G-0062/cumulative_821_quotient_gate.py --self-test
.venv/bin/python -B artifacts/math/G-0062/cumulative_821_quotient_gate.py \
  --check-report artifacts/math/G-0062/cumulative_821_quotient_gate_v1.json.gz
```

The scientific projection independently recomputes to the recorded digest
after recursively removing runtime measurements, worker counts, resource
preflights, and resource thresholds.  The self-test perturbs previously
unseen nested `*_seconds` and `*_gib` keys and requires the projected digest
to remain unchanged.
