use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{
    N, Record, full_normal_form, hinge_coefficients, validate_direction,
};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::de::{self, DeserializeOwned, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use std::time::Instant;

const K: usize = 128;
const RECORDS: usize = 163_740;
const TERMS: usize = 135;
const ROWS: usize = 412;
const SELECTED_SLOTS: usize = 204;
const ZERO_SELECTED_COEFFICIENTS: usize = 69;
const CARRY_DIRECTIONS: usize = 100;
const MAX_TERM_SEQUENCE: usize = 189;
const THREADS: usize = 12;
const HINGE_ENTRIES: usize = K * RECORDS;
const EXPECTED_LABELLED_PERMUTATIONS: u64 = 5_388_768_000;
const EXPECTED_HINGE_ENTRIES_PROCESSED: u64 = 4_409_740;
const EXPECTED_AGGREGATE_HINGE_SUPPORT: usize = 147_062;
const EXPECTED_NONZERO_HINGE_DIRECTIONS: usize = 146_950;

const PANEL_INPUT_PATH: &str = "artifacts/math/G-0113/panel_solver_input_v1.json";
const CANDIDATE_PATH: &str = "artifacts/math/G-0135/full_family_master_result_v3.json";
const ANCESTOR_STAGE_D_RESULT_PATH: &str = "artifacts/math/G-0135/new_member_global_replay_v1.json";
const STAGE_A_RECEIPT_PATH: &str = "artifacts/math/G-0140/pool128_global_replay_v1.json";
const MANIFEST_PATH: &str = "artifacts/math/G-0140/pool128_manifest_v1.json";
const OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_coordinate_prices_v1.json";
const STAGE_C_OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json";
const STAGE_D_OUTPUT_PATH: &str = "artifacts/math/G-0140/rank_aware_master_result_v1.json";
const STAGE_E_OUTPUT_PATH: &str = "artifacts/math/G-0140/new_member_global_replay_v1.json";
const PREREGISTRATION_PATH: &str = "artifacts/math/G-0140/PREREGISTRATION.md";
const KERNEL_PATH: &str = "artifacts/math/G-0117/src/lib.rs";
const G0139_AUDIT_PATH: &str = "artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json";
const G0139_AUDIT_SHA256: &str = "282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f";
const G0139_AUDIT_COMMIT: &str = "0bfdbf2db065d8517ad2d98d762473fed052cb54";
const G0139_EVIDENCE_CLASS: &str = "T1_SAME_LINEAGE_OUTCOME_AWARE_RESULT_AUDIT";
const G0139_CLAIM_BOUNDARY: &str = "Consistency only for the exact committed 135-term Stage-C member and exact G-0135 Stage-D result bytes. Same-lineage outcome-aware T1 evidence; no T2 independence, family completeness, frozen-family nonmembership, MAX11 lower bound, unrestricted nonrepresentability, all-n theorem, refereed status, formalization, or Lean theorem.";
const ANCESTOR_STAGE_D_COMMIT: &str = "270a62455097cbaf0a8f80426c54b6121d1afcba";
const ANCESTOR_STAGE_D_AUDIT_PATH: &str =
    "artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json";
const ANCESTOR_STAGE_D_AUDIT_SHA256: &str =
    "f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944";

const STAGE_A_SOURCE_PATH: &str = "artifacts/math/G-0140/stage_a_pool/src/main.rs";
const STAGE_A_ENGINE_PATH: &str = "artifacts/math/G-0140/stage_a_pool/src/engine.rs";
const STAGE_A_CARGO_PATH: &str = "artifacts/math/G-0140/stage_a_pool/Cargo.toml";
const STAGE_A_LOCK_PATH: &str = "artifacts/math/G-0140/stage_a_pool/Cargo.lock";
const STAGE_A_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay";
const STAGE_A_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0150-g0140-stage-a-final2-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_A_SOURCE_AUDIT_PREREG_PATH: &str =
    "artifacts/reviews/G-0150-g0140-stage-a-final2-source/PREREGISTRATION.md";
const STAGE_A_SOURCE_AUDIT_SCHEMA: &str = "max11-g0150-g0140-stage-a-final2-source-audit-v1";
const STAGE_B_SOURCE_PATH: &str = "artifacts/math/G-0140/stage_b_pricer/src/main.rs";
const STAGE_B_CARGO_PATH: &str = "artifacts/math/G-0140/stage_b_pricer/Cargo.toml";
const STAGE_B_LOCK_PATH: &str = "artifacts/math/G-0140/stage_b_pricer/Cargo.lock";
const STAGE_B_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0140/stage_b_pricer/target/release/g0140-stage-b-pool128-coordinate-pricer";
const STAGE_B_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0158-g0140-stage-b-final3-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_B_SOURCE_AUDIT_PREREG_PATH: &str =
    "artifacts/reviews/G-0158-g0140-stage-b-final3-source/PREREGISTRATION.md";
const STAGE_B_SOURCE_AUDIT_SCHEMA: &str = "max11-g0158-g0140-stage-b-final3-source-audit-v1";
const SOURCE_CUSTODY_PASS_RESULT: &str = "SOURCE_CUSTODY_AUDIT_PASS_T1";
const SOURCE_AUDIT_EVIDENCE_CLASS: &str = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT";
const STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen Stage-A producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.";
const STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen Stage-B producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.";
const STAGE_A_SOURCE_AUDIT_NO_CLAIM: &str = "This source audit does not adjudicate a G-0140 scientific manifest or result, establish or exclude a Pool128 member, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem.";
const STAGE_B_SOURCE_AUDIT_NO_CLAIM: &str = "This source audit does not adjudicate a G-0140 scientific manifest or result, establish or exclude a Pool128 coordinate matrix or exact-rank selection, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem.";

const PANEL_INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const CANDIDATE_SHA256: &str = "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8";
const CANDIDATE_GIT_COMMIT: &str = "2a567c1fcc8eed745235a50e638fc8c5e3ca83cc";
const ANCESTOR_STAGE_D_RESULT_SHA256: &str =
    "d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875";
const PREREGISTRATION_SHA256: &str =
    "e358f0ef9a6dcdcc798ec3cee780f3d220200bf70a2eaf2755060354e28dddb4";
const KERNEL_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";
const EXPECTED_AGGREGATE_HINGE_SHA256: &str =
    "168f91bd8735c778b492fd7f2f7414d4428dfd1af8af21bd8afe294c1b2ecf60";
const EXPECTED_NONZERO_HINGE_SHA256: &str =
    "9d7dd907d6885ab5e5b5a5a783b0212da8f145c1202fdb4de2c90f44d55023aa";
const EXPECTED_TERM_TRANSCRIPT_SHA256: &str =
    "7670731c72b64e89517d4d68d8ca44b73947db3c2a24938a4e843dfb9d8c1bbd";
const TARGET_SCALE: &str = "2329270928790555589661209267268423730843925879653148985745510422328358820404600447119688179933994479831727151713637545914351443501143908210073466765600822065562910";
const EXPECTED_FIRST_DIRECTION: [i8; N] = [0, 0, 0, 0, 0, 0, 1, -2, -2, 1, 2];
const EXPECTED_FIRST_COEFFICIENT: &str = "511838695529252537134751622979004566912532181650940275812075139014937590867028110892243795641237175143066549672701558636166678186077128694292857947716107231627691338960";

const CANDIDATE_SCHEMA: &str = "max11-g0135-full-family-master-result-v3";
const CANDIDATE_RESULT: &str = "FULL_FAMILY_412ROW_EXACT_Q_MEMBER";
const MANIFEST_SCHEMA: &str = "max11-g0140-rank-aware-manifest-v1";
const STAGE_A_SCHEMA: &str = "max11-g0140-pool128-global-replay-v1";
const STAGE_A_RESULT: &str = "EXACT_RESIDUAL_POOL128";
const OUTPUT_SCHEMA: &str = "max11-g0140-pool128-coordinate-prices-v1";
const STAGE_C_OUTPUT_SCHEMA: &str = "max11-g0140-pool128-exact-rank-selection-v1";
const STAGE_D_OUTPUT_SCHEMA: &str = "max11-g0140-rank-aware-master-result-v1";
const STAGE_E_OUTPUT_SCHEMA: &str = "max11-g0140-new-member-global-replay-v1";
const OUTPUT_RESULT: &str = "EXACT_FULL_FAMILY_POOL128_COORDINATES";
const OUTPUT_CLAIM: &str = "Exact 128-row ordered-cone hinge coordinates over the frozen 163,740-record family, in deterministic G-0140 Stage-A pool order, with arbitrary-precision 135-term member dot bridges. This is complete-matrix rank-selection input only, not a membership decision, family-completeness theorem, global MAX11 identity, lower bound, minimality result, or Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../../PREREGISTRATION.md");
const COMPILED_CANDIDATE: &[u8] =
    include_bytes!("../../../G-0135/full_family_master_result_v3.json");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../../G-0117/src/lib.rs");
