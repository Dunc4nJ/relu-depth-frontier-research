# G-0113c preregistration — arbitrary-edge degree-five quotient census

Registered before writing or running the G-0113c census producer and before
accessing any MAX11 target rank.  This is a target-blind tractability gate for
the MAX10-to-MAX11 analogue of the successful lower-arity family reported by
the coordinating agent.

## Frozen family

Load all 402 terms of the public degree-four MAX10 certificate whose bytes have
SHA-256
`10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`.
For a source pair `(L_T,R_T)` and unordered nonloop edges `e_L,e_R` on labels
`1,...,11`, form the degree-five pair

```text
(L_T + {e_L}, R_T + {e_R}).
```

The primary family requires `e_L != e_R` and has two raw strata:

- DISJOINT: `e_L` and `e_R` have no common endpoint, hence
  `402 * 55 * 36 = 795,960` ordered raw extensions;
- SHARED_DISTINCT: they share exactly one endpoint, hence
  `402 * 55 * 18 = 397,980` ordered raw extensions.

Their union therefore has 1,193,940 raw extensions.  Loops and identical
added edges are excluded from the primary family because the reported
lower-arity 58-term support used neither.  This exclusion is a search-priority
decision, not a theorem that those atoms are useless.

## Exact quotient

For every pair, cancel common edge occurrences between branches.  Encode the
remaining signed edge multiset as a colored incidence graph with:

1. eleven coordinate vertices in one color class, including inactive labels;
2. two branch vertices in one color class;
3. one occurrence vertex per surviving edge in one color class, joined to its
   branch vertex and to the one or two incident coordinates.

The `pynauty.certificate` of this graph is the exact semantic orbit key.  The
interchangeability of the two same-colored branch vertices implements global
sign reversal, while occurrence vertices preserve multiplicity and distinguish
loops by degree.  Thus a key represents a signed graphical hinge `W` up to
S11 relabeling and multiplication by `-1`, which is the correct column
quotient for an unrestricted rational span.

The producer must retain one deterministic raw representative for each key and
report, separately and jointly:

- raw count, unique signed-W orbit count, and class-size histogram;
- DISJOINT/SHARED_DISTINCT intersection and each slice's exclusive orbits;
- signed mass, active-vertex, loop, component, and cycle-rank strata;
- overlap with a regenerated common-apex STAR control consisting of
  `(a,11)` and `(b,11)` for all 402 sources and `a,b in {1,...,11}`;
- primary orbits outside STAR, and STAR orbits outside the primary union.

The representative manifest and orbit/class histogram receive canonical
SHA-256 digests.  A deterministic gzip JSONL representative map may be
written, but no 1.19-million-row raw map is required.

## Controls and method-disjoint checks

Before accepting the primary census, the same incidence certificate must
regenerate the complete G-0090 STAR family and reproduce exactly:

- 48,642 raw extensions;
- 23,147 signed-W orbits.

The source certificate must contain exactly 402 degree-four pairs.  Relabeling
and branch-swap metamorphic tests must preserve certificates; a changed edge
multiplicity and a changed loop/nonloop status must be rejected by at least
one frozen witness.  A deterministic stratified sample of nonrepresentatives
from both primary slices and the STAR control must be checked by NetworkX VF2
on the same typed incidence graphs.  These checks are diagnostic independence,
not independent T2 review of every canonical class.

## Decisions frozen before outcomes

- If any binding, raw count, metamorphic control, VF2 check, or G-0090 known
  answer fails, classify the run as INVALID and do not interpret the census.
- Otherwise classify the census as TRACTABLE if the primary union has at most
  400,000 signed-W orbits and its deterministic gzip representative map is at
  most 250 MiB.  Above either bound classify it as LARGE and recommend a
  topology-first column-generation strategy rather than a monolithic exact
  rank.
- Within a valid TRACTABLE run, rank future construction priority by exact
  novelty only: first the DISJOINT orbits outside STAR, then
  SHARED_DISTINCT outside STAR.  This is a computation-order rule, not
  evidence of mathematical efficacy.

No target values, target ranks, sampled fits, modular fits, or coefficients are
computed in this gate.  A successful census establishes only the size and
overlap of a finite source-derived dictionary.  It neither represents MAX11
nor obstructs unrestricted two-hidden-layer ReLU networks.
