# G-0113f preregistration — exact all-column separator replay

Registered while the corrected modular scan was still below 20,000 records,
before either slice target decision and before exact-Q postprocessing.

This branch runs only if the frozen exact postprocessor returns a primitive
integer separator for the retained span.  It must refuse member outputs,
modular disagreement, missing scan completion, binding drift, or non-decimal
separator data.

The verifier reuses the frozen G-0116 evaluator source and scans all 163,740
records sequentially under an explicit 12-thread Rayon pool for fixed-colour
assignments.  For every exact 301-entry `i128` vector it must:

1. reproduce both complete ordered vector hash streams from the corrected scan;
2. reproduce all eight independent control-vector hashes;
3. pair the vector with the arbitrary-precision primitive integer separator;
4. continue through the full stream even after a nonzero pairing, retaining the
   first failure and the total failure count.

It must also pair the separator with the exact frozen target and reproduce the
nonzero pairing reported by the exact postprocessor.  Only zero pairings for
all 163,740 columns plus the nonzero target pairing yield
`PASS_EXACT_ALL_COLUMN_SEPARATOR`.

That result proves nonmembership only for the enumerated degree-five
source-derived DISJOINT plus SHARED_DISTINCT family on the finite witness panel.
It does not prove completeness of that family, rule out unrestricted
two-hidden-layer networks, or settle MAX11.  Any nonzero candidate pairing
rejects the proposed separator as an all-family witness and is retained as a
counterexample for another exact-span round.
