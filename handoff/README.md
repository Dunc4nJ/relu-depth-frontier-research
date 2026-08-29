# Native-subagent handoff protocol

The root agent is the research lead and sole integrator. A subagent receives one bounded object/route,
explicit allowed and forbidden inputs, expected artifacts, controls, resource ceiling, and stop condition.
Subagents may challenge, compute, or implement; they do not promote claims, close gaps, or declare rounds.

For clean-room work, the dispatch freezes a contamination boundary before the worker starts. A worker
forbidden from reading an upstream implementation must not receive a conversation fork containing that
code or a derivative description. It may receive the mathematical specification, pinned subject bytes,
paper locators, and preregistered controls. Contamination or scope drift yields `cannot-verify`, not an
independence claim.

Every returned handoff must state:

1. claimed object/route IDs and exact base commit;
2. files read, files changed, and forbidden inputs avoided or encountered;
3. code/environment/subject hashes and exact commands;
4. findings, nulls, failures, aborts, and resource use;
5. which preregistered controls passed or failed, with artifacts;
6. no-claim boundary, remaining falsifier, and smallest next discriminator.

The research lead independently inspects diffs and artifacts before integration. Same-lineage Codex
subagents are T1 challenge only and cannot satisfy the charter's T2 promotion bar.
