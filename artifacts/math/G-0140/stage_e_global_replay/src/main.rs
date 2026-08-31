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
const BASE_ROWS: usize = ROWS;
const MAX_STAGE_D_APPENDED_ROWS: usize = 32;
const INHERITED_DIRECTIONS: usize = CARRY_DIRECTIONS;
const ANCESTOR_BATCH_K: usize = 32;
const RESIDUAL_PREFIX_K: usize = 128;
const BATCH_K: usize = RESIDUAL_PREFIX_K;
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
const G0139_AUDIT_PATH: &str = "artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json";
const G0139_AUDIT_SHA256: &str = "282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f";
const G0139_AUDIT_COMMIT: &str = "0bfdbf2db065d8517ad2d98d762473fed052cb54";
const G0139_EVIDENCE_CLASS: &str = "T1_SAME_LINEAGE_OUTCOME_AWARE_RESULT_AUDIT";
const G0139_CLAIM_BOUNDARY: &str = "Consistency only for the exact committed 135-term Stage-C member and exact G-0135 Stage-D result bytes. Same-lineage outcome-aware T1 evidence; no T2 independence, family completeness, frozen-family nonmembership, MAX11 lower bound, unrestricted nonrepresentability, all-n theorem, refereed status, formalization, or Lean theorem.";
const G0140_MANIFEST_PATH: &str = "artifacts/math/G-0140/pool128_manifest_v1.json";
const G0140_STAGE_A_RESULT_PATH: &str = "artifacts/math/G-0140/pool128_global_replay_v1.json";
const STAGE_B_OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_coordinate_prices_v1.json";
const STAGE_C_OUTPUT_PATH: &str = "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json";
const STAGE_D_OUTPUT_PATH: &str = "artifacts/math/G-0140/rank_aware_master_result_v1.json";
const STAGE_E_OUTPUT_PATH: &str = "artifacts/math/G-0140/new_member_global_replay_v1.json";
const STAGE_D_SOURCE_PATH_G0140: &str =
    "artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py";
const STAGE_D_SOURCE_SHA256_G0140: &str =
    "6112c55f943c20acd80402a9800db581c1ee6d5caf35c2f418d2a52cf09ad03e";
const STAGE_D_SOURCE_COMMIT_G0140: &str = "69a3449c7bc291f283c10c669e5d39f2a1212782";
const STAGE_D_SOURCE_AUDIT_PATH_G0140: &str =
    "artifacts/reviews/G-0155-g0140-stage-d-master-final2-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_D_SOURCE_AUDIT_PREREG_PATH_G0140: &str =
    "artifacts/reviews/G-0155-g0140-stage-d-master-final2-source/PREREGISTRATION.md";
const STAGE_D_SOURCE_AUDIT_SCHEMA_G0140: &str =
    "max11-g0155-g0140-stage-d-master-final2-source-audit-v1";
const STAGE_D_SOURCE_AUDIT_CLAIM_G0140: &str = "T1 source/custody clearance for the exact frozen G-0140 reopened-master producer bytes only; no scientific manifest, input, or output was observed, no scientific column-generation run was executed, and no mathematical claim is promoted.";
const STAGE_D_SOURCE_AUDIT_NO_CLAIM_G0140: &str = "This source audit does not adjudicate any future G-0140 scientific manifest or result and does not establish family membership, family nonmembership, a MAX11 identity, a lower bound, unrestricted nonrepresentability, minimality, an all-n theorem, refereed status, formalization, or a Lean theorem.";
const STAGE_E_SOURCE_PATH: &str = "artifacts/math/G-0140/stage_e_global_replay/src/main.rs";
const STAGE_E_ENGINE_PATH: &str = "artifacts/math/G-0140/stage_e_global_replay/src/engine.rs";
const STAGE_E_CARGO_PATH: &str = "artifacts/math/G-0140/stage_e_global_replay/Cargo.toml";
const STAGE_E_LOCK_PATH: &str = "artifacts/math/G-0140/stage_e_global_replay/Cargo.lock";
const STAGE_E_EXECUTABLE_PATH: &str =
    "artifacts/math/G-0140/stage_e_global_replay/target/release/g0140-stage-e-global-replay";
const STAGE_E_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0156-g0140-stage-e-global-replay-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_E_SOURCE_AUDIT_PREREG_PATH: &str =
    "artifacts/reviews/G-0156-g0140-stage-e-global-replay-source/PREREGISTRATION.md";
const STAGE_E_SOURCE_AUDIT_SCHEMA: &str = "max11-g0156-g0140-stage-e-global-replay-source-audit-v1";
const STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS: &str = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT";
const STAGE_E_SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen G-0140 Stage-E complete-global-replay producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.";
const STAGE_E_SOURCE_AUDIT_NO_CLAIM: &str = "This source audit does not adjudicate any future G-0140 scientific manifest or result, establish or exclude a global exact identity, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem.";
const G0140_STAGE_A_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0150-g0140-stage-a-final2-source/SOURCE_AUDIT_RECEIPT.json";
const G0140_STAGE_A_SOURCE_AUDIT_PREREG_PATH: &str =
    "artifacts/reviews/G-0150-g0140-stage-a-final2-source/PREREGISTRATION.md";
const G0140_STAGE_A_SOURCE_AUDIT_SCHEMA: &str = "max11-g0150-g0140-stage-a-final2-source-audit-v1";
const SOURCE_CUSTODY_PASS_RESULT: &str = "SOURCE_CUSTODY_AUDIT_PASS_T1";
const G0140_STAGE_A_SOURCE_AUDIT_EVIDENCE_CLASS: &str =
    "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT";
const G0140_STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen Stage-A producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.";
const G0140_STAGE_A_SOURCE_AUDIT_NO_CLAIM: &str = "This source audit does not adjudicate a G-0140 scientific manifest or result, establish or exclude a Pool128 member, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem.";
const PRIOR_MASTER_RESULT_PATH: &str = "artifacts/math/G-0128/full_family_master_result_v2.json";
const PRIOR_MASTER_MANIFEST_PATH: &str =
    "artifacts/math/G-0128/full_family_master_manifest_v2.json";
const PRIOR_MASTER_SOURCE_PATH: &str = "artifacts/math/G-0128/full_family_master_v2.py";
const EXACT_Q_CORE_PATH: &str = "artifacts/math/G-0117/fresh_q_cegis_exact.py";

