# G-0179 outcome-blind preregistration — STAR loop quarantine

Frozen on 2026-09-01 before pricing the 5,771 by 5,771 square and before
computing any rank or determinant of that square.

## The question

G-0113's 163,740 primary signed-
\(W\) classes are loopless.  The frozen common-apex `STAR` construction has
23,147 signed-\(W\) classes, of which 5,773 are absent from that primary
quotient.  Every one of those 5,773 outside classes contains exactly one
residual unit loop.  The decisive question is whether these omitted
loop-bearing classes can help represent a target, such as \(\mathrm{MAX}_{11}\),
that has no ordered-chamber hinge coordinates with first component nonzero.

This experiment tests one frozen square minor.  Directions were selected from
the graph structure alone.  No target value, price, rank, determinant, fitted
coefficient, or kernel was used to choose them.

## Exact conditional theorem

Let \(O\) be the real span of the 163,740 canonical fully
\(S_{11}\)-symmetrized G-0113 primary columns together with the pure
ordered-chamber-linear (zero-interior-hinge) carriers \(5E\) and \(5L\).  Let
\(S\) be the full frozen uncancelled
common-apex `STAR` family.

Cancelling common edges from a degree-five atom changes the fully symmetrized
column only by additive carrier columns.  If the signed mass is \(s\) and the
padding has \(c\) loops, replacing it by canonical nonloop padding changes the
column by \(c(L-E)\).  Both possible carrier types are absorbed by \(O\), since

\[
L-E=(5L-5E)/5\in O.
\]

This is a characteristic-zero linear-span statement, not a nonnegative-cone
statement.  The exact structural replay additionally finds that all common
edges in the 5,773 stored `STAR` representatives are nonloops.

Two outside classes are already in \(O\):

\[
q_{1548}=5E,
\qquad
q_{4259}=2p_{5341}-p_{66223}.
\]

Both identities have empty complete hinge maps and are independently checked
on all 301 frozen panel rows and all 11 linear coordinates.  Delete these two
classes and retain the other 5,771 in increasing sequence order.

Let \(D=(d_1,\ldots,d_{5771})\) be the frozen ordered list of distinct,
primitive, active ordered-chamber directions, all with \((d_i)_0=1\).  For the
remaining outside classes define

\[
M_{ij}=h_{d_i}(q_j).
\]

The producer writes the record-major transpose
\(A_{ji}=h_{d_i}(q_j)=M^T_{ji}\), which has the same determinant and rank.

If the exact integer square has nonzero determinant, then

\[
\operatorname{span}_{\mathbb R}(O\cup S)
=O\oplus\operatorname{span}_{\mathbb R}\{q_j:j\ne1548,4259\}
\]

and, for the restriction \(R_D\) to the selected hinge coordinates,

\[
\ker(R_D)\cap\operatorname{span}_{\mathbb R}(O\cup S)=O.
\]

Consequently every function \(f\) with \(R_D(f)=0\), including
\(\mathrm{MAX}_{11}\), obeys

\[
f\in\operatorname{span}_{\mathbb R}(O\cup S)
\quad\Longleftrightarrow\quad
f\in O.
\]

Full rank therefore would not say that `STAR` adds no functions.  It would say
that the 5,771 remaining columns add a direct 5,771-dimensional summand which
cannot help a selected-hinge-free target.

## Frozen inputs and audited premises

| object | SHA-256 |
|---|---|
| G-0113 primary representative map | `57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48` |
| 5,773 outside records | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| 5,771 matching-direction document | `231752384d357be45a9d2513a9185539bf0df970640c28e4f259da37fc8a982f` |
| signed-i8 direction payload | `858c182304ae5256dfa85e720803b54013afb70b7b67383aa6680ecbc0d8336d` |
| matching manifest | `e9cdc74219ca4feb5fd00d57f31d7d1315e421c906093105ca5edb1d5e3d6a04` |
| semantic controls | `f74d95d3fe443b42cfe28df9617e1435e78062418b718900b7010b7d2bd0209b` |
| old-primary hardcode binding receipt | `4c5b6f131671892660f417359480ae3ce412bfe01a5d1f67e05c1bd1352c0327` |
| G-0109 independent normal-form cross-check | `fb2bb557eb4e894e02c80750f731bf10917630e0f93f44724beb9c8acbc9ffb4` |
| structural-premise receipt v2 | `720b9c7d52f6f5c6e07f72dd8bebfbe65b4e5d508d10235612a66835c44de072` |

The structural matching has size 5,771 but is not rank evidence.  The 256-row
pilot is performance and density evidence only; it is neither random nor a
rank certificate.

## Frozen producer and certificate code

