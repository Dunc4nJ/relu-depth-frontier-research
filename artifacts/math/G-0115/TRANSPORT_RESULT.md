# G-0115 transport-law result — preregistered stop

## Outcome

The 395-term degree-four MAX9 identity is exact, but it does not expose an
eligible local coefficient-transport law in the preregistered families.

This is a scoped obstruction, not a functional nonmembership theorem. The
MAX9 identity remains valid. What failed is the attempt to reinterpret its
sparse solver support as a low-description source-local rule suitable for
MAX10-to-MAX11.

## Support and coefficient evidence

All 139,725 raw one-edge-per-branch lifts were regenerated with exact full-atom
and signed-`W` fiber reconciliation. Every signature was checked under two
simultaneous coordinate relabelings and global branch swap; deliberately
broken source-only and one-edge-only relabelings were rejected.

No preregistered local signature family isolates the 395 nonzero signed
classes:

```text
family       signatures   selected classes covered by pure signatures
coarse            2,122    62 / 395
incidence        12,653   255 / 395
radius1          31,613   378 / 395
```

The fitted coefficients are also strongly nonuniform: there are 262 distinct
ratios to the representative source coefficient, 317 distinct ratios to the
raw-fiber source sum, and nine selected classes whose raw-fiber source sum is
exactly zero. Of the 328 retained public-support classes, 177 retain the public
MAX9 coefficient exactly and 151 do not.

These facts reject a literal local-support explanation. They do not by
themselves reject functional cancellation among mixed signatures.

## Exact functional rank-cap decision

The preregistration allowed at most 64 independent fitted parameters and at
most 32 nonzero signature weights. Before fitting the MAX9 target, the coarse
functional family was tested on complete ordered-cone hinge semantics.

For each frozen aggregation convention, a 65-by-65 rational minor has exact
rank 65:

```text
raw sum             exact Q rank 65   minor SHA 132d49df63c4619a13b7a969111aaeac2006c22bd11e40b31bd60eed84896ab6
full-atom average   exact Q rank 65   minor SHA ceb22c0ae05119307d0bbfa63bd3d774b05603f9d9895361f7094211bfda2bf0
```

Thus the complete coarse family has exact rank at least 65 under both
conventions and exceeds the frozen cap. The 12,653 incidence signatures refine
the coarse signatures, and the 31,613 radius-one signatures refine the
incidence signatures, so both refined functional spans contain the coarse span
and inherit the same lower bound.

Per the preregistered stopping rule, no target membership fit was performed.
Continuing in a family already over the cap would produce a compressed solve,
not evidence for a low-description transport theorem.

An independent verifier replayed both serialized minors over Q and modulo
1,000,003 without importing the rank-gate producer or loading the 1.8 GB
semantic matrix. It recovered rank 65 in both cases; the raw-sum integer minor
also has exact integer-matrix rank 65.

## Evidence bindings

```text
1c276c26e16227fb0cef37910363a2db7364db24d2b8586a4c185ae07c531e49  TRANSPORT_LAW_PREREGISTRATION.md
a6472ae3aa0d146ac42d8479ef3b06a50b3ca0ceaf4dedb3896e4df93f223439  TRANSPORT_LAW_CONTROL_ADDENDUM.md
4e27a4c11fe4fa66708b8b1d59771c8902a4747329c5fcc6cb63fe59a66628ba  transport_support_probe.py
fedbbc7e845d8af20cfb0f6f71814f149193486234e5ec26535da3f67806be56  transport_support_probe_v1.json
5382220b3bf855fcaa6146395736d7279dd8935239eb5eae6ac58d4d934f1717  transport_functional_rank_gate.py
5b84d5ba45094c5603c127b0a632978de6e05e7684911d167b5246e16af28c9b  transport_functional_rank_gate_v1.json
4ecbf5bb26961fdaacb03da54b05134b48af842df0e8061c251b723ee00c2b90  verify_transport_rank_witness.py
6df6abc1e089b2237316f062ee8480006f8c961c48f88b9e1da8be1fb6c0c6bf  independent_transport_rank_replay_v1.json
```

## Claim boundary and prior update

This result rejects eligibility only for the frozen coarse/incidence/radius-one
source-local families and the two frozen aggregation conventions. It does not
prove those families miss MAX9, reject a different equivariant operator, or
decide MAX11.

The rational prior update is nevertheless downward: the 395-term MAX9 support
is more plausibly a sparse basis chosen by the exact solver than a visible
arity-independent local recurrence. MAX11 effort should pivot to a
statement-matched direct construction or obstruction rather than further
post-hoc fitting of this lower-arity certificate.