const COMPILED_G0139_AUDIT: &[u8] =
    include_bytes!("../../../../reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json");

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Binding {
    path: String,
    sha256: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct SourceAuditReviewer {
    agent_name: String,
    program: String,
    model: String,
    same_model_lineage: bool,
    fresh_context: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct SourceAuditPreregistration {
    path: String,
    sha256: String,
    git_commit: String,
    committed_and_pushed_before_subject_source_inspection: bool,
    committed_and_pushed_before_runtime_checks: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditBindings {
    main_source: Binding,
    engine_source: Binding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    release_executable: Binding,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditSubject {
    git_commit: String,
    commit_object_and_working_bytes_equal_for_all_bindings: bool,
    bindings: FinalStageASourceAuditBindings,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditChecks {
    exact_named_binding_contract: bool,
    displaced_recursive_lookalikes_rejected: bool,
    correct_decoy_with_missing_named_binding_rejected: bool,
    duplicate_path_occurrences_rejected: bool,
    unknown_envelope_fields_rejected: bool,
    audit_git_commit_rejected: bool,
    duplicate_json_keys_rejected: bool,
    trailing_json_data_rejected: bool,
    producer_self_test_passed: bool,
    producer_static_preflight_passed: bool,
    producer_ancestor_preflight_passed: bool,
    prohibited_scientific_modes_not_run: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: SourceAuditReviewer,
    preregistration: SourceAuditPreregistration,
    subject: FinalStageASourceAuditSubject,
    required_checks: FinalStageASourceAuditChecks,
    scientific_manifest_observed: bool,
    scientific_input_observed: bool,
    scientific_output_observed: bool,
    scientific_replay_run: bool,
    no_claim: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageBSourceAuditBindings {
    main_source: Binding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    release_executable: Binding,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageBSourceAuditSubject {
    git_commit: String,
    commit_object_and_working_bytes_equal_for_all_bindings: bool,
    bindings: FinalStageBSourceAuditBindings,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageBSourceAuditChecks {
    exact_named_binding_contract: bool,
    displaced_recursive_lookalikes_rejected: bool,
    correct_decoy_with_missing_named_binding_rejected: bool,
    duplicate_path_occurrences_rejected: bool,
    unknown_envelope_fields_rejected: bool,
    audit_git_commit_rejected: bool,
    duplicate_json_keys_rejected: bool,
    trailing_json_data_rejected: bool,
    stage_a_missing_nullable_field_rejected: bool,
    stage_a_mutation_control_schemas_validated: bool,
    stage_a_source_audit_exact_contract_validated: bool,
    g0139_subject_and_exact_fixed_inputs_gate_verified: bool,
    compiled_source_manifest_lock_match_working_bytes: bool,
    overwrite_refusal_verified: bool,
    end_rehash_verified: bool,
    bigint_unconditional_paths_verified: bool,
    producer_self_test_passed: bool,
    producer_static_preflight_passed: bool,
    prohibited_scientific_modes_not_run: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageBSourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: SourceAuditReviewer,
    preregistration: SourceAuditPreregistration,
    subject: FinalStageBSourceAuditSubject,
    required_checks: FinalStageBSourceAuditChecks,
    scientific_manifest_observed: bool,
    scientific_input_observed: bool,
    scientific_output_observed: bool,
    scientific_replay_run: bool,
    no_claim: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ManifestParameters {
    n: usize,
    records: usize,
    existing_rows: usize,
    existing_terms: usize,
    accumulated_hinge_rows: usize,
    pool_k: usize,
    max_admitted_rows: usize,
    threads: usize,
    arithmetic: String,
    direction_order: String,
    column_order: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct PlannedOutput {
    path: String,
    schema: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StudyManifest {
    schema: String,
    selected_branch: String,
    preregistration_git_commit: String,
    producer_git_commit: String,
    source_audit_git_commit: String,
    bindings: BTreeMap<String, Binding>,
    transitive_inputs: Vec<Binding>,
    parameters: ManifestParameters,
    stage_order: Vec<String>,
    planned_outputs: BTreeMap<String, PlannedOutput>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Term {
    sequence: usize,
    coefficient: String,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Candidate {
    schema: String,
    result: String,
    claim_boundary: String,
    manifest_path: String,
    manifest_sha256: String,
    solver: Binding,
    stage_a_receipt: Binding,
    stage_b_receipt: Binding,
    prior_master_result: Binding,
    prior_master_manifest: Binding,
    audited_exact_q_core: Value,
    records: usize,
    old_rows: usize,
    appended_rows: usize,
    rows: usize,
    target: Vec<i64>,
    target_i128le_sha256: String,
    target_construction: String,
    prior_target_scale_not_reused: bool,
    row_order: Vec<String>,
    stage_a_selected_directions_i8_sha256: String,
    stage_a_selected_exact_residuals_decimal_lf_sha256: String,
    stage_b_direction_major_hinge_i64_le_sha256: String,
    stage_b_exact_candidate_dots_decimal_lf_sha256: String,
    warm_seed_policy: String,
    initial_selected_sequences: Vec<usize>,
    initial_selected_sequences_u64le_sha256: String,
    initial_rank: usize,
    max_rank_increases: usize,
    all_columns_reopened: bool,
    canonical_column_order: bool,
    no_modular_terminal_decision: bool,
    no_support_freeze: bool,
    no_zero_price_column_deletion: bool,
    no_row_dependency_deletion: bool,
    no_preferred_sparsity_search: bool,
    old_member_validation: Value,
    input_snapshot_sha256: String,
    all_412_rows_replayed: bool,
    rank: usize,
    augmented_rank: usize,
    selected_sequences: Vec<usize>,
    support_sequences: Vec<usize>,
    coordinate_rows: Vec<usize>,
    selected_basis_i128le_sha256: String,
    rational_coefficients: Vec<String>,
    rational_coefficients_lf_sha256: String,
    integer_coefficients: Vec<String>,
    integer_coefficients_decimal_lf_sha256: String,
    target_scale: String,
    terms: Vec<Term>,
    support_receipt: CandidateSupportReceipt,
    replay_receipt: CandidateReplayReceipt,
    coefficient_plus_one_mutant: CandidateCoefficientMutant,
    prior_target_scale_carryover_mutant_rejected: bool,
    trials: Vec<Value>,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StrictRepresentative {
    left_added_edge: [usize; 2],
    right_added_edge: [usize; 2],
    source_term: usize,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct StrictRecord {
    stage: String,
    orbit_index: usize,
    representative: StrictRepresentative,
    signed_class_sha256: String,
    sequence: usize,
    signed_mass: usize,
    active_vertices: usize,
    negative_edges: Vec<[usize; 2]>,
    positive_edges: Vec<[usize; 2]>,
    in_disjoint: bool,
    in_shared_distinct: bool,
}

impl From<StrictRecord> for Record {
    fn from(value: StrictRecord) -> Self {
        Self {
            sequence: value.sequence,
            signed_mass: value.signed_mass,
            active_vertices: value.active_vertices,
            negative_edges: value.negative_edges,
            positive_edges: value.positive_edges,
        }
    }
}

fn deserialize_records_strict<'de, D>(deserializer: D) -> std::result::Result<Vec<Record>, D::Error>
where
    D: serde::Deserializer<'de>,
{
    Vec::<StrictRecord>::deserialize(deserializer)
        .map(|records| records.into_iter().map(Record::from).collect())
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CandidateSupportReceipt {
    selected_columns: usize,
    support_columns: usize,
    support_is_exact_pivot_basis: bool,
    selected_sequences_u64le_sha256: String,
    support_sequences_u64le_sha256: String,
    term_support_u64le_sha256: String,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CandidateReplayReceipt {
    rows: usize,
    rational_all_rows_replayed: bool,
    rational_lhs_lf_sha256: String,
    primitive_denominator_clearing: bool,
    integer_all_rows_replayed: bool,
    integer_residuals_decimal_lf_sha256: String,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CandidateCoefficientMutant {
    support_index: usize,
    sequence: usize,
    coefficient_delta: String,
    first_nonzero_residual_row: usize,
    residuals_decimal_lf_sha256: String,
    rejected: bool,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PanelInput {
    schema: String,
    control_sequences: Vec<usize>,
    primes: [u64; 2],
    #[serde(deserialize_with = "deserialize_records_strict")]
    records: Vec<Record>,
    rows_path: String,
    target: Vec<i64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactLinear {
    coordinate: usize,
    coefficient: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct RequiredNullable<T>(Option<T>);

impl<'de, T> Deserialize<'de> for RequiredNullable<T>
where
    T: DeserializeOwned,
{
    fn deserialize<D>(deserializer: D) -> std::result::Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        let value = Value::deserialize(deserializer)?;
        if value.is_null() {
            Ok(Self(None))
        } else {
            serde_json::from_value(value)
                .map(Some)
                .map(Self)
                .map_err(de::Error::custom)
        }
    }
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct TermNormalFormReceipt {
    sequence: usize,
    active_vertices: usize,
    enumeration_mode: String,
    compressed_leaves_generated: u64,
    compressed_leaves_visited: u64,
    compressed_leaves_accepted: u64,
    inactive_label_multiplicity: u64,
    generated_labelled_permutations: u64,
    visited_labelled_permutations: u64,
    accepted_labelled_permutations: u64,
    skipped_labelled_permutations: u64,
    unclassified_labelled_permutations: u64,
    failed_labelled_permutations: u64,
    hinge_entries: usize,
    normal_form_sha256: String,
    scientific_coefficient_arithmetic: String,
    independent_exact_linear_crosscheck: bool,
    bounded_kernel_crosscheck: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct FiniteCoefficientMutant {
    sequence: usize,
    coefficient_delta: String,
    first_nonzero_residual_row: usize,
    residuals_decimal_lf_sha256: String,
    rejected: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct FiniteReplayReceipt {
    rows: usize,
    panel_rows: usize,
    linear_rows: usize,
    accumulated_hinge_rows: usize,
    cache_layout: String,
    arithmetic: String,
    all_rows_exactly_replayed: bool,
    residuals_decimal_lf_sha256: String,
    coefficient_plus_one_mutant: FiniteCoefficientMutant,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct MutationControl {
    name: String,
    first_nonzero_hinge: RequiredNullable<ExactHinge>,
    first_nonzero_linear: RequiredNullable<ExactLinear>,
    baseline_complete_residual_sha256: String,
    mutated_complete_residual_sha256: String,
    changed_from_baseline: bool,
    detected: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CensusControls {
    dynamic_term_count: usize,
    factorial_11: u64,
    expected_labelled_permutations: u64,
    observed_labelled_permutations: u64,
    per_term_generated_equals_visited_equals_accepted: bool,
    zero_skipped_unclassified_failed: bool,
    omitted_last_orbit_rejected: bool,
    decremented_global_census_rejected: bool,
    accumulated_direction_count_100: bool,
    omitted_accumulated_direction_rejected: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SelectionControls {
    exact_batch_count_or_zero_terminal: bool,
    strict_signed_lexicographic_order: bool,
    excludes_accumulated_directions: bool,
    direction_reordering_changes_digest: bool,
    coefficient_plus_one_changes_digest: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AccumulatedDirectionCheck {
    index: usize,
    source: String,
    source_index: usize,
    direction: [i8; N],
    aggregate_coefficient: String,
    direct_dp_coefficient: String,
    routes_agree: bool,
    exact_zero: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageAReceipt {
    schema: String,
    result: String,
    claim_boundary: String,
    g0140_manifest: Binding,
    g0135_manifest: Binding,
    protocol: Binding,
    producer_source: Binding,
    producer_engine: Binding,
    producer_executable: Binding,
    g0139_result_audit: Binding,
    ancestor_stage_d_result: Binding,
    stage_c_member: Binding,
    source_and_audit_bindings: BTreeMap<String, Binding>,
    candidate_schema: String,
    candidate_result: String,
    rows: usize,
    records: usize,
    selected_rank: usize,
    support_columns: usize,
    terms: usize,
    target_scale: String,
    target_subtraction_coordinate_10: String,
    stage_c_all_412_rational_rows_replayed: bool,
    stage_c_all_412_integer_rows_replayed: bool,
    stage_c_primitive_denominator_clearing: bool,
    stage_c_coefficient_plus_one_mutant_rejected: bool,
    stage_c_prior_scale_carryover_mutant_rejected: bool,
    independent_finite_412_row_replay: FiniteReplayReceipt,
    arithmetic: String,
    decision_rule: String,
    complete_global_replay: bool,
    all_hinge_and_linear_residuals_zero: bool,
    labelled_permutations_expected: u64,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_directions: usize,
    aggregate_hinge_decimal_lf_sha256: String,
    nonzero_hinge_decimal_lf_sha256: String,
    complete_residual_decimal_lf_sha256: String,
    term_normal_form_transcript_sha256: String,
    term_normal_forms: Vec<TermNormalFormReceipt>,
    accumulated_direction_checks: Vec<AccumulatedDirectionCheck>,
    all_100_accumulated_directions_exact_zero: bool,
    linear_residuals_after_target: Vec<String>,
    all_11_linear_residuals_exact_zero: bool,
    first_nonzero_hinge: RequiredNullable<ExactHinge>,
    first_nonzero_linear: RequiredNullable<ExactLinear>,
    pool_k: usize,
    pool_count: usize,
    pool_directions_i8_sha256: String,
    pool_exact_residuals_decimal_lf_sha256: String,
    pool: Vec<ExactHinge>,
    coefficient_plus_one: MutationControl,
    target_scale_plus_one: MutationControl,
    target_coordinate_plus_one: MutationControl,
    omitted_final_term: MutationControl,
    omitted_first_term_direction: MutationControl,
    census_controls: CensusControls,
    selection_controls: SelectionControls,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    candidate_rehashed_at_end: bool,
    wall_seconds: f64,
}

#[derive(Serialize)]
struct PriceRow {
    index: usize,
    direction: [i8; N],
    exact_stage_a_residual: String,
    exact_candidate_dot: String,
    records: usize,
    nonzero_hinge_coefficients: usize,
    minimum_hinge_coefficient: i64,
    maximum_hinge_coefficient: i64,
    maximum_absolute_hinge_coefficient: u64,
    hinge_coefficients_i64_le_sha256: String,
    hinge_coefficients: Vec<i64>,
}

#[derive(Serialize)]
struct InputMutationControls {
    pool_count_mutant_rejected: bool,
    pool_order_mutant_rejected: bool,
    pool_duplicate_mutant_rejected: bool,
    direction_invalidity_mutant_rejected: bool,
    residual_plus_one_mutant_rejected: bool,
    record_census_truncation_rejected: bool,
    record_order_mutant_rejected: bool,
    all_rejected: bool,
}

#[derive(Serialize)]
struct CoefficientPlusOneMutant {
    sequence: usize,
    coefficient_delta: &'static str,
    baseline_exact_dots_decimal_lf_sha256: String,
    mutated_exact_dots_decimal_lf_sha256: String,
    changed_rows: usize,
    rejected: bool,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    manifest_path: &'static str,
    manifest_sha256: String,
    source_and_input_bindings: BTreeMap<String, Binding>,
    stage_a_receipt: Binding,
    candidate: Binding,
    g0139_result_audit: Binding,
    pool_k: usize,
    records: usize,
    hinge_entries: usize,
    pool_count: usize,
    pool_directions_i8_sha256: String,
    pool_exact_residuals_decimal_lf_sha256: String,
    directions: Vec<[i8; N]>,
    direction_major_hinge_i64_le_sha256: String,
    exact_candidate_dots_decimal_lf_sha256: String,
    exact_candidate_dots: Vec<String>,
    rows: Vec<PriceRow>,
    input_mutation_controls: InputMutationControls,
    coefficient_plus_one_mutant: CoefficientPlusOneMutant,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
}

struct ManifestSnapshot {
    manifest: StudyManifest,
    sha256: String,
    bindings_by_path: BTreeMap<String, String>,
}

struct ValidatedInputs {
    panel: PanelInput,
    candidate: Candidate,
    receipt: StageAReceipt,
    manifest: ManifestSnapshot,
    custody: BTreeMap<String, String>,
}

struct StrictValue(Value);

impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D>(deserializer: D) -> std::result::Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        struct StrictVisitor;

        impl<'de> Visitor<'de> for StrictVisitor {
            type Value = StrictValue;

            fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str("JSON without duplicate object keys")
            }

            fn visit_bool<E>(self, value: bool) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Bool(value)))
            }

            fn visit_i64<E>(self, value: i64) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Number(value.into())))
            }

            fn visit_u64<E>(self, value: u64) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Number(value.into())))
            }

            fn visit_f64<E>(self, value: f64) -> std::result::Result<Self::Value, E>
            where
                E: de::Error,
            {
                serde_json::Number::from_f64(value)
                    .map(Value::Number)
                    .map(StrictValue)
                    .ok_or_else(|| E::custom("non-finite JSON number"))
            }

            fn visit_str<E>(self, value: &str) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::String(value.to_string())))
            }

            fn visit_string<E>(self, value: String) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::String(value)))
            }

            fn visit_none<E>(self) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Null))
            }

            fn visit_unit<E>(self) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Null))
            }

            fn visit_some<D>(self, deserializer: D) -> std::result::Result<Self::Value, D::Error>
            where
                D: serde::Deserializer<'de>,
            {
                StrictValue::deserialize(deserializer)
            }

            fn visit_seq<A>(self, mut sequence: A) -> std::result::Result<Self::Value, A::Error>
            where
                A: SeqAccess<'de>,
            {
                let mut values = Vec::new();
                while let Some(value) = sequence.next_element::<StrictValue>()? {
                    values.push(value.0);
                }
                Ok(StrictValue(Value::Array(values)))
            }

            fn visit_map<A>(self, mut map: A) -> std::result::Result<Self::Value, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut values = serde_json::Map::new();
                while let Some((key, value)) = map.next_entry::<String, StrictValue>()? {
                    if values.insert(key.clone(), value.0).is_some() {
                        return Err(<A::Error as de::Error>::custom(format!(
                            "duplicate JSON key: {key}"
                        )));
                    }
                }
                Ok(StrictValue(Value::Object(values)))
            }
        }

        deserializer.deserialize_any(StrictVisitor)
    }
}

fn strict_json_value(reader: impl Read) -> Result<Value> {
    let mut deserializer = serde_json::Deserializer::from_reader(reader);
    let value = StrictValue::deserialize(&mut deserializer)?.0;
    deserializer.end()?;
    Ok(value)
}

fn strict_json<T: DeserializeOwned>(reader: impl Read) -> Result<T> {
    serde_json::from_value(strict_json_value(reader)?).context("strict JSON schema validation")
}

fn factorial(value: usize) -> u64 {
    (1..=value as u64).product()
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut source = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    loop {
        let read = source.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn sha256_bytes(value: &[u8]) -> String {
    format!("{:x}", Sha256::digest(value))
}

fn canonical_sha256(raw: &str) -> bool {
    raw.len() == 64
        && raw
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn digest_i64<'a>(values: impl Iterator<Item = &'a i64>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn selected_direction_digest(selected: &[ExactHinge]) -> String {
    let mut digest = Sha256::new();
    for item in selected {
        for coordinate in item.direction {
            digest.update(coordinate.to_le_bytes());
        }
    }
    format!("{:x}", digest.finalize())
}

fn decimal_lf_digest<'a>(values: impl Iterator<Item = &'a str>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn bigint_decimal_lf_digest(values: &[BigInt]) -> String {
    let rendered = values.iter().map(ToString::to_string).collect::<Vec<_>>();
    decimal_lf_digest(rendered.iter().map(String::as_str))
}

fn canonical_integer(raw: &str) -> bool {
    if raw == "0" {
        return true;
    }
    let digits = raw.strip_prefix('-').unwrap_or(raw);
    !digits.is_empty()
        && !digits.starts_with('0')
        && digits.bytes().all(|byte| byte.is_ascii_digit())
}

fn canonical_positive_integer(raw: &str) -> bool {
    canonical_integer(raw) && raw != "0" && !raw.starts_with('-')
}

fn parse_bigint(raw: &str) -> Result<BigInt> {
    ensure!(canonical_integer(raw), "noncanonical integer: {raw}");
    BigInt::parse_bytes(raw.as_bytes(), 10).context("parse integer")
}

fn repo_root() -> Result<PathBuf> {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(4)
        .context("resolve repository root")?
        .canonicalize()
        .context("canonicalize repository root")
}

fn checked_repo_path(root: &Path, raw: &str) -> Result<PathBuf> {
    let relative = Path::new(raw);
    ensure!(
        relative.is_relative(),
        "absolute input path forbidden: {raw}"
    );
    ensure!(
        relative
            .components()
            .all(|component| matches!(component, Component::Normal(_))),
        "nonnormal input path forbidden: {raw}"
    );
    let mut cursor = root.to_path_buf();
    for component in relative.components() {
        let Component::Normal(piece) = component else {
            unreachable!()
        };
        cursor.push(piece);
        let metadata = std::fs::symlink_metadata(&cursor)
            .with_context(|| format!("stat bound path component {}", cursor.display()))?;
        ensure!(
            !metadata.file_type().is_symlink(),
            "symlink input path forbidden: {}",
            cursor.display()
        );
    }
    let canonical = cursor
        .canonicalize()
        .with_context(|| format!("canonicalize {raw}"))?;
    ensure!(
        canonical.starts_with(root),
        "input escapes repository: {raw}"
    );
    ensure!(canonical.is_file(), "bound input is not a file: {raw}");
    Ok(canonical)
}

fn make_binding(root: &Path, raw: &str) -> Result<Binding> {
    Ok(Binding {
        path: raw.to_string(),
        sha256: sha256_path(&checked_repo_path(root, raw)?)?,
    })
}

fn make_expected_binding(root: &Path, raw: &str, expected: &str) -> Result<Binding> {
    let binding = make_binding(root, raw)?;
    ensure!(binding.sha256 == expected, "binding drift: {raw}");
    Ok(binding)
}

fn git_commit_for_path(root: &Path, raw: &str) -> Result<String> {
    let path = checked_repo_path(root, raw)?;
    let output = Command::new("git")
        .args(["log", "-1", "--format=%H", "--", raw])
        .current_dir(root)
        .output()
        .with_context(|| format!("inspect Git ancestry for {raw}"))?;
    ensure!(output.status.success(), "git log failed for {raw}");
    let commit = String::from_utf8(output.stdout)?.trim().to_string();
    ensure!(
        commit.len() == 40
            && commit
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte)),
        "untracked or malformed Git ancestry for {raw}"
    );
    let blob = Command::new("git")
        .args(["show", &format!("{commit}:{raw}")])
        .current_dir(root)
        .output()
        .with_context(|| format!("inspect committed blob for {raw}"))?;
    ensure!(blob.status.success(), "git show failed for {raw}");
    ensure!(
        sha256_bytes(&blob.stdout) == sha256_path(&path)?,
        "working bytes differ from committed binding: {raw}"
    );
    Ok(commit)
}

fn publish_exclusive(path: &Path, bytes: &[u8]) -> Result<()> {
    ensure!(!path.exists(), "refusing to overwrite output");
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    ensure!(parent.is_dir(), "output parent missing");
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .context("output filename is not UTF-8")?;
    let temporary = path.with_file_name(format!(".{file_name}.tmp.{}", std::process::id()));
    ensure!(
        !temporary.exists(),
        "exclusive temporary output already exists"
    );

    let write_result = (|| -> Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(bytes)?;
        file.flush()?;
        file.sync_all()?;
        Ok(())
    })();
    if let Err(error) = write_result {
        let _ = std::fs::remove_file(&temporary);
        return Err(error);
    }
    if let Err(error) = std::fs::hard_link(&temporary, path) {
        let _ = std::fs::remove_file(&temporary);
        return Err(error).context("atomic no-overwrite output publication");
    }
    if let Err(error) = std::fs::remove_file(&temporary) {
        let _ = std::fs::remove_file(path);
        return Err(error).context("remove exclusive temporary output link");
    }
    if let Err(error) = File::open(parent).and_then(|directory| directory.sync_all()) {
        let _ = std::fs::remove_file(path);
        return Err(error).context("directory fsync after atomic publication");
    }
    Ok(())
}

fn transpose_record_major(record_major: Vec<Vec<i64>>, directions: usize) -> Result<Vec<Vec<i64>>> {
    let records = record_major.len();
    ensure!(
        record_major.iter().all(|row| row.len() == directions),
        "record-major batch width drift"
    );
    let mut direction_major = (0..directions)
        .map(|_| Vec::with_capacity(records))
        .collect::<Vec<_>>();
    for row in record_major {
        for (direction, value) in row.into_iter().enumerate() {
            direction_major[direction].push(value);
        }
    }
    Ok(direction_major)
}

fn exact_dot(row: &[i64], terms: &[(usize, BigInt)]) -> BigInt {
    terms
        .iter()
        .fold(BigInt::from(0), |total, (sequence, coefficient)| {
            total + coefficient * BigInt::from(row[*sequence])
        })
}

fn nonzero_term_projection(sequences: &[usize], coefficients: &[String]) -> Result<Vec<Term>> {
    ensure!(sequences.len() == coefficients.len(), "basis census drift");
    ensure!(
        coefficients.iter().all(|value| canonical_integer(value)),
        "noncanonical basis coefficient"
    );
    Ok(sequences
        .iter()
        .copied()
        .zip(coefficients.iter())
        .filter(|(_, coefficient)| coefficient.as_str() != "0")
        .map(|(sequence, coefficient)| Term {
            sequence,
            coefficient: coefficient.clone(),
        })
        .collect())
}

fn validate_strict_axis(values: &[usize], length: usize, upper: usize, name: &str) -> Result<()> {
    ensure!(values.len() == length, "{name} census drift");
    ensure!(
        values.iter().all(|value| *value < upper),
        "{name} bound drift"
    );
    ensure!(
        values.windows(2).all(|window| window[0] < window[1]),
        "{name} order/uniqueness drift"
    );
    Ok(())
}

fn validate_record_axis(
    sequences: impl IntoIterator<Item = usize>,
    expected_records: usize,
) -> Result<()> {
    let mut seen = 0usize;
    for (expected, sequence) in sequences.into_iter().enumerate() {
        ensure!(sequence == expected, "record-order drift at {expected}");
        seen += 1;
    }
    ensure!(seen == expected_records, "record census drift");
    Ok(())
}

fn validate_panel(input: &PanelInput) -> Result<()> {
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1"
            && input.control_sequences == [0, 1, 284, 5_341, 30_223, 133_449, 134_301]
            && input.primes == [2_000_081, 3_000_017]
            && input.rows_path == "artifacts/math/G-0111/dual_rows_v1.json"
            && input.target.len() == 301,
        "panel metadata drift"
    );
    validate_record_axis(input.records.iter().map(|record| record.sequence), RECORDS)
}

fn validate_candidate(candidate: &Candidate) -> Result<()> {
    ensure!(
        candidate.schema == CANDIDATE_SCHEMA
            && candidate.result == CANDIDATE_RESULT
            && !candidate.claim_boundary.is_empty()
            && candidate.records == RECORDS
            && candidate.old_rows == 380
            && candidate.appended_rows == 32
            && candidate.rows == ROWS
            && candidate.all_412_rows_replayed
            && candidate.rank == SELECTED_SLOTS
            && candidate.augmented_rank == SELECTED_SLOTS,
        "candidate identity/dimension drift"
    );
    ensure!(
        !candidate.manifest_path.is_empty()
            && canonical_sha256(&candidate.manifest_sha256)
            && candidate.target_scale == TARGET_SCALE
            && canonical_positive_integer(&candidate.target_scale),
        "candidate provenance or target-scale drift"
    );
    validate_strict_axis(
        &candidate.selected_sequences,
        SELECTED_SLOTS,
        RECORDS,
        "candidate selected axis",
    )?;
    ensure!(
        candidate.support_sequences == candidate.selected_sequences,
        "candidate support/selected axis drift"
    );
    validate_strict_axis(
        &candidate.coordinate_rows,
        SELECTED_SLOTS,
        ROWS,
        "candidate coordinate-row axis",
    )?;
    ensure!(
        candidate.integer_coefficients.len() == SELECTED_SLOTS
            && candidate
                .integer_coefficients
                .iter()
                .filter(|value| value.as_str() == "0")
                .count()
                == ZERO_SELECTED_COEFFICIENTS,
        "candidate coefficient-slot census drift"
    );
    ensure!(
        candidate.terms
            == nonzero_term_projection(
                &candidate.selected_sequences,
                &candidate.integer_coefficients,
            )?
            && candidate.terms.len() == TERMS,
        "candidate term projection drift"
    );
    for (index, term) in candidate.terms.iter().enumerate() {
        ensure!(
            term.sequence <= MAX_TERM_SEQUENCE
                && canonical_integer(&term.coefficient)
                && term.coefficient != "0"
                && (index == 0 || candidate.terms[index - 1].sequence < term.sequence),
            "candidate term structure drift at {index}"
        );
    }
    ensure!(
        candidate
            .terms
            .first()
            .is_some_and(|term| term.sequence == 0)
            && candidate.support_receipt.selected_columns == SELECTED_SLOTS
            && candidate.support_receipt.support_columns == SELECTED_SLOTS
            && candidate.support_receipt.support_is_exact_pivot_basis
            && candidate.replay_receipt.rows == ROWS
            && candidate.replay_receipt.rational_all_rows_replayed
            && candidate.replay_receipt.primitive_denominator_clearing
            && candidate.replay_receipt.integer_all_rows_replayed
            && candidate.coefficient_plus_one_mutant.coefficient_delta == "+1"
            && candidate.coefficient_plus_one_mutant.rejected
            && candidate.prior_target_scale_carryover_mutant_rejected
            && candidate.inputs_rehashed_at_end
            && candidate.wall_seconds > 0.0
            && candidate.maximum_rss_kib > 0,
        "candidate exact replay/control drift"
    );
    ensure!(
        [
            &candidate.support_receipt.selected_sequences_u64le_sha256,
            &candidate.support_receipt.support_sequences_u64le_sha256,
            &candidate.support_receipt.term_support_u64le_sha256,
            &candidate.replay_receipt.rational_lhs_lf_sha256,
            &candidate.replay_receipt.integer_residuals_decimal_lf_sha256,
            &candidate
                .coefficient_plus_one_mutant
                .residuals_decimal_lf_sha256,
        ]
        .into_iter()
        .all(|digest| canonical_sha256(digest)),
        "candidate digest drift"
    );
    Ok(())
}

fn validate_pool(
    pool: &[ExactHinge],
    expected_direction_digest: &str,
    expected_residual_digest: &str,
    carried_directions: &[[i8; N]],
    enforce_first_anchor: bool,
) -> Result<()> {
    ensure!(pool.len() == K, "Pool128 direction census drift");
    ensure!(
        pool.windows(2)
            .all(|window| window[0].direction < window[1].direction),
        "Pool128 direction order/uniqueness drift"
    );
    let carried = carried_directions.iter().copied().collect::<BTreeSet<_>>();
    let mut seen = BTreeSet::new();
    for item in pool {
        validate_direction(&item.direction)?;
        ensure!(seen.insert(item.direction), "duplicate Pool128 direction");
        ensure!(
            !carried.contains(&item.direction),
            "Pool128 direction duplicates accumulated row"
        );
        ensure!(
            canonical_integer(&item.coefficient) && item.coefficient != "0",
            "Pool128 residual is not canonical nonzero decimal"
        );
    }
    ensure!(
        selected_direction_digest(pool) == expected_direction_digest,
        "Pool128 signed-byte digest drift"
    );
    ensure!(
        decimal_lf_digest(pool.iter().map(|item| item.coefficient.as_str()))
            == expected_residual_digest,
        "Pool128 residual decimal-LF digest drift"
    );
    if enforce_first_anchor {
        let first = pool.first().context("Pool128 missing first row")?;
        ensure!(
            first.direction == EXPECTED_FIRST_DIRECTION
                && first.coefficient == EXPECTED_FIRST_COEFFICIENT,
            "G-0139 first residual anchor drift"
        );
    }
    Ok(())
}

fn manifest_binding<'a>(manifest: &'a ManifestSnapshot, raw: &str) -> Result<&'a str> {
    manifest
        .bindings_by_path
        .get(raw)
        .map(String::as_str)
        .with_context(|| format!("manifest omits required binding: {raw}"))
}

