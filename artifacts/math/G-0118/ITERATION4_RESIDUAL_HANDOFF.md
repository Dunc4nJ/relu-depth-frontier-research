# G-0118 iteration-4 exact residual handoff

## Appended direction

The first canonical global hinge residual of the iteration-3 prefix member is

```text
d = (0,0,0,0,0,0,0,0,1,-2,1).
```

For the denominator-cleared 101-term certificate, its exact integer
coefficient is

```text
-2569037380781138550866227164032447962596830880486090488375885126283130833555936658580160857076351162672.
```

The corresponding reduced rational residual is

```text
-142724298932285475048123731335135997922046160027005027131993618126840601864218703254453380948686175704
---------------------------------------------------------------------------------------------------------.
 34675797302613629654635214812447674583989196554832504587033138888338089545573336062937165379785
```

The reduction gcd is 18. Reducing the exact integer modulo the two replay
primes gives 737,152,734 and 959,268,884, exactly matching the complete modular
replay.

## Complete family row

`iteration4_residual_coordinate_v1.json` prices this direction exactly for all
163,740 frozen columns. It contains every signed-i64 hinge coefficient and all
eleven linear vectors. The hinge row has 109,638 nonzero values and maximum
value 645,120. Its ordered signed-i64 stream digest is

```text
5957206923bec9ae8c595e7bed066a019a72520cd221dc95c743d9f4a29e072d.
```

The unchanged all-linear stream digest is

```text
84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51.
```

This row is ready to append with target zero. Iteration 4 must reopen the
complete 163,740-column family and solve over Q; restricting to the previous
124 basis columns would not be a family decision.

## SHA-256 bindings

```text
16138d23a7c8fef316680dc870266923b20fb5084673c3a84c96fc6bca2946aa  iteration4_residual_query_v1.json
862dbbbd6c2bee9424b8faf4e8cb0a2e7b4c76c94ef0a6bd78bc3e14b90258cb  iteration4_residual_coordinate_v1.json
cf14304010b29fea6730550f1b3a72b136ce8e617a7d3a383a270853f461010c  prefix_exact_cegis_iteration3_v1.json
97ff7a369a7e3269a0b67a8872f8a5f4aca0d9bd9a6232b7ef8c8a59b65b1916  prefix_exact_cegis_iteration3_recheck_v1.json
b48b73cc74758d1fe772c6375038b20612907b58a6250cbe525d469fba879eaf  prefix_iteration3_global_adapter_v1.json
8174b4b2f84eb670f656d6d9f05b2ab902a7300a78d9194179f28d5d7ba57886  prefix_iteration3_global_modular_replay_v1.json
b8f079d08f1100108433428bc5fe4daa40edf5e90757736013fa07002c1fab0c  ../G-0117/src/main.rs
84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa  ../G-0117/src/lib.rs
b25d5451cf0649be14f67fb7eb2f8bef4fa4b7272fe6e58a29ea5b6bbee6be69  ../G-0117/target/release/g0117-global-coordinate-pricer
```

## Claim boundary

The exact nonzero coefficient refutes only the iteration-3 rational candidate.
The complete priced row is finite-family CEGIS input, not evidence that the
next restricted solve succeeds, not a proof that another family member exists,
and not a MAX11 theorem.
