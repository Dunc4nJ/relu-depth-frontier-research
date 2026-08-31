# G-0118 — exact early-prefix iteration-1 member

## Exact bounded result

The preregistered prefix shortcut found a rational member of the 313-row
iteration-1 system.  Starting from the 115-column G-0113 panel basis, exact
left-separator column generation added sequences 98 through 104.  The selected
rank rose from 115 to 122, after which adjoining the target did not increase
rank.

After denominator clearing, 99 coefficients are nonzero.  Every nonzero term
has sequence at most 104, even though three high-sequence panel-basis columns
were admitted by the frozen subset.  Exact arithmetic replayed all 301 panel
rows, all eleven ordered-cone linear rows with target `(0,...,0,11!)`, and the
first global hinge row `(0,0,0,0,0,0,0,0,1,-5,4)`.  Adding one unit to the
first nonzero cleared coefficient breaks the replay.

The producer was rerun to a distinct output path.  Removing wall time and peak
RSS gives an identical decision projection, including every separator,
selected sequence, coefficient, scale, and exact-row receipt.

## Evidence

```text
bad55cb45134cfdab3be86b3d3c676807acb402d69b6d37d0af59767152e531c  prefix_exact_cegis_v1.json
b5aeb50c9190c7f2f7fe453c5326b5fa780794029447a49f32d8cb468cec147f  prefix_exact_cegis_recheck_v1.json
6a152c1fbfe72101affeff05aea35367a0ae14d293c633c13f51ec7b260d14bf  prefix_exact_cegis.py
3292a64a7ee811a03bef2b0d41b3df9c809d11ebd931af1351ff5f68ccd18107  PREFIX_EXACT_CEGIS_PREREGISTRATION.md
a6f82b9f0d17e05d8cfb8a82d726d0a5cc163c540c89ddfa160e839e01a0d850  IMPLEMENTATION_BINDING_CORRECTION.md
d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde  first 192640000 cache bytes
```

## Claim boundary and next gate

This is an exact finite-row member, not a global identity or MAX11 theorem.
It is stronger than the previous 92-term seed because it also satisfies the
complete linear target and the first observed global residual, but the global
normal form contains many more hinge directions.  The candidate proceeds now
to complete two-prime modular replay; modular zero then requires BigInt exact
replay, while any nonzero residue exactly refutes this candidate and supplies
the next CEGIS row.

