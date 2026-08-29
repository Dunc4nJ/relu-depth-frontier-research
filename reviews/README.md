# Research-lead review protocol

All subagent work is advisory until the root research lead checks statement match, provenance, exact
commands, artifacts, hashes, control potency, null boundaries, and ledger consequences. Findings are
adjudicated individually; agent agreement is not evidence-family independence.

For a run lasting longer than one hour, the lead performs manual checkpoints at roughly one-hour
intervals: inspect live output and resource use, compare the work to its preregistration, review the Git
diff and new artifacts, send corrective guidance if needed, and record the checkpoint. No cron job or
agent-authored self-review substitutes for this inspection.

A review verdict is one of `pass`, `revise`, `fail`, or `cannot-verify`. Interrupted reviews are
`cannot-verify` and never count toward a clean promotion bar. A pass certifies only the stated scope and
review tier; it does not upgrade mathematical standing by prose.
