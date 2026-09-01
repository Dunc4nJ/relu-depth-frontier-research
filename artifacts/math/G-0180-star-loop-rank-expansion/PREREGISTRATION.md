# G-0180 preregistration — quotient-aware STAR loop quarantine

Frozen on 2026-09-01 before pricing any G-0180 expansion direction against a
STAR record and before computing any augmented or quotient rank.

## The corrected question

Let \(O\) be the real span of the 163,740 canonical fully
\(S_{11}\)-symmetrized G-0113 primary columns together with the pure
ordered-chamber-linear carriers \(5E,5L\).  Let \(S\) be the full frozen
common-apex `STAR` family.

Every column in \(O\) has zero active hinge coordinate with \(d_0=1\): the
primary signed graphs are loopless, and the carriers have no interior hinges.
`MAX11` is linear on the ordered chamber and has the same zero restriction.

G-0179 already certified

\[
q_{1548}=5E,
\qquad
q_{4259}=2p_{5341}-p_{66223}.
\]

Its failed square exposed two complete \(d_0=1\) collisions.  Independent
G-0109 and G-0179 complete-normal-form evaluators now certify

\[
q_{22}-q_{3140}=0
\]

and

\[
q_{2986}-q_{5656}=2p_{15947}-p_{22121}-p_{36968}\in O.
\]

The second equality holds on all 11 linear coordinates and all 434 hinge
directions in the five-column union.  No carrier correction is omitted: the
five coefficients sum to zero, and the complete normal-form residual is
identically zero.

Delete sequences \(1548,3140,4259,5656\), retaining the other 5,769 STAR
records in increasing sequence order.  These retained columns represent every
STAR coset modulo \(O\).  This reduction additionally relies on the frozen
G-0179 structural receipt: its 5,773-record census covers the full frozen STAR
family outside the primary quotient, and every full-atom/cancelled-carrier
discrepancy was replayed into \(O\).  The rank certificate must hash-bind that
receipt; a rank result without this coverage premise cannot promote the theorem
below.

## Exact conditional theorem

Let \(D\) be either frozen direction prefix below, appended after G-0179's
5,771 directions, and let

\[
A_D=(h_d(q_j))_{j\in Q,\ d\in D_{\mathrm{old}}\cup D}
\]

be the record-by-direction integer matrix for the 5,769 retained quotient
representatives \(Q\).

If \(A_D\) has row rank 5,769 over one fixed prime, it has row rank 5,769 over
\(\mathbb Q\) and \(\mathbb R\).  Then

\[
\ker(R_{d_0=1})\cap\operatorname{span}_{\mathbb R}(O\cup S)\subseteq O.
\]

Proof: use the four displayed relations to rewrite any STAR combination as an
element of \(O\) plus a combination of the 5,769 retained representatives.
The \(O\) term restricts to zero.  If the whole function restricts to zero,
full row rank of \(A_D\) forces every retained coefficient to vanish.  The
function therefore lies in \(O\).

Consequently every function \(f\) with zero active \(d_0=1\) hinges, including
`MAX11`, obeys

\[
f\in\operatorname{span}_{\mathbb R}(O\cup S)
\quad\Longleftrightarrow\quad
f\in O.
\]

This is a target-membership equivalence for the frozen STAR extension.  It is
not formal independence of all STAR records, a decision that `MAX11` is or is
not in \(O\), completeness of the degree-five family, or an unrestricted ReLU
depth/width lower bound.

## Frozen direction order

The candidate universe contains 16,661 active primitive \(d_0=1\) directions.
G-0179 priced 5,771 of them; “unpriced” below means absent from that STAR
matrix.  No value from a different panel or residual was used in selection.

The complete 10,890-direction continuation is frozen in
`expansion_directions_v1.json`:

1. Hash-rank all unpriced directions by
   `SHA256(b"G-0179-unused-direction-order-v1\0" || raw_signed_i8)`, with raw
   signed-i8 bytes as the tie-break.  The first 480 form the hash gate.  Their
   identities and ordering use no pivot, target, or new-price information;
   the length 480 is explicitly rank-outcome-aware and gives two columns of
   slack over the post-quotient minimum possible increment 478.
2. Append every one of the 466 deterministic Hopcroft-Karp matches to the
   identical two-prime G-0179 nonpivot-record set which is absent from the first
   480, in retained-record order.
3. Fill to 1,024 from the same hash order, then freeze the entire remaining
   continuation in hash order.

