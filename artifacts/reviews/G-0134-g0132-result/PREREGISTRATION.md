# G-0134 preregistration — fresh-context T1 audit of the G-0132 MEMBER result

## Freeze and admission boundary

- Registered: `2026-08-31T04:21:30Z`.
- Reviewer: `BlackIbis` (Codex / GPT-5; fresh context, same model lineage; T1 only).
- Before this registration, the reviewer saw only the untracked path names
  `artifacts/math/G-0132/Cargo.toml` and `artifacts/math/G-0132/src/main.rs`.
  Their bytes were not opened, hashed, parsed, diffed, compiled, or executed.
  Filename-only inventory showed no G-0132 manifest and no scientific output;
  in particular, `artifacts/math/G-0132/member_global_normal_form_replay_v1.json`
  was absent. No future producer draft, manifest, log, branch enum, residual, zero
  claim, census, or result-derived hash may be inspected until this file is
  committed, pushed, and reported to the orchestrator.
- This is a bounded adversarial result audit, not source clearance, an
  independent proof campaign, or T2 review. After registration the reviewer
  waits for explicit release of the admitted source-audit receipt, manifest,
  and result commit.

## Frozen anchors

```text
6db51f8716d0ba0a82606bddc7573dafd889f2fe  G-0132 protocol commit
73ccd2ce2a96c0d46b0a40166ca6a84050577cdba3f23ff12d1b89e043e8c692  artifacts/math/G-0132/PREREGISTRATION.md

b5b73a1b6ffec75ca2c54a31bf2ebb62ec9dbf0c  G-0128 candidate-result commit
17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838  artifacts/math/G-0128/full_family_master_result_v2.json

0c10fb938340877a35d2efedf971e599a5fd84b0  G-0131 bounded-audit commit
15f3f0f8bd4952d7773effa393a5cecbd0d6f74895ded134efeb5e3701ebb197  artifacts/reviews/G-0131-g0128-result/REPORT.md
0159910b476b1cac9ea0e8f6ad05e16e061036b361efc8b2f5a3a1aa02c09926  artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json

279b4318f5ef7097b7eb919c0f52cc78628bb085  G-0133 source-audit preregistration commit
d2461477ce22c3f8afa036886b63988a3914303a54486bea4bb76d49d164b9bc  artifacts/reviews/G-0133-g0132-source/PREREGISTRATION.md
```

G-0131 admits only the exact `FULL_FAMILY_380ROW_EXACT_Q_MEMBER` certificate:
176 selected coefficient slots, 44 exact zeros, and 132 canonical nonzero
terms. G-0134 therefore rejects a G-0132 NONMEMBER-arm output or any ambiguous
terminal branch.

The future G-0133 receipt is a mandatory admission gate. It must be the
committed file
`artifacts/reviews/G-0133-g0132-source/SOURCE_AUDIT_RECEIPT.json`, schema
`max11-g0133-g0132-source-audit-receipt-v1`, with exact `verdict == PASS` for
the released source SHA and its Cargo/executable hashes, and with
`scientific_manifest_observed=false` and `scientific_output_observed=false`.
The later G-0132 manifest and result must bind that exact receipt and source.
Missing evidence, source drift after clearance, a result that predates the
PASS commit, or any G-0133 verdict other than `PASS` stops `CANNOT_VERIFY`.

## Common exact checks

The audit checker will be written independently after admission and will not
import, call, or copy the G-0132 producer. It must:

1. Rehash at entry and exit the protocol, G-0128 result and transitive inputs,
   G-0131 report/receipt, G-0133 receipt, frozen source/Cargo/executable, the
   one-shot G-0132 manifest, and the result. Reject drift, symlink/path escape,
   resolved duplicates, malformed integers, stale executable, mixed branches,
   missing inputs, or undocumented serialization.
2. Reconstruct the exact order-preserving nonzero projection of the 176
   selected coefficient slots. Require 44 zeros, exactly 132 unique ordered
   nonzero terms, exact sequence/coefficient pairing, positive primitive
   normalization, and no hidden zero, duplicate, reorder, or omitted last term.
