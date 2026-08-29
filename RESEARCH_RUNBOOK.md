# RESEARCH RUNBOOK — relu-depth-frontier-research

The per-campaign operating notes: how THIS campaign runs the standard machinery. Method lives in the
package; only campaign-specific bindings belong here.

## Bound runtime

`./skill-runtime` is the only package-rail entry point from this workspace. Before every dispatch it
checks `.skill-runtime.toml`: canonical package root, skill version, and the recorded package-content
digest must still match. A mismatch REFUSES execution; it never silently rebinds. This detects ordinary
runtime drift. It is not a signed or tamper-proof security boundary.

These are the cold-safe literal commands. A fresh session MUST run all six exactly as
written:

<!-- COLD-E2E:BEGIN -->
```bash
./skill-runtime binding-status
./skill-runtime detect
./skill-runtime verify-quick
./skill-runtime view
./skill-runtime convergence status
./skill-runtime verify-full
```
<!-- COLD-E2E:END -->

## Round loop (every round)
1. Run `./skill-runtime verify-quick`; stop if red. On resume this happens before trusting or acting
   on the orientation pointer.
2. Read `STATUS.md`, reconcile its phase/round/commit/count summary against ledger, `ROUNDS.md`, and Git,
   then claim the next work item (mark it claimed in `beads/QUEUE.md`). Active object IDs are checked
   mechanically; the orientation summary is operator-maintained and never grants standing.
3. Do the work; every result lands as ledger records (claims/evidence/routes/experiments) — not prose.
   When computation bears on a mathematical claim, preregister the exact subject, implementation,
   domain, detection floor, and stop/retry predicates before execution. All six campaign controls must
   be green as subject-bound `control-run` evidence before such computation promotes a live claim
   (§Control gates, below). Pure deductive work owes statement matching and adversarial proof review,
   not synthetic computational controls that do not bear on it.
4. Regenerate the view: `./skill-runtime view`. This comes BEFORE the verifying step: the view is
   generated from canon, so verifying a round that touched canon against a stale view reports an
   SE-15 that means nothing. A gate that cries wolf every round is a gate agents learn to ignore.
5. Close the round through the cooperative writer (do not hand-edit `phases/ROUNDS.md`):
   `parent=$(./skill-runtime state-digest)` then
   `./skill-runtime convergence close-round --round auto --phase {P#} --yield {substantive|low-yield} --note "{LEDGER_DELTA}" --expect-state "$parent"`.
   It prints the allocated `R-####`; use it in step 6 and in the commit subject.
6. Dual-write next queue → `STATUS.md` + `beads/QUEUE.md`. Both files must name exactly the same
   active object IDs; mark finished items `- [x] … (done: R-####)` with the round just closed.
7. Run `./skill-runtime verify-quick` → fix anything red before committing. Every canonical mutation
   this round made — records, view, round log, and the dual-write — is now inside what it checks.
8. Commit: `R-####: <one-line ledger delta>`.

## Control gates

The package's demonstration runners live outside this workspace. `./skill-runtime gates` is how this workspace
reaches them:

```bash
./skill-runtime gates list                     # available control runners + exact method strings
./skill-runtime gates show {RUNNER_OR_METHOD}  # contract, both-direction demo, honest limit
./skill-runtime gates demo {RUNNER_OR_METHOD}  # watch a hostile arm caught and an honest arm pass
./skill-runtime gates record {METHOD}          # the exact control-run evidence skeleton
```

**Those runners discharge nothing.** They run seeded synthetic fixtures and print a verdict about
themselves; they accept no pipeline, subject, or config, because no package can ship a harness for
an arbitrary pipeline. A gate is discharged only by a harness built against THIS campaign's
subject — the exact code, data, and environment under review — recorded as `control-run` evidence
whose `method` is one of six exact strings: `known-answer` · `sweep-plant-recovery` ·
`empty-region-null` · `census-reconciliation` · `trivial-witness-null` ·
`metamorphic-invariance`. Equality is exact; a method string that merely contains one of these
discharges nothing.
`references/CONTROL-GATES.md` is the construction guide and the discharge procedure.

This campaign binds the six controls as follows:

| Exact method | Honest/positive arm | Hostile/null arm |
|---|---|---|
| `known-answer` | untouched exact MAX5–MAX10 subjects pass | an independently specified false identity is rejected |
| `sweep-plant-recovery` | a hidden valid control at the registered far edge is recovered | the identical unplanted sweep returns no planted hit |
| `empty-region-null` | a neighboring registered nonempty slice exercises the path | a deliberately impossible/empty registered slice returns no witness |
| `census-reconciliation` | generated = accepted + rejected + skipped + failed, including orbit/row/column totals | a deliberate omission or duplicate is detected |
| `trivial-witness-null` | a valid shape-correct certificate passes | zero, random, and equality-destroying corruptions fail |
| `metamorphic-invariance` | coordinate permutations and positive homogeneous scalings preserve validity | a coefficient perturbation breaking a chamber identity flips the verdict |