| object | count | signed-i8 payload SHA-256 |
|---|---:|---|
| lexicographic unpriced set | 10,890 | `ce2dd0ed44657e24f35b78ab9e08c19aa734a9e7715fec5e3789f150bf30ba6b` |
| hash-ranked unpriced order | 10,890 | `7d0af3f83d3cf32228df7e10f8940bb72c39a56b2bc076e0839071230dfe9886` |
| hash prefix | 480 | `3d83256a9c755a84a2b8b873f5baecc8e8e991c6007dcf2e108dbb9a07b37e5e` |
| rank-directed prefix | 1,024 | `197da75ae725a389d57934b2cb7ba81446420420ac7a60f7d0204b2e2c259323` |
| full nested continuation | 10,890 | `973ed1a113beb8ed79d01cdbb3391e4fcdb9c94749082264acdebfd0f78340f8` |

The 1,024 gate is honestly post-outcome rank-directed through structural
incidence.  It is still blind to every new STAR price and to the target.

## Frozen inputs and code

| object | SHA-256 |
|---|---|
| G-0179 STAR records | `c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4` |
| G-0179 selected directions | `231752384d357be45a9d2513a9185539bf0df970640c28e4f259da37fc8a982f` |
| G-0179 exact base matrix | `0e7236e06adc906f2859338b12848e6fc04156963d1567de84dd1e83784162ad` |
| G-0179 intrinsic-relation receipt | `c2fe511b628169929cce87fc116ab7fde09defc5746d1e40663660502d2ad6fa` |
| G-0179 semantic controls | `f74d95d3fe443b42cfe28df9617e1435e78062418b718900b7010b7d2bd0209b` |
| G-0179 semantic-to-old-primary binding | `4c5b6f131671892660f417359480ae3ce412bfe01a5d1f67e05c1bd1352c0327` |
| G-0179 structural-premise receipt | `720b9c7d52f6f5c6e07f72dd8bebfbe65b4e5d508d10235612a66835c44de072` |
| G-0179 rank receipt, prime 1,000,003 | `c368c31700b498847256337973d51d9804351704f44cbb74da163aea750bf5d5` |
| G-0179 rank receipt, prime 1,000,033 | `1b20292d0e297ed7bdceccd53d637abed5836d07d78b9976c7f5c8d7d64c4e51` |
| direction-freeze source | `cabf8c1a84f08f7e6a1013f2b2fe064c92a3093c9c337e32c2b05fa73bc67670` |
| frozen direction document | `546f0a248816487f104fe609261667ade9ef7823d3f38a6dadc70a2a5ca8da16` |
| Rust pricer manifest | `6ecbd74cf899a594c8e95aa3144109bcf45ea0c61d1a8fa02593d89a14b85c6a` |
| Rust lockfile | `f6374521cecd8cd0d90c787956fa6ec8f7902ae5da65e22879dbdc80011505b0` |
| Rust pricer source | `7eb9e6ab9722d5f31e0702033f18c3d553ce51c660fb3f900678fd0a0b86a237` |
| G-0179 evaluator dependency | `8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73` |
| release pricer binary | `eaaf2d068be7c196ab57a17396fcdb5bb8f8e61443efc25468e2bcaa2330dfd9` |
| augmented assembler source | `e313cbc10ad30d62797f5657fb347deaf2b40239e85838d2e98fc99146531c01` |
| rectangular FLINT source | `5bd74383f47570b2ce80c4dd5599d8f4bd47d04c99b993ade4fe43bea4fe600d` |
| rectangular FLINT binary | `7829a042b22873fb59bfdfa2902317f04af4ac03759e9a4d75eac90876c82728` |
| rank build script | `b5cb0859afe2bbd893ff9ddf003f469a49d30e1b18e392e5ff4b1cb90a2dec2b` |
| rank self-test | `188ec07f2ea1e2a9a419adc4c746b91b5f86dc3d8fe508991196ecbd0e7a900a` |
| two-prime rank wrapper | `b493a826e6ec0ab69fafc33c6d3a9e6c204dcec5be894737fc98103a82da2c48` |

The quotient record sequence digest is
`2bf3aa764a3311578aea110f29dcca60284d69b4b5f4b3cb71c1fc5bf1a44606`.
The Rust build, strict Clippy, and compilation pass.  The FLINT production-path
self-test passes signed extrema, rectangular full-row and deficient ranks,
prefix selection, independent signed reduction on every cell, both fixed
primes, truncation rejection, prime rejection, and overwrite rejection.
Before rank, the wrapper independently re-hashes the pricer manifest, lockfile,
source, evaluator dependency, release binary, assembler source, expansion
matrix, all assembly inputs, ranker source/binary, and every theorem-premise
receipt listed above.  Receipt text alone is not accepted as source custody.

