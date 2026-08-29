# G-0009: principled MAX11 lift identities and bounded redundancy

G-0009 tested two explicit MAX10-to-MAX11 topology changes outside G-0008's
9,804 same-component classes.  It found an exact common-edge lift identity,
but neither new family adds a rational-span dimension over the G-0008
baseline on the frozen 886-row joint system.

The exact finite-system result is:

| System | G-0008 baseline rank | Rank after cross family | Rank after beta2 family |
|---|---:|---:|---:|
| 364 orbit rows | 192 | 192 | 192 |
| 511 adaptive held-out hinge rows + 11 linear rows | 506 | 506 | 506 |
| all 886 rows jointly | 694 | 694 | 694 |

Because the baseline columns are included in each union, equal exact ranks
show that every added cross/beta2 column belongs to the baseline column span
**on these 886 rows**.  This is not a global functional identity and is not a
MAX11 impossibility theorem.

The two tested families are:

- 9,200 cross-component raw lifts, exactly quotiented to 3,615 connected
  full-support beta=0 graph classes;
- 6,740 common-internal-edge raw lifts, exactly quotiented to 4,916 beta=2
  graph classes with one ambient isolate.

The common-edge identity globally collapses the 4,916 beta2 graph classes to
at most the 252 source-atom functions.  On the frozen joint rows there are
exactly 252 distinct columns.

Start with [REPORT.md](REPORT.md) for the mathematical result and claim
boundaries, [EVIDENCE.md](EVIDENCE.md) for the artifact-local evidence ledger,
and [REPLAY.md](REPLAY.md) for verification commands.  The machine-readable
dual replay is [dual_witness_verification.json](dual_witness_verification.json).

Epistemic status: theorem-level algebra plus exact single-lineage computation.
The graph quotient and atom evaluator do not yet have independent
implementations.  No campaign ledger claim is promoted by this artifact.

