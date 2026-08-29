# Research workspace — what this directory is

This tree seeds a **campaign workspace**: the durable state of ONE research engagement. The skill
package is the reusable method; the workspace is where that method's artifacts live. The two never
mix — the package carries no campaign state, and a campaign never edits the package.

**Bootstrap.** From the installed skill package, run its `bootstrap-research-workspace.sh` with
`<target-statement-or-path> <workspace-dir> [--resume-ok]`. It creates the workspace as a sibling
**git repository** — the campaign's source of truth — copies these seeds, records the canonical package
root/version/content digest in `.skill-runtime.toml`, generates the small `./skill-runtime` dispatcher,
and fills `{CURLY_SLOTS}` where it can. `--resume-ok` verifies that binding, then resumes from `STATUS.md`
without silently rebinding. `--self-test` exercises the literal cold-runbook commands in a throwaway
directory.

**Lazy creation.** Only the files here are created up front. Working directories
(`proofs/ counterexamples/ experiments/ computations/ formalization/ witnesses/ certificates/
artifacts/ reviews/referee/ exploration/ literature/ logs/ scripts/ lockbox/`) are created
the first time something real lands in them — an empty scaffold is noise.

**The rhythm.** Every round closes with: ledger updated → `./skill-runtime view` →
`phases/ROUNDS.md` updated → next work dual-written to `STATUS.md` and the queue file
`beads/QUEUE.md` (format defined in that file; an external beads-style tracker MAY mirror it, but
the file is canonical and no external tool is required) → `./skill-runtime verify-quick` green →
one git commit naming the round. The verifying step comes last on purpose: it then covers every
canonical mutation the round made, and never reports a stale-view SE-15 the round itself caused.
A fresh session resumes from `STATUS.md` and the runbook without re-deriving settled state.

**The rules that bind everything here** are the package's `references/KERNEL.md` and
`references/CLAIMS-LEDGER-SPEC.md`. The one to remember: `CLAIMS_LEDGER.md` is GENERATED — edit the
TOML under `ledger/`, never the view.
