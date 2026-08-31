mod engine;

use anyhow::{Context, Result, ensure};
use engine::{
    ExactNormalForm, exact_hinge_coefficients, exact_linear_vector, factorial, normal_form_digest,
    validated_full_normal_form,
};
use g0117_global_coordinate_pricer::{N, Record, validate_direction};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::de::{self, DeserializeOwned, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Seek, SeekFrom, Write};
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use std::time::Instant;

const RECORDS: usize = 163_740;
const OLD_ROWS: usize = 380;
const APPENDED_ROWS: usize = 32;
const ROWS: usize = OLD_ROWS + APPENDED_ROWS;
const OLD_CARRY_DIRECTIONS: usize = 68;
const CARRY_DIRECTIONS: usize = OLD_CARRY_DIRECTIONS + APPENDED_ROWS;
const ANCESTOR_BATCH_K: usize = 32;
const BATCH_K: usize = 128;
const THREADS: usize = 12;
const PANEL_ROWS: usize = 301;
const LINEAR_ROWS: usize = N;
const PANEL_ENTRY_BYTES: usize = 16;
const PANEL_COLUMN_BYTES: usize = PANEL_ROWS * PANEL_ENTRY_BYTES;

const PANEL_INPUT_PATH: &str = "artifacts/math/G-0113/panel_solver_input_v1.json";
const PANEL_CACHE_PATH: &str = "artifacts/math/G-0117/full_family_cache_v1.i128le";
const PANEL_CACHE_MANIFEST_PATH: &str = "artifacts/math/G-0117/full_family_cache_manifest_v1.json";
const SHARED_MANIFEST_PATH: &str = "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json";
const STAGE_A_RECEIPT_PATH: &str = "artifacts/math/G-0135/batch32_global_replay_v1.json";
const STAGE_B_RECEIPT_PATH: &str = "artifacts/math/G-0135/batch32_coordinate_prices_v1.json";
const STAGE_C_RESULT_PATH: &str = "artifacts/math/G-0135/full_family_master_result_v3.json";
const ANCESTOR_STAGE_D_RESULT_PATH: &str = "artifacts/math/G-0135/new_member_global_replay_v1.json";
const ANCESTOR_STAGE_D_RESULT_SHA256: &str =
    "d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875";
const ANCESTOR_STAGE_D_COMMIT: &str = "270a62455097cbaf0a8f80426c54b6121d1afcba";
const ANCESTOR_AGGREGATE_HINGE_SHA256: &str =
    "168f91bd8735c778b492fd7f2f7414d4428dfd1af8af21bd8afe294c1b2ecf60";
const ANCESTOR_NONZERO_HINGE_SHA256: &str =
    "9d7dd907d6885ab5e5b5a5a783b0212da8f145c1202fdb4de2c90f44d55023aa";
const ANCESTOR_COMPLETE_RESIDUAL_SHA256: &str =
    "3f9ca1a339ad8cdcb3260b12a48b554b4c5b401144cf5cd627f7ec1db30a7ce6";
const ANCESTOR_TERM_TRANSCRIPT_SHA256: &str =
    "7670731c72b64e89517d4d68d8ca44b73947db3c2a24938a4e843dfb9d8c1bbd";
const ANCESTOR_FIRST32_DIRECTIONS_SHA256: &str =
    "b91dcdedc2834f6d0639846dc258cd6bf4aba42c0debae34761fd857f25384ce";
const ANCESTOR_FIRST32_RESIDUALS_SHA256: &str =
    "7a95296dc09b6a156f2ec385e1f6b4e94907a9c8c0ae0c18428d16a925903321";
const ANCESTOR_FIRST_DIRECTION: [i8; N] = [0, 0, 0, 0, 0, 0, 1, -2, -2, 1, 2];
const ANCESTOR_FIRST_COEFFICIENT: &str = "511838695529252537134751622979004566912532181650940275812075139014937590867028110892243795641237175143066549672701558636166678186077128694292857947716107231627691338960";
const G0139_AUDIT_PATH: &str = "artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json";
const G0139_AUDIT_SHA256: &str = "282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f";
const G0139_AUDIT_COMMIT: &str = "0bfdbf2db065d8517ad2d98d762473fed052cb54";
const G0139_EVIDENCE_CLASS: &str = "T1_SAME_LINEAGE_OUTCOME_AWARE_RESULT_AUDIT";
const G0139_CLAIM_BOUNDARY: &str = "Consistency only for the exact committed 135-term Stage-C member and exact G-0135 Stage-D result bytes. Same-lineage outcome-aware T1 evidence; no T2 independence, family completeness, frozen-family nonmembership, MAX11 lower bound, unrestricted nonrepresentability, all-n theorem, refereed status, formalization, or Lean theorem.";
const G0140_MANIFEST_PATH: &str = "artifacts/math/G-0140/pool128_manifest_v1.json";
const OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_global_replay_v1.json";
const STAGE_B_OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_coordinate_prices_v1.json";
const STAGE_C_OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json";
const STAGE_D_OUTPUT_PATH: &str = "artifacts/math/G-0140/rank_aware_master_result_v1.json";
const STAGE_E_OUTPUT_PATH: &str = "artifacts/math/G-0140/new_member_global_replay_v1.json";
const STAGE_A_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0146-g0140-stage-a-final-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_A_SOURCE_AUDIT_SCHEMA: &str = "max11-g0146-g0140-stage-a-final-source-audit-v1";
const SOURCE_CUSTODY_PASS_RESULT: &str = "SOURCE_CUSTODY_AUDIT_PASS_T1";
const STAGE_A_SOURCE_AUDIT_EVIDENCE_CLASS: &str = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT";
const STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen Stage-A producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.";
const PRIOR_MASTER_RESULT_PATH: &str = "artifacts/math/G-0128/full_family_master_result_v2.json";
const PRIOR_MASTER_MANIFEST_PATH: &str =
    "artifacts/math/G-0128/full_family_master_manifest_v2.json";
const PRIOR_MASTER_SOURCE_PATH: &str = "artifacts/math/G-0128/full_family_master_v2.py";
const EXACT_Q_CORE_PATH: &str = "artifacts/math/G-0117/fresh_q_cegis_exact.py";

const PREREGISTRATION_PATH: &str = "artifacts/math/G-0140/PREREGISTRATION.md";
const ANCESTOR_PREREGISTRATION_PATH: &str = "artifacts/math/G-0135/PREREGISTRATION.md";
const PRODUCER_SOURCE_PATH: &str = "artifacts/math/G-0140/stage_a_pool/src/main.rs";
const PRODUCER_ENGINE_PATH: &str = "artifacts/math/G-0140/stage_a_pool/src/engine.rs";
const PRODUCER_CARGO_PATH: &str = "artifacts/math/G-0140/stage_a_pool/Cargo.toml";
const PRODUCER_LOCK_PATH: &str = "artifacts/math/G-0140/stage_a_pool/Cargo.lock";
const PRODUCER_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0140/stage_a_pool/target/release/g0140-stage-a-pool128-global-replay";
const STAGE_A_SOURCE_PATH: &str = "artifacts/math/G-0135/src/main.rs";
const STAGE_A_CARGO_PATH: &str = "artifacts/math/G-0135/Cargo.toml";
const STAGE_A_LOCK_PATH: &str = "artifacts/math/G-0135/Cargo.lock";
const STAGE_A_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0135/target/release/g0135-batch32-global-replay";
const STAGE_B_SOURCE_PATH: &str = "artifacts/math/G-0135/stage_b_pricer/src/main.rs";
const STAGE_B_CARGO_PATH: &str = "artifacts/math/G-0135/stage_b_pricer/Cargo.toml";
const STAGE_B_LOCK_PATH: &str = "artifacts/math/G-0135/stage_b_pricer/Cargo.lock";
const STAGE_B_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0135/stage_b_pricer/target/release/g0135-stage-b-batch32-coordinate-pricer";
const STAGE_C_SOURCE_PATH: &str = "artifacts/math/G-0135/stage_c_master/full_family_master_v3.py";
const STAGE_C_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0135/stage_c_master/run-full-family-master-v3";
const STAGE_D_SOURCE_PATH: &str = "artifacts/math/G-0135/stage_d_global_replay/src/main.rs";
const STAGE_D_ENGINE_PATH: &str = "artifacts/math/G-0135/stage_d_global_replay/src/engine.rs";
const STAGE_D_CARGO_PATH: &str = "artifacts/math/G-0135/stage_d_global_replay/Cargo.toml";
const STAGE_D_LOCK_PATH: &str = "artifacts/math/G-0135/stage_d_global_replay/Cargo.lock";
const STAGE_D_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0135/stage_d_global_replay/target/release/g0135-stage-d-global-replay";
const KERNEL_PATH: &str = "artifacts/math/G-0117/src/lib.rs";
const UNIQUENESS_PATH: &str = "artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md";

const STAGE_A_AUDIT_PATH: &str = "artifacts/reviews/G-0136-g0135-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_BC_AUDIT_PATH: &str =
    "artifacts/reviews/G-0137-g0135-stages-bc-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_D_AUDIT_PATH: &str =
    "artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_D_AUDIT_SHA256: &str =
    "f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944";

const MANIFEST_SCHEMA: &str = "max11-g0135-batch32-global-replay-manifest-v1";
const STAGE_A_SCHEMA: &str = "max11-g0135-batch32-global-replay-v1";
const STAGE_B_SCHEMA: &str = "max11-g0135-batch32-coordinate-prices-v1";
const STAGE_C_SCHEMA: &str = "max11-g0135-full-family-master-result-v3";
const STAGE_C_MEMBER: &str = "FULL_FAMILY_412ROW_EXACT_Q_MEMBER";
const ANCESTOR_STAGE_D_SCHEMA: &str = "max11-g0135-new-member-global-replay-v1";
const G0140_MANIFEST_SCHEMA: &str = "max11-g0140-rank-aware-manifest-v1";
const OUTPUT_SCHEMA: &str = "max11-g0140-pool128-global-replay-v1";
const STAGE_B_OUTPUT_SCHEMA: &str = "max11-g0140-pool128-coordinate-prices-v1";
const STAGE_C_OUTPUT_SCHEMA: &str = "max11-g0140-pool128-exact-rank-selection-v1";
const STAGE_D_OUTPUT_SCHEMA: &str = "max11-g0140-rank-aware-master-result-v1";
const STAGE_E_OUTPUT_SCHEMA: &str = "max11-g0140-new-member-global-replay-v1";
const ZERO_RESULT: &str = "GLOBAL_EXACT_ZERO";
const ANCESTOR_RESIDUAL_RESULT: &str = "EXACT_RESIDUAL_BATCH_CONTINUE";
const RESIDUAL_RESULT: &str = "EXACT_RESIDUAL_POOL128";
const DECISION_RULE: &str = "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate";
const CLAIM_BOUNDARY: &str = "This receipt reproduces the already-known nonzero complete ordered-chamber normal form of the frozen G-0135 135-term member and emits its deterministic first 128 eligible residual directions. It refutes only that member and is input to a separately certified rank-selection study; it proves neither family completeness nor an unrestricted theorem, lower bound, minimality, all-n target, or Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_ENGINE: &[u8] = include_bytes!("engine.rs");
const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../../PREREGISTRATION.md");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../../G-0117/src/lib.rs");
const COMPILED_UNIQUENESS: &[u8] =
    include_bytes!("../../../G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md");
const COMPILED_G0139_AUDIT: &[u8] =
    include_bytes!("../../../../reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json");

