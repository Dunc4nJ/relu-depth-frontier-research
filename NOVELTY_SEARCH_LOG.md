# NOVELTY SEARCH LOG — relu-depth-frontier-research

A failed search means only “not found by this search.” Verdicts use the bounded vocabulary and apply to the exact query/corpus/date, not to all scholarship.

| date (UTC) | query | corpus/engine | hits examined | outcome | REF ids |
|---|---|---|---:|---|---|
| 2026-08-29 | MAX11 ReLU | arXiv web search, newest first | 0 | NO_PRIOR_FOUND |  |
| 2026-08-29 | "two hidden layers" maximum ReLU | arXiv web search, newest first | 4 | PRIOR_FOUND(REF-0002) | REF-0001, REF-0002, REF-0003 |
| 2026-08-29 | "MAX11" ReLU "two hidden layers" | paper-research: Semantic Scholar; arXiv/OpenAlex branches reported separately | 25 | NO_PRIOR_FOUND |  |
| 2026-08-29 | "maximum of 11" ReLU exact two hidden layers | paper-research: OpenAlex | 18 | NO_PRIOR_FOUND |  |
| 2026-08-29 | "MAX functions" "two-hidden-layer" ReLU | paper-research: OpenAlex + Semantic Scholar, deduplicated | 46 | PRIOR_FOUND(REF-0002) | REF-0002 |
| 2026-08-29 | "Shallower ReLU Network Representations" exact maximum | paper-research: OpenAlex | 1 | PRIOR_FOUND(REF-0001) | REF-0001 |

Screen interpretation:

- The exact arXiv MAX11 query returned no result.
- The broader arXiv query returned REF-0001, REF-0002, REF-0003, and one off-topic committee-machine paper (arXiv:2402.05696).
- The exact-query result sets were screened by title and abstract where present; the stored JSON files retain every counted record. Nearby results included REF-0001 and REF-0002, but neither settles MAX11, so they are discussed here rather than mislabeled as prior coverage of the exact object.
- The newest directly relevant source found was REF-0002, submitted 2026-08-25. Its abstract still describes the constant-depth/all-n answer as open and reports MAX5–MAX8 while acknowledging REF-0001's MAX≤10 result.
- This supports only a bounded “no MAX11 settlement found in these searches through 2026-08-29” statement. It is not a priority proof and must be refreshed before external novelty language.

Retained search snapshots are under literature/searches/ and hash-bound in literature/MANIFEST.sha256.

Coverage gaps:

- arXiv export API: rate-limited (HTTP 429) during the multi-database runs; two arXiv HTML searches were retained as fallback.
- Semantic Scholar: rate-limited/circuit-broken on several queries; successful result files and failures are both recorded in the log narrative.
- MathSciNet and zbMATH: no authenticated search available in this session.
- Google Scholar: not used as a reproducible corpus endpoint.
- IEEE full text for REF-0004: closed in queried registries.
- Search engines can miss new/unindexed manuscripts, renamed formulations, workshop notes, and private drafts.
