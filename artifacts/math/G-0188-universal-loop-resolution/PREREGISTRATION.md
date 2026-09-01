# G-0188 freeze — universal orbit-identity deletion theorem

Frozen at `2026-09-01T11:03:09Z`, after exploratory base-dimension replays
suggested the theorem but before a source-bound clean promotion replay. This is
a post-discovery verification freeze.

## Candidate theorem

The frozen candidate is `theorem_candidate.json`, SHA-256
`ff57717365cb852b673926953390f144df1c8113662598fc1cc7bbee731ee839`.

For a fixed signed pair-max graph template (G), let (Phi_{G,n}) be its raw
full-(S_n) orbit symmetrization, with inactive-label multiplicity and the
frozen degree-five nonloop padding convention. The candidate deletion lemma is

\[
\Phi_{G,n+1}(x_1,\ldots,x_{n+1})
=\sum_{j=1}^{n+1}
  \Phi_{G,n}(x_1,\ldots,\widehat{x_j},\ldots,x_{n+1}).
\]

Consequently, an exact identity among templates using at most (K) labelled
vertices propagates from its base case at (n=K) to every (n\ge K). The
candidate applies this once to the fixed G-0182 identity, giving every
(n\ge6), and to the fixed G-0183 and G-0184 identities, giving every
(n\ge7).

Exploratory scripts had already observed exact base-case cancellation. They
are not the promotion gate.

## Frozen inputs

| object | SHA-256 |
|---|---|
| theorem candidate | `ff57717365cb852b673926953390f144df1c8113662598fc1cc7bbee731ee839` |
| G-0113 old-primary census | `093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8` |
| G-0179 STAR census | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0182 candidate | `b345639a47faf6b18d728648f891b913a55a7217a741b9537187da2dd3751d47` |
| G-0183 candidate | `df295599ac4e0f3fc94666198d9aa075b081866efa8a7e5dcf43a67edb76220e` |
| G-0184 candidate | `6ce618ddf34b00ec442e8a0d533eb3caef54b91245c6be626dcf3834125728bc` |
| G-0182 promoted (n=11) receipt | `f92635277b6d24c8c69eac2048af1152008ef5626ab96cc7a41403a7d520aa3d` |
| G-0183 promoted (n=11) receipt | `c3dd7eb92a906b3ad2563dea96f02ec3cbfb51777f34dc681840de7e6e6419e1` |
| G-0184 promoted (n=11) receipt | `5860b2b15c01b5951f76d82751451d450a62b03c4b9c9f576e96fbee62555898` |

## Fresh promotion gate

A verifier written after this freeze must:

1. bind every frozen hash and source schema, and map every STAR and primary
   coefficient in each candidate to its authoritative signed graph record;
2. treat the source graph records, not their (n=11) sequence names, as the
   universal templates, add explicit isolates only when needed, and require
   maximum active support exactly 6 for G-0182 and exactly 7 for G-0183 and
   G-0184;
3. independently enumerate all ordered chambers at the stated base dimension,
   reconstruct complete primitive-hinge and linear normal forms with exact
   integers, and require zero residual for each identity;
4. retain a canonical digest and census of the full per-record base-case table,
   not just the final zero;
5. reject a one-unit coefficient mutation separately for every identity;
6. directly check the next ambient dimension as a redundant implementation
   control;
7. prove the recurrence by injection counting: a fixed (k)-label injection
   appears in (n+1-k) deletion summands, changing multiplicity
   ((n-k)!) into ((n+1-k)!), and verify the same convention for the padding
   carrier;
8. re-hash all inputs at exit and refuse to overwrite output.

## Claim boundary

The candidate concerns three fixed graph-template identities. It does not
show that their relabellings span new orbit relations, classify other kernel
circuits, produce a parameterized loop-straightening family, prove the full
STAR quarantine, decide MAX11, establish ansatz completeness, or imply an
unrestricted two-hidden-layer ReLU lower bound.
