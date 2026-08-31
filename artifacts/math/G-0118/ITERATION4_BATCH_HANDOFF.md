# G-0118 candidate-4 Batch32 handoff

## Certified outcome

The exact 316-row, 102-term candidate is not a global identity. Complete
two-prime replay processed all 3,585,323 normal-form hinge entries and
4,071,513,600 labelled permutations. All four accumulated CEGIS directions
replayed to zero in both fields, and both complete linear residual vectors were
zero. Of the 172,454 supported hinge directions, 172,430 had a nonzero residue
in at least one field.

The preregistered signed-lexicographic rule selected the first 32 nonzero
directions. The ordered selection receipt digest is

~~~text
78c3f84bfd8f4361d594cef39b7406f79c9e3f2fc7e93b21def6c2edfad950f8.
~~~

The first selected direction and residues are

~~~text
d = (0,0,0,0,0,0,0,0,2,-3,1)
residues = (469475727, 88067972).
~~~

The last selected direction and residues are

~~~text
d = (0,0,0,0,0,0,0,2,-3,0,1)
residues = (49815667, 685735519).
~~~

## Exact prices

iteration4_batch32_exact_prices_v1.json contains a direction-major
32 × 163,740 signed-i64 hinge matrix and the complete 163,740 × 11 linear
matrix. Its complete hinge and linear stream digests are

~~~text
c8446c3b2541e364529f5ee531534554bc99d758e022f75f3134c2bd3d9283f2  direction-major hinge stream
84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51  linear stream
~~~

Across the 32 rows, nonzero hinge coefficients range from 656 to 130,256
per row; the total number of nonzero matrix entries is 1,371,787. Per-row
maximum coefficients range from 40,320 to 777,168.

Two independent arbitrary-precision bridges dotted every exact row with the
candidate's 102 integer coefficients. All 32 exact values were nonzero and all
64 reductions reproduced the two recorded residues. The first
denominator-cleared exact residual is

~~~text
-5703892799919658490059922221725686307699370673780978850497132842536171588240320361770407843463279886049056.
~~~

The canonical stream of all 32 exact residuals is their base-10 strings joined
by LF bytes with a final LF. It is 3,431 bytes and has SHA-256

~~~text
98f507b0d4277018a7d704c951c1e6b3cac10243b59c3df407b5a195d0e9686b.
~~~

An independent bridge also verified that the complete linear value, after
subtracting 11! times target_scale, is exactly zero.

## Full-master continuation

The next exact solve may append these rows with target zero in their frozen
order, discarding only rows proved exactly rank-dependent on the existing
305-row system. It must reopen all 163,740 frozen columns using the completed
301-row cache and the exact batch rows. The large cache payload is intentionally
not committed; its small manifest binds the 788,571,840-byte payload.

## SHA-256 bindings

~~~text
54a329587786c8824e8eede13a6165983ecc64c27a7f758be9676583bd283feb  BATCH32_ITERATION4_PREREGISTRATION.md
728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b  prefix_exact_cegis_iteration4_v1.json
f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f  prefix_exact_cegis_iteration4_recheck_v1.json
c402c0c9e89c2d8a95fc8b40c44346f9eaeae3c2ade5a7662d97cda04680ad80  iteration4_batch32_global_modular_replay_v1.json
349e63a7a2f254a2b0d4c05a4ce4c088afa7ff859675876e2b8c3bac05b6547b  iteration4_batch32_exact_prices_v1.json
172be64103b9ebf7516514923c94bc7de8ee63bfc92a776e321c87c469a58db9  ../G-0117/src/bin/g0118_batch_modular_replay.rs
35cabc07a3e6a50366c584c737493b393b202092d64f0951a37dde4f515d3058  ../G-0117/src/bin/g0118_batch_coordinate_pricer.rs
2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6  ../G-0117/src/lib.rs
e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf  ../G-0117/full_family_cache_manifest_v1.json
da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b  ../G-0117/full_family_cache_v1.i128le
~~~

## Claim boundary

This is a certificate-backed refutation of candidate 4 and a batch of exact
finite-family CEGIS rows. It is not a proof that the reopened exact system has
a member, not a family-completeness theorem, and not a MAX11 result.
