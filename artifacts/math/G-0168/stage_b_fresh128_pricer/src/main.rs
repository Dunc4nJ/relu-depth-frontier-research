#![recursion_limit = "512"]

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
const TERMS: usize = 304;
const OLD_ROWS: usize = 540;
const NEW_ROWS: usize = 1;
const ROWS: usize = OLD_ROWS + NEW_ROWS;
const OLD_RANK: usize = 349;
const NEW_RANK: usize = 350;
const THREADS: usize = 12;
const HINGE_ENTRIES: usize = K * RECORDS;

const PANEL_INPUT_PATH: &str = "artifacts/math/G-0113/panel_solver_input_v1.json";
const MEMBER_PATH: &str = "artifacts/math/G-0164/all128_direct_basis_member_v1.json";
const GLOBAL_RESULT_PATH: &str = "artifacts/math/G-0164/all128_global_replay_v1.json";
const PREREGISTRATION_PATH: &str = "artifacts/math/G-0168/PREREGISTRATION.md";
const KERNEL_PATH: &str = "artifacts/math/G-0117/src/lib.rs";
const STAGE_A_PRODUCER_PATH: &str = "artifacts/math/G-0168/first_row_exact_admission.py";
const STAGE_A_MANIFEST_PATH: &str = "artifacts/math/G-0168/first_row_admission_manifest_v1.json";
const STAGE_A_RESULT_PATH: &str = "artifacts/math/G-0168/first_row_exact_admission_v1.json";
const STAGE_A_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0171-g0168-first-row-source/SOURCE_AUDIT_RECEIPT.json";
const G0170_PREREGISTRATION_PATH: &str = "artifacts/math/G-0170/PREREGISTRATION.md";
const G0170_QUERY_PATH: &str = "artifacts/math/G-0170/first_fresh_direction_query_v1.json";
const G0170_COORDINATE_PATH: &str =
    "artifacts/math/G-0170/first_fresh_direction_coordinate_v1.json";
const G0170_BRIDGE_PATH: &str = "artifacts/math/G-0170/first_fresh_direction_bridge_v1.json";
const MANIFEST_PATH: &str = "artifacts/math/G-0168/fresh128_manifest_v1.json";
const OUTPUT_PATH: &str = "artifacts/math/G-0168/fresh128_coordinate_prices_v1.json";
const SOURCE_PATH: &str = "artifacts/math/G-0168/stage_b_fresh128_pricer/src/main.rs";
const CARGO_PATH: &str = "artifacts/math/G-0168/stage_b_fresh128_pricer/Cargo.toml";
const LOCK_PATH: &str = "artifacts/math/G-0168/stage_b_fresh128_pricer/Cargo.lock";
const EXECUTABLE_PATH: &str = "artifacts/math/G-0168/stage_b_fresh128_pricer/target/release/g0168-stage-b-fresh128-coordinate-pricer";
const SOURCE_AUDIT_PREREGISTRATION_PATH: &str =
    "artifacts/reviews/G-0173-g0168-fresh128-pricer-source/PREREGISTRATION.md";
const SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0173-g0168-fresh128-pricer-source/SOURCE_AUDIT_RECEIPT.json";

const PANEL_INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const MEMBER_SHA256: &str = "bc4d1c58587aef6cd3b555b166ba7ec8e0f365cb0089cfd889a235e8f2e20119";
const GLOBAL_RESULT_SHA256: &str =
    "c04e39834de079b7ea89884cedc23956aaaf585c6ac2f3d79241395c943dba6a";
const PREREGISTRATION_SHA256: &str =
    "335b82ad402ca0ccc9ca6b0124fd4f1cc133bb2d6854912a326f4e142d11b11b";
const KERNEL_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";
const MEMBER_SELECTED_DIRECTIONS_SHA256: &str =
    "2cb4c036ee887d9fd285eba3794a80205e6d47f9a9cd48c8ed0618417d88d0e3";
const BASIS_SEQUENCES_SHA256: &str =
    "c9ec5dbb017e2f735a115ca2eb757adf4d93f072a287f08286c2776b29ec08b3";
const BASIS_MATRIX_SHA256: &str =
    "7451a36e42c479819b6f9ae28ec8c2f7b23360ddc5203b17cf9e3417d1ac9d10";
const SQUARE_MATRIX_SHA256: &str =
    "f06bf820562a96575274bd8358b7ca0eef695e3e991034072deecf97823d3606";
const TARGET_SHA256: &str = "a30ec0a4ff135350f217363831c6ffd2ee0a44f74b4d14549aa3b88da3967874";
const INTEGER_COEFFICIENTS_SHA256: &str =
    "7669849235c573ba39b20219e77b5378fcba57c600328f02eb3704543691759f";
const RESIDUAL_DIRECTIONS_SHA256: &str =
    "401f959ef40eeb099a39f4758dcdb8ac0d681bdae6dec4591a6b78b6eb46003d";
const RESIDUAL_COEFFICIENTS_SHA256: &str =
    "b5f51eddada538ba8a8d224abcd97dca04f9c042c08d1548fac43a6826784ce5";
const FIRST_ROW_I64_SHA256: &str =
    "f4285a36af1c3985576c2471352c36d972e8c69ed32f372b6bd83da4dec89ddc";

const MEMBER_SCHEMA: &str = "max11-g0164-all128-direct-basis-member-v1";
const MEMBER_RESULT: &str = "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER";
const GLOBAL_SCHEMA: &str = "max11-g0164-all128-global-replay-v1";
const GLOBAL_RESULT: &str = "EXACT_RESIDUAL_CONTINUE";
const STAGE_A_MANIFEST_SCHEMA: &str = "max11-g0168-first-row-admission-manifest-v1";
const STAGE_A_SCHEMA: &str = "max11-g0168-first-row-exact-admission-v1";
const STAGE_A_RANK_RESULT: &str = "FIRST_ROW_EXACT_RANK_GROWTH";
const STAGE_A_DEPENDENCY_RESULT: &str = "FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY";
const MANIFEST_SCHEMA: &str = "max11-g0168-fresh128-pricing-manifest-v1";
const MANIFEST_RESULT: &str = "FROZEN_BEFORE_G0168_FRESH128_PRICING";
const OUTPUT_SCHEMA: &str = "max11-g0168-fresh128-coordinate-prices-v1";
const OUTPUT_RESULT: &str = "EXACT_FULL_FAMILY_FRESH128_COORDINATES";
const SOURCE_AUDIT_SCHEMA: &str = "max11-g0173-g0168-fresh128-pricer-source-audit-v1";
const SOURCE_AUDIT_RESULT: &str = "SOURCE_CUSTODY_AUDIT_PASS_T1";
const SOURCE_AUDIT_EVIDENCE: &str = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT";

