# REPRODUCIBILITY — relu-depth-frontier-research

The replay contract, not an essay:

- Every computational evidence record carries `repro` (exact command), `env_digest`, and a
  workspace-relative `artifact` path; stochastic work additionally carries `seeds`.
- `./skill-runtime verify-quick` must be green at every round close. At P10,
  `./skill-runtime verify-full` additionally inspects every machine-checkable replay recipe and local
  authorization at HEAD; ordinary full mode executes zero commands.
- Byte-identical reproduction is reproduction, NOT correctness — correctness needs a clean-room
  `CONSISTENT` (see `references/EVIDENCE-HIERARCHY.md`).
- A computational result that cannot be reproduced from its bound artifact, environment manifest,
  and ledger recipe does not exist as replay-grade evidence. Other evidence kinds retain their own
  shape-specific obligations.
