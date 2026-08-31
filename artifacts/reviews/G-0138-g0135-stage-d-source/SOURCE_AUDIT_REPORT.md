# G-0138 independent Stage-D source audit

## Verdict

`PASS` for T1 outcome-blind source clearance of the exact committed Stage-D
producer and release executable below.  Both source inspection and the fresh
no-import probe passed.  No scientific replay was run, and no scientific
manifest, Stage-C member, or scientific output was opened or created.

## Frozen subject

- Git commit: `1189d0f6e5446e78abc4a5546f1b02fd2815954f`
- Git parent: `8744bebc48bc57e35feeeb7e8b2262e523f97f70`
- Git tree: `a3ab403b05e19c1cd8da3ba72baa5d631bf3c89e`
- `src/main.rs`: `e120f0b1ef7b8465cfcd6d8ae1cd389b6554c19cff1d6f7ae3e8fbc8bace8665`
- `src/engine.rs`: `b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c`
- `Cargo.toml`: `0dc8c61a7114b7b3625f86f550ae682ac650b21081b7b0a70d19802a337bb4da`
- `Cargo.lock`: `13f29a23a9883e0ec61774532534819df16dcc86599b427952c06da6600f8d18`
- release executable: `1d4142782ff6a81e77162b5c599a71985c934f455b128507519c911a749e63b4`

The five hashes were recomputed from the commit objects and from the working
files; all pairs were equal.  The subject commit is an ancestor of the
published remote branch.  A locked release rebuild from the canonical source
path into an isolated target directory was byte-identical to the committed
2,009,032-byte executable.

## Findings against the preregistration

1. **Candidate admission and finite replay — pass.**  The manifest rejects
   duplicate and unknown fields.  The Stage-C member has an exact top-level key
   set plus `deny_unknown_fields` on the typed member, terms, bindings, support,
   replay, and coefficient-mutant records.  Admission checks the frozen
   163,740-record/412-row identity, strict selected/support/coordinate axes,
   selected=support pivot basis, rational-to-integer denominator clearing,
   positive target scale, primitive gcd, exact nonzero term projection, target
   construction, and rank transcript.  A separate replay reconstructs every
   nonzero term's 301 panel, 11 linear, and 100 accumulated-hinge coordinates
   and requires all 412 `BigInt` residuals to be zero.
2. **Complete normal forms and census — pass.**  Each nonzero term is enumerated
   by active-label injections with the exact inactive-label factorial
   multiplicity.  Every term reconciles to `11!`; generated, visited, and
   accepted counts are equal; skipped, unclassified, and failed counts are
   zero.  The global expected census is checked as the dynamic term count times
   `11!`, and transcript sequences must equal the candidate term sequence.
3. **Arithmetic — pass.**  Scientific coefficients, normal-form values,
   products, target subtraction, finite residuals, aggregate residuals, and
   decisions are signed `num_bigint::BigInt`.  The `i8`, `u64`, `i64`, and
   `i128` operations are bounded input/census/cache operations.  The older
   bounded normal-form kernel is post-bound-checked and used only as a
   fail-closed diagnostic cross-check of the independently accumulated exact
   form.
4. **Accumulated and linear coordinates — pass.**  Exactly 68 prior plus 32
   Stage-A directions are validated and deduplicated.  Every one is recomputed
   both from the complete aggregate and by a separate exact direction-pricing
   DP; the routes must agree and equal zero.  The 11 linear coordinates use an
   independent exact DP, then subtract `target_scale * 11!` exactly once at
   coordinate 10 and require all residuals to be zero.
5. **Global terminal — pass.**  The aggregate map is the union of all hinge
   keys produced by every term.  `GLOBAL_EXACT_ZERO` is selected only when the
   complete map has no nonzero coefficient and the already-mandatory linear
   check is zero.  Otherwise the only scientific branch is the exact residual
   continuation.
6. **Next Batch32 — pass.**  The producer orders the complete nonzero hinge map
   with Rust's signed lexicographic `[i8; 11]` ordering, excludes all 100
   accumulated directions, and takes exactly the first 32.  No score, modulus,
   rank, magnitude, or sparsity filter occurs.  It hashes the 11 two's-complement
   signed bytes per direction and the canonical signed-decimal coefficient plus
   LF stream separately.
