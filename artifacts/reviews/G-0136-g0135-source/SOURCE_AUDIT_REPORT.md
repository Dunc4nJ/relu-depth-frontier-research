# G-0136 source audit — G-0135 Stage A

Reviewer: `GoldenSnow` (Codex / GPT-5; fresh-context, same-lineage T1)

Subject: commit `e2f20e14076863737ea3c01fa78073f2c704eceb`, source
`6786760c2d9c6d11782ae0f2e7a7efed19ddb026e959cf50701b473a1d979668`,
`Cargo.toml` `9d3db2f04d56a9979ca605a177b0a097ff1e44288c7b1a444a5281b3c524664b`,
`Cargo.lock` `bb4c2eec22788cd3f705330b163a19638f7f55e87c4b6d659754a0485632811c`,
and release executable
`f96dbdf5a8998f11629477e81ac0b8ef3fa860fb4e7e813e3ff5b2ccead2d897`.

## Verdict

`PASS` for same-lineage T1 source clearance of the exact replacement subject
named above. No G-0135 scientific manifest or output was observed, and this
audit promotes no mathematical result.

## Scope and method

This is an outcome-blind W2 source audit of Stage A only. The audit inspected
the committed source, dependency manifest/lock, executable binding, prior
G-0132 residual (explicitly allowed by the preregistration), and the complete
direct/transitive custody graph. It did not build a scientific manifest and did
not run the scientific replay. The probe is a fresh Python arbitrary-precision
implementation and does not import the producer; its only pinned comparison is
a temporary Rust helper linked directly to G-0117.

The earlier commit `488f417d72e32bb78856c0bff8f8b0902cc1ba03` is not this
audit's subject. It was rejected before any verdict artifact was published
because its `--preflight` path did not enforce the source-audit receipt. The
replacement subject above adds that fail-closed gate and is being audited from
scratch.

## Source findings

- The 176 selected slots are paired in order with 176 canonical integer
  coefficients, exactly 44 zeros are removed, and the resulting 132 terms are
  required to equal the candidate's own term list. Strict sequence order and
  the frozen sequence/coefficient stream digests are rechecked.
- Every scientific coefficient, product, sum, target subtraction, residual,
  and comparison that can decide Stage A uses signed `num_bigint::BigInt`.
  The G-0117 `i64` kernel is diagnostic only: the code first constructs the
  BigInt normal form, independently reconstructs the linear route, proves the
  pinned frozen-domain bounds, and requires exact equality.
- Each term enumerates all active-label injections and multiplies by the exact
  inactive-label factorial. Generated, visited, and accepted compressed leaves
  and labelled permutations reconcile; skipped, unclassified, and failed are
  zero. The global count is exactly `132 * 11! = 5,269,017,600`.
- Before selection, the aggregate must reproduce G-0132's term/census/support,
  aggregate and nonzero stream hashes, transcript hash, first direction, and
  first coefficient. A second exact coordinate route requires all 68 carried
  directions to be zero, and selection requires all 11 linear residuals zero.
- Batch admission is exactly nonzero coefficient, signed-`i8` tuple order, then
  `take(32)`. The admission function contains no modular, magnitude, rank,
  sparsity, or dependency filter. It separately rejects a carried-row
  collision, invalid direction, duplicate/order failure, noncanonical decimal,
  and fewer than 32 rows.
- Direction hashes consume each coordinate as its single signed-byte bit
  pattern. Coefficient hashes consume canonical signed decimal bytes followed
  by LF. Reordering and plus-one mutants must change the respective digests.
- Candidate, preregistrations, prior replay/audit, kernel, uniqueness lemma,
  46 direct frozen bindings, 41 transitive manifest inputs, source, Cargo files,
  executable, audit artifacts, Git commits, and start/end inputs are checked.
  Paths must be contained normal non-symlink files.
- Preflight, manifest construction, and replay all require the source-audit
  chain. Manifest/result publication uses same-directory exclusive creation,
  hard-link no-overwrite publication, file and directory synchronization,
  opposite-branch guards, an end rehash, and rollback on a publication race.

## Tests and boundary

The release self-test, targeted release unit test, actual ignored active-10
near-frontier exact/pinned test, and release Clippy with warnings denied passed.
The missing-receipt preflight failed at the exact G-0136 receipt path, as
required.

The one-shot independent probe passed. Its fresh Python arbitrary-precision DP
matched a temporary Rust helper linked only to the pinned G-0117 kernel on five
directions for each of panel sequences 0 and 1 and an active-10 signed-mass-five
near-frontier record. The planted combinations reproduced `662784` and
`786432`. Coefficient-plus-one, linear-plus-one, direction reorder,
coefficient-digest, missing-LF, noncanonical-decimal, omitted-contribution, and
one-labelled-permutation census mutants all failed as intended.

The probe independently rehashed 46 direct and 41 transitive inputs (87 unique
path/SHA pairs). Five CLI/path/preflight failures and nine hostile
source-audit-receipt variants were rejected. The exact independently derived
frozen-input set reached the producer's later uncommitted-artifact guard,
demonstrating equality with the producer's own set before commit. After commit,
the positive producer preflight is the final end-to-end custody check.

Residual risk is ordinary implementation/platform risk inside the exact pinned
Rust/Python/toolchain bytes and any error outside the audited hashes. Any source,
executable, frozen input, audit artifact, command, or commit change is outside
this clearance and requires a new audit.

Promotion boundary: T1 source clearance for this exact committed producer and
executable only; no scientific manifest or output was observed, and no
mathematical result is promoted by this receipt.
