# G-0075 result — generic four-level direct rank gate

## Registered outcome

The preregistered direct augmented-rank gate is **inconclusive**.

| panels | exact integer shape | rank mod 1,000,003 | rank mod 1,000,033 | rank mod 1,000,037 | augmented nullity |
|---:|---:|---:|---:|---:|---:|
| 64 | 8,140 × 8,108 | 5,513 | 5,513 | 5,513 | 2,595 |
| 128 | 15,820 × 8,108 | 6,877 | 6,877 | 6,877 | 1,231 |

No registered prime reached rank 8,108, so no nonzero 8,108-square
integer minor was emitted.  This outcome proves neither target membership nor
target nonmembership, supplies no MAX11 network, and is not an unrestricted
ReLU lower bound.

## What changed scientifically

The second 64-panel tranche added 7,680 direct rows but only 1,364 modular rank
dimensions.  The identical ranks at three primes make an accidental
prime-specific collapse less plausible, but they do not establish a
characteristic-zero rank upper bound.  The useful discovery is therefore a
large, stable finite-row quotient, not a theorem about membership.

Further blind panel sampling is low leverage.  The next discriminator should
regenerate the bound matrices while retaining their exact rows and report,
for each registered prime,

```text
r_A = rank(A),  r_N = rank([A|b]),  epsilon = r_N-r_A,
K = ker([A|b]).
```

It should first test whether all 1,378 G-0074 rows lie in the exact rational
span of the selected 460-row subsystem.  It should then use the surviving
right kernel as a Schur quotient: for any complete global row block `C`, only
`C K` can add rank beyond the direct system.  Exact gradients come first,
followed by the canonical oriented gated-facet coordinates in
`GLOBAL_FACET_FOLLOWON.md`.  Only an exact replayed left dual, a full combined
integer minor, or a globally replayed construction can support a promoted
claim.

## Bindings

```text
registered producer SHA-256: ba169bb9b3734c14d30afebba925a358e6f68a0cdd9734a30d78390438567bab
preflight SHA-256:           bbe4e8410e2d042deea2844aa7099f2601feaa201d903557ca09d5f16f2514e0
outcome SHA-256:             ec8f1f1213f9105a5aa51d1b842ac2dc331d82224157d598a7caf0af93425371
scientific payload SHA-256:  f55f4c23cb14fcf5974e527e4775183420c028fdf9a859f4febeb265405950da
64-panel augmented SHA-256:  24502cacddaa464c060288b08590dd028e4dbfa1d6a4c821d2fccb7b6e875c29
128-panel augmented SHA-256: f029fddb62924f2e6739396c58b81fbe7d393bad1b22bdec49819c4fa82a2184
```

The registered run used 16 workers and completed in 5,042.6 seconds.  Direct
row generation took 1,583.0 seconds for panels 1–64 and 1,594.7 seconds for
panels 65–128.  The three modular analyses took 401.6 seconds at 64 panels and
996.9 seconds at 128 panels.
