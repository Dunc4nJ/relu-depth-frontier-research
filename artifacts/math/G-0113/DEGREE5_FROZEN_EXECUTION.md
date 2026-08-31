# G-0113c frozen execution

Frozen before the first producer execution and before any MAX11 target rank.

- original preregistration SHA-256:
  `9b57dc419e7ab54de621e84a0e3d713b1a78a13572517b9e50af99bf3b023141`
- source-fiber addendum SHA-256:
  `23e657b646581ef81c61654e2a966d0f73ad23618b15de27e15f40b6926e3822`
- public MAX10 certificate SHA-256:
  `10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4`
- producer `degree5_quotient_census.py` SHA-256:
  `e0cb483d383021cba14730a4cac5b3f4c401106291b37f318233158ce3178edd`

Registered invocation from the repository root:

```bash
source scripts/activate-toolchain.sh
/usr/bin/time -v python artifacts/math/G-0113/degree5_quotient_census.py \
  --workers 8 \
  --map artifacts/math/G-0113/degree5_signed_orbit_representatives_v1.jsonl.gz \
  --output artifacts/math/G-0113/degree5_quotient_census_v1.json
```

The producer refuses to overwrite either output.  If it stops before both
artifacts are complete, preserve the failure transcript and freeze any repair
as a new producer version before retrying.
