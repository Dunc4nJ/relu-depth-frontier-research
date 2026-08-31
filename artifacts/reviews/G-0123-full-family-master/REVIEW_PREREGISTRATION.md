# G-0123 exact-Q full-family master: fresh-context review preregistration

- Frozen at: `2026-08-31T02:02:34Z`
- Reviewer: `SageBridge` (Codex / GPT-5; same-family fresh context, therefore T1 only)
- Mode: read-only adversarial audit of the proposed scientific driver
- Subject preregistration: `artifacts/math/G-0121/FULL_FAMILY_MASTER_PREREGISTRATION.md`
- Subject implementation: `artifacts/math/G-0123/full_family_master.py`
- Forbidden input: every scientific result produced by the subject driver, including the future path named in the subject preregistration

## Exact review question

Does the proposed driver, without relying on its own future scientific output, implement the preregistered exact-rational all-column master strongly enough that either terminal branch has the narrow meaning claimed for it?

The two branches to audit are:

1. finite-family membership on the exact 348-row augmented system, yielding only a finite-row candidate that still requires independent complete global replay; and
2. finite-family nonmembership, permitted only after an exact separator has been checked against all 163,740 columns with no missed violation, yielding only the bounded no-go for the frozen dictionary and row system.

No outcome from the scientific run will be read or inferred during this review. The reviewer will not execute the scientific master.

## Precommitted audit obligations

1. **Statement match.** Reconstruct the row order, target, frozen dictionary, initial basis, stopping rules, and allowed conclusions from the prose preregistration, then compare them to code.
2. **Exact arithmetic.** Check that every rank, separator, coefficient, and replay equality is over exact integers/rationals, with no float, modular-only, or lossy conversion in a decision path.
3. **All-column separation.** Verify that nonmembership can be returned only after a deterministic scan of every declared column, including the final column, and that a separator violation is defined with the correct orientation and exact target pairing.
4. **Membership reconstruction.** Verify that reported coefficients correspond to the actual selected columns, normalization preserves the represented target, zero terms are treated consistently, and the candidate is replayed exactly on every augmented row before emission.
5. **Bindings and custody.** Trace every load-bearing datum transitively to a fixed path, byte size, digest, schema/count/order assertion, and source binding. Check source-staleness refusal and exclusive output creation.
6. **Fail-closed behavior.** Exercise malformed, truncated, reordered, duplicated, hash-mismatched, stale-source, pre-existing-output, and semantically inconsistent small fixtures where the interface permits doing so without running the scientific master.
7. **Hostile controls.** Check that the planted coefficient mutation and separator/target mutation each force rejection in the branch they are meant to protect, rather than merely changing a digest.
8. **No-claim boundary.** Reject any code or prose path that upgrades a 348-row membership result to a global identity, or a frozen-family nonmembership result to an unrestricted impossibility theorem.

## Precommitted attack lenses

- off-by-one omission in the 163,740-column scan;
- a separator calculated for one row matrix but paired with a different target;
- column/record order drift between cache, price table, coordinate payloads, and reported indices;
- coefficient normalization that changes the represented vector;
- pivot-support versus coefficient-position mismatch;
- exactness laundering through Python integer coercion, JSON number parsing, or FLINT conversion;
- a digest that binds only a top-level receipt while leaving a transitive payload mutable;
- stale executable/source acceptance;
- hostile controls that do not cross the actual terminal decision path;
- `O_EXCL` implemented too late, after expensive work or after overwriting an existing artifact;
- a final `no violation` branch reached after a partial scan or swallowed exception.

## Verdict vocabulary

- `PASS`: no correctness blocker found for the narrow preregistered meanings; residual reproducibility limitations are enumerated.
- `CONDITIONAL_PASS`: core mathematics matches, but a specified non-scientific repair or missing binding must be discharged before the run can carry evidence.
- `FAIL`: at least one reachable path can emit a terminal result whose narrow stated meaning is not established.
- `INCONCLUSIVE`: the audit cannot reach a verdict without reading or executing a forbidden scientific result.

Severity will be assigned from consequence, not presentation: `BLOCKER`, `MAJOR`, `MINOR`, or `NOTE`. A same-family T1 review cannot promote the research claim to `REFEREED` or `FORMALIZED` standing.