fn binding_matches(root: &Path, manifest: &ManifestSnapshot, binding: &Binding) -> Result<()> {
    ensure!(
        canonical_sha256(&binding.sha256)
            && manifest_binding(manifest, &binding.path)? == binding.sha256,
        "receipt binding is not admitted by manifest: {}",
        binding.path
    );
    ensure!(
        sha256_path(&checked_repo_path(root, &binding.path)?)? == binding.sha256,
        "receipt binding drift: {}",
        binding.path
    );
    Ok(())
}

fn value_string<'a>(value: &'a Value, pointer: &str) -> Result<&'a str> {
    value
        .pointer(pointer)
        .and_then(Value::as_str)
        .with_context(|| format!("missing string at {pointer}"))
}

fn value_bool(value: &Value, pointer: &str) -> Result<bool> {
    value
        .pointer(pointer)
        .and_then(Value::as_bool)
        .with_context(|| format!("missing Boolean at {pointer}"))
}

fn value_u64(value: &Value, pointer: &str) -> Result<u64> {
    value
        .pointer(pointer)
        .and_then(Value::as_u64)
        .with_context(|| format!("missing unsigned integer at {pointer}"))
}

fn source_audit_reviewer_is_valid(reviewer: &SourceAuditReviewer) -> bool {
    !reviewer.agent_name.is_empty()
        && reviewer.program == "codex"
        && !reviewer.model.is_empty()
        && reviewer.same_model_lineage
        && reviewer.fresh_context
}

fn source_audit_preregistration_is_valid(
    preregistration: &SourceAuditPreregistration,
    expected_path: &str,
) -> bool {
    preregistration.path == expected_path
        && canonical_sha256(&preregistration.sha256)
        && preregistration.git_commit.len() == 40
        && preregistration
            .git_commit
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit())
        && preregistration.committed_and_pushed_before_subject_source_inspection
        && preregistration.committed_and_pushed_before_runtime_checks
}

