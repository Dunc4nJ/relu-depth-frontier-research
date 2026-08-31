# G-0118 iteration-2 exact residual handoff

## Appended direction

The first canonical global hinge residual of the iteration-1 prefix member is

```text
d = (0,0,0,0,0,0,0,0,1,-4,3).
```

For the denominator-cleared 99-term certificate, its exact integer coefficient
is

```text
17306432986245829359126857284999367406350584104047326805750547562384183940065977315491866463260101120.
```

The corresponding reduced rational residual is

```text
72110137442690955663028572020830697526460767100197195023960614843267433083608238814549443596917088
-----------------------------------------------------------------------------------------------.
32201777340161904389140313580084037042798625698219646644648502134346701825607402897554036559
```

Independent red-team recomputation returned the same exact integer.  Reducing
that integer modulo the two global-replay primes gives 282,521,085 and
222,337,686, exactly matching the complete modular replay.

## Complete family row

`iteration2_residual_coordinate_v1.json` prices this direction exactly for all
163,740 frozen columns.  It contains every signed-i64 hinge coefficient and all
eleven linear vectors.  The hinge row has 2,861 nonzero values and maximum
value 161,280.  Its ordered signed-i64 stream digest is

```text
7252a7c025f560f6c71332d044ffee5fc8517d7f7a45e4c14b0bec7593f962af.
```

The unchanged all-linear stream digest is

```text
84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51.
```

This row is ready to append with target zero.  Iteration 2 must reopen the
complete 163,740-column family and solve over Q; restricting to the old 122
basis columns would not be a family decision.

## SHA-256 bindings

```text
5cceb8b6907e5b683d52ec3970a8ba8fd8675d03e4cba50386d99bf8c7dc8ad3  iteration2_residual_query_v1.json
41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f  iteration2_residual_coordinate_v1.json
bad55cb45134cfdab3be86b3d3c676807acb402d69b6d37d0af59767152e531c  prefix_exact_cegis_v1.json
ee7ccc77c34454845b59e709507b901d814263242d8ff9b66e4257f06e0e90d4  prefix_global_modular_replay_v1.json
b8f079d08f1100108433428bc5fe4daa40edf5e90757736013fa07002c1fab0c  ../G-0117/src/main.rs
84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa  ../G-0117/src/lib.rs
b25d5451cf0649be14f67fb7eb2f8bef4fa4b7272fe6e58a29ea5b6bbee6be69  ../G-0117/target/release/g0117-global-coordinate-pricer
```

## Claim boundary

The exact nonzero coefficient refutes only the iteration-1 rational candidate.
The complete priced row is finite-family CEGIS input, not a proof that another
family member exists or that the family is complete.
