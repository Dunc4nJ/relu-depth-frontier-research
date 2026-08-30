# G-0114 preregistration — final small correction span

Frozen after the exact MAX8 -> MAX9 failure of the 148-weight law and before
computing any MAX9 uniform-relation aggregate normal form.

```text
90519cde87e30c26c4d91b50873164b91b9e36b85ff55466491c07dd38e2011c  frozen_law_max9_v1.json
ea0ca13cc13848783e2ec2e6f30b9703852943315e2497c29c8017e4f72fc5b3  frozen_law_max9.py
```

The only correction space admitted is the pre-existing tied uniform relation
space from the first G-0114 test.  For the public MAX8 certificate form four
exact aggregates, each retaining raw multiplicity and source coefficients:

1. identical common nonloop added edges;
2. distinct nonloops sharing one endpoint;
3. vertex-disjoint nonloops;
4. at least one added loop.

`unequal = share + disjoint` and `all = common + share + disjoint + has-loop`,
so they add no span.  No incidence signature, source-specific scalar, fitted
feature, or sampled row is admitted.

Compute complete subset-DP ordered-cone normal forms, quotienting only by the
lossless full-atom incidence graph.  Decide over Q whether

```text
MAX9 in span(frozen_148_weight_output,
             common, share-one, disjoint, has-loop).
```

Membership must replay every linear and hinge row and survive a coefficient
mutation.  Nonmembership must provide an exact rational rank gap and primitive
integer row functional annihilating all five columns with nonzero MAX9
pairing.  Nonmembership ends this degree-raising-identity route: the frozen
law cannot be repaired by the only small symmetric correction class already
motivated before its failure.  It does not reject a large refitted incidence
model or the full MAX11 dictionary.

