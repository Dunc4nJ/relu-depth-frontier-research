# G-0078 clean-room audit

Decision: **SHIP**, with the claim boundary below enforced literally.

The standalone verifier parses the frozen G-0078 certificate without importing or calling either the G-0077 or G-0078 producer. It loads an owned, read-only snapshot of the frozen `full-N.npy`, verifies custody before and after the run, recomputes every selected and failing augmented-row gcd over all 8,108 entries, checks exact divisibility, reconstructs the 230 raw rational weights, and evaluates every theorem-bearing linear combination with Python arbitrary-precision integers.

Run it from the repository root:

```bash
.venv/bin/python artifacts/cleanroom/G-0078/verify_sparse_exact_left_dual.py
```

## Decisive evidence

- Exact artifact gzip SHA-256: `8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96`
- Frozen matrix raw-int64 SHA-256: `41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095`
- Frozen `.npy` file SHA-256: `5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f`
- Selected augmented rows checked: 229; failing augmented rows checked: 1
- Recomputed divisor SHA-256: `561568d665f18a3b131cca41f1e5606dd482f7b6075b60967c698c00083669cc`, exactly equal to the declared-divisor hash
- Witness support: 229 selected primitive rows plus the failing primitive row
- Construction columns replayed: 8,107
- Exact residuals: all zero; maximum absolute residual `0`
- Residual transcript SHA-256: `938979956e0c62988cb9002c58aa40cfc8abd756d5f331da836b0269ad82b579`
- Exact target pairing:

  ```text
  -133983976591838155692739468995654488385375268983412555455167208022395819866232233253671595525158820759909165251604480000
  ```

  This is nonzero and exactly equals the serialized value.
- Certificate gcd: 1; nonzero selected numerators: 229; maximum numerator size: 417 bits; failing-weight size: 390 bits
- Modular-lineage check: reduction of the exact certificate modulo `1,000,003` reproduces both the G-0078 support-coefficient hash and the complete frozen G-0077 dual-coefficient hash.
- Mutation control: incrementing `integer_dual_numerators[0]` by one fails immediately at construction column 0 with residual `759921`. Every one-unit selected-numerator mutation and a one-unit failing-weight mutation is necessarily rejected because its corresponding primitive construction row is nonzero.

The verifier was run twice after its final edit. Both runs emitted audit-payload SHA-256 `b5c469436e99485b7f3adfdf272af543f95926aee653aa45ace7fa2081bb3f50` and byte-identical receipt SHA-256 `d5149c9e6495e97549ffb43d5a2f1d75cd4ca71929dec6fc6e09c5d613f42119`. The verifier SHA-256 is `39fd3b6f0a74ef22b264e16bb184eed2d5094a32c08ab018124182dd10ff5d52`.

## What is proved

Let `A` be the exact frozen `16,738 × 8,107` rational construction matrix and `b` its MAX11 target column, jointly bound by the raw matrix hash above. The reconstructed rational raw-row vector `y` satisfies

```text
yᵀ A = 0       and       yᵀ b ≠ 0.
```

Therefore `b` is outside the column span of `A` over both the rationals and the reals. This is a complete exact obstruction for that frozen finite Y-spoke construction family and bound row system; exceptional-prime ambiguity is gone.

## What is not proved

This does **not** prove an unrestricted two-hidden-layer ReLU lower bound. It does not show that every relevant network can be transformed into a member of the frozen Y-spoke family, and it says nothing about construction families absent from the 8,107 columns. The clean-room run is independent at the code path and exact-arithmetic levels but still uses the same frozen local inputs; a separately implemented rerun on another machine would raise replication confidence, not enlarge the theorem.

## Forest-level consequence

The certificate itself is no longer the bottleneck. Further coefficient hunting or alternate exact solvers has sharply diminishing value. The highest-leverage research question is now the bridge theorem: characterize when an arbitrary candidate shallow representation can be normalized into the frozen Y-spoke family, or find the smallest principled enlargement that escapes it. A valid completeness/normal-form theorem would promote this exact finite obstruction into the sought neural-depth lower bound; a counterexample would precisely identify which missing construction directions must be added before the next obstruction search.
