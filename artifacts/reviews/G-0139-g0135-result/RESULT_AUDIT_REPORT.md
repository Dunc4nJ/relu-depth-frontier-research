# G-0139 outcome-aware T1 result audit of G-0135 Stage D

## Verdict

**PASS — `CONSISTENT_RESIDUAL_T1`** for the exact committed subject
`artifacts/math/G-0135/new_member_global_replay_v1.json`, SHA-256
`d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875`,
at commit `270a62455097cbaf0a8f80426c54b6121d1afcba`.

This is same-lineage, outcome-aware T1 evidence.  Reviewer `GoldenSnow`
(Codex/GPT-5) had previously performed the G-0136 Stage-A source audit.  The
reviewer did not import or translate the Stage-D implementation, did not invoke
the Stage-D executable, and did not rerun the Stage-D scientific replay.
Stage-D bound files were consumed only by streaming SHA-256 rehashes.

The verdict establishes consistency of this exact 135-term certificate and
these exact committed bytes.  It does **not** establish T2 independence,
family completeness, frozen-family nonmembership, a MAX11 lower bound,
unrestricted two-hidden-layer nonrepresentability, the all-n target,
`REFEREED`, `FORMALIZED`, or a Lean theorem.

## Independent replay

The separately written checker admitted the exact Stage-C certificate, derived
the 135 nonzero terms as the order-preserving projection of its 204 coefficient
slots, checked the positive primitive denominator clearing, and cross-multiplied
every rational/integer coefficient pair.

For each frozen family record it independently enumerated active-vertex
permutations and inactive-label placements, applied inactive-label factorial
multiplicity, canonicalized primitive signed hinge directions, and formed the
complete dynamic hinge union.  Each term's 11 linear coordinates were checked
by both a subset dynamic program and an exhaustive permutation/placement route.
Scientific aggregation used signed arbitrary-precision `num_bigint::BigInt`.

The checker independently decoded the sequence-major signed-i128 cache for all
301 panel rows and rebuilt the remaining 11 linear plus 100 accumulated-hinge
rows.  It then replayed all 412 Stage-C equations exactly.  Producer fields
were comparison outputs only; they were not inputs to the derivation.

## Exact findings

| Check | Independently recomputed value |
|---|---|
| Nonzero terms / selected slots | 135 / 204 |
| Labelled permutations | 5,388,768,000 |
| Hinge entries processed | 4,409,740 |
| Aggregate hinge support | 147,062 |
| Nonzero hinge residuals | 146,950 |
| All accumulated directions | 100 exact zeros |
| Linear residuals | 11 exact zeros |
| Finite replay | 412 exact zero residuals |
| First nonzero direction | `[0,0,0,0,0,0,1,-2,-2,1,2]` |
| Aggregate hinge digest | `168f91bd8735c778b492fd7f2f7414d4428dfd1af8af21bd8afe294c1b2ecf60` |
| Nonzero hinge digest | `9d7dd907d6885ab5e5b5a5a783b0212da8f145c1202fdb4de2c90f44d55023aa` |
| Complete residual digest | `3f9ca1a339ad8cdcb3260b12a48b554b4c5b401144cf5cd627f7ec1db30a7ce6` |
| Term transcript digest | `7670731c72b64e89517d4d68d8ca44b73947db3c2a24938a4e843dfb9d8c1bbd` |
| Finite 412-row digest | `65fbdf70dc944ed94e66dec089c0368b15288f1f881fcd93b6ff243f889a7828` |
| Next Batch32 direction digest | `b91dcdedc2834f6d0639846dc258cd6bf4aba42c0debae34761fd857f25384ce` |
| Next Batch32 coefficient digest | `7a95296dc09b6a156f2ec385e1f6b4e94907a9c8c0ae0c18428d16a925903321` |

The first nonzero coefficient was independently reproduced exactly as
`511838695529252537134751622979004566912532181650940275812075139014937590867028110892243795641237175143066549672701558636166678186077128694292857947716107231627691338960`.

All 135 independently rebuilt term receipts, all 100 accumulated-direction
receipts, and all 32 next-selected rows were field-for-field equal to the
subject.  The result branch was therefore reproduced as
`EXACT_RESIDUAL_BATCH_CONTINUE`.

## Hostile controls and custody

The acceptance path rejected every preregistered hostile control: first
coefficient `+1`; final-term omission; sequence/term reversal; one-count and
whole-orbit census decrements; accumulated-direction omission; target-scale
`+1`; target-coordinate `+1`; wrong target coordinate; direction sign and gcd
corruption; next-row reordering; missing coefficient LF; first-residual `+1`;
subject/transitive SHA mutations; path escape; symlink substitution; and false
reverse ancestry.  The finite coefficient mutant failed first at row 0 with
digest `0336b686fb8d09f9de22146c81dd82d1daf7fc8c1530cc6485b2530b0865b2de`.

