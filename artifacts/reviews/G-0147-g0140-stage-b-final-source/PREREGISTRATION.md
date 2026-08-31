# G-0147 preregistration — G-0140 Stage-B final source/custody audit

Date: 2026-08-31
Reviewer: CyanSwan (Codex / GPT-5; fresh same-lineage context)
Mode: W2 read-only source/custody audit
Evidence ceiling: T1 same-lineage, outcome-blind source audit

## Decision and no-claim boundary

This is a single bounded admission gate for the exact frozen G-0140 Stage-B producer bytes. It may
clear only source/custody fitness. It cannot observe or promote a scientific result, validate a
candidate, replay Stage B, or establish any mathematical claim.

The terminal PASS claim, if earned, is exactly:

> T1 source/custody clearance for the exact frozen Stage-B producer bytes only; no scientific
> manifest, input, or output was observed, no scientific replay was run, and no mathematical claim
> is promoted.

Any failed obligation below produces an honest FAIL receipt under the prescribed schema, naming
the minimal blocker. No partial credit, severity shopping, or inferred equivalence can produce a
consumable PASS.

## Frozen subject

Git commit: `f55df23361382a9b99b5ca3c07794611a7253c6c`

Four subject bindings are in scope, all as exact commit-object bytes and exact working bytes:

1. `artifacts/math/G-0140/stage_b_pricer/src/main.rs`
   - required SHA-256: `f6c4c4b210a32c8453626fd9a63bfde8a3083f6fb083dce56646a3361289390a`
2. `artifacts/math/G-0140/stage_b_pricer/Cargo.toml`
   - required identity: exact blob at the frozen commit; SHA-256 will be independently measured
     only after this preregistration is pushed
3. `artifacts/math/G-0140/stage_b_pricer/Cargo.lock`
   - required identity: exact blob at the frozen commit; SHA-256 will be independently measured
     only after this preregistration is pushed
4. `artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-coordinate-pricer`
   - required SHA-256: `0dcb50e154797ee8104457a93ce172a46054d9a5836c499cf31796134ccb5050`

The commit object, an isolated extraction, and the working tree must agree for every binding.
Recompiling an approximately equivalent binary is not a substitute for the frozen executable.

## Outcome-blindness and permitted surfaces

Before inspecting any subject source or running any check, this file must be committed and pushed.
After that point the audit may inspect only:

- the four frozen subject bindings above;
- the historical G-0142 FAIL record and its checker/review artifacts;
- source/schema/interface code needed to establish the current Stage-A output contract;
- non-scientific review receipts needed to establish required admission constants;
- synthetic fixtures created by this audit;
- the executable's self-test mode; and
- the executable's outcome-blind static-preflight mode, with only the frozen public panel and
  G-0135 candidate paths already hard-coded/named by the subject source supplied as opaque inputs.

The audit must not open, print, hash directly, parse outside static preflight, or otherwise inspect
any future G-0140 scientific manifest, any Stage-A scientific result, any candidate/scientific
input, or any Stage-B scientific output. It must not invoke the science-producing runtime mode.
Static preflight is allowed only because it does not consume any future G-0140 output and is
required to expose non-outcome structural counts and bindings.

## Predeclared obligations and falsifiers

PASS requires every item below. A single falsifier is terminal.

### O1 — exact four-file custody

- Resolve each path at the frozen commit without following a working-tree substitute.
- Extract the four commit blobs into a fresh isolated temporary custody root.
- Independently SHA-256 the commit blob, isolated copy, and working file.
- Require all three byte streams equal for all four paths, plus the two predeclared source/binary
  digests above.
- Rehash all four working files and isolated copies at audit end; any drift is FAIL.
- Record exact Cargo.toml and Cargo.lock digests in the final binding record and receipt.

Hostile controls: mutate a copied byte, substitute a same-name file from another revision, remove a
binding, and present a working file that differs from its commit blob. The custody checker must
reject each.

### O2 — repair the exact G-0142 schema blockers

The frozen implementation must reject unknown JSON fields for each of:

- `Candidate`;
- `StageAReceipt`;
- `AccumulatedDirectionCheck`; and
- imported `Record`.

It must nevertheless accept the complete legitimate current `Record` schema; a narrowed synthetic
surrogate is not sufficient. Admission of the upstream source audit must require exact schema and
exact result constants, not presence, substring, prefix, a generic PASS, or a lookalike field.

Hostile controls: inject one unknown field at every object level; delete or mistype every required
field; use the legitimate full record; and try the four source-audit combinations
`(right schema,right result)`, `(right,wrong)`, `(wrong,right)`, `(wrong,wrong)`. Only the first may
pass.

### O3 — complete fail-closed receipt and output schemas

The top-level Stage-B output and consumed Stage-A receipt must have complete, explicit schemas:
unknown fields rejected, all security/custody fields mandatory, fixed schema/result values checked
by equality, and no `Option`, `default`, `flatten`, aliases, coercions, or ignored duplicate keys
that can omit or disguise a required obligation.

Hostile controls: add an unknown top-level field; omit each required field one at a time; replace
constants with semantic lookalikes; use wrong JSON types; duplicate a security-sensitive key; and
substitute a valid inner object under the wrong outer schema/result.

### O4 — mandatory upstream and control bindings

