# NOVELTY SEARCH LOG — relu-depth-frontier-research

Dated searches only. **A failed search means "not found by this search" — NEVER "new."** Citations
get `REF-####` IDs shared with `literature/bibliography.bib`. Corpora that could not be searched are
recorded as coverage gaps, not skipped silently. This log is append-only; it is the sole basis on
which a `novelty-claim` can resolve, and its verdict vocabulary is bounded:
`NO_PRIOR_FOUND · PRIOR_FOUND(REF-####) · REFORMULATION_OF(REF-####) · SPECIAL_CASE_OF(REF-####) ·
UNRESOLVED`.

| date (UTC) | query | corpus/engine | hits examined | outcome | REF ids |
|---|---|---|---|---|---|
| {YYYY-MM-DD} | {exact query string} | {engine/database} | {N} | {bounded verdict} | {REF-#### …} |

Coverage gaps (corpora unavailable to this campaign):
- {CORPUS}: {why unavailable} — the no-claim boundary of every novelty verdict includes this gap.

Before ANY priority claim leaves this workspace, the log is re-run fresh (`references/LITERATURE-AND-NOVELTY.md`).