fn final_stage_a_source_audit_bindings(
    receipt: &FinalStageASourceAuditReceipt,
) -> [(&'static str, &Binding); 5] {
    [
        (STAGE_A_SOURCE_PATH, &receipt.subject.bindings.main_source),
        (STAGE_A_ENGINE_PATH, &receipt.subject.bindings.engine_source),
        (STAGE_A_CARGO_PATH, &receipt.subject.bindings.cargo_manifest),
        (STAGE_A_LOCK_PATH, &receipt.subject.bindings.cargo_lock),
        (
            STAGE_A_EXECUTABLE_PATH,
            &receipt.subject.bindings.release_executable,
        ),
    ]
}

fn final_stage_b_source_audit_bindings(
    receipt: &FinalStageBSourceAuditReceipt,
) -> [(&'static str, &Binding); 4] {
    [
        (STAGE_B_SOURCE_PATH, &receipt.subject.bindings.main_source),
        (STAGE_B_CARGO_PATH, &receipt.subject.bindings.cargo_manifest),
        (STAGE_B_LOCK_PATH, &receipt.subject.bindings.cargo_lock),
        (
            STAGE_B_EXECUTABLE_PATH,
            &receipt.subject.bindings.release_executable,
        ),
    ]
}

fn final_stage_a_source_audit_receipt(receipt: &Value) -> Result<FinalStageASourceAuditReceipt> {
    serde_json::from_value(receipt.clone())
        .context("strict final Stage-A source-audit schema validation")
}

fn final_stage_b_source_audit_receipt(receipt: &Value) -> Result<FinalStageBSourceAuditReceipt> {
    serde_json::from_value(receipt.clone())
        .context("strict final Stage-B source-audit schema validation")
}

fn validate_final_stage_a_source_audit_semantics(
    receipt: &FinalStageASourceAuditReceipt,
) -> Result<()> {
    ensure!(
        receipt.schema == STAGE_A_SOURCE_AUDIT_SCHEMA
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_CUSTODY_PASS_RESULT
            && receipt.evidence_class == SOURCE_AUDIT_EVIDENCE_CLASS
            && receipt.claim_boundary == STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY
            && receipt.no_claim == STAGE_A_SOURCE_AUDIT_NO_CLAIM
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_replay_run
            && source_audit_reviewer_is_valid(&receipt.reviewer)
            && source_audit_preregistration_is_valid(
                &receipt.preregistration,
                STAGE_A_SOURCE_AUDIT_PREREG_PATH,
            )
            && receipt.subject.git_commit.len() == 40
            && receipt
                .subject
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings,
        "final Stage-A source audit semantic boundary drift"
    );
    for (expected_path, binding) in final_stage_a_source_audit_bindings(receipt) {
        ensure!(
            binding.path == expected_path && canonical_sha256(&binding.sha256),
            "final Stage-A source audit named binding drift: {expected_path}"
        );
    }
    let checks = &receipt.required_checks;
    ensure!(
        checks.exact_named_binding_contract
            && checks.displaced_recursive_lookalikes_rejected
            && checks.correct_decoy_with_missing_named_binding_rejected
            && checks.duplicate_path_occurrences_rejected
            && checks.unknown_envelope_fields_rejected
            && checks.audit_git_commit_rejected
            && checks.duplicate_json_keys_rejected
            && checks.trailing_json_data_rejected
            && checks.producer_self_test_passed
            && checks.producer_static_preflight_passed
            && checks.producer_ancestor_preflight_passed
            && checks.prohibited_scientific_modes_not_run,
        "final Stage-A source audit required-check drift"
    );
    Ok(())
}

fn validate_final_stage_b_source_audit_semantics(
    receipt: &FinalStageBSourceAuditReceipt,
) -> Result<()> {
    ensure!(
        receipt.schema == STAGE_B_SOURCE_AUDIT_SCHEMA
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_CUSTODY_PASS_RESULT
            && receipt.evidence_class == SOURCE_AUDIT_EVIDENCE_CLASS
            && receipt.claim_boundary == STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY
            && receipt.no_claim == STAGE_B_SOURCE_AUDIT_NO_CLAIM
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_replay_run
            && source_audit_reviewer_is_valid(&receipt.reviewer)
            && source_audit_preregistration_is_valid(
                &receipt.preregistration,
                STAGE_B_SOURCE_AUDIT_PREREG_PATH,
            )
            && receipt.subject.git_commit.len() == 40
            && receipt
                .subject
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings,
        "final Stage-B source audit semantic boundary drift"
    );
    for (expected_path, binding) in final_stage_b_source_audit_bindings(receipt) {
        ensure!(
            binding.path == expected_path && canonical_sha256(&binding.sha256),
            "final Stage-B source audit named binding drift: {expected_path}"
        );
    }
    let checks = &receipt.required_checks;
    ensure!(
        checks.exact_named_binding_contract
            && checks.displaced_recursive_lookalikes_rejected
            && checks.correct_decoy_with_missing_named_binding_rejected
            && checks.duplicate_path_occurrences_rejected
            && checks.unknown_envelope_fields_rejected
            && checks.audit_git_commit_rejected
            && checks.duplicate_json_keys_rejected
            && checks.trailing_json_data_rejected
            && checks.stage_a_missing_nullable_field_rejected
            && checks.stage_a_mutation_control_schemas_validated
            && checks.stage_a_source_audit_exact_contract_validated
            && checks.g0139_subject_and_exact_fixed_inputs_gate_verified
            && checks.compiled_source_manifest_lock_match_working_bytes
            && checks.overwrite_refusal_verified
            && checks.end_rehash_verified
            && checks.bigint_unconditional_paths_verified
            && checks.producer_self_test_passed
            && checks.producer_static_preflight_passed
            && checks.prohibited_scientific_modes_not_run,
        "final Stage-B source audit required-check drift"
    );
    Ok(())
}

fn validate_source_audit_envelope(receipt: &Value, audit_path: &str) -> Result<()> {
    match audit_path {
        STAGE_A_SOURCE_AUDIT_PATH => validate_final_stage_a_source_audit_semantics(
            &final_stage_a_source_audit_receipt(receipt)?,
        ),
        STAGE_B_SOURCE_AUDIT_PATH => validate_final_stage_b_source_audit_semantics(
            &final_stage_b_source_audit_receipt(receipt)?,
        ),
        _ => anyhow::bail!("unknown source-audit contract: {audit_path}"),
    }
}

fn validate_g0139_receipt_semantics(receipt: &Value) -> Result<()> {
    let custody = receipt
        .pointer("/input_custody")
        .and_then(Value::as_object)
        .context("G-0139 missing input_custody object")?;
    let fixed_inputs = custody
        .get("fixed_inputs")
        .and_then(Value::as_object)
        .context("G-0139 missing exact fixed_inputs map")?;
    let transitive_inputs = custody
        .get("transitive_bound_inputs")
        .and_then(Value::as_object)
        .context("G-0139 missing transitive_bound_inputs map")?;
    ensure!(
        value_string(receipt, "/schema")? == "max11-g0139-g0135-result-audit-v1"
            && value_string(receipt, "/verdict")? == "PASS"
            && value_string(receipt, "/result")? == "CONSISTENT_RESIDUAL_T1"
            && value_string(receipt, "/evidence_class")? == G0139_EVIDENCE_CLASS
            && value_string(receipt, "/claim_boundary")? == G0139_CLAIM_BOUNDARY
            && value_bool(receipt, "/reviewer/same_model_lineage")?
            && value_bool(receipt, "/preregistration/outcome_aware")?
            && value_string(receipt, "/subject/path")? == ANCESTOR_STAGE_D_RESULT_PATH
            && value_string(receipt, "/subject/sha256")? == ANCESTOR_STAGE_D_RESULT_SHA256
            && value_string(receipt, "/subject/git_commit")? == ANCESTOR_STAGE_D_COMMIT
            && value_string(receipt, "/subject/result_observed_before_checker")?
                == "EXACT_RESIDUAL_BATCH_CONTINUE"
            && value_string(receipt, "/git_custody/subject_commit")? == ANCESTOR_STAGE_D_COMMIT
            && value_bool(receipt, "/git_custody/strict_linear_ancestry")?
            && value_string(receipt, "/source_audit_anchor/path")? == ANCESTOR_STAGE_D_AUDIT_PATH
            && value_string(receipt, "/source_audit_anchor/sha256")?
                == ANCESTOR_STAGE_D_AUDIT_SHA256
            && value_string(receipt, "/source_audit_anchor/verdict")? == "PASS"
            && value_bool(
                receipt,
                "/clean_room_execution_boundary/stage_d_bound_bytes_consumed_as_hashes_only"
            )?
            && !value_bool(
                receipt,
                "/clean_room_execution_boundary/stage_d_scientific_replay_rerun"
            )?
            && value_bool(receipt, "/input_custody/entry_exit_rehash_equal")?
            && value_u64(receipt, "/input_custody/fixed_input_count")? == fixed_inputs.len() as u64
            && fixed_inputs.len() == 8
            && fixed_inputs
                .get(ANCESTOR_STAGE_D_RESULT_PATH)
                .and_then(Value::as_str)
                == Some(ANCESTOR_STAGE_D_RESULT_SHA256)
            && fixed_inputs.get(CANDIDATE_PATH).and_then(Value::as_str) == Some(CANDIDATE_SHA256)
            && fixed_inputs
                .get(ANCESTOR_STAGE_D_AUDIT_PATH)
                .and_then(Value::as_str)
                == Some(ANCESTOR_STAGE_D_AUDIT_SHA256)
            && value_u64(receipt, "/input_custody/transitive_bound_input_count")?
                == transitive_inputs.len() as u64
            && transitive_inputs.len() == 92,
        "G-0139 semantic/custody admission drift"
    );
    Ok(())
}

fn validate_g0139_gate(root: &Path, manifest: &ManifestSnapshot) -> Result<Binding> {
    let binding = make_binding(root, G0139_AUDIT_PATH)?;
    ensure!(
        binding.sha256 == G0139_AUDIT_SHA256
            && manifest_binding(manifest, G0139_AUDIT_PATH)? == binding.sha256,
        "manifest does not bind the exact admitted G-0139 receipt"
    );
    ensure!(
        git_commit_for_path(root, G0139_AUDIT_PATH)? == G0139_AUDIT_COMMIT,
        "G-0139 receipt commit drift"
    );
    let receipt = strict_json_value(File::open(checked_repo_path(root, G0139_AUDIT_PATH)?)?)?;
    validate_g0139_receipt_semantics(&receipt)?;
    Ok(binding)
}

fn validate_source_audit(
    root: &Path,
    manifest: &ManifestSnapshot,
    audit_path: &str,
    required_subjects: &[&str],
) -> Result<()> {
    let expected = manifest_binding(manifest, audit_path)?;
    let path = checked_repo_path(root, audit_path)?;
    ensure!(sha256_path(&path)? == expected, "source audit digest drift");
    git_commit_for_path(root, audit_path)?;
    let receipt = strict_json_value(File::open(path)?)?;
    validate_source_audit_envelope(&receipt, audit_path)?;
    match audit_path {
        STAGE_A_SOURCE_AUDIT_PATH => {
            ensure!(
                required_subjects
                    == [
                        STAGE_A_SOURCE_PATH,
                        STAGE_A_ENGINE_PATH,
                        STAGE_A_CARGO_PATH,
                        STAGE_A_LOCK_PATH,
                        STAGE_A_EXECUTABLE_PATH,
                    ],
                "final Stage-A source-audit call contract drift"
            );
            let receipt = final_stage_a_source_audit_receipt(&receipt)?;
            ensure!(
                receipt.subject.git_commit == git_commit_for_path(root, STAGE_A_SOURCE_PATH)?,
                "final Stage-A source-audit subject Git identity drift"
            );
            ensure!(
                sha256_path(&checked_repo_path(root, STAGE_A_SOURCE_AUDIT_PREREG_PATH)?)?
                    == receipt.preregistration.sha256
                    && git_commit_for_path(root, STAGE_A_SOURCE_AUDIT_PREREG_PATH)?
                        == receipt.preregistration.git_commit,
                "final Stage-A source-audit preregistration custody drift"
            );
            for (subject, binding) in final_stage_a_source_audit_bindings(&receipt) {
                let expected = manifest_binding(manifest, subject)?;
                ensure!(
                    binding.sha256 == expected
                        && sha256_path(&checked_repo_path(root, subject)?)? == binding.sha256
                        && !git_commit_for_path(root, subject)?.is_empty(),
                    "final Stage-A source audit does not bind exact named subject: {subject}"
                );
            }
            Ok(())
        }
        STAGE_B_SOURCE_AUDIT_PATH => {
            ensure!(
                required_subjects
                    == [
                        STAGE_B_SOURCE_PATH,
                        STAGE_B_CARGO_PATH,
                        STAGE_B_LOCK_PATH,
                        STAGE_B_EXECUTABLE_PATH,
                    ],
                "final Stage-B source-audit call contract drift"
            );
            let receipt = final_stage_b_source_audit_receipt(&receipt)?;
            ensure!(
                receipt.subject.git_commit == git_commit_for_path(root, STAGE_B_SOURCE_PATH)?,
                "final Stage-B source-audit subject Git identity drift"
            );
            ensure!(
                sha256_path(&checked_repo_path(root, STAGE_B_SOURCE_AUDIT_PREREG_PATH)?)?
                    == receipt.preregistration.sha256
                    && git_commit_for_path(root, STAGE_B_SOURCE_AUDIT_PREREG_PATH)?
                        == receipt.preregistration.git_commit,
                "final Stage-B source-audit preregistration custody drift"
            );
            for (subject, binding) in final_stage_b_source_audit_bindings(&receipt) {
                let expected = manifest_binding(manifest, subject)?;
                ensure!(
                    binding.sha256 == expected
                        && sha256_path(&checked_repo_path(root, subject)?)? == binding.sha256
                        && !git_commit_for_path(root, subject)?.is_empty(),
                    "final Stage-B source audit does not bind exact named subject: {subject}"
                );
            }
            Ok(())
        }
        _ => anyhow::bail!("unknown source-audit contract: {audit_path}"),
    }
}

fn validate_compiled_and_static(root: &Path) -> Result<()> {
    for (compiled, path, expected) in [
        (COMPILED_SOURCE, STAGE_B_SOURCE_PATH, None),
        (COMPILED_MANIFEST, STAGE_B_CARGO_PATH, None),
        (COMPILED_LOCK, STAGE_B_LOCK_PATH, None),
        (
            COMPILED_PREREGISTRATION,
            PREREGISTRATION_PATH,
            Some(PREREGISTRATION_SHA256),
        ),
        (COMPILED_CANDIDATE, CANDIDATE_PATH, Some(CANDIDATE_SHA256)),
        (COMPILED_KERNEL, KERNEL_PATH, Some(KERNEL_SHA256)),
        (
            COMPILED_G0139_AUDIT,
            G0139_AUDIT_PATH,
            Some(G0139_AUDIT_SHA256),
        ),
    ] {
        let compiled_sha = sha256_bytes(compiled);
        let disk_sha = sha256_path(&checked_repo_path(root, path)?)?;
        ensure!(
            compiled_sha == disk_sha && expected.is_none_or(|value| value == disk_sha),
            "compiled/static byte drift: {path}"
        );
    }
    make_expected_binding(root, PANEL_INPUT_PATH, PANEL_INPUT_SHA256)?;
    ensure!(
        git_commit_for_path(root, CANDIDATE_PATH)? == CANDIDATE_GIT_COMMIT,
        "candidate Git ancestry drift"
    );
    git_commit_for_path(root, PREREGISTRATION_PATH)?;
    git_commit_for_path(root, KERNEL_PATH)?;
    Ok(())
}

fn validate_manifest(root: &Path, supplied_path: &Path) -> Result<ManifestSnapshot> {
    ensure!(
        supplied_path == Path::new(MANIFEST_PATH),
        "G-0140 manifest path drift"
    );
    let path = checked_repo_path(root, MANIFEST_PATH)?;
    let sha256 = sha256_path(&path)?;
    let manifest: StudyManifest = strict_json(File::open(path)?)?;
    ensure!(
        manifest.schema == MANIFEST_SCHEMA
            && manifest.selected_branch == "G0135_EXACT_RESIDUAL_POOL128"
            && [
                &manifest.preregistration_git_commit,
                &manifest.producer_git_commit,
                &manifest.source_audit_git_commit,
            ]
            .iter()
            .all(|commit| {
                commit.len() == 40
                    && commit
                        .bytes()
                        .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
            })
            && manifest.stage_order
                == [
                    "A_REPLAY_POOL128",
                    "B_PRICE_POOL128",
                    "C_COMPLETE_MATRIX_RANK_SELECT",
                    "D_REOPENED_EXACT_MASTER",
                    "E_GLOBAL_REPLAY_IF_MEMBER",
                ],
        "G-0140 manifest identity/stage-order drift"
    );
    ensure!(
        manifest.parameters
            == ManifestParameters {
                n: N,
                records: RECORDS,
                existing_rows: ROWS,
                existing_terms: TERMS,
                accumulated_hinge_rows: CARRY_DIRECTIONS,
                pool_k: K,
                max_admitted_rows: 32,
                threads: THREADS,
                arithmetic: "signed_num_bigint_BigInt_and_exact_Q".to_string(),
                direction_order: "ordinary_signed_i8_tuple_lexicographic".to_string(),
                column_order: "canonical_sequence_0_through_163739".to_string(),
            },
        "G-0140 manifest parameter drift"
    );
    let expected_outputs = BTreeMap::from([
        (
            "A".to_string(),
            PlannedOutput {
                path: STAGE_A_RECEIPT_PATH.to_string(),
                schema: STAGE_A_SCHEMA.to_string(),
            },
        ),
        (
            "B".to_string(),
            PlannedOutput {
                path: OUTPUT_PATH.to_string(),
                schema: OUTPUT_SCHEMA.to_string(),
            },
        ),
        (
            "C".to_string(),
            PlannedOutput {
                path: STAGE_C_OUTPUT_PATH.to_string(),
                schema: STAGE_C_OUTPUT_SCHEMA.to_string(),
            },
        ),
        (
            "D".to_string(),
            PlannedOutput {
                path: STAGE_D_OUTPUT_PATH.to_string(),
                schema: STAGE_D_OUTPUT_SCHEMA.to_string(),
            },
        ),
        (
            "E".to_string(),
            PlannedOutput {
                path: STAGE_E_OUTPUT_PATH.to_string(),
                schema: STAGE_E_OUTPUT_SCHEMA.to_string(),
            },
        ),
    ]);
    ensure!(
        manifest.planned_outputs == expected_outputs,
        "G-0140 manifest planned-output drift"
    );

    let mut bindings_by_path = BTreeMap::new();
    for (label, binding) in &manifest.bindings {
        ensure!(
            !label.is_empty()
                && canonical_sha256(&binding.sha256)
                && bindings_by_path
                    .insert(binding.path.clone(), binding.sha256.clone())
                    .is_none(),
            "duplicate/malformed manifest binding: {label}"
        );
    }
    for binding in &manifest.transitive_inputs {
        ensure!(
            canonical_sha256(&binding.sha256)
                && bindings_by_path
                    .insert(binding.path.clone(), binding.sha256.clone())
                    .is_none(),
            "duplicate/malformed transitive binding: {}",
            binding.path
        );
    }
    for required in [
        PREREGISTRATION_PATH,
        PANEL_INPUT_PATH,
        CANDIDATE_PATH,
        ANCESTOR_STAGE_D_RESULT_PATH,
        KERNEL_PATH,
        G0139_AUDIT_PATH,
        STAGE_A_SOURCE_PATH,
        STAGE_A_ENGINE_PATH,
        STAGE_A_CARGO_PATH,
        STAGE_A_LOCK_PATH,
        STAGE_A_EXECUTABLE_PATH,
        STAGE_A_SOURCE_AUDIT_PATH,
        STAGE_B_SOURCE_PATH,
        STAGE_B_CARGO_PATH,
        STAGE_B_LOCK_PATH,
        STAGE_B_EXECUTABLE_PATH,
        STAGE_B_SOURCE_AUDIT_PATH,
    ] {
        ensure!(
            bindings_by_path.contains_key(required),
            "G-0140 manifest omits required Stage-B path: {required}"
        );
    }
    for (path, expected) in &bindings_by_path {
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "manifest-bound input drift: {path}"
        );
    }
    let snapshot = ManifestSnapshot {
        manifest,
        sha256,
        bindings_by_path,
    };
    ensure!(
        snapshot.manifest.preregistration_git_commit
            == git_commit_for_path(root, PREREGISTRATION_PATH)?
            && snapshot.manifest.producer_git_commit
                == git_commit_for_path(root, STAGE_A_SOURCE_PATH)?
            && snapshot.manifest.source_audit_git_commit
                == git_commit_for_path(root, STAGE_A_SOURCE_AUDIT_PATH)?,
        "G-0140 manifest Git commit drift"
    );
    validate_source_audit(
        root,
        &snapshot,
        STAGE_A_SOURCE_AUDIT_PATH,
        &[
            STAGE_A_SOURCE_PATH,
            STAGE_A_ENGINE_PATH,
            STAGE_A_CARGO_PATH,
            STAGE_A_LOCK_PATH,
            STAGE_A_EXECUTABLE_PATH,
        ],
    )?;
    validate_source_audit(
        root,
        &snapshot,
        STAGE_B_SOURCE_AUDIT_PATH,
        &[
            STAGE_B_SOURCE_PATH,
            STAGE_B_CARGO_PATH,
            STAGE_B_LOCK_PATH,
            STAGE_B_EXECUTABLE_PATH,
        ],
    )?;
    validate_g0139_gate(root, &snapshot)?;
    Ok(snapshot)
}

fn validate_current_release(root: &Path, manifest: &ManifestSnapshot) -> Result<Binding> {
    let executable = std::env::current_exe()?.canonicalize()?;
    let expected = checked_repo_path(root, STAGE_B_EXECUTABLE_PATH)?;
    ensure!(
        executable == expected,
        "scientific preflight/run requires frozen Stage-B release executable"
    );
    let binding = make_binding(root, STAGE_B_EXECUTABLE_PATH)?;
    ensure!(
        manifest_binding(manifest, STAGE_B_EXECUTABLE_PATH)? == binding.sha256,
        "manifest Stage-B executable digest drift"
    );
    git_commit_for_path(root, STAGE_B_EXECUTABLE_PATH)?;
    Ok(binding)
}

fn validate_exact_hinge(value: &ExactHinge) -> Result<()> {
    validate_direction(&value.direction)?;
    ensure!(
        canonical_integer(&value.coefficient) && value.coefficient != "0",
        "nonzero hinge receipt coefficient drift"
    );
    Ok(())
}

fn validate_exact_linear(value: &ExactLinear) -> Result<()> {
    ensure!(
        value.coordinate < N && canonical_integer(&value.coefficient) && value.coefficient != "0",
        "nonzero linear receipt drift"
    );
    Ok(())
}

fn validate_term_normal_form_receipts(
    receipts: &[TermNormalFormReceipt],
    candidate: &Candidate,
) -> Result<()> {
    ensure!(
        receipts.len() == candidate.terms.len()
            && receipts
                .iter()
                .map(|receipt| receipt.sequence)
                .eq(candidate.terms.iter().map(|term| term.sequence)),
        "Stage-A term normal-form transcript order drift"
    );
    let mut total = 0u64;
    let mut hinge_entries = 0u64;
    for receipt in receipts {
        let inactive_multiplier = N.checked_sub(receipt.active_vertices).map(factorial);
        let expected_leaves = inactive_multiplier.map(|value| factorial(N) / value);
        ensure!(
            receipt.enumeration_mode
                == "exact_active_vertex_injections_with_inactive_label_factorial_multiplicity"
                && receipt.active_vertices <= N
                && inactive_multiplier == Some(receipt.inactive_label_multiplicity)
                && expected_leaves == Some(receipt.compressed_leaves_generated)
                && receipt.compressed_leaves_generated == receipt.compressed_leaves_visited
                && receipt.compressed_leaves_visited == receipt.compressed_leaves_accepted
                && receipt
                    .compressed_leaves_accepted
                    .checked_mul(receipt.inactive_label_multiplicity)
                    == Some(factorial(N))
                && receipt.generated_labelled_permutations == factorial(N)
                && receipt.visited_labelled_permutations == factorial(N)
                && receipt.accepted_labelled_permutations == factorial(N)
                && receipt.skipped_labelled_permutations == 0
                && receipt.unclassified_labelled_permutations == 0
                && receipt.failed_labelled_permutations == 0
                && canonical_sha256(&receipt.normal_form_sha256)
                && receipt.scientific_coefficient_arithmetic == "signed_num_bigint_BigInt"
                && receipt.independent_exact_linear_crosscheck
                && receipt.bounded_kernel_crosscheck,
            "Stage-A term normal-form receipt drift at sequence {}",
            receipt.sequence
        );
        total = total
            .checked_add(receipt.visited_labelled_permutations)
            .context("Stage-A term transcript census overflow")?;
        hinge_entries = hinge_entries
            .checked_add(u64::try_from(receipt.hinge_entries)?)
            .context("Stage-A hinge-entry transcript census overflow")?;
    }
    ensure!(
        total == EXPECTED_LABELLED_PERMUTATIONS
            && hinge_entries == EXPECTED_HINGE_ENTRIES_PROCESSED,
        "Stage-A term transcript global census or hinge-entry drift"
    );
    Ok(())
}

fn validate_mutation_control(
    control: &MutationControl,
    expected_name: &str,
    baseline_digest: &str,
) -> Result<()> {
    if let Some(hinge) = &control.first_nonzero_hinge.0 {
        validate_exact_hinge(hinge)?;
    }
    if let Some(linear) = &control.first_nonzero_linear.0 {
        validate_exact_linear(linear)?;
    }
    ensure!(
        control.name == expected_name
            && control.baseline_complete_residual_sha256 == baseline_digest
            && canonical_sha256(&control.mutated_complete_residual_sha256)
            && control.mutated_complete_residual_sha256 != baseline_digest
            && control.changed_from_baseline
            && control.detected
            && (control.first_nonzero_hinge.0.is_some()
                || control.first_nonzero_linear.0.is_some()),
        "Stage-A mutation-control semantic drift: {expected_name}"
    );
    Ok(())
}

fn validate_stage_a_structured_controls(
    receipt: &StageAReceipt,
    candidate: &Candidate,
) -> Result<()> {
    let finite = &receipt.independent_finite_412_row_replay;
    let finite_mutant = &finite.coefficient_plus_one_mutant;
    let zero_residual_digest = sha256_bytes("0\n".repeat(ROWS).as_bytes());
    ensure!(
        finite.rows == ROWS
            && finite.panel_rows == 301
            && finite.linear_rows == N
            && finite.accumulated_hinge_rows == CARRY_DIRECTIONS
            && finite.cache_layout
                == "sequence-major: offset=((sequence*301)+row)*16; signed little-endian i128"
            && finite.arithmetic == "signed_num_bigint_BigInt"
            && finite.all_rows_exactly_replayed
            && finite.residuals_decimal_lf_sha256 == zero_residual_digest
            && finite_mutant.sequence
                == candidate
                    .terms
                    .first()
                    .context("Stage-A finite replay candidate has no term")?
                    .sequence
            && finite_mutant.coefficient_delta == "+1"
            && finite_mutant.first_nonzero_residual_row < ROWS
            && canonical_sha256(&finite_mutant.residuals_decimal_lf_sha256)
            && finite_mutant.residuals_decimal_lf_sha256 != zero_residual_digest
            && finite_mutant.rejected,
        "Stage-A independent finite replay receipt drift"
    );
    validate_term_normal_form_receipts(&receipt.term_normal_forms, candidate)?;
    for (control, expected_name) in [
        (
            &receipt.coefficient_plus_one,
            "first_nonzero_coefficient_plus_one",
        ),
        (&receipt.target_scale_plus_one, "target_scale_plus_one"),
        (
            &receipt.target_coordinate_plus_one,
            "target_coordinate_10_plus_one",
        ),
        (&receipt.omitted_final_term, "omitted_final_nonzero_term"),
        (
            &receipt.omitted_first_term_direction,
            "omitted_first_term_active_direction",
        ),
    ] {
        validate_mutation_control(
            control,
            expected_name,
            &receipt.complete_residual_decimal_lf_sha256,
        )?;
    }
    let census = &receipt.census_controls;
    ensure!(
        census.dynamic_term_count == TERMS
            && census.factorial_11 == factorial(N)
            && census.expected_labelled_permutations == EXPECTED_LABELLED_PERMUTATIONS
            && census.observed_labelled_permutations == EXPECTED_LABELLED_PERMUTATIONS
            && census.per_term_generated_equals_visited_equals_accepted
            && census.zero_skipped_unclassified_failed
            && census.omitted_last_orbit_rejected
            && census.decremented_global_census_rejected
            && census.accumulated_direction_count_100
            && census.omitted_accumulated_direction_rejected,
        "Stage-A census-control receipt drift"
    );
    let selection = &receipt.selection_controls;
    ensure!(
        selection.exact_batch_count_or_zero_terminal
            && selection.strict_signed_lexicographic_order
            && selection.excludes_accumulated_directions
            && selection.direction_reordering_changes_digest
            && selection.coefficient_plus_one_changes_digest,
        "Stage-A Pool128 selection-control receipt drift"
    );
    Ok(())
}

fn validate_stage_a_receipt(
    root: &Path,
    manifest: &ManifestSnapshot,
    supplied_path: &Path,
    candidate: &Candidate,
) -> Result<StageAReceipt> {
    ensure!(
        supplied_path == Path::new(STAGE_A_RECEIPT_PATH),
        "Stage-A receipt path drift"
    );
    let receipt: StageAReceipt =
        strict_json(File::open(checked_repo_path(root, STAGE_A_RECEIPT_PATH)?)?)?;
    ensure!(
        receipt.schema == STAGE_A_SCHEMA
            && receipt.result == STAGE_A_RESULT
            && !receipt.claim_boundary.is_empty()
            && receipt.g0140_manifest.path == MANIFEST_PATH
            && receipt.g0140_manifest.sha256 == manifest.sha256
            && receipt.candidate_schema == CANDIDATE_SCHEMA
            && receipt.candidate_result == CANDIDATE_RESULT
            && receipt.rows == ROWS
            && receipt.records == RECORDS
            && receipt.selected_rank == candidate.rank
            && receipt.support_columns == candidate.support_sequences.len()
            && receipt.terms == TERMS
            && receipt.target_scale == TARGET_SCALE
            && receipt.stage_c_all_412_rational_rows_replayed
            && receipt.stage_c_all_412_integer_rows_replayed
            && receipt.stage_c_primitive_denominator_clearing
            && receipt.stage_c_coefficient_plus_one_mutant_rejected
            && receipt.stage_c_prior_scale_carryover_mutant_rejected
            && receipt.arithmetic == "signed_num_bigint_BigInt_unconditional_exact"
            && receipt.decision_rule
                == "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate"
            && receipt.complete_global_replay
            && !receipt.all_hinge_and_linear_residuals_zero,
        "Stage-A Pool128 identity/arithmetic drift"
    );
    for binding in [
        &receipt.g0135_manifest,
        &receipt.protocol,
        &receipt.producer_source,
        &receipt.producer_engine,
        &receipt.producer_executable,
        &receipt.g0139_result_audit,
        &receipt.ancestor_stage_d_result,
        &receipt.stage_c_member,
    ] {
        binding_matches(root, manifest, binding)?;
    }
    ensure!(
        receipt.g0135_manifest.path == candidate.manifest_path
            && receipt.g0135_manifest.sha256 == candidate.manifest_sha256
            && receipt.protocol.path == PREREGISTRATION_PATH
            && receipt.protocol.sha256 == PREREGISTRATION_SHA256
            && receipt.producer_source.path == STAGE_A_SOURCE_PATH
            && receipt.producer_engine.path == STAGE_A_ENGINE_PATH
            && receipt.producer_executable.path == STAGE_A_EXECUTABLE_PATH
            && receipt.g0139_result_audit.path == G0139_AUDIT_PATH
            && receipt.ancestor_stage_d_result.path == ANCESTOR_STAGE_D_RESULT_PATH
            && receipt.ancestor_stage_d_result.sha256 == ANCESTOR_STAGE_D_RESULT_SHA256
            && receipt.stage_c_member.path == CANDIDATE_PATH
            && receipt.stage_c_member.sha256 == CANDIDATE_SHA256,
        "Stage-A source/admission/candidate binding drift"
    );
    for binding in receipt.source_and_audit_bindings.values() {
        binding_matches(root, manifest, binding)?;
    }
    ensure!(
        receipt.labelled_permutations_expected == EXPECTED_LABELLED_PERMUTATIONS
            && receipt.hinge_entries_processed == EXPECTED_HINGE_ENTRIES_PROCESSED
            && receipt.labelled_permutations_checked == EXPECTED_LABELLED_PERMUTATIONS
            && receipt.aggregate_hinge_support == EXPECTED_AGGREGATE_HINGE_SUPPORT
            && receipt.nonzero_hinge_directions == EXPECTED_NONZERO_HINGE_DIRECTIONS
            && receipt.aggregate_hinge_decimal_lf_sha256 == EXPECTED_AGGREGATE_HINGE_SHA256
            && receipt.nonzero_hinge_decimal_lf_sha256 == EXPECTED_NONZERO_HINGE_SHA256
            && canonical_sha256(&receipt.complete_residual_decimal_lf_sha256)
            && receipt.term_normal_form_transcript_sha256 == EXPECTED_TERM_TRANSCRIPT_SHA256
            && receipt.term_normal_forms.len() == TERMS,
        "Stage-A disclosed exact replay anchor drift"
    );
    ensure!(
        receipt.accumulated_direction_checks.len() == CARRY_DIRECTIONS
            && receipt.all_100_accumulated_directions_exact_zero,
        "Stage-A accumulated-direction census drift"
    );
    let mut carried = Vec::with_capacity(CARRY_DIRECTIONS);
    let mut seen = BTreeSet::new();
    for (index, check) in receipt.accumulated_direction_checks.iter().enumerate() {
        validate_direction(&check.direction)?;
        ensure!(
            check.index == index
                && check.source_index < CARRY_DIRECTIONS
                && !check.source.is_empty()
                && check.aggregate_coefficient == "0"
                && check.direct_dp_coefficient == "0"
                && check.routes_agree
                && check.exact_zero
                && seen.insert(check.direction),
            "Stage-A accumulated-direction check drift at {index}"
        );
        carried.push(check.direction);
    }
    ensure!(
        receipt.linear_residuals_after_target.len() == N
            && receipt
                .linear_residuals_after_target
                .iter()
                .all(|value| value == "0")
            && receipt.all_11_linear_residuals_exact_zero
            && receipt.first_nonzero_linear.0.is_none(),
        "Stage-A linear reconciliation drift"
    );
    ensure!(
        receipt.first_nonzero_hinge.0.as_ref()
            == Some(&ExactHinge {
                direction: EXPECTED_FIRST_DIRECTION,
                coefficient: EXPECTED_FIRST_COEFFICIENT.to_string(),
            })
            && receipt.pool_k == K
            && receipt.pool_count == K,
        "Stage-A first residual or Pool128 census drift"
    );
    validate_stage_a_structured_controls(&receipt, candidate)?;
    validate_pool(
        &receipt.pool,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )?;
    ensure!(
        receipt.inputs_rehashed_at_end
            && receipt.manifest_rehashed_at_end
            && receipt.candidate_rehashed_at_end
            && receipt.wall_seconds > 0.0
            && candidate.terms.len() == receipt.terms,
        "Stage-A end custody/resource drift"
    );
    Ok(receipt)
}

fn custody_snapshot(
    root: &Path,
    manifest: &ManifestSnapshot,
    stage_a_sha: &str,
) -> Result<BTreeMap<String, String>> {
    let mut snapshot = manifest.bindings_by_path.clone();
    snapshot.insert(MANIFEST_PATH.to_string(), manifest.sha256.clone());
    snapshot.insert(STAGE_A_RECEIPT_PATH.to_string(), stage_a_sha.to_string());
    for (path, expected) in &snapshot {
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "custody drift: {path}"
        );
    }
    Ok(snapshot)
}

