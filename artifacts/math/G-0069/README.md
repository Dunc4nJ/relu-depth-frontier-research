# G-0069 — zero-high atoms versus the exact S1 quotient

## Result

The three genuine mass-five natural lifts found to vanish identically on
`D5 \ D4` do **not** produce a hinge circuit with the frozen S1 baseline.
Instead, their degree-at-most-four hinge classes are linearly independent
modulo S1 over `Q`.

| Same-family class | Seed Boolean charge | Full-orbit Lambda | Lower hinge support |
|---:|---:|---:|---:|
| 161 | 0 | 0 | 13,208 |
| 3,600 | 0 | 0 | 13,818 |
| 7,172 | -12 | -479,001,600 | 16,108 |

The executable rebuilt all three representatives from G-0049, independently
matched the complete G-0049 and G-0057 hinge normal forms, and reduced them
against the exact rank-1,288 G-0061 S1 baseline.  The three-column Schur
residual has rank three modulo both frozen primes.  Every one of the seven
nonempty candidate subsets has residual rank equal to its column count and
zero augmented gain at both primes.

## Exact characteristic-zero bridge

G-0061 proves that the baseline has exact rank 1,288 over `Q`.  G-0069 uses a
1,288-square integer baseline minor that is nonsingular modulo each prime.
At either prime, the three Schur residual columns add rank three, so the
combined integer matrix has modular rank 1,291.  Therefore its rational rank
is at least 1,291.  It is at most `1,288 + 3 = 1,291`, hence

```text
rank_Q(S1 plus classes 161, 3600, 7172) = 1291
rank_Q(the three classes modulo S1)      = 3.
```

This exact conclusion is stronger than merely observing the same result at
two primes.  In particular, no nonzero rational combination of these three
candidates can have its hinge vector canceled by the S1 baseline.

The nonzero displayed Schur deltas are not construction evidence because the
corresponding residuals are nonzero.

## Reproduction

```bash
source scripts/activate-toolchain.sh
python artifacts/math/G-0069/zero_high_s1_quotient_gate.py --self-test
python artifacts/math/G-0069/zero_high_s1_quotient_gate.py \
  --preflight-only --minimum-available-gib 20
python artifacts/math/G-0069/zero_high_s1_quotient_gate.py \
  --run --workers 4 --minimum-available-gib 20
```

The normal run regenerates the complete 1,358-column baseline semantics and
all three candidate semantics rather than trusting serialized matrices.  It
then replays the baseline dual, both pivot solves, every Schur residual, and
any potent circuit on all 99,858 rows.  This run found no potent circuit.

The frozen artifact's scientific digest was replayed after perturbing both
runtime-dependent semantic timing fields; the digest remained unchanged.
An independent clean-room audit found no outcome-changing indexing,
symmetrization, orientation, sign, rank, or exact-`Q` inference defect.

Frozen hashes:

```text
zero_high_s1_quotient_gate.py
  2396c8d4884d7cfee29a61b6ee51b1f352f5d444dd88342e4ec4ccf5e33d9a81
zero_high_s1_quotient_gate_v1.json.gz
  7c336f0e2081afb6bd61b9d07f18a0144f0d7233a97eafcd4d4d4135118b5099
canonical scientific payload
  b6dfe1852b1520be12f4f1d6c8380f7f8e32408c9d1ab4fab68fcfe25de4f1bd
```

## What this changes

The class-7,172 singleton route is exactly retired relative to S1, as is every
combination of the three currently known zero-high atoms.  The mechanism is
not retired: additional zero-high columns can have independent residuals that
cancel jointly.  The next decisive experiment is therefore the exhaustive
G-0068 census of all 11,542 genuine natural lifts, followed by one joint
quotient computation on every emitted zero-high column, retaining zero-charge
columns as possible cancellation directions.

This result says nothing about all mass-five atoms, asymmetric atoms, higher
signed masses, or unrestricted two-hidden-layer ReLU networks.  Even a future
exact potent hinge circuit would still require correction of all eleven
linear normal-form coordinates and an independent replay of the compiled
MAX11 network.
