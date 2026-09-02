# Exact sketch-minor integration control

This is a one-column exact MEMBER known answer for the same `MCOLGEN1 ->
ELIFTQ02 -> lift-large` path used by the n=11 stage-A run.  The column is the
target linear row itself at `n=2`.  The pivot report uses sketch seed
2,026,090,201 and one exact pivot bucket.

Commands, run from the repository root:

```bash
tools/exactlift/lift_large_rs/target/release/max11-lift-large build-sketch-member \
  --pivot-report artifacts/math/n11-stageA-exact-lift/sketch-member-tiny-control/pivots.json \
  --sketch-index 0 \
  --batch-dir artifacts/math/n11-stageA-exact-lift/sketch-member-tiny-control/batches \
  --output artifacts/math/n11-stageA-exact-lift/sketch-member-tiny-control/problem.eliftq02 \
  --report artifacts/math/n11-stageA-exact-lift/sketch-member-tiny-control/build.json

tools/exactlift/lift_large_rs/target/release/max11-lift-large solve \
  --input artifacts/math/n11-stageA-exact-lift/sketch-member-tiny-control/problem.eliftq02 \
  --prime 65521 --lu-block 1 --row-tile 2 --threads 2 \
  --max-steps 3 --reconstruct-every 1 --candidate-support-limit 1 \
  --crt-primes 65519,65497 \
  --output artifacts/math/n11-stageA-exact-lift/sketch-member-tiny-control/solve.json
```

The builder reproduced 1/1 pivot column and constructed 1 sketch row plus 2
real rows.  The solver recovered the planted coefficient `1/1`, with support
1/1 and denominator LCM 1.  Exact verification passed on 3/3 combined rows.
The mandatory `+1/1` coefficient mutation was nonzero on 2/3 rows, so the
negative-direction control failed as intended.

Custody hashes:

```text
c0bf377d9ce65193d83cd8ae9f526c47ebff4f77cb40d6ae9dc329aafca1c454  pivots.json
780d12c8093e456b3979af23c8fbad979ee84907de7015b9b05eec585affe8fb  batches/batch-000.mcolgen1
86fde87f52d9deeb1476e29da4eeb21e3f9525db4b3ea954293996d48d2dc8c9  problem.eliftq02
f41bf5ccdc80c416c4f0418939291ded70ae9bd58df26f5454cbe7b80c6945c8  build.json
15c51c094f03584e49fc417b7f97cc483f3529142b4b59df1f717c65cf0671c6  solve.json
```

No claim: this tiny control validates the named implementation path and its
exact positive/negative checks; it says nothing about MAX11.
