# G-0118 iteration-2 candidate — independent red-team report

Reviewer: CrimsonSpire / Codex / same-lineage fresh context (T1)  
Pinned candidate: `artifacts/math/G-0118/prefix_exact_cegis_iteration2_v1.json`  
Pinned candidate SHA-256:
`1d3fd50449fd63c0f8d795cb4d1428fd7a89ef97bcd709c01c579115ea8ccb4b`

## Verdict

The candidate is an exact member of the frozen 314-row system, but it is not a
global identity.

Independent integer replay gives zero residual on all 301 panel rows, all
eleven ordered-cone linear rows, and both registered hinge rows.  Complete
two-prime ordered-cone replay then finds the lexicographically first nonzero
hinge residual at

```text
(0,0,0,0,0,0,0,0,1,-3,2).
```

Its residues are

```text
272554640  modulo 1000000007
538760177  modulo 1000000009.
```

A separate arbitrary-precision coordinate computation gives the exact
nonzero integer

```text
-6682222336261653691138141713369607563179755071274345059365269959075182620102873087225424810312518464.
```

Reducing this integer modulo the two replay primes gives exactly the displayed
residues.  Thus modular aliasing is not involved: this exact candidate is
globally refuted.

## What was independently checked

### Frozen 314-row membership

- The candidate file hash equals the pinned SHA-256.
- Every declared input binding, the separate preregistration binding, and the
  producer binding equal the actual file hashes.  The producer was hashed but
  neither imported nor executed.
- The first `192640000 = 40000 * 301 * 16` cache bytes reproduce the frozen
  prefix SHA-256
  `d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde`.
- Every retained-column overlap agrees byte-for-byte with its signed-i128 cache
  record, and retained metadata agrees with the same-index panel record.
- The support is exactly the sorted union of the 115 common panel-basis
  sequences and the eight rank-growing sequences
  `98,99,100,101,102,103,104,105`: 123 support slots total.  Twenty-three slots
  are zero, leaving the candidate's 100 unique increasing nonzero terms.
- The complete row-major 314-by-123 selected-basis digest is
  `53c437c654295a6e2ea8e595401b5b7a41dcb80c36d99c85ce1534dd08f38071`,
  equal to the candidate field.
- The two 163,740-entry hinge streams reproduce their signed-i64 digests:
  `c812bb4833289cbc79c68b0bf41ce8e36fbf263e822a0761a24a05877103a22c`
  for `(0,0,0,0,0,0,0,0,1,-5,4)`, and
  `7252a7c025f560f6c71332d044ffee5fc8517d7f7a45e4c14b0bec7593f962af`
  for `(0,0,0,0,0,0,0,0,1,-4,3)`.  Their common linear stream reproduces
  `84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51`.
- A second independent semantic path re-priced both hinge directions and all
  eleven linear coordinates for every one of the 123 support sequences
  directly from the signed graph records; all values equal the frozen streams.
- Python BigInt accumulation equals the independently assembled scaled target
  on all 314 rows.  Both row vectors have canonical decimal SHA-256
  `a46bcf54e4d540cbd18235ecf4a4c578430b4e0e01efa1b33b1d567ea5a3c210`.

This is exact integer equality for the denominator-cleared certificate, hence
exact rational equality after division by the positive target scale.  No
floating arithmetic enters this decision.

### Complete global replay

The clean-room C++ implementation constructs each selected atom's full
ordered-cone normal form from the signed loopless graph specification.  Its
subset histogram counts every labelled permutation exactly; it does not call
the G-0117 or G-0118 global replayers.  The complete census is:

| quantity | count |
|---|---:|
| nonzero candidate terms | 100 |
| labelled permutations represented | 3,991,680,000 = 100 * 11! |
| distinct per-atom raw words | 7,076,902 |
| per-atom active-hinge entries | 3,499,662 |
| aggregate primitive hinge directions | 170,547 |
| directions nonzero at one or both primes | 170,525 |

All eleven global linear residual coordinates are zero at both primes.  The
first nonzero object is therefore the hinge direction displayed in the
verdict, not a linear fallback.

The exact coordinate was not reconstructed from the C++ direction histogram.
A separate Python active-vertex rank-injection DP priced that one direction
for all 100 terms, and Python BigInt accumulated the 24 nonzero term prices.
The complete contribution list is retained in `review_v1.json`.

## Adversarial controls