7. **Hostile controls — pass.**  Producer tests cover coefficient-plus-one,
   target-scale, target-coordinate, omitted term, omitted active direction,
   omitted orbit, decremented global census, omitted accumulated direction,
   direction reordering, coefficient digest mutation, exact-zero, and nonzero
   terminals.  The independent probe additionally rejects exact candidate
   key/axis/term mutations, duplicate JSON, finite-column omission, target
   mutations, digest mutations, and custody-byte mutation.
8. **Custody/publication — pass.**  Entry validation hashes the strict shared
   manifest, all named and transitive bindings, Stage A/B/C receipts and
   sources, all three source audits, Stage-D source/engine/Cargo/lock, the
   currently running executable, the exact kernel, and the uniqueness note.
   Compiled bytes are compared to repository bytes, relevant paths must be
   committed and working-byte equal, path traversal and symlinks are refused,
   and the entire validation is repeated before publication.  Publication uses
   exclusive creation, file and directory sync, atomic hard-link installation,
   and no overwrite.

## Executed non-scientific checks

- Locked tests at the exact archived commit: 2 passed, 0 failed, 0 ignored.
- Locked clippy with warnings denied: pass, 0 warnings.
- Canonical-path locked release rebuild: byte-identical, SHA-256
  `1d4142782ff6a81e77162b5c599a71985c934f455b128507519c911a749e63b4`.
- Committed executable `--self-test`: pass.
- Committed executable `--preflight-static`: pass.
- Independent Python probe: 20 passed, 0 failed; planted 6-active-vertex
  normal form reconciled 332,640 compressed leaves to 39,916,800 labelled
  permutations and 1,441 hinge directions.  Its selected-direction digest is
  `7e59719db6d9cd954843b793e1560a09685f85bc0e48bb558cbeedb60eb82ece`;
  its signed-decimal-LF digest is
  `8b7c5133176abe5bca499b0d9ba989a9c71b7012f780134a99fc1d613927f8bc`.

Bound receipts:

- `SELF_TEST_RECEIPT.json`: `eff6a5e7b3805fbd71ff8d1e8e8f66d678f544dfaeac5aea374b1f2edb12e573`
- `independent_probe.py`: `4d31f23ef30eb6995a5048586fd9f5ba64ed84da3183a34f7af65b3b6ff9a1d3`
- `INDEPENDENT_PROBE_RECEIPT.json`: `181cbbb5205b93dcc398bf1fb8ef5f8988219e6964bc1443d85a7c991e9b2ed7`

## Residuals and honest boundary

- This is same-lineage T1 source clearance, not an independent scientific
  replay or mathematical promotion.
- The executable embeds the canonical `CARGO_MANIFEST_DIR`.  As expected, an
  otherwise exact build from a different temporary source path was not
  byte-identical; rebuilding from the canonical source path into an isolated
  target was byte-identical.  The audit therefore binds the exact committed
  executable and canonical path, not a claim of path-independent builds.
- The producer's completeness still depends on the frozen manifest/input
  bindings being honestly constructed.  This audit establishes that the
  producer checks and consumes those bindings as preregistered; it did not
  inspect future scientific contents.
- During probe development, a first symmetric planted graph produced no active
  hinges and correctly tripped the probe assertion.  It emitted no receipt.
  The final declared six-active-vertex fixture is nondegenerate and all checks
  pass; no failed probe was presented as evidence.

`scientific_manifest_observed=false`  
`scientific_output_observed=false`

**No claim:** this audit does not establish a future Stage-C member, global
identity, residual, frozen-family conclusion, unrestricted MAX11 result, or
Lean theorem.  Any scientific result still requires the separately
preregistered run and independent result review.

## Anti-ceremony and honesty disposition

Creation-gate verdict: legitimate runtime gate.  The Stage-D executable is the
consumer; it refuses scientific execution without this exact PASS receipt.
The observed defect class was real (an initially supplied nonexistent full
commit hash and a prior nested unknown-field custody gap); retirement occurs
when any subject binding changes or G-0135 closes.  The minimum requested
artifacts only were created.

Real-work classification for this bounded window: one runtime-gating audit
unit, no tracker closes, no speculative governance.  Honesty inventory:
checked the commit diff, exact source, tests, clippy, build, executable,
probe failure and final probe; no tests were weakened or skipped, no mocks or
goldens were substituted, no stderr was suppressed, no unrun command is
claimed, and no same-family agreement is presented as scientific confirmation.
The initial hash mismatch, temporary-path binary mismatch, and first null probe
fixture are disclosed above.  Disposition: clean after disclosure; no hidden
acceptance condition remains.
