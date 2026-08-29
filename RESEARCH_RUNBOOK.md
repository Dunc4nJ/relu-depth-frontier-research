# RESEARCH RUNBOOK — relu-depth-frontier-research

The per-campaign operating notes: how THIS campaign runs the standard machinery. Method lives in the
package; only campaign-specific bindings belong here.

## Bound runtime

`./skill-runtime` is the only package-rail entry point from this workspace. Before every dispatch it
checks `.skill-runtime.toml`: canonical package root, skill version, and the recorded package-content
digest must still match. A mismatch REFUSES execution; it never silently rebinds. This detects ordinary
runtime drift. It is not a signed or tamper-proof security boundary.

These are the cold-safe literal commands. A freshly bootstrapped workspace MUST run all seven exactly as
written:

<!-- COLD-E2E:BEGIN -->
```bash
./skill-runtime binding-status
./skill-runtime detect
./skill-runtime verify-quick
./skill-runtime view
./skill-runtime lockbox status
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
   For a quantitative subject, the control gates come FIRST inside this step: no strategy number is
   discussed until all six are green as `control-run` evidence (§Control gates, below).
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

A11's control runners live in the package, not here. `./skill-runtime gates` is how this workspace
reaches them:

```bash
./skill-runtime gates list                     # all fourteen control runners + method strings
./skill-runtime gates show {RUNNER_OR_METHOD}  # contract, both-direction demo, honest limit
./skill-runtime gates demo {RUNNER_OR_METHOD}  # watch a hostile arm caught and an honest arm pass
./skill-runtime gates record {METHOD}          # the exact control-run evidence skeleton
```

**Those runners discharge nothing.** They run seeded synthetic fixtures and print a verdict about
themselves; they accept no pipeline, subject, or config, because no package can ship a harness for
an arbitrary pipeline. A gate is discharged only by a harness built against THIS campaign's
subject — the exact code, data, and environment under review — recorded as `control-run` evidence
whose `method` is one of six exact strings: `planted-alpha` · `lookahead-probe` ·
`random-after-cost` · `pnl-reconcile` · `truncation-refusal` · `cross-subject-rejection`. Equality
is exact; a method string that merely contains one of these discharges nothing.
`references/CONTROL-GATES.md` is the construction guide and the discharge procedure.

Both arms, every gate: the hostile case must be CAUGHT and the honest case must PASS. Any pipeline
change unbinds every gate — re-run and re-record, because the record is bound to the bytes that
produced it. `./skill-runtime verify-quick` reports what is still missing as
`control gate '<method>' is not green` inside its `walk-obligations` result.

What a green gate establishes is SHAPE — a contained artifact whose digest still matches its
bytes, an exact method string, a subject binding that matches the implementation-claim, and the
joined preregistered experiment and route. **Whether what ran was truly a planted-alpha recovery
stays JUDGMENT** (`references/THREAT-MODEL.md` RR-06). Do not write a sentence that upgrades a
green gate into a claim about the world.

P10 uses `./skill-runtime verify-full` to inspect replay recipes, pins, and local authorizations;
ordinary full mode executes zero commands. Any separately authorized replay is one exact evidence
handle and is not sandboxed merely because the operator consented. Every mutating lockbox or
convergence command consumes a just-read canonical-state parent:

To execute one replay locally, first add its exact closed-form authorization row inside the
`REPLAY-AUTHORIZATIONS-V1` block in `TOOLCHAIN.md`, check that `./skill-runtime verify-full` is green,
then give the second explicit consent:

```bash
./skill-runtime execute-replay E-#### --authorize-local-execution
```

The executor accepts one handle, verifies the command and environment-manifest digests, bounds time
and output, rejects canonical-state mutation, and checks the output artifact digest. It is not a
sandbox: the authorized command can access anything the current user can access.

The lockbox is sealed at P1 and opened once at P12. **A commit is mandatory between the two**, not
housekeeping afterwards: `open` refuses unless every canonical path — `lockbox/manifest.toml`
included — is clean at HEAD, so a seal that was never committed refuses its own open with
`ERR-LOCKBOX: open requires a clean committed pre-open canonical baseline: lockbox/manifest.toml
is not present at HEAD`. Each segment below is literal and complete on its own; they are separated
because a whole campaign runs between them.

```bash
# P1 — seal the holdout range, then COMMIT the seal. The commit is part of sealing.
parent=$(./skill-runtime state-digest)
./skill-runtime lockbox seal {PATH...} --by {ROLE} --expect-state "$parent"
git add lockbox/manifest.toml && git commit -m "lockbox: seal L-0001"
```

```bash
# P12 — the one-shot open. It also refuses unless an eligible latest claim stands exactly at
# COST_AWARE_DEV with all six frontier control gates green; see the gate block above.
parent=$(./skill-runtime state-digest)
./skill-runtime lockbox open --by {VERIFIER_ROLE} --expect-state "$parent"
# Before reading/running against the holdout, commit the sole dirty canonical mutation:
git add lockbox/manifest.toml && git commit -m "lockbox: commit one-shot open L-####"
```

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

Read-only forms are `./skill-runtime lockbox status` and `./skill-runtime convergence status`. A parent
is single-proposal context, not a reusable token. `ERR-CONFLICT` means another cooperative mutation won:
re-read the changed campaign state, reconsider the proposal, obtain a fresh digest, and retry only if it
still applies.

For a quantitative campaign, complete both typed contract templates before
recording cost-aware evidence, then bind their exact current bytes:

```bash
quant_contract_sha256=$(./skill-runtime quant-contract-digest)
```

Copy that value into the exact `method = "cost-model-application"` computation
record together with every applied `cost_facets` entry and the central, stress,
and cost-floor outcomes. The command refuses incomplete contracts; editing
either contract later changes the digest and revokes that evidence's standing.

The coordination lock is advisory and same-filesystem only. It prevents lost updates among these
package writers; it does not stop a same-user process from editing files directly or ignoring the lock,
and it is not an external custody or multi-user security boundary. Manual canonical edits remain governed
by `verify-quick` and the round Git anchor.

## Campaign bindings
- Domain pack: {domains/quantitative-trading.md | domains/mathematics.md | {DOMAIN}_EPISTEMICS.md}
- Route: {W#} · Referee roster: {ROLE/INSTANCE_NAMES} · Cross-family transport: {BINDING}
- Compute policy: {LOCAL | offload rules} · Heavy-run approval: {REQUIRED_ABOVE_N_MINUTES}

## Recovery
- Interrupted mid-round: the ledger is append-only — re-run `./skill-runtime verify-quick`, reconcile
  `ROUNDS.md`, continue. Harvest any partial review WITH attribution; it does not count as complete.
- Runtime binding refusal: do not edit `.skill-runtime.toml` or `skill-runtime`. Restore the recorded
  package bytes/location. To adopt a new package deliberately, bootstrap a new workspace under P0 and
  import this workspace as quarantined prior material; no in-place rebind is supported.
- Suspected corruption: restore from the last round commit; ledgers are never edited in place.
