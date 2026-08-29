# TRUST MODEL — relu-depth-frontier-research

What this campaign trusts, to do what, and why. A tool being installed and runnable grants it
NOTHING here — trust is a recorded decision with a scope.

| Component | Trusted for | NOT trusted for | Basis |
|---|---|---|---|
| {tool/library} | {e.g. exact integer arithmetic} | {e.g. floating-point claims at tolerance < X} | {version pin + known-answer check E-####} |
| {data vendor/feed} | {fields, as-of semantics} | {survivorship completeness, revision history} | {data-contract.toml + coverage class} |
| {formal checker} | {kernel-checked steps} | {statement match to the target — audited separately} | {trust scan record} |

Standing rules:
- Model recall is never a trusted source (`source = "model-memory"` caps at the floor rung).
- A check that has never failed on a planted defect is not yet trusted — record the planted-defect
  run that earned each trust row.
- Trust rows are versioned like everything else: a changed basis appends a new row, never edits one.