Where a control naturally has two arms, the hostile/null case must be caught and the honest case must
pass. Any subject, code, configuration, or environment change unbinds the affected controls: re-run and
re-record them against the new hashes. `./skill-runtime verify-quick` checks record shape and bindings;
the research lead must still inspect whether the implemented test actually instantiates the named method.

What a green gate establishes mechanically is SHAPE — a contained artifact whose digest still matches its
bytes, an exact method string, a subject binding that matches the implementation-claim, and the
joined preregistered experiment and route. **Whether what ran was truly the named mathematical control
stays JUDGMENT** (`references/THREAT-MODEL.md` RR-06). Do not write a sentence that upgrades a
green gate into a claim about the world.

P10 uses `./skill-runtime verify-full` to inspect replay recipes, pins, and local authorizations;
ordinary full mode executes zero commands. Any separately authorized replay is one exact evidence
handle and is not sandboxed merely because the operator consented. Every mutating convergence
command consumes a just-read canonical-state parent:

To execute one replay locally, first add its exact closed-form authorization row inside the
`REPLAY-AUTHORIZATIONS-V1` block in `TOOLCHAIN.md`, check that `./skill-runtime verify-full` is green,
then give the second explicit consent:

```bash
./skill-runtime execute-replay E-#### --authorize-local-execution
```

The executor accepts one handle, verifies the command and environment-manifest digests, bounds time
and output, rejects canonical-state mutation, and checks the output artifact digest. It is not a
sandbox: the authorized command can access anything the current user can access.

### Lockbox and quantitative contracts — not applicable

This W1 mathematics campaign has no dataset, time-ordered holdout, or one-shot sealed evaluation.
Do not seal or open a lockbox and do not interpret P1/P12 as data-access phases. Surprise is provided
instead by withheld known arities/certificates, preregistered corruptions, clean-room implementations,
independent replay, and external referee review. Those objects are ordinary hash-bound artifacts and
must be disclosed in the experiment ledger; they are not a concealed benchmark.

```bash
# after the sealed evaluation, or after any clean adversarial pass
parent=$(./skill-runtime state-digest)
./skill-runtime convergence record-pass --round auto --family "{ATTACK_FAMILY}" --clean --expect-state "$parent"
```

`record-pass` runs the battery itself against the exact state the pass claims and writes a verifier
witness into the row; a clean pass against a red battery is REFUSED (record the honest result with
`--findings substantive` instead), and a pass row typed by hand is refused when the streak is
recomputed. The first pass mints `phases/.pass-witness-key`: commit it with that round and never
delete or ignore it, or the recorded passes stop being re-derivable and the tracker fails closed.

The relevant read-only state form is `./skill-runtime convergence status`. A parent
is single-proposal context, not a reusable token. `ERR-CONFLICT` means another cooperative mutation won:
re-read the changed campaign state, reconsider the proposal, obtain a fresh digest, and retry only if it
still applies.

The `quant-contract-digest` path and the quantitative cost-model evidence class are inactive here.
Computational experiments instead bind code, environment, subject/certificate snapshot, exact domain,
resource ceiling, detection floor, and output digest through the mathematics evidence ladder in
`NEURAL_REPRESENTATION_EPISTEMICS.md`.

The coordination lock is advisory and same-filesystem only. It prevents lost updates among these
package writers; it does not stop a same-user process from editing files directly or ignoring the lock,
and it is not an external custody or multi-user security boundary. Manual canonical edits remain governed
by `verify-quick` and the round Git anchor.

## Campaign bindings
- Domain pack: `domains/mathematics.md` plus the binding W11 translation `NEURAL_REPRESENTATION_EPISTEMICS.md`
- Route: W1 dual prove/refute
- Research lead: Agent Mail identity `CrimsonBirch`; native Codex subagents are bounded same-family T1 challengers, never autonomous promoters
- Referee roster: no T2 reviewer bound at bootstrap; named human or explicitly authorized genuinely different model lineage required for T2+
- Cross-family transport: `NONE`; fail closed for `REFEREED`/`FORMALIZED` promotion until a valid transport record exists
- Compute policy: project-local CPU/storage by default; preregister any run projected above 30 minutes, 16 GiB RAM, or 100 GiB additional storage; human approval is required before paid/external compute

## Recovery
- Interrupted mid-round: the ledger is append-only — re-run `./skill-runtime verify-quick`, reconcile
  `ROUNDS.md`, continue. Harvest any partial review WITH attribution; it does not count as complete.
- Runtime binding refusal: do not edit `.skill-runtime.toml` or `skill-runtime`. Restore the recorded
  package bytes/location. To adopt a new package deliberately, bootstrap a new workspace under P0 and
  import this workspace as quarantined prior material; no in-place rebind is supported.
- Suspected corruption: restore from the last round commit; ledgers are never edited in place.
