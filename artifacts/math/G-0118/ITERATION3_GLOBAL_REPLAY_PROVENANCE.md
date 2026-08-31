# G-0118 iteration-3 global replay provenance

## Outcome

The exact 315-row prefix member is **not** a global identity. Complete modular
replay over the frozen 163,740-column family found the first canonical nonzero
hinge residual at

```text
d = (0,0,0,0,0,0,0,0,1,-2,1),
```

with residues 737,152,734 modulo 1,000,000,007 and 959,268,884 modulo
1,000,000,009. Both linear residual vectors are zero. The replay processed all
3,556,887 hinge entries and 4,031,596,800 labelled permutations; it found
172,431 nonzero-residual directions among 172,454 supported directions.

The exact denominator-cleared residual, independently recomputed from the
copied integer term vector and the complete coordinate row, is

```text
-2569037380781138550866227164032447962596830880486090488375885126283130833555936658580160857076351162672.
```

Reduction modulo both replay primes gives exactly the recorded residues.

## Adapter limitation and direct equality check

`prefix_iteration3_global_adapter_v1.json` is a compatibility adapter for the
existing v2 replay executable. Its `source_exact_postprocess` object is not a
machine-checked provenance link to the G-0118 iteration-3 solver result. The
scientifically relevant projection was therefore checked directly: its 101
ordered `(sequence, coefficient)` terms and `target_scale` are byte-for-byte
JSON-value equal to those in `prefix_exact_cegis_iteration3_v1.json`.

This limitation is explicit: the replay proves the global arithmetic
refutation of the copied integer candidate. Reproducible source linkage relies
on the hashes below and the direct projection equality check, pending a generic
source-bound adapter for accumulated iterations.

## SHA-256 bindings

```text
cf14304010b29fea6730550f1b3a72b136ce8e617a7d3a383a270853f461010c  prefix_exact_cegis_iteration3_v1.json
97ff7a369a7e3269a0b67a8872f8a5f4aca0d9bd9a6232b7ef8c8a59b65b1916  prefix_exact_cegis_iteration3_recheck_v1.json
e068241f45edbfbb37265fb5a58a46919294fb6b8456ada74f0cbf42303d73fc  ITERATION3_PREFIX_PREREGISTRATION.md
8f364f384f070d5e061d8f61afe8374e8af5f5cac268fe3998d5bbf3c187d370  prefix_exact_cegis_accumulated.py
b48b73cc74758d1fe772c6375038b20612907b58a6250cbe525d469fba879eaf  prefix_iteration3_global_adapter_v1.json
8174b4b2f84eb670f656d6d9f05b2ab902a7300a78d9194179f28d5d7ba57886  prefix_iteration3_global_modular_replay_v1.json
d0496bfc9bb33ca4c21a8255a163f04bbf1cdcf60b654a58a3252d81ab504445  ../G-0117/src/bin/global_modular_replay.rs
84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa  ../G-0117/src/lib.rs
d702825f89cfd9a068ac0b2fa8a12508a8649301f0220b266f6ab9565cddd9a4  ../G-0117/target/release/global_modular_replay
```

## Claim boundary

The nonzero residues and matching exact integer refute only the iteration-3
rational candidate as a global identity. They do not refute the frozen family,
prove family completeness, or settle MAX11.