fn load_static_inputs(
    root: &Path,
    input_path: &Path,
    candidate_path: &Path,
) -> Result<(PanelInput, Candidate)> {
    ensure!(
        input_path == Path::new(PANEL_INPUT_PATH) && candidate_path == Path::new(CANDIDATE_PATH),
        "static input path drift"
    );
    validate_compiled_and_static(root)?;
    let panel: PanelInput = strict_json(File::open(checked_repo_path(root, PANEL_INPUT_PATH)?)?)?;
    let candidate: Candidate = strict_json(File::open(checked_repo_path(root, CANDIDATE_PATH)?)?)?;
    validate_panel(&panel)?;
    validate_candidate(&candidate)?;
    Ok((panel, candidate))
}

fn load_and_validate_inputs(
    root: &Path,
    input_path: &Path,
    receipt_path: &Path,
    candidate_path: &Path,
    manifest_path: &Path,
) -> Result<ValidatedInputs> {
    let (panel, candidate) = load_static_inputs(root, input_path, candidate_path)?;
    let manifest = validate_manifest(root, manifest_path)?;
    validate_current_release(root, &manifest)?;
    let receipt = validate_stage_a_receipt(root, &manifest, receipt_path, &candidate)?;
    let stage_a_sha = sha256_path(&checked_repo_path(root, STAGE_A_RECEIPT_PATH)?)?;
    let custody = custody_snapshot(root, &manifest, &stage_a_sha)?;
    Ok(ValidatedInputs {
        panel,
        candidate,
        receipt,
        manifest,
        custody,
    })
}

