# G-0007: Pair-atom structure and a MAX11 search ansatz

This artifact freezes an exact-arithmetic calibration study of the public
MAX9 and MAX10 pair-atom certificates and derives a restricted candidate
family for a future MAX11 search.

The strongest new result in this artifact is a reported exact computation
over the rationals: MAX9 is not in the span of all 739 two-colored,
full-support tree atoms of degree four. A mixed family consisting of
bridge-generated trees plus published non-tree corrections does contain
MAX9; the included
391-term certificate verifies exactly.

This does **not** solve MAX11. The proposed MAX11 family is a bounded search
ansatz:

    A_11^(<=4, loopless)
      = {(A,B): |A|=|B|=5, no loops, beta(G(A,B))<=4}
        / (vertex relabeling and global A/B swap).

The evidence motivating that family is retrospective MAX9/MAX10 structure,
so negative search results inside it must not be reported as global
impossibility results.

Files:

- REPORT.md: claims, evidence, limitations, and the MAX11 decision rule.
- PROPER_SUBSET_NO_GO.md: a short human proof ruling out linear lifts from
  proper-subset maxima.
- REPLAY.md: environment, ordered commands, and expected checkpoints.
- data/: exact MAX9 hybrid solution, certificate, and replay attestation.
- scripts/: enumeration, isomorphism, rank, and solve scripts.
- transcripts/: captured replay output.
- MANIFEST.sha256: hashes of every frozen file except the manifest itself.

Epistemic status: exploratory research artifact with exact computational
checks and run-isolated, provenance-keyed intermediate caches. It uses the
same upstream expansion kernel as the source
certificates and therefore is not an independent clean-room certification.
No campaign ledger was edited and no frontier claim is asserted here.
