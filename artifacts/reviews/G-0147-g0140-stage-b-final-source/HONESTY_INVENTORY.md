# G-0147 anti-ceremony and honesty inventory

Session/window: CyanSwan's full G-0147 session on 2026-08-31, one preregistration commit and the
uncommitted final review bundle before handoff.

## Process creation gate

The filled creation gate is in `PREREGISTRATION.md`. The audit is an explicitly requested,
decision-changing authorization gate responding to the observed G-0142 failures; it retires when
this frozen-subject decision is emitted. Verdict: `LEGITIMATE GATE`. The upstream FAIL changed the
decision immediately, so further machinery was stopped.

## Real-work audit worksheet

- Project purpose: determine whether every finite maximum has an exact two-hidden-layer ReLU
  representation, with MAX11 as the first unresolved retrieved rung, while refusing cousins as a
  settlement.
- Window record examined: `git log --oneline --stat -2 -- <G-0147 review path>` and the exact
  current review-path status/diff.
- Classification: USER 0; ENABLER 1 (the source-admission decision); PROCESS 2 (preregistration and
  handoff/report); UNKNOWN 0.
- Most user-visible item: none; this task intentionally shipped an authorization decision. The
  two-minute demo is the frozen G-0146 FAIL plus the Stage-B hard-coded PASS predicate causing a
  non-consumable G-0147 receipt.
- If the process items had not happened, an invalid Stage-B authorization could have proceeded;
  the observed decision would differ.
- The enabler was exercised by the orchestrator's explicit stop/FAIL decision for G-0140.
- Oldest user-facing open item: not inspected because it is outside this bounded audit and the
  stop directive prohibited expanding scope.
- Swarm question: not applicable; CyanSwan delegated no work and spawned no agents.
- No plan/spec edit stood in for implementation and no follow-up was minted to launder unmet
  acceptance. Producer repair was explicitly forbidden in W2 audit mode.
- Verdict: `HEALTHY_BOUNDED_GATE`; process was limited to the requested decision and stopped as
  soon as the terminal blocker arrived. Correction dispatched: stop broad audit, emit FAIL, return
  required refreeze obligations to the orchestrator.

## Honesty inventory

1. No (checked: the review-path commit/stat and full uncommitted review diff; no producer tests,
   CI, lint configuration, or historical gates were weakened, deleted, ignored, or edited).
2. No (checked: synthetic decoy and Serde fixtures are explicitly labeled hostile probes and do
   not stand in for scientific behavior; the real executable self-test/static preflight also ran).
3. No (checked: no golden or snapshot file was generated or updated).
4. Yes, the independent audit checker was authored and corrected during the same review. It never
   modified the producer or its tests. The first uncommitted run exposed two checker defects: a
   post-write relative-path formatting crash and an overbroad attribute detector. The generated
   result was deleted, both defects were corrected in the checker, and self-test plus audit were
   rerun cleanly with all hostile controls green. This is disclosed here and in `COMMAND_LOG.md`;
   no tolerance, timeout, assertion, or producer gate was relaxed.
5. No (checked: there is no demo hard-code, environment success branch, narrowed denominator, or
   fixture-specific PASS path; planted mutants must fail and the subject audit exits nonzero).
6. No (checked: producer self-test reported its named PASS, static preflight parsed 163,740 real
   records/135 terms, the Serde probe asserted three behaviors, and seven hostile controls ran).
7. No (checked: every command claimed in the report appears in the tool transcript or retained
   `CHECK_RESULTS.json`; the aborted state is stated explicitly).
8. No (checked: the recursive-binding witness is labeled a source-modeled predicate, not direct
   invocation of a private Rust function; all evidence remains T1 and no scientific claim is made).
9. No (checked: the upstream FAIL is the first decision in the report; the three already-observed
   partial-check failures are also disclosed rather than buried).
10. No (checked: cited producer/checker commands captured stderr and record its content/hash; no
    cited command redirects stderr to null).
11. No (checked: CyanSwan closes no Bead/task; the work is handed to the orchestrator as FAIL with
    unmet refreeze obligations).
12. No (checked: the preregistered PASS contract and frozen subject were not edited after results;
    the receipt uses FAIL rather than changing requirements).
13. Not applicable (no subagent or swarm was delegated by CyanSwan; the parent delegated this
    bounded audit to CyanSwan, who does not close the parent's item).
14. Not applicable (no subagent dispatch occurred).
15. Not applicable (no subagent report was accepted).
16. Not applicable (no panes/subagents existed under CyanSwan).
17. No (checked: same-lineage status is recorded as T1; agreement with G-0146 is not promoted as
    independent confirmation).
18. No (checked: the preregistration fixed the four bindings, 128 by 163,740 census, and PASS/FAIL
    rule before inspection; no denominator was selected after results).

Older-session sweep: not run. CyanSwan is a fresh identity with no earlier session in this project,
and the orchestrator explicitly ordered immediate bounded stop rather than expanding into unrelated
session mining.

19. Yes: the owner should know about the checker crash/attribute-detector bug before seeing the
    transcript. It happened before any committed result; the bad generated result was removed, the
    defects were fixed, the checker was rerun from scratch, and this disclosure preserves the full
    chain rather than hiding it.
20. Strongest evidence: the exact G-0146 receipt has identical committed/working SHA-256
    `dc01ef4b...`, verdict `FAIL`, and the frozen Stage-B source hard-codes that path/schema while
    requiring PASS. A skeptic can re-execute the four commands in `COMMAND_LOG.md` without opening
    scientific data.

## Disposition

- Corrected in place: yes, both checker defects were fixed before the retained run; no producer or
  historical artifact was changed.
- Disclosed to operator: yes, exact failure chain and the earlier checker defects are in the final
  report and handoff.
- Countermeasure: fail-closed exclusive result publication plus checker self-test/hostile controls;
  the incident is treated as RH-1-style gate/checker co-review risk, so only the clean rerun is
  retained and checker changes are disclosed rather than self-certified silently.

No work was delegated, no scientific artifact was observed, and no task is self-closed.