- Every one of the 100 nonzero coefficients was incremented by one in turn.
  All 100 mutants fail the exact 314-row replay; per-mutant first residuals and
  row digests are retained in the receipt.
- A sequence-to-coefficient swap, duplicate support, sparse-projection
  mutation, declared binding-hash mutation, target-scale increment, `10!`
  target, wrong linear target coordinate, and row-order mutation are all
  rejected.
- The Python targeted hinge and linear DPs agree with literal permutation
  enumeration on a synthetic signed graph; an equality-destroying edge mutant
  is rejected.
- The C++ subset histogram independently agrees with literal permutation
  enumeration.  Omitting the negative-orientation linear correction is
  detected, vertex relabelling leaves the full-orbit normal form unchanged,
  and an equality-destroying edge mutant changes the result.
- Two complete subject runs have identical canonical scientific payload SHA-256
  `08c358b58c4b0f3398e7a2d6c57699f36ca845e61f3b1055478dbadec787a8e9`
  after removing only the measured `wall_seconds` field.  The two global phases
  took 46.7817 and 44.6782 seconds on this host.

## Independence and review standing

`review_candidate.py` never imports or executes
`prefix_exact_cegis_iteration2.py`.  The finite replay is new BigInt
accumulation over frozen records; the global replay is a new C++ subset-DP and
normal-form implementation; and the exact falsifying coordinate uses another
Python DP that does not consume the C++ histogram.  Literal-permutation tests
exercise both implementations' core recurrence and sign conventions.

This is still same-model-lineage T1 review, not a T2 referee action.  It
dispositions this candidate by a concrete exact countercoordinate; it does not
raise any broader claim to `REFEREED` standing.

## Promotion gate disposition

- **Consumer:** the research lead's promotion gate for this exact candidate.
- **Gate outcome:** closed against promotion; the candidate fails the complete
  global normal form.
- **Observed defect class:** the iteration-1 finite/global mismatch recurred one
  CEGIS row later: exact agreement on the accumulated finite rows, followed by
  a new global hinge residual.
- **Deletion/retirement condition:** satisfied for this exact candidate by the
  complete global refutation and independent exact countercoordinate.  The
  review evidence should remain as the disposition record; it is superseded
  only if the candidate bytes change, in which case the new hash is a new
  subject and this verdict does not transfer.

## No-claim boundary

The 314-row equality is not MAX11.  The nonzero global residual refutes only
this exact cleared rational coefficient vector.  It does not show that the
40,003-sequence subset has no other member, that the full 163,740-column family
has no identity, that the family is complete, that unrestricted two-hidden-
layer ReLU networks cannot represent MAX11, or that the all-arity target is
false.

## Evidence and reproduction

| artifact | SHA-256 |
|---|---|
| `PREREGISTRATION.md` | `674916b5fd5c49c7bfe93d6ba344d2879cb3f4bcb5fcf97229994419a1b37fb8` |
| `review_candidate.py` | `1133c4fa3ec6b6c1c644b82434a8d2384ee31a866d4fc3b04a76e06136fe955a` |
| `cleanroom_global_replay.cpp` | `cb5422128c22019b6d40626cb97c7e1ec33adb53fcefea6a2384db4a69682885` |
| `review_v1.json` | `6d5b320055327b69d56997ce799486bfc651575e807fc67fafabcfd799927d30` |
| `review_recheck_v1.json` | `e1950d47e080b6aff8d8c0ee3c5b984e27767082cd3ef7212a8fad3f657c916a` |

From the repository root:

```bash
python3 artifacts/reviews/G-0118-iteration2-candidate/review_candidate.py --self-test
python3 artifacts/reviews/G-0118-iteration2-candidate/review_candidate.py \
  --output /tmp/g0118-iteration2-independent-replay.json
```

The runner refuses an existing output.  For the two retained receipts, the
deterministic payload comparison is:

```bash
jq -S 'del(.global_modular_replay.wall_seconds)' \
  artifacts/reviews/G-0118-iteration2-candidate/review_v1.json | sha256sum
jq -S 'del(.global_modular_replay.wall_seconds)' \
  artifacts/reviews/G-0118-iteration2-candidate/review_recheck_v1.json | sha256sum
```

Both commands return
`08c358b58c4b0f3398e7a2d6c57699f36ca845e61f3b1055478dbadec787a8e9`.
