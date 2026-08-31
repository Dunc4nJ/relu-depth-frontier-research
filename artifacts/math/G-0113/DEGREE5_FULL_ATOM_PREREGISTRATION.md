# G-0113d preregistration — uncancelled full-atom quotient refinement

Registered after observing the target-blind G-0113c signed-W census, after the
scope audit recorded in `SIGNED_W_SCOPE_CORRECTION.md`, and before computing
any uncancelled primary orbit count or MAX11 target rank.

## Purpose and frozen inputs

Refine the already enumerated 1,193,940 primary extensions into complete
graphical pair-template orbits.  The raw family and its DISJOINT (795,960) and
SHARED_DISTINCT (397,980) slices are exactly those frozen in
`DEGREE5_QUOTIENT_PREREGISTRATION.md`.  Bind:

- public MAX10 certificate SHA-256
  `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`;
- frozen v1 producer SHA-256
  `e0cb483d383021cba14730a4cac5b3f4c401106291b37f318233158ce3178edd`;
- frozen v1 map SHA-256
  `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48`;
- frozen v1 signed-W orbit counts: DISJOINT 133,449,
  SHARED_DISTINCT 94,843, union 163,740.

These signed-W outcomes are known inputs to this refinement.  The uncancelled
full-atom counts and their split-fiber distribution are not known at
registration.

## Exact full-atom certificate

Do not cancel common edges.  Encode all ten edge occurrences of a degree-five
pair as a colored incidence graph with eleven coordinate vertices, two
same-colored branch vertices, and one same-colored occurrence vertex per edge.
Each occurrence is adjacent to its branch and to its one loop endpoint or two
nonloop endpoints.  The `pynauty.certificate` of this graph implements exactly
S11 coordinate relabeling and global branch swap while preserving branch
membership, multiplicity, loops, and common-edge content.

For every full certificate, also compute the frozen v1 signed-W certificate.
Assert that the map FULL_ATOM -> SIGNED_W is a function.  Retain one
deterministic full-pair representative and, separately by relation slice, the
complete ordered source fiber: source term, exact source coefficient, raw
multiplicity, first witnessing added-edge pair, and exact coefficient-weight
sum.  Report how many full atoms lie over each signed-W class and bind the
complete split manifest by canonical SHA-256.

## Controls and decisions

- Regenerate all 48,642 common-apex STAR raw extensions.  The uncancelled
  certificate must reproduce the G-0090 known answer of exactly 27,623 pair
  templates; its cancelled projection must reproduce 23,147 signed-W orbits.
- Recompute and match the complete v1 primary signed-W hash set and the three
  frozen v1 counts above.
- Run S11 relabel, global branch-swap, multiplicity, and loop/nonloop
  metamorphic controls on the uncancelled certificate.
- Check 64 deterministic nonrepresentative pairs from each of STAR, DISJOINT,
  and SHARED_DISTINCT with NetworkX typed-incidence VF2.
- Any failed binding, raw count, projection function, known-answer control, or
  VF2 check makes the run INVALID.
- Otherwise classify the complete primary dictionary as TRACTABLE if it has at
  most 400,000 full-atom orbits and its deterministic gzip map is at most
  250 MiB; classify it LARGE above either bound.

This remains a quotient/tractability census.  It computes no MAX11 target
value, target rank, sampled fit, coefficient solution, identity, or
obstruction.  A future solver may quotient by FULL_ATOM certificates directly.
It may quotient only by SIGNED_W if it separately supplies a proved common-edge
basis treatment.
