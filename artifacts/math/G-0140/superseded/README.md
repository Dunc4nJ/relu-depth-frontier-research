# Superseded G-0140 lineages

The archived Stage-A receipt in this directory remains a valid exact replay for
the original Pool128 manifest, but it is not an input to the repaired lineage.

- Original manifest path: `artifacts/math/G-0140/pool128_manifest_v1.json`
- Original manifest SHA-256: `31c07f70b94d04b86cfce88455a979f332105f8757d25b0a82f6ea8b1f6a8649`
- Original manifest commit: `47dd6a7c31c69fae445d46bc824ceb8d520bf03e`
- Archived Stage-A receipt SHA-256: `63be3b1376c316d5cac5d138106344e7190071d5b3cf8370445367772d93ccc7`
- Stage-A receipt commit: `061cf871bc91a1c260cb36e265bdf2370c7a1ce3`
- Mathematical result: `EXACT_RESIDUAL_POOL128`, with 146,950 nonzero hinge directions.

Stage B created no output under this lineage. Its preflight stopped on the
false-negative error `G-0139 PASS does not bind exact G-0135 inputs`: the old
validator searched recursively for `{path, sha256}` objects even though the
candidate was correctly bound in G-0139's `path -> digest` fixed-input map.
The Stage-B and Stage-C admission gates were repaired and must receive fresh,
immutable source audits before the manifest is refrozen.
