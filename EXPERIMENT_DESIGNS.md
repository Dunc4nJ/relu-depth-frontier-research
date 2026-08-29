# EXPERIMENT DESIGNS — relu-depth-frontier-research

Design notes for trials BEFORE they run. Canon for executed trials is `ledger/experiments.toml`;
this file holds the thinking: candidate designs, discriminating power, and the controls each design
owes. A design graduates by being registered (`prereg = true`) — results never edit a design
retroactively.

## Design template
- **EXP-#### (planned):** serves route {H-####}
- What is varied · what is measured · what would count as FAILURE (written first)
- Which live routes it discriminates between (a measurement every surviving route predicts equally
  is low priority — prefer the test that kills something)
- Controls owed: {planted positive | null input | reconciliation | metamorphic transform} — per
  `references/EXPERIMENT-DESIGNS.md`, a battery must be able to fail AND able to recover a planted
  true effect
- Data custody consumed: {none | dev-oos | …} — lockbox is NEVER consumed by design work
- Detection floor and domain the result will be bounded to