const CLAIM_BOUNDARY: &str = "Exact signed-i64 prices for the frozen 128 G-0164 residual-prefix directions over the frozen 163,740-column family, with arbitrary-precision 304-term G-0164 member dot bridges, admitted only after the committed G-0168 first row returns FIRST_ROW_EXACT_RANK_GROWTH. This coordinate matrix is correction input only; it is not a corrected member, separator, global identity, family-completeness theorem, lower bound, minimality result, all-n theorem, refereed result, formalization, or Lean theorem.";
const SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen G-0168 Fresh128 batch-pricer source, Cargo, lock, G-0117 kernel, and release-executable bytes only; no G-0168 Fresh128 scientific manifest, Stage-A outcome, pricing output, or correction result was observed or produced.";
const SOURCE_AUDIT_NO_CLAIM: &str = "This source audit does not price the Fresh128 matrix, decide the correction system, establish a corrected member or separator, validate family completeness, prove a global MAX11 identity or lower bound, establish minimality, prove an all-n statement, or supply a Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_CARGO: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../../PREREGISTRATION.md");
const COMPILED_MEMBER: &[u8] = include_bytes!("../../../G-0164/all128_direct_basis_member_v1.json");
const COMPILED_GLOBAL_RESULT: &[u8] =
    include_bytes!("../../../G-0164/all128_global_replay_v1.json");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../../G-0117/src/lib.rs");

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Binding {
    path: String,
    sha256: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct CommitBinding {
    path: String,
    sha256: String,
    git_commit: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Term {
    sequence: usize,
    coefficient: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct DirectBasisMutantReceipt {
    basis_index: usize,
    sequence: usize,
    first_nonzero_row: usize,
    first_nonzero_residual: String,
    nonzero_rows: usize,
    residuals_decimal_lf_sha256: String,
    rejected: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct DirectBasisMember {
    schema: String,
    result: String,
    claim_boundary: String,
    manifest: Binding,
    solver: Binding,
    source_audit: Binding,
    stage_a_receipt: Binding,
    stage_b_receipt: Binding,
    stage_c_receipt: Binding,
    n: usize,
    records: usize,
    base_rows: usize,
    appended_rows: usize,
    rows: usize,
    selected_pool_indices: Vec<usize>,
    selected_directions: Vec<[i8; N]>,
    selected_directions_i8_sha256: String,
    target: Vec<String>,
    target_i128le_sha256: String,
    target_construction: String,
    rank: usize,
    augmented_rank: usize,
    basis_sequences: Vec<usize>,
    basis_sequences_u64le_sha256: String,
    coordinate_rows: Vec<usize>,
    basis_i128le_sha256: String,
    square_i128le_sha256: String,
    rational_coefficients: Vec<String>,
    rational_coefficients_decimal_lf_sha256: String,
    integer_coefficients: Vec<String>,
    integer_coefficients_decimal_lf_sha256: String,
    target_scale: String,
    support_columns: usize,
    terms: Vec<Term>,
    all_540_rational_rows_replayed: bool,
    rational_residuals_decimal_lf_sha256: String,
    all_540_primitive_integer_rows_replayed: bool,
    integer_residuals_decimal_lf_sha256: String,
    primitive_denominator_clearing: bool,
    coefficient_plus_one_mutant: DirectBasisMutantReceipt,
    prior_target_scale: String,
    prior_target_scale_not_used_as_input: bool,
    complete_basis_reused: bool,
    pricing_recomputed: bool,
    rank_discovery_recomputed: bool,
    complete_family_scan_recomputed: bool,
    column_generation_executed: bool,
    alternative_basis_or_nullspace_search_executed: bool,
    input_snapshot_sha256: String,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
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

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct PrefixControls {
    maximum_k: usize,
    expected_count: usize,
    observed_count: usize,
    strict_signed_lexicographic_order: bool,
    excludes_accumulated_directions: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct FrozenGlobalResult {
    schema: String,
    result: String,
    claim_boundary: String,
    global_manifest: Binding,
    finite_manifest: Binding,
    finite_member: Binding,
    preregistration: Binding,
    producer_source: Binding,
    candidate_source: Binding,
    producer_engine: Binding,
    producer_cargo_manifest: Binding,
    producer_cargo_lock: Binding,
    g0117_cargo_manifest: Binding,
    g0117_lib_source: Binding,
    producer_executable: Binding,
    source_audit: Binding,
    parent_replay_source: Binding,
    parent_replay_engine: Binding,
    parent_source_audit: Binding,
    source_and_audit_bindings: BTreeMap<String, Binding>,
    candidate_schema: String,
    candidate_result: String,
    base_rows: usize,
    appended_rows: usize,
    rows: usize,
    records: usize,
    selected_pool_indices: Vec<usize>,
    selected_directions: Vec<[i8; N]>,
    selected_directions_i8_sha256: String,
    rank: usize,
    basis_coordinates: usize,
    support_columns: usize,
    terms: usize,
    target_scale: String,
    target_subtraction_coordinate_10: String,
    finite_all_rational_rows_replayed: bool,
    finite_all_integer_rows_replayed: bool,
    finite_primitive_denominator_clearing: bool,
    finite_coefficient_plus_one_mutant_rejected: bool,
    independent_finite_replay: Value,
    arithmetic: String,
    decision_rule: String,
    complete_global_replay: bool,
    all_hinge_and_linear_residuals_zero: bool,
    labelled_permutations_expected: u64,
    labelled_permutations_checked: u64,
    hinge_entries_processed: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_directions: usize,
    aggregate_hinge_decimal_lf_sha256: String,
    nonzero_hinge_decimal_lf_sha256: String,
    complete_residual_decimal_lf_sha256: String,
    term_normal_form_transcript_sha256: String,
    term_normal_forms: Vec<Value>,
    accumulated_direction_checks: Vec<AccumulatedDirectionCheck>,
    inherited_accumulated_directions: usize,
    selected_accumulated_directions: usize,
    accumulated_direction_count: usize,
    all_accumulated_directions_exact_zero: bool,
    linear_residuals_after_target: Vec<String>,
    all_11_linear_residuals_exact_zero: bool,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<Value>,
    residual_prefix_k: usize,
    residual_prefix_count: usize,
    residual_prefix_directions_i8_sha256: String,
    residual_prefix_exact_residuals_decimal_lf_sha256: String,
    residual_prefix: Vec<ExactHinge>,
    no_automatic_next_study: bool,
    coefficient_plus_one: Value,
    target_scale_plus_one: Value,
    target_coordinate_plus_one: Value,
    omitted_final_term: Value,
    omitted_first_term_direction: Value,
    census_controls: Value,
    prefix_controls: PrefixControls,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    candidate_rehashed_at_end: bool,
    wall_seconds: f64,
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

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageARelation {
    old_coordinate_rows: Vec<usize>,
    integer_coefficients: Vec<String>,
    hinge_scale: String,
    basis_relation_exactly_replayed: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct CanonicalNullVector {
    basis_sequences: Vec<usize>,
    basis_integer_coefficients: Vec<String>,
    witness_sequence: usize,
    witness_integer_coefficient: String,
    support: usize,
    all_540_old_rows_exact_zero: bool,
    old_residuals_decimal_lf_sha256: String,
    new_row_pairing: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactMinor {
    rows: usize,
    columns: usize,
    coordinate_rows: Vec<usize>,
    column_sequences: Vec<usize>,
    matrix_i128le_sha256: String,
    determinant: String,
    determinant_decimal_sha256: String,
    square_determinant: String,
    schur_formula_verified: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct CorrectedMemberMutant {
    coefficient_index: usize,
    sequence: usize,
    is_witness_column: bool,
    old_nonzero_rows: usize,
    new_row_residual: String,
    rejected: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct CorrectedMember {
    target_scale: String,
    basis_sequences: Vec<usize>,
    integer_coefficients: Vec<String>,
    integer_coefficients_decimal_lf_sha256: String,
    support_columns: usize,
    terms: Vec<Term>,
    all_540_old_rows_exactly_replayed: bool,
    old_residuals_decimal_lf_sha256: String,
    appended_zero_target_exactly_replayed: bool,
    appended_residual: String,
    coefficient_plus_one_mutant: CorrectedMemberMutant,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct RankGrowthBranch {
    witness_sequence: usize,
    delta_numerator: String,
    delta_denominator: String,
    old_rank: usize,
    new_rank: usize,
    canonical_null_vector: CanonicalNullVector,
    exact_350_minor: ExactMinor,
    corrected_member: CorrectedMember,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageAManifestParameters {
    n: usize,
    records: usize,
    old_rows: usize,
    appended_rows: usize,
    rows: usize,
    old_rank: usize,
    basis_sequences_u64le_sha256: String,
    basis_i128le_sha256: String,
    square_i128le_sha256: String,
    target_i128le_sha256: String,
    first_row_i64le_sha256: String,
    column_order: String,
    arithmetic: String,
    fixed_modular_primes_diagnostic_only: Vec<u64>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageAPlannedOutput {
    path: String,
    schema: String,
    allowed_results: Vec<String>,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageAManifest {
    schema: String,
    result: String,
    claim_boundary: String,
    preregistration: CommitBinding,
    producer: CommitBinding,
    source_audit: CommitBinding,
    g0164_member: CommitBinding,
    g0164_global_result: CommitBinding,
    g0170_preregistration: CommitBinding,
    g0170_query: CommitBinding,
    g0170_coordinate: CommitBinding,
    g0170_bridge: CommitBinding,
    parameters: StageAManifestParameters,
    input_snapshot: BTreeMap<String, String>,
    input_snapshot_sha256: String,
    planned_output: StageAPlannedOutput,
    scientific_run_executed: bool,
    scientific_output_created: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageAResult {
    schema: String,
    result: String,
    claim_boundary: String,
    manifest: CommitBinding,
    preregistration: CommitBinding,
    producer: CommitBinding,
    source_audit: CommitBinding,
    g0164_member: CommitBinding,
    g0164_global_result: CommitBinding,
    g0170_coordinate: CommitBinding,
    g0170_bridge: CommitBinding,
    source_and_input_bindings: BTreeMap<String, Binding>,
    n: usize,
    records: usize,
    old_rows: usize,
    appended_rows: usize,
    rows: usize,
    old_rank: usize,
    direction: [i8; N],
    frozen_primitive_member_residual: String,
    frozen_member_target_scale: String,
    exact_dot_bridge_replayed: bool,
    basis_sequences: Vec<usize>,
    basis_sequences_u64le_sha256: String,
    coordinate_rows: Vec<usize>,
    basis_i128le_sha256: String,
    square_i128le_sha256: String,
    relation: StageARelation,
    canonical_columns_scanned: usize,
    first_modular_nonzero_diagnostics: BTreeMap<String, Option<usize>>,
    modular_role: String,
    branch: RankGrowthBranch,
    input_snapshot_sha256: String,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    no_automatic_fresh128_run: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ProducerBindings {
    git_commit: String,
    main_source: Binding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    g0117_lib_source: Binding,
    release_executable: Binding,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ManifestParameters {
    n: usize,
    records: usize,
    directions: usize,
    member_terms: usize,
    hinge_entries: usize,
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
    result: String,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StudyManifest {
    schema: String,
    result: String,
    claim_boundary: String,
    preregistration: CommitBinding,
    producer: ProducerBindings,
    source_audit_preregistration: CommitBinding,
    source_audit: CommitBinding,
    stage_a_manifest: CommitBinding,
    stage_a_result: CommitBinding,
    g0164_member: CommitBinding,
    g0164_global_result: CommitBinding,
    panel_input: CommitBinding,
    g0117_lib_source: CommitBinding,
    transitive_inputs: Vec<Binding>,
    parameters: ManifestParameters,
    planned_output: PlannedOutput,
    scientific_pricing_executed: bool,
    scientific_output_created: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditReviewer {
    agent_name: String,
    program: String,
    model: String,
    same_model_lineage: bool,
    fresh_context: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditSubject {
    git_commit: String,
    commit_object_and_working_bytes_equal_for_all_bindings: bool,
    bindings: ProducerBindings,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditChecks {
    exact_named_binding_contract: bool,
    duplicate_json_keys_rejected: bool,
    trailing_json_data_rejected: bool,
    strict_input_and_future_manifest_schemas_verified: bool,
    hostile_direction_order_count_and_residual_mutants_rejected: bool,
    hostile_member_term_mutants_rejected: bool,
    dependency_branch_rejected: bool,
    stage_a_rank_growth_contract_verified: bool,
    compiled_source_cargo_lock_kernel_match_working_bytes: bool,
    fixed_12_thread_record_parallel_batch_kernel_verified: bool,
    arbitrary_precision_304_term_dots_verified: bool,
    atomic_exclusive_output_verified: bool,
    end_rehash_verified: bool,
    producer_self_test_passed: bool,
    producer_static_preflight_passed: bool,
    prohibited_scientific_modes_not_run: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: SourceAuditReviewer,
    audit_preregistration: CommitBinding,
    subject: SourceAuditSubject,
    required_checks: SourceAuditChecks,
    scientific_manifest_observed: bool,
    scientific_input_observed: bool,
    scientific_output_observed: bool,
    scientific_run_executed: bool,
    no_claim: String,
}

#[derive(Serialize)]
struct PriceRow {
    index: usize,
    direction: [i8; N],
    frozen_residual: String,
    exact_member_dot: String,
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
    direction_count_mutant_rejected: bool,
    direction_order_mutant_rejected: bool,
    direction_duplicate_mutant_rejected: bool,
    direction_invalidity_mutant_rejected: bool,
    residual_plus_one_mutant_rejected: bool,
    member_term_count_mutant_rejected: bool,
    member_term_order_mutant_rejected: bool,
    member_term_coefficient_mutant_rejected: bool,
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
    manifest: CommitBinding,
    stage_a_result: CommitBinding,
    g0164_member: Binding,
    g0164_global_result: Binding,
    source_and_input_bindings: BTreeMap<String, Binding>,
    n: usize,
    records: usize,
    terms: usize,
    directions: usize,
    hinge_entries: usize,
    threads: usize,
    arithmetic: &'static str,
    residual_prefix_directions_i8_sha256: String,
    residual_prefix_exact_residuals_decimal_lf_sha256: String,
    ordered_directions: Vec<[i8; N]>,
    direction_major_hinge_i64_le_sha256: String,
    exact_member_dots_decimal_lf_sha256: String,
    exact_member_dots: Vec<String>,
    rows: Vec<PriceRow>,
    input_mutation_controls: InputMutationControls,
    coefficient_plus_one_mutant: CoefficientPlusOneMutant,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    stage_a_result_rehashed_at_end: bool,
    wall_seconds: f64,
}

struct StaticInputs {
    panel: PanelInput,
    member: DirectBasisMember,
    global: FrozenGlobalResult,
}

struct ManifestSnapshot {
    manifest: StudyManifest,
    binding: CommitBinding,
    bindings_by_path: BTreeMap<String, String>,
}

struct ValidatedInputs {
    static_inputs: StaticInputs,
    stage_a: StageAResult,
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

fn canonical_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

fn canonical_commit(value: &str) -> bool {
    value.len() == 40
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
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

fn digest_i64<'a>(values: impl Iterator<Item = &'a i64>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn direction_digest<'a>(directions: impl Iterator<Item = &'a [i8; N]>) -> String {
    let mut digest = Sha256::new();
    for direction in directions {
        for coordinate in direction {
            digest.update(coordinate.to_le_bytes());
        }
    }
    format!("{:x}", digest.finalize())
}

fn u64le_digest<'a>(values: impl Iterator<Item = &'a usize>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((*value as u64).to_le_bytes());
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

fn input_snapshot_digest(values: &BTreeMap<String, String>) -> String {
    let mut digest = Sha256::new();
    for (path, sha256) in values {
        digest.update(path.as_bytes());
        digest.update(b"\t");
        digest.update(sha256.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
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
        !raw.is_empty()
            && relative.is_relative()
            && relative
                .components()
                .all(|component| matches!(component, Component::Normal(_))),
        "path is not a contained repository-relative path: {raw}"
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

fn binding_for_path(root: &Path, raw: &str) -> Result<Binding> {
    Ok(Binding {
        path: raw.to_string(),
        sha256: sha256_path(&checked_repo_path(root, raw)?)?,
    })
}

fn expected_binding(root: &Path, raw: &str, expected: &str) -> Result<Binding> {
    let binding = binding_for_path(root, raw)?;
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
    ensure!(canonical_commit(&commit), "untracked Git binding: {raw}");
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

fn commit_binding_for_path(root: &Path, raw: &str) -> Result<CommitBinding> {
    let binding = binding_for_path(root, raw)?;
    Ok(CommitBinding {
        path: binding.path,
        sha256: binding.sha256,
        git_commit: git_commit_for_path(root, raw)?,
    })
}

fn validate_binding(root: &Path, binding: &Binding, expected_path: &str) -> Result<()> {
    ensure!(
        binding.path == expected_path
            && canonical_sha256(&binding.sha256)
            && sha256_path(&checked_repo_path(root, expected_path)?)? == binding.sha256,
        "binding contract drift: {expected_path}"
    );
    Ok(())
}

fn validate_commit_binding(
    root: &Path,
    binding: &CommitBinding,
    expected_path: &str,
) -> Result<()> {
    validate_binding(
        root,
        &Binding {
            path: binding.path.clone(),
            sha256: binding.sha256.clone(),
        },
        expected_path,
    )?;
    ensure!(
        canonical_commit(&binding.git_commit)
            && git_commit_for_path(root, expected_path)? == binding.git_commit,
        "committed binding drift: {expected_path}"
    );
    Ok(())
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

fn validate_member(member: &DirectBasisMember) -> Result<()> {
    ensure!(
        member.schema == MEMBER_SCHEMA
            && member.result == MEMBER_RESULT
            && !member.claim_boundary.is_empty()
            && member.n == N
            && member.records == RECORDS
            && member.base_rows == 412
            && member.appended_rows == 128
            && member.rows == OLD_ROWS
            && member.rank == OLD_RANK
            && member.augmented_rank == OLD_RANK
            && member.support_columns == TERMS
            && member.all_540_rational_rows_replayed
            && member.all_540_primitive_integer_rows_replayed
            && member.primitive_denominator_clearing
            && member.complete_basis_reused
            && !member.pricing_recomputed
            && !member.rank_discovery_recomputed
            && !member.complete_family_scan_recomputed
            && !member.column_generation_executed
            && !member.alternative_basis_or_nullspace_search_executed
            && member.prior_target_scale_not_used_as_input
            && member.inputs_rehashed_at_end
            && member.wall_seconds > 0.0
            && member.maximum_rss_kib > 0,
        "G-0164 member identity/replay drift"
    );
    validate_strict_axis(
        &member.basis_sequences,
        OLD_RANK,
        RECORDS,
        "member basis sequence axis",
    )?;
    validate_strict_axis(
        &member.coordinate_rows,
        OLD_RANK,
        OLD_ROWS,
        "member coordinate-row axis",
    )?;
    ensure!(
        member.selected_pool_indices == (0..K).collect::<Vec<_>>()
            && member.selected_directions.len() == K
            && member.selected_directions_i8_sha256 == MEMBER_SELECTED_DIRECTIONS_SHA256
            && direction_digest(member.selected_directions.iter())
                == MEMBER_SELECTED_DIRECTIONS_SHA256
            && member.basis_sequences_u64le_sha256 == BASIS_SEQUENCES_SHA256
            && u64le_digest(member.basis_sequences.iter()) == BASIS_SEQUENCES_SHA256
            && member.basis_i128le_sha256 == BASIS_MATRIX_SHA256
            && member.square_i128le_sha256 == SQUARE_MATRIX_SHA256
            && member.target_i128le_sha256 == TARGET_SHA256
            && member.integer_coefficients_decimal_lf_sha256 == INTEGER_COEFFICIENTS_SHA256,
        "G-0164 member exact digest drift"
    );
    ensure!(
        member.target.len() == OLD_ROWS
            && member.target.iter().all(|value| canonical_integer(value))
            && canonical_positive_integer(&member.target_scale)
            && member.integer_coefficients.len() == OLD_RANK
            && decimal_lf_digest(member.integer_coefficients.iter().map(String::as_str))
                == INTEGER_COEFFICIENTS_SHA256
            && member.terms.len() == TERMS
            && member.terms
                == nonzero_term_projection(&member.basis_sequences, &member.integer_coefficients)?,
        "G-0164 member term projection/digest drift"
    );
    for (index, term) in member.terms.iter().enumerate() {
        ensure!(
            term.sequence < RECORDS
                && canonical_integer(&term.coefficient)
                && term.coefficient != "0"
                && (index == 0 || member.terms[index - 1].sequence < term.sequence),
            "G-0164 member term structure drift at {index}"
        );
    }
    Ok(())
}

fn validate_global(global: &FrozenGlobalResult, member: &DirectBasisMember) -> Result<()> {
    ensure!(
        global.schema == GLOBAL_SCHEMA
            && global.result == GLOBAL_RESULT
            && !global.claim_boundary.is_empty()
            && global.records == RECORDS
            && global.base_rows == 412
            && global.appended_rows == 128
            && global.rows == OLD_ROWS
            && global.rank == OLD_RANK
            && global.basis_coordinates == OLD_RANK
            && global.support_columns == TERMS
            && global.terms == TERMS
            && global.complete_global_replay
            && !global.all_hinge_and_linear_residuals_zero
            && global.all_accumulated_directions_exact_zero
            && global.all_11_linear_residuals_exact_zero
            && global.first_nonzero_linear.is_none()
            && global.no_automatic_next_study
            && global.inputs_rehashed_at_end
            && global.manifest_rehashed_at_end
            && global.candidate_rehashed_at_end
            && global.wall_seconds > 0.0,
        "G-0164 global result identity/replay drift"
    );
    ensure!(
        global.finite_member.path == MEMBER_PATH
            && global.finite_member.sha256 == MEMBER_SHA256
            && global.selected_pool_indices == member.selected_pool_indices
            && global.selected_directions == member.selected_directions
            && global.selected_directions_i8_sha256 == member.selected_directions_i8_sha256
            && global.target_scale == member.target_scale,
        "G-0164 global/member bridge drift"
    );
    ensure!(
        global.accumulated_direction_count == 228
            && global.accumulated_direction_checks.len() == 228
            && global.inherited_accumulated_directions == 100
            && global.selected_accumulated_directions == 128,
        "G-0164 accumulated-direction census drift"
    );
    let mut accumulated = BTreeSet::new();
    for (index, check) in global.accumulated_direction_checks.iter().enumerate() {
        validate_direction(&check.direction)?;
        ensure!(
            check.index == index
                && check.aggregate_coefficient == "0"
                && check.direct_dp_coefficient == "0"
                && check.routes_agree
                && check.exact_zero
                && accumulated.insert(check.direction),
            "G-0164 accumulated-direction check drift at {index}"
        );
    }
    ensure!(
        global.residual_prefix_k == K
            && global.residual_prefix_count == K
            && global.residual_prefix.len() == K
            && global.residual_prefix_directions_i8_sha256 == RESIDUAL_DIRECTIONS_SHA256
            && global.residual_prefix_exact_residuals_decimal_lf_sha256
                == RESIDUAL_COEFFICIENTS_SHA256
            && direction_digest(global.residual_prefix.iter().map(|item| &item.direction))
                == RESIDUAL_DIRECTIONS_SHA256
            && decimal_lf_digest(
                global
                    .residual_prefix
                    .iter()
                    .map(|item| item.coefficient.as_str())
            ) == RESIDUAL_COEFFICIENTS_SHA256,
        "G-0164 residual-prefix census/digest drift"
    );
    ensure!(
        global
            .residual_prefix
            .windows(2)
            .all(|window| window[0].direction < window[1].direction),
        "G-0164 residual-prefix order/uniqueness drift"
    );
    let mut seen = BTreeSet::new();
    for item in &global.residual_prefix {
        validate_direction(&item.direction)?;
        ensure!(
            canonical_integer(&item.coefficient)
                && item.coefficient != "0"
                && seen.insert(item.direction)
                && !accumulated.contains(&item.direction),
            "G-0164 residual-prefix direction/residual drift"
        );
    }
    ensure!(
        global.first_nonzero_hinge.as_ref() == global.residual_prefix.first()
            && global.prefix_controls.maximum_k == K
            && global.prefix_controls.expected_count == K
            && global.prefix_controls.observed_count == K
            && global.prefix_controls.strict_signed_lexicographic_order
            && global.prefix_controls.excludes_accumulated_directions,
        "G-0164 residual-prefix control drift"
    );
    Ok(())
}

fn validate_compiled_and_static(root: &Path) -> Result<()> {
    for (compiled, path, expected) in [
        (COMPILED_SOURCE, SOURCE_PATH, None),
        (COMPILED_CARGO, CARGO_PATH, None),
        (COMPILED_LOCK, LOCK_PATH, None),
        (
            COMPILED_PREREGISTRATION,
            PREREGISTRATION_PATH,
            Some(PREREGISTRATION_SHA256),
        ),
        (COMPILED_MEMBER, MEMBER_PATH, Some(MEMBER_SHA256)),
        (
            COMPILED_GLOBAL_RESULT,
            GLOBAL_RESULT_PATH,
            Some(GLOBAL_RESULT_SHA256),
        ),
        (COMPILED_KERNEL, KERNEL_PATH, Some(KERNEL_SHA256)),
    ] {
        let compiled_sha = sha256_bytes(compiled);
        let disk_sha = sha256_path(&checked_repo_path(root, path)?)?;
        ensure!(
            compiled_sha == disk_sha && expected.is_none_or(|value| value == disk_sha),
            "compiled/static byte drift: {path}"
        );
    }
    expected_binding(root, PANEL_INPUT_PATH, PANEL_INPUT_SHA256)?;
    for path in [
        PANEL_INPUT_PATH,
        MEMBER_PATH,
        GLOBAL_RESULT_PATH,
        PREREGISTRATION_PATH,
        KERNEL_PATH,
    ] {
        git_commit_for_path(root, path)?;
    }
    Ok(())
}

fn load_static_inputs(
    root: &Path,
    panel_path: &Path,
    member_path: &Path,
    global_path: &Path,
) -> Result<StaticInputs> {
    ensure!(
        panel_path == Path::new(PANEL_INPUT_PATH)
            && member_path == Path::new(MEMBER_PATH)
            && global_path == Path::new(GLOBAL_RESULT_PATH),
        "static input path drift"
    );
    validate_compiled_and_static(root)?;
    let panel: PanelInput = strict_json(File::open(checked_repo_path(root, PANEL_INPUT_PATH)?)?)?;
    let member: DirectBasisMember =
        strict_json(File::open(checked_repo_path(root, MEMBER_PATH)?)?)?;
    let global: FrozenGlobalResult =
        strict_json(File::open(checked_repo_path(root, GLOBAL_RESULT_PATH)?)?)?;
    validate_panel(&panel)?;
    validate_member(&member)?;
    validate_global(&global, &member)?;
    Ok(StaticInputs {
        panel,
        member,
        global,
    })
}

fn make_input_mutation_controls(inputs: &StaticInputs) -> Result<InputMutationControls> {
    let mut count_mutant = inputs.global.clone();
    count_mutant.residual_prefix.pop();
    let direction_count_mutant_rejected = validate_global(&count_mutant, &inputs.member).is_err();

    let mut order_mutant = inputs.global.clone();
    order_mutant.residual_prefix.swap(0, 1);
    let direction_order_mutant_rejected = validate_global(&order_mutant, &inputs.member).is_err();

    let mut duplicate_mutant = inputs.global.clone();
    duplicate_mutant.residual_prefix[1] = duplicate_mutant.residual_prefix[0].clone();
    let direction_duplicate_mutant_rejected =
        validate_global(&duplicate_mutant, &inputs.member).is_err();

    let mut invalid_direction_mutant = inputs.global.clone();
    for coordinate in &mut invalid_direction_mutant.residual_prefix[0].direction {
        *coordinate = -*coordinate;
    }
    let direction_invalidity_mutant_rejected =
        validate_global(&invalid_direction_mutant, &inputs.member).is_err();

    let mut residual_mutant = inputs.global.clone();
    residual_mutant.residual_prefix[0].coefficient =
        (parse_bigint(&residual_mutant.residual_prefix[0].coefficient)? + BigInt::from(1))
            .to_string();
    let residual_plus_one_mutant_rejected =
        validate_global(&residual_mutant, &inputs.member).is_err();

    let mut member_count_mutant = inputs.member.clone();
    member_count_mutant.terms.pop();
    let member_term_count_mutant_rejected = validate_member(&member_count_mutant).is_err();

    let mut member_order_mutant = inputs.member.clone();
    member_order_mutant.terms.swap(0, 1);
    let member_term_order_mutant_rejected = validate_member(&member_order_mutant).is_err();

    let mut member_coefficient_mutant = inputs.member.clone();
    member_coefficient_mutant.terms[0].coefficient =
        (parse_bigint(&member_coefficient_mutant.terms[0].coefficient)? + BigInt::from(1))
            .to_string();
    let member_term_coefficient_mutant_rejected =
        validate_member(&member_coefficient_mutant).is_err();

    let record_census_truncation_rejected = validate_record_axis(
        inputs.panel.records[..RECORDS - 1]
            .iter()
            .map(|record| record.sequence),
        RECORDS,
    )
    .is_err();
    let mut order = inputs
        .panel
        .records
        .iter()
        .map(|record| record.sequence)
        .collect::<Vec<_>>();
    order.swap(0, 1);
    let record_order_mutant_rejected = validate_record_axis(order, RECORDS).is_err();

    let all_rejected = direction_count_mutant_rejected
        && direction_order_mutant_rejected
        && direction_duplicate_mutant_rejected
        && direction_invalidity_mutant_rejected
        && residual_plus_one_mutant_rejected
        && member_term_count_mutant_rejected
        && member_term_order_mutant_rejected
        && member_term_coefficient_mutant_rejected
        && record_census_truncation_rejected
        && record_order_mutant_rejected;
    ensure!(all_rejected, "Fresh128 hostile input mutant escaped");
    Ok(InputMutationControls {
        direction_count_mutant_rejected,
        direction_order_mutant_rejected,
        direction_duplicate_mutant_rejected,
        direction_invalidity_mutant_rejected,
        residual_plus_one_mutant_rejected,
        member_term_count_mutant_rejected,
        member_term_order_mutant_rejected,
        member_term_coefficient_mutant_rejected,
        record_census_truncation_rejected,
        record_order_mutant_rejected,
        all_rejected,
    })
}

fn git_is_ancestor(root: &Path, ancestor: &str, descendant: &str, label: &str) -> Result<()> {
    let status = Command::new("git")
        .args(["merge-base", "--is-ancestor", ancestor, descendant])
        .current_dir(root)
        .status()
        .with_context(|| format!("inspect Git ancestry: {label}"))?;
    ensure!(status.success(), "Git ancestry failure: {label}");
    Ok(())
}

fn validate_stage_a_manifest(
    root: &Path,
    binding: &CommitBinding,
    member: &DirectBasisMember,
) -> Result<StageAManifest> {
    validate_commit_binding(root, binding, STAGE_A_MANIFEST_PATH)?;
    let manifest: StageAManifest =
        strict_json(File::open(checked_repo_path(root, STAGE_A_MANIFEST_PATH)?)?)?;
    ensure!(
        manifest.schema == STAGE_A_MANIFEST_SCHEMA
            && manifest.result == "FROZEN_BEFORE_G0168_FIRST_ROW_EXACT_ADMISSION"
            && !manifest.claim_boundary.is_empty()
            && manifest.parameters
                == StageAManifestParameters {
                    n: N,
                    records: RECORDS,
                    old_rows: OLD_ROWS,
                    appended_rows: NEW_ROWS,
                    rows: ROWS,
                    old_rank: OLD_RANK,
                    basis_sequences_u64le_sha256: BASIS_SEQUENCES_SHA256.to_string(),
                    basis_i128le_sha256: BASIS_MATRIX_SHA256.to_string(),
                    square_i128le_sha256: SQUARE_MATRIX_SHA256.to_string(),
                    target_i128le_sha256: TARGET_SHA256.to_string(),
                    first_row_i64le_sha256: FIRST_ROW_I64_SHA256.to_string(),
                    column_order: "canonical_sequence_0_through_163739".to_string(),
                    arithmetic: "python_flint_exact_Q_and_unbounded_Python_int".to_string(),
                    fixed_modular_primes_diagnostic_only: vec![1_000_003, 1_000_033],
                }
            && manifest.planned_output
                == StageAPlannedOutput {
                    path: STAGE_A_RESULT_PATH.to_string(),
                    schema: STAGE_A_SCHEMA.to_string(),
                    allowed_results: vec![
                        STAGE_A_RANK_RESULT.to_string(),
                        STAGE_A_DEPENDENCY_RESULT.to_string(),
                    ],
                }
            && !manifest.scientific_run_executed
            && !manifest.scientific_output_created
            && canonical_sha256(&manifest.input_snapshot_sha256),
        "G-0168 Stage-A manifest contract drift"
    );
    for (commit_binding, path) in [
        (&manifest.preregistration, PREREGISTRATION_PATH),
        (&manifest.producer, STAGE_A_PRODUCER_PATH),
        (&manifest.source_audit, STAGE_A_SOURCE_AUDIT_PATH),
        (&manifest.g0164_member, MEMBER_PATH),
        (&manifest.g0164_global_result, GLOBAL_RESULT_PATH),
        (&manifest.g0170_preregistration, G0170_PREREGISTRATION_PATH),
        (&manifest.g0170_query, G0170_QUERY_PATH),
        (&manifest.g0170_coordinate, G0170_COORDINATE_PATH),
        (&manifest.g0170_bridge, G0170_BRIDGE_PATH),
    ] {
        validate_commit_binding(root, commit_binding, path)?;
    }
    ensure!(
        manifest.preregistration.sha256 == PREREGISTRATION_SHA256
            && manifest.g0164_member.sha256 == MEMBER_SHA256
            && manifest.g0164_global_result.sha256 == GLOBAL_RESULT_SHA256
            && manifest.parameters.basis_sequences_u64le_sha256
                == member.basis_sequences_u64le_sha256,
        "G-0168 Stage-A manifest frozen binding drift"
    );
    ensure!(
        manifest.input_snapshot.iter().all(|(path, expected)| {
            canonical_sha256(expected)
                && checked_repo_path(root, path)
                    .and_then(|resolved| sha256_path(&resolved))
                    .is_ok_and(|observed| observed == *expected)
        }),
        "G-0168 Stage-A manifest transitive-input drift"
    );
    ensure!(
        !manifest.input_snapshot.is_empty()
            && input_snapshot_digest(&manifest.input_snapshot) == manifest.input_snapshot_sha256,
        "G-0168 Stage-A manifest snapshot digest drift"
    );
    for commit_binding in [
        &manifest.preregistration,
        &manifest.producer,
        &manifest.source_audit,
        &manifest.g0164_member,
        &manifest.g0164_global_result,
        &manifest.g0170_preregistration,
        &manifest.g0170_query,
        &manifest.g0170_coordinate,
        &manifest.g0170_bridge,
    ] {
        ensure!(
            manifest.input_snapshot.get(&commit_binding.path) == Some(&commit_binding.sha256),
            "G-0168 Stage-A manifest snapshot omits exact named binding: {}",
            commit_binding.path
        );
    }
    Ok(manifest)
}

fn validate_stage_a_result(
    root: &Path,
    binding: &CommitBinding,
    stage_a_manifest: &StageAManifest,
    inputs: &StaticInputs,
) -> Result<StageAResult> {
    validate_commit_binding(root, binding, STAGE_A_RESULT_PATH)?;
    let stage_a: StageAResult =
        strict_json(File::open(checked_repo_path(root, STAGE_A_RESULT_PATH)?)?)
            .context("G-0168 Stage-A result strong typed contract")?;
    ensure!(
        stage_a.schema == STAGE_A_SCHEMA
            && stage_a.result == STAGE_A_RANK_RESULT
            && !stage_a.claim_boundary.is_empty()
            && stage_a.n == N
            && stage_a.records == RECORDS
            && stage_a.old_rows == OLD_ROWS
            && stage_a.appended_rows == NEW_ROWS
            && stage_a.rows == ROWS
            && stage_a.old_rank == OLD_RANK
            && stage_a.exact_dot_bridge_replayed
            && stage_a.modular_role == "DIAGNOSTIC_ONLY_NEVER_A_DECISION"
            && stage_a.inputs_rehashed_at_end
            && stage_a.manifest_rehashed_at_end
            && stage_a.no_automatic_fresh128_run
            && stage_a.wall_seconds > 0.0
            && stage_a.maximum_rss_kib > 0,
        "G-0168 Stage-A result is not the admitted rank-growth branch"
    );
    for (commit_binding, path) in [
        (&stage_a.manifest, STAGE_A_MANIFEST_PATH),
        (&stage_a.preregistration, PREREGISTRATION_PATH),
        (&stage_a.producer, STAGE_A_PRODUCER_PATH),
        (&stage_a.source_audit, STAGE_A_SOURCE_AUDIT_PATH),
        (&stage_a.g0164_member, MEMBER_PATH),
        (&stage_a.g0164_global_result, GLOBAL_RESULT_PATH),
        (&stage_a.g0170_coordinate, G0170_COORDINATE_PATH),
        (&stage_a.g0170_bridge, G0170_BRIDGE_PATH),
    ] {
        validate_commit_binding(root, commit_binding, path)?;
    }
    ensure!(
        stage_a.manifest.sha256 == binding_for_path(root, STAGE_A_MANIFEST_PATH)?.sha256
            && stage_a.manifest.git_commit == git_commit_for_path(root, STAGE_A_MANIFEST_PATH)?,
        "G-0168 Stage-A result manifest binding drift"
    );
    ensure!(
        stage_a.preregistration.sha256 == PREREGISTRATION_SHA256
            && stage_a.producer == stage_a_manifest.producer
            && stage_a.g0164_member.sha256 == MEMBER_SHA256
            && stage_a.g0164_global_result.sha256 == GLOBAL_RESULT_SHA256
            && stage_a.direction == inputs.global.residual_prefix[0].direction
            && stage_a.frozen_primitive_member_residual
                == inputs.global.residual_prefix[0].coefficient
            && stage_a.frozen_member_target_scale == inputs.member.target_scale
            && stage_a.basis_sequences == inputs.member.basis_sequences
            && stage_a.coordinate_rows == inputs.member.coordinate_rows
            && stage_a.basis_sequences_u64le_sha256 == BASIS_SEQUENCES_SHA256
            && u64le_digest(stage_a.basis_sequences.iter()) == BASIS_SEQUENCES_SHA256
            && stage_a.basis_i128le_sha256 == BASIS_MATRIX_SHA256
            && stage_a.square_i128le_sha256 == SQUARE_MATRIX_SHA256,
        "G-0168 Stage-A/member/global bridge drift"
    );
    ensure!(
        stage_a.relation.old_coordinate_rows == inputs.member.coordinate_rows
            && stage_a.relation.integer_coefficients.len() == OLD_RANK
            && stage_a
                .relation
                .integer_coefficients
                .iter()
                .all(|value| canonical_integer(value))
            && canonical_positive_integer(&stage_a.relation.hinge_scale)
            && stage_a.relation.basis_relation_exactly_replayed,
        "G-0168 Stage-A relation drift"
    );
    let branch = &stage_a.branch;
    ensure!(
        branch.witness_sequence < RECORDS
            && !inputs
                .member
                .basis_sequences
                .contains(&branch.witness_sequence)
            && canonical_integer(&branch.delta_numerator)
            && branch.delta_numerator != "0"
            && canonical_positive_integer(&branch.delta_denominator)
            && branch.old_rank == OLD_RANK
            && branch.new_rank == NEW_RANK
            && stage_a.canonical_columns_scanned == branch.witness_sequence + 1,
        "G-0168 Stage-A rank witness drift"
    );
    let null = &branch.canonical_null_vector;
    ensure!(
        null.basis_sequences == inputs.member.basis_sequences
            && null.basis_integer_coefficients.len() == OLD_RANK
            && null
                .basis_integer_coefficients
                .iter()
                .all(|value| canonical_integer(value))
            && null.witness_sequence == branch.witness_sequence
            && canonical_integer(&null.witness_integer_coefficient)
            && null.witness_integer_coefficient != "0"
            && null.support > 0
            && null.support <= NEW_RANK
            && null.all_540_old_rows_exact_zero
            && canonical_sha256(&null.old_residuals_decimal_lf_sha256)
            && canonical_integer(&null.new_row_pairing)
            && null.new_row_pairing != "0",
        "G-0168 Stage-A canonical null-vector drift"
    );
    let minor = &branch.exact_350_minor;
    let mut expected_rows = inputs.member.coordinate_rows.clone();
    expected_rows.push(OLD_ROWS);
    let mut expected_columns = inputs.member.basis_sequences.clone();
    expected_columns.push(branch.witness_sequence);
    ensure!(
        minor.rows == NEW_RANK
            && minor.columns == NEW_RANK
            && minor.coordinate_rows == expected_rows
            && minor.column_sequences == expected_columns
            && canonical_sha256(&minor.matrix_i128le_sha256)
            && canonical_integer(&minor.determinant)
            && minor.determinant != "0"
            && canonical_sha256(&minor.determinant_decimal_sha256)
            && canonical_integer(&minor.square_determinant)
            && minor.square_determinant != "0"
            && minor.schur_formula_verified,
        "G-0168 Stage-A exact 350-minor drift"
    );
    let corrected = &branch.corrected_member;
    ensure!(
        canonical_positive_integer(&corrected.target_scale)
            && corrected.basis_sequences == expected_columns
            && corrected.integer_coefficients.len() == NEW_RANK
            && corrected
                .integer_coefficients
                .iter()
                .all(|value| canonical_integer(value))
            && canonical_sha256(&corrected.integer_coefficients_decimal_lf_sha256)
            && decimal_lf_digest(corrected.integer_coefficients.iter().map(String::as_str))
                == corrected.integer_coefficients_decimal_lf_sha256
            && corrected.terms
                == nonzero_term_projection(
                    &corrected.basis_sequences,
                    &corrected.integer_coefficients,
                )?
            && corrected.support_columns == corrected.terms.len()
            && corrected.all_540_old_rows_exactly_replayed
            && canonical_sha256(&corrected.old_residuals_decimal_lf_sha256)
            && corrected.appended_zero_target_exactly_replayed
            && corrected.appended_residual == "0"
            && corrected.coefficient_plus_one_mutant.coefficient_index < NEW_RANK
            && corrected.coefficient_plus_one_mutant.sequence < RECORDS
            && canonical_integer(&corrected.coefficient_plus_one_mutant.new_row_residual)
            && (corrected.coefficient_plus_one_mutant.old_nonzero_rows > 0
                || corrected.coefficient_plus_one_mutant.new_row_residual != "0")
            && corrected.coefficient_plus_one_mutant.rejected,
        "G-0168 Stage-A corrected-member contract drift"
    );
    ensure!(
        stage_a
            .source_and_input_bindings
            .iter()
            .all(|(path, binding)| {
                path == &binding.path
                    && canonical_sha256(&binding.sha256)
                    && checked_repo_path(root, path)
                        .and_then(|resolved| sha256_path(&resolved))
                        .is_ok_and(|observed| observed == binding.sha256)
            }),
        "G-0168 Stage-A output transitive binding drift"
    );
    ensure!(
        stage_a.source_and_input_bindings.len() == stage_a_manifest.input_snapshot.len()
            && stage_a
                .source_and_input_bindings
                .iter()
                .all(|(path, binding)| {
                    stage_a_manifest.input_snapshot.get(path) == Some(&binding.sha256)
                })
            && stage_a.input_snapshot_sha256 == stage_a_manifest.input_snapshot_sha256
            && input_snapshot_digest(&stage_a_manifest.input_snapshot)
                == stage_a.input_snapshot_sha256,
        "G-0168 Stage-A manifest/result snapshot disagreement"
    );
    Ok(stage_a)
}

fn source_audit_checks_pass(checks: &SourceAuditChecks) -> bool {
    checks.exact_named_binding_contract
        && checks.duplicate_json_keys_rejected
        && checks.trailing_json_data_rejected
        && checks.strict_input_and_future_manifest_schemas_verified
        && checks.hostile_direction_order_count_and_residual_mutants_rejected
        && checks.hostile_member_term_mutants_rejected
        && checks.dependency_branch_rejected
        && checks.stage_a_rank_growth_contract_verified
        && checks.compiled_source_cargo_lock_kernel_match_working_bytes
        && checks.fixed_12_thread_record_parallel_batch_kernel_verified
        && checks.arbitrary_precision_304_term_dots_verified
        && checks.atomic_exclusive_output_verified
        && checks.end_rehash_verified
        && checks.producer_self_test_passed
        && checks.producer_static_preflight_passed
        && checks.prohibited_scientific_modes_not_run
}

fn validate_source_audit(root: &Path, manifest: &StudyManifest) -> Result<()> {
    validate_commit_binding(
        root,
        &manifest.source_audit_preregistration,
        SOURCE_AUDIT_PREREGISTRATION_PATH,
    )?;
    validate_commit_binding(root, &manifest.source_audit, SOURCE_AUDIT_PATH)?;
    let receipt: SourceAuditReceipt =
        strict_json(File::open(checked_repo_path(root, SOURCE_AUDIT_PATH)?)?)?;
    ensure!(
        receipt.schema == SOURCE_AUDIT_SCHEMA
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_AUDIT_RESULT
            && receipt.evidence_class == SOURCE_AUDIT_EVIDENCE
            && receipt.claim_boundary == SOURCE_AUDIT_CLAIM_BOUNDARY
            && receipt.no_claim == SOURCE_AUDIT_NO_CLAIM
            && !receipt.reviewer.agent_name.is_empty()
            && receipt.reviewer.program == "codex"
            && !receipt.reviewer.model.is_empty()
            && receipt.reviewer.same_model_lineage
            && receipt.reviewer.fresh_context
            && receipt.audit_preregistration == manifest.source_audit_preregistration
            && receipt.subject.git_commit == manifest.producer.git_commit
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings
            && receipt.subject.bindings == manifest.producer
            && source_audit_checks_pass(&receipt.required_checks)
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_run_executed,
        "G-0173 outcome-blind source-audit gate drift"
    );
    git_is_ancestor(
        root,
        &manifest.producer.git_commit,
        &manifest.source_audit_preregistration.git_commit,
        "Fresh128 producer -> source-audit preregistration",
    )?;
    git_is_ancestor(
        root,
        &manifest.source_audit_preregistration.git_commit,
        &manifest.source_audit.git_commit,
        "Fresh128 source-audit preregistration -> receipt",
    )
}

fn validate_current_release(root: &Path, producer: &ProducerBindings) -> Result<()> {
    let executable = std::env::current_exe()?.canonicalize()?;
    let expected = checked_repo_path(root, EXECUTABLE_PATH)?;
    ensure!(
        executable == expected,
        "scientific preflight/run requires frozen Fresh128 release executable"
    );
    ensure!(
        canonical_commit(&producer.git_commit),
        "producer commit drift"
    );
    for (binding, path) in [
        (&producer.main_source, SOURCE_PATH),
        (&producer.cargo_manifest, CARGO_PATH),
        (&producer.cargo_lock, LOCK_PATH),
        (&producer.g0117_lib_source, KERNEL_PATH),
        (&producer.release_executable, EXECUTABLE_PATH),
    ] {
        validate_binding(root, binding, path)?;
    }
    ensure!(
        producer.g0117_lib_source.sha256 == KERNEL_SHA256
            && [SOURCE_PATH, CARGO_PATH, LOCK_PATH, EXECUTABLE_PATH]
                .iter()
                .all(|path| git_commit_for_path(root, path)
                    .is_ok_and(|commit| commit == producer.git_commit)),
        "producer one-commit freeze drift"
    );
    Ok(())
}

fn validate_manifest(
    root: &Path,
    supplied_path: &Path,
    supplied_stage_a_path: &Path,
    inputs: &StaticInputs,
) -> Result<(ManifestSnapshot, StageAResult)> {
    ensure!(
        supplied_path == Path::new(MANIFEST_PATH),
        "Fresh128 manifest path drift"
    );
    ensure!(
        supplied_stage_a_path == Path::new(STAGE_A_RESULT_PATH),
        "G-0168 Stage-A result path drift"
    );
    let manifest: StudyManifest =
        strict_json(File::open(checked_repo_path(root, MANIFEST_PATH)?)?)?;
    let manifest_binding = commit_binding_for_path(root, MANIFEST_PATH)?;
    ensure!(
        manifest.schema == MANIFEST_SCHEMA
            && manifest.result == MANIFEST_RESULT
            && manifest.claim_boundary == CLAIM_BOUNDARY
            && manifest.parameters
                == ManifestParameters {
                    n: N,
                    records: RECORDS,
                    directions: K,
                    member_terms: TERMS,
                    hinge_entries: HINGE_ENTRIES,
                    threads: THREADS,
                    arithmetic: "signed_i64_prices_and_num_bigint_BigInt_dots".to_string(),
                    direction_order: "G0164_residual_prefix_signed_lexicographic".to_string(),
                    column_order: "canonical_sequence_0_through_163739".to_string(),
                }
            && manifest.planned_output
                == PlannedOutput {
                    path: OUTPUT_PATH.to_string(),
                    schema: OUTPUT_SCHEMA.to_string(),
                    result: OUTPUT_RESULT.to_string(),
                }
            && !manifest.scientific_pricing_executed
            && !manifest.scientific_output_created,
        "Fresh128 manifest identity/parameter/output drift"
    );
    for (binding, path) in [
        (&manifest.preregistration, PREREGISTRATION_PATH),
        (&manifest.stage_a_manifest, STAGE_A_MANIFEST_PATH),
        (&manifest.stage_a_result, STAGE_A_RESULT_PATH),
        (&manifest.g0164_member, MEMBER_PATH),
        (&manifest.g0164_global_result, GLOBAL_RESULT_PATH),
        (&manifest.panel_input, PANEL_INPUT_PATH),
        (&manifest.g0117_lib_source, KERNEL_PATH),
    ] {
        validate_commit_binding(root, binding, path)?;
    }
    ensure!(
        manifest.preregistration.sha256 == PREREGISTRATION_SHA256
            && manifest.g0164_member.sha256 == MEMBER_SHA256
            && manifest.g0164_global_result.sha256 == GLOBAL_RESULT_SHA256
            && manifest.panel_input.sha256 == PANEL_INPUT_SHA256
            && manifest.g0117_lib_source.sha256 == KERNEL_SHA256,
        "Fresh128 manifest frozen input drift"
    );
    validate_current_release(root, &manifest.producer)?;
    validate_source_audit(root, &manifest)?;
    let stage_a_manifest =
        validate_stage_a_manifest(root, &manifest.stage_a_manifest, &inputs.member)?;
    let stage_a =
        validate_stage_a_result(root, &manifest.stage_a_result, &stage_a_manifest, inputs)?;
    ensure!(
        stage_a.manifest == manifest.stage_a_manifest,
        "Fresh128 manifest/Stage-A manifest binding disagreement"
    );

    let mut bindings_by_path = BTreeMap::new();
    for binding in &manifest.transitive_inputs {
        ensure!(
            canonical_sha256(&binding.sha256)
                && bindings_by_path
                    .insert(binding.path.clone(), binding.sha256.clone())
                    .is_none(),
            "duplicate/malformed Fresh128 transitive binding: {}",
            binding.path
        );
    }
    ensure!(
        manifest
            .transitive_inputs
            .windows(2)
            .all(|window| window[0].path < window[1].path),
        "Fresh128 transitive bindings are not in strict path order"
    );
    for (path, expected) in &bindings_by_path {
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "Fresh128 manifest-bound input drift: {path}"
        );
    }
    for binding in [
        Binding {
            path: manifest.preregistration.path.clone(),
            sha256: manifest.preregistration.sha256.clone(),
        },
        manifest.producer.main_source.clone(),
        manifest.producer.cargo_manifest.clone(),
        manifest.producer.cargo_lock.clone(),
        manifest.producer.g0117_lib_source.clone(),
        manifest.producer.release_executable.clone(),
        Binding {
            path: manifest.source_audit_preregistration.path.clone(),
            sha256: manifest.source_audit_preregistration.sha256.clone(),
        },
        Binding {
            path: manifest.source_audit.path.clone(),
            sha256: manifest.source_audit.sha256.clone(),
        },
        Binding {
            path: manifest.stage_a_manifest.path.clone(),
            sha256: manifest.stage_a_manifest.sha256.clone(),
        },
        Binding {
            path: manifest.stage_a_result.path.clone(),
            sha256: manifest.stage_a_result.sha256.clone(),
        },
        Binding {
            path: manifest.g0164_member.path.clone(),
            sha256: manifest.g0164_member.sha256.clone(),
        },
        Binding {
            path: manifest.g0164_global_result.path.clone(),
            sha256: manifest.g0164_global_result.sha256.clone(),
        },
        Binding {
            path: manifest.panel_input.path.clone(),
            sha256: manifest.panel_input.sha256.clone(),
        },
    ] {
        ensure!(
            bindings_by_path.get(&binding.path) == Some(&binding.sha256),
            "Fresh128 transitive map omits exact named binding: {}",
            binding.path
        );
    }
    for (path, binding) in &stage_a.source_and_input_bindings {
        ensure!(
            bindings_by_path.get(path) == Some(&binding.sha256),
            "Fresh128 manifest omits Stage-A transitive binding: {path}"
        );
    }
    let snapshot = ManifestSnapshot {
        manifest,
        binding: manifest_binding,
        bindings_by_path,
    };
    git_is_ancestor(
        root,
        &snapshot.manifest.source_audit.git_commit,
        &snapshot.binding.git_commit,
        "Fresh128 source audit -> scientific manifest",
    )?;
    git_is_ancestor(
        root,
        &snapshot.manifest.stage_a_result.git_commit,
        &snapshot.binding.git_commit,
        "G-0168 Stage-A result -> Fresh128 manifest",
    )?;
    Ok((snapshot, stage_a))
}

fn custody_snapshot(root: &Path, manifest: &ManifestSnapshot) -> Result<BTreeMap<String, String>> {
    let mut snapshot = manifest.bindings_by_path.clone();
    snapshot.insert(MANIFEST_PATH.to_string(), manifest.binding.sha256.clone());
    for (path, expected) in &snapshot {
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "custody drift: {path}"
        );
    }
    Ok(snapshot)
}

fn load_and_validate_inputs(
    root: &Path,
    panel_path: &Path,
    member_path: &Path,
    global_path: &Path,
    stage_a_path: &Path,
    manifest_path: &Path,
) -> Result<ValidatedInputs> {
    let static_inputs = load_static_inputs(root, panel_path, member_path, global_path)?;
    let (manifest, stage_a) = validate_manifest(root, manifest_path, stage_a_path, &static_inputs)?;
    let custody = custody_snapshot(root, &manifest)?;
    Ok(ValidatedInputs {
        static_inputs,
        stage_a,
        manifest,
        custody,
    })
}

fn fixture_binding(path: &str) -> Value {
    serde_json::json!({"path": path, "sha256": "0".repeat(64)})
}

fn fixture_commit_binding(path: &str) -> Value {
    serde_json::json!({
        "path": path,
        "sha256": "0".repeat(64),
        "git_commit": "0".repeat(40)
    })
}

fn stage_a_fixture_value(result: &str) -> Value {
    serde_json::json!({
        "schema": STAGE_A_SCHEMA,
        "result": result,
        "claim_boundary": "fixture",
        "manifest": fixture_commit_binding(STAGE_A_MANIFEST_PATH),
        "preregistration": fixture_commit_binding(PREREGISTRATION_PATH),
        "producer": fixture_commit_binding(STAGE_A_PRODUCER_PATH),
        "source_audit": fixture_commit_binding(STAGE_A_SOURCE_AUDIT_PATH),
        "g0164_member": fixture_commit_binding(MEMBER_PATH),
        "g0164_global_result": fixture_commit_binding(GLOBAL_RESULT_PATH),
        "g0170_coordinate": fixture_commit_binding(G0170_COORDINATE_PATH),
        "g0170_bridge": fixture_commit_binding(G0170_BRIDGE_PATH),
        "source_and_input_bindings": {},
        "n": N,
        "records": RECORDS,
        "old_rows": OLD_ROWS,
        "appended_rows": NEW_ROWS,
        "rows": ROWS,
        "old_rank": OLD_RANK,
        "direction": [0,0,0,0,0,0,0,1,-3,-2,4],
        "frozen_primitive_member_residual": "1",
        "frozen_member_target_scale": "1",
        "exact_dot_bridge_replayed": true,
        "basis_sequences": (0..OLD_RANK).collect::<Vec<_>>(),
        "basis_sequences_u64le_sha256": "0".repeat(64),
        "coordinate_rows": (0..OLD_RANK).collect::<Vec<_>>(),
        "basis_i128le_sha256": "0".repeat(64),
        "square_i128le_sha256": "0".repeat(64),
        "relation": {
            "old_coordinate_rows": (0..OLD_RANK).collect::<Vec<_>>(),
            "integer_coefficients": vec!["0"; OLD_RANK],
            "hinge_scale": "1",
            "basis_relation_exactly_replayed": true
        },
        "canonical_columns_scanned": 351,
        "first_modular_nonzero_diagnostics": {"1000003": 350, "1000033": 350},
        "modular_role": "DIAGNOSTIC_ONLY_NEVER_A_DECISION",
        "branch": {
            "witness_sequence": 350,
            "delta_numerator": "1",
            "delta_denominator": "1",
            "old_rank": OLD_RANK,
            "new_rank": NEW_RANK,
            "canonical_null_vector": {
                "basis_sequences": (0..OLD_RANK).collect::<Vec<_>>(),
                "basis_integer_coefficients": vec!["0"; OLD_RANK],
                "witness_sequence": 350,
                "witness_integer_coefficient": "1",
                "support": 1,
                "all_540_old_rows_exact_zero": true,
                "old_residuals_decimal_lf_sha256": "0".repeat(64),
                "new_row_pairing": "1"
            },
            "exact_350_minor": {
                "rows": NEW_RANK,
                "columns": NEW_RANK,
                "coordinate_rows": (0..NEW_RANK).collect::<Vec<_>>(),
                "column_sequences": (0..NEW_RANK).collect::<Vec<_>>(),
                "matrix_i128le_sha256": "0".repeat(64),
                "determinant": "1",
                "determinant_decimal_sha256": "0".repeat(64),
                "square_determinant": "1",
                "schur_formula_verified": true
            },
            "corrected_member": {
                "target_scale": "1",
                "basis_sequences": (0..NEW_RANK).collect::<Vec<_>>(),
                "integer_coefficients": vec!["0"; NEW_RANK],
                "integer_coefficients_decimal_lf_sha256": "0".repeat(64),
                "support_columns": 0,
                "terms": [],
                "all_540_old_rows_exactly_replayed": true,
                "old_residuals_decimal_lf_sha256": "0".repeat(64),
                "appended_zero_target_exactly_replayed": true,
                "appended_residual": "0",
                "coefficient_plus_one_mutant": {
                    "coefficient_index": 0,
                    "sequence": 0,
                    "is_witness_column": false,
                    "old_nonzero_rows": 1,
                    "new_row_residual": "0",
                    "rejected": true
                }
            }
        },
        "input_snapshot_sha256": "0".repeat(64),
        "inputs_rehashed_at_end": true,
        "manifest_rehashed_at_end": true,
        "no_automatic_fresh128_run": true,
        "wall_seconds": 1.0,
        "maximum_rss_kib": 1
    })
}

fn producer_fixture_value() -> Value {
    serde_json::json!({
        "git_commit": "0".repeat(40),
        "main_source": fixture_binding(SOURCE_PATH),
        "cargo_manifest": fixture_binding(CARGO_PATH),
        "cargo_lock": fixture_binding(LOCK_PATH),
        "g0117_lib_source": fixture_binding(KERNEL_PATH),
        "release_executable": fixture_binding(EXECUTABLE_PATH)
    })
}

fn manifest_fixture_value() -> Value {
    serde_json::json!({
        "schema": MANIFEST_SCHEMA,
        "result": MANIFEST_RESULT,
        "claim_boundary": CLAIM_BOUNDARY,
        "preregistration": fixture_commit_binding(PREREGISTRATION_PATH),
        "producer": producer_fixture_value(),
        "source_audit_preregistration": fixture_commit_binding(SOURCE_AUDIT_PREREGISTRATION_PATH),
        "source_audit": fixture_commit_binding(SOURCE_AUDIT_PATH),
        "stage_a_manifest": fixture_commit_binding(STAGE_A_MANIFEST_PATH),
        "stage_a_result": fixture_commit_binding(STAGE_A_RESULT_PATH),
        "g0164_member": fixture_commit_binding(MEMBER_PATH),
        "g0164_global_result": fixture_commit_binding(GLOBAL_RESULT_PATH),
        "panel_input": fixture_commit_binding(PANEL_INPUT_PATH),
        "g0117_lib_source": fixture_commit_binding(KERNEL_PATH),
        "transitive_inputs": [],
        "parameters": {
            "n": N,
            "records": RECORDS,
            "directions": K,
            "member_terms": TERMS,
            "hinge_entries": HINGE_ENTRIES,
            "threads": THREADS,
            "arithmetic": "signed_i64_prices_and_num_bigint_BigInt_dots",
            "direction_order": "G0164_residual_prefix_signed_lexicographic",
            "column_order": "canonical_sequence_0_through_163739"
        },
        "planned_output": {
            "path": OUTPUT_PATH,
            "schema": OUTPUT_SCHEMA,
            "result": OUTPUT_RESULT
        },
        "scientific_pricing_executed": false,
        "scientific_output_created": false
    })
}

fn source_audit_fixture_value() -> Value {
    serde_json::json!({
        "schema": SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": SOURCE_AUDIT_RESULT,
        "evidence_class": SOURCE_AUDIT_EVIDENCE,
        "claim_boundary": SOURCE_AUDIT_CLAIM_BOUNDARY,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": true,
            "fresh_context": true
        },
        "audit_preregistration": fixture_commit_binding(SOURCE_AUDIT_PREREGISTRATION_PATH),
        "subject": {
            "git_commit": "0".repeat(40),
            "commit_object_and_working_bytes_equal_for_all_bindings": true,
            "bindings": producer_fixture_value()
        },
        "required_checks": {
            "exact_named_binding_contract": true,
            "duplicate_json_keys_rejected": true,
            "trailing_json_data_rejected": true,
            "strict_input_and_future_manifest_schemas_verified": true,
            "hostile_direction_order_count_and_residual_mutants_rejected": true,
            "hostile_member_term_mutants_rejected": true,
            "dependency_branch_rejected": true,
            "stage_a_rank_growth_contract_verified": true,
            "compiled_source_cargo_lock_kernel_match_working_bytes": true,
            "fixed_12_thread_record_parallel_batch_kernel_verified": true,
            "arbitrary_precision_304_term_dots_verified": true,
            "atomic_exclusive_output_verified": true,
            "end_rehash_verified": true,
            "producer_self_test_passed": true,
            "producer_static_preflight_passed": true,
            "prohibited_scientific_modes_not_run": true
        },
        "scientific_manifest_observed": false,
        "scientific_input_observed": false,
        "scientific_output_observed": false,
        "scientific_run_executed": false,
        "no_claim": SOURCE_AUDIT_NO_CLAIM
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
            && strict_json_value(br#"{"ok":true} trailing"#.as_slice()).is_err()
            && serde_json::from_str::<Term>(r#"{"sequence":0,"coefficient":"1","extra":2}"#)
                .is_err(),
        "duplicate/trailing/unknown JSON control failed"
    );

    let member: DirectBasisMember = strict_json(std::io::Cursor::new(COMPILED_MEMBER))?;
    let global: FrozenGlobalResult = strict_json(std::io::Cursor::new(COMPILED_GLOBAL_RESULT))?;
    validate_member(&member)?;
    validate_global(&global, &member)?;
    let mut global_unknown = strict_json_value(std::io::Cursor::new(COMPILED_GLOBAL_RESULT))?;
    global_unknown["__unexpected"] = Value::Bool(true);
    let mut member_unknown = strict_json_value(std::io::Cursor::new(COMPILED_MEMBER))?;
    member_unknown["__unexpected"] = Value::Bool(true);
    ensure!(
        serde_json::from_value::<FrozenGlobalResult>(global_unknown).is_err()
            && serde_json::from_value::<DirectBasisMember>(member_unknown).is_err(),
        "unknown frozen input field accepted"
    );

    let rank_fixture: StageAResult =
        serde_json::from_value(stage_a_fixture_value(STAGE_A_RANK_RESULT))?;
    let dependency_fixture: StageAResult =
        serde_json::from_value(stage_a_fixture_value(STAGE_A_DEPENDENCY_RESULT))?;
    ensure!(
        rank_fixture.result == STAGE_A_RANK_RESULT
            && dependency_fixture.result != STAGE_A_RANK_RESULT,
        "Stage-A rank/dependency branch gate drift"
    );
    let mut stage_a_unknown = stage_a_fixture_value(STAGE_A_RANK_RESULT);
    stage_a_unknown["__unexpected"] = Value::Bool(true);
    let manifest_fixture = manifest_fixture_value();
    let source_audit_fixture = source_audit_fixture_value();
    ensure!(
        serde_json::from_value::<StudyManifest>(manifest_fixture.clone()).is_ok()
            && serde_json::from_value::<SourceAuditReceipt>(source_audit_fixture.clone()).is_ok()
            && serde_json::from_value::<StageAResult>(stage_a_unknown).is_err(),
        "future strong typed schema fixture failed"
    );
    let mut manifest_unknown = manifest_fixture;
    manifest_unknown["parameters"]["__unexpected"] = Value::Bool(true);
    let mut source_audit_unknown = source_audit_fixture;
    source_audit_unknown["required_checks"]["__unexpected"] = Value::Bool(true);
    ensure!(
        serde_json::from_value::<StudyManifest>(manifest_unknown).is_err()
            && serde_json::from_value::<SourceAuditReceipt>(source_audit_unknown).is_err(),
        "unknown future manifest/source-audit field accepted"
    );

    let transposed = transpose_record_major(vec![vec![1, 2, 3], vec![4, 5, 6]], 3)?;
    ensure!(
        transposed == vec![vec![1, 4], vec![2, 5], vec![3, 6]]
            && transpose_record_major(vec![vec![1], vec![2, 3]], 2).is_err(),
        "direction-major transpose/census drift"
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
        form.labelled_permutations == (1..=N as u64).product::<u64>() && form.hinges.len() > K,
        "known-answer normal form lacks Fresh128 support"
    );
    let mut directions = form.hinges.keys().copied().collect::<Vec<_>>();
    directions.sort();
    directions.truncate(K);
    let prices = hinge_coefficients(&record, &directions)?;
    ensure!(
        directions
            .iter()
            .zip(&prices)
            .all(|(direction, value)| form.hinges[direction] == *value),
        "audited batch kernel/full-normal-form bridge drift"
    );

    let huge = parse_bigint(&global.residual_prefix[0].coefficient)?;
    let row = [i64::MAX, i64::MIN + 1];
    let terms = [(0usize, huge.clone()), (1usize, -huge)];
    ensure!(
        exact_dot(&row, &terms).to_string().len() > 300,
        "arbitrary-precision dot narrowed"
    );

    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0168-fresh128-publish-self-test-{}-{unique}",
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

fn static_preflight(panel_path: PathBuf, member_path: PathBuf, global_path: PathBuf) -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let inputs = load_static_inputs(&root, &panel_path, &member_path, &global_path)?;
    let controls = make_input_mutation_controls(&inputs)?;
    ensure!(controls.all_rejected, "static hostile-control drift");
    println!(
        "G-0168 Fresh128 Stage-B static preflight PASS: {} records; {} exact member terms; {} frozen residual-prefix directions; future manifest/Stage-A result not consumed",
        inputs.panel.records.len(),
        inputs.member.terms.len(),
        inputs.global.residual_prefix.len()
    );
    Ok(())
}

fn preflight(
    panel_path: PathBuf,
    member_path: PathBuf,
    global_path: PathBuf,
    stage_a_path: PathBuf,
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
        &panel_path,
        &member_path,
        &global_path,
        &stage_a_path,
        &manifest_path,
    )?;
    let controls = make_input_mutation_controls(&inputs.static_inputs)?;
    ensure!(
        controls.all_rejected && inputs.stage_a.result == STAGE_A_RANK_RESULT,
        "scientific preflight gate drift"
    );
    println!(
        "G-0168 Fresh128 Stage-B preflight PASS: {} records; {} directions; committed FIRST_ROW_EXACT_RANK_GROWTH and all custody bindings verified",
        inputs.static_inputs.panel.records.len(),
        inputs.static_inputs.global.residual_prefix.len()
    );
    Ok(())
}

fn run(
    panel_path: PathBuf,
    member_path: PathBuf,
    global_path: PathBuf,
    stage_a_path: PathBuf,
    manifest_path: PathBuf,
    output_path: PathBuf,
) -> Result<()> {
    ensure!(output_path == Path::new(OUTPUT_PATH), "output path drift");
    ensure!(!output_path.exists(), "refusing to overwrite output");
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(THREADS)
        .build_global()
        .context("build fixed Fresh128 thread pool")?;
    let started = Instant::now();
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let inputs = load_and_validate_inputs(
        &root,
        &panel_path,
        &member_path,
        &global_path,
        &stage_a_path,
        &manifest_path,
    )?;
    let input_mutation_controls = make_input_mutation_controls(&inputs.static_inputs)?;
    let directions = inputs
        .static_inputs
        .global
        .residual_prefix
        .iter()
        .map(|item| item.direction)
        .collect::<Vec<_>>();
    ensure!(
        directions.len() == K,
        "Fresh128 pricing direction census drift"
    );

    let record_major = inputs
        .static_inputs
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
        "exact Fresh128 coordinate dimensions drift"
    );
    let complete_hinge_digest = digest_i64(direction_major.iter().flat_map(|row| row.iter()));

    let exact_terms = inputs
        .static_inputs
        .member
        .terms
        .iter()
        .map(|term| Ok((term.sequence, parse_bigint(&term.coefficient)?)))
        .collect::<Result<Vec<_>>>()?;
    ensure!(exact_terms.len() == TERMS, "exact member term census drift");
    let exact_dots = direction_major
        .iter()
        .map(|row| exact_dot(row, &exact_terms))
        .collect::<Vec<_>>();
    let exact_dot_strings = exact_dots
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    ensure!(
        exact_dot_strings.len() == K,
        "exact member-dot census drift"
    );
    for (index, (dot, frozen)) in exact_dot_strings
        .iter()
        .zip(&inputs.static_inputs.global.residual_prefix)
        .enumerate()
    {
        ensure!(
            canonical_integer(dot) && dot == &frozen.coefficient,
            "exact 304-term member dot disagrees with frozen residual at Fresh128 row {index}"
        );
    }
    let exact_dot_digest = decimal_lf_digest(exact_dot_strings.iter().map(String::as_str));
    ensure!(
        exact_dot_digest == RESIDUAL_COEFFICIENTS_SHA256,
        "exact member-dot decimal-LF digest drift"
    );

    let mutant_term = inputs
        .static_inputs
        .member
        .terms
        .iter()
        .find(|term| direction_major.iter().any(|row| row[term.sequence] != 0))
        .context("no member coefficient can exercise a Fresh128 row")?;
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
        "member coefficient-plus-one mutant survived"
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
        .static_inputs
        .global
        .residual_prefix
        .iter()
        .zip(direction_major)
        .zip(exact_dot_strings.iter())
        .enumerate()
        .map(|(index, ((frozen, coefficients), exact_dot))| {
            let minimum = coefficients.iter().copied().min().unwrap_or(0);
            let maximum = coefficients.iter().copied().max().unwrap_or(0);
            let maximum_absolute = coefficients
                .iter()
                .map(|value| value.unsigned_abs())
                .max()
                .unwrap_or(0);
            PriceRow {
                index,
                direction: frozen.direction,
                frozen_residual: frozen.coefficient.clone(),
                exact_member_dot: exact_dot.clone(),
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
                    && row.exact_member_dot == row.frozen_residual
            }),
        "output row census/order/dot drift"
    );

    let custody_end = custody_snapshot(&root, &inputs.manifest)?;
    ensure!(
        inputs.custody == custody_end,
        "input/source custody drift during Fresh128 pricing"
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
        claim_boundary: CLAIM_BOUNDARY,
        manifest: inputs.manifest.binding.clone(),
        stage_a_result: inputs.manifest.manifest.stage_a_result.clone(),
        g0164_member: expected_binding(&root, MEMBER_PATH, MEMBER_SHA256)?,
        g0164_global_result: expected_binding(&root, GLOBAL_RESULT_PATH, GLOBAL_RESULT_SHA256)?,
        source_and_input_bindings,
        n: N,
        records: RECORDS,
        terms: TERMS,
        directions: K,
        hinge_entries: HINGE_ENTRIES,
        threads: THREADS,
        arithmetic: "signed_i64_prices_and_num_bigint_BigInt_dots",
        residual_prefix_directions_i8_sha256: RESIDUAL_DIRECTIONS_SHA256.to_string(),
        residual_prefix_exact_residuals_decimal_lf_sha256: exact_dot_digest.clone(),
        ordered_directions: directions,
        direction_major_hinge_i64_le_sha256: complete_hinge_digest,
        exact_member_dots_decimal_lf_sha256: exact_dot_digest,
        exact_member_dots: exact_dot_strings,
        rows,
        input_mutation_controls,
        coefficient_plus_one_mutant,
        inputs_rehashed_at_end: true,
        manifest_rehashed_at_end: true,
        stage_a_result_rehashed_at_end: true,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let stdout = serde_json::json!({
        "schema": output.schema,
        "result": output.result,
        "records": output.records,
        "directions": output.directions,
        "hinge_entries": output.hinge_entries,
        "direction_major_hinge_i64_le_sha256": output.direction_major_hinge_i64_le_sha256,
        "exact_member_dots_decimal_lf_sha256": output.exact_member_dots_decimal_lf_sha256,
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
        println!("G-0168 Fresh128 Stage-B self-test PASS");
        return Ok(());
    }
    if args.len() == 5 && args[1] == "--preflight-static" {
        return static_preflight(
            PathBuf::from(&args[2]),
            PathBuf::from(&args[3]),
            PathBuf::from(&args[4]),
        );
    }
    if args.len() == 7 && args[1] == "--preflight" {
        return preflight(
            PathBuf::from(&args[2]),
            PathBuf::from(&args[3]),
            PathBuf::from(&args[4]),
            PathBuf::from(&args[5]),
            PathBuf::from(&args[6]),
        );
    }
    ensure!(
        args.len() == 7,
        "usage: g0168-stage-b-fresh128-coordinate-pricer --self-test | --preflight-static PANEL G0164_MEMBER G0164_GLOBAL | --preflight PANEL G0164_MEMBER G0164_GLOBAL G0168_STAGE_A_RESULT MANIFEST | PANEL G0164_MEMBER G0164_GLOBAL G0168_STAGE_A_RESULT MANIFEST OUTPUT"
    );
    run(
        PathBuf::from(&args[1]),
        PathBuf::from(&args[2]),
        PathBuf::from(&args[3]),
        PathBuf::from(&args[4]),
        PathBuf::from(&args[5]),
        PathBuf::from(&args[6]),
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
        let huge = BigInt::parse_bytes(b"9".repeat(500).as_slice(), 10).unwrap();
        let row = [i64::MAX, i64::MIN + 1];
        let terms = [(0usize, huge.clone()), (1usize, -huge)];
        assert!(exact_dot(&row, &terms).to_string().len() > 500);
    }
}
