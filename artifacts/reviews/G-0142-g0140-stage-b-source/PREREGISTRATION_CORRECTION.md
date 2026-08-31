# G-0142 preregistration correction 01

- Registered UTC: `2026-08-31T18:27:38Z`
- Corrects: `PREREGISTRATION.md` at commit `7bb0fc1`
- Auditor: `CobaltSpire`

The original preregistration transcribed the frozen executable path as
`artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-pricer`.
That path omitted the component `coordinate-` and is not the subject executable.

The exact executable committed at subject commit
`f603a6b8e51e31b810d957176836da52142aa0a9` is:

`artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-coordinate-pricer`

Its observed SHA-256 is the already-preregistered executable digest:
`13d24a884b3714f803bb1b79d879527ed4f99445788debe7922a5c53054cc79e`, and its
subject-commit Git blob is `60468e5db415c5abf4f46bacb897eff9b224ec3e`.

This correction was triggered by an exact Git-tree/path/hash check before any Stage-B source
inspection, audit-checker authoring, self-test, or static-preflight execution. The three forbidden
future G-0140 artifacts were checked for existence only and were absent; no scientific manifest,
Stage-A scientific output, Stage-B scientific output, or scientific outcome was observed.

Protocol version 2 is the original preregistration plus this single path replacement. Every other
subject binding, falsifier, PASS/FAIL rule, execution exclusion, claim boundary, and T1 limitation
is unchanged. The original preregistration remains preserved, and the final receipt must bind both
documents and disclose this reviewer transcription error. The nonexistent shorter path is not a
producer custody failure; all executable checks apply to the corrected exact committed path above.
