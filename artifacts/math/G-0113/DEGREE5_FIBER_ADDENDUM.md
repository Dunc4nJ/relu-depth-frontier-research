# G-0113c preregistration addendum — preserve source fibers

Registered before executing `degree5_quotient_census.py` and before accessing
any MAX11 target rank.  After the original G-0113c preregistration, the
coordinating agent reported two further exact lower-arity controls: the
share-one and disjoint nonloop slices each span MAX7 separately, while tied
aggregation by relation (both universal and source-specific variants) excludes
MAX7.  This externally reported result was not independently reproduced here.

Accordingly, the census must not reduce an orbit to relation membership and a
single representative alone.  For every signed-W orbit and separately for
DISJOINT and SHARED_DISTINCT, its representative map must retain the complete
source fiber:

- every contributing source-term index in ascending order;
- that term's exact public rational coefficient;
- the number of raw added-edge pairs from that source term in the orbit;
- the lexicographically first added-edge pair witnessing that source fiber;
- the exact product of coefficient and raw multiplicity;
- the exact sum of those products across the slice.

The map must bind canonical hashes of the per-orbit fiber records and report a
global hash over all fibers.  The sum of all fiber multiplicities must replay
the registered raw count in each slice.  These fields preserve source-relative
incidence for a later solve; they do not authorize tying coefficients, using
the inherited coefficient sums as a candidate identity, or evaluating a
MAX11 target.