fn make_input_mutation_controls(
    records: &[Record],
    receipt: &StageAReceipt,
) -> Result<InputMutationControls> {
    let carried = receipt
        .accumulated_direction_checks
        .iter()
        .map(|check| check.direction)
        .collect::<Vec<_>>();
    validate_pool(
        &receipt.pool,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )?;

    let mut count_mutant = receipt.pool.clone();
    count_mutant.pop();
    let pool_count_mutant_rejected = validate_pool(
        &count_mutant,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )
    .is_err();

    let mut order_mutant = receipt.pool.clone();
    order_mutant.swap(0, 1);
    let pool_order_mutant_rejected = validate_pool(
        &order_mutant,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )
    .is_err();

    let mut duplicate_mutant = receipt.pool.clone();
    duplicate_mutant[1] = duplicate_mutant[0].clone();
    let pool_duplicate_mutant_rejected = validate_pool(
        &duplicate_mutant,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )
    .is_err();

    let mut invalid_direction_mutant = receipt.pool.clone();
    for coordinate in &mut invalid_direction_mutant[0].direction {
        *coordinate = -*coordinate;
    }
    let direction_invalidity_mutant_rejected = validate_pool(
        &invalid_direction_mutant,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )
    .is_err();

    let mut residual_mutant = receipt.pool.clone();
    residual_mutant[0].coefficient =
        (parse_bigint(&residual_mutant[0].coefficient)? + BigInt::from(1)).to_string();
    let residual_plus_one_mutant_rejected = validate_pool(
        &residual_mutant,
        &receipt.pool_directions_i8_sha256,
        &receipt.pool_exact_residuals_decimal_lf_sha256,
        &carried,
        true,
    )
    .is_err();

    let record_census_truncation_rejected = validate_record_axis(
        records[..RECORDS - 1].iter().map(|record| record.sequence),
        RECORDS,
    )
    .is_err();
    let mut order = records
        .iter()
        .map(|record| record.sequence)
        .collect::<Vec<_>>();
    order.swap(0, 1);
    let record_order_mutant_rejected = validate_record_axis(order, RECORDS).is_err();
    let all_rejected = pool_count_mutant_rejected
        && pool_order_mutant_rejected
        && pool_duplicate_mutant_rejected
        && direction_invalidity_mutant_rejected
        && residual_plus_one_mutant_rejected
        && record_census_truncation_rejected
        && record_order_mutant_rejected;
    ensure!(all_rejected, "Stage-B input mutation control escaped");
    Ok(InputMutationControls {
        pool_count_mutant_rejected,
        pool_order_mutant_rejected,
        pool_duplicate_mutant_rejected,
        direction_invalidity_mutant_rejected,
        residual_plus_one_mutant_rejected,
        record_census_truncation_rejected,
        record_order_mutant_rejected,
        all_rejected,
    })
}

fn rejects_unknown_field<T: DeserializeOwned>() -> bool {
    serde_json::from_value::<T>(serde_json::json!({"__unexpected": true}))
        .is_err_and(|error| error.to_string().contains("unknown field"))
}

fn source_audit_binding_fixture(path: &str) -> Value {
    serde_json::json!({"path": path, "sha256": "0".repeat(64)})
}

fn stage_a_source_audit_fixture() -> Value {
    serde_json::json!({
        "schema": STAGE_A_SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": SOURCE_CUSTODY_PASS_RESULT,
        "evidence_class": SOURCE_AUDIT_EVIDENCE_CLASS,
        "claim_boundary": STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": true,
            "fresh_context": true
        },
        "preregistration": {
            "path": STAGE_A_SOURCE_AUDIT_PREREG_PATH,
            "sha256": "0".repeat(64),
            "git_commit": "0".repeat(40),
            "committed_and_pushed_before_subject_source_inspection": true,
            "committed_and_pushed_before_runtime_checks": true
        },
        "subject": {
            "git_commit": "0".repeat(40),
            "commit_object_and_working_bytes_equal_for_all_bindings": true,
            "bindings": {
                "main_source": source_audit_binding_fixture(STAGE_A_SOURCE_PATH),
                "engine_source": source_audit_binding_fixture(STAGE_A_ENGINE_PATH),
                "cargo_manifest": source_audit_binding_fixture(STAGE_A_CARGO_PATH),
                "cargo_lock": source_audit_binding_fixture(STAGE_A_LOCK_PATH),
                "release_executable": source_audit_binding_fixture(STAGE_A_EXECUTABLE_PATH)
            }
        },
        "required_checks": {
            "exact_named_binding_contract": true,
            "displaced_recursive_lookalikes_rejected": true,
            "correct_decoy_with_missing_named_binding_rejected": true,
            "duplicate_path_occurrences_rejected": true,
            "unknown_envelope_fields_rejected": true,
            "audit_git_commit_rejected": true,
            "duplicate_json_keys_rejected": true,
            "trailing_json_data_rejected": true,
            "producer_self_test_passed": true,
            "producer_static_preflight_passed": true,
            "producer_ancestor_preflight_passed": true,
            "prohibited_scientific_modes_not_run": true
        },
        "scientific_manifest_observed": false,
        "scientific_input_observed": false,
        "scientific_output_observed": false,
        "scientific_replay_run": false,
        "no_claim": STAGE_A_SOURCE_AUDIT_NO_CLAIM
    })
}