The manifest, Stage-A producer/receipt/result, candidate, G-0139 source-audit/control, and mutation
control bindings required by the protocol must all be mandatory and validated by exact path,
SHA-256, schema, result, and/or claim boundary as applicable. No missing or optional binding may
fail open. A binding to a scientific object may be audited structurally without opening that
object in this review.

Hostile controls: omit each binding; swap any two digests; use a correct digest under a wrong path;
use uppercase, truncated, prefixed, or whitespace-padded digests; and replace a required exact
schema/result with a plausible lookalike.

### O5 — current Stage-A interface compatibility

Compare the frozen Stage-B consumer type against the current committed Stage-A producer's declared
output interface without opening a Stage-A scientific result. Every legitimate required field and
type must be accepted; every field the protocol declares closed must reject additions. Any drift
that would reject real output or silently ignore new fields is FAIL.

Hostile controls: construct a synthetic full positive fixture from the declared producer interface,
then independently mutate each field name/type/requiredness and require rejection where specified.

### O6 — exact arithmetic and no narrowing

All potentially unbounded integer quantities and accumulated-direction checks must remain exact
(BigInt or equivalently proved exact representation) through parse, arithmetic, comparison, and
serialization. No lossy `as` cast, float round-trip, bounded parse, or narrowing intermediary may
sit on a load-bearing path.

Hostile controls: positive and negative integers beyond `u64` and `i128`, boundary-adjacent values,
large cancellation pairs, non-integers, exponent notation, and overlong decimal strings. Exact
integers must round-trip; malformed/non-integral representations must fail closed.

### O7 — exact finite census and deterministic order

The structural census must be exactly 128 directions by 163,740 rows, hence 20,958,720
direction-row checks. Direction order and row order must be canonical and deterministic, not
filesystem, hash-map, locale, thread-schedule, or input-incidental order.

Hostile controls: 127/129 directions, 163,739/163,741 rows, duplicate/missing direction IDs,
permuted rows, repeated self-test/preflight runs, and deterministic comparison of their
non-scientific structural reports.

### O8 — compiled-byte/source custody and semantic admission

The executable actually tested must be the frozen release byte string and must internally bind the
expected source/protocol identity strongly enough that a same-name or semantic-lookalike program
cannot inherit clearance. Self-test success alone is not identity. Any audit admission consumed by
the producer must check exact schema/result and required subject bindings.

Hostile controls: renamed executable, one-byte-mutated executable, wrong source digest, correct
generic PASS under the wrong schema, correct schema with wrong result, and correct constants with a
different subject hash.

### O9 — overwrite refusal, fail-closed I/O, and end rehash

Scientific output creation must refuse an existing output path atomically; partial writes must not
be promoted as complete; every read, parse, hash, count, and write error must propagate to nonzero
failure. Inputs/custody bindings must be rehashed after processing so time-of-check/time-of-use
mutation cannot pass silently.

Hostile controls: pre-create the target output, make its parent unwritable/missing, truncate an
input during a synthetic mutation-control test if the shipped self-test provides one, induce a
late write error, and change a copied input between initial hash and final rehash. Existing bytes
must remain unchanged after overwrite refusal.

### O10 — runtime-mode firewall

Only self-test and outcome-blind static preflight may execute. Each must be explicitly selected,
must not fall through to science, must not create Stage-B scientific output, and must fail closed on
unknown/mixed modes. The audit command log must demonstrate that no scientific mode ran and must
not contain scientific outcomes.

Hostile controls: no mode, unknown mode, both allowed modes together, extra positional arguments,
and output-path flags in an allowed mode. None may trigger scientific execution.

## Evidence plan

The final review bundle will contain, at minimum:

- a machine-readable four-file custody manifest;
- one or more audit checker scripts confined to this review directory;
- synthetic fixtures only (never copied scientific inputs or outputs);
- raw command/result logs with exit codes and stderr retained;
- an obligation-by-obligation adversarial review report;
- an anti-ceremony and honesty inventory; and
- exactly one PASS or honest FAIL receipt under schema
  `max11-g0147-g0140-stage-b-final-source-audit-v1`.

The PASS receipt will use verdict `PASS`, result `SOURCE_CUSTODY_AUDIT_PASS_T1`, evidence class
`T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT`, all four observation/replay booleans false, the exact
frozen Git commit, `commit_object_and_working_bytes_equal_for_all_bindings=true`, and nested
`{path,sha256}` objects for all four files. It will not contain a self-referential audit commit.

## Anti-ceremony creation gate (filled before creation)

- Boundary test: process. Runtime does not branch on this Markdown preregistration.
- Consumer: the G-0147 operator and the later source-audit admission decision.
- Gate: the exact frozen Stage-B producer cannot receive T1 source/custody clearance without an
  outcome-blind, precommitted attack plan.
- Observed defect: historical G-0142 failed on unknown-field acceptance and inexact source-audit
  admission, demonstrating that an outcome-aware checklist could be silently tailored after seeing
  the repair.
- Retirement: it stops governing when this one frozen-subject receipt is emitted; it remains only
  as immutable provenance for that decision and creates no recurring workflow.
- Integrity-control exception: not invoked; the ordinary creation gate is satisfied.
- Opportunity cost: the ready capability is this audit itself. The minimum preregistration is a
  mandated bias control and takes one bounded pass; any further governance design would be parked.
- Verdict: **LEGITIMATE GATE**, minimum one-file version.
