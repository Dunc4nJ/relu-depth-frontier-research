# TOOLCHAIN — relu-depth-frontier-research

Pinned tools for replay. `./skill-runtime detect` verifies the package binding and prints the detection
table; the AGENT records the table and PINS here in the same round. Detection is informational:
**usable ≠ trusted** — trust decisions live in `TRUST_MODEL.md`, not here.

The method runtime itself is recorded in `.skill-runtime.toml` (canonical package root, skill version,
digest algorithm, and package-content digest). `./skill-runtime binding-status` rechecks it before work;
the dispatcher also performs that check before every rail command. This is drift detection, not a
signature or a trust grant.

| Tool | Version | Pin (exact invocation/env) | Purpose |
|---|---|---|---|
| {python} | {3.x.y} | {.venv path / env_digest} | {computations} |
| {solver/library} | {ver} | {pin} | {…} |

Machine-readable retry inventory (record exact numeric versions only; verification reads this block
but never executes a named tool):

<!-- TOOL-VERSIONS-V1:BEGIN -->
<!-- TOOL-VERSIONS-V1:END -->

Rows have the exact form `TOOL-VERSION-V1 <tool-name> <numeric.version>`, for example
`TOOL-VERSION-V1 python3 3.13.2`. Run `./skill-runtime detect` explicitly, inspect its output, then
record accepted versions here. Missing or malformed rows simply cannot fire `tool_beyond(...)` retry
predicates; they never trigger ambient discovery.

Environment digest for replay: {sha256 of the environment manifest — referenced by evidence records
as `env_digest`}.

Local replay execution is disabled unless this file contains one exact, handle-scoped authorization
row between the markers below. The row has five single-space-delimited fields:
`REPLAY-AUTHORIZATION-V1 E-#### sha256:<digest-of-exact-repro-UTF8> <workspace-relative-env-manifest> sha256:<digest-of-env-manifest-bytes>`.
The final digest must equal the evidence record's `env_digest`. Keep the block empty when no local
execution is authorized.

<!-- REPLAY-AUTHORIZATIONS-V1:BEGIN -->
<!-- REPLAY-AUTHORIZATIONS-V1:END -->

Install policy: {no-sudo installs permitted into the campaign venv; every install appended here in
the same round it happens}.