const REQUIRED_MANIFEST_PATHS: &[&str] = &[
    ANCESTOR_PREREGISTRATION_PATH,
    PANEL_INPUT_PATH,
    PANEL_CACHE_PATH,
    PANEL_CACHE_MANIFEST_PATH,
    PRIOR_MASTER_RESULT_PATH,
    PRIOR_MASTER_MANIFEST_PATH,
    PRIOR_MASTER_SOURCE_PATH,
    EXACT_Q_CORE_PATH,
    STAGE_A_SOURCE_PATH,
    STAGE_A_CARGO_PATH,
    STAGE_A_LOCK_PATH,
    STAGE_A_EXECUTABLE_PATH,
    STAGE_B_SOURCE_PATH,
    STAGE_B_CARGO_PATH,
    STAGE_B_LOCK_PATH,
    STAGE_B_EXECUTABLE_PATH,
    STAGE_C_SOURCE_PATH,
    STAGE_C_EXECUTABLE_PATH,
    STAGE_D_SOURCE_PATH,
    STAGE_D_ENGINE_PATH,
    STAGE_D_CARGO_PATH,
    STAGE_D_LOCK_PATH,
    KERNEL_PATH,
    UNIQUENESS_PATH,
    STAGE_A_AUDIT_PATH,
    STAGE_BC_AUDIT_PATH,
    STAGE_D_AUDIT_PATH,
];

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Binding {
    path: String,
    sha256: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ManifestParameters {
    n: usize,
    rows: usize,
    records: usize,
    terms: usize,
    batch_k: usize,
    selected_slots: usize,
    carry_directions: usize,
    target_coordinate: usize,
    labelled_permutations: u64,
    threads: usize,
    arithmetic: String,
    decision_rule: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ManifestEnvironment {
    os: String,
    arch: String,
    rustc_verbose: String,
    available_parallelism: usize,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct PlannedOutput {
    path: String,
    schema: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StudyManifest {
    schema: String,
    selected_branch: String,
    output_path: String,
    preregistration_git_commit: String,
    producer_git_commit: String,
    source_audit_git_commit: String,
    bindings: BTreeMap<String, Binding>,
    transitive_inputs: Vec<Binding>,
    parameters: ManifestParameters,
    environment: ManifestEnvironment,
    stage_order: Vec<String>,
    planned_outputs: BTreeMap<String, PlannedOutput>,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct G0140Parameters {
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

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct G0140Manifest {
    schema: String,
    selected_branch: String,
    preregistration_git_commit: String,
    producer_git_commit: String,
    source_audit_git_commit: String,
    bindings: BTreeMap<String, Binding>,
    transitive_inputs: Vec<Binding>,
    parameters: G0140Parameters,
    stage_order: Vec<String>,
    planned_outputs: BTreeMap<String, PlannedOutput>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PanelInput {
    schema: String,
    control_sequences: Vec<usize>,
    primes: [u64; 2],
    records: Vec<Record>,
    rows_path: String,
    target: Vec<i64>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Term {
    sequence: usize,
    coefficient: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SupportReceipt {
    selected_columns: usize,
    support_columns: usize,
    support_is_exact_pivot_basis: bool,
    selected_sequences_u64le_sha256: String,
    support_sequences_u64le_sha256: String,
    term_support_u64le_sha256: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayReceipt {
    rows: usize,
    rational_all_rows_replayed: bool,
    rational_lhs_lf_sha256: String,
    primitive_denominator_clearing: bool,
    integer_all_rows_replayed: bool,
    integer_residuals_decimal_lf_sha256: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CoefficientMutantReceipt {
    support_index: usize,
    sequence: usize,
    coefficient_delta: String,
    first_nonzero_residual_row: usize,
    residuals_decimal_lf_sha256: String,
    rejected: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageCMember {
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
    target_scale: String,
    integer_coefficients: Vec<String>,
    integer_coefficients_decimal_lf_sha256: String,
    terms: Vec<Term>,
    support_receipt: SupportReceipt,
    replay_receipt: ReplayReceipt,
    coefficient_plus_one_mutant: CoefficientMutantReceipt,
    prior_target_scale_carryover_mutant_rejected: bool,
    trials: Vec<Value>,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageACarry {
    index: usize,
    direction: [i8; N],
    coefficient: String,
    exact_zero: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Clone, Debug, Deserialize)]
struct StageAReceipt {
    schema: String,
    result: String,
    manifest_path: String,
    manifest_sha256: String,
    complete_global_replay: bool,
    all_hinge_and_linear_residuals_zero: bool,
    carry_forward_checks: Vec<StageACarry>,
    first_carry_forward_failure: Option<usize>,
    linear_residuals_after_target: Vec<String>,
    batch_k: usize,
    selected_count: usize,
    selected_directions_i8_sha256: String,
    selected_exact_residuals_decimal_lf_sha256: String,
    selected: Vec<ExactHinge>,
    inputs_rehashed_at_end: bool,
}

#[derive(Clone, Debug, Deserialize)]
struct StageBReceipt {
    schema: String,
    result: String,
    manifest_path: String,
    manifest_sha256: String,
    stage_a_receipt: Binding,
    candidate: Binding,
    batch_k: usize,
    records: usize,
    hinge_entries: usize,
    selected_count: usize,
    selected_directions_i8_sha256: String,
    selected_exact_residuals_decimal_lf_sha256: String,
    directions: Vec<[i8; N]>,
    direction_major_hinge_i64_le_sha256: String,
    exact_candidate_dots_decimal_lf_sha256: String,
    exact_candidate_dots: Vec<String>,
    rows: Vec<Value>,
    inputs_rehashed_at_end: bool,
}

#[derive(Clone, Debug)]
struct ManifestSnapshot {
    sha256: String,
    bindings_by_path: BTreeMap<String, String>,
}

#[derive(Default)]
struct ExactAggregate {
    hinges: HashMap<[i8; N], BigInt>,
    linear: [BigInt; N],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    term_receipts: Vec<TermNormalFormReceipt>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
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

#[derive(Clone, Debug, Serialize)]
struct AccumulatedDirectionCheck {
    index: usize,
    source: &'static str,
    source_index: usize,
    direction: [i8; N],
    aggregate_coefficient: String,
    direct_dp_coefficient: String,
    routes_agree: bool,
    exact_zero: bool,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
struct ExactLinear {
    coordinate: usize,
    coefficient: String,
}

#[derive(Clone, Debug, Serialize)]
struct MutationControl {
    name: &'static str,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
    baseline_complete_residual_sha256: String,
    mutated_complete_residual_sha256: String,
    changed_from_baseline: bool,
    detected: bool,
}

#[derive(Clone, Debug, Serialize)]
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

#[derive(Clone, Debug, Serialize)]
struct SelectionControls {
    exact_batch_count_or_zero_terminal: bool,
    strict_signed_lexicographic_order: bool,
    excludes_accumulated_directions: bool,
    direction_reordering_changes_digest: bool,
    coefficient_plus_one_changes_digest: bool,
}

#[derive(Clone, Debug, Serialize)]
struct FiniteCoefficientMutant {
    sequence: usize,
    coefficient_delta: &'static str,
    first_nonzero_residual_row: usize,
    residuals_decimal_lf_sha256: String,
    rejected: bool,
}

#[derive(Clone, Debug, Serialize)]
struct FiniteReplayReceipt {
    rows: usize,
    panel_rows: usize,
    linear_rows: usize,
    accumulated_hinge_rows: usize,
    cache_layout: &'static str,
    arithmetic: &'static str,
    all_rows_exactly_replayed: bool,
    residuals_decimal_lf_sha256: String,
    coefficient_plus_one_mutant: FiniteCoefficientMutant,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
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
    arithmetic: &'static str,
    decision_rule: &'static str,
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
    term_normal_forms: Vec<TermNormalFormReceipt>,
    accumulated_direction_checks: Vec<AccumulatedDirectionCheck>,
    all_100_accumulated_directions_exact_zero: bool,
    linear_residuals_after_target: Vec<String>,
    all_11_linear_residuals_exact_zero: bool,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
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

fn is_sha256(value: &str) -> bool {
    value.len() == 64
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

fn bigint_abs(value: BigInt) -> BigInt {
    if value < BigInt::from(0) {
        -value
    } else {
        value
    }
}

fn bigint_gcd(mut left: BigInt, mut right: BigInt) -> BigInt {
    left = bigint_abs(left);
    right = bigint_abs(right);
    while right != BigInt::from(0) {
        let remainder = &left % &right;
        left = right;
        right = remainder;
    }
    left
}

fn parse_rational(raw: &str) -> Result<(BigInt, BigInt)> {
    let mut pieces = raw.split('/');
    let numerator_raw = pieces.next().context("missing rational numerator")?;
    let denominator_raw = pieces.next();
    ensure!(pieces.next().is_none(), "multiple rational separators");
    let numerator = parse_bigint(numerator_raw)?;
    let denominator = match denominator_raw {
        None => BigInt::from(1),
        Some(value) => {
            ensure!(
                canonical_positive_integer(value),
                "invalid rational denominator"
            );
            let parsed = parse_bigint(value)?;
            ensure!(parsed > BigInt::from(1), "noncanonical denominator /1");
            parsed
        }
    };
    ensure!(
        bigint_gcd(numerator.clone(), denominator.clone()) == BigInt::from(1),
        "rational is not reduced"
    );
    Ok((numerator, denominator))
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

fn binding_matches(root: &Path, binding: &Binding, path: &str) -> Result<()> {
    ensure!(binding.path == path, "binding path drift: {path}");
    ensure!(
        is_sha256(&binding.sha256),
        "binding digest malformed: {path}"
    );
    ensure!(
        sha256_path(&checked_repo_path(root, path)?)? == binding.sha256,
        "binding digest drift: {path}"
    );
    Ok(())
}

fn binding_for_path(root: &Path, path: &str) -> Result<Binding> {
    Ok(Binding {
        path: path.to_string(),
        sha256: sha256_path(&checked_repo_path(root, path)?)?,
    })
}

fn git_commit_for_path(root: &Path, path: &str) -> Result<String> {
    let output = Command::new("git")
        .args(["log", "-1", "--format=%H", "--", path])
        .current_dir(root)
        .output()?;
    ensure!(
        output.status.success(),
        "git commit lookup failed for {path}"
    );
    let commit = String::from_utf8(output.stdout)?.trim().to_string();
    ensure!(
        commit.len() == 40 && commit.bytes().all(|byte| byte.is_ascii_hexdigit()),
        "uncommitted or invalid binding: {path}"
    );
    let blob = Command::new("git")
        .args(["show", &format!("{commit}:{path}")])
        .current_dir(root)
        .output()?;
    ensure!(blob.status.success(), "git blob lookup failed for {path}");
    ensure!(
        sha256_bytes(&blob.stdout) == sha256_path(&checked_repo_path(root, path)?)?,
        "working bytes differ from committed binding: {path}"
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
        let _ = File::open(parent).and_then(|directory| directory.sync_all());
        return Err(error).context("remove exclusive temporary output link");
    }
    if let Err(error) = File::open(parent).and_then(|directory| directory.sync_all()) {
        let _ = std::fs::remove_file(path);
        let _ = File::open(parent).and_then(|directory| directory.sync_all());
        return Err(error).context("directory fsync after atomic publication");
    }
    Ok(())
}

fn u64le_digest(values: impl IntoIterator<Item = usize>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((value as u64).to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn i128le_digest(values: impl IntoIterator<Item = i64>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(i128::from(value).to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn decimal_lf_digest<'a>(values: impl IntoIterator<Item = &'a str>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn integer_lf_digest(values: impl IntoIterator<Item = i64>) -> String {
    let rendered = values
        .into_iter()
        .map(|value| value.to_string())
        .collect::<Vec<_>>();
    decimal_lf_digest(rendered.iter().map(String::as_str))
}

fn zero_lf_digest(count: usize) -> String {
    let mut digest = Sha256::new();
    for _ in 0..count {
        digest.update(b"0\n");
    }
    format!("{:x}", digest.finalize())
}

fn selected_direction_digest(selected: &[ExactHinge]) -> String {
    let mut digest = Sha256::new();
    for item in selected {
        for coordinate in item.direction {
            digest.update([coordinate as u8]);
        }
    }
    format!("{:x}", digest.finalize())
}

fn selected_residual_digest(selected: &[ExactHinge]) -> String {
    decimal_lf_digest(selected.iter().map(|item| item.coefficient.as_str()))
}

fn validate_strict_axis(values: &[usize], upper: usize, name: &str) -> Result<()> {
    ensure!(!values.is_empty(), "{name} is empty");
    ensure!(
        values.windows(2).all(|pair| pair[0] < pair[1]),
        "{name} is not strictly increasing"
    );
    ensure!(
        values.last().is_some_and(|value| *value < upper),
        "{name} outside range"
    );
    Ok(())
}

fn nonzero_term_projection(sequences: &[usize], coefficients: &[String]) -> Result<Vec<Term>> {
    ensure!(
        sequences.len() == coefficients.len(),
        "support/coefficient census drift"
    );
    ensure!(
        coefficients.iter().all(|value| canonical_integer(value)),
        "noncanonical support coefficient"
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

fn value_string<'a>(value: &'a Value, pointer: &str) -> Result<&'a str> {
    value
        .pointer(pointer)
        .and_then(Value::as_str)
        .with_context(|| format!("missing string at {pointer}"))
}

fn value_u64(value: &Value, pointer: &str) -> Result<u64> {
    value
        .pointer(pointer)
        .and_then(Value::as_u64)
        .with_context(|| format!("missing integer at {pointer}"))
}

fn value_bool(value: &Value, pointer: &str) -> Result<bool> {
    value
        .pointer(pointer)
        .and_then(Value::as_bool)
        .with_context(|| format!("missing boolean at {pointer}"))
}

fn validate_ancestor_stage_d(root: &Path) -> Result<Vec<ExactHinge>> {
    let path = checked_repo_path(root, ANCESTOR_STAGE_D_RESULT_PATH)?;
    ensure!(
        sha256_path(&path)? == ANCESTOR_STAGE_D_RESULT_SHA256,
        "G-0135 Stage-D result digest drift"
    );
    ensure!(
        git_commit_for_path(root, ANCESTOR_STAGE_D_RESULT_PATH)? == ANCESTOR_STAGE_D_COMMIT,
        "G-0135 Stage-D result commit drift"
    );
    let receipt = strict_json_value(BufReader::new(File::open(path)?))?;
    let first: ExactHinge = serde_json::from_value(
        receipt
            .pointer("/first_nonzero_hinge")
            .context("G-0135 first nonzero hinge missing")?
            .clone(),
    )?;
    let selected: Vec<ExactHinge> = serde_json::from_value(
        receipt
            .pointer("/next_selected")
            .context("G-0135 next-selected batch missing")?
            .clone(),
    )?;
    ensure!(
        value_string(&receipt, "/schema")? == ANCESTOR_STAGE_D_SCHEMA
            && value_string(&receipt, "/result")? == ANCESTOR_RESIDUAL_RESULT
            && value_u64(&receipt, "/terms")? == 135
            && value_u64(&receipt, "/labelled_permutations_expected")? == 5_388_768_000
            && value_u64(&receipt, "/labelled_permutations_checked")? == 5_388_768_000
            && value_u64(&receipt, "/hinge_entries_processed")? == 4_409_740
            && value_u64(&receipt, "/aggregate_hinge_support")? == 147_062
            && value_u64(&receipt, "/nonzero_hinge_directions")? == 146_950
            && value_string(&receipt, "/aggregate_hinge_decimal_lf_sha256")?
                == ANCESTOR_AGGREGATE_HINGE_SHA256
            && value_string(&receipt, "/nonzero_hinge_decimal_lf_sha256")?
                == ANCESTOR_NONZERO_HINGE_SHA256
            && value_string(&receipt, "/complete_residual_decimal_lf_sha256")?
                == ANCESTOR_COMPLETE_RESIDUAL_SHA256
            && value_string(&receipt, "/term_normal_form_transcript_sha256")?
                == ANCESTOR_TERM_TRANSCRIPT_SHA256
            && value_bool(&receipt, "/all_100_accumulated_directions_exact_zero")?
            && value_bool(&receipt, "/all_11_linear_residuals_exact_zero")?
            && first.direction == ANCESTOR_FIRST_DIRECTION
            && first.coefficient == ANCESTOR_FIRST_COEFFICIENT
            && selected.len() == ANCESTOR_BATCH_K
            && selected_direction_digest(&selected) == ANCESTOR_FIRST32_DIRECTIONS_SHA256
            && selected_residual_digest(&selected) == ANCESTOR_FIRST32_RESIDUALS_SHA256
            && value_string(&receipt, "/next_selected_directions_i8_sha256")?
                == ANCESTOR_FIRST32_DIRECTIONS_SHA256
            && value_string(&receipt, "/next_selected_exact_residuals_decimal_lf_sha256",)?
                == ANCESTOR_FIRST32_RESIDUALS_SHA256,
        "G-0135 Stage-D disclosed anchor drift"
    );
    Ok(selected)
}

fn validate_g0139_semantics(receipt: &Value) -> Result<()> {
    let custody = receipt
        .pointer("/input_custody")
        .and_then(Value::as_object)
        .context("G-0139 input-custody object missing")?;
    let fixed = custody
        .get("fixed_inputs")
        .and_then(Value::as_object)
        .context("G-0139 fixed-input map missing")?;
    let transitive = custody
        .get("transitive_bound_inputs")
        .and_then(Value::as_object)
        .context("G-0139 transitive-input map missing")?;
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
                == ANCESTOR_RESIDUAL_RESULT
            && value_string(receipt, "/git_custody/subject_commit")? == ANCESTOR_STAGE_D_COMMIT
            && value_bool(receipt, "/git_custody/strict_linear_ancestry")?
            && value_string(receipt, "/source_audit_anchor/path")? == STAGE_D_AUDIT_PATH
            && value_string(receipt, "/source_audit_anchor/sha256")? == STAGE_D_AUDIT_SHA256
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
            && value_u64(receipt, "/input_custody/fixed_input_count")? == fixed.len() as u64
            && fixed.len() == 8
            && fixed
                .get(ANCESTOR_STAGE_D_RESULT_PATH)
                .and_then(Value::as_str)
                == Some(ANCESTOR_STAGE_D_RESULT_SHA256)
            && fixed.get(STAGE_D_AUDIT_PATH).and_then(Value::as_str) == Some(STAGE_D_AUDIT_SHA256)
            && value_u64(receipt, "/input_custody/transitive_bound_input_count")?
                == transitive.len() as u64
            && transitive.len() == 92,
        "G-0139 semantic/custody admission drift"
    );
    Ok(())
}

fn validate_g0139_gate(root: &Path) -> Result<Binding> {
    let path = checked_repo_path(root, G0139_AUDIT_PATH)?;
    let sha256 = sha256_path(&path)?;
    ensure!(sha256 == G0139_AUDIT_SHA256, "G-0139 receipt digest drift");
    ensure!(
        git_commit_for_path(root, G0139_AUDIT_PATH)? == G0139_AUDIT_COMMIT,
        "G-0139 receipt commit drift"
    );
    let receipt = strict_json_value(BufReader::new(File::open(path)?))?;
    validate_g0139_semantics(&receipt)?;
    let mut nested = Vec::new();
    collect_recursive_bindings(&receipt, &mut nested);
    ensure!(
        nested.iter().any(|binding| {
            binding.path == ANCESTOR_STAGE_D_RESULT_PATH
                && binding.sha256 == ANCESTOR_STAGE_D_RESULT_SHA256
        }),
        "G-0139 PASS does not bind the exact G-0135 Stage-D subject"
    );
    Ok(Binding {
        path: G0139_AUDIT_PATH.to_string(),
        sha256,
    })
}

fn validate_current_release_executable(root: &Path) -> Result<Binding> {
    let executable = std::env::current_exe()?.canonicalize()?;
    let expected = root.join(PRODUCER_EXECUTABLE_PATH).canonicalize()?;
    ensure!(
        executable == expected,
        "scientific preflight/run requires the frozen release executable"
    );
    git_commit_for_path(root, PRODUCER_EXECUTABLE_PATH)?;
    Ok(Binding {
        path: PRODUCER_EXECUTABLE_PATH.to_string(),
        sha256: sha256_path(&executable)?,
    })
}

fn parse_binding_value(value: &Value, label: &str) -> Result<Binding> {
    let object = value
        .as_object()
        .with_context(|| format!("{label} binding is not an object"))?;
    let path = object
        .get("path")
        .and_then(Value::as_str)
        .with_context(|| format!("{label} path missing"))?;
    let sha256 = object
        .get("sha256")
        .and_then(Value::as_str)
        .with_context(|| format!("{label} digest missing"))?;
    ensure!(is_sha256(sha256), "{label} digest malformed");
    Ok(Binding {
        path: path.to_string(),
        sha256: sha256.to_string(),
    })
}

fn collect_recursive_bindings(value: &Value, output: &mut Vec<Binding>) {
    match value {
        Value::Array(values) => {
            for value in values {
                collect_recursive_bindings(value, output);
            }
        }
        Value::Object(object) => {
            if let (Some(path), Some(sha256)) = (
                object.get("path").and_then(Value::as_str),
                object.get("sha256").and_then(Value::as_str),
            ) && is_sha256(sha256)
            {
                output.push(Binding {
                    path: path.to_string(),
                    sha256: sha256.to_string(),
                });
            }
            for value in object.values() {
                collect_recursive_bindings(value, output);
            }
        }
        _ => {}
    }
}

fn source_audit_contract(audit_path: &str) -> Result<(&'static str, Option<&'static str>)> {
    match audit_path {
        STAGE_A_AUDIT_PATH => Ok(("max11-g0136-g0135-source-audit-v1", None)),
        STAGE_BC_AUDIT_PATH => Ok(("max11-g0137-g0135-stages-bc-source-audit-v1", None)),
        STAGE_D_AUDIT_PATH => Ok(("max11-g0138-g0135-stage-d-source-audit-v1", None)),
        STAGE_A_SOURCE_AUDIT_PATH => Ok((
            STAGE_A_SOURCE_AUDIT_SCHEMA,
            Some(SOURCE_CUSTODY_PASS_RESULT),
        )),
        _ => anyhow::bail!("unknown source-audit contract: {audit_path}"),
    }
}

fn validate_source_audit_envelope(receipt: &Value, audit_path: &str) -> Result<()> {
    let (expected_schema, expected_result) = source_audit_contract(audit_path)?;
    let result_matches = match expected_result {
        Some(result) => value_string(receipt, "/result")? == result,
        None => true,
    };
    ensure!(
        value_string(receipt, "/schema")? == expected_schema
            && value_string(receipt, "/verdict")? == "PASS"
            && !value_bool(receipt, "/scientific_manifest_observed")?
            && !value_bool(receipt, "/scientific_output_observed")?
            && result_matches,
        "source audit is not the exact outcome-blind PASS contract for {audit_path}"
    );
    if audit_path == STAGE_A_SOURCE_AUDIT_PATH {
        ensure!(
            value_string(receipt, "/evidence_class")? == STAGE_A_SOURCE_AUDIT_EVIDENCE_CLASS
                && value_string(receipt, "/claim_boundary")? == STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY
                && !value_bool(receipt, "/scientific_input_observed")?
                && !value_bool(receipt, "/scientific_replay_run")?
                && value_bool(
                    receipt,
                    "/subject/commit_object_and_working_bytes_equal_for_all_bindings"
                )?,
            "final Stage-A source audit semantic boundary drift"
        );
    }
    Ok(())
}

fn validate_source_audit(
    root: &Path,
    manifest: &ManifestSnapshot,
    audit_path: &str,
    required_subject_paths: &[&str],
) -> Result<()> {
    let expected = manifest
        .bindings_by_path
        .get(audit_path)
        .with_context(|| format!("shared manifest omits audit receipt {audit_path}"))?;
    let path = checked_repo_path(root, audit_path)?;
    ensure!(
        sha256_path(&path)? == *expected,
        "audit receipt drift: {audit_path}"
    );
    let audit_commit = git_commit_for_path(root, audit_path)?;
    let receipt = strict_json_value(BufReader::new(File::open(path)?))?;
    validate_source_audit_envelope(&receipt, audit_path)?;
    if audit_path == STAGE_A_SOURCE_AUDIT_PATH {
        let subject_path = required_subject_paths
            .first()
            .context("final Stage-A audit subject path missing")?;
        ensure!(
            value_string(&receipt, "/subject/git_commit")?
                == git_commit_for_path(root, subject_path)?
                && value_string(&receipt, "/audit_git_commit")? == audit_commit,
            "final Stage-A audit Git identity drift"
        );
    }
    let mut observed = Vec::new();
    collect_recursive_bindings(&receipt, &mut observed);
    for required in required_subject_paths {
        let expected = manifest
            .bindings_by_path
            .get(*required)
            .with_context(|| format!("shared manifest omits audited subject {required}"))?;
        ensure!(
            observed
                .iter()
                .any(|binding| binding.path == *required && binding.sha256 == *expected),
            "source audit does not bind exact subject: {required}"
        );
    }
    for binding in observed {
        let resolved = checked_repo_path(root, &binding.path)?;
        ensure!(
            sha256_path(&resolved)? == binding.sha256,
            "source audit nested binding drift: {}",
            binding.path
        );
    }
    Ok(())
}

fn validate_compiled_bytes(root: &Path) -> Result<()> {
    for (compiled, path) in [
        (COMPILED_SOURCE, PRODUCER_SOURCE_PATH),
        (COMPILED_ENGINE, PRODUCER_ENGINE_PATH),
        (COMPILED_MANIFEST, PRODUCER_CARGO_PATH),
        (COMPILED_LOCK, PRODUCER_LOCK_PATH),
        (COMPILED_PREREGISTRATION, PREREGISTRATION_PATH),
        (COMPILED_KERNEL, KERNEL_PATH),
        (COMPILED_UNIQUENESS, UNIQUENESS_PATH),
        (COMPILED_G0139_AUDIT, G0139_AUDIT_PATH),
    ] {
        ensure!(
            sha256_bytes(compiled) == sha256_path(&checked_repo_path(root, path)?)?,
            "running binary was compiled against different bytes: {path}"
        );
    }
    Ok(())
}

fn validate_shared_manifest(root: &Path) -> Result<ManifestSnapshot> {
    let manifest_path = checked_repo_path(root, SHARED_MANIFEST_PATH)?;
    let sha256 = sha256_path(&manifest_path)?;
    let manifest: StudyManifest = strict_json(BufReader::new(File::open(manifest_path)?))?;
    ensure!(
        manifest.schema == MANIFEST_SCHEMA
            && manifest.selected_branch == "MEMBER"
            && manifest.output_path == STAGE_A_RECEIPT_PATH
            && manifest.preregistration_git_commit.len() == 40
            && manifest.producer_git_commit.len() == 40
            && manifest.source_audit_git_commit.len() == 40
            && [
                &manifest.preregistration_git_commit,
                &manifest.producer_git_commit,
                &manifest.source_audit_git_commit,
            ]
            .iter()
            .all(|commit| commit.bytes().all(|byte| byte.is_ascii_hexdigit())),
        "shared manifest identity drift"
    );
    ensure!(
        manifest.stage_order
            == [
                "A_REPLAY_SELECT",
                "B_PRICE",
                "C_MASTER",
                "D_GLOBAL_REPLAY_IF_MEMBER",
            ],
        "shared manifest stage order drift"
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
                path: STAGE_B_RECEIPT_PATH.to_string(),
                schema: STAGE_B_SCHEMA.to_string(),
            },
        ),
        (
            "C".to_string(),
            PlannedOutput {
                path: STAGE_C_RESULT_PATH.to_string(),
                schema: STAGE_C_SCHEMA.to_string(),
            },
        ),
        (
            "D".to_string(),
            PlannedOutput {
                path: ANCESTOR_STAGE_D_RESULT_PATH.to_string(),
                schema: ANCESTOR_STAGE_D_SCHEMA.to_string(),
            },
        ),
    ]);
    ensure!(
        manifest.planned_outputs == expected_outputs,
        "shared manifest planned-output contract drift"
    );
    ensure!(
        manifest.parameters.n == N
            && manifest.parameters.rows == OLD_ROWS
            && manifest.parameters.records == RECORDS
            && manifest.parameters.terms == 132
            && manifest.parameters.batch_k == ANCESTOR_BATCH_K
            && manifest.parameters.selected_slots == 176
            && manifest.parameters.carry_directions == OLD_CARRY_DIRECTIONS
            && manifest.parameters.target_coordinate == N - 1
            && manifest.parameters.labelled_permutations == 132 * factorial(N)
            && manifest.parameters.threads == THREADS
            && manifest.parameters.arithmetic == "signed_num_bigint_BigInt_unconditional_exact"
            && manifest.parameters.decision_rule == DECISION_RULE
            && !manifest.environment.os.is_empty()
            && !manifest.environment.arch.is_empty()
            && !manifest.environment.rustc_verbose.is_empty()
            && manifest.environment.available_parallelism > 0,
        "shared manifest parameter/environment drift"
    );

    let mut bindings_by_path = BTreeMap::new();
    for (label, binding) in &manifest.bindings {
        ensure!(
            is_sha256(&binding.sha256),
            "malformed manifest binding: {label}"
        );
        ensure!(
            bindings_by_path
                .insert(binding.path.clone(), binding.sha256.clone())
                .is_none(),
            "duplicate manifest-bound path: {}",
            binding.path
        );
    }
    for (index, binding) in manifest.transitive_inputs.iter().enumerate() {
        ensure!(
            is_sha256(&binding.sha256),
            "malformed manifest transitive binding {index}"
        );
        ensure!(
            bindings_by_path
                .insert(binding.path.clone(), binding.sha256.clone())
                .is_none(),
            "duplicate manifest/transitive path: {}",
            binding.path
        );
    }

    let executable = STAGE_D_EXECUTABLE_PATH;
    for required in REQUIRED_MANIFEST_PATHS
        .iter()
        .copied()
        .chain(std::iter::once(executable))
    {
        ensure!(
            bindings_by_path.contains_key(required),
            "shared manifest omits required Stage-D custody path: {required}"
        );
    }
    for (path, expected) in &bindings_by_path {
        ensure!(is_sha256(expected), "manifest digest malformed: {path}");
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "manifest-bound input drift: {path}"
        );
    }
    for source in [
        SHARED_MANIFEST_PATH,
        STAGE_A_SOURCE_PATH,
        STAGE_A_CARGO_PATH,
        STAGE_A_LOCK_PATH,
        STAGE_A_EXECUTABLE_PATH,
        STAGE_B_SOURCE_PATH,
        STAGE_B_CARGO_PATH,
        STAGE_B_LOCK_PATH,
        STAGE_B_EXECUTABLE_PATH,
        STAGE_C_SOURCE_PATH,
        STAGE_C_EXECUTABLE_PATH,
        STAGE_D_SOURCE_PATH,
        STAGE_D_ENGINE_PATH,
        STAGE_D_CARGO_PATH,
        STAGE_D_LOCK_PATH,
        executable,
        STAGE_A_AUDIT_PATH,
        STAGE_BC_AUDIT_PATH,
        STAGE_D_AUDIT_PATH,
    ] {
        git_commit_for_path(root, source)?;
    }
    ensure!(
        manifest.preregistration_git_commit
            == git_commit_for_path(root, ANCESTOR_PREREGISTRATION_PATH)?
            && manifest.producer_git_commit == git_commit_for_path(root, STAGE_A_SOURCE_PATH)?
            && manifest.source_audit_git_commit == git_commit_for_path(root, STAGE_A_AUDIT_PATH)?,
        "shared manifest Git ancestry drift"
    );
    let snapshot = ManifestSnapshot {
        sha256,
        bindings_by_path,
    };
    validate_source_audit(
        root,
        &snapshot,
        STAGE_A_AUDIT_PATH,
        &[
            STAGE_A_SOURCE_PATH,
            STAGE_A_CARGO_PATH,
            STAGE_A_LOCK_PATH,
            STAGE_A_EXECUTABLE_PATH,
        ],
    )?;
    validate_source_audit(
        root,
        &snapshot,
        STAGE_BC_AUDIT_PATH,
        &[
            STAGE_B_SOURCE_PATH,
            STAGE_B_CARGO_PATH,
            STAGE_B_LOCK_PATH,
            STAGE_B_EXECUTABLE_PATH,
            STAGE_C_SOURCE_PATH,
            STAGE_C_EXECUTABLE_PATH,
        ],
    )?;
    validate_source_audit(
        root,
        &snapshot,
        STAGE_D_AUDIT_PATH,
        &[
            STAGE_D_SOURCE_PATH,
            STAGE_D_ENGINE_PATH,
            STAGE_D_CARGO_PATH,
            STAGE_D_LOCK_PATH,
            executable,
        ],
    )?;
    Ok(snapshot)
}

fn validate_g0140_manifest(root: &Path) -> Result<ManifestSnapshot> {
    let manifest_path = checked_repo_path(root, G0140_MANIFEST_PATH)?;
    git_commit_for_path(root, G0140_MANIFEST_PATH)?;
    let sha256 = sha256_path(&manifest_path)?;
    let manifest: G0140Manifest = strict_json(BufReader::new(File::open(manifest_path)?))?;
    let commits = [
        &manifest.preregistration_git_commit,
        &manifest.producer_git_commit,
        &manifest.source_audit_git_commit,
    ];
    ensure!(
        manifest.schema == G0140_MANIFEST_SCHEMA
            && manifest.selected_branch == "G0135_EXACT_RESIDUAL_POOL128"
            && commits.iter().all(|commit| {
                commit.len() == 40 && commit.bytes().all(|byte| byte.is_ascii_hexdigit())
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
            == G0140Parameters {
                n: N,
                records: RECORDS,
                existing_rows: ROWS,
                existing_terms: 135,
                accumulated_hinge_rows: CARRY_DIRECTIONS,
                pool_k: BATCH_K,
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
                path: OUTPUT_PATH.to_string(),
                schema: OUTPUT_SCHEMA.to_string(),
            },
        ),
        (
            "B".to_string(),
            PlannedOutput {
                path: STAGE_B_OUTPUT_PATH.to_string(),
                schema: STAGE_B_OUTPUT_SCHEMA.to_string(),
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
                && is_sha256(&binding.sha256)
                && bindings_by_path
                    .insert(binding.path.clone(), binding.sha256.clone())
                    .is_none(),
            "duplicate/malformed G-0140 binding: {label}"
        );
    }
    for binding in &manifest.transitive_inputs {
        ensure!(
            is_sha256(&binding.sha256)
                && bindings_by_path
                    .insert(binding.path.clone(), binding.sha256.clone())
                    .is_none(),
            "duplicate/malformed G-0140 transitive binding: {}",
            binding.path
        );
    }
    for required in [
        PREREGISTRATION_PATH,
        PRODUCER_SOURCE_PATH,
        PRODUCER_ENGINE_PATH,
        PRODUCER_CARGO_PATH,
        PRODUCER_LOCK_PATH,
        PRODUCER_EXECUTABLE_PATH,
        STAGE_A_SOURCE_AUDIT_PATH,
        G0139_AUDIT_PATH,
        ANCESTOR_STAGE_D_RESULT_PATH,
        STAGE_C_RESULT_PATH,
        SHARED_MANIFEST_PATH,
        PANEL_INPUT_PATH,
        PANEL_CACHE_PATH,
        PANEL_CACHE_MANIFEST_PATH,
        KERNEL_PATH,
        UNIQUENESS_PATH,
    ] {
        ensure!(
            bindings_by_path.contains_key(required),
            "G-0140 manifest omits required Stage-A path: {required}"
        );
    }
    for (path, expected) in &bindings_by_path {
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "G-0140 manifest-bound input drift: {path}"
        );
    }
    ensure!(
        manifest.preregistration_git_commit == git_commit_for_path(root, PREREGISTRATION_PATH)?
            && manifest.producer_git_commit == git_commit_for_path(root, PRODUCER_SOURCE_PATH)?
            && manifest.source_audit_git_commit
                == git_commit_for_path(root, STAGE_A_SOURCE_AUDIT_PATH)?,
        "G-0140 manifest Git commit drift"
    );
    let snapshot = ManifestSnapshot {
        sha256,
        bindings_by_path,
    };
    validate_source_audit(
        root,
        &snapshot,
        STAGE_A_SOURCE_AUDIT_PATH,
        &[
            PRODUCER_SOURCE_PATH,
            PRODUCER_ENGINE_PATH,
            PRODUCER_CARGO_PATH,
            PRODUCER_LOCK_PATH,
            PRODUCER_EXECUTABLE_PATH,
        ],
    )?;
    let g0139 = validate_g0139_gate(root)?;
    ensure!(
        snapshot.bindings_by_path.get(G0139_AUDIT_PATH) == Some(&g0139.sha256),
        "G-0140 manifest does not bind the admitted G-0139 PASS"
    );
    Ok(snapshot)
}

fn validate_panel(input: &PanelInput) -> Result<()> {
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1"
            && input.control_sequences == [0, 1, 284, 5_341, 30_223, 133_449, 134_301]
            && input.primes == [2_000_081, 3_000_017]
            && input.rows_path == "artifacts/math/G-0111/dual_rows_v1.json"
            && input.target.len() == 301,
        "panel-input metadata drift"
    );
    ensure!(input.records.len() == RECORDS, "record census drift");
    ensure!(
        input
            .records
            .iter()
            .enumerate()
            .all(|(sequence, record)| record.sequence == sequence),
        "record order drift"
    );
    Ok(())
}

fn validate_panel_cache(root: &Path, manifest: &ManifestSnapshot) -> Result<()> {
    let cache_path = checked_repo_path(root, PANEL_CACHE_PATH)?;
    let cache_manifest_path = checked_repo_path(root, PANEL_CACHE_MANIFEST_PATH)?;
    let receipt = strict_json_value(BufReader::new(File::open(cache_manifest_path)?))?;
    let expected_bytes = u64::try_from(RECORDS)?
        .checked_mul(u64::try_from(PANEL_COLUMN_BYTES)?)
        .context("panel cache size overflow")?;
    let data_sha256 = value_string(&receipt, "/data_sha256")?;
    ensure!(
        value_string(&receipt, "/schema")? == "max11-g0117-full-family-panel-cache-v1"
            && value_string(&receipt, "/result")? == "EXACT_PANEL_CACHE_REPRODUCED"
            && value_u64(&receipt, "/records")? == RECORDS as u64
            && value_u64(&receipt, "/rows")? == PANEL_ROWS as u64
            && value_u64(&receipt, "/entry_bytes")? == PANEL_ENTRY_BYTES as u64
            && value_u64(&receipt, "/payload_bytes")? == expected_bytes
            && value_string(&receipt, "/layout")?
                == "sequence-major: offset=((sequence*301)+row)*16"
            && value_string(&receipt, "/integer_width")? == "signed i128"
            && value_string(&receipt, "/endianness")? == "little"
            && is_sha256(data_sha256)
            && cache_path.metadata()?.len() == expected_bytes
            && manifest
                .bindings_by_path
                .get(PANEL_CACHE_PATH)
                .map(String::as_str)
                == Some(data_sha256),
        "panel cache identity/layout/custody drift"
    );
    Ok(())
}

fn load_prior_target(root: &Path) -> Result<Vec<i64>> {
    let manifest = strict_json_value(BufReader::new(File::open(checked_repo_path(
        root,
        PRIOR_MASTER_MANIFEST_PATH,
    )?)?))?;
    ensure!(
        value_string(&manifest, "/schema")? == "max11-g0128-full-family-master-manifest-v2"
            && value_u64(&manifest, "/rows")? == OLD_ROWS as u64
            && value_u64(&manifest, "/records")? == RECORDS as u64,
        "prior master manifest identity drift"
    );
    let target = manifest
        .get("target")
        .and_then(Value::as_array)
        .context("prior target missing")?
        .iter()
        .map(|value| {
            let raw = value
                .as_i64()
                .context("prior target coordinate is not i64")?;
            Ok(raw)
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(target.len() == OLD_ROWS, "prior target row census drift");
    Ok(target)
}

fn validate_stage_a_receipt(
    root: &Path,
    manifest: &ManifestSnapshot,
    expected: &Binding,
) -> Result<(StageAReceipt, Vec<[i8; N]>)> {
    binding_matches(root, expected, STAGE_A_RECEIPT_PATH)?;
    let receipt: StageAReceipt = strict_json(BufReader::new(File::open(checked_repo_path(
        root,
        STAGE_A_RECEIPT_PATH,
    )?)?))?;
    ensure!(
        receipt.schema == STAGE_A_SCHEMA
            && receipt.result == "EXACT_RESIDUAL_BATCH"
            && receipt.manifest_path == SHARED_MANIFEST_PATH
            && receipt.manifest_sha256 == manifest.sha256
            && receipt.complete_global_replay
            && !receipt.all_hinge_and_linear_residuals_zero
            && receipt.first_carry_forward_failure.is_none()
            && receipt.inputs_rehashed_at_end,
        "Stage A receipt identity or completion drift"
    );
    ensure!(
        receipt.linear_residuals_after_target.len() == N
            && receipt
                .linear_residuals_after_target
                .iter()
                .all(|value| value == "0"),
        "Stage A linear residual drift"
    );
    ensure!(
        receipt.carry_forward_checks.len() == OLD_CARRY_DIRECTIONS,
        "Stage A old-direction census drift"
    );
    let mut old = Vec::with_capacity(OLD_CARRY_DIRECTIONS);
    let mut seen = HashSet::new();
    for (index, check) in receipt.carry_forward_checks.iter().enumerate() {
        validate_direction(&check.direction)?;
        ensure!(
            check.index == index
                && check.coefficient == "0"
                && check.exact_zero
                && seen.insert(check.direction),
            "Stage A carry-forward receipt drift at {index}"
        );
        old.push(check.direction);
    }
    ensure!(
        receipt.batch_k == ANCESTOR_BATCH_K
            && receipt.selected_count == ANCESTOR_BATCH_K
            && receipt.selected.len() == ANCESTOR_BATCH_K
            && is_sha256(&receipt.selected_directions_i8_sha256)
            && is_sha256(&receipt.selected_exact_residuals_decimal_lf_sha256),
        "Stage A selection census/digest shape drift"
    );
    for item in &receipt.selected {
        validate_direction(&item.direction)?;
        ensure!(
            seen.insert(item.direction)
                && canonical_integer(&item.coefficient)
                && item.coefficient != "0",
            "Stage A selected direction/coefficient drift"
        );
    }
    ensure!(
        receipt
            .selected
            .windows(2)
            .all(|pair| pair[0].direction < pair[1].direction)
            && selected_direction_digest(&receipt.selected)
                == receipt.selected_directions_i8_sha256
            && selected_residual_digest(&receipt.selected)
                == receipt.selected_exact_residuals_decimal_lf_sha256,
        "Stage A selected order or digest drift"
    );
    old.extend(receipt.selected.iter().map(|item| item.direction));
    ensure!(
        old.len() == CARRY_DIRECTIONS,
        "accumulated direction census drift"
    );
    Ok((receipt, old))
}

fn validate_stage_b_receipt(
    root: &Path,
    manifest: &ManifestSnapshot,
    expected: &Binding,
    stage_a_binding: &Binding,
    prior_master_binding: &Binding,
    stage_a: &StageAReceipt,
) -> Result<StageBReceipt> {
    binding_matches(root, expected, STAGE_B_RECEIPT_PATH)?;
    let receipt: StageBReceipt = strict_json(BufReader::new(File::open(checked_repo_path(
        root,
        STAGE_B_RECEIPT_PATH,
    )?)?))?;
    ensure!(
        receipt.schema == STAGE_B_SCHEMA
            && receipt.result == "EXACT_FULL_FAMILY_BATCH32_COORDINATES"
            && receipt.manifest_path == SHARED_MANIFEST_PATH
            && receipt.manifest_sha256 == manifest.sha256
            && receipt.stage_a_receipt == *stage_a_binding
            && receipt.candidate == *prior_master_binding
            && receipt.batch_k == ANCESTOR_BATCH_K
            && receipt.records == RECORDS
            && receipt.hinge_entries == ANCESTOR_BATCH_K * RECORDS
            && receipt.selected_count == ANCESTOR_BATCH_K
            && receipt.rows.len() == ANCESTOR_BATCH_K
            && is_sha256(&receipt.direction_major_hinge_i64_le_sha256)
            && is_sha256(&receipt.exact_candidate_dots_decimal_lf_sha256)
            && receipt.exact_candidate_dots.len() == ANCESTOR_BATCH_K
            && receipt.inputs_rehashed_at_end,
        "Stage B receipt identity or census drift"
    );
    ensure!(
        receipt.selected_directions_i8_sha256 == stage_a.selected_directions_i8_sha256
            && receipt.selected_exact_residuals_decimal_lf_sha256
                == stage_a.selected_exact_residuals_decimal_lf_sha256
            && receipt.directions
                == stage_a
                    .selected
                    .iter()
                    .map(|item| item.direction)
                    .collect::<Vec<_>>()
            && receipt.exact_candidate_dots
                == stage_a
                    .selected
                    .iter()
                    .map(|item| item.coefficient.clone())
                    .collect::<Vec<_>>()
            && decimal_lf_digest(receipt.exact_candidate_dots.iter().map(String::as_str))
                == receipt.exact_candidate_dots_decimal_lf_sha256,
        "Stage B direction/residual binding drift"
    );
    Ok(receipt)
}

fn validate_old_member_receipt(value: &Value) -> Result<()> {
    ensure!(
        value_u64(value, "/old_rows")? == OLD_ROWS as u64
            && value_u64(value, "/old_rank")? == 176
            && value_u64(value, "/old_augmented_rank")? == 176
            && value_u64(value, "/old_selected_columns")? == 176
            && value_bool(value, "/all_old_rows_exactly_replayed")?
            && value_u64(value, "/full_seed_rank")? == 176
            && value_u64(value, "/full_seed_augmented_rank")? == 177
            && value_u64(value, "/appended_rows")? == APPENDED_ROWS as u64
            && value_bool(value, "/appended_rows_reject_old_member")?
            && value_bool(value, "/all_32_appended_residuals_nonzero")?,
        "Stage C old-member replay receipt drift"
    );
    ensure!(
        canonical_positive_integer(value_string(value, "/old_target_scale")?),
        "invalid Stage C old-member target scale"
    );
    for pointer in [
        "/old_selected_sequences_u64le_sha256",
        "/old_selected_basis_i128le_sha256",
        "/old_integer_residuals_decimal_lf_sha256",
        "/appended_residuals_decimal_lf_sha256",
    ] {
        ensure!(
            is_sha256(value_string(value, pointer)?),
            "old-member digest drift"
        );
    }
    Ok(())
}

fn validate_rank_trials(candidate: &StageCMember) -> Result<()> {
    ensure!(
        !candidate.trials.is_empty(),
        "Stage C rank transcript missing"
    );
    for (index, trial) in candidate.trials.iter().enumerate() {
        ensure!(
            value_u64(trial, "/iteration")? == index as u64
                && value_u64(trial, "/rank")? == (176 + index) as u64,
            "Stage C rank trial order/growth drift"
        );
        let result = value_string(trial, "/result")?;
        if index + 1 == candidate.trials.len() {
            ensure!(
                result == "EXACT_Q_MEMBER"
                    && value_u64(trial, "/rank")? == candidate.rank as u64
                    && value_u64(trial, "/augmented_rank")? == candidate.augmented_rank as u64,
                "Stage C terminal member trial drift"
            );
        } else {
            ensure!(
                result == "SEPARATOR_VIOLATED"
                    && value_u64(trial, "/augmented_rank")? == value_u64(trial, "/rank")? + 1
                    && value_u64(trial, "/columns_scanned")? > 0
                    && value_u64(trial, "/columns_scanned")? <= RECORDS as u64
                    && canonical_integer(value_string(trial, "/first_violating_price")?)
                    && value_string(trial, "/first_violating_price")? != "0",
                "Stage C nonterminal separator trial drift"
            );
        }
    }
    Ok(())
}

const STAGE_C_MEMBER_KEYS: &[&str] = &[
    "schema",
    "result",
    "claim_boundary",
    "manifest_path",
    "manifest_sha256",
    "solver",
    "stage_a_receipt",
    "stage_b_receipt",
    "prior_master_result",
    "prior_master_manifest",
    "audited_exact_q_core",
    "records",
    "old_rows",
    "appended_rows",
    "rows",
    "target",
    "target_i128le_sha256",
    "target_construction",
    "prior_target_scale_not_reused",
    "row_order",
    "stage_a_selected_directions_i8_sha256",
    "stage_a_selected_exact_residuals_decimal_lf_sha256",
    "stage_b_direction_major_hinge_i64_le_sha256",
    "stage_b_exact_candidate_dots_decimal_lf_sha256",
    "warm_seed_policy",
    "initial_selected_sequences",
    "initial_selected_sequences_u64le_sha256",
    "initial_rank",
    "max_rank_increases",
    "all_columns_reopened",
    "canonical_column_order",
    "no_modular_terminal_decision",
    "no_support_freeze",
    "no_zero_price_column_deletion",
    "no_row_dependency_deletion",
    "no_preferred_sparsity_search",
    "old_member_validation",
    "input_snapshot_sha256",
    "inputs_rehashed_at_end",
    "wall_seconds",
    "maximum_rss_kib",
    "all_412_rows_replayed",
    "rank",
    "augmented_rank",
    "selected_sequences",
    "support_sequences",
    "coordinate_rows",
    "selected_basis_i128le_sha256",
    "rational_coefficients",
    "rational_coefficients_lf_sha256",
    "target_scale",
    "integer_coefficients",
    "integer_coefficients_decimal_lf_sha256",
    "terms",
    "support_receipt",
    "replay_receipt",
    "coefficient_plus_one_mutant",
    "prior_target_scale_carryover_mutant_rejected",
    "trials",
];

fn validate_stage_c_member_keys(value: &Value) -> Result<()> {
    let object = value
        .as_object()
        .context("Stage C member must be a JSON object")?;
    let expected = STAGE_C_MEMBER_KEYS.iter().copied().collect::<BTreeSet<_>>();
    let observed = object.keys().map(String::as_str).collect::<BTreeSet<_>>();
    ensure!(
        expected.len() == STAGE_C_MEMBER_KEYS.len() && observed == expected,
        "Stage C member key-set drift"
    );
    Ok(())
}

fn validate_stage_c_member(
    root: &Path,
    manifest: &ManifestSnapshot,
    candidate: &StageCMember,
    candidate_binding: &Binding,
    prior_target: &[i64],
) -> Result<()> {
    binding_matches(root, candidate_binding, STAGE_C_RESULT_PATH)?;
    ensure!(
        candidate.schema == STAGE_C_SCHEMA
            && candidate.result == STAGE_C_MEMBER
            && !candidate.claim_boundary.trim().is_empty()
            && candidate.manifest_path == SHARED_MANIFEST_PATH
            && candidate.manifest_sha256 == manifest.sha256
            && candidate.records == RECORDS
            && candidate.old_rows == OLD_ROWS
            && candidate.appended_rows == APPENDED_ROWS
            && candidate.rows == ROWS
            && candidate.all_412_rows_replayed
            && candidate.inputs_rehashed_at_end
            && candidate.wall_seconds > 0.0
            && candidate.maximum_rss_kib > 0,
        "Stage C member identity/completion drift"
    );
    binding_matches(root, &candidate.solver, STAGE_C_SOURCE_PATH)?;
    binding_matches(root, &candidate.stage_a_receipt, STAGE_A_RECEIPT_PATH)?;
    binding_matches(root, &candidate.stage_b_receipt, STAGE_B_RECEIPT_PATH)?;
    binding_matches(
        root,
        &candidate.prior_master_result,
        PRIOR_MASTER_RESULT_PATH,
    )?;
    binding_matches(
        root,
        &candidate.prior_master_manifest,
        PRIOR_MASTER_MANIFEST_PATH,
    )?;
    for binding in [
        &candidate.solver,
        &candidate.prior_master_result,
        &candidate.prior_master_manifest,
    ] {
        ensure!(
            manifest.bindings_by_path.get(&binding.path) == Some(&binding.sha256),
            "Stage C result binding absent from shared manifest: {}",
            binding.path
        );
    }
    let audited = candidate
        .audited_exact_q_core
        .as_object()
        .context("Stage C audited exact-Q core must be an object")?;
    ensure!(
        audited.len() == 2
            && audited.contains_key("g0128_source")
            && audited.contains_key("g0117_source"),
        "Stage C audited exact-Q core key drift"
    );
    for (label, expected_path) in [
        ("g0128_source", PRIOR_MASTER_SOURCE_PATH),
        ("g0117_source", EXACT_Q_CORE_PATH),
    ] {
        let binding = parse_binding_value(
            audited
                .get(label)
                .context("missing audited exact-Q binding")?,
            label,
        )?;
        binding_matches(root, &binding, expected_path)?;
        ensure!(
            manifest.bindings_by_path.get(expected_path) == Some(&binding.sha256),
            "Stage C audited core absent from shared manifest: {expected_path}"
        );
    }

    ensure!(
        candidate.target.len() == ROWS
            && candidate.target[..OLD_ROWS] == *prior_target
            && candidate.target[OLD_ROWS..] == [0; APPENDED_ROWS]
            && i128le_digest(candidate.target.iter().copied()) == candidate.target_i128le_sha256
            && candidate.target_construction
                == "original_unscaled_G0128_380_entry_target_followed_by_32_exact_zeros"
            && candidate.prior_target_scale_not_reused
            && candidate.row_order
                == [
                    "immutable_prefix:G-0128:380",
                    "batch:G-0135-stage-A-receipt-order:32",
                ],
        "Stage C target or row-order drift"
    );
    ensure!(
        candidate.warm_seed_policy
            == "all_176_G0128_selected_sequences_then_every_separator_scan_reopens_all_163740_columns_in_canonical_sequence_order"
            && candidate.initial_rank == 176
            && candidate.max_rank_increases == ROWS - 176
            && candidate.all_columns_reopened
            && candidate.canonical_column_order
            && candidate.no_modular_terminal_decision
            && candidate.no_support_freeze
            && candidate.no_zero_price_column_deletion
            && candidate.no_row_dependency_deletion
            && candidate.no_preferred_sparsity_search,
        "Stage C exact all-column policy drift"
    );
    validate_strict_axis(
        &candidate.initial_selected_sequences,
        RECORDS,
        "Stage C warm seed",
    )?;
    ensure!(
        candidate.initial_selected_sequences.len() == 176
            && u64le_digest(candidate.initial_selected_sequences.iter().copied())
                == candidate.initial_selected_sequences_u64le_sha256
            && is_sha256(&candidate.input_snapshot_sha256)
            && is_sha256(&candidate.stage_a_selected_directions_i8_sha256)
            && is_sha256(&candidate.stage_a_selected_exact_residuals_decimal_lf_sha256)
            && is_sha256(&candidate.stage_b_direction_major_hinge_i64_le_sha256)
            && is_sha256(&candidate.stage_b_exact_candidate_dots_decimal_lf_sha256),
        "warm-seed census drift"
    );
    validate_old_member_receipt(&candidate.old_member_validation)?;

    ensure!(
        candidate.rank == candidate.augmented_rank
            && candidate.rank > 0
            && candidate.rank <= ROWS
            && candidate.selected_sequences.len() == candidate.rank
            && candidate.support_sequences.len() == candidate.rank
            && candidate.coordinate_rows.len() == candidate.rank
            && candidate.rational_coefficients.len() == candidate.rank
            && candidate.integer_coefficients.len() == candidate.rank,
        "Stage C variable rank/support/coefficient census drift"
    );
    validate_strict_axis(&candidate.selected_sequences, RECORDS, "selected sequences")?;
    validate_strict_axis(&candidate.support_sequences, RECORDS, "support sequences")?;
    validate_strict_axis(&candidate.coordinate_rows, ROWS, "coordinate rows")?;
    ensure!(
        candidate.selected_sequences == candidate.support_sequences,
        "Stage C selected/support pivot-basis axis drift"
    );
    ensure!(
        is_sha256(&candidate.selected_basis_i128le_sha256)
            && is_sha256(&candidate.rational_coefficients_lf_sha256)
            && is_sha256(&candidate.integer_coefficients_decimal_lf_sha256)
            && decimal_lf_digest(candidate.rational_coefficients.iter().map(String::as_str))
                == candidate.rational_coefficients_lf_sha256
            && decimal_lf_digest(candidate.integer_coefficients.iter().map(String::as_str))
                == candidate.integer_coefficients_decimal_lf_sha256,
        "Stage C coefficient digest drift"
    );

    let scale = parse_bigint(&candidate.target_scale)?;
    ensure!(
        scale > BigInt::from(0),
        "Stage C target scale is not positive"
    );
    let integers = candidate
        .integer_coefficients
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        integers.iter().any(|value| *value != BigInt::from(0)),
        "zero member"
    );
    for ((rational, integer), sequence) in candidate
        .rational_coefficients
        .iter()
        .zip(integers.iter())
        .zip(candidate.support_sequences.iter())
    {
        let (numerator, denominator) = parse_rational(rational)?;
        ensure!(
            &scale % &denominator == BigInt::from(0)
                && numerator * (&scale / denominator) == *integer,
            "rational/integer clearing drift at support sequence {sequence}"
        );
    }
    let primitive = integers.iter().cloned().fold(scale.clone(), bigint_gcd);
    ensure!(
        primitive == BigInt::from(1),
        "Stage C certificate is not primitive"
    );
    ensure!(
        candidate.terms
            == nonzero_term_projection(
                &candidate.support_sequences,
                &candidate.integer_coefficients
            )?
            && !candidate.terms.is_empty(),
        "Stage C exact nonzero term projection drift"
    );

    let support = &candidate.support_receipt;
    ensure!(
        support.selected_columns == candidate.selected_sequences.len()
            && support.support_columns == candidate.support_sequences.len()
            && support.support_is_exact_pivot_basis
            && support.selected_sequences_u64le_sha256
                == u64le_digest(candidate.selected_sequences.iter().copied())
            && support.support_sequences_u64le_sha256
                == u64le_digest(candidate.support_sequences.iter().copied())
            && support.term_support_u64le_sha256
                == u64le_digest(candidate.terms.iter().map(|term| term.sequence)),
        "Stage C support receipt drift"
    );
    let replay = &candidate.replay_receipt;
    ensure!(
        replay.rows == ROWS
            && replay.rational_all_rows_replayed
            && replay.primitive_denominator_clearing
            && replay.integer_all_rows_replayed
            && replay.rational_lhs_lf_sha256 == integer_lf_digest(candidate.target.iter().copied())
            && replay.integer_residuals_decimal_lf_sha256 == zero_lf_digest(ROWS),
        "Stage C all-412-row replay receipt drift"
    );
    let mutant = &candidate.coefficient_plus_one_mutant;
    ensure!(
        mutant.support_index < candidate.support_sequences.len()
            && candidate.integer_coefficients[mutant.support_index] != "0"
            && mutant.sequence == candidate.support_sequences[mutant.support_index]
            && mutant.coefficient_delta == "+1"
            && mutant.first_nonzero_residual_row < ROWS
            && is_sha256(&mutant.residuals_decimal_lf_sha256)
            && mutant.rejected
            && candidate.prior_target_scale_carryover_mutant_rejected,
        "Stage C member hostile-control drift"
    );
    validate_rank_trials(candidate)?;
    Ok(())
}

struct ValidatedInputs {
    panel: PanelInput,
    candidate: StageCMember,
    candidate_binding: Binding,
    manifest: ManifestSnapshot,
    accumulated_directions: Vec<[i8; N]>,
}

fn load_and_validate_inputs(root: &Path) -> Result<ValidatedInputs> {
    validate_compiled_bytes(root)?;
    let manifest = validate_shared_manifest(root)?;
    let panel: PanelInput = strict_json(BufReader::new(File::open(checked_repo_path(
        root,
        PANEL_INPUT_PATH,
    )?)?))?;
    validate_panel(&panel)?;
    validate_panel_cache(root, &manifest)?;
    let candidate_path = checked_repo_path(root, STAGE_C_RESULT_PATH)?;
    let candidate_binding = Binding {
        path: STAGE_C_RESULT_PATH.to_string(),
        sha256: sha256_path(&candidate_path)?,
    };
    let candidate_value = strict_json_value(BufReader::new(File::open(candidate_path)?))?;
    validate_stage_c_member_keys(&candidate_value)?;
    let candidate: StageCMember =
        serde_json::from_value(candidate_value).context("Stage C member schema")?;
    let prior_target = load_prior_target(root)?;
    validate_stage_c_member(
        root,
        &manifest,
        &candidate,
        &candidate_binding,
        &prior_target,
    )?;
    let (stage_a, accumulated_directions) =
        validate_stage_a_receipt(root, &manifest, &candidate.stage_a_receipt)?;
    let stage_b = validate_stage_b_receipt(
        root,
        &manifest,
        &candidate.stage_b_receipt,
        &candidate.stage_a_receipt,
        &candidate.prior_master_result,
        &stage_a,
    )?;
    ensure!(
        candidate.stage_a_selected_directions_i8_sha256 == stage_a.selected_directions_i8_sha256
            && candidate.stage_a_selected_exact_residuals_decimal_lf_sha256
                == stage_a.selected_exact_residuals_decimal_lf_sha256
            && candidate.stage_b_direction_major_hinge_i64_le_sha256
                == stage_b.direction_major_hinge_i64_le_sha256
            && candidate.stage_b_exact_candidate_dots_decimal_lf_sha256
                == stage_b.exact_candidate_dots_decimal_lf_sha256,
        "Stage C receipt-bridge digest drift"
    );
    for committed_output in [
        SHARED_MANIFEST_PATH,
        STAGE_A_RECEIPT_PATH,
        STAGE_B_RECEIPT_PATH,
        STAGE_C_RESULT_PATH,
    ] {
        git_commit_for_path(root, committed_output)?;
    }
    Ok(ValidatedInputs {
        panel,
        candidate,
        candidate_binding,
        manifest,
        accumulated_directions,
    })
}

fn term_receipt(record: &Record, form: &ExactNormalForm) -> Result<TermNormalFormReceipt> {
    let inactive = N
        .checked_sub(record.active_vertices)
        .context("active vertex census exceeds n")?;
    let multiplicity = factorial(inactive);
    let leaves = form.compressed_leaves;
    ensure!(
        leaves
            .checked_mul(multiplicity)
            .context("compressed orbit receipt overflow")?
            == form.labelled_permutations
            && leaves == factorial(N) / multiplicity,
        "compressed orbit reconciliation failed"
    );
    Ok(TermNormalFormReceipt {
        sequence: record.sequence,
        active_vertices: record.active_vertices,
        enumeration_mode:
            "exact_active_vertex_injections_with_inactive_label_factorial_multiplicity".to_string(),
        compressed_leaves_generated: leaves,
        compressed_leaves_visited: leaves,
        compressed_leaves_accepted: leaves,
        inactive_label_multiplicity: multiplicity,
        generated_labelled_permutations: form.labelled_permutations,
        visited_labelled_permutations: form.labelled_permutations,
        accepted_labelled_permutations: form.labelled_permutations,
        skipped_labelled_permutations: 0,
        unclassified_labelled_permutations: 0,
        failed_labelled_permutations: 0,
        hinge_entries: form.hinges.len(),
        normal_form_sha256: normal_form_digest(form, None, None),
        scientific_coefficient_arithmetic: "signed_num_bigint_BigInt".to_string(),
        independent_exact_linear_crosscheck: true,
        bounded_kernel_crosscheck: true,
    })
}

fn expected_labelled_permutations(term_count: usize) -> Result<u64> {
    u64::try_from(term_count)?
        .checked_mul(factorial(N))
        .context("dynamic labelled-permutation census overflow")
}

fn validate_term_receipts(receipts: &[TermNormalFormReceipt], expected_terms: usize) -> Result<()> {
    ensure!(
        receipts.len() == expected_terms,
        "term receipt census drift"
    );
    let mut total = 0u64;
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
                && receipt.scientific_coefficient_arithmetic == "signed_num_bigint_BigInt"
                && receipt.independent_exact_linear_crosscheck
                && receipt.bounded_kernel_crosscheck
                && is_sha256(&receipt.normal_form_sha256),
            "term receipt reconciliation failed at sequence {}",
            receipt.sequence
        );
        total = total
            .checked_add(receipt.visited_labelled_permutations)
            .context("term receipt total overflow")?;
    }
    ensure!(
        total == expected_labelled_permutations(expected_terms)?,
        "dynamic global labelled-permutation receipt drift"
    );
    Ok(())
}

fn add_exact(
    aggregate: &mut ExactAggregate,
    record: &Record,
    form: ExactNormalForm,
    coefficient: &BigInt,
) -> Result<()> {
    let receipt = term_receipt(record, &form)?;
    aggregate.terms += 1;
    aggregate.labelled_permutations_checked = aggregate
        .labelled_permutations_checked
        .checked_add(form.labelled_permutations)
        .context("aggregate labelled census overflow")?;
    aggregate.hinge_entries_processed = aggregate
        .hinge_entries_processed
        .checked_add(u64::try_from(form.hinges.len())?)
        .context("aggregate hinge-entry census overflow")?;
    for (rank, value) in form.linear.into_iter().enumerate() {
        aggregate.linear[rank] += coefficient * value;
    }
    for (direction, value) in form.hinges {
        *aggregate.hinges.entry(direction).or_default() += coefficient * value;
    }
    aggregate.term_receipts.push(receipt);
    Ok(())
}

fn merge_exact(mut left: ExactAggregate, right: ExactAggregate) -> ExactAggregate {
    if left.hinges.len() < right.hinges.len() {
        return merge_exact(right, left);
    }
    left.terms += right.terms;
    left.labelled_permutations_checked += right.labelled_permutations_checked;
    left.hinge_entries_processed += right.hinge_entries_processed;
    for rank in 0..N {
        left.linear[rank] += &right.linear[rank];
    }
    for (direction, coefficient) in right.hinges {
        *left.hinges.entry(direction).or_default() += coefficient;
    }
    left.term_receipts.extend(right.term_receipts);
    left
}

fn direct_accumulated_prices(
    panel: &PanelInput,
    candidate: &StageCMember,
    directions: &[[i8; N]],
) -> Result<Vec<BigInt>> {
    ensure!(
        directions.len() == CARRY_DIRECTIONS,
        "direct-DP direction width drift"
    );
    candidate
        .terms
        .par_iter()
        .map(|term| -> Result<Vec<BigInt>> {
            let coefficient = parse_bigint(&term.coefficient)?;
            let prices = exact_hinge_coefficients(&panel.records[term.sequence], directions)?;
            ensure!(
                prices.len() == CARRY_DIRECTIONS,
                "direct-DP term width drift"
            );
            Ok(prices
                .into_iter()
                .map(|price| &coefficient * price)
                .collect())
        })
        .try_reduce(
            || vec![BigInt::from(0); CARRY_DIRECTIONS],
            |mut left, right| -> Result<Vec<BigInt>> {
                ensure!(
                    right.len() == CARRY_DIRECTIONS,
                    "direct-DP reduction width drift"
                );
                for (total, contribution) in left.iter_mut().zip(right) {
                    *total += contribution;
                }
                Ok(left)
            },
        )
}

fn read_panel_column(cache: &mut File, sequence: usize) -> Result<Vec<BigInt>> {
    ensure!(
        sequence < RECORDS,
        "panel-cache sequence outside frozen family"
    );
    let offset = sequence
        .checked_mul(PANEL_COLUMN_BYTES)
        .and_then(|value| u64::try_from(value).ok())
        .context("panel-cache offset overflow")?;
    cache.seek(SeekFrom::Start(offset))?;
    let mut encoded = vec![0u8; PANEL_COLUMN_BYTES];
    cache.read_exact(&mut encoded)?;
    let values = encoded
        .chunks_exact(PANEL_ENTRY_BYTES)
        .map(|chunk| {
            let bytes: [u8; PANEL_ENTRY_BYTES] = chunk
                .try_into()
                .expect("chunks_exact has the frozen i128 width");
            BigInt::from(i128::from_le_bytes(bytes))
        })
        .collect::<Vec<_>>();
    ensure!(values.len() == PANEL_ROWS, "panel-cache column width drift");
    Ok(values)
}

fn exact_matrix_residuals(
    columns: &[Vec<BigInt>],
    coefficients: &[BigInt],
    target: &[BigInt],
    scale: &BigInt,
) -> Result<Vec<BigInt>> {
    ensure!(
        !columns.is_empty()
            && columns.len() == coefficients.len()
            && !target.is_empty()
            && columns.iter().all(|column| column.len() == target.len()),
        "ragged or empty exact finite-row replay"
    );
    let mut residuals = target
        .iter()
        .map(|value| -(scale * value))
        .collect::<Vec<_>>();
    for (column, coefficient) in columns.iter().zip(coefficients) {
        for (residual, value) in residuals.iter_mut().zip(column) {
            *residual += coefficient * value;
        }
    }
    Ok(residuals)
}

fn independent_finite_replay(
    root: &Path,
    panel: &PanelInput,
    candidate: &StageCMember,
    accumulated_directions: &[[i8; N]],
) -> Result<FiniteReplayReceipt> {
    ensure!(
        candidate.target.len() == ROWS
            && accumulated_directions.len() == CARRY_DIRECTIONS
            && PANEL_ROWS + LINEAR_ROWS + CARRY_DIRECTIONS == ROWS,
        "finite replay dimensions drift"
    );
    let mut cache = File::open(checked_repo_path(root, PANEL_CACHE_PATH)?)?;
    let mut columns = Vec::with_capacity(candidate.terms.len());
    let mut coefficients = Vec::with_capacity(candidate.terms.len());
    for term in &candidate.terms {
        let record = &panel.records[term.sequence];
        let mut column = read_panel_column(&mut cache, term.sequence)?;
        column.extend(exact_linear_vector(record)?);
        column.extend(exact_hinge_coefficients(record, accumulated_directions)?);
        ensure!(column.len() == ROWS, "finite replay column width drift");
        columns.push(column);
        coefficients.push(parse_bigint(&term.coefficient)?);
    }
    let target = candidate
        .target
        .iter()
        .copied()
        .map(BigInt::from)
        .collect::<Vec<_>>();
    let scale = parse_bigint(&candidate.target_scale)?;
    let residuals = exact_matrix_residuals(&columns, &coefficients, &target, &scale)?;
    ensure!(
        residuals.iter().all(|value| *value == BigInt::from(0)),
        "independent finite 412-row replay failed"
    );

    let first_term = candidate
        .terms
        .first()
        .context("finite replay has no term")?;
    let first_column = columns.first().context("finite replay has no column")?;
    let mutated = residuals
        .iter()
        .zip(first_column)
        .map(|(residual, value)| residual + value)
        .collect::<Vec<_>>();
    let first_nonzero_residual_row = mutated
        .iter()
        .position(|value| *value != BigInt::from(0))
        .context("finite coefficient-plus-one mutant escaped")?;
    let residual_strings = residuals
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    let mutated_strings = mutated.iter().map(ToString::to_string).collect::<Vec<_>>();
    Ok(FiniteReplayReceipt {
        rows: ROWS,
        panel_rows: PANEL_ROWS,
        linear_rows: LINEAR_ROWS,
        accumulated_hinge_rows: CARRY_DIRECTIONS,
        cache_layout: "sequence-major: offset=((sequence*301)+row)*16; signed little-endian i128",
        arithmetic: "signed_num_bigint_BigInt",
        all_rows_exactly_replayed: true,
        residuals_decimal_lf_sha256: decimal_lf_digest(residual_strings.iter().map(String::as_str)),
        coefficient_plus_one_mutant: FiniteCoefficientMutant {
            sequence: first_term.sequence,
            coefficient_delta: "+1",
            first_nonzero_residual_row,
            residuals_decimal_lf_sha256: decimal_lf_digest(
                mutated_strings.iter().map(String::as_str),
            ),
            rejected: true,
        },
    })
}

fn hinge_digest(hinges: &HashMap<[i8; N], BigInt>, nonzero_only: bool) -> String {
    let mut digest = Sha256::new();
    for (direction, coefficient) in hinges.iter().collect::<BTreeMap<_, _>>() {
        if nonzero_only && *coefficient == BigInt::from(0) {
            continue;
        }
        for (index, coordinate) in direction.iter().enumerate() {
            if index != 0 {
                digest.update(b",");
            }
            digest.update(coordinate.to_string().as_bytes());
        }
        digest.update(b"\t");
        digest.update(coefficient.to_string().as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn residual_summary(
    aggregate: &ExactAggregate,
    form_delta: Option<(&ExactNormalForm, &BigInt)>,
    linear_delta: Option<(usize, &BigInt)>,
) -> (Option<ExactHinge>, Option<ExactLinear>) {
    let mut keys = aggregate.hinges.keys().copied().collect::<BTreeSet<_>>();
    if let Some((form, _)) = form_delta {
        keys.extend(form.hinges.keys().copied());
    }
    let first_hinge = keys.into_iter().find_map(|direction| {
        let mut coefficient = aggregate
            .hinges
            .get(&direction)
            .cloned()
            .unwrap_or_default();
        if let Some((form, multiplier)) = form_delta
            && let Some(value) = form.hinges.get(&direction)
        {
            coefficient += multiplier * value;
        }
        (coefficient != BigInt::from(0)).then(|| ExactHinge {
            direction,
            coefficient: coefficient.to_string(),
        })
    });
    let first_linear = first_hinge
        .is_none()
        .then(|| {
            (0..N).find_map(|coordinate| {
                let mut coefficient = aggregate.linear[coordinate].clone();
                if let Some((form, multiplier)) = form_delta {
                    coefficient += multiplier * &form.linear[coordinate];
                }
                if let Some((mutated_coordinate, delta)) = linear_delta
                    && coordinate == mutated_coordinate
                {
                    coefficient += delta;
                }
                (coefficient != BigInt::from(0)).then(|| ExactLinear {
                    coordinate,
                    coefficient: coefficient.to_string(),
                })
            })
        })
        .flatten();
    (first_hinge, first_linear)
}

fn residual_digest(
    aggregate: &ExactAggregate,
    form_delta: Option<(&ExactNormalForm, &BigInt)>,
    linear_delta: Option<(usize, &BigInt)>,
) -> String {
    let mut digest = Sha256::new();
    digest.update(b"G0135-STAGE-D-COMPLETE-EXACT-RESIDUAL-V1\0");
    let mut keys = aggregate.hinges.keys().copied().collect::<BTreeSet<_>>();
    if let Some((form, _)) = form_delta {
        keys.extend(form.hinges.keys().copied());
    }
    for direction in keys {
        let mut coefficient = aggregate
            .hinges
            .get(&direction)
            .cloned()
            .unwrap_or_default();
        if let Some((form, multiplier)) = form_delta
            && let Some(value) = form.hinges.get(&direction)
        {
            coefficient += multiplier * value;
        }
        if coefficient == BigInt::from(0) {
            continue;
        }
        digest.update(b"H\t");
        for (index, coordinate) in direction.iter().enumerate() {
            if index != 0 {
                digest.update(b",");
            }
            digest.update(coordinate.to_string().as_bytes());
        }
        digest.update(b"\t");
        digest.update(coefficient.to_string().as_bytes());
        digest.update(b"\n");
    }
    for coordinate in 0..N {
        let mut coefficient = aggregate.linear[coordinate].clone();
        if let Some((form, multiplier)) = form_delta {
            coefficient += multiplier * &form.linear[coordinate];
        }
        if let Some((mutated_coordinate, delta)) = linear_delta
            && coordinate == mutated_coordinate
        {
            coefficient += delta;
        }
        if coefficient == BigInt::from(0) {
            continue;
        }
        digest.update(b"L\t");
        digest.update(coordinate.to_string().as_bytes());
        digest.update(b"\t");
        digest.update(coefficient.to_string().as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn mutation_control(
    name: &'static str,
    aggregate: &ExactAggregate,
    form_delta: Option<(&ExactNormalForm, &BigInt)>,
    linear_delta: Option<(usize, &BigInt)>,
) -> Result<MutationControl> {
    let baseline_complete_residual_sha256 = residual_digest(aggregate, None, None);
    let mutated_complete_residual_sha256 = residual_digest(aggregate, form_delta, linear_delta);
    let changed_from_baseline =
        mutated_complete_residual_sha256 != baseline_complete_residual_sha256;
    let (first_nonzero_hinge, first_nonzero_linear) =
        residual_summary(aggregate, form_delta, linear_delta);
    let detected =
        changed_from_baseline && (first_nonzero_hinge.is_some() || first_nonzero_linear.is_some());
    ensure!(detected, "hostile mutation survived or was inert: {name}");
    Ok(MutationControl {
        name,
        first_nonzero_hinge,
        first_nonzero_linear,
        baseline_complete_residual_sha256,
        mutated_complete_residual_sha256,
        changed_from_baseline,
        detected,
    })
}

fn select_next_batch(
    aggregate: &ExactAggregate,
    accumulated_directions: &[[i8; N]],
    global_zero: bool,
) -> Result<Vec<ExactHinge>> {
    ensure!(
        aggregate
            .linear
            .iter()
            .all(|value| *value == BigInt::from(0)),
        "nonzero linear residual invalidates Stage D terminal"
    );
    if global_zero {
        return Ok(Vec::new());
    }
    let accumulated = accumulated_directions
        .iter()
        .copied()
        .collect::<HashSet<_>>();
    let selected = aggregate
        .hinges
        .iter()
        .collect::<BTreeMap<_, _>>()
        .into_iter()
        .filter(|(direction, coefficient)| {
            **coefficient != BigInt::from(0) && !accumulated.contains(*direction)
        })
        .take(BATCH_K)
        .map(|(direction, coefficient)| ExactHinge {
            direction: *direction,
            coefficient: coefficient.to_string(),
        })
        .collect::<Vec<_>>();
    ensure!(
        selected.len() == BATCH_K,
        "residual has fewer than 128 eligible hinges"
    );
    ensure!(
        selected
            .windows(2)
            .all(|pair| pair[0].direction < pair[1].direction),
        "Pool128 order is not strict signed lexicographic"
    );
    for item in &selected {
        validate_direction(&item.direction)?;
        ensure!(
            canonical_integer(&item.coefficient)
                && item.coefficient != "0"
                && !accumulated.contains(&item.direction),
            "invalid Pool128 item"
        );
    }
    Ok(selected)
}

fn validate_accumulated_directions(directions: &[[i8; N]]) -> Result<()> {
    ensure!(
        directions.len() == CARRY_DIRECTIONS,
        "accumulated direction census is not 100"
    );
    let mut seen = HashSet::new();
    for direction in directions {
        validate_direction(direction)?;
        ensure!(seen.insert(*direction), "duplicate accumulated direction");
    }
    Ok(())
}

fn self_test() -> Result<()> {
    ensure!(
        strict_json_value(std::io::Cursor::new(br#"{"ok":[1,true,null]}"#)).is_ok()
            && strict_json_value(std::io::Cursor::new(br#"{"x":1,"x":2}"#)).is_err()
            && strict_json::<StudyManifest>(std::io::Cursor::new(br#"{}"#)).is_err()
            && strict_json::<Binding>(std::io::Cursor::new(
                br#"{"path":"x","sha256":"0000000000000000000000000000000000000000000000000000000000000000","extra":true}"#,
            ))
            .is_err()
            && validate_stage_c_member_keys(&serde_json::json!({"schema": STAGE_C_SCHEMA}))
                .is_err()
            && strict_json::<StageCMember>(std::io::Cursor::new(
                format!(r#"{{"schema":"{STAGE_C_SCHEMA}"}}"#).into_bytes(),
            ))
            .is_err(),
        "malformed manifest/result or duplicate JSON control escaped"
    );
    let g0139 = strict_json_value(std::io::Cursor::new(COMPILED_G0139_AUDIT))?;
    validate_g0139_semantics(&g0139)?;
    let mut wrong_subject_commit = g0139.clone();
    wrong_subject_commit["subject"]["git_commit"] = Value::String("0".repeat(40));
    let mut false_evidence_class = g0139.clone();
    false_evidence_class["evidence_class"] = Value::String("T2_INDEPENDENT_REPLAY".to_string());
    let mut false_lineage = g0139.clone();
    false_lineage["reviewer"]["same_model_lineage"] = Value::Bool(false);
    false_lineage["preregistration"]["outcome_aware"] = Value::Bool(false);
    let mut missing_boundary = g0139.clone();
    missing_boundary["claim_boundary"] = Value::String(String::new());
    let mut missing_custody = g0139.clone();
    missing_custody
        .as_object_mut()
        .context("G-0139 self-test object drift")?
        .remove("input_custody");
    let mut false_source_audit = g0139;
    false_source_audit["source_audit_anchor"]["sha256"] = Value::String("0".repeat(64));
    false_source_audit["source_audit_anchor"]["verdict"] = Value::String("FAIL".to_string());
    ensure!(
        [
            wrong_subject_commit,
            false_evidence_class,
            false_lineage,
            missing_boundary,
            missing_custody,
            false_source_audit,
        ]
        .iter()
        .all(|mutant| validate_g0139_semantics(mutant).is_err()),
        "G-0139 semantic hostile control escaped"
    );
    let source_audit = serde_json::json!({
        "schema": STAGE_A_SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": SOURCE_CUSTODY_PASS_RESULT,
        "evidence_class": STAGE_A_SOURCE_AUDIT_EVIDENCE_CLASS,
        "claim_boundary": STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY,
        "scientific_manifest_observed": false,
        "scientific_input_observed": false,
        "scientific_output_observed": false,
        "scientific_replay_run": false,
        "subject": {
            "commit_object_and_working_bytes_equal_for_all_bindings": true
        }
    });
    validate_source_audit_envelope(&source_audit, STAGE_A_SOURCE_AUDIT_PATH)?;
    let mut source_audit_schema_mutant = source_audit.clone();
    source_audit_schema_mutant["schema"] = Value::String("lookalike-source-audit".to_string());
    let mut source_audit_result_mutant = source_audit;
    source_audit_result_mutant["result"] = Value::String("LOOKALIKE_PASS".to_string());
    let mut source_audit_observation_mutant = source_audit_result_mutant.clone();
    source_audit_observation_mutant["result"] =
        Value::String(SOURCE_CUSTODY_PASS_RESULT.to_string());
    source_audit_observation_mutant["scientific_input_observed"] = Value::Bool(true);
    ensure!(
        validate_source_audit_envelope(&source_audit_schema_mutant, STAGE_A_SOURCE_AUDIT_PATH)
            .is_err()
            && validate_source_audit_envelope(
                &source_audit_result_mutant,
                STAGE_A_SOURCE_AUDIT_PATH
            )
            .is_err()
            && validate_source_audit_envelope(
                &source_audit_observation_mutant,
                STAGE_A_SOURCE_AUDIT_PATH
            )
            .is_err(),
        "Stage-A source-audit schema/result hostile control escaped"
    );
    for valid in ["0", "1", "-1", "12345678901234567890"] {
        ensure!(canonical_integer(valid), "valid integer rejected");
    }
    for invalid in ["", "-", "+1", "00", "01", "-0", "-01", "1/2", " 1"] {
        ensure!(!canonical_integer(invalid), "invalid integer accepted");
    }
    for (valid, numerator, denominator) in [
        ("0", "0", "1"),
        ("-7", "-7", "1"),
        ("3/5", "3", "5"),
        ("-11/13", "-11", "13"),
    ] {
        let (actual_numerator, actual_denominator) = parse_rational(valid)?;
        ensure!(
            actual_numerator == parse_bigint(numerator)?
                && actual_denominator == parse_bigint(denominator)?,
            "valid rational drift"
        );
    }
    for invalid in ["1/1", "2/4", "1/0", "1/-2", "+1/2", "1/02", "1/2/3"] {
        ensure!(
            parse_rational(invalid).is_err(),
            "invalid rational accepted"
        );
    }

    let record = Record {
        sequence: 0,
        signed_mass: 3,
        active_vertices: 6,
        negative_edges: vec![[0, 1], [1, 2], [3, 4]],
        positive_edges: vec![[0, 2], [2, 5], [4, 5]],
    };
    let form = validated_full_normal_form(&record)?;
    ensure!(!form.hinges.is_empty(), "planted record lost its hinges");
    let directions = form.hinges.keys().copied().collect::<Vec<_>>();
    let direct = exact_hinge_coefficients(&record, &directions)?;
    ensure!(
        directions
            .iter()
            .zip(direct)
            .all(|(direction, coefficient)| form.hinges[direction] == coefficient),
        "full-normal-form/direct-DP fixture disagreement"
    );

    let receipt = term_receipt(&record, &form)?;
    let receipts = vec![receipt.clone(), receipt.clone()];
    validate_term_receipts(&receipts, 2)?;
    ensure!(
        expected_labelled_permutations(2)? == 2 * factorial(N)
            && validate_term_receipts(&receipts, 3).is_err(),
        "variable-term census control drift"
    );
    let mut orbit_mutant = receipts.clone();
    orbit_mutant[1].visited_labelled_permutations -= 1;
    ensure!(
        validate_term_receipts(&orbit_mutant, 2).is_err(),
        "omitted final orbit escaped term census"
    );

    let support = [2usize, 7, 11];
    let coefficients = ["5".to_string(), "0".to_string(), "-9".to_string()];
    ensure!(
        nonzero_term_projection(&support, &coefficients)?
            == [
                Term {
                    sequence: 2,
                    coefficient: "5".to_string(),
                },
                Term {
                    sequence: 11,
                    coefficient: "-9".to_string(),
                },
            ],
        "variable support/nonzero projection drift"
    );

    let scale = BigInt::from(4);
    let rationals = ["1/2", "-3/4"];
    let integers = [BigInt::from(2), BigInt::from(-3)];
    for (raw, integer) in rationals.iter().zip(integers.iter()) {
        let (numerator, denominator) = parse_rational(raw)?;
        ensure!(
            &scale % &denominator == BigInt::from(0)
                && numerator * (&scale / denominator) == *integer,
            "primitive rational-clearing fixture drift"
        );
    }
    ensure!(
        integers.iter().cloned().fold(scale, bigint_gcd) == BigInt::from(1),
        "primitive clearing gcd fixture drift"
    );

    let finite_columns = vec![
        vec![BigInt::from(1), BigInt::from(0), BigInt::from(2)],
        vec![BigInt::from(0), BigInt::from(1), BigInt::from(-1)],
    ];
    let finite_coefficients = vec![BigInt::from(2), BigInt::from(-3)];
    let finite_target = vec![BigInt::from(2), BigInt::from(-3), BigInt::from(7)];
    let finite_zero = exact_matrix_residuals(
        &finite_columns,
        &finite_coefficients,
        &finite_target,
        &BigInt::from(1),
    )?;
    let mut finite_mutant_coefficients = finite_coefficients.clone();
    finite_mutant_coefficients[0] += BigInt::from(1);
    let finite_mutant = exact_matrix_residuals(
        &finite_columns,
        &finite_mutant_coefficients,
        &finite_target,
        &BigInt::from(1),
    )?;
    ensure!(
        finite_zero.iter().all(|value| *value == BigInt::from(0))
            && finite_mutant.iter().any(|value| *value != BigInt::from(0))
            && exact_matrix_residuals(
                &finite_columns[..1],
                &finite_coefficients,
                &finite_target,
                &BigInt::from(1),
            )
            .is_err(),
        "exact finite zero/nonzero/coefficient/omission branches drift"
    );

    let mut zero = ExactAggregate::default();
    add_exact(
        &mut zero,
        &record,
        validated_full_normal_form(&record)?,
        &BigInt::from(1),
    )?;
    add_exact(
        &mut zero,
        &record,
        validated_full_normal_form(&record)?,
        &BigInt::from(-1),
    )?;
    let (zero_hinge, zero_linear) = residual_summary(&zero, None, None);
    ensure!(
        zero_hinge.is_none() && zero_linear.is_none(),
        "known exact-zero aggregate did not cancel"
    );
    mutation_control(
        "known_nonzero_normal_form",
        &zero,
        Some((&form, &BigInt::from(1))),
        None,
    )?;

    let ordered_directions = form
        .hinges
        .keys()
        .copied()
        .collect::<BTreeSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    ensure!(
        ordered_directions.len() > CARRY_DIRECTIONS + BATCH_K,
        "planted normal form is too small for census/selection fixtures"
    );
    let accumulated = ordered_directions[..CARRY_DIRECTIONS].to_vec();
    validate_accumulated_directions(&accumulated)?;
    ensure!(
        validate_accumulated_directions(&accumulated[..CARRY_DIRECTIONS - 1]).is_err(),
        "omitted accumulated direction escaped census"
    );

    let mut selection_fixture = ExactAggregate::default();
    for (index, direction) in ordered_directions
        .iter()
        .copied()
        .skip(CARRY_DIRECTIONS)
        .take(BATCH_K + 1)
        .enumerate()
    {
        selection_fixture
            .hinges
            .insert(direction, BigInt::from(index + 1));
    }
    let selected = select_next_batch(&selection_fixture, &accumulated, false)?;
    ensure!(
        select_next_batch(&zero, &accumulated, true)?.is_empty(),
        "exact-zero terminal emitted a residual batch"
    );
    let direction_digest = selected_direction_digest(&selected);
    let coefficient_digest = selected_residual_digest(&selected);
    let mut reordered = selected.clone();
    reordered.swap(0, 1);
    let mut coefficient_mutant = selected.clone();
    coefficient_mutant[0].coefficient =
        (parse_bigint(&coefficient_mutant[0].coefficient)? + BigInt::from(1)).to_string();
    ensure!(
        selected.len() == BATCH_K
            && selected
                .windows(2)
                .all(|pair| pair[0].direction < pair[1].direction)
            && selected_direction_digest(&reordered) != direction_digest
            && selected_residual_digest(&coefficient_mutant) != coefficient_digest,
        "Pool128 order/digest mutation control drift"
    );
    let carried_mutant = [accumulated, vec![selected[0].direction]].concat();
    ensure!(
        validate_accumulated_directions(&carried_mutant).is_err(),
        "carried-direction omission/filter mutation escaped"
    );

    let mut target_fixture = ExactAggregate::default();
    target_fixture.linear[N - 1] = BigInt::from(factorial(N));
    target_fixture.linear[N - 1] -= BigInt::from(factorial(N));
    mutation_control(
        "target_coordinate_plus_one_fixture",
        &target_fixture,
        None,
        Some((N - 1, &BigInt::from(-1))),
    )?;

    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0140-stage-a-publish-self-test-{}-{unique}",
        std::process::id()
    ));
    std::fs::create_dir(&temporary_directory)?;
    let publication = temporary_directory.join("receipt.json");
    publish_exclusive(&publication, b"complete\n")?;
    ensure!(
        std::fs::read(&publication)? == b"complete\n"
            && publish_exclusive(&publication, b"mutant\n").is_err(),
        "exclusive publication control drift"
    );
    std::fs::remove_file(&publication)?;
    let bound_input = temporary_directory.join("bound-input.json");
    std::fs::write(&bound_input, b"original\n")?;
    let temporary_root = temporary_directory.canonicalize()?;
    let binding = Binding {
        path: "bound-input.json".to_string(),
        sha256: sha256_path(&bound_input)?,
    };
    binding_matches(&temporary_root, &binding, "bound-input.json")?;
    std::fs::write(&bound_input, b"mutant\n")?;
    ensure!(
        binding_matches(&temporary_root, &binding, "bound-input.json").is_err(),
        "bound-file hash mutation escaped"
    );
    std::fs::remove_file(&bound_input)?;
    std::fs::remove_dir(&temporary_directory)?;
    Ok(())
}

fn static_preflight() -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    validate_compiled_bytes(&root)?;
    validate_current_release_executable(&root)?;
    for path in [
        PRODUCER_SOURCE_PATH,
        PRODUCER_ENGINE_PATH,
        PRODUCER_CARGO_PATH,
        PRODUCER_LOCK_PATH,
    ] {
        git_commit_for_path(&root, path)?;
    }
    for required in [
        SHARED_MANIFEST_PATH,
        STAGE_A_RECEIPT_PATH,
        STAGE_B_RECEIPT_PATH,
        STAGE_C_RESULT_PATH,
        ANCESTOR_STAGE_D_RESULT_PATH,
        PREREGISTRATION_PATH,
    ] {
        ensure!(
            root.join(required).is_file(),
            "missing declared ancestor: {required}"
        );
    }
    for forbidden in [G0140_MANIFEST_PATH, OUTPUT_PATH] {
        ensure!(
            !root.join(forbidden).exists(),
            "outcome-blind static preflight observed future scientific path: {forbidden}"
        );
    }
    println!("G-0140 Stage A outcome-blind static preflight PASS");
    Ok(())
}

fn ancestor_preflight() -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    validate_compiled_bytes(&root)?;
    let first32 = validate_ancestor_stage_d(&root)?;
    let inputs = load_and_validate_inputs(&root)?;
    validate_accumulated_directions(&inputs.accumulated_directions)?;
    ensure!(
        first32.len() == ANCESTOR_BATCH_K
            && inputs.candidate.terms.len() == 135
            && inputs.accumulated_directions.len() == CARRY_DIRECTIONS,
        "G-0135 ancestor admission census drift"
    );
    println!(
        "G-0140 Stage A ancestor preflight PASS: 135 terms; 100 accumulated rows; disclosed first32 reconciled"
    );
    Ok(())
}

fn full_preflight(manifest_path: &Path, candidate_path: &Path) -> Result<()> {
    ensure!(
        manifest_path == Path::new(G0140_MANIFEST_PATH)
            && candidate_path == Path::new(STAGE_C_RESULT_PATH),
        "preflight input path drift"
    );
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    ensure!(
        !root.join(OUTPUT_PATH).exists(),
        "scientific output already exists"
    );
    validate_ancestor_stage_d(&root)?;
    validate_g0139_gate(&root)?;
    validate_current_release_executable(&root)?;
    validate_g0140_manifest(&root)?;
    let inputs = load_and_validate_inputs(&root)?;
    validate_accumulated_directions(&inputs.accumulated_directions)?;
    println!(
        "G-0140 Stage A preflight PASS: {} target-sufficient selected columns; {} support columns; {} nonzero terms; G-0135 412-row member admitted; no G-0140 scientific output written",
        inputs.candidate.selected_sequences.len(),
        inputs.candidate.support_sequences.len(),
        inputs.candidate.terms.len(),
    );
    Ok(())
}

fn run(manifest_path: &Path, candidate_path: &Path, output_path: &Path) -> Result<()> {
    ensure!(
        manifest_path == Path::new(G0140_MANIFEST_PATH)
            && candidate_path == Path::new(STAGE_C_RESULT_PATH)
            && output_path == Path::new(OUTPUT_PATH),
        "scientific invocation path drift"
    );
    ensure!(!output_path.exists(), "refusing to overwrite output");
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(THREADS)
        .build_global()
        .context("build fixed G-0140 Stage-A thread pool")?;
    let started = Instant::now();
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let inputs = load_and_validate_inputs(&root)?;
    let protocol_manifest = validate_g0140_manifest(&root)?;
    let ancestor_first32 = validate_ancestor_stage_d(&root)?;
    let g0139_result_audit = validate_g0139_gate(&root)?;
    let producer_executable = validate_current_release_executable(&root)?;
    validate_accumulated_directions(&inputs.accumulated_directions)?;
    let candidate = &inputs.candidate;

    let mut aggregate = candidate
        .terms
        .par_iter()
        .map(|term| -> Result<ExactAggregate> {
            let record = &inputs.panel.records[term.sequence];
            let coefficient = parse_bigint(&term.coefficient)?;
            let form = validated_full_normal_form(record)?;
            let mut output = ExactAggregate::default();
            add_exact(&mut output, record, form, &coefficient)?;
            Ok(output)
        })
        .try_reduce(
            ExactAggregate::default,
            |left, right| -> Result<ExactAggregate> { Ok(merge_exact(left, right)) },
        )?;
    aggregate
        .term_receipts
        .sort_by_key(|receipt| receipt.sequence);
    let labelled_expected = expected_labelled_permutations(candidate.terms.len())?;
    ensure!(
        aggregate.terms == candidate.terms.len()
            && aggregate.labelled_permutations_checked == labelled_expected
            && aggregate
                .term_receipts
                .iter()
                .map(|receipt| receipt.sequence)
                .eq(candidate.terms.iter().map(|term| term.sequence)),
        "dynamic term/orbit transcript drift"
    );
    validate_term_receipts(&aggregate.term_receipts, candidate.terms.len())?;
    let target_subtraction = parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N));
    aggregate.linear[N - 1] -= &target_subtraction;

    let direct =
        direct_accumulated_prices(&inputs.panel, candidate, &inputs.accumulated_directions)?;
    let independent_finite_412_row_replay = independent_finite_replay(
        &root,
        &inputs.panel,
        candidate,
        &inputs.accumulated_directions,
    )?;
    ensure!(
        independent_finite_412_row_replay.all_rows_exactly_replayed
            && independent_finite_412_row_replay.residuals_decimal_lf_sha256
                == zero_lf_digest(ROWS)
            && independent_finite_412_row_replay
                .coefficient_plus_one_mutant
                .rejected,
        "independent finite-row replay receipt drift"
    );
    let accumulated_direction_checks = inputs
        .accumulated_directions
        .iter()
        .enumerate()
        .map(|(index, direction)| {
            let aggregate_coefficient =
                aggregate.hinges.get(direction).cloned().unwrap_or_default();
            let routes_agree = aggregate_coefficient == direct[index];
            AccumulatedDirectionCheck {
                index,
                source: if index < OLD_CARRY_DIRECTIONS {
                    "G0128_ACCUMULATED_68"
                } else {
                    "G0135_STAGE_A_BATCH32"
                },
                source_index: if index < OLD_CARRY_DIRECTIONS {
                    index
                } else {
                    index - OLD_CARRY_DIRECTIONS
                },
                direction: *direction,
                aggregate_coefficient: aggregate_coefficient.to_string(),
                direct_dp_coefficient: direct[index].to_string(),
                routes_agree,
                exact_zero: aggregate_coefficient == BigInt::from(0)
                    && direct[index] == BigInt::from(0),
            }
        })
        .collect::<Vec<_>>();
    ensure!(
        accumulated_direction_checks.len() == CARRY_DIRECTIONS
            && accumulated_direction_checks
                .iter()
                .all(|check| check.routes_agree && check.exact_zero),
        "full-normal-form/direct-DP accumulated-row replay failed"
    );
    let all_linear_zero = aggregate
        .linear
        .iter()
        .all(|value| *value == BigInt::from(0));
    ensure!(all_linear_zero, "one of 11 linear residuals is nonzero");

    let nonzero_hinge_directions = aggregate
        .hinges
        .values()
        .filter(|coefficient| **coefficient != BigInt::from(0))
        .count();
    let global_zero = nonzero_hinge_directions == 0;
    let result = if global_zero {
        ZERO_RESULT
    } else {
        RESIDUAL_RESULT
    };
    let (first_nonzero_hinge, first_nonzero_linear) = residual_summary(&aggregate, None, None);
    ensure!(
        first_nonzero_linear.is_none() && (global_zero == first_nonzero_hinge.is_none()),
        "terminal residual summary drift"
    );
    let next_selected = select_next_batch(&aggregate, &inputs.accumulated_directions, global_zero)?;
    let next_direction_digest = selected_direction_digest(&next_selected);
    let next_coefficient_digest = selected_residual_digest(&next_selected);
    let all_hinge_digest = hinge_digest(&aggregate.hinges, false);
    let nonzero_hinge_digest = hinge_digest(&aggregate.hinges, true);
    let complete_residual_digest = residual_digest(&aggregate, None, None);
    let term_transcript_digest = sha256_bytes(&serde_json::to_vec(&aggregate.term_receipts)?);
    ensure!(
        result == RESIDUAL_RESULT
            && aggregate.terms == 135
            && aggregate.labelled_permutations_checked == 5_388_768_000
            && aggregate.hinge_entries_processed == 4_409_740
            && aggregate.hinges.len() == 147_062
            && nonzero_hinge_directions == 146_950
            && all_hinge_digest == ANCESTOR_AGGREGATE_HINGE_SHA256
            && nonzero_hinge_digest == ANCESTOR_NONZERO_HINGE_SHA256
            && complete_residual_digest == ANCESTOR_COMPLETE_RESIDUAL_SHA256
            && term_transcript_digest == ANCESTOR_TERM_TRANSCRIPT_SHA256
            && first_nonzero_hinge.as_ref()
                == Some(&ExactHinge {
                    direction: ANCESTOR_FIRST_DIRECTION,
                    coefficient: ANCESTOR_FIRST_COEFFICIENT.to_string(),
                })
            && next_selected[..ANCESTOR_BATCH_K] == ancestor_first32
            && selected_direction_digest(&next_selected[..ANCESTOR_BATCH_K])
                == ANCESTOR_FIRST32_DIRECTIONS_SHA256
            && selected_residual_digest(&next_selected[..ANCESTOR_BATCH_K])
                == ANCESTOR_FIRST32_RESIDUALS_SHA256,
        "independent G-0140 replay disagrees with a disclosed G-0135 Stage-D anchor"
    );

    let first_term = candidate.terms.first().context("first term missing")?;
    let final_term = candidate.terms.last().context("final term missing")?;
    let first_form = validated_full_normal_form(&inputs.panel.records[first_term.sequence])?;
    let final_form = validated_full_normal_form(&inputs.panel.records[final_term.sequence])?;
    let one = BigInt::from(1);
    let coefficient_plus_one = mutation_control(
        "first_nonzero_coefficient_plus_one",
        &aggregate,
        Some((&first_form, &one)),
        None,
    )?;
    let target_scale_plus_one = mutation_control(
        "target_scale_plus_one",
        &aggregate,
        None,
        Some((N - 1, &-BigInt::from(factorial(N)))),
    )?;
    let target_coordinate_plus_one = mutation_control(
        "target_coordinate_10_plus_one",
        &aggregate,
        None,
        Some((N - 1, &BigInt::from(-1))),
    )?;
    let omitted_final_term = mutation_control(
        "omitted_final_nonzero_term",
        &aggregate,
        Some((&final_form, &-parse_bigint(&final_term.coefficient)?)),
        None,
    )?;
    let omitted_direction = first_form
        .hinges
        .keys()
        .copied()
        .min()
        .context("first term has no active hinge")?;
    let mut one_hinge = HashMap::new();
    one_hinge.insert(
        omitted_direction,
        first_form
            .hinges
            .get(&omitted_direction)
            .context("omitted hinge disappeared")?
            .clone(),
    );
    let omitted_form = ExactNormalForm {
        linear: std::array::from_fn(|_| BigInt::from(0)),
        hinges: one_hinge,
        labelled_permutations: factorial(N),
        compressed_leaves: factorial(N),
    };
    let omitted_first_term_direction = mutation_control(
        "omitted_first_term_active_direction",
        &aggregate,
        Some((&omitted_form, &-parse_bigint(&first_term.coefficient)?)),
        None,
    )?;

    let mut orbit_mutant = aggregate.term_receipts.clone();
    orbit_mutant
        .last_mut()
        .context("final term receipt missing")?
        .visited_labelled_permutations -= 1;
    let census_controls = CensusControls {
        dynamic_term_count: candidate.terms.len(),
        factorial_11: factorial(N),
        expected_labelled_permutations: labelled_expected,
        observed_labelled_permutations: aggregate.labelled_permutations_checked,
        per_term_generated_equals_visited_equals_accepted: aggregate.term_receipts.iter().all(
            |receipt| {
                receipt.generated_labelled_permutations == receipt.visited_labelled_permutations
                    && receipt.visited_labelled_permutations
                        == receipt.accepted_labelled_permutations
                    && receipt.accepted_labelled_permutations == factorial(N)
            },
        ),
        zero_skipped_unclassified_failed: aggregate.term_receipts.iter().all(|receipt| {
            receipt.skipped_labelled_permutations == 0
                && receipt.unclassified_labelled_permutations == 0
                && receipt.failed_labelled_permutations == 0
        }),
        omitted_last_orbit_rejected: validate_term_receipts(&orbit_mutant, candidate.terms.len())
            .is_err(),
        decremented_global_census_rejected: aggregate.labelled_permutations_checked.checked_sub(1)
            != Some(labelled_expected),
        accumulated_direction_count_100: inputs.accumulated_directions.len() == CARRY_DIRECTIONS,
        omitted_accumulated_direction_rejected: validate_accumulated_directions(
            &inputs.accumulated_directions[..CARRY_DIRECTIONS - 1],
        )
        .is_err(),
    };
    ensure!(
        census_controls.per_term_generated_equals_visited_equals_accepted
            && census_controls.zero_skipped_unclassified_failed
            && census_controls.omitted_last_orbit_rejected
            && census_controls.decremented_global_census_rejected
            && census_controls.accumulated_direction_count_100
            && census_controls.omitted_accumulated_direction_rejected,
        "census hostile control failed"
    );

    let selection_controls = if global_zero {
        SelectionControls {
            exact_batch_count_or_zero_terminal: next_selected.is_empty(),
            strict_signed_lexicographic_order: true,
            excludes_accumulated_directions: true,
            direction_reordering_changes_digest: true,
            coefficient_plus_one_changes_digest: true,
        }
    } else {
        let mut reordered = next_selected.clone();
        reordered.swap(0, 1);
        let mut coefficient_mutant = next_selected.clone();
        coefficient_mutant[0].coefficient =
            (parse_bigint(&coefficient_mutant[0].coefficient)? + BigInt::from(1)).to_string();
        let accumulated = inputs
            .accumulated_directions
            .iter()
            .copied()
            .collect::<HashSet<_>>();
        SelectionControls {
            exact_batch_count_or_zero_terminal: next_selected.len() == BATCH_K,
            strict_signed_lexicographic_order: next_selected
                .windows(2)
                .all(|pair| pair[0].direction < pair[1].direction),
            excludes_accumulated_directions: next_selected
                .iter()
                .all(|item| !accumulated.contains(&item.direction)),
            direction_reordering_changes_digest: selected_direction_digest(&reordered)
                != next_direction_digest,
            coefficient_plus_one_changes_digest: selected_residual_digest(&coefficient_mutant)
                != next_coefficient_digest,
        }
    };
    ensure!(
        selection_controls.exact_batch_count_or_zero_terminal
            && selection_controls.strict_signed_lexicographic_order
            && selection_controls.excludes_accumulated_directions
            && selection_controls.direction_reordering_changes_digest
            && selection_controls.coefficient_plus_one_changes_digest,
        "Pool128 hostile control failed"
    );

    let source_and_audit_bindings = inputs
        .manifest
        .bindings_by_path
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
        result,
        claim_boundary: CLAIM_BOUNDARY,
        g0140_manifest: Binding {
            path: G0140_MANIFEST_PATH.to_string(),
            sha256: protocol_manifest.sha256.clone(),
        },
        g0135_manifest: Binding {
            path: SHARED_MANIFEST_PATH.to_string(),
            sha256: inputs.manifest.sha256.clone(),
        },
        protocol: binding_for_path(&root, PREREGISTRATION_PATH)?,
        producer_source: binding_for_path(&root, PRODUCER_SOURCE_PATH)?,
        producer_engine: binding_for_path(&root, PRODUCER_ENGINE_PATH)?,
        producer_executable,
        g0139_result_audit,
        ancestor_stage_d_result: binding_for_path(&root, ANCESTOR_STAGE_D_RESULT_PATH)?,
        stage_c_member: inputs.candidate_binding.clone(),
        source_and_audit_bindings,
        candidate_schema: candidate.schema.clone(),
        candidate_result: candidate.result.clone(),
        rows: candidate.rows,
        records: candidate.records,
        selected_rank: candidate.rank,
        support_columns: candidate.support_sequences.len(),
        terms: candidate.terms.len(),
        target_scale: candidate.target_scale.clone(),
        target_subtraction_coordinate_10: target_subtraction.to_string(),
        stage_c_all_412_rational_rows_replayed: candidate.replay_receipt.rational_all_rows_replayed,
        stage_c_all_412_integer_rows_replayed: candidate.replay_receipt.integer_all_rows_replayed,
        stage_c_primitive_denominator_clearing: candidate
            .replay_receipt
            .primitive_denominator_clearing,
        stage_c_coefficient_plus_one_mutant_rejected: candidate
            .coefficient_plus_one_mutant
            .rejected,
        stage_c_prior_scale_carryover_mutant_rejected: candidate
            .prior_target_scale_carryover_mutant_rejected,
        independent_finite_412_row_replay,
        arithmetic: "signed_num_bigint_BigInt_unconditional_exact",
        decision_rule: DECISION_RULE,
        complete_global_replay: true,
        all_hinge_and_linear_residuals_zero: global_zero && all_linear_zero,
        labelled_permutations_expected: labelled_expected,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        aggregate_hinge_support: aggregate.hinges.len(),
        nonzero_hinge_directions,
        aggregate_hinge_decimal_lf_sha256: all_hinge_digest,
        nonzero_hinge_decimal_lf_sha256: nonzero_hinge_digest,
        complete_residual_decimal_lf_sha256: complete_residual_digest,
        term_normal_form_transcript_sha256: term_transcript_digest,
        term_normal_forms: aggregate.term_receipts,
        accumulated_direction_checks,
        all_100_accumulated_directions_exact_zero: true,
        linear_residuals_after_target: aggregate.linear.iter().map(ToString::to_string).collect(),
        all_11_linear_residuals_exact_zero: all_linear_zero,
        first_nonzero_hinge,
        first_nonzero_linear,
        pool_k: if global_zero { 0 } else { BATCH_K },
        pool_count: next_selected.len(),
        pool_directions_i8_sha256: next_direction_digest,
        pool_exact_residuals_decimal_lf_sha256: next_coefficient_digest,
        pool: next_selected,
        coefficient_plus_one,
        target_scale_plus_one,
        target_coordinate_plus_one,
        omitted_final_term,
        omitted_first_term_direction,
        census_controls,
        selection_controls,
        inputs_rehashed_at_end: true,
        manifest_rehashed_at_end: true,
        candidate_rehashed_at_end: true,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let stdout = serde_json::json!({
        "result": output.result,
        "terms": output.terms,
        "labelled_permutations_checked": output.labelled_permutations_checked,
        "nonzero_hinge_directions": output.nonzero_hinge_directions,
        "pool_count": output.pool_count,
        "pool_directions_i8_sha256": output.pool_directions_i8_sha256,
        "pool_exact_residuals_decimal_lf_sha256": output.pool_exact_residuals_decimal_lf_sha256,
    });
    let mut serialized = serde_json::to_vec_pretty(&output)?;
    serialized.push(b'\n');

    let end = load_and_validate_inputs(&root)?;
    let end_protocol_manifest = validate_g0140_manifest(&root)?;
    let end_audit = validate_g0139_gate(&root)?;
    let end_executable = validate_current_release_executable(&root)?;
    ensure!(
        end.manifest.sha256 == inputs.manifest.sha256
            && end_protocol_manifest.sha256 == output.g0140_manifest.sha256
            && end_protocol_manifest.bindings_by_path == protocol_manifest.bindings_by_path
            && end.manifest.bindings_by_path == inputs.manifest.bindings_by_path
            && end.candidate_binding == inputs.candidate_binding
            && end.candidate.terms == candidate.terms
            && end.accumulated_directions == inputs.accumulated_directions
            && end_audit == output.g0139_result_audit
            && end_executable == output.producer_executable
            && binding_for_path(&root, ANCESTOR_STAGE_D_RESULT_PATH)?
                == output.ancestor_stage_d_result
            && binding_for_path(&root, PREREGISTRATION_PATH)? == output.protocol
            && binding_for_path(&root, PRODUCER_SOURCE_PATH)? == output.producer_source
            && binding_for_path(&root, PRODUCER_ENGINE_PATH)? == output.producer_engine,
        "input/source/audit drift during G-0140 Stage-A replay"
    );
    publish_exclusive(output_path, &serialized)?;
    println!("{stdout}");
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() == 2 && args[1] == "--self-test" {
        self_test()?;
        println!("G-0140 Stage A self-test PASS");
        return Ok(());
    }
    if args.len() == 2 && args[1] == "--preflight-ancestor" {
        return ancestor_preflight();
    }
    if args.len() == 2 && args[1] == "--preflight-static" {
        return static_preflight();
    }
    if args.len() == 4 && args[1] == "--preflight" {
        return full_preflight(Path::new(&args[2]), Path::new(&args[3]));
    }
    ensure!(
        args.len() == 4,
        "usage: g0140-stage-a-pool128-global-replay --self-test | --preflight-ancestor | --preflight-static | --preflight G0140_MANIFEST G0135_STAGE_C_MEMBER | G0140_MANIFEST G0135_STAGE_C_MEMBER OUTPUT"
    );
    run(
        Path::new(&args[1]),
        Path::new(&args[2]),
        Path::new(&args[3]),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn producer_self_test() {
        self_test().unwrap();
    }
}
