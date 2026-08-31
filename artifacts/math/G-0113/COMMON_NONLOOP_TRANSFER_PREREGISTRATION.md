# G-0113c common-nonloop transfer verification protocol

Registered before writing or running the G-0113-specific transfer verifier.
No MAX11 target rank is part of this check.

Bind the following completed inputs:

- G-0113c signed-W map SHA-256
  `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48`;
- public MAX10 certificate SHA-256
  `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`;
- G-0027 theorem/enumerator SHA-256
  `92ce1d017a12ce9dc44c3f43103028dcfe635fa7ba9e8c1026c3d6ca8fe19f13`;
- G-0027 README SHA-256, frozen below in the execution record.

For every G-0113c primary orbit record and every stored source-fiber witness,
reconstruct the full degree-five pair and verify exactly:

1. both branches contain five edge occurrences;
2. every source and added edge is nonloop;
3. common-multiset cancellation leaves equal branch mass `s`;
4. the common multiset has cardinality `5-s`;
5. the record's signed mass and raw multiplicities replay;
6. exact source coefficients and coefficient-times-multiplicity fields replay.

Also verify the two raw relation enumerators contain only nonloop edges and
have respectively 1,980 and 990 ordered pairs per source.  These finite checks
bind the general G-0027 algebraic lemma to every raw member because no
unrecorded raw edge can be a loop.

As an implementation control, construct two degree-five pairs on seven labels
with the same cancelled signed pair and the same number of differently placed
common nonloop edges.  Exhaustively sum their pair-max values over all `7!`
coordinate permutations on a deterministic set of integer points and require
exact equality.  A loop mutant must disagree on at least one point.

Passing this protocol proves that the G-0113c signed-W quotient is sound for
the fully symmetrized primary loopless atom family.  It does not prove that
distinct signed-W orbits define distinct functions, that STAR's loop-bearing
records have the same transfer, or that the finite dictionary spans MAX11.