## Frozen execution

From this directory:

```bash
./target/release/g0180-star-loop-expansion-pricer \
  price-prefix-1024 \
  ../G-0179-star-loop-quarantine/star_outside_primary_records.json \
  expansion_directions_v1.json \
  ../G-0179-star-loop-quarantine/intrinsic_kernel_relations_v1.json \
  results/expansion5769x1024.i64le \
  results/expansion5769x1024_receipt.json \
  --threads 12
```

The exact expansion matrix must have shape 5,769 by 1,024 and exactly
47,259,648 bytes.  The writer refuses input-hash drift, source drift, overwrite,
any record census other than the exact four exclusions, direction-order drift,
or a nonunique/nonprimitive/inactive direction with \(d_0\ne1\).

Then assemble the record-major augmented matrix.  Raw file concatenation is
forbidden because each base row must be followed by its expansion row:

```bash
python3 assemble_augmented.py \
  --base ../G-0179-star-loop-quarantine/results/hinge5771.i64le \
  --expansion results/expansion5769x1024.i64le \
  --expansion-receipt results/expansion5769x1024_receipt.json \
  --records ../G-0179-star-loop-quarantine/star_outside_primary_records.json \
  --relations ../G-0179-star-loop-quarantine/intrinsic_kernel_relations_v1.json \
  --output results/augmented5769x6795.i64le \
  --receipt results/augmented5769x6795_receipt.json
```

The assembler skips base row 3,139 (sequence 3,140) and row 5,654 (sequence
5,656), both zero-based in the original 5,771-row matrix.  Its output must have
shape 5,769 by 6,795 and exactly 313,602,840 bytes, checked again by the
producer receipt before rank.

Finally run the exact two-prime gate using the assembler receipt's externally
pinned matrix hash:

```bash
python3 rank/certify_augmented.py \
  --matrix results/augmented5769x6795.i64le \
  --expected-matrix-sha256 HASH_FROM_ASSEMBLER_RECEIPT \
  --ranker rank/rank_rectangular_flint \
  --ranker-source rank/rank_rectangular_flint.cpp \
  --base-rank-1000003 ../G-0179-star-loop-quarantine/results/rank_certificate_v1/rank_mod_1000003.json \
  --base-rank-1000033 ../G-0179-star-loop-quarantine/results/rank_certificate_v1/rank_mod_1000033.json \
  --out-dir results/rank_certificate_v1 \
  --binding-file expansion_receipt=results/expansion5769x1024_receipt.json \
  --binding-file assembly_receipt=results/augmented5769x6795_receipt.json \
  --binding-file directions=expansion_directions_v1.json \
  --binding-file intrinsic_relations=../G-0179-star-loop-quarantine/intrinsic_kernel_relations_v1.json \
  --binding-file semantic_controls=../G-0179-star-loop-quarantine/semantic_controls.json \
  --binding-file semantic_binding=../G-0179-star-loop-quarantine/semantic_control_binding_receipt.json \
  --binding-file structural_receipt=../G-0179-star-loop-quarantine/quarantine_structure_receipt_v2.json
```

The fixed primes are 1,000,003 and 1,000,033.  Every selected signed cell is
reduced independently by byte-Horner and 32-bit-limb-Horner arithmetic.  FLINT
computes rectangular RREF/rank; there is no determinant for this matrix.

## Outcome rules

1. Run the base-plus-480 gate at column end 6,251 under both primes.
2. If both ranks are 5,769, promote the conditional theorem and do not run the
   1,024 gate.
3. Otherwise run the base-plus-1,024 gate at column end 6,795 under both primes.
4. Full row rank at either prime proves rational full row rank.  Conservative
   promotion requires both fixed primes to report 5,769 at the same gate.  A
   one-prime discrepancy still certifies rational full row rank but triggers an
   audit before theorem promotion.
5. Every appended-matrix RREF must preserve the first 5,291 base pivot columns
   exactly and may add pivots only after column 5,770.
6. If both gates are deficient at both primes, report the exact ranks without
   reselection.  This does not prove the rational ranks are no larger.  Any
   continuation must follow the already frozen remaining direction order or
   separately lift exact kernel relations.
7. No outcome decides whether `MAX11` lies in \(O\), the completeness of the
   finite ansatz, minimality, all-\(n\) behavior, or an unrestricted neural
   network lower bound.