const PREREGISTRATION_PATH: &str = "artifacts/math/G-0140/PREREGISTRATION.md";
const ANCESTOR_PREREGISTRATION_PATH: &str = "artifacts/math/G-0135/PREREGISTRATION.md";
const G0140_STAGE_A_SOURCE_PATH: &str = "artifacts/math/G-0140/stage_a_pool/src/main.rs";
const G0140_STAGE_A_ENGINE_PATH: &str = "artifacts/math/G-0140/stage_a_pool/src/engine.rs";
const G0140_STAGE_A_CARGO_PATH: &str = "artifacts/math/G-0140/stage_a_pool/Cargo.toml";
const G0140_STAGE_A_LOCK_PATH: &str = "artifacts/math/G-0140/stage_a_pool/Cargo.lock";
const G0140_STAGE_A_EXECUTABLE_PATH: &str =
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
const G0140_STAGE_A_OUTPUT_SCHEMA: &str = "max11-g0140-pool128-global-replay-v1";
const STAGE_B_OUTPUT_SCHEMA: &str = "max11-g0140-pool128-coordinate-prices-v1";
const STAGE_C_OUTPUT_SCHEMA: &str = "max11-g0140-pool128-exact-rank-selection-v1";
const STAGE_D_OUTPUT_SCHEMA: &str = "max11-g0140-rank-aware-master-result-v1";
const STAGE_E_OUTPUT_SCHEMA: &str = "max11-g0140-new-member-global-replay-v1";
const ZERO_RESULT: &str = "GLOBAL_EXACT_ZERO";
const ANCESTOR_RESIDUAL_RESULT: &str = "EXACT_RESIDUAL_BATCH_CONTINUE";
const STAGE_A_RESIDUAL_RESULT: &str = "EXACT_RESIDUAL_POOL128";
const RESIDUAL_RESULT: &str = "EXACT_RESIDUAL_CONTINUE";
const STAGE_D_MEMBER_RESULT: &str = "RANK_AWARE_SELECTED_ROWS_EXACT_Q_MEMBER";
const DECISION_RULE: &str = "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate";
const CLAIM_BOUNDARY: &str = "GLOBAL_EXACT_ZERO establishes only the complete arbitrary-precision ordered-chamber normal form identity for the exact frozen G-0140 Stage-D member. EXACT_RESIDUAL_CONTINUE refutes only that member and reports the deterministic signed-lexicographic residual prefix without opening another study. Neither branch proves family completeness, an unrestricted theorem, a lower bound, minimality, the all-n target, refereed status, formalization, or a Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_ENGINE: &[u8] = include_bytes!("engine.rs");
const COMPILED_STAGE_A_ENGINE: &[u8] = include_bytes!("../../stage_a_pool/src/engine.rs");
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

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditReviewer {
    agent_name: String,
    program: String,
    model: String,
    same_model_lineage: bool,
    fresh_context: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditPreregistration {
    path: String,
    sha256: String,
    git_commit: String,
    committed_and_pushed_before_subject_source_inspection: bool,
    committed_and_pushed_before_runtime_checks: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditBindings {
    main_source: Binding,
    engine_source: Binding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    release_executable: Binding,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditSubject {
    git_commit: String,
    commit_object_and_working_bytes_equal_for_all_bindings: bool,
    bindings: FinalStageASourceAuditBindings,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
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

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct FinalStageASourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: FinalStageASourceAuditReviewer,
    preregistration: FinalStageASourceAuditPreregistration,
    subject: FinalStageASourceAuditSubject,
    required_checks: FinalStageASourceAuditChecks,
    scientific_manifest_observed: bool,
    scientific_input_observed: bool,
    scientific_output_observed: bool,
    scientific_replay_run: bool,
    no_claim: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageESourceAuditChecks {
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
    compiled_source_manifest_lock_match_working_bytes: bool,
    engine_byte_identity_with_stage_a_verified: bool,
    g0155_stage_d_source_audit_gate_verified: bool,
    scientific_output_commit_chain_gate_verified: bool,
    dynamic_stage_d_member_contract_verified: bool,
    global_zero_and_residual_branches_verified: bool,
    complete_label_census_and_end_rehash_verified: bool,
    overwrite_refusal_verified: bool,
    prohibited_scientific_modes_not_run: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageESourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: FinalStageASourceAuditReviewer,
    preregistration: FinalStageASourceAuditPreregistration,
    subject: FinalStageASourceAuditSubject,
    required_checks: StageESourceAuditChecks,
    scientific_manifest_observed: bool,
    scientific_input_observed: bool,
    scientific_output_observed: bool,
    scientific_replay_run: bool,
    no_claim: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageDSourceAuditBindings {
    master_source: Binding,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageDSourceAuditSubject {
    git_commit: String,
    commit_object_and_working_bytes_equal_for_all_bindings: bool,
    bindings: StageDSourceAuditBindings,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageDSourceAuditChecks {
    exact_named_binding_contract: bool,
    displaced_recursive_lookalikes_rejected: bool,
    correct_decoy_with_missing_named_binding_rejected: bool,
    unknown_envelope_fields_rejected: bool,
    audit_git_commit_rejected: bool,
    duplicate_json_keys_rejected: bool,
    trailing_json_data_rejected: bool,
    imported_exact_core_binding_verified: bool,
    future_input_gate_verified: bool,
    exact_column_generation_protocol_verified: bool,
    member_and_separator_fixtures_verified: bool,
    committed_blob_custody_verified: bool,
    producer_self_test_passed: bool,
    producer_static_preflight_passed: bool,
    prohibited_scientific_modes_not_run: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct StageDSourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: FinalStageASourceAuditReviewer,
    preregistration: FinalStageASourceAuditPreregistration,
    subject: StageDSourceAuditSubject,
    required_checks: StageDSourceAuditChecks,
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

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct MemberRankTrial {
    iteration: usize,
    rank: usize,
    augmented_rank: usize,
    result: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct SeparatorRankTrial {
    iteration: usize,
    rank: usize,
    augmented_rank: usize,
    separator_target_pairing: String,
    separator_free_row: usize,
    first_violating_sequence: usize,
    first_violating_price: String,
    columns_scanned: usize,
    scanned_prices_decimal_lf_sha256: String,
    result: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(untagged)]
enum RankTrial {
    Member(MemberRankTrial),
    Separator(SeparatorRankTrial),
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageDMember {
    schema: String,
    result: String,
    claim_boundary: String,
    manifest: Binding,
    stage_a_receipt: Binding,
    stage_b_receipt: Binding,
    stage_c_receipt: Binding,
    source_audit: Binding,
    solver: Binding,
    records: usize,
    base_rows: usize,
    selected_pool_indices: Vec<usize>,
    selected_pool_indices_u64le_sha256: String,
    selected_directions: Vec<[i8; N]>,
    selected_directions_i8_sha256: String,
    appended_rows: usize,
    rows: usize,
    target: Vec<String>,
    target_i128le_sha256: String,
    target_construction: String,
    initial_selected_sequences: Vec<usize>,
    initial_selected_sequences_u64le_sha256: String,
    initial_rank: usize,
    all_columns_reopened: bool,
    canonical_column_order: bool,
    no_modular_terminal_decision: bool,
    no_support_freeze: bool,
    no_zero_price_column_deletion: bool,
    no_row_dependency_deletion: bool,
    no_preferred_sparsity_search: bool,
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
    trials: Vec<RankTrial>,
    input_snapshot_sha256: String,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

#[derive(Clone, Debug, Deserialize)]
struct StageAPoolView {
    schema: String,
    result: String,
    g0140_manifest: Binding,
    complete_global_replay: bool,
    all_hinge_and_linear_residuals_zero: bool,
    accumulated_direction_checks: Vec<AccumulatedDirectionCheck>,
    all_100_accumulated_directions_exact_zero: bool,
    pool_k: usize,
    pool_count: usize,
    pool_directions_i8_sha256: String,
    pool_exact_residuals_decimal_lf_sha256: String,
    pool: Vec<ExactHinge>,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    candidate_rehashed_at_end: bool,
}

#[derive(Clone, Debug, Deserialize)]
struct StageCRankSelectionView {
    result: String,
    selected_pool_indices: Vec<usize>,
    selected_count: usize,
    selected_system_rank: usize,
    all_pool_rows_compatibility_checked: bool,
    compatibility_decision_complete: bool,
    no_modular_row_selection: bool,
}

#[derive(Clone, Debug, Deserialize)]
struct StageCSelectionView {
    schema: String,
    result: String,
    manifest: Binding,
    stage_a_receipt: Binding,
    stage_b_receipt: Binding,
    rank_selection: StageCRankSelectionView,
    inputs_rehashed_at_end: bool,
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

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
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
    expected_accumulated_direction_count: usize,
    observed_accumulated_direction_count: usize,
    accumulated_direction_count_exact: bool,
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
    selected_basis_columns: usize,
    selected_basis_i128le_sha256: String,
    selected_basis_digest_replayed: bool,
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
    producer_cargo_manifest: Binding,
    producer_cargo_lock: Binding,
    producer_executable: Binding,
    stage_e_source_audit: Binding,
    stage_d_member: Binding,
    stage_output_git_commits: BTreeMap<String, String>,
    source_and_audit_bindings: BTreeMap<String, Binding>,
    candidate_schema: String,
    candidate_result: String,
    base_rows: usize,
    appended_rows: usize,
    rows: usize,
    records: usize,
    selected_pool_indices: Vec<usize>,
    selected_pool_indices_u64le_sha256: String,
    selected_directions: Vec<[i8; N]>,
    selected_directions_i8_sha256: String,
    selected_rank: usize,
    support_columns: usize,
    terms: usize,
    target_scale: String,
    target_subtraction_coordinate_10: String,
    stage_d_all_rational_rows_replayed: bool,
    stage_d_all_integer_rows_replayed: bool,
    stage_d_primitive_denominator_clearing: bool,
    stage_d_coefficient_plus_one_mutant_rejected: bool,
    stage_d_prior_scale_carryover_mutant_rejected: bool,
    independent_finite_row_replay: FiniteReplayReceipt,
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
    inherited_accumulated_directions: usize,
    stage_d_selected_accumulated_directions: usize,
    accumulated_direction_count: usize,
    all_accumulated_directions_exact_zero: bool,
    linear_residuals_after_target: Vec<String>,
    all_11_linear_residuals_exact_zero: bool,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
    residual_prefix_k: usize,
    residual_prefix_count: usize,
    residual_prefix_directions_i8_sha256: String,
    residual_prefix_exact_residuals_decimal_lf_sha256: String,
    residual_prefix: Vec<ExactHinge>,
    no_automatic_next_study: bool,
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

fn git_is_ancestor(root: &Path, ancestor: &str, descendant: &str, label: &str) -> Result<()> {
    ensure!(
        ancestor.len() == 40
            && descendant.len() == 40
            && ancestor.bytes().all(|byte| byte.is_ascii_hexdigit())
            && descendant.bytes().all(|byte| byte.is_ascii_hexdigit()),
        "invalid Git ancestry identity: {label}"
    );
    let status = Command::new("git")
        .args(["merge-base", "--is-ancestor", ancestor, descendant])
        .current_dir(root)
        .status()?;
    ensure!(status.success(), "Git ancestry failed: {label}");
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

fn validate_optional_strict_axis(values: &[usize], upper: usize, name: &str) -> Result<()> {
    ensure!(
        values.windows(2).all(|pair| pair[0] < pair[1]),
        "{name} is not strictly increasing"
    );
    ensure!(
        values.iter().all(|value| *value < upper),
        "{name} outside range"
    );
    Ok(())
}

fn direction_digest(directions: &[[i8; N]]) -> String {
    let mut digest = Sha256::new();
    for direction in directions {
        for coordinate in direction {
            digest.update([*coordinate as u8]);
        }
    }
    format!("{:x}", digest.finalize())
}

fn pool_directions_at(pool: &[ExactHinge], selected_indices: &[usize]) -> Result<Vec<[i8; N]>> {
    validate_optional_strict_axis(selected_indices, pool.len(), "selected pool indices")?;
    selected_indices
        .iter()
        .map(|index| {
            pool.get(*index)
                .map(|item| item.direction)
                .with_context(|| format!("selected pool index outside pool: {index}"))
        })
        .collect()
}

fn validate_exact_object_keys(value: &Value, expected: &[&str], label: &str) -> Result<()> {
    let object = value
        .as_object()
        .with_context(|| format!("{label} must be a JSON object"))?;
    let expected_set = expected.iter().copied().collect::<BTreeSet<_>>();
    let observed = object.keys().map(String::as_str).collect::<BTreeSet<_>>();
    ensure!(
        expected_set.len() == expected.len() && observed == expected_set,
        "{label} key-set drift"
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
    let expected = root.join(STAGE_E_EXECUTABLE_PATH).canonicalize()?;
    ensure!(
        executable == expected,
        "scientific preflight/run requires the frozen release executable"
    );
    git_commit_for_path(root, STAGE_E_EXECUTABLE_PATH)?;
    Ok(Binding {
        path: STAGE_E_EXECUTABLE_PATH.to_string(),
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

fn final_stage_a_source_audit_bindings(
    receipt: &FinalStageASourceAuditReceipt,
) -> [(&'static str, &Binding); 5] {
    [
        (
            G0140_STAGE_A_SOURCE_PATH,
            &receipt.subject.bindings.main_source,
        ),
        (
            G0140_STAGE_A_ENGINE_PATH,
            &receipt.subject.bindings.engine_source,
        ),
        (
            G0140_STAGE_A_CARGO_PATH,
            &receipt.subject.bindings.cargo_manifest,
        ),
        (
            G0140_STAGE_A_LOCK_PATH,
            &receipt.subject.bindings.cargo_lock,
        ),
        (
            G0140_STAGE_A_EXECUTABLE_PATH,
            &receipt.subject.bindings.release_executable,
        ),
    ]
}

fn final_stage_a_source_audit_receipt(receipt: &Value) -> Result<FinalStageASourceAuditReceipt> {
    serde_json::from_value(receipt.clone())
        .context("strict final Stage-A source-audit schema validation")
}

fn validate_final_stage_a_source_audit_semantics(
    receipt: &FinalStageASourceAuditReceipt,
) -> Result<()> {
    ensure!(
        receipt.schema == G0140_STAGE_A_SOURCE_AUDIT_SCHEMA
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_CUSTODY_PASS_RESULT
            && receipt.evidence_class == G0140_STAGE_A_SOURCE_AUDIT_EVIDENCE_CLASS
            && receipt.claim_boundary == G0140_STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY
            && receipt.no_claim == G0140_STAGE_A_SOURCE_AUDIT_NO_CLAIM
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_replay_run,
        "final Stage-A source audit semantic boundary drift"
    );
    ensure!(
        !receipt.reviewer.agent_name.is_empty()
            && receipt.reviewer.program == "codex"
            && !receipt.reviewer.model.is_empty()
            && receipt.reviewer.same_model_lineage
            && receipt.reviewer.fresh_context,
        "final Stage-A source audit reviewer disclosure drift"
    );
    ensure!(
        receipt.preregistration.path == G0140_STAGE_A_SOURCE_AUDIT_PREREG_PATH
            && is_sha256(&receipt.preregistration.sha256)
            && receipt.preregistration.git_commit.len() == 40
            && receipt
                .preregistration
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .preregistration
                .committed_and_pushed_before_subject_source_inspection
            && receipt
                .preregistration
                .committed_and_pushed_before_runtime_checks,
        "final Stage-A source audit preregistration drift"
    );
    ensure!(
        receipt.subject.git_commit.len() == 40
            && receipt
                .subject
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings,
        "final Stage-A source audit subject custody drift"
    );
    for (expected_path, binding) in final_stage_a_source_audit_bindings(receipt) {
        ensure!(
            binding.path == expected_path && is_sha256(&binding.sha256),
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

fn stage_e_source_audit_bindings(
    receipt: &StageESourceAuditReceipt,
) -> [(&'static str, &Binding); 5] {
    [
        (STAGE_E_SOURCE_PATH, &receipt.subject.bindings.main_source),
        (STAGE_E_ENGINE_PATH, &receipt.subject.bindings.engine_source),
        (STAGE_E_CARGO_PATH, &receipt.subject.bindings.cargo_manifest),
        (STAGE_E_LOCK_PATH, &receipt.subject.bindings.cargo_lock),
        (
            STAGE_E_EXECUTABLE_PATH,
            &receipt.subject.bindings.release_executable,
        ),
    ]
}

fn stage_e_source_audit_receipt(receipt: &Value) -> Result<StageESourceAuditReceipt> {
    serde_json::from_value(receipt.clone())
        .context("strict final Stage-E source-audit schema validation")
}

fn validate_stage_e_source_audit_semantics(receipt: &StageESourceAuditReceipt) -> Result<()> {
    ensure!(
        receipt.schema == STAGE_E_SOURCE_AUDIT_SCHEMA
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_CUSTODY_PASS_RESULT
            && receipt.evidence_class == STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS
            && receipt.claim_boundary == STAGE_E_SOURCE_AUDIT_CLAIM_BOUNDARY
            && receipt.no_claim == STAGE_E_SOURCE_AUDIT_NO_CLAIM
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_replay_run,
        "final Stage-E source audit semantic boundary drift"
    );
    ensure!(
        !receipt.reviewer.agent_name.is_empty()
            && receipt.reviewer.program == "codex"
            && !receipt.reviewer.model.is_empty()
            && receipt.reviewer.same_model_lineage
            && receipt.reviewer.fresh_context,
        "final Stage-E source audit reviewer disclosure drift"
    );
    ensure!(
        receipt.preregistration.path == STAGE_E_SOURCE_AUDIT_PREREG_PATH
            && is_sha256(&receipt.preregistration.sha256)
            && receipt.preregistration.git_commit.len() == 40
            && receipt
                .preregistration
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .preregistration
                .committed_and_pushed_before_subject_source_inspection
            && receipt
                .preregistration
                .committed_and_pushed_before_runtime_checks,
        "final Stage-E source audit preregistration drift"
    );
    ensure!(
        receipt.subject.git_commit.len() == 40
            && receipt
                .subject
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings,
        "final Stage-E source audit subject custody drift"
    );
    let mut paths = HashSet::new();
    for (expected_path, binding) in stage_e_source_audit_bindings(receipt) {
        ensure!(
            binding.path == expected_path
                && is_sha256(&binding.sha256)
                && paths.insert(binding.path.as_str()),
            "final Stage-E source audit named binding drift: {expected_path}"
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
            && checks.compiled_source_manifest_lock_match_working_bytes
            && checks.engine_byte_identity_with_stage_a_verified
            && checks.g0155_stage_d_source_audit_gate_verified
            && checks.scientific_output_commit_chain_gate_verified
            && checks.dynamic_stage_d_member_contract_verified
            && checks.global_zero_and_residual_branches_verified
            && checks.complete_label_census_and_end_rehash_verified
            && checks.overwrite_refusal_verified
            && checks.prohibited_scientific_modes_not_run,
        "final Stage-E source audit required-check drift"
    );
    Ok(())
}

fn validate_stage_e_source_audit_gate(root: &Path, protocol: &ManifestSnapshot) -> Result<Binding> {
    let audit_path = checked_repo_path(root, STAGE_E_SOURCE_AUDIT_PATH)?;
    let audit_sha256 = sha256_path(&audit_path)?;
    let value = strict_json_value(BufReader::new(File::open(audit_path)?))?;
    let receipt = stage_e_source_audit_receipt(&value)?;
    validate_stage_e_source_audit_semantics(&receipt)?;
    git_commit_for_path(root, STAGE_E_SOURCE_AUDIT_PATH)?;
    ensure!(
        receipt.subject.git_commit == git_commit_for_path(root, STAGE_E_SOURCE_PATH)?,
        "G-0156 subject commit does not match Stage-E source"
    );
    let preregistration = checked_repo_path(root, STAGE_E_SOURCE_AUDIT_PREREG_PATH)?;
    ensure!(
        sha256_path(&preregistration)? == receipt.preregistration.sha256
            && git_commit_for_path(root, STAGE_E_SOURCE_AUDIT_PREREG_PATH)?
                == receipt.preregistration.git_commit,
        "G-0156 preregistration custody drift"
    );
    for (expected_path, binding) in stage_e_source_audit_bindings(&receipt) {
        binding_matches(root, binding, expected_path)?;
        git_commit_for_path(root, expected_path)?;
        ensure!(
            protocol.bindings_by_path.get(expected_path) == Some(&binding.sha256),
            "G-0140 manifest omits exact G-0156 subject binding: {expected_path}"
        );
    }
    let audit_binding = Binding {
        path: STAGE_E_SOURCE_AUDIT_PATH.to_string(),
        sha256: audit_sha256,
    };
    ensure!(
        protocol.bindings_by_path.get(STAGE_E_SOURCE_AUDIT_PATH) == Some(&audit_binding.sha256),
        "G-0140 manifest omits exact G-0156 receipt binding"
    );
    let audit_commit = git_commit_for_path(root, STAGE_E_SOURCE_AUDIT_PATH)?;
    let manifest_commit = git_commit_for_path(root, G0140_MANIFEST_PATH)?;
    git_is_ancestor(
        root,
        &receipt.subject.git_commit,
        &receipt.preregistration.git_commit,
        "Stage-E source -> G-0156 preregistration",
    )?;
    git_is_ancestor(
        root,
        &receipt.preregistration.git_commit,
        &audit_commit,
        "G-0156 preregistration -> receipt",
    )?;
    git_is_ancestor(
        root,
        &audit_commit,
        &manifest_commit,
        "G-0156 receipt -> G-0140 manifest",
    )?;
    Ok(audit_binding)
}

fn validate_stage_d_source_audit_semantics(receipt: &StageDSourceAuditReceipt) -> Result<()> {
    let checks = &receipt.required_checks;
    ensure!(
        receipt.schema == STAGE_D_SOURCE_AUDIT_SCHEMA_G0140
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_CUSTODY_PASS_RESULT
            && receipt.evidence_class == STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS
            && receipt.claim_boundary == STAGE_D_SOURCE_AUDIT_CLAIM_G0140
            && receipt.no_claim == STAGE_D_SOURCE_AUDIT_NO_CLAIM_G0140
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_replay_run
            && !receipt.reviewer.agent_name.is_empty()
            && receipt.reviewer.program == "codex"
            && !receipt.reviewer.model.is_empty()
            && receipt.reviewer.same_model_lineage
            && receipt.reviewer.fresh_context
            && receipt.subject.git_commit == STAGE_D_SOURCE_COMMIT_G0140
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings
            && receipt.subject.bindings.master_source.path == STAGE_D_SOURCE_PATH_G0140
            && receipt.subject.bindings.master_source.sha256 == STAGE_D_SOURCE_SHA256_G0140
            && checks.exact_named_binding_contract
            && checks.displaced_recursive_lookalikes_rejected
            && checks.correct_decoy_with_missing_named_binding_rejected
            && checks.unknown_envelope_fields_rejected
            && checks.audit_git_commit_rejected
            && checks.duplicate_json_keys_rejected
            && checks.trailing_json_data_rejected
            && checks.imported_exact_core_binding_verified
            && checks.future_input_gate_verified
            && checks.exact_column_generation_protocol_verified
            && checks.member_and_separator_fixtures_verified
            && checks.committed_blob_custody_verified
            && checks.producer_self_test_passed
            && checks.producer_static_preflight_passed
            && checks.prohibited_scientific_modes_not_run,
        "G-0155 exact source-audit PASS contract drift"
    );
    ensure!(
        receipt.preregistration.path == STAGE_D_SOURCE_AUDIT_PREREG_PATH_G0140
            && is_sha256(&receipt.preregistration.sha256)
            && receipt.preregistration.git_commit.len() == 40
            && receipt
                .preregistration
                .git_commit
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit())
            && receipt
                .preregistration
                .committed_and_pushed_before_subject_source_inspection
            && receipt
                .preregistration
                .committed_and_pushed_before_runtime_checks,
        "G-0155 preregistration disclosure drift"
    );
    Ok(())
}

fn validate_stage_d_source_audit_gate(
    root: &Path,
    protocol: &ManifestSnapshot,
    expected: &Binding,
) -> Result<Binding> {
    binding_matches(root, expected, STAGE_D_SOURCE_AUDIT_PATH_G0140)?;
    let path = checked_repo_path(root, STAGE_D_SOURCE_AUDIT_PATH_G0140)?;
    let receipt: StageDSourceAuditReceipt = strict_json(BufReader::new(File::open(path)?))?;
    validate_stage_d_source_audit_semantics(&receipt)?;
    binding_matches(
        root,
        &receipt.subject.bindings.master_source,
        STAGE_D_SOURCE_PATH_G0140,
    )?;
    let preregistration = checked_repo_path(root, STAGE_D_SOURCE_AUDIT_PREREG_PATH_G0140)?;
    ensure!(
        sha256_path(&preregistration)? == receipt.preregistration.sha256
            && git_commit_for_path(root, STAGE_D_SOURCE_AUDIT_PREREG_PATH_G0140)?
                == receipt.preregistration.git_commit,
        "G-0155 preregistration byte/Git custody drift"
    );
    for binding in [expected, &receipt.subject.bindings.master_source] {
        ensure!(
            protocol.bindings_by_path.get(&binding.path) == Some(&binding.sha256),
            "G-0140 manifest omits exact G-0155 custody binding: {}",
            binding.path
        );
    }
    let audit_commit = git_commit_for_path(root, STAGE_D_SOURCE_AUDIT_PATH_G0140)?;
    let manifest_commit = git_commit_for_path(root, G0140_MANIFEST_PATH)?;
    git_is_ancestor(
        root,
        STAGE_D_SOURCE_COMMIT_G0140,
        &receipt.preregistration.git_commit,
        "Stage-D source -> G-0155 preregistration",
    )?;
    git_is_ancestor(
        root,
        &receipt.preregistration.git_commit,
        &audit_commit,
        "G-0155 preregistration -> receipt",
    )?;
    git_is_ancestor(
        root,
        &audit_commit,
        &manifest_commit,
        "G-0155 receipt -> G-0140 manifest",
    )?;
    Ok(expected.clone())
}

fn source_audit_contract(audit_path: &str) -> Result<(&'static str, Option<&'static str>)> {
    match audit_path {
        STAGE_A_AUDIT_PATH => Ok(("max11-g0136-g0135-source-audit-v1", None)),
        STAGE_BC_AUDIT_PATH => Ok(("max11-g0137-g0135-stages-bc-source-audit-v1", None)),
        STAGE_D_AUDIT_PATH => Ok(("max11-g0138-g0135-stage-d-source-audit-v1", None)),
        G0140_STAGE_A_SOURCE_AUDIT_PATH => Ok((
            G0140_STAGE_A_SOURCE_AUDIT_SCHEMA,
            Some(SOURCE_CUSTODY_PASS_RESULT),
        )),
        STAGE_E_SOURCE_AUDIT_PATH => Ok((
            STAGE_E_SOURCE_AUDIT_SCHEMA,
            Some(SOURCE_CUSTODY_PASS_RESULT),
        )),
        _ => anyhow::bail!("unknown source-audit contract: {audit_path}"),
    }
}

fn validate_source_audit_envelope(receipt: &Value, audit_path: &str) -> Result<()> {
    if audit_path == G0140_STAGE_A_SOURCE_AUDIT_PATH {
        return validate_final_stage_a_source_audit_semantics(&final_stage_a_source_audit_receipt(
            receipt,
        )?);
    }
    if audit_path == STAGE_E_SOURCE_AUDIT_PATH {
        return validate_stage_e_source_audit_semantics(&stage_e_source_audit_receipt(receipt)?);
    }
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
    git_commit_for_path(root, audit_path)?;
    let receipt = strict_json_value(BufReader::new(File::open(path)?))?;
    validate_source_audit_envelope(&receipt, audit_path)?;
    if audit_path == G0140_STAGE_A_SOURCE_AUDIT_PATH {
        ensure!(
            required_subject_paths
                == [
                    G0140_STAGE_A_SOURCE_PATH,
                    G0140_STAGE_A_ENGINE_PATH,
                    G0140_STAGE_A_CARGO_PATH,
                    G0140_STAGE_A_LOCK_PATH,
                    G0140_STAGE_A_EXECUTABLE_PATH,
                ],
            "final Stage-A audit named-subject call contract drift"
        );
        let receipt = final_stage_a_source_audit_receipt(&receipt)?;
        ensure!(
            receipt.subject.git_commit == git_commit_for_path(root, G0140_STAGE_A_SOURCE_PATH)?,
            "final Stage-A audited-subject Git identity drift"
        );
        let preregistration_path = checked_repo_path(root, G0140_STAGE_A_SOURCE_AUDIT_PREREG_PATH)?;
        ensure!(
            sha256_path(&preregistration_path)? == receipt.preregistration.sha256
                && git_commit_for_path(root, G0140_STAGE_A_SOURCE_AUDIT_PREREG_PATH)?
                    == receipt.preregistration.git_commit,
            "final Stage-A audit preregistration custody drift"
        );
        for (required, binding) in final_stage_a_source_audit_bindings(&receipt) {
            let expected = manifest
                .bindings_by_path
                .get(required)
                .with_context(|| format!("shared manifest omits audited subject {required}"))?;
            ensure!(
                binding.sha256 == *expected,
                "final Stage-A source audit does not bind exact named subject: {required}"
            );
            ensure!(
                sha256_path(&checked_repo_path(root, required)?)? == binding.sha256,
                "final Stage-A source audit named binding drift: {required}"
            );
        }
        return Ok(());
    }
    if audit_path == STAGE_E_SOURCE_AUDIT_PATH {
        ensure!(
            required_subject_paths
                == [
                    STAGE_E_SOURCE_PATH,
                    STAGE_E_ENGINE_PATH,
                    STAGE_E_CARGO_PATH,
                    STAGE_E_LOCK_PATH,
                    STAGE_E_EXECUTABLE_PATH,
                ],
            "final Stage-E audit named-subject call contract drift"
        );
        let receipt = stage_e_source_audit_receipt(&receipt)?;
        ensure!(
            receipt.subject.git_commit == git_commit_for_path(root, STAGE_E_SOURCE_PATH)?,
            "final Stage-E audited-subject Git identity drift"
        );
        let preregistration_path = checked_repo_path(root, STAGE_E_SOURCE_AUDIT_PREREG_PATH)?;
        ensure!(
            sha256_path(&preregistration_path)? == receipt.preregistration.sha256
                && git_commit_for_path(root, STAGE_E_SOURCE_AUDIT_PREREG_PATH)?
                    == receipt.preregistration.git_commit,
            "final Stage-E audit preregistration custody drift"
        );
        for (required, binding) in stage_e_source_audit_bindings(&receipt) {
            let expected = manifest
                .bindings_by_path
                .get(required)
                .with_context(|| format!("Stage-E custody snapshot omits {required}"))?;
            ensure!(
                binding.sha256 == *expected
                    && sha256_path(&checked_repo_path(root, required)?)? == binding.sha256,
                "final Stage-E source audit named binding drift: {required}"
            );
        }
        return Ok(());
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
        (COMPILED_SOURCE, STAGE_E_SOURCE_PATH),
        (COMPILED_ENGINE, STAGE_E_ENGINE_PATH),
        (COMPILED_MANIFEST, STAGE_E_CARGO_PATH),
        (COMPILED_LOCK, STAGE_E_LOCK_PATH),
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
    ensure!(
        COMPILED_ENGINE == COMPILED_STAGE_A_ENGINE
            && sha256_path(&checked_repo_path(root, STAGE_E_ENGINE_PATH)?)?
                == sha256_path(&checked_repo_path(root, G0140_STAGE_A_ENGINE_PATH)?)?,
        "Stage-E engine is not byte-identical to the exact Stage-A engine"
    );
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
                path: G0140_STAGE_A_RESULT_PATH.to_string(),
                schema: G0140_STAGE_A_OUTPUT_SCHEMA.to_string(),
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
        G0140_STAGE_A_SOURCE_PATH,
        G0140_STAGE_A_ENGINE_PATH,
        G0140_STAGE_A_CARGO_PATH,
        G0140_STAGE_A_LOCK_PATH,
        G0140_STAGE_A_EXECUTABLE_PATH,
        G0140_STAGE_A_SOURCE_AUDIT_PATH,
        STAGE_D_SOURCE_PATH_G0140,
        STAGE_D_SOURCE_AUDIT_PATH_G0140,
        STAGE_E_SOURCE_PATH,
        STAGE_E_ENGINE_PATH,
        STAGE_E_CARGO_PATH,
        STAGE_E_LOCK_PATH,
        STAGE_E_EXECUTABLE_PATH,
        STAGE_E_SOURCE_AUDIT_PATH,
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
            && manifest.producer_git_commit
                == git_commit_for_path(root, G0140_STAGE_A_SOURCE_PATH)?
            && manifest.source_audit_git_commit
                == git_commit_for_path(root, G0140_STAGE_A_SOURCE_AUDIT_PATH)?,
        "G-0140 manifest Git commit drift"
    );
    let snapshot = ManifestSnapshot {
        sha256,
        bindings_by_path,
    };
    validate_source_audit(
        root,
        &snapshot,
        G0140_STAGE_A_SOURCE_AUDIT_PATH,
        &[
            G0140_STAGE_A_SOURCE_PATH,
            G0140_STAGE_A_ENGINE_PATH,
            G0140_STAGE_A_CARGO_PATH,
            G0140_STAGE_A_LOCK_PATH,
            G0140_STAGE_A_EXECUTABLE_PATH,
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

const STAGE_A_POOL_KEYS: &[&str] = &[
    "schema",
    "result",
    "claim_boundary",
    "g0140_manifest",
    "g0135_manifest",
    "protocol",
    "producer_source",
    "producer_engine",
    "producer_executable",
    "g0139_result_audit",
    "ancestor_stage_d_result",
    "stage_c_member",
    "source_and_audit_bindings",
    "candidate_schema",
    "candidate_result",
    "rows",
    "records",
    "selected_rank",
    "support_columns",
    "terms",
    "target_scale",
    "target_subtraction_coordinate_10",
    "stage_c_all_412_rational_rows_replayed",
    "stage_c_all_412_integer_rows_replayed",
    "stage_c_primitive_denominator_clearing",
    "stage_c_coefficient_plus_one_mutant_rejected",
    "stage_c_prior_scale_carryover_mutant_rejected",
    "independent_finite_412_row_replay",
    "arithmetic",
    "decision_rule",
    "complete_global_replay",
    "all_hinge_and_linear_residuals_zero",
    "labelled_permutations_expected",
    "labelled_permutations_checked",
    "hinge_entries_processed",
    "aggregate_hinge_support",
    "nonzero_hinge_directions",
    "aggregate_hinge_decimal_lf_sha256",
    "nonzero_hinge_decimal_lf_sha256",
    "complete_residual_decimal_lf_sha256",
    "term_normal_form_transcript_sha256",
    "term_normal_forms",
    "accumulated_direction_checks",
    "all_100_accumulated_directions_exact_zero",
    "linear_residuals_after_target",
    "all_11_linear_residuals_exact_zero",
    "first_nonzero_hinge",
    "first_nonzero_linear",
    "pool_k",
    "pool_count",
    "pool_directions_i8_sha256",
    "pool_exact_residuals_decimal_lf_sha256",
    "pool",
    "coefficient_plus_one",
    "target_scale_plus_one",
    "target_coordinate_plus_one",
    "omitted_final_term",
    "omitted_first_term_direction",
    "census_controls",
    "selection_controls",
    "inputs_rehashed_at_end",
    "manifest_rehashed_at_end",
    "candidate_rehashed_at_end",
    "wall_seconds",
];

const G0140_STAGE_C_KEYS: &[&str] = &[
    "schema",
    "result",
    "claim_boundary",
    "manifest",
    "stage_a_receipt",
    "stage_b_receipt",
    "g0139_admission_receipt",
    "stage_c_source_audit",
    "solver",
    "launcher",
    "runtime",
    "native_proposer",
    "rows",
    "base_rows",
    "pool_rows",
    "records",
    "admit_limit",
    "target",
    "target_i128le_sha256",
    "target_construction",
    "row_order",
    "inherited_g0135_warm_start",
    "complete_column_basis",
    "rank_selection",
    "input_snapshot_sha256",
    "inputs_rehashed_at_end",
    "wall_seconds",
    "maximum_rss_kib",
];

fn load_stage_a_pool_view(
    root: &Path,
    protocol: &ManifestSnapshot,
    binding: &Binding,
) -> Result<StageAPoolView> {
    binding_matches(root, binding, G0140_STAGE_A_RESULT_PATH)?;
    let value = strict_json_value(BufReader::new(File::open(checked_repo_path(
        root,
        G0140_STAGE_A_RESULT_PATH,
    )?)?))?;
    validate_exact_object_keys(&value, STAGE_A_POOL_KEYS, "G-0140 Stage-A pool receipt")?;
    let receipt: StageAPoolView =
        serde_json::from_value(value).context("typed G-0140 Stage-A pool receipt")?;
    ensure!(
        receipt.schema == G0140_STAGE_A_OUTPUT_SCHEMA
            && receipt.result == STAGE_A_RESIDUAL_RESULT
            && receipt.g0140_manifest.path == G0140_MANIFEST_PATH
            && receipt.g0140_manifest.sha256 == protocol.sha256
            && receipt.complete_global_replay
            && !receipt.all_hinge_and_linear_residuals_zero
            && receipt.pool_k == RESIDUAL_PREFIX_K
            && receipt.pool_count == RESIDUAL_PREFIX_K
            && receipt.pool.len() == RESIDUAL_PREFIX_K
            && receipt.accumulated_direction_checks.len() == INHERITED_DIRECTIONS
            && receipt.all_100_accumulated_directions_exact_zero
            && receipt.inputs_rehashed_at_end
            && receipt.manifest_rehashed_at_end
            && receipt.candidate_rehashed_at_end,
        "G-0140 Stage-A pool identity/completion drift"
    );
    ensure!(
        selected_direction_digest(&receipt.pool) == receipt.pool_directions_i8_sha256
            && selected_residual_digest(&receipt.pool)
                == receipt.pool_exact_residuals_decimal_lf_sha256
            && receipt
                .pool
                .windows(2)
                .all(|pair| pair[0].direction < pair[1].direction),
        "G-0140 Stage-A pool ordering/digest drift"
    );
    let mut seen = HashSet::new();
    for (index, check) in receipt.accumulated_direction_checks.iter().enumerate() {
        validate_direction(&check.direction)?;
        let (expected_source, expected_source_index) = if index < OLD_CARRY_DIRECTIONS {
            ("G0128_ACCUMULATED_68", index)
        } else {
            ("G0135_STAGE_A_BATCH32", index - OLD_CARRY_DIRECTIONS)
        };
        ensure!(
            check.index == index
                && check.source == expected_source
                && check.source_index == expected_source_index
                && check.routes_agree
                && check.exact_zero
                && check.aggregate_coefficient == "0"
                && check.direct_dp_coefficient == "0"
                && seen.insert(check.direction),
            "G-0140 Stage-A inherited accumulated-direction drift at {index}"
        );
    }
    for item in &receipt.pool {
        validate_direction(&item.direction)?;
        ensure!(
            canonical_integer(&item.coefficient)
                && item.coefficient != "0"
                && !seen.contains(&item.direction),
            "G-0140 Stage-A pool item drift"
        );
    }
    Ok(receipt)
}

fn load_stage_c_selection_view(
    root: &Path,
    protocol: &ManifestSnapshot,
    binding: &Binding,
    stage_a_binding: &Binding,
) -> Result<StageCSelectionView> {
    binding_matches(root, binding, STAGE_C_OUTPUT_PATH)?;
    let value = strict_json_value(BufReader::new(File::open(checked_repo_path(
        root,
        STAGE_C_OUTPUT_PATH,
    )?)?))?;
    validate_exact_object_keys(
        &value,
        G0140_STAGE_C_KEYS,
        "G-0140 Stage-C selector receipt",
    )?;
    let receipt: StageCSelectionView =
        serde_json::from_value(value).context("typed G-0140 Stage-C selection view")?;
    ensure!(
        receipt.schema == STAGE_C_OUTPUT_SCHEMA
            && matches!(
                receipt.result.as_str(),
                "EXACT_RANK32_SELECTED" | "FIXED_POOL128_EXACT_RANK_GAIN_LT32"
            )
            && receipt.manifest.path == G0140_MANIFEST_PATH
            && receipt.manifest.sha256 == protocol.sha256
            && receipt.stage_a_receipt == *stage_a_binding
            && receipt.rank_selection.result == receipt.result
            && receipt.rank_selection.selected_count
                == receipt.rank_selection.selected_pool_indices.len()
            && receipt.rank_selection.selected_count <= MAX_STAGE_D_APPENDED_ROWS
            && receipt.rank_selection.all_pool_rows_compatibility_checked
            && receipt.rank_selection.compatibility_decision_complete
            && receipt.rank_selection.no_modular_row_selection
            && receipt.inputs_rehashed_at_end,
        "G-0140 Stage-C selection identity/completion drift"
    );
    validate_optional_strict_axis(
        &receipt.rank_selection.selected_pool_indices,
        RESIDUAL_PREFIX_K,
        "G-0140 Stage-C selected pool indices",
    )?;
    Ok(receipt)
}

fn validate_stage_d_trials(candidate: &StageDMember) -> Result<()> {
    ensure!(
        !candidate.trials.is_empty()
            && candidate.trials.len() == candidate.rank - candidate.initial_rank + 1,
        "Stage-D rank-trial census drift"
    );
    for (index, trial) in candidate.trials.iter().enumerate() {
        match trial {
            RankTrial::Member(trial) => ensure!(
                index + 1 == candidate.trials.len()
                    && trial.iteration == index
                    && trial.rank == candidate.rank
                    && trial.augmented_rank == candidate.augmented_rank
                    && trial.result == "EXACT_Q_MEMBER",
                "Stage-D terminal member trial drift"
            ),
            RankTrial::Separator(trial) => ensure!(
                index + 1 < candidate.trials.len()
                    && trial.iteration == index
                    && trial.rank == candidate.initial_rank + index
                    && trial.augmented_rank == trial.rank + 1
                    && trial.separator_free_row < candidate.rows
                    && canonical_integer(&trial.separator_target_pairing)
                    && trial.separator_target_pairing != "0"
                    && trial.first_violating_sequence < RECORDS
                    && canonical_integer(&trial.first_violating_price)
                    && trial.first_violating_price != "0"
                    && (1..=RECORDS).contains(&trial.columns_scanned)
                    && is_sha256(&trial.scanned_prices_decimal_lf_sha256)
                    && trial.result == "SEPARATOR_VIOLATED",
                "Stage-D nonterminal separator trial drift"
            ),
        }
    }
    Ok(())
}

fn load_and_validate_stage_d_member(
    root: &Path,
    protocol: &ManifestSnapshot,
    ancestor: &StageCMember,
    inherited_directions: &[[i8; N]],
) -> Result<(StageDMember, Binding, Vec<[i8; N]>)> {
    let path = checked_repo_path(root, STAGE_D_OUTPUT_PATH)?;
    let binding = Binding {
        path: STAGE_D_OUTPUT_PATH.to_string(),
        sha256: sha256_path(&path)?,
    };
    let candidate: StageDMember = strict_json(BufReader::new(File::open(path)?))?;
    binding_matches(root, &candidate.manifest, G0140_MANIFEST_PATH)?;
    ensure!(
        candidate.manifest.sha256 == protocol.sha256,
        "Stage-D manifest bridge drift"
    );
    binding_matches(root, &candidate.solver, STAGE_D_SOURCE_PATH_G0140)?;
    ensure!(
        candidate.solver.sha256 == STAGE_D_SOURCE_SHA256_G0140
            && git_commit_for_path(root, STAGE_D_SOURCE_PATH_G0140)? == STAGE_D_SOURCE_COMMIT_G0140,
        "Stage-D frozen source identity drift"
    );
    binding_matches(
        root,
        &candidate.source_audit,
        STAGE_D_SOURCE_AUDIT_PATH_G0140,
    )?;
    validate_stage_d_source_audit_gate(root, protocol, &candidate.source_audit)?;
    for candidate_binding in [
        &candidate.stage_a_receipt,
        &candidate.stage_b_receipt,
        &candidate.stage_c_receipt,
        &candidate.source_audit,
        &candidate.solver,
    ] {
        ensure!(
            protocol.bindings_by_path.get(&candidate_binding.path)
                == Some(&candidate_binding.sha256),
            "G-0140 manifest omits exact Stage-D-bound input: {}",
            candidate_binding.path
        );
    }

    let stage_a = load_stage_a_pool_view(root, protocol, &candidate.stage_a_receipt)?;
    binding_matches(root, &candidate.stage_b_receipt, STAGE_B_OUTPUT_PATH)?;
    let stage_c = load_stage_c_selection_view(
        root,
        protocol,
        &candidate.stage_c_receipt,
        &candidate.stage_a_receipt,
    )?;
    ensure!(
        stage_c.stage_b_receipt == candidate.stage_b_receipt
            && stage_c.rank_selection.selected_pool_indices == candidate.selected_pool_indices
            && stage_a
                .accumulated_direction_checks
                .iter()
                .map(|check| check.direction)
                .eq(inherited_directions.iter().copied()),
        "Stage-D Stage-B/Stage-C receipt bridge drift"
    );

    ensure!(
        candidate.schema == STAGE_D_OUTPUT_SCHEMA
            && candidate.result == STAGE_D_MEMBER_RESULT
            && !candidate.claim_boundary.trim().is_empty()
            && candidate.records == RECORDS
            && candidate.base_rows == BASE_ROWS
            && candidate.appended_rows == candidate.selected_pool_indices.len()
            && candidate.appended_rows == candidate.selected_directions.len()
            && candidate.appended_rows <= MAX_STAGE_D_APPENDED_ROWS
            && candidate.rows == BASE_ROWS + candidate.appended_rows
            && candidate.inputs_rehashed_at_end
            && candidate.wall_seconds > 0.0
            && candidate.maximum_rss_kib > 0,
        "Stage-D member identity/completion drift"
    );
    validate_optional_strict_axis(
        &candidate.selected_pool_indices,
        RESIDUAL_PREFIX_K,
        "Stage-D selected pool indices",
    )?;
    ensure!(
        u64le_digest(candidate.selected_pool_indices.iter().copied())
            == candidate.selected_pool_indices_u64le_sha256
            && direction_digest(&candidate.selected_directions)
                == candidate.selected_directions_i8_sha256
            && candidate.selected_pool_indices == stage_c.rank_selection.selected_pool_indices
            && candidate.selected_directions
                == pool_directions_at(&stage_a.pool, &candidate.selected_pool_indices)?
            && stage_c.rank_selection.selected_system_rank
                == candidate.initial_rank + candidate.appended_rows,
        "Stage-D selected-row bridge/digest drift"
    );
    for direction in &candidate.selected_directions {
        validate_direction(direction)?;
    }

    let target = candidate
        .target
        .iter()
        .map(|raw| {
            ensure!(canonical_integer(raw), "Stage-D target is not canonical");
            raw.parse::<i64>().context("Stage-D target exceeds i64")
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        target.len() == candidate.rows
            && target[..BASE_ROWS] == ancestor.target
            && target[BASE_ROWS..].iter().all(|value| *value == 0)
            && i128le_digest(target.iter().copied()) == candidate.target_i128le_sha256
            && candidate.target_construction
                == "immutable_G0135_412_entry_unscaled_target_followed_by_selected_exact_zeros",
        "Stage-D target construction/digest drift"
    );
    ensure!(
        candidate.initial_rank == 204
            && candidate.initial_selected_sequences == ancestor.selected_sequences
            && candidate.initial_selected_sequences.len() == 204
            && u64le_digest(candidate.initial_selected_sequences.iter().copied())
                == candidate.initial_selected_sequences_u64le_sha256
            && candidate.all_columns_reopened
            && candidate.canonical_column_order
            && candidate.no_modular_terminal_decision
            && candidate.no_support_freeze
            && candidate.no_zero_price_column_deletion
            && candidate.no_row_dependency_deletion
            && candidate.no_preferred_sparsity_search,
        "Stage-D 204-column warm seed/all-column policy drift"
    );

    ensure!(
        candidate.rank == candidate.augmented_rank
            && candidate.rank >= candidate.initial_rank
            && candidate.rank <= candidate.rows
            && candidate.selected_sequences.len() == candidate.rank
            && candidate.support_sequences.len() == candidate.rank
            && candidate.coordinate_rows.len() == candidate.rank
            && candidate.rational_coefficients.len() == candidate.rank
            && candidate.integer_coefficients.len() == candidate.rank,
        "Stage-D rank/support/coefficient census drift"
    );
    validate_strict_axis(
        &candidate.selected_sequences,
        RECORDS,
        "Stage-D selected sequences",
    )?;
    validate_strict_axis(
        &candidate.support_sequences,
        RECORDS,
        "Stage-D support sequences",
    )?;
    validate_strict_axis(
        &candidate.coordinate_rows,
        candidate.rows,
        "Stage-D coordinate rows",
    )?;
    ensure!(
        candidate.selected_sequences == candidate.support_sequences
            && is_sha256(&candidate.selected_basis_i128le_sha256)
            && decimal_lf_digest(candidate.rational_coefficients.iter().map(String::as_str))
                == candidate.rational_coefficients_lf_sha256
            && decimal_lf_digest(candidate.integer_coefficients.iter().map(String::as_str))
                == candidate.integer_coefficients_decimal_lf_sha256,
        "Stage-D pivot axes/coefficient digest drift"
    );
    let scale = parse_bigint(&candidate.target_scale)?;
    ensure!(
        scale > BigInt::from(0),
        "Stage-D target scale is not positive"
    );
    let integers = candidate
        .integer_coefficients
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        integers.iter().any(|value| *value != BigInt::from(0)),
        "Stage-D zero member"
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
            "Stage-D rational/integer clearing drift at sequence {sequence}"
        );
    }
    ensure!(
        integers.iter().cloned().fold(scale, bigint_gcd) == BigInt::from(1)
            && candidate.terms
                == nonzero_term_projection(
                    &candidate.support_sequences,
                    &candidate.integer_coefficients,
                )?
            && !candidate.terms.is_empty(),
        "Stage-D primitive clearing/nonzero term projection drift"
    );
    let support = &candidate.support_receipt;
    ensure!(
        support.selected_columns == candidate.rank
            && support.support_columns == candidate.rank
            && support.support_is_exact_pivot_basis
            && support.selected_sequences_u64le_sha256
                == u64le_digest(candidate.selected_sequences.iter().copied())
            && support.support_sequences_u64le_sha256
                == u64le_digest(candidate.support_sequences.iter().copied())
            && support.term_support_u64le_sha256
                == u64le_digest(candidate.terms.iter().map(|term| term.sequence)),
        "Stage-D support receipt drift"
    );
    ensure!(
        candidate.replay_receipt.rows == candidate.rows
            && candidate.replay_receipt.rational_all_rows_replayed
            && candidate.replay_receipt.primitive_denominator_clearing
            && candidate.replay_receipt.integer_all_rows_replayed
            && candidate.replay_receipt.rational_lhs_lf_sha256
                == decimal_lf_digest(candidate.target.iter().map(String::as_str))
            && candidate.replay_receipt.integer_residuals_decimal_lf_sha256
                == zero_lf_digest(candidate.rows),
        "Stage-D all-row exact replay receipt drift"
    );
    let mutant = &candidate.coefficient_plus_one_mutant;
    ensure!(
        mutant.support_index < candidate.rank
            && candidate.integer_coefficients[mutant.support_index] != "0"
            && mutant.sequence == candidate.support_sequences[mutant.support_index]
            && mutant.coefficient_delta == "+1"
            && mutant.first_nonzero_residual_row < candidate.rows
            && is_sha256(&mutant.residuals_decimal_lf_sha256)
            && mutant.rejected
            && candidate.prior_target_scale_carryover_mutant_rejected
            && is_sha256(&candidate.input_snapshot_sha256),
        "Stage-D hostile-control/snapshot drift"
    );
    validate_stage_d_trials(&candidate)?;

    ensure!(
        inherited_directions.len() == INHERITED_DIRECTIONS,
        "inherited G-0135 direction census drift"
    );
    let mut accumulated = inherited_directions.to_vec();
    accumulated.extend(candidate.selected_directions.iter().copied());
    let mut seen = HashSet::new();
    for direction in &accumulated {
        validate_direction(direction)?;
        ensure!(
            seen.insert(*direction),
            "duplicate accumulated Stage-E direction"
        );
    }
    Ok((candidate, binding, accumulated))
}

struct ValidatedInputs {
    panel: PanelInput,
    ancestor_candidate: StageCMember,
    ancestor_candidate_binding: Binding,
    candidate: StageDMember,
    candidate_binding: Binding,
    manifest: ManifestSnapshot,
    protocol_manifest: ManifestSnapshot,
    stage_e_source_audit: Binding,
    accumulated_directions: Vec<[i8; N]>,
    finite_replay: FiniteReplayReceipt,
    stage_output_git_commits: BTreeMap<String, String>,
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
    let ancestor_path = checked_repo_path(root, STAGE_C_RESULT_PATH)?;
    let ancestor_candidate_binding = Binding {
        path: STAGE_C_RESULT_PATH.to_string(),
        sha256: sha256_path(&ancestor_path)?,
    };
    let ancestor_value = strict_json_value(BufReader::new(File::open(ancestor_path)?))?;
    validate_stage_c_member_keys(&ancestor_value)?;
    let ancestor_candidate: StageCMember =
        serde_json::from_value(ancestor_value).context("G-0135 Stage C member schema")?;
    let prior_target = load_prior_target(root)?;
    validate_stage_c_member(
        root,
        &manifest,
        &ancestor_candidate,
        &ancestor_candidate_binding,
        &prior_target,
    )?;
    let (stage_a, accumulated_directions) =
        validate_stage_a_receipt(root, &manifest, &ancestor_candidate.stage_a_receipt)?;
    let stage_b = validate_stage_b_receipt(
        root,
        &manifest,
        &ancestor_candidate.stage_b_receipt,
        &ancestor_candidate.stage_a_receipt,
        &ancestor_candidate.prior_master_result,
        &stage_a,
    )?;
    ensure!(
        ancestor_candidate.stage_a_selected_directions_i8_sha256
            == stage_a.selected_directions_i8_sha256
            && ancestor_candidate.stage_a_selected_exact_residuals_decimal_lf_sha256
                == stage_a.selected_exact_residuals_decimal_lf_sha256
            && ancestor_candidate.stage_b_direction_major_hinge_i64_le_sha256
                == stage_b.direction_major_hinge_i64_le_sha256
            && ancestor_candidate.stage_b_exact_candidate_dots_decimal_lf_sha256
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
    let protocol_manifest = validate_g0140_manifest(root)?;
    let (candidate, candidate_binding, accumulated_directions) = load_and_validate_stage_d_member(
        root,
        &protocol_manifest,
        &ancestor_candidate,
        &accumulated_directions,
    )?;
    let protocol_manifest_commit = git_commit_for_path(root, G0140_MANIFEST_PATH)?;
    let stage_output_git_commits = BTreeMap::from([
        (
            "A".to_string(),
            git_commit_for_path(root, G0140_STAGE_A_RESULT_PATH)?,
        ),
        (
            "B".to_string(),
            git_commit_for_path(root, STAGE_B_OUTPUT_PATH)?,
        ),
        (
            "C".to_string(),
            git_commit_for_path(root, STAGE_C_OUTPUT_PATH)?,
        ),
        (
            "D".to_string(),
            git_commit_for_path(root, STAGE_D_OUTPUT_PATH)?,
        ),
    ]);
    git_is_ancestor(
        root,
        &protocol_manifest_commit,
        &stage_output_git_commits["A"],
        "G-0140 manifest -> Stage-A scientific result",
    )?;
    for (earlier, later) in [("A", "B"), ("B", "C"), ("C", "D")] {
        git_is_ancestor(
            root,
            &stage_output_git_commits[earlier],
            &stage_output_git_commits[later],
            &format!("G-0140 Stage-{earlier} -> Stage-{later} scientific result"),
        )?;
    }
    git_is_ancestor(
        root,
        &protocol_manifest_commit,
        &stage_output_git_commits["D"],
        "G-0140 manifest -> Stage-D scientific result",
    )?;
    let stage_e_source_audit = validate_stage_e_source_audit_gate(root, &protocol_manifest)?;
    let finite_replay =
        independent_finite_replay(root, &panel, &candidate, &accumulated_directions)?;
    Ok(ValidatedInputs {
        panel,
        ancestor_candidate,
        ancestor_candidate_binding,
        candidate,
        candidate_binding,
        manifest,
        protocol_manifest,
        stage_e_source_audit,
        accumulated_directions,
        finite_replay,
        stage_output_git_commits,
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
    candidate: &StageDMember,
    directions: &[[i8; N]],
) -> Result<Vec<BigInt>> {
    let expected = INHERITED_DIRECTIONS + candidate.appended_rows;
    ensure!(
        directions.len() == expected,
        "direct-DP direction width drift"
    );
    candidate
        .terms
        .par_iter()
        .map(|term| -> Result<Vec<BigInt>> {
            let coefficient = parse_bigint(&term.coefficient)?;
            let prices = exact_hinge_coefficients(&panel.records[term.sequence], directions)?;
            ensure!(prices.len() == expected, "direct-DP term width drift");
            Ok(prices
                .into_iter()
                .map(|price| &coefficient * price)
                .collect())
        })
        .try_reduce(
            || vec![BigInt::from(0); expected],
            |mut left, right| -> Result<Vec<BigInt>> {
                ensure!(right.len() == expected, "direct-DP reduction width drift");
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

fn assemble_finite_column(
    mut panel: Vec<BigInt>,
    linear: Vec<BigInt>,
    accumulated_hinges: Vec<BigInt>,
    expected_rows: usize,
) -> Result<Vec<BigInt>> {
    panel.extend(linear);
    panel.extend(accumulated_hinges);
    ensure!(
        panel.len() == expected_rows,
        "finite replay column width drift"
    );
    Ok(panel)
}

fn selected_basis_i128le_digest(columns: &[Vec<BigInt>], rows: usize) -> Result<String> {
    ensure!(
        !columns.is_empty() && columns.iter().all(|column| column.len() == rows),
        "selected basis matrix is empty or ragged"
    );
    let mut digest = Sha256::new();
    for row in 0..rows {
        for column in columns {
            let value = column[row]
                .to_string()
                .parse::<i128>()
                .context("selected basis entry exceeds signed i128")?;
            digest.update(value.to_le_bytes());
        }
    }
    Ok(format!("{:x}", digest.finalize()))
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
    candidate: &StageDMember,
    accumulated_directions: &[[i8; N]],
) -> Result<FiniteReplayReceipt> {
    ensure!(
        candidate.target.len() == candidate.rows
            && accumulated_directions.len() == INHERITED_DIRECTIONS + candidate.appended_rows
            && PANEL_ROWS + LINEAR_ROWS + accumulated_directions.len() == candidate.rows,
        "finite replay dimensions drift"
    );
    let mut cache = File::open(checked_repo_path(root, PANEL_CACHE_PATH)?)?;
    let mut columns = Vec::with_capacity(candidate.selected_sequences.len());
    for sequence in &candidate.selected_sequences {
        let record = &panel.records[*sequence];
        let column = assemble_finite_column(
            read_panel_column(&mut cache, *sequence)?,
            exact_linear_vector(record)?.to_vec(),
            exact_hinge_coefficients(record, accumulated_directions)?,
            candidate.rows,
        )?;
        columns.push(column);
    }
    let selected_basis_digest = selected_basis_i128le_digest(&columns, candidate.rows)?;
    ensure!(
        selected_basis_digest == candidate.selected_basis_i128le_sha256,
        "independent selected-basis digest replay failed"
    );
    let coefficients = candidate
        .integer_coefficients
        .iter()
        .map(|coefficient| parse_bigint(coefficient))
        .collect::<Result<Vec<_>>>()?;
    let target = candidate
        .target
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    let scale = parse_bigint(&candidate.target_scale)?;
    let residuals = exact_matrix_residuals(&columns, &coefficients, &target, &scale)?;
    ensure!(
        residuals.iter().all(|value| *value == BigInt::from(0)),
        "independent finite dynamic-row replay failed"
    );

    let first_nonzero = coefficients
        .iter()
        .position(|coefficient| *coefficient != BigInt::from(0))
        .context("finite replay has no nonzero coefficient")?;
    let first_column = &columns[first_nonzero];
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
        rows: candidate.rows,
        panel_rows: PANEL_ROWS,
        linear_rows: LINEAR_ROWS,
        accumulated_hinge_rows: accumulated_directions.len(),
        selected_basis_columns: candidate.selected_sequences.len(),
        selected_basis_i128le_sha256: selected_basis_digest,
        selected_basis_digest_replayed: true,
        cache_layout: "sequence-major: offset=((sequence*301)+row)*16; signed little-endian i128",
        arithmetic: "signed_num_bigint_BigInt",
        all_rows_exactly_replayed: true,
        residuals_decimal_lf_sha256: decimal_lf_digest(residual_strings.iter().map(String::as_str)),
        coefficient_plus_one_mutant: FiniteCoefficientMutant {
            sequence: candidate.selected_sequences[first_nonzero],
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

fn validate_accumulated_directions(directions: &[[i8; N]], expected: usize) -> Result<()> {
    ensure!(
        directions.len() == expected,
        "accumulated direction census is not {expected}"
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
    let zero_sha256 = "0".repeat(64);
    let zero_commit = "0".repeat(40);
    let source_audit = serde_json::json!({
        "schema": G0140_STAGE_A_SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": SOURCE_CUSTODY_PASS_RESULT,
        "evidence_class": G0140_STAGE_A_SOURCE_AUDIT_EVIDENCE_CLASS,
        "claim_boundary": G0140_STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": true,
            "fresh_context": true
        },
        "preregistration": {
            "path": G0140_STAGE_A_SOURCE_AUDIT_PREREG_PATH,
            "sha256": zero_sha256.clone(),
            "git_commit": zero_commit.clone(),
            "committed_and_pushed_before_subject_source_inspection": true,
            "committed_and_pushed_before_runtime_checks": true
        },
        "subject": {
            "git_commit": zero_commit,
            "commit_object_and_working_bytes_equal_for_all_bindings": true,
            "bindings": {
                "main_source": {"path": G0140_STAGE_A_SOURCE_PATH, "sha256": zero_sha256.clone()},
                "engine_source": {"path": G0140_STAGE_A_ENGINE_PATH, "sha256": zero_sha256.clone()},
                "cargo_manifest": {"path": G0140_STAGE_A_CARGO_PATH, "sha256": zero_sha256.clone()},
                "cargo_lock": {"path": G0140_STAGE_A_LOCK_PATH, "sha256": zero_sha256.clone()},
                "release_executable": {
                    "path": G0140_STAGE_A_EXECUTABLE_PATH,
                    "sha256": zero_sha256
                }
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
        "no_claim": G0140_STAGE_A_SOURCE_AUDIT_NO_CLAIM
    });
    validate_source_audit_envelope(&source_audit, G0140_STAGE_A_SOURCE_AUDIT_PATH)?;
    let mut source_audit_schema_mutant = source_audit.clone();
    source_audit_schema_mutant["schema"] = Value::String("lookalike-source-audit".to_string());
    let mut source_audit_result_mutant = source_audit.clone();
    source_audit_result_mutant["result"] = Value::String("LOOKALIKE_PASS".to_string());
    let mut source_audit_observation_mutant = source_audit.clone();
    source_audit_observation_mutant["scientific_input_observed"] = Value::Bool(true);
    let mut source_audit_displaced_bindings = source_audit.clone();
    let displaced = source_audit_displaced_bindings["subject"]
        .as_object_mut()
        .context("Stage-A audit subject fixture drift")?
        .remove("bindings")
        .context("Stage-A audit binding fixture drift")?;
    source_audit_displaced_bindings["unrelated_receipt_lookalikes"] = displaced;
    let mut source_audit_missing_named_with_decoy = source_audit.clone();
    let decoy = source_audit_missing_named_with_decoy["subject"]["bindings"]
        .as_object_mut()
        .context("Stage-A named binding fixture drift")?
        .remove("main_source")
        .context("Stage-A main-source fixture drift")?;
    source_audit_missing_named_with_decoy["subject"]["unrelated_main_source_decoy"] = decoy;
    let mut source_audit_duplicate_path = source_audit.clone();
    source_audit_duplicate_path["subject"]["bindings"]["engine_source"]["path"] =
        Value::String(G0140_STAGE_A_SOURCE_PATH.to_string());
    let mut source_audit_unknown_envelope = source_audit.clone();
    source_audit_unknown_envelope["unknown_extension"] = Value::Bool(true);
    let mut source_audit_self_reference = source_audit.clone();
    source_audit_self_reference["audit_git_commit"] = Value::String("0".repeat(40));
    ensure!(
        [
            source_audit_schema_mutant,
            source_audit_result_mutant,
            source_audit_observation_mutant,
            source_audit_displaced_bindings,
            source_audit_missing_named_with_decoy,
            source_audit_duplicate_path,
            source_audit_unknown_envelope,
            source_audit_self_reference,
        ]
        .iter()
        .all(|mutant| validate_source_audit_envelope(
            mutant,
            G0140_STAGE_A_SOURCE_AUDIT_PATH
        )
        .is_err()),
        "Stage-A source-audit exact-schema hostile control escaped"
    );
    let mut stage_e_audit = source_audit.clone();
    stage_e_audit["schema"] = Value::String(STAGE_E_SOURCE_AUDIT_SCHEMA.to_string());
    stage_e_audit["evidence_class"] =
        Value::String(STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS.to_string());
    stage_e_audit["claim_boundary"] =
        Value::String(STAGE_E_SOURCE_AUDIT_CLAIM_BOUNDARY.to_string());
    stage_e_audit["no_claim"] = Value::String(STAGE_E_SOURCE_AUDIT_NO_CLAIM.to_string());
    stage_e_audit["preregistration"]["path"] =
        Value::String(STAGE_E_SOURCE_AUDIT_PREREG_PATH.to_string());
    stage_e_audit["subject"]["bindings"] = serde_json::json!({
        "main_source": {"path": STAGE_E_SOURCE_PATH, "sha256": "0".repeat(64)},
        "engine_source": {"path": STAGE_E_ENGINE_PATH, "sha256": "0".repeat(64)},
        "cargo_manifest": {"path": STAGE_E_CARGO_PATH, "sha256": "0".repeat(64)},
        "cargo_lock": {"path": STAGE_E_LOCK_PATH, "sha256": "0".repeat(64)},
        "release_executable": {"path": STAGE_E_EXECUTABLE_PATH, "sha256": "0".repeat(64)},
    });
    stage_e_audit["required_checks"] = serde_json::json!({
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
        "compiled_source_manifest_lock_match_working_bytes": true,
        "engine_byte_identity_with_stage_a_verified": true,
        "g0155_stage_d_source_audit_gate_verified": true,
        "scientific_output_commit_chain_gate_verified": true,
        "dynamic_stage_d_member_contract_verified": true,
        "global_zero_and_residual_branches_verified": true,
        "complete_label_census_and_end_rehash_verified": true,
        "overwrite_refusal_verified": true,
        "prohibited_scientific_modes_not_run": true,
    });
    validate_source_audit_envelope(&stage_e_audit, STAGE_E_SOURCE_AUDIT_PATH)?;
    let mut stage_e_false_check = stage_e_audit.clone();
    stage_e_false_check["required_checks"]["dynamic_stage_d_member_contract_verified"] =
        Value::Bool(false);
    let mut stage_e_displaced = stage_e_audit.clone();
    let bindings = stage_e_displaced["subject"]
        .as_object_mut()
        .context("Stage-E audit subject fixture drift")?
        .remove("bindings")
        .context("Stage-E audit binding fixture drift")?;
    stage_e_displaced["unrelated_binding_decoy"] = bindings;
    let mut stage_e_missing_named = stage_e_audit.clone();
    let decoy = stage_e_missing_named["subject"]["bindings"]
        .as_object_mut()
        .context("Stage-E named binding fixture drift")?
        .remove("main_source")
        .context("Stage-E main-source fixture drift")?;
    stage_e_missing_named["subject"]["unrelated_main_source_decoy"] = decoy;
    let mut stage_e_duplicate_path = stage_e_audit.clone();
    stage_e_duplicate_path["subject"]["bindings"]["engine_source"]["path"] =
        Value::String(STAGE_E_SOURCE_PATH.to_string());
    let mut stage_e_unknown = stage_e_audit.clone();
    stage_e_unknown["unknown_extension"] = Value::Bool(true);
    let mut stage_e_self_reference = stage_e_audit.clone();
    stage_e_self_reference["audit_git_commit"] = Value::String("0".repeat(40));
    let mut stage_e_numeric_true = stage_e_audit.clone();
    stage_e_numeric_true["required_checks"]["exact_named_binding_contract"] =
        Value::Number(1.into());
    let mut stage_e_numeric_false = stage_e_audit.clone();
    stage_e_numeric_false["scientific_output_observed"] = Value::Number(0.into());
    ensure!(
        [
            stage_e_false_check,
            stage_e_displaced,
            stage_e_missing_named,
            stage_e_duplicate_path,
            stage_e_unknown,
            stage_e_self_reference,
            stage_e_numeric_true,
            stage_e_numeric_false,
        ]
        .iter()
        .all(|mutant| validate_source_audit_envelope(mutant, STAGE_E_SOURCE_AUDIT_PATH).is_err()),
        "Stage-E source-audit exact-schema hostile control escaped"
    );
    let stage_d_audit_value = serde_json::json!({
        "schema": STAGE_D_SOURCE_AUDIT_SCHEMA_G0140,
        "verdict": "PASS",
        "result": SOURCE_CUSTODY_PASS_RESULT,
        "evidence_class": STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS,
        "claim_boundary": STAGE_D_SOURCE_AUDIT_CLAIM_G0140,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": true,
            "fresh_context": true
        },
        "preregistration": {
            "path": STAGE_D_SOURCE_AUDIT_PREREG_PATH_G0140,
            "sha256": "0".repeat(64),
            "git_commit": "0".repeat(40),
            "committed_and_pushed_before_subject_source_inspection": true,
            "committed_and_pushed_before_runtime_checks": true
        },
        "subject": {
            "git_commit": STAGE_D_SOURCE_COMMIT_G0140,
            "commit_object_and_working_bytes_equal_for_all_bindings": true,
            "bindings": {
                "master_source": {
                    "path": STAGE_D_SOURCE_PATH_G0140,
                    "sha256": STAGE_D_SOURCE_SHA256_G0140
                }
            }
        },
        "required_checks": {
            "exact_named_binding_contract": true,
            "displaced_recursive_lookalikes_rejected": true,
            "correct_decoy_with_missing_named_binding_rejected": true,
            "unknown_envelope_fields_rejected": true,
            "audit_git_commit_rejected": true,
            "duplicate_json_keys_rejected": true,
            "trailing_json_data_rejected": true,
            "imported_exact_core_binding_verified": true,
            "future_input_gate_verified": true,
            "exact_column_generation_protocol_verified": true,
            "member_and_separator_fixtures_verified": true,
            "committed_blob_custody_verified": true,
            "producer_self_test_passed": true,
            "producer_static_preflight_passed": true,
            "prohibited_scientific_modes_not_run": true
        },
        "scientific_manifest_observed": false,
        "scientific_input_observed": false,
        "scientific_output_observed": false,
        "scientific_replay_run": false,
        "no_claim": STAGE_D_SOURCE_AUDIT_NO_CLAIM_G0140
    });
    let stage_d_audit: StageDSourceAuditReceipt =
        serde_json::from_value(stage_d_audit_value.clone())?;
    validate_stage_d_source_audit_semantics(&stage_d_audit)?;
    let mut stage_d_false_check = stage_d_audit_value.clone();
    stage_d_false_check["required_checks"]["exact_column_generation_protocol_verified"] =
        Value::Bool(false);
    let mut stage_d_wrong_binding = stage_d_audit_value.clone();
    stage_d_wrong_binding["subject"]["bindings"]["master_source"]["sha256"] =
        Value::String("0".repeat(64));
    let mut stage_d_observed = stage_d_audit_value.clone();
    stage_d_observed["scientific_manifest_observed"] = Value::Bool(true);
    let mut stage_d_unknown = stage_d_audit_value;
    stage_d_unknown["unknown_extension"] = Value::Bool(true);
    ensure!(
        [stage_d_false_check, stage_d_wrong_binding, stage_d_observed]
            .into_iter()
            .all(
                |value| serde_json::from_value::<StageDSourceAuditReceipt>(value)
                    .and_then(|receipt| validate_stage_d_source_audit_semantics(&receipt)
                        .map_err(serde::de::Error::custom))
                    .is_err()
            )
            && serde_json::from_value::<StageDSourceAuditReceipt>(stage_d_unknown).is_err(),
        "G-0155 exact typed source-audit hostile control escaped"
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
    validate_accumulated_directions(&accumulated, CARRY_DIRECTIONS)?;
    ensure!(
        validate_accumulated_directions(&accumulated[..CARRY_DIRECTIONS - 1], CARRY_DIRECTIONS,)
            .is_err(),
        "omitted accumulated direction escaped census"
    );
    let pool_fixture = ordered_directions
        .iter()
        .copied()
        .skip(CARRY_DIRECTIONS)
        .take(RESIDUAL_PREFIX_K)
        .map(|direction| ExactHinge {
            direction,
            coefficient: "1".to_string(),
        })
        .collect::<Vec<_>>();
    let no_appended = pool_directions_at(&pool_fixture, &[])?;
    let asymmetric_indices = [1usize, 4, 9];
    let asymmetric_appended = pool_directions_at(&pool_fixture, &asymmetric_indices)?;
    let asymmetric_accumulated = [accumulated.clone(), asymmetric_appended.clone()].concat();
    validate_accumulated_directions(
        &asymmetric_accumulated,
        INHERITED_DIRECTIONS + asymmetric_indices.len(),
    )?;
    ensure!(
        no_appended.is_empty()
            && asymmetric_appended
                == asymmetric_indices
                    .iter()
                    .map(|index| pool_fixture[*index].direction)
                    .collect::<Vec<_>>()
            && pool_directions_at(&pool_fixture, &[4, 1]).is_err()
            && pool_directions_at(&pool_fixture, &[RESIDUAL_PREFIX_K]).is_err(),
        "zero/asymmetric appended-row selection fixture drift"
    );
    let dynamic_column = assemble_finite_column(
        vec![BigInt::from(0); PANEL_ROWS],
        vec![BigInt::from(0); LINEAR_ROWS],
        vec![BigInt::from(0); INHERITED_DIRECTIONS + asymmetric_indices.len()],
        BASE_ROWS + asymmetric_indices.len(),
    )?;
    let dynamic_target = dynamic_column.clone();
    let dynamic_zero = exact_matrix_residuals(
        std::slice::from_ref(&dynamic_column),
        &[BigInt::from(1)],
        &dynamic_target,
        &BigInt::from(1),
    )?;
    let mut dynamic_target_mutant = dynamic_target.clone();
    *dynamic_target_mutant
        .last_mut()
        .context("dynamic target fixture is empty")? += BigInt::from(1);
    let dynamic_nonzero = exact_matrix_residuals(
        std::slice::from_ref(&dynamic_column),
        &[BigInt::from(1)],
        &dynamic_target_mutant,
        &BigInt::from(1),
    )?;
    ensure!(
        dynamic_column.len() == BASE_ROWS + asymmetric_indices.len()
            && dynamic_zero.iter().all(|value| *value == BigInt::from(0))
            && dynamic_nonzero
                .iter()
                .any(|value| *value != BigInt::from(0))
            && assemble_finite_column(
                vec![BigInt::from(0); PANEL_ROWS],
                vec![BigInt::from(0); LINEAR_ROWS],
                vec![BigInt::from(0); INHERITED_DIRECTIONS + asymmetric_indices.len()],
                BASE_ROWS,
            )
            .is_err(),
        "dynamic appended finite-column width fixture drift"
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
        validate_accumulated_directions(&carried_mutant, CARRY_DIRECTIONS).is_err(),
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

fn insert_output_binding(bindings: &mut BTreeMap<String, Binding>, binding: Binding) -> Result<()> {
    if let Some(previous) = bindings.insert(binding.path.clone(), binding.clone()) {
        ensure!(previous == binding, "conflicting output custody binding");
    }
    Ok(())
}

fn stage_e_static_preflight() -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    validate_compiled_bytes(&root)?;
    ensure!(
        sha256_path(&checked_repo_path(&root, STAGE_D_SOURCE_PATH_G0140)?)?
            == STAGE_D_SOURCE_SHA256_G0140
            && git_commit_for_path(&root, STAGE_D_SOURCE_PATH_G0140)?
                == STAGE_D_SOURCE_COMMIT_G0140,
        "frozen Stage-D source custody drift"
    );
    for forbidden in [
        G0140_MANIFEST_PATH,
        G0140_STAGE_A_RESULT_PATH,
        STAGE_B_OUTPUT_PATH,
        STAGE_C_OUTPUT_PATH,
        STAGE_D_OUTPUT_PATH,
        STAGE_E_OUTPUT_PATH,
        STAGE_E_SOURCE_AUDIT_PATH,
    ] {
        ensure!(
            !root.join(forbidden).exists(),
            "outcome-blind static preflight observed future path: {forbidden}"
        );
    }
    println!("G-0140 Stage E outcome-blind static preflight PASS");
    Ok(())
}

fn stage_e_full_preflight(manifest_path: &Path, candidate_path: &Path) -> Result<()> {
    ensure!(
        manifest_path == Path::new(G0140_MANIFEST_PATH)
            && candidate_path == Path::new(STAGE_D_OUTPUT_PATH),
        "preflight input path drift"
    );
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    ensure!(
        !root.join(STAGE_E_OUTPUT_PATH).exists(),
        "scientific output already exists"
    );
    let inputs = load_and_validate_inputs(&root)?;
    let source_audit = inputs.stage_e_source_audit.clone();
    let executable = validate_current_release_executable(&root)?;
    validate_accumulated_directions(
        &inputs.accumulated_directions,
        INHERITED_DIRECTIONS + inputs.candidate.appended_rows,
    )?;
    println!(
        "G-0140 Stage E preflight PASS: {} appended rows; {} selected/support columns; {} nonzero terms; {} accumulated directions; G0156 {}; executable {}; no scientific output written",
        inputs.candidate.appended_rows,
        inputs.candidate.rank,
        inputs.candidate.terms.len(),
        inputs.accumulated_directions.len(),
        source_audit.sha256,
        executable.sha256,
    );
    Ok(())
}

fn stage_e_run(manifest_path: &Path, candidate_path: &Path, output_path: &Path) -> Result<()> {
    ensure!(
        manifest_path == Path::new(G0140_MANIFEST_PATH)
            && candidate_path == Path::new(STAGE_D_OUTPUT_PATH)
            && output_path == Path::new(STAGE_E_OUTPUT_PATH),
        "scientific invocation path drift"
    );
    ensure!(!output_path.exists(), "refusing to overwrite output");
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(THREADS)
        .build_global()
        .context("build fixed G-0140 Stage-E thread pool")?;
    let started = Instant::now();
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let inputs = load_and_validate_inputs(&root)?;
    let source_audit = inputs.stage_e_source_audit.clone();
    let producer_executable = validate_current_release_executable(&root)?;
    let candidate = &inputs.candidate;
    let expected_accumulated = INHERITED_DIRECTIONS + candidate.appended_rows;
    validate_accumulated_directions(&inputs.accumulated_directions, expected_accumulated)?;

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
    let independent_finite_row_replay = inputs.finite_replay.clone();
    ensure!(
        independent_finite_row_replay.rows == candidate.rows
            && independent_finite_row_replay.all_rows_exactly_replayed
            && independent_finite_row_replay.selected_basis_columns == candidate.rank
            && independent_finite_row_replay.selected_basis_i128le_sha256
                == candidate.selected_basis_i128le_sha256
            && independent_finite_row_replay.selected_basis_digest_replayed
            && independent_finite_row_replay.residuals_decimal_lf_sha256
                == zero_lf_digest(candidate.rows)
            && independent_finite_row_replay
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
            let (source, source_index) = if index < OLD_CARRY_DIRECTIONS {
                ("G0128_ACCUMULATED_68", index)
            } else if index < INHERITED_DIRECTIONS {
                ("G0135_STAGE_A_BATCH32", index - OLD_CARRY_DIRECTIONS)
            } else {
                ("G0140_STAGE_D_SELECTED_ROW", index - INHERITED_DIRECTIONS)
            };
            AccumulatedDirectionCheck {
                index,
                source: source.to_string(),
                source_index,
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
        accumulated_direction_checks.len() == expected_accumulated
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
    let residual_prefix =
        select_next_batch(&aggregate, &inputs.accumulated_directions, global_zero)?;
    let residual_direction_digest = selected_direction_digest(&residual_prefix);
    let residual_coefficient_digest = selected_residual_digest(&residual_prefix);

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
        expected_accumulated_direction_count: expected_accumulated,
        observed_accumulated_direction_count: inputs.accumulated_directions.len(),
        accumulated_direction_count_exact: inputs.accumulated_directions.len()
            == expected_accumulated,
        omitted_accumulated_direction_rejected: validate_accumulated_directions(
            &inputs.accumulated_directions[..expected_accumulated - 1],
            expected_accumulated,
        )
        .is_err(),
    };
    ensure!(
        census_controls.per_term_generated_equals_visited_equals_accepted
            && census_controls.zero_skipped_unclassified_failed
            && census_controls.omitted_last_orbit_rejected
            && census_controls.decremented_global_census_rejected
            && census_controls.accumulated_direction_count_exact
            && census_controls.omitted_accumulated_direction_rejected,
        "census hostile control failed"
    );

    let selection_controls = if global_zero {
        SelectionControls {
            exact_batch_count_or_zero_terminal: residual_prefix.is_empty(),
            strict_signed_lexicographic_order: true,
            excludes_accumulated_directions: true,
            direction_reordering_changes_digest: true,
            coefficient_plus_one_changes_digest: true,
        }
    } else {
        let mut reordered = residual_prefix.clone();
        reordered.swap(0, 1);
        let mut coefficient_mutant = residual_prefix.clone();
        coefficient_mutant[0].coefficient =
            (parse_bigint(&coefficient_mutant[0].coefficient)? + BigInt::from(1)).to_string();
        let accumulated = inputs
            .accumulated_directions
            .iter()
            .copied()
            .collect::<HashSet<_>>();
        SelectionControls {
            exact_batch_count_or_zero_terminal: residual_prefix.len() == RESIDUAL_PREFIX_K,
            strict_signed_lexicographic_order: residual_prefix
                .windows(2)
                .all(|pair| pair[0].direction < pair[1].direction),
            excludes_accumulated_directions: residual_prefix
                .iter()
                .all(|item| !accumulated.contains(&item.direction)),
            direction_reordering_changes_digest: selected_direction_digest(&reordered)
                != residual_direction_digest,
            coefficient_plus_one_changes_digest: selected_residual_digest(&coefficient_mutant)
                != residual_coefficient_digest,
        }
    };
    ensure!(
        selection_controls.exact_batch_count_or_zero_terminal
            && selection_controls.strict_signed_lexicographic_order
            && selection_controls.excludes_accumulated_directions
            && selection_controls.direction_reordering_changes_digest
            && selection_controls.coefficient_plus_one_changes_digest,
        "residual-prefix hostile control failed"
    );

    let mut source_and_audit_bindings = BTreeMap::new();
    for (path, sha256) in inputs
        .manifest
        .bindings_by_path
        .iter()
        .chain(inputs.protocol_manifest.bindings_by_path.iter())
    {
        insert_output_binding(
            &mut source_and_audit_bindings,
            Binding {
                path: path.clone(),
                sha256: sha256.clone(),
            },
        )?;
    }
    for binding in [source_audit.clone(), inputs.candidate_binding.clone()] {
        insert_output_binding(&mut source_and_audit_bindings, binding)?;
    }
    let all_hinge_digest = hinge_digest(&aggregate.hinges, false);
    let nonzero_hinge_digest = hinge_digest(&aggregate.hinges, true);
    let complete_residual_digest = residual_digest(&aggregate, None, None);
    let term_transcript_digest = sha256_bytes(&serde_json::to_vec(&aggregate.term_receipts)?);
    let output = Output {
        schema: STAGE_E_OUTPUT_SCHEMA,
        result,
        claim_boundary: CLAIM_BOUNDARY,
        g0140_manifest: Binding {
            path: G0140_MANIFEST_PATH.to_string(),
            sha256: inputs.protocol_manifest.sha256.clone(),
        },
        g0135_manifest: Binding {
            path: SHARED_MANIFEST_PATH.to_string(),
            sha256: inputs.manifest.sha256.clone(),
        },
        protocol: binding_for_path(&root, PREREGISTRATION_PATH)?,
        producer_source: binding_for_path(&root, STAGE_E_SOURCE_PATH)?,
        producer_engine: binding_for_path(&root, STAGE_E_ENGINE_PATH)?,
        producer_cargo_manifest: binding_for_path(&root, STAGE_E_CARGO_PATH)?,
        producer_cargo_lock: binding_for_path(&root, STAGE_E_LOCK_PATH)?,
        producer_executable,
        stage_e_source_audit: source_audit,
        stage_d_member: inputs.candidate_binding.clone(),
        stage_output_git_commits: inputs.stage_output_git_commits.clone(),
        source_and_audit_bindings,
        candidate_schema: candidate.schema.clone(),
        candidate_result: candidate.result.clone(),
        base_rows: candidate.base_rows,
        appended_rows: candidate.appended_rows,
        rows: candidate.rows,
        records: candidate.records,
        selected_pool_indices: candidate.selected_pool_indices.clone(),
        selected_pool_indices_u64le_sha256: candidate.selected_pool_indices_u64le_sha256.clone(),
        selected_directions: candidate.selected_directions.clone(),
        selected_directions_i8_sha256: candidate.selected_directions_i8_sha256.clone(),
        selected_rank: candidate.rank,
        support_columns: candidate.support_sequences.len(),
        terms: candidate.terms.len(),
        target_scale: candidate.target_scale.clone(),
        target_subtraction_coordinate_10: target_subtraction.to_string(),
        stage_d_all_rational_rows_replayed: candidate.replay_receipt.rational_all_rows_replayed,
        stage_d_all_integer_rows_replayed: candidate.replay_receipt.integer_all_rows_replayed,
        stage_d_primitive_denominator_clearing: candidate
            .replay_receipt
            .primitive_denominator_clearing,
        stage_d_coefficient_plus_one_mutant_rejected: candidate
            .coefficient_plus_one_mutant
            .rejected,
        stage_d_prior_scale_carryover_mutant_rejected: candidate
            .prior_target_scale_carryover_mutant_rejected,
        independent_finite_row_replay,
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
        inherited_accumulated_directions: INHERITED_DIRECTIONS,
        stage_d_selected_accumulated_directions: candidate.appended_rows,
        accumulated_direction_count: expected_accumulated,
        all_accumulated_directions_exact_zero: true,
        linear_residuals_after_target: aggregate.linear.iter().map(ToString::to_string).collect(),
        all_11_linear_residuals_exact_zero: all_linear_zero,
        first_nonzero_hinge,
        first_nonzero_linear,
        residual_prefix_k: if global_zero { 0 } else { RESIDUAL_PREFIX_K },
        residual_prefix_count: residual_prefix.len(),
        residual_prefix_directions_i8_sha256: residual_direction_digest,
        residual_prefix_exact_residuals_decimal_lf_sha256: residual_coefficient_digest,
        residual_prefix,
        no_automatic_next_study: true,
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
        "residual_prefix_count": output.residual_prefix_count,
        "residual_prefix_directions_i8_sha256": output.residual_prefix_directions_i8_sha256,
        "residual_prefix_exact_residuals_decimal_lf_sha256": output.residual_prefix_exact_residuals_decimal_lf_sha256,
    });
    let mut serialized = serde_json::to_vec_pretty(&output)?;
    serialized.push(b'\n');

    let end = load_and_validate_inputs(&root)?;
    let end_source_audit = end.stage_e_source_audit.clone();
    let end_executable = validate_current_release_executable(&root)?;
    ensure!(
        end.manifest.sha256 == inputs.manifest.sha256
            && end.manifest.bindings_by_path == inputs.manifest.bindings_by_path
            && end.protocol_manifest.sha256 == inputs.protocol_manifest.sha256
            && end.protocol_manifest.bindings_by_path == inputs.protocol_manifest.bindings_by_path
            && end.ancestor_candidate_binding == inputs.ancestor_candidate_binding
            && end.ancestor_candidate.terms == inputs.ancestor_candidate.terms
            && end.candidate_binding == inputs.candidate_binding
            && end.stage_output_git_commits == inputs.stage_output_git_commits
            && end.candidate.terms == candidate.terms
            && end.candidate.target == candidate.target
            && end.candidate.selected_pool_indices == candidate.selected_pool_indices
            && end.candidate.selected_directions == candidate.selected_directions
            && end.accumulated_directions == inputs.accumulated_directions
            && end_source_audit == output.stage_e_source_audit
            && end_executable == output.producer_executable
            && binding_for_path(&root, PREREGISTRATION_PATH)? == output.protocol
            && binding_for_path(&root, STAGE_E_SOURCE_PATH)? == output.producer_source
            && binding_for_path(&root, STAGE_E_ENGINE_PATH)? == output.producer_engine
            && binding_for_path(&root, STAGE_E_CARGO_PATH)? == output.producer_cargo_manifest
            && binding_for_path(&root, STAGE_E_LOCK_PATH)? == output.producer_cargo_lock,
        "input/source/audit drift during G-0140 Stage-E replay"
    );
    publish_exclusive(output_path, &serialized)?;
    println!("{stdout}");
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() == 2 && args[1] == "--self-test" {
        self_test()?;
        println!("G-0140 Stage E self-test PASS");
        return Ok(());
    }
    if args.len() == 2 && args[1] == "--preflight-static" {
        return stage_e_static_preflight();
    }
    if args.len() == 4 && args[1] == "--preflight" {
        return stage_e_full_preflight(Path::new(&args[2]), Path::new(&args[3]));
    }
    ensure!(
        args.len() == 4,
        "usage: g0140-stage-e-global-replay --self-test | --preflight-static | --preflight MANIFEST STAGE_D_MEMBER | MANIFEST STAGE_D_MEMBER OUTPUT"
    );
    stage_e_run(
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
