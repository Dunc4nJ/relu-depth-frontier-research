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

## Reproduce

```bash
python -B artifacts/math/G-0058/support8_proper_filtration.py --self-test
python -B artifacts/math/G-0058/support8_proper_filtration.py \
  --workers 8 \
  --output artifacts/math/G-0058/support8_proper_filtration_replay.json.gz
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

This exact counterexample refutes only the proposed proper-core support-eight
vanishing filtration. It does not determine `rank(H8)`, produce a
lambda-nonzero circuit, prove a mass-at-most-four construction, or decide
unrestricted MAX11. The next G-0058 milestone treats support eight as a
construction-oriented restricted matrix and adds proper columns explicitly.