fn stage_b_source_audit_fixture() -> Value {
    serde_json::json!({
        "schema": STAGE_B_SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": SOURCE_CUSTODY_PASS_RESULT,
        "evidence_class": SOURCE_AUDIT_EVIDENCE_CLASS,
        "claim_boundary": STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": true,
            "fresh_context": true
        },
        "preregistration": {
            "path": STAGE_B_SOURCE_AUDIT_PREREG_PATH,
            "sha256": "0".repeat(64),
            "git_commit": "0".repeat(40),
            "committed_and_pushed_before_subject_source_inspection": true,
            "committed_and_pushed_before_runtime_checks": true
        },
        "subject": {
            "git_commit": "0".repeat(40),
            "commit_object_and_working_bytes_equal_for_all_bindings": true,
            "bindings": {
                "main_source": source_audit_binding_fixture(STAGE_B_SOURCE_PATH),
                "cargo_manifest": source_audit_binding_fixture(STAGE_B_CARGO_PATH),
                "cargo_lock": source_audit_binding_fixture(STAGE_B_LOCK_PATH),
                "release_executable": source_audit_binding_fixture(STAGE_B_EXECUTABLE_PATH)
            }
        },
        "required_checks": {
            "exact_named_binding_contract": true,
            "displaced_recursive_lookalikes_rejected": true,
            "correct_decoy_with_missing_named_binding_rejected": true,
            "duplicate_path_occurrences_rejected": true,
            "unknown_envelope_fields_rejected": true,
            "audit_git_commit_rejected": true,
            "duplicate_json_keys_rejected": true,
            "trailing_json_data_rejected": true,
            "stage_a_missing_nullable_field_rejected": true,
            "stage_a_mutation_control_schemas_validated": true,
            "stage_a_source_audit_exact_contract_validated": true,
            "g0139_subject_and_exact_fixed_inputs_gate_verified": true,
            "compiled_source_manifest_lock_match_working_bytes": true,
            "overwrite_refusal_verified": true,
            "end_rehash_verified": true,
            "bigint_unconditional_paths_verified": true,
            "producer_self_test_passed": true,
            "producer_static_preflight_passed": true,
            "prohibited_scientific_modes_not_run": true
        },
        "scientific_manifest_observed": false,
        "scientific_input_observed": false,
        "scientific_output_observed": false,
        "scientific_replay_run": false,
        "no_claim": STAGE_B_SOURCE_AUDIT_NO_CLAIM
    })
}

fn self_test() -> Result<()> {
    for valid in ["0", "1", "-1", "123456789012345678901234567890"] {
        ensure!(canonical_integer(valid), "valid integer rejected");
    }
    for invalid in ["", "-", "+1", "00", "01", "-0", "-01", "1/2", " 1"] {
        ensure!(!canonical_integer(invalid), "invalid integer accepted");
    }
    ensure!(
        canonical_positive_integer("1")
            && !canonical_positive_integer("0")
            && !canonical_positive_integer("-1"),
        "canonical positive-integer drift"
    );
    ensure!(
        strict_json::<Term>(br#"{"sequence":0,"coefficient":"1","coefficient":"2"}"#.as_slice())
            .is_err()
            && serde_json::from_str::<Term>(r#"{"sequence":0,"coefficient":"1","extra":2}"#)
                .is_err(),
        "duplicate or unknown term field accepted"
    );
    let mut candidate_unknown = strict_json_value(COMPILED_CANDIDATE)?;
    candidate_unknown["__unexpected"] = Value::Bool(true);
    let strict_record_fixture = serde_json::json!({
        "stage": "DISJOINT",
        "orbit_index": 0,
        "representative": {
            "left_added_edge": [0, 1],
            "right_added_edge": [0, 1],
            "source_term": 0
        },
        "signed_class_sha256": "0".repeat(64),
        "sequence": 0,
        "signed_mass": 1,
        "active_vertices": 2,
        "negative_edges": [[0, 1]],
        "positive_edges": [[0, 1]],
        "in_disjoint": true,
        "in_shared_distinct": true
    });
    ensure!(
        serde_json::from_value::<Candidate>(candidate_unknown).is_err()
            && rejects_unknown_field::<StageAReceipt>()
            && rejects_unknown_field::<AccumulatedDirectionCheck>()
            && serde_json::from_value::<StrictRecord>(strict_record_fixture.clone()).is_ok(),
        "strict Candidate/Stage-A/nested input schema control failed"
    );
    let mut strict_record_unknown = strict_record_fixture;
    strict_record_unknown["__unexpected"] = Value::Bool(true);
    ensure!(
        serde_json::from_value::<StrictRecord>(strict_record_unknown).is_err(),
        "unknown imported Record field accepted"
    );

    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct RequiredNullableFixture {
        first_nonzero_linear: RequiredNullable<ExactLinear>,
    }
    let explicit_null: RequiredNullableFixture =
        serde_json::from_value(serde_json::json!({"first_nonzero_linear": null}))?;
    ensure!(
        explicit_null.first_nonzero_linear.0.is_none()
            && serde_json::from_value::<RequiredNullableFixture>(serde_json::json!({})).is_err(),
        "required-nullable missing/null distinction failed"
    );
    let mutation_fixture = serde_json::json!({
        "name": "target_scale_plus_one",
        "first_nonzero_hinge": null,
        "first_nonzero_linear": {"coordinate": 10, "coefficient": "-39916800"},
        "baseline_complete_residual_sha256": "0".repeat(64),
        "mutated_complete_residual_sha256": "1".repeat(64),
        "changed_from_baseline": true,
        "detected": true
    });
    let mut missing_mutation_nullable = mutation_fixture.clone();
    missing_mutation_nullable
        .as_object_mut()
        .context("mutation-control fixture drift")?
        .remove("first_nonzero_linear");
    let mut unknown_mutation_field = mutation_fixture.clone();
    unknown_mutation_field["unknown"] = Value::Bool(true);
    ensure!(
        serde_json::from_value::<MutationControl>(mutation_fixture).is_ok()
            && serde_json::from_value::<MutationControl>(missing_mutation_nullable).is_err()
            && serde_json::from_value::<MutationControl>(unknown_mutation_field).is_err()
            && serde_json::from_value::<FiniteReplayReceipt>(serde_json::json!([])).is_err()
            && serde_json::from_value::<TermNormalFormReceipt>(serde_json::json!([])).is_err()
            && serde_json::from_value::<CensusControls>(serde_json::json!([])).is_err()
            && serde_json::from_value::<SelectionControls>(serde_json::json!([])).is_err(),
        "Stage-A structured mutation/census receipt schema control failed"
    );

    let g0139 = strict_json_value(std::io::Cursor::new(COMPILED_G0139_AUDIT))?;
    validate_g0139_receipt_semantics(&g0139)?;
    let mut g0139_missing_candidate = g0139.clone();
    g0139_missing_candidate["input_custody"]["fixed_inputs"]
        .as_object_mut()
        .context("G-0139 fixed-input fixture drift")?
        .remove(CANDIDATE_PATH);
    g0139_missing_candidate["input_custody"]["fixed_inputs"]["fixture/replacement"] =
        Value::String("6".repeat(64));
    g0139_missing_candidate["unrelated_recursive_decoy"] = serde_json::json!({
        "path": CANDIDATE_PATH,
        "sha256": CANDIDATE_SHA256
    });
    let mut g0139_wrong_candidate = g0139.clone();
    g0139_wrong_candidate["input_custody"]["fixed_inputs"][CANDIDATE_PATH] =
        Value::String("f".repeat(64));
    let mut g0139_missing_stage_d = g0139.clone();
    g0139_missing_stage_d["input_custody"]["fixed_inputs"]
        .as_object_mut()
        .context("G-0139 fixed-input fixture drift")?
        .remove(ANCESTOR_STAGE_D_RESULT_PATH);
    g0139_missing_stage_d["input_custody"]["fixed_inputs"]["fixture/replacement"] =
        Value::String("6".repeat(64));
    let mut g0139_wrong_subject = g0139.clone();
    g0139_wrong_subject["subject"]["sha256"] = Value::String("f".repeat(64));
    let mut g0139_wrong_subject_commit = g0139.clone();
    g0139_wrong_subject_commit["subject"]["git_commit"] = Value::String("f".repeat(40));
    let mut g0139_false_evidence = g0139.clone();
    g0139_false_evidence["evidence_class"] = Value::String("LOOKALIKE_T1".to_string());
    let mut g0139_false_lineage = g0139.clone();
    g0139_false_lineage["reviewer"]["same_model_lineage"] = Value::Bool(false);
    let mut g0139_false_source_audit = g0139.clone();
    g0139_false_source_audit["source_audit_anchor"]["sha256"] = Value::String("f".repeat(64));
    let mut g0139_false_rehash = g0139;
    g0139_false_rehash["input_custody"]["entry_exit_rehash_equal"] = Value::Bool(false);
    ensure!(
        [
            g0139_missing_candidate,
            g0139_wrong_candidate,
            g0139_missing_stage_d,
            g0139_wrong_subject,
            g0139_wrong_subject_commit,
            g0139_false_evidence,
            g0139_false_lineage,
            g0139_false_source_audit,
            g0139_false_rehash,
        ]
        .iter()
        .all(|mutant| validate_g0139_receipt_semantics(mutant).is_err()),
        "G-0139 subject/fixed-input hostile control escaped"
    );

    let stage_a_audit = stage_a_source_audit_fixture();
    let stage_b_audit = stage_b_source_audit_fixture();
    validate_source_audit_envelope(&stage_a_audit, STAGE_A_SOURCE_AUDIT_PATH)?;
    validate_source_audit_envelope(&stage_b_audit, STAGE_B_SOURCE_AUDIT_PATH)?;
    let mut audit_schema_mutant = stage_a_audit.clone();
    audit_schema_mutant["schema"] = Value::String("lookalike-audit-v1".to_string());
    let mut audit_result_mutant = stage_a_audit.clone();
    audit_result_mutant["result"] = Value::String("LOOKALIKE_PASS".to_string());
    let mut audit_unknown_mutant = stage_a_audit.clone();
    audit_unknown_mutant["unknown_extension"] = Value::Bool(true);
    let mut audit_self_reference_mutant = stage_a_audit.clone();
    audit_self_reference_mutant["audit_git_commit"] = Value::String("0".repeat(40));
    let mut audit_displaced_mutant = stage_a_audit.clone();
    let displaced_bindings = audit_displaced_mutant["subject"]
        .as_object_mut()
        .context("Stage-A source-audit subject fixture drift")?
        .remove("bindings")
        .context("Stage-A source-audit bindings fixture drift")?;
    audit_displaced_mutant["unrelated_receipt_lookalikes"] = displaced_bindings;
    let mut audit_decoy_mutant = stage_a_audit.clone();
    let main_source_decoy = audit_decoy_mutant["subject"]["bindings"]
        .as_object_mut()
        .context("Stage-A named source-audit binding fixture drift")?
        .remove("main_source")
        .context("Stage-A source-audit main-source fixture drift")?;
    audit_decoy_mutant["subject"]["unrelated_main_source_decoy"] = main_source_decoy;
    let mut audit_duplicate_path_mutant = stage_a_audit;
    audit_duplicate_path_mutant["subject"]["bindings"]["engine_source"]["path"] =
        Value::String(STAGE_A_SOURCE_PATH.to_string());

    let mut stage_b_displaced_mutant = stage_b_audit.clone();
    let displaced_bindings = stage_b_displaced_mutant["subject"]
        .as_object_mut()
        .context("Stage-B source-audit subject fixture drift")?
        .remove("bindings")
        .context("Stage-B source-audit bindings fixture drift")?;
    stage_b_displaced_mutant["unrelated_receipt_lookalikes"] = displaced_bindings;
    let mut stage_b_duplicate_path_mutant = stage_b_audit.clone();
    stage_b_duplicate_path_mutant["subject"]["bindings"]["cargo_manifest"]["path"] =
        Value::String(STAGE_B_SOURCE_PATH.to_string());
    let mut stage_b_unknown_mutant = stage_b_audit;
    stage_b_unknown_mutant["unknown_extension"] = Value::Bool(true);
    ensure!(
        [
            audit_schema_mutant,
            audit_result_mutant,
            audit_unknown_mutant,
            audit_self_reference_mutant,
            audit_displaced_mutant,
            audit_decoy_mutant,
            audit_duplicate_path_mutant,
        ]
        .iter()
        .all(|mutant| validate_source_audit_envelope(mutant, STAGE_A_SOURCE_AUDIT_PATH).is_err())
            && [
                stage_b_displaced_mutant,
                stage_b_duplicate_path_mutant,
                stage_b_unknown_mutant,
            ]
            .iter()
            .all(|mutant| validate_source_audit_envelope(
                mutant,
                STAGE_B_SOURCE_AUDIT_PATH
            )
            .is_err()),
        "exact named source-audit hostile control escaped"
    );

    let manifest_fixture = serde_json::json!({
        "schema": MANIFEST_SCHEMA,
        "selected_branch": "G0135_EXACT_RESIDUAL_POOL128",
        "preregistration_git_commit": "0".repeat(40),
        "producer_git_commit": "1".repeat(40),
        "source_audit_git_commit": "2".repeat(40),
        "bindings": {},
        "transitive_inputs": [],
        "parameters": {
            "n": N,
            "records": RECORDS,
            "existing_rows": ROWS,
            "existing_terms": TERMS,
            "accumulated_hinge_rows": CARRY_DIRECTIONS,
            "pool_k": K,
            "max_admitted_rows": 32,
            "threads": THREADS,
            "arithmetic": "signed_num_bigint_BigInt_and_exact_Q",
            "direction_order": "ordinary_signed_i8_tuple_lexicographic",
            "column_order": "canonical_sequence_0_through_163739"
        },
        "stage_order": [
            "A_REPLAY_POOL128",
            "B_PRICE_POOL128",
            "C_COMPLETE_MATRIX_RANK_SELECT",
            "D_REOPENED_EXACT_MASTER",
            "E_GLOBAL_REPLAY_IF_MEMBER"
        ],
        "planned_outputs": {
            "A": {"path": STAGE_A_RECEIPT_PATH, "schema": STAGE_A_SCHEMA},
            "B": {"path": OUTPUT_PATH, "schema": OUTPUT_SCHEMA},
            "C": {"path": STAGE_C_OUTPUT_PATH, "schema": STAGE_C_OUTPUT_SCHEMA},
            "D": {"path": STAGE_D_OUTPUT_PATH, "schema": STAGE_D_OUTPUT_SCHEMA},
            "E": {"path": STAGE_E_OUTPUT_PATH, "schema": STAGE_E_OUTPUT_SCHEMA}
        }
    });
    ensure!(
        serde_json::from_value::<StudyManifest>(manifest_fixture.clone()).is_ok(),
        "valid G-0140 manifest shape rejected"
    );
    let mut top_level_unknown = manifest_fixture.clone();
    top_level_unknown["extra"] = Value::Bool(true);
    let mut planned_output_unknown = manifest_fixture;
    planned_output_unknown["planned_outputs"]["B"]["extra"] = Value::Bool(true);
    ensure!(
        serde_json::from_value::<StudyManifest>(top_level_unknown).is_err()
            && serde_json::from_value::<StudyManifest>(planned_output_unknown).is_err(),
        "unknown manifest field accepted"
    );

    let transposed = transpose_record_major(vec![vec![1, 2, 3], vec![4, 5, 6]], 3)?;
    ensure!(
        transposed == vec![vec![1, 4], vec![2, 5], vec![3, 6]]
            && transpose_record_major(vec![vec![1], vec![2, 3]], 2).is_err(),
        "direction-major transpose/census drift"
    );
    let signed = [1i64, -2, 3];
    let reordered = [1i64, 3, -2];
    ensure!(
        digest_i64(signed.iter()) != digest_i64(reordered.iter()),
        "signed i64 order mutant escaped"
    );

    let record = Record {
        sequence: 0,
        signed_mass: 3,
        active_vertices: 6,
        negative_edges: vec![[0, 1], [1, 2], [3, 4]],
        positive_edges: vec![[0, 2], [2, 5], [4, 5]],
    };
    let form = full_normal_form(&record)?;
    ensure!(
        form.labelled_permutations == factorial(N) && form.hinges.len() > K,
        "known-answer normal form lacks Pool128 support"
    );
    let mut directions = form.hinges.keys().copied().collect::<Vec<_>>();
    directions.sort();
    directions.truncate(K + 1);
    let prices = hinge_coefficients(&record, &directions)?;
    ensure!(
        directions
            .iter()
            .zip(&prices)
            .all(|(direction, value)| form.hinges[direction] == *value),
        "hinge kernel/full-normal-form bridge drift"
    );
    let pool = directions[..K]
        .iter()
        .enumerate()
        .map(|(index, direction)| ExactHinge {
            direction: *direction,
            coefficient: (index + 1).to_string(),
        })
        .collect::<Vec<_>>();
    let direction_digest = selected_direction_digest(&pool);
    let residual_digest = decimal_lf_digest(pool.iter().map(|item| item.coefficient.as_str()));
    validate_pool(&pool, &direction_digest, &residual_digest, &[], false)?;

    let mut count_mutant = pool.clone();
    count_mutant.pop();
    let mut order_mutant = pool.clone();
    order_mutant.swap(0, 1);
    let mut duplicate_mutant = pool.clone();
    duplicate_mutant[1] = duplicate_mutant[0].clone();
    let mut direction_mutant = pool.clone();
    for coordinate in &mut direction_mutant[0].direction {
        *coordinate = -*coordinate;
    }
    let mut residual_mutant = pool.clone();
    residual_mutant[0].coefficient = "2".to_string();
    ensure!(
        validate_pool(
            &count_mutant,
            &direction_digest,
            &residual_digest,
            &[],
            false
        )
        .is_err()
            && validate_pool(
                &order_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false
            )
            .is_err()
            && validate_pool(
                &duplicate_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false,
            )
            .is_err()
            && validate_pool(
                &direction_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false,
            )
            .is_err()
            && validate_pool(
                &residual_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false,
            )
            .is_err(),
        "Pool128 order/direction/residual mutant escaped"
    );
    ensure!(
        validate_record_axis([0, 1, 2], 3).is_ok()
            && validate_record_axis([0, 1], 3).is_err()
            && validate_record_axis([1, 0, 2], 3).is_err(),
        "record census/order mutant escaped"
    );

    let huge = parse_bigint(EXPECTED_FIRST_COEFFICIENT)?;
    let row = [i64::MAX, i64::MIN + 1];
    let terms = [(0usize, huge.clone()), (1usize, -huge)];
    ensure!(
        exact_dot(&row, &terms).to_string().len() > 170,
        "arbitrary-precision dot narrowed"
    );

    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0140-stage-b-publish-self-test-{}-{unique}",
        std::process::id()
    ));
    std::fs::create_dir(&temporary_directory)?;
    let publication = temporary_directory.join("receipt.json");
    publish_exclusive(&publication, b"complete\n")?;
    ensure!(
        std::fs::read(&publication)? == b"complete\n"
            && publish_exclusive(&publication, b"mutant\n").is_err(),
        "atomic no-overwrite publication control failed"
    );
    std::fs::remove_file(&publication)?;
    std::fs::remove_dir(&temporary_directory)?;
    Ok(())
}

