# ROUNDS — relu-depth-frontier-research

Machine-read and mutated through `./skill-runtime convergence`. Never hand-edit or rewrite history;
the runbook obtains a fresh `state-digest` and supplies `--expect-state` at every round close/pass.

Each P10 pass row carries a verifier witness (`verifier-green · state:… · verify:… · witness:…`).
`record-pass` runs the battery against the exact state the pass claims and binds the result with the
workspace key `phases/.pass-witness-key`; the streak is recomputed from those witnesses, so a
hand-typed pass row is refused and a clean pass cannot be minted while the battery is red. **Commit
the key file with the round it witnesses and never delete or ignore it** — without it the recorded
passes cannot be re-derived and the tracker fails closed. It is not a secret from whoever owns the
workspace (`references/THREAT-MODEL.md` RR-01); it makes forging a pass deliberate rather than a
one-line table edit.

```
rounds_recorded: 0
substantive_rounds: 0
last_two_rounds_low_yield: false
clean_pass_streak: 0
```

## Round log (append-only)

| Round | Phase | Yield | What changed (one line, ledger deltas by ID) | Lens/attack family (P10 passes) |
|---|---|---|---|---|
| {R-0001} | {P#} | {substantive|low-yield} | {…} | {—|family name, normalized} |

Yield qualifies as `substantive` ONLY if the round produced at least one of: a new obstruction · a
closed gap · a certified bound · an eliminated route · a stronger discriminator · a meaningful retry
predicate. More agents, tokens, documents, or confidence do not qualify (`references/CONVERGENCE.md`).
