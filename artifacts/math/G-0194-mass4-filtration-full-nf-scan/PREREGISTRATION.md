# G-0194 outcome-blind contract: complete normal forms for the remaining mass-four filtration basis

## Question

What are the exact complete G-0179 ordered-chamber normal forms of the 23
directions in the certified G-0190 mass-`<=4` kernel basis that are neither
the three lower-mass directions nor one of the 17 mass-four directions already
certified as exact global identities by G-0189?

This is a classification experiment. It is not, by itself, a proof of
old-primary membership, MAX11 representability, or a neural-network lower
bound.

This contract becomes frozen only in the research-lead commit containing the
source and this file. No selected normal form may be computed before that
freeze and explicit research-lead authorization.

## Frozen inputs

- G-0190 sparse filtration basis JSONL:
  `7870fde3d67eb8eba0eaa10b924a4f8a717f9aa9e9e56acc54411c716edc2385`
- G-0190 row-major `5769 x 43` signed-`i64` basis binary:
  `bc949c3f95da084ab71d7c3aeea35469bb638fcea1ac0602bdb407aae6c3c798`
- G-0190 final filtration certificate:
  `1b1561f74ba266b9ddd72906dbc4f42c4222e56fd1a219c1f88c8f22a19ec055`
- G-0189 registered complete-normal-form result:
  `e90a79984c0dd7c582ca9dbbcb7f73b08c0c1505d0597bfcd98d44361ded8005`
- G-0179 STAR records:
  `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4`
- G-0180 quotient-expansion receipt:
  `6e7d58666b9a58d1ea68141595bdd1404a519f10e7f47068166c7d7a290864d5`
- G-0179 `src/lib.rs`:
  `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73`

The scanner requires the sparse JSONL to agree cell-for-cell with the complete
row-major binary. It also verifies the exact row-to-sequence map obtained by
deleting STAR sequences `1548,3140,4259,5656`.

## Frozen selector and structural expectations

The first 42 filtration columns are, in order, old sparse-basis columns

`[0,1,12,15,17,21,24,28,62,68,72,75,82,87,90,91,108,117,121,122,132,135,148,161,215,220,226,232,235,240,241,242,246,250,271,272,273,277,280,282,283,352]`.

Column 42 is the optimized missing direction
`B_24 + B_174 + B_235 - B_295 + B_345`.

- lower-mass filtration columns: `[0,1,8]`;
- G-0189 exact-identity filtration columns:
  `[2,3,4,5,6,7,9,10,11,12,13,14,15,16,17,18,19]`;
- selected columns: every integer from `20` through `42`, inclusive.

The scanner must reject unless selection gives exactly:

- 23 independent directions;
- 442 term incidences and 262 unique STAR records;
- support histogram
  `{8:1,10:1,12:2,16:9,17:1,18:4,22:2,24:1,34:1,65:1}`;
- maximum coefficient magnitude `3`;
- 53 non-unit coefficient incidences;
- aggregate coefficient `l1` norm `498`;
- maximum single-relation coefficient `l1` norm `76`.

## Frozen implementation

- `src/main.rs` SHA-256:
  `3c962a5f9ea43477bb8f987d85fd0a012af020db72c6848c0e25e0390c8c87ca`
- `Cargo.toml` SHA-256:
  `a90229b632ba2e682a3bde80ad4ba8db7772bc1c922bb310c2d58106b5dfe9ba`
- `Cargo.lock` SHA-256:
  `1c173e1d6ccd01438c170f51206a610056e2ce427751b22d78a70a109297e57c`
- release binary SHA-256:
  `7a405da561fcc2ea0362f90a4aba1dd7ed3f79df8a1694a66ec661cb7bbe3925`

Before the freeze, four outcome-blind unit tests passed, Clippy passed with
warnings denied, the locked release build completed, and the validation-only
mode accepted the frozen inputs and exact selector. Validation-only mode
created no result file and did not call `full_normal_form`.

The outcome-bearing mode requires the literal flag `--execute-frozen-scan`.
The separate `--validate-frozen-inputs` mode exits before any selected normal
form is computed.

## Frozen computation

1. Re-hash and semantically validate every frozen input.
2. Verify all 43 sparse columns against every cell of the bound binary, and
   validate every term's output-row/record-sequence correspondence and signed
   mass histogram.
3. Derive the selector from the bound G-0189 exact identities and then require
   the exact frozen tranche interval `20..42` and every structural count above.
4. Compute `g0179_star_loop_pricer::full_normal_form` exactly once for each of
   the 262 unique selected STAR records, using deterministic ordered
   collection.
5. Aggregate all 11 linear coordinates and every hinge coefficient with
   checked signed-`i128` arithmetic. Delete a hinge only after its exact sum is
   zero.
6. For each relation, record the complete residual, its canonical SHA-256, the
   `d[0]=0`/`d[0]!=0` split, and first exact witnesses.
7. For every one of the 23 relations, add `+1` to its first atom coefficient
   and require the complete mutant-minus-original residual—linear coordinates
   and all hinges—to equal exactly that atom's independently computed complete
   normal form.
8. Re-hash every input and the executing binary before creating the output;
   use no-overwrite creation followed by flush and `sync_all`.

For any original coordinate, the exact absolute accumulation bound is
`76 * (2^63-1) = 700976274800962961332`. For the hostile
mutant-minus-original intermediate, the bound is
`153 * (2^63-1) = 1411175921638780698471`. Both are far below the signed
`i128` maximum, and every multiplication, addition, and subtraction is also
checked dynamically.

## Decision rule

Each selected direction receives exactly one classification:

- `EXACT_ZERO_IDENTITY`: all 11 linear coordinates and all hinges vanish.
- `D0_NONZERO_HINGE_LEAKAGE`: at least one exact residual hinge has
  `d[0] != 0`. This proves that direction is not in the loopless old-primary
  span `O`.
- `NONZERO_RESIDUAL_WITH_D0_ZERO_HINGES_ONLY`: the residual is nonzero, but
  every residual hinge has `d[0]=0`. This remains compatible with membership
  in `O`; the scan does not decide it.

If all 23 directions are exact zero identities, then, combined with the
separately frozen G-0189 result, all 40 genuinely mass-four directions in the
G-0190 filtration basis have been classified as exact global identities.
Any stronger conclusion involving the three lower-mass directions must cite
their separate certificates. Mixed outcomes are reported relation-by-relation
without promoting a global theorem.
