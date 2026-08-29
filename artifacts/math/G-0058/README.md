# G-0058 — support-eight discriminator

## Milestone 1: proper-vanishing hypothesis refuted

The proposed universal identity is false. The lexicographically first frozen
proper mass-four counterexample is G-0038 sequence **92,489**:

```text
negative: (4,4), (5,5), (6,6), (7,7)
positive: (0,0), (1,1), (2,2), (3,3)
active vertices: 8
```

Its two branches are complementary four-loop sets. Under an ordering of the
eight active labels, the branch words differ by a balanced word containing
four `+1` and four `-1` entries. Canonical branch orientation leaves 35
complement pairs. Fourteen are nonnegative Catalan words and contribute only
to the linear part; the remaining **21** cross the ordered cone and are
primitive support-eight hinges. Each has exact multiplicity

```text
2 * 4! * 4! = 1,152.
```

Embedding into eleven coordinates inserts three zero positions in
`C(11,3)=165` ways and contributes the unused-label factor `3!=6`. Therefore
this single proper atom has coefficient **6,912 on every one of the 3,465
ambient support-eight rows**. Its ambient column SHA-256 is
`524062c323fc1e3b6b494bbb52510c02f52de7d513b565a1672a931419b6ac04`.

The executable scanned the stream in canonical sequence order. Before
sequence 92,489, 86,690 proper records were excluded because they have at
most seven active coordinates, and 2,488 active-eight records were checked
with the independent clean-room subset-state DP. The counterexample was then
replayed by direct enumeration of all `8!=40,320` label orders. Both methods
produce exactly the same 21-direction hinge column.

This atom had zero price under the frozen one-coordinate G-0053 dual, which
exposes a blind spot in that scheduling discriminator. G-0055 already stated
the correct boundary: zero price does not imply that a column is irrelevant.

## Milestone 2: restricted H8 gain was already present

An independent clean-room reconstruction of the `3,465 x 1,465` S0
support-eight matrix gives the same rank tuple at both frozen primes:

| Stage | `rank(H8)` | `rank([H8; lambda])` |
|---|---:|---:|
| S0 | 222 | 223 |
| S0 + sequence 92,489 | 223 | 224 |

Each value is backed by an explicit nonzero modular minor and a complete
replayed right-kernel basis. The normalized gain witness at both primes is
supported on S0 column zero, sequence **136,039**.

This witness lifts without CRT: the integer H8 column for sequence 136,039 is
exactly zero on all 3,465 support-eight rows, while its independently
recomputed lambda value is **79,833,600**. In fact, S0 contains 430 zero H8
columns, 321 of which have nonzero lambda. H8 is therefore far too coarse to
serve by itself as a mass-four obstruction.

The boundary is decisive. Sequence 136,039 has **1,326 nonzero hinges** in
the complete 99,858-row degree-four matrix, with fingerprint
`082d245e27f4559780dac68ccc0dfcf12f6166d5a0d14164e55116b353fa0be5`.
Thus its unit vector fails complete hinge replay on 1,326 rows: it is an exact
restricted-H8 witness, not a MAX11 circuit.

Appending sequence 92,489 adds the constant column 6,912 on all H8 rows and
lambda zero. It raises both restricted ranks by one and leaves the pre-existing
gain unchanged.

Rank-gate bindings:

```text
support8_rank_gate.py
  2be8d7c8e95bc7a437af1534356521916fe0d9481d264de074c53672de2b4dc0
support8_rank_gate_v1.json.gz
  b18dc35ab221d0517bb496bf87cbaa4b23748b5a17f198a23c2cb9d525f030a4
canonical scientific payload
  56c9efb93f379f9d7a927077b6d396b15bf147500fb01718814953aad9f22d3e
canonical full report payload
  db450584f8e5ea0213c65e92bb1bfa921c79dba772f003c433063ead455eb352
```

The scientific projection recursively removes runtime and available-memory
observations before hashing. Mutation tests confirm that changing those
run-specific fields leaves the scientific digest unchanged.

## Reproduce

```bash
python -B artifacts/math/G-0058/support8_proper_filtration.py --self-test
python -B artifacts/math/G-0058/support8_proper_filtration.py \
  --workers 8 \
  --output artifacts/math/G-0058/support8_proper_filtration_replay.json.gz
.venv/bin/python -B artifacts/math/G-0058/support8_rank_gate.py --self-test
.venv/bin/python -B artifacts/math/G-0058/support8_rank_gate.py \
  --workers 8 \
  --output artifacts/math/G-0058/support8_rank_gate_replay.json.gz
```

Frozen artifacts:

```text
support8_proper_filtration.py
  0de659ebef2dea44bc07c3c5f2fbb5f50c7d50338534bdc0e686d087bd120629
support8_proper_filtration_v1.json.gz
  90d801abeb6820a27fe8f181dc35b0cf06ac23dac6a98c2d2bc2548db3397d2f
canonical report payload
  7d54e8e24529c41ccb463e351312fe618d31ff7283649e3526e1095a83a0deba
```

## Claim boundary

The first milestone refutes the proposed proper-core support-eight vanishing
filtration. The second certifies an exact lambda-nonzero circuit only after
restricting to H8; it explicitly fails complete 99,858-row hinge replay.
Neither proves a mass-at-most-four construction or decides unrestricted
MAX11. The finite-field rank integers are not asserted as exact rational
ranks.