| object | SHA-256 |
|---|---|
| Rust normal-form library | `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73` |
| Rust CLI | `128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2` |
| Rust literal-row tests | `5aabf30f0b3370df45b9395017b9279f91a7b4c8d7e8e5e9e631cb4d75650ff6` |
| old-primary binding verifier | `fc338b13cfbdbb96fe2205aa3681bdff4fae12ec46b27308c69947c645d9dcc1` |
| release matrix producer | `ba629a044408e170235523a6f578c55d3201d7be37bb07acf86e27d409a00824` |
| FLINT ranker source | `8e3bfe48816bd9d0f5437d90034294b7247a833d79e5374c613f1fc3333bdabc` |
| two-prime custody wrapper | `1eefd3f26f2e61ad0420d2dd2ff11e2b2849ff68633bc60b7cbd6387ba44dabf` |
| ranker build script | `52441f6e3378a53415670daff617fd35ad31a76b4322828cbe741fcbdd763518` |
| production-path self-test | `03385b12716b31eed6bde6f6793bb0b825d665ad75f3288a0ab410054b13cb31` |
| built FLINT ranker | `a6ab04c94c51e43cd02c1c57c36d7d190415050cf4ae387a7a11ebd65405af43` |

The Rust suite has 10 passing tests, formatting passes, and strict Clippy
passes.  The rank pipeline's independent signed-i64 full-rank, singular,
extreme-value, residue, determinant, digest, truncation, prime, and overwrite
tests pass.  The latest local self-test receipt has SHA-256
`7cd7ec15e77ec51347f48e5a3be1c36f5d7f62e3bce6d3ab219286a175edef94`.

The normal-form evaluator also agrees exactly with the independently frozen
G-0109 implementation on eight deterministic loop-bearing labelled forms,
including branch swaps.

## Frozen execution

From this directory, after recreating the two executable bytes from the frozen
sources when necessary:

```bash
mkdir -p results
./target/release/g0179-star-loop-pricer matched-price \
  star_outside_primary_records.json \
  matching5771_directions.json \
  results/hinge5771.i64le \
  results/hinge5771_producer_receipt.json \
  --threads 12
```

The required matrix is record-major signed-i64 little-endian with shape
5,771 by 5,771, exactly 33,304,441 cells and 266,435,528 bytes.  The command
must refuse `--limit`, overwrite, input-hash drift, source drift, a sequence
census other than 5,773, an exclusion set other than exactly 1548 and 4259,
direction drift, a non-primitive/inactive direction, any \(d_0\ne1\), or an
out-of-i64 exact coefficient.

Then run:

```bash
python3 rank/certify_square.py \
  --matrix results/hinge5771.i64le \
  --dimension 5771 \
  --encoding i64le \
  --ranker rank/rank_signed_le_flint \
  --ranker-source rank/rank_i128_flint.cpp \
  --out-dir results/rank_certificate_v1 \
  --expected-matrix-sha256 MATRIX_SHA_FROM_PRODUCER_RECEIPT \
  --binding-file producer_receipt=results/hinge5771_producer_receipt.json \
  --binding-file directions=matching5771_directions.json \
  --binding-file semantic_controls=semantic_controls.json \
  --binding-file semantic_binding=semantic_control_binding_receipt.json \
  --binding-file structural_receipt=quarantine_structure_receipt_v2.json
```

The only preregistered primes are 1,000,003 and 1,000,033.  Every signed cell
is reduced independently by byte-Horner and 32-bit-limb-Horner arithmetic.
For each prime, FLINT computes both determinant and RREF/rank, and the wrapper
checks their consistency and rehashes every input.

## Outcome rules

1. If either modular determinant is nonzero, the integer determinant is
   nonzero, so the square is nonsingular over \(\mathbb Q\) and \(\mathbb R\).
2. Promotion as the clean G-0179 result requires both preregistered primes to
   report rank 5,771 and nonzero determinant.  A one-prime discrepancy still
   contains a valid rational full-rank certificate from the nonzero prime, but
   triggers an implementation/bad-prime audit before promotion.
3. If both modular determinants vanish, report the failure without changing
   directions.  This does not prove rational singularity.  Compare modular
   kernels and use additional independently frozen primes or exact lifting to
   decide whether the integer square is singular.
4. No direction reselection is allowed after seeing the square or ranks.  A
   different minor is a separately preregistered experiment.
5. The result concerns only the frozen `STAR` extension relative to \(O\).
   It does not decide whether \(\mathrm{MAX}_{11}\in O\), completeness of the
   degree-five family, unrestricted two-hidden-layer ReLU representability,
   a width/depth lower bound, minimality, an all-\(n\) statement, refereed
   status, or formal verification.
