# G-0070 — joint zero-high quotient gate

## Decision this gate makes

G-0068 certified 526 natural single-edge mass-five columns whose complete
degree-five-only normal form is exactly zero.  Their lower-degree normal forms
can still cancel each other and the existing lower-mass basis.  G-0070 tests
all 526 jointly against the exact rank-1,288 S1 hinge/Lambda span.

The direct matrix is

```text
N = [1,288 exact S1 pivot columns | reconstructed unique zero-high columns]
```

on all 99,858 primitive degree-four rows.  Because the 70 exact dependencies
inside the original 1,358-column S1 family have also been replayed with zero
Lambda residual, replacing S1 by its pivots preserves both its hinge span and
its target coordinate over Q.

The primary question is whether `ker(N)` contains a vector with nonzero Lambda.
Such a vector is the shortest current path to a MAX11 identity: lift it over Q,
replay every hinge and target coordinate exactly, correct the remaining linear
normal form, compile, and globally replay the two-hidden-layer network.

## Frozen primary protocol

The script rebuilds every selected pair, exact full normal form, degree-five
vanishing condition, Boolean charge, and semantic digest afresh.  The G-0068
structure artifact supplies only the ordered class manifest and frozen
cross-checks.  This is not clean-room semantic independence: both G-0068 and
G-0070 call the same hash-bound G-0049 normal-form engine, while the separate
alternating-cycle verifier independently supports the zero-high selection.

It then:

1. regenerates the exact S1 integer semantics and its rank-1,288 Q certificate;
2. deduplicates only identical complete candidate normal forms;
3. forms one common deterministic signed CountSketch of the direct integer
   matrix, with 4,096 buckets and seed
   `max11-g0070-direct-s1-plus-zero-high-v1`;
4. ranks that same integer sketch modulo 1,000,003 and 1,000,033;
5. if neither prime is full rank, replays every proposed sketch kernel on all
   complete sparse rows, adds violating source rows, and finally streams all
   99,858 original rows while retaining an explicit source-row basis;
6. compares matrix rank with rank after appending the exact Lambda row.

The one-sided bridge is exact: full column rank after left sketching modulo one
prime implies full column rank of the integer matrix over Q.  Sketch deficiency
is never promoted.  The complete source-row fallback may prove full rank from
an explicit nonzero modular minor, but any potent modular circuit remains only
a candidate until exact-Q lifting and global replay.

## Preregistered outcome classes

- `FULL_ZERO_HIGH_BLOCK_INJECTIVE_MODULO_EXACT_S1_OVER_Q`: one sketch or
  complete-source minor has full column rank.  The primary 526-column block is
  retired, but the 252 structural mass-four base semantics must still be
  appended before any registered-natural-family claim.
- `POTENT_MODULAR_CIRCUIT_DISCOVERED_PENDING_EXACT_Q_LIFT`: a complete-row
  modular kernel has nonzero Lambda.  Freeze the coefficients and immediately
  perform multi-prime alignment, rational lift, exact replay, and compilation.
- `DEFICIENT_MODULAR_QUOTIENT_PENDING_EXACT_Q_LIFT_OR_NO_GO`: complete modular
  deficiency without a promoted construction.  Do not call this a rational
  no-go; align/lift the kernel or build an exact rational dual.

## Controls and frozen hash

The self-test exercises original-row basis selection, signed modular reduction
before unsigned conversion, explicit nonzero minors, direct-versus-Schur rank
and Lambda identities, a full-rank CountSketch, a dependent-column common-map
plant and coefficient mutant, complete sparse replay, and CEGIS source-row
repair.

```bash
.venv/bin/python -B artifacts/math/G-0070/joint_zero_high_s1_quotient_gate.py \
  --self-test

.venv/bin/python -B artifacts/math/G-0070/joint_zero_high_s1_quotient_gate.py \
  --preflight-only --workers 8 --sketch-buckets 4096 \
  --minimum-available-gib 16
```

Frozen pre-outcome script SHA-256:

```text
0e24f192d3f467e992d6cfa31f9534247d72ced597aa12d225287e615fbff27e
```

The primary run, forbidden until the preregistration commit is pushed, is:

```bash
.venv/bin/python -B artifacts/math/G-0070/joint_zero_high_s1_quotient_gate.py \
  --run --workers 8 --sketch-buckets 4096 --row-block 2048 \
  --cegis-rounds 8 --minimum-available-gib 16 \
  --output artifacts/math/G-0070/joint_zero_high_s1_quotient_gate_v1.json.gz
```

The current preflight estimates a conservative 1.44 GiB peak and passes the
16-GiB availability latch.  No registered-subject outcome existed when this
README and EXP-0009 were frozen.

## Claim boundary

This gate covers only the 526 G-0068 zero-high natural representatives modulo
the exact S1 span.  It omits the structural mass-four appendix by default and
covers no other mass-five atoms, higher signed masses, asymmetric atoms, or
unrestricted two-hidden-layer networks.  A modular potent circuit is discovery
evidence, not a solution, until exact-Q and compiled-network replay both pass.
