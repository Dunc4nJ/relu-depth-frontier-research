# Exact shallow-ReLU frontier campaign

This repository is the durable, Git-backed workspace for one question:

> Can every finite maximum `MAX_n(x) = max_i x_i` be represented exactly by a finite ReLU network with exactly two hidden ReLU layers and unrestricted real weights?

The first unresolved rung in this campaign's retrieved frontier is `n = 11`: the dated searches in `NOVELTY_SEARCH_LOG.md` found constructions through `n = 10` and no MAX11 settlement. That is a bounded search result, not a universal priority claim. The campaign runs prove and refute routes in parallel. A result about a restricted ansatz, rational weights, bounded width, approximation, or a bounded domain is a cousin—not a settlement.

## Cold start

1. Read `AGENTS.md`, `START_HERE.md`, `RESEARCH_RUNBOOK.md`, `RESEARCH_CHARTER.md`, and `PROBLEM_SPECIFICATION.md`.
2. Run `source scripts/activate-toolchain.sh`.
3. Run `scripts/verify-toolchain.sh` and `./skill-runtime verify-quick`.
4. Reconcile `STATUS.md`, `beads/QUEUE.md`, the ledger, `phases/ROUNDS.md`, and Git before claiming work.
5. Work only on a named route/gap and close every round with the skill runtime, ledger, queue, verifier, and one commit.

## What “certified literature” means here

Each retained source is bound to primary retrieval metadata, immutable local bytes, SHA-256, extraction checks, a source card, and an exact locator/short excerpt. That certifies provenance and statement traceability; it does **not** certify that a theorem is correct. Correctness is promoted separately through reconstruction, independent replay, referee review, and formalization.

## Main entry points

- `STATUS.md` — current resume pointer
- `RESEARCH_CHARTER.md` — frozen scope, review bar, and budget
- `PROBLEM_SPECIFICATION.md` — exact mathematical object and cousin register
- `NEURAL_REPRESENTATION_EPISTEMICS.md` — binding field translation
- `literature/INDEX.md` — admitted corpus and certification status
- `CLAIMS_LEDGER.md` — generated standing view; edit only `ledger/*.toml`
- `TASKS.md` — human-readable campaign roadmap
- `handoff/README.md` — bounded native-subagent dispatch and contamination rules
- `reviews/README.md` — research-lead adjudication and long-run checkpoint protocol