3. Independently recover the exact target scale

   ```text
   2289393005496338240468982655090335335732668690900751540287809289663720291914849699943112917639850352050294840444775090516901570116753181129941246082620
   ```

   and apply the target correction exactly once: subtract
   `target_scale * 11!`, with `11! = 39,916,800`, from linear coordinate 10
   only. No hinge or coordinate 0--9 receives a target subtraction.
4. Reconstruct terms from their frozen family records rather than cached
   380-row columns. Recheck the exact ordered set, digest, and zero value of all
   68 carried G-0128 hinge directions, while treating those 68 only as controls
   and never as the complete direction universe.
5. Reconcile per-term and total orbit censuses. A complete replay contains
   `132 * 11! = 5,269,017,600` labelled contributions, including stabilizer
   duplicates and the final contribution of the final term. Skipped,
   unclassified, failed, duplicated, or exception-swallowed work is fatal.
6. Verify no-overwrite custody: manifest before computation, exclusive
   same-directory temporary publication, flush/fsync, atomic link, directory
   fsync, immediate prepublication rehash, no pre-existing final path, and an
   absent unselected NONMEMBER output. Atomicity that cannot be evidenced is
   not inferred from a valid-looking JSON result.

All decision-bearing arithmetic is signed arbitrary-precision integer
arithmetic. Floating point, tolerance, sampled directions, fixed-width
overflow, or modular equality cannot decide either branch.

## Branch R — `MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL`

Using a separately written exact route, independently regenerate the reported
primitive hinge direction (or linear coordinate) and reprice its residual from
all 132 terms and all corresponding labelled orbit contributions. Require the
same canonical sign/gcd orientation and the same exact nonzero integer.

For a reported hinge, independently test every canonical hinge that precedes
it when computationally feasible. For a reported linear residual, firstness
requires exact zero of every hinge and every earlier linear coordinate. The
report must state `lexicographic_first = VERIFIED` or `NOT_VERIFIED`; lack of
resources never permits an inferred firstness claim. An independently exact
nonzero residual is sufficient to refute **only this coefficient vector**, even
if firstness is not verified. It does not establish frozen-family
nonmembership, a MAX11 lower bound, or any unrestricted-network claim.

## Branch Z — `MEMBER_EXACT_GLOBAL_NORMAL_FORM_ZERO`

No consistency verdict is allowed without an independent complete BigInt
replay of all 132 terms and all `11!` labelled orbits per term. The checker must
dynamically accumulate every canonical primitive active hinge direction and
all 11 linear coordinates, then apply the exact target subtraction above and
obtain exact zero everywhere. A sampled, 68-direction-only, modular, digest-
only, or producer-cached zero is forbidden. Resource exhaustion yields
`CANNOT_VERIFY`, never a weakened zero verdict.

## Hostile controls and verdicts

The independent terminal path must accept a known exact-zero fixture and reject
at least: `+1` to the first coefficient, the final nonzero term, or target
scale; omission of the final term or final orbit contribution; subtraction in
the wrong coordinate; direction sign/gcd, branch-swap, relabelling, or linear-
orientation corruption; omission/mutation of one carried direction; a planted
nonzero divisible by every screening prime; and a one-unit mutation of the
reported residual. Census, hash, serialization, pre-existing-output, and
post-link failure mutants must fail closed without a scientific result.

Verdicts are:

- `CONSISTENT_RESIDUAL`: the exact nonzero value and the reported firstness are
  independently verified;
- `EXACT_VECTOR_REFUTATION_ONLY`: an exact nonzero is independently verified
  but lexicographic firstness is not;
- `CONSISTENT_ZERO`: the complete all-term/all-orbit/all-coordinate replay is
  exact zero;
- `INCONSISTENT`: a decision-bearing reconstruction contradicts the result or
  a hostile mutant reaches acceptance; or
- `CANNOT_VERIFY`: custody, specification, evidence, or resources prevent a
  precommitted obligation.

Even `CONSISTENT_ZERO` establishes only the frozen global orbit identity. G-0134
refuses promotion to a compiled two-hidden-layer architecture, a MAX11
representability claim, `REFEREED`, `FORMALIZED`, or a Lean theorem until a
separately preregistered exact compilation and independent compiled-network
replay are complete.
