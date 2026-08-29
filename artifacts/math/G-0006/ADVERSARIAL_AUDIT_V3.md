# G-0006 corrected-v3 adversarial audit

Date: 2026-08-29

Verdict: **PASS**, bounded to the frozen quotient, finite orbit-grid solve, and
complete residual of the serialized 192-term seed.  The seed is not a global
identity.  This audit neither decides the span of all 9,804 classes nor says
anything about unrestricted two-hidden-layer networks.

## Frozen family

The generator starts from the 252 full-active simple two-component forest
terms in the pinned MAX10 certificate.  It adds one edge of each colour from
the new eleventh vertex to endpoints in the same component, producing 16,000
raw loopless pairs.  Exact typed-graph isomorphism under vertex relabelling and
one global colour swap gives 9,804 classes.  Weisfeiler--Lehman hashing is only
a bucket accelerator; exact VF2 is the authority.

An independent quotient implementation produced the identical 9,804-part
partition.  It also checked the raw-to-class census and representative list.

## Orbit-grid computation

The eight frozen NPZ inputs cover all 364 `S_11` orbits of
`{0,1,2,3}^11`.  Both primes 1,000,003 and 1,000,033 gave candidate rank 192
with the target in the modular span.  The recorded solution then solved and
replayed an exact rational 192-by-192 subsystem.

This is only necessary finite-grid evidence.  The reported `grid_rank=192` is
a modular rank, not an independently established rank over `Q`.

## Normalization correction

The first serialized residual was invalid: a row represents all distinct
assignments in an orbit, so the internal orbit solution targets `11!*MAX11`.
Version 1 subtracted `MAX11` rather than `11!*MAX11`.  Its files are retained
only as superseded provenance and are described in `SUPERSEDED_V1.md`.

Version 3 divides every serialized certificate coefficient by `11!` before
complete hinge replay.  The independently audited principal hashes are:

```text
isomorphism_classes_v2.json
  3f24edd0b8928256e90fe41fbafd846b693efd37285065da907a1ffdf9561f48
orbit_seed_solution_v3.json
  c6e853076f952464f29aeceec76e5a43a3cf3e9c5fd6ddb1b89e9c186bff989f
orbit_seed_hinge_residual_v3.json.gz
  5089f96cc93d022f1a5f0a820c693ae6f9d3392271ac818b4a0a6e3244692553
raw orbit matrix, int64 C order
  751a6e7dddf5b3028ea8b8386b1c68440e546623b894a98304812844309e3340
quotient orbit matrix, int64 C order
  b3e52cf1185058667d6f126a62b239e3b0a3692c07ff7a6d22de40de14ed4a3a
canonical raw pair list
  d1c6755e5585c5c4f3160589bcb21ca1a989161fb289946b9bbb935a0d6cd569
```

## Independent falsification

The auditor used a separate dynamic program, with its direction and cone
conventions brute-validated through `n=7`, and independently transported all
364 profile/stabilizer weights.  It reproduced the v3 finite-grid equations.

At the off-grid point

```text
(0,0,0,0,0,0,0,1,1,2,4)
```

the complete exact residual is nonzero, with sign and magnitude matching the
frozen v3 residual.  Therefore the particular 192-term seed is **not** a
global MAX11 certificate.

## Claim boundary

- Passing the 364 orbit rows does not imply a CPWL identity on `R^11`.
- Failure of this one 192-term basis solution does not refute another linear
  combination of the 9,804 classes.
- Failure or success of the 9,804-class family would still not decide the
  unrestricted arbitrary-real-weight two-hidden-layer problem without a
  completeness theorem.
- The v3 residual schema retains a historical `v1` label; consumers must bind
  the file hash and normalization fields rather than infer semantics from that
  label alone.
