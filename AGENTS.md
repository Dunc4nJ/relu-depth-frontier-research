# AGENTS — campaign operating law

## Session initialization

Before editing, call Agent Mail `macro_start_session` with human key `/data/projects/relu-depth-frontier-research`, your actual program/model, and a bounded task description. Use the returned agent name for reservations and mail. Reserve the narrow files you will edit, then release them at handoff.

## Mandatory method

Use `$frontier-research-with-epistemic-humility` in **campaign mode**, domain **mathematics**, W1 dual **prove/refute**. Read its `SKILL.md` completely and follow the workspace runtime. The binding field translation is `NEURAL_REPRESENTATION_EPISTEMICS.md`.

Cold start:

1. Read `README.md`, `START_HERE.md`, `RESEARCH_RUNBOOK.md`, `RESEARCH_CHARTER.md`, `PROBLEM_SPECIFICATION.md`, `STATUS.md`, and `TASKS.md`.
2. `source scripts/activate-toolchain.sh`
3. `scripts/verify-toolchain.sh`
4. `./skill-runtime verify-quick`
5. Reconcile Git, ledger, rounds, status, and queue before acting.

## Research authority and boundaries

- You may search for and retrieve additional literature when a route exposes a gap.
- Admit a source only through `literature/CERTIFICATION.md`: primary URL, retrieved bytes/metadata, SHA-256, extraction check, source card, exact locator, short excerpt, and cousin/statement match.
- Never call byte certification mathematical verification.
- Record every trial, including failures, aborts, exploratory variants, and nulls. No survivor-only reporting.
- Floating solvers discover candidates. Exact arithmetic, certificate checking, or proof establishes equality.
- A restricted ansatz failure is a bounded null, never an unrestricted depth lower bound.
- Do not edit the frozen target after results. Version claims instead.
- You may add tools locally when route-necessary, but must pin, hash, control-test, and document them in the same round.
- Do not spawn further agents unless the human or orchestrator explicitly expands the team.

## Honest credit

Progress is a new obstruction, closed gap, certified bound, eliminated route, stronger discriminator, exact witness, or meaningful retry predicate. More notes, agents, searches, files, tokens, or commits are not substantive yield. Do not close work yourself without cited verification evidence; hand it to the orchestrator for review.

## Round close

Update canonical ledger TOML, regenerate views, append the round, dual-write next object IDs to `STATUS.md` and `beads/QUEUE.md`, run `./skill-runtime verify-quick`, commit one round, and leave a handoff. `CLAIMS_LEDGER.md` and generated sections are never hand-edited.

## Swarm operations (added 2026-09-02 by orchestrator AmberBluff; human expanded the team)

- Work items live in Beads (`br`). `br ready --json` is the sole ready authority. Every `br` mutation passes `--actor <YourAgentMailName>`. Claim with `br update <id> --claim --actor <name> --json`; one in-progress bead per agent.
- Reserve the files you edit through Agent Mail (`reason=<bead id>`), announce start in thread `<bead id>`, reply in the same thread with `[<id>] RESULT` when done or blocked. Check your inbox at every natural pause.
- Exploratory compute writes to `artifacts/math/<bead-slug>/` with a `RESULT.md`: exact commands, input hashes, primes, counts, controls in both directions, and a **no-claim** line stating what the result does not show. That is the light custody standard for exploration; the orchestrator ledgers promoted results with full custody. Do not edit `ledger/`, `CLAIMS_LEDGER.md`, `STATUS.md`, `RESEARCH_CHARTER.md`, `PROBLEM_SPECIFICATION.md`. `./skill-runtime verify-quick` currently reports one known SE-10 finding on G-0015; ignore it.
- Honest-credit floor: real code plus real known-answer controls in the same bead; never weaken a control to go green; a negative on any finite family is a bounded null, never a theorem; never claim an identity without exact rational verification on every row; every reported number names its denominator; say what you did not verify. Only the orchestrator closes beads, citing evidence.
- Commit your own paths as you go with the bead id in the message; never rewrite history; never push; never commit files over 50 MB (list them in RESULT.md with hashes instead).
- Shared machine: 16 cores, 62 GB RAM. Do not start a job that needs more than 8 cores or 24 GB without telling AmberBluff first.