fn static_preflight(input_path: PathBuf, candidate_path: PathBuf) -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let (input, candidate) = load_static_inputs(&root, &input_path, &candidate_path)?;
    ensure!(
        input.records.len() == RECORDS && candidate.terms.len() == TERMS,
        "static preflight census drift"
    );
    println!(
        "G-0140 Stage-B static preflight PASS: {} records; {} candidate terms; future manifest/Stage-A/G-0142 receipts not consumed",
        input.records.len(),
        candidate.terms.len()
    );
    Ok(())
}

fn preflight(
    input_path: PathBuf,
    receipt_path: PathBuf,
    candidate_path: PathBuf,
    manifest_path: PathBuf,
) -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let inputs = load_and_validate_inputs(
        &root,
        &input_path,
        &receipt_path,
        &candidate_path,
        &manifest_path,
    )?;
    let controls = make_input_mutation_controls(&inputs.panel.records, &inputs.receipt)?;
    ensure!(controls.all_rejected, "preflight mutation-control drift");
    println!(
        "G-0140 Stage-B preflight PASS: {} records; {} Pool128 directions; all manifest/G-0139/source bindings verified",
        inputs.panel.records.len(),
        inputs.receipt.pool.len()
    );
    Ok(())
}

fn run(
    input_path: PathBuf,
    receipt_path: PathBuf,
    candidate_path: PathBuf,
    manifest_path: PathBuf,
    output_path: PathBuf,
) -> Result<()> {
    ensure!(output_path == Path::new(OUTPUT_PATH), "output path drift");
    ensure!(!output_path.exists(), "refusing to overwrite output");
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(THREADS)
        .build_global()
        .context("build fixed Stage-B thread pool")?;
    let started = Instant::now();
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let inputs = load_and_validate_inputs(
        &root,
        &input_path,
        &receipt_path,
        &candidate_path,
        &manifest_path,
    )?;
    let input_mutation_controls =
        make_input_mutation_controls(&inputs.panel.records, &inputs.receipt)?;
    let directions = inputs
        .receipt
        .pool
        .iter()
        .map(|item| item.direction)
        .collect::<Vec<_>>();
    ensure!(directions.len() == K, "pricing Pool128 census drift");

    let record_major = inputs
        .panel
        .records
        .par_iter()
        .map(|record| hinge_coefficients(record, &directions))
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        record_major.len() == RECORDS,
        "computed record census drift"
    );
    let direction_major = transpose_record_major(record_major, K)?;
    ensure!(
        direction_major.len() == K
            && direction_major.iter().all(|row| row.len() == RECORDS)
            && direction_major.iter().map(Vec::len).sum::<usize>() == HINGE_ENTRIES,
        "exact Pool128 coordinate dimensions drift"
    );
    let complete_hinge_digest = digest_i64(direction_major.iter().flat_map(|row| row.iter()));

    let exact_terms = inputs
        .candidate
        .terms
        .iter()
        .map(|term| Ok((term.sequence, parse_bigint(&term.coefficient)?)))
        .collect::<Result<Vec<_>>>()?;
    let exact_dots = direction_major
        .iter()
        .map(|row| exact_dot(row, &exact_terms))
        .collect::<Vec<_>>();
    ensure!(exact_dots.len() == K, "exact candidate-dot census drift");
    let exact_dot_strings = exact_dots
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    for (index, (dot, selected)) in exact_dot_strings
        .iter()
        .zip(&inputs.receipt.pool)
        .enumerate()
    {
        ensure!(
            canonical_integer(dot) && dot != "0" && dot == &selected.coefficient,
            "exact candidate dot disagrees with Stage-A residual at Pool128 row {index}"
        );
    }
    let exact_dot_digest = decimal_lf_digest(exact_dot_strings.iter().map(String::as_str));
    ensure!(
        exact_dot_digest == inputs.receipt.pool_exact_residuals_decimal_lf_sha256,
        "exact candidate-dot decimal-LF digest drift"
    );

    let mutant_term = inputs
        .candidate
        .terms
        .iter()
        .find(|term| direction_major.iter().any(|row| row[term.sequence] != 0))
        .context("no candidate coefficient can exercise a Pool128 row")?;
    let mutant_dots = exact_dots
        .iter()
        .zip(&direction_major)
        .map(|(dot, row)| dot + BigInt::from(row[mutant_term.sequence]))
        .collect::<Vec<_>>();
    let mutant_dot_digest = bigint_decimal_lf_digest(&mutant_dots);
    let changed_rows = exact_dots
        .iter()
        .zip(&mutant_dots)
        .filter(|(original, mutant)| original != mutant)
        .count();
    ensure!(
        changed_rows > 0 && mutant_dot_digest != exact_dot_digest,
        "candidate coefficient-plus-one mutant survived"
    );
    let coefficient_plus_one_mutant = CoefficientPlusOneMutant {
        sequence: mutant_term.sequence,
        coefficient_delta: "+1",
        baseline_exact_dots_decimal_lf_sha256: exact_dot_digest.clone(),
        mutated_exact_dots_decimal_lf_sha256: mutant_dot_digest,
        changed_rows,
        rejected: true,
    };

    let rows = inputs
        .receipt
        .pool
        .iter()
        .zip(direction_major)
        .zip(exact_dot_strings.iter())
        .enumerate()
        .map(|(index, ((selected, coefficients), exact_dot))| {
            let minimum = coefficients.iter().copied().min().unwrap_or(0);
            let maximum = coefficients.iter().copied().max().unwrap_or(0);
            let maximum_absolute = coefficients
                .iter()
                .map(|value| value.unsigned_abs())
                .max()
                .unwrap_or(0);
            PriceRow {
                index,
                direction: selected.direction,
                exact_stage_a_residual: selected.coefficient.clone(),
                exact_candidate_dot: exact_dot.clone(),
                records: coefficients.len(),
                nonzero_hinge_coefficients: coefficients
                    .iter()
                    .filter(|value| **value != 0)
                    .count(),
                minimum_hinge_coefficient: minimum,
                maximum_hinge_coefficient: maximum,
                maximum_absolute_hinge_coefficient: maximum_absolute,
                hinge_coefficients_i64_le_sha256: digest_i64(coefficients.iter()),
                hinge_coefficients: coefficients,
            }
        })
        .collect::<Vec<_>>();
    ensure!(
        rows.len() == K
            && rows.iter().enumerate().all(|(index, row)| {
                row.index == index
                    && row.records == RECORDS
                    && row.direction == directions[index]
                    && row.exact_candidate_dot == row.exact_stage_a_residual
            }),
        "output row census/order/dot drift"
    );

    let stage_a_sha_end = sha256_path(&checked_repo_path(&root, STAGE_A_RECEIPT_PATH)?)?;
    let custody_end = custody_snapshot(&root, &inputs.manifest, &stage_a_sha_end)?;
    ensure!(
        inputs.custody == custody_end,
        "input/source custody drift during Pool128 pricing"
    );
    let source_and_input_bindings = custody_end
        .iter()
        .map(|(path, sha256)| {
            (
                path.clone(),
                Binding {
                    path: path.clone(),
                    sha256: sha256.clone(),
                },
            )
        })
        .collect::<BTreeMap<_, _>>();
    let output = Output {
        schema: OUTPUT_SCHEMA,
        result: OUTPUT_RESULT,
        claim_boundary: OUTPUT_CLAIM,
        manifest_path: MANIFEST_PATH,
        manifest_sha256: inputs.manifest.sha256.clone(),
        source_and_input_bindings,
        stage_a_receipt: make_binding(&root, STAGE_A_RECEIPT_PATH)?,
        candidate: make_expected_binding(&root, CANDIDATE_PATH, CANDIDATE_SHA256)?,
        g0139_result_audit: make_binding(&root, G0139_AUDIT_PATH)?,
        pool_k: K,
        records: RECORDS,
        hinge_entries: HINGE_ENTRIES,
        pool_count: K,
        pool_directions_i8_sha256: inputs.receipt.pool_directions_i8_sha256.clone(),
        pool_exact_residuals_decimal_lf_sha256: inputs
            .receipt
            .pool_exact_residuals_decimal_lf_sha256
            .clone(),
        directions,
        direction_major_hinge_i64_le_sha256: complete_hinge_digest,
        exact_candidate_dots_decimal_lf_sha256: exact_dot_digest,
        exact_candidate_dots: exact_dot_strings,
        rows,
        input_mutation_controls,
        coefficient_plus_one_mutant,
        inputs_rehashed_at_end: true,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let stdout = serde_json::json!({
        "schema": output.schema,
        "result": output.result,
        "records": output.records,
        "pool_count": output.pool_count,
        "hinge_entries": output.hinge_entries,
        "direction_major_hinge_i64_le_sha256": output.direction_major_hinge_i64_le_sha256,
        "exact_candidate_dots_decimal_lf_sha256": output.exact_candidate_dots_decimal_lf_sha256,
        "wall_seconds": output.wall_seconds,
    });
    let mut serialized = serde_json::to_vec(&output)?;
    serialized.push(b'\n');
    publish_exclusive(&output_path, &serialized)?;
    println!("{stdout}");
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() == 2 && args[1] == "--self-test" {
        self_test()?;
        println!("G-0140 Stage-B Pool128 self-test PASS");
        return Ok(());
    }
    if args.len() == 4 && args[1] == "--preflight-static" {
        return static_preflight(PathBuf::from(&args[2]), PathBuf::from(&args[3]));
    }
    if args.len() == 6 && args[1] == "--preflight" {
        return preflight(
            PathBuf::from(&args[2]),
            PathBuf::from(&args[3]),
            PathBuf::from(&args[4]),
            PathBuf::from(&args[5]),
        );
    }
    ensure!(
        args.len() == 6,
        "usage: g0140-stage-b-pool128-coordinate-pricer --self-test | --preflight-static PANEL CANDIDATE | --preflight PANEL STAGE_A_RECEIPT CANDIDATE MANIFEST | PANEL STAGE_A_RECEIPT CANDIDATE MANIFEST OUTPUT"
    );
    run(
        PathBuf::from(&args[1]),
        PathBuf::from(&args[2]),
        PathBuf::from(&args[3]),
        PathBuf::from(&args[4]),
        PathBuf::from(&args[5]),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn producer_self_test_passes() {
        self_test().unwrap();
    }

    #[test]
    fn exact_coordinate_census_is_frozen() {
        assert_eq!(HINGE_ENTRIES, 20_958_720);
        assert_eq!(HINGE_ENTRIES, K.checked_mul(RECORDS).unwrap());
    }

    #[test]
    fn arbitrary_precision_dot_does_not_narrow() {
        let huge = parse_bigint(EXPECTED_FIRST_COEFFICIENT).unwrap();
        let row = [i64::MAX, i64::MIN + 1];
        let terms = [(0usize, huge.clone()), (1usize, -huge)];
        let dot = exact_dot(&row, &terms);
        assert!(dot.to_string().len() > 170);
    }
}
