# G-0009 replay guide

Run commands from `/data/projects/relu-depth-frontier-research`.

Observed tool split:

- system `python3`: NetworkX 3.6.1 for graph quotient generation;
- `.venv/bin/python`: NumPy plus python-flint for exact ranks and verifiers.

The fast replay uses the frozen matrices.  The full rebuild section regenerates
the expensive enumeration and evaluation layers.

## 1. Verify frozen bytes

    sha256sum -c artifacts/math/G-0009/MANIFEST.sha256

The manifest intentionally excludes itself and generated `__pycache__` files.

## 2. Replay the common-edge identity

    G0009_TMP="$(mktemp -d /tmp/g0009-replay.XXXXXX)"
    python3 artifacts/math/G-0009/scripts/lift_identity.py \
      --output "$G0009_TMP/lift_identity_attestation.json"
    cmp "$G0009_TMP/lift_identity_attestation.json" \
      artifacts/math/G-0009/lift_identity_attestation.json

Expected: 28 exact small-`n` points and a zero-status `cmp`.

## 3. Replay both sparse duals

    .venv/bin/python artifacts/math/G-0009/scripts/verify_duals.py \
      --cross-classes artifacts/math/G-0009/cross_component_classes.json \
      --cross-orbits artifacts/math/G-0009/orbit_data \
      --cross-cut artifacts/math/G-0009/cross_heldout_cut_matrix.npz \
      --cross-report artifacts/math/G-0009/cross_joint_rank_report_exact.json \
      --beta2-classes artifacts/math/G-0009/beta2_common_classes.json \
      --beta2-orbits artifacts/math/G-0009/beta2_orbit_data \
      --beta2-cut artifacts/math/G-0009/beta2_heldout_cut_matrix.npz \
      --beta2-report artifacts/math/G-0009/beta2_joint_rank_report_exact.json \
      --selection artifacts/math/G-0009/heldout_selection.json \
      --output "$G0009_TMP/dual_witness_verification.json"
    cmp "$G0009_TMP/dual_witness_verification.json" \
      artifacts/math/G-0009/dual_witness_verification.json

Expected exact pairings:

    cross target pairing = 5
    beta2 target pairing = 1/5

The verifier also checks zero pairing with every standalone candidate column.

## 4. Replay the beta2 functional collapse

    .venv/bin/python artifacts/math/G-0009/scripts/verify_beta2_collapse.py \
      --classes artifacts/math/G-0009/beta2_common_classes.json \
      --orbits artifacts/math/G-0009/beta2_orbit_data \
      --selection artifacts/math/G-0009/heldout_selection.json \
      --cut artifacts/math/G-0009/beta2_heldout_cut_matrix.npz \
      --identity artifacts/math/G-0009/lift_identity_attestation.json \
      --output "$G0009_TMP/beta2_functional_collapse.json"
    cmp "$G0009_TMP/beta2_functional_collapse.json" \
      artifacts/math/G-0009/beta2_functional_collapse.json

Expected: 4,916 columns partition into 252 exact-equality groups with zero
within-source disagreement.

## 5. Replay exact ranks from frozen matrices

Cross-component report:

    .venv/bin/python artifacts/math/G-0009/scripts/cross_component_search.py rank \
      --classes artifacts/math/G-0009/cross_component_classes.json \
      --cross-orbit-directory artifacts/math/G-0009/orbit_data \
      --selection artifacts/math/G-0009/heldout_selection.json \
      --same-cut artifacts/math/G-0009/same_heldout_cut_matrix.npz \
      --cross-cut artifacts/math/G-0009/cross_heldout_cut_matrix.npz \
      --exact \
      --output "$G0009_TMP/cross_joint_rank_report_exact.json"

Beta2 report:

    .venv/bin/python artifacts/math/G-0009/scripts/beta2_evaluate.py rank \
      --cross-classes artifacts/math/G-0009/cross_component_classes.json \
      --cross-orbit-directory artifacts/math/G-0009/orbit_data \
      --beta2-classes artifacts/math/G-0009/beta2_common_classes.json \
      --beta2-orbit-directory artifacts/math/G-0009/beta2_orbit_data \
      --selection artifacts/math/G-0009/heldout_selection.json \
      --same-cut artifacts/math/G-0009/same_heldout_cut_matrix.npz \
      --cross-cut artifacts/math/G-0009/cross_heldout_cut_matrix.npz \
      --beta2-cut artifacts/math/G-0009/beta2_heldout_cut_matrix.npz \
      --exact \
      --output "$G0009_TMP/beta2_joint_rank_report_exact.json"

Wall-clock `seconds` fields make these reports intentionally non-byte-stable.
Compare their mathematical fields:

    jq '.results | with_entries(.value = {
      rank: .value.exact.rank_over_Q,
      augmented: .value.exact.augmented_rank_over_Q,
      member: .value.exact.target_member_over_Q
    })' "$G0009_TMP/cross_joint_rank_report_exact.json"

    jq '.results | with_entries(.value = {
      rank: .value.exact.rank_over_Q,
      augmented: .value.exact.augmented_rank_over_Q,
      member: .value.exact.target_member_over_Q
    })' "$G0009_TMP/beta2_joint_rank_report_exact.json"

The expected values are the two tables in `REPORT.md`.

## 6. Full deterministic graph-list rebuild

These commands are slower and use NetworkX exact VF2 within WL buckets:

    python3 artifacts/math/G-0009/scripts/cross_component_search.py classes \
      --output "$G0009_TMP/cross_component_classes.json"
    cmp "$G0009_TMP/cross_component_classes.json" \
      artifacts/math/G-0009/cross_component_classes.json

    python3 artifacts/math/G-0009/scripts/enumerate_beta2_common.py \
      --output "$G0009_TMP/beta2_common_classes.json"
    cmp "$G0009_TMP/beta2_common_classes.json" \
      artifacts/math/G-0009/beta2_common_classes.json

Expected raw/class counts are `9,200/3,615` and `6,740/4,916`.

## 7. Full orbit and cut rebuild outline

Regenerate eight orbit groups for each family:

    for i in 0 1 2 3 4 5 6 7; do
      python3 artifacts/math/G-0009/scripts/cross_component_search.py orbit-group \
        --group-index "$i" --output-directory "$G0009_TMP/cross-orbits"
      python3 artifacts/math/G-0009/scripts/beta2_evaluate.py orbit-group \
        --group-index "$i" --output-directory "$G0009_TMP/beta2-orbits"
    done

Regenerate the held-out selection:

    python3 artifacts/math/G-0009/scripts/cross_component_search.py heldout-selection \
      --output "$G0009_TMP/heldout_selection.json"
    cmp "$G0009_TMP/heldout_selection.json" \
      artifacts/math/G-0009/heldout_selection.json

Cut matrices are partitioned into 16 shards.  For `family=same` and
`family=cross`, run `cross_component_search.py cut-shard` for shard indices
0 through 15 and then `assemble-cuts`.  For beta2, run
`beta2_evaluate.py cut-shard` and `assemble-cuts` with the same indices.
All commands validate selection and class hashes before accepting shards.

NPZ container bytes can carry ZIP metadata, so validate stored matrix hashes
and exact rank outputs rather than requiring byte-identical regenerated NPZ
containers.

## Certification boundary

Successful replay certifies the generated lists and matrices under the pinned
single-lineage code.  It does not supply an independent graph enumerator,
independent atom evaluator, complete MAX11 family, or global MAX11 theorem.