Entry and exit rehashes agreed for 8 fixed inputs and all 92 distinct
transitive bindings.  Git custody established the strict Stage-C → result →
audit-preregistration ancestry and the single-path result/preregistration
commits.  No-overwrite publication used `create_new` only after every
scientific, mutation, and exit-custody check passed.

The final receipt is
`artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json`, SHA-256
`282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f`.
The checker source SHA-256 is
`29f157e6109c7c8a6d28faac9980c94a8e6cddc8aab25505d3488c018e25aa55`.

## Execution record and disclosed preliminary failure

The final acceptance-path command completed in 83.691 seconds and emitted
`G-0139 PASS CONSISTENT_RESIDUAL_T1`.  A separate temporary publication run
also passed in 90.879 seconds before the final no-overwrite run.

The first full attempt rebuilt all 135 forms but stopped in the hostile-control
phase and emitted no receipt.  The checker had interpreted the disclosed
`target_coordinate_10_plus_one` control as a scale-weighted perturbation rather
than the protocol's literal post-scaling one-unit perturbation.  The control
was corrected from `-target_scale` to `-1`; the scientific replay algorithm and
subject anchors were unchanged.  Both subsequent complete runs passed.  This
failure is disclosed because omitting it would make the validation history
look cleaner than it was.

Post-publication checks observed:

- `cargo fmt --check`: exit 0.
- `cargo clippy --release --locked ... -- -D warnings`: exit 0.
- Clean-room executable `--self-test`: explicit PASS with nonzero, sign, gcd,
  and canonical-decimal negative controls.
- Full 135-term acceptance path: explicit PASS; not a zero-run test.
- `./skill-runtime verify-quick`: 0 findings; 6 dead ends, 0 fired.
- `git diff --check`: clean.

## Completion honesty and real-work audit

Window: this G-0139 work item, beginning with preregistration commit
`47b32a9`.  Core purpose: produce reproducible frontier-math evidence with
explicit epistemic limits.  Classification: USER 1 (the result audit), ENABLER
1 (the executable checker), PROCESS 2 (frozen preregistration and this handoff
report), UNKNOWN 0.  Verdict: **HEALTHY**.  The process artifacts were bounded
and gated a completed executable replay; they did not substitute for it.  The
two-minute demo is the final receipt plus a re-execution of the full checker.
No subagents were used and no follow-up item was minted to carry an unmet
condition.

Bounded honesty inventory:

1. No (checked the G-0139 diff, test-path history since 17:00 UTC, and reflog;
   no test was weakened, deleted, skipped, or ignored).
2. No (checked the only fixture: it exercises real enumeration and negative
   controls, while the claimed result depends on the full frozen dataset).
3. No (checked the audit directory; no golden or snapshot was regenerated).
4. Yes, four scoped `#[allow]` declarations suppress only Clippy's
   `needless_range_loop` and `too_many_arguments` style lints.  They do not
   suppress arithmetic, safety, test, or acceptance checks; strict Clippy with
   `-D warnings` still passed.  Disposition: disclosed here; each scope was
   reviewed against the scientific path; the countermeasure is the recorded
   suppression grep and exact source hash.  No behavioral correction was
   warranted because no gate was weakened.
5. No (checked hard-coded constants: they are preregistered comparison anchors;
   every accepted value is independently recomputed from the frozen inputs).
6. No (checked explicit counters and output: 135 terms, 4,409,740 hinge entries,
   and 5,388,768,000 labelled permutations were exercised).
7. No (checked the command log against the verification list above).
8. No (checked receipt/report labels: evidence remains same-lineage,
   outcome-aware T1 and is not presented as T2).
9. No (checked the report includes the failed first full attempt and its exact
   cause before the two successful runs).
10. No (expected negative Git probes silenced only their expected stderr; the
    exit statuses were checked, and no discarded output is cited as evidence).
11. No (checked the frozen acceptance contract; every condition completed
    before PASS publication).
12. No (checked preregistration SHA/commit; it was not edited after the result
    was known and before checker execution).
13. No (checked session structure: no subagent or swarm worker was used).
14. No (checked session structure: no subagent dispatch occurred).
15. No (checked session structure: no subagent report was accepted).
16. No (checked session structure: no panes or subagents existed to farm guard
    paths).
17. No (parent inspection is reported as an additional check, not counted as
    independent scientific confirmation).
18. No (checked all denominators and counts against the frozen preregistration;
    none was selected after the run).
19. The two moments requiring advance explanation are the temporary workspace
    path mismatch after resumption and the first full-run mutant-interpretation
    failure.  The correct repository was resolved by commit identity before any
    edit, and the failure chain is disclosed above.
20. The strongest evidence is the no-overwrite result receipt bound to the
    exact checker/input hashes and the re-executable full command in
    `SELF_TEST_RECEIPT.json`.

The bounded `cass` sweep found zero hits for the five prescribed
test/golden/done concealment phrases and for the session-specific failed-mutant
phrase.  The lexical index was stale but searchable; a capped background
refresh was started, so the null result is recorded as bounded rather than
universal.
