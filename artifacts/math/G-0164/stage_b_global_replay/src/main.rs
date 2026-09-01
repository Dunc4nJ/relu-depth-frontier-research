mod candidate;
mod engine;

use anyhow::{Context, Result, ensure};
use candidate::{
    Binding, CommitBinding, DirectBasisMember, ValidatedCandidate, binding_for_path,
    checked_repo_path, git_commit_for_path, git_is_ancestor, load_and_validate, publish_exclusive,
    rehash_snapshot, sha256_path, strict_json,
};
use engine::{
    ExactNormalForm, exact_hinge_coefficients, factorial, normal_form_digest,
    validated_full_normal_form,
};
use g0117_global_coordinate_pricer::{N, Record, validate_direction};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs::File;
use std::io::BufReader;
use std::path::{Path, PathBuf};
use std::time::Instant;

const RECORDS: usize = 163_740;
const BASE_ROWS: usize = 412;
const APPENDED_ROWS: usize = 128;
const ROWS: usize = BASE_ROWS + APPENDED_ROWS;
const RANK: usize = 349;
const INHERITED_DIRECTIONS: usize = 100;
const ACCUMULATED_DIRECTIONS: usize = INHERITED_DIRECTIONS + APPENDED_ROWS;
const RESIDUAL_PREFIX_K: usize = 128;
const THREADS: usize = 12;

const PREREGISTRATION_PATH: &str = "artifacts/math/G-0164/PREREGISTRATION.md";
const FINITE_MANIFEST_PATH: &str = "artifacts/math/G-0164/all128_manifest_v1.json";
const FINITE_MEMBER_PATH: &str = "artifacts/math/G-0164/all128_direct_basis_member_v1.json";
const GLOBAL_MANIFEST_PATH: &str = "artifacts/math/G-0164/all128_global_replay_manifest_v1.json";
const GLOBAL_OUTPUT_PATH: &str = "artifacts/math/G-0164/all128_global_replay_v1.json";
const SOURCE_PATH: &str = "artifacts/math/G-0164/stage_b_global_replay/src/main.rs";
const CANDIDATE_SOURCE_PATH: &str = "artifacts/math/G-0164/stage_b_global_replay/src/candidate.rs";
const ENGINE_PATH: &str = "artifacts/math/G-0164/stage_b_global_replay/src/engine.rs";
const CARGO_PATH: &str = "artifacts/math/G-0164/stage_b_global_replay/Cargo.toml";
const LOCK_PATH: &str = "artifacts/math/G-0164/stage_b_global_replay/Cargo.lock";
const EXECUTABLE_PATH: &str =
    "artifacts/math/G-0164/stage_b_global_replay/target/release/g0164-stage-b-global-replay";
const SOURCE_AUDIT_PREREGISTRATION_PATH: &str =
    "artifacts/reviews/G-0166-g0164-global-replay-source/PREREGISTRATION.md";
const SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0166-g0164-global-replay-source/SOURCE_AUDIT_RECEIPT.json";

const PARENT_SOURCE_PATH: &str = "artifacts/math/G-0140/stage_e_global_replay/src/main.rs";
const PARENT_ENGINE_PATH: &str = "artifacts/math/G-0140/stage_e_global_replay/src/engine.rs";
const PARENT_SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0163-g0140-stage-e-final4-source/SOURCE_AUDIT_RECEIPT.json";
const G0117_CARGO_PATH: &str = "artifacts/math/G-0117/Cargo.toml";
const G0117_LIB_PATH: &str = "artifacts/math/G-0117/src/lib.rs";

const PREREGISTRATION_SHA256: &str =
    "f28813a182327e38e713c8a20e9039f12d9722861455dcb1a5fb0bb332b00c10";
const FINITE_MANIFEST_SHA256: &str =
    "c6d6b0f995f26d87321e3c27a36bf39ed6d8eb40a185a85f25b73a5e98120420";
const FINITE_MEMBER_SHA256: &str =
    "bc4d1c58587aef6cd3b555b166ba7ec8e0f365cb0089cfd889a235e8f2e20119";
const PARENT_SOURCE_SHA256: &str =
    "be4852b63ff2118182cdd07ead85708f0b4ef0785445f0f873ebd4367c9e866a";
const PARENT_ENGINE_SHA256: &str =
    "b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c";
const PARENT_SOURCE_AUDIT_SHA256: &str =
    "a86e851e02a9b6805060d72a6d1191ad8275693b6b396250f768de24890d51e9";
const G0117_CARGO_SHA256: &str = "0e2ff3c73ce82b508ae21b35bc973c202efbeae03b7e9cf78d3b784664ce5815";
const G0117_LIB_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";

const GLOBAL_MANIFEST_SCHEMA: &str = "max11-g0164-all128-global-replay-manifest-v1";
const GLOBAL_MANIFEST_RESULT: &str = "FROZEN_BEFORE_G0164_COMPLETE_GLOBAL_REPLAY";
const FINITE_MEMBER_SCHEMA: &str = "max11-g0164-all128-direct-basis-member-v1";
const FINITE_MEMBER_RESULT: &str = "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER";
const OUTPUT_SCHEMA: &str = "max11-g0164-all128-global-replay-v1";
const SOURCE_AUDIT_SCHEMA: &str = "max11-g0166-g0164-global-replay-source-audit-v1";
const SOURCE_AUDIT_RESULT: &str = "SOURCE_CUSTODY_AUDIT_PASS_T1";
const SOURCE_AUDIT_EVIDENCE: &str = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT";
const ZERO_RESULT: &str = "GLOBAL_EXACT_ZERO";
const RESIDUAL_RESULT: &str = "EXACT_RESIDUAL_CONTINUE";
const DECISION_RULE: &str = "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate";
const CLAIM_BOUNDARY: &str = "GLOBAL_EXACT_ZERO establishes only the complete arbitrary-precision ordered-chamber normal-form identity for the exact frozen G-0164 all-128 direct-basis member. EXACT_RESIDUAL_CONTINUE refutes only that deterministic member and reports the signed-lexicographic residual prefix without opening another study. Neither branch proves family completeness, frozen-family nonmembership, an unrestricted theorem, a lower bound, minimality, the all-n target, refereed status, formalization, or a Lean theorem.";
const SOURCE_AUDIT_CLAIM_BOUNDARY: &str = "T1 source/custody clearance for the exact frozen G-0164 complete-global-replay producer bytes only; no scientific manifest, finite member, or global output was observed, no scientific replay was run, and no mathematical claim is promoted.";
const SOURCE_AUDIT_NO_CLAIM: &str = "This source audit does not adjudicate any future G-0164 scientific manifest, finite member, or global result, establish or exclude a global exact identity, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_CANDIDATE_SOURCE: &[u8] = include_bytes!("candidate.rs");
const COMPILED_ENGINE: &[u8] = include_bytes!("engine.rs");
const COMPILED_CARGO: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../../PREREGISTRATION.md");
const COMPILED_PARENT_SOURCE: &[u8] =
    include_bytes!("../../../G-0140/stage_e_global_replay/src/main.rs");
const COMPILED_PARENT_ENGINE: &[u8] =
    include_bytes!("../../../G-0140/stage_e_global_replay/src/engine.rs");
const COMPILED_PARENT_SOURCE_AUDIT: &[u8] = include_bytes!(
    "../../../../reviews/G-0163-g0140-stage-e-final4-source/SOURCE_AUDIT_RECEIPT.json"
);
const COMPILED_G0117_CARGO: &[u8] = include_bytes!("../../../G-0117/Cargo.toml");
const COMPILED_G0117_LIB: &[u8] = include_bytes!("../../../G-0117/src/lib.rs");

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ProducerBindings {
    git_commit: String,
    main_source: Binding,
    candidate_source: Binding,
    engine_source: Binding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    release_executable: Binding,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct GlobalParameters {
    n: usize,
    records: usize,
    base_rows: usize,
    appended_rows: usize,
    rows: usize,
    rank: usize,
    selected_pool_indices: Vec<usize>,
    inherited_accumulated_directions: usize,
    total_accumulated_directions: usize,
    terms: usize,
    threads: usize,
    arithmetic: String,
    decision_rule: String,
    labelled_permutations: u64,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct PlannedOutput {
    path: String,
    schema: String,
    allowed_results: Vec<String>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct GlobalManifest {
    schema: String,
    result: String,
    claim_boundary: String,
    preregistration: CommitBinding,
    finite_manifest: CommitBinding,
    finite_member: CommitBinding,
    producer: ProducerBindings,
    g0117_cargo_manifest: CommitBinding,
    g0117_lib_source: CommitBinding,
    source_audit_preregistration: CommitBinding,
    source_audit: CommitBinding,
    parent_replay_source: CommitBinding,
    parent_replay_engine: CommitBinding,
    parent_source_audit: CommitBinding,
    parameters: GlobalParameters,
    planned_output: PlannedOutput,
    scientific_replay_executed: bool,
    scientific_output_created: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuditReviewer {
    agent_name: String,
    program: String,
    model: String,
    same_model_lineage: bool,
    fresh_context: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuditPreregistration {
    path: String,
    sha256: String,
    git_commit: String,
    committed_and_pushed_before_subject_source_inspection: bool,
    committed_and_pushed_before_runtime_checks: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuditSubject {
    git_commit: String,
    commit_object_and_working_bytes_equal_for_all_bindings: bool,
    bindings: AuditSubjectBindings,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuditSubjectBindings {
    main_source: Binding,
    candidate_source: Binding,
    engine_source: Binding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    g0117_cargo_manifest: Binding,
    g0117_lib_source: Binding,
    release_executable: Binding,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct AuditChecks {
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
    engine_byte_identity_with_g0140_verified: bool,
    finite_member_source_audit_gate_verified: bool,
    finite_member_global_manifest_commit_chain_verified: bool,
    scientific_outputs_excluded_from_manifest_bindings: bool,
    dynamic_direct_basis_member_contract_verified: bool,
    global_zero_and_residual_branches_verified: bool,
    complete_label_census_and_end_rehash_verified: bool,
    overwrite_refusal_verified: bool,
    prohibited_scientific_modes_not_run: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditReceipt {
    schema: String,
    verdict: String,
    result: String,
    evidence_class: String,
    claim_boundary: String,
    reviewer: AuditReviewer,
    preregistration: AuditPreregistration,
    subject: AuditSubject,
    required_checks: AuditChecks,
    scientific_manifest_observed: bool,
    scientific_input_observed: bool,
    scientific_output_observed: bool,
    scientific_replay_run: bool,
    no_claim: String,
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
    compressed_leaves: u64,
    inactive_label_multiplicity: u64,
    labelled_permutations: u64,
    hinge_entries: usize,
    normal_form_sha256: String,
    independent_exact_linear_crosscheck: bool,
    bounded_kernel_crosscheck: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
struct ExactLinear {
    coordinate: usize,
    coefficient: String,
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

#[derive(Clone, Debug, Serialize)]
struct MutationControl {
    name: &'static str,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
    baseline_sha256: String,
    mutated_sha256: String,
    detected: bool,
}

#[derive(Clone, Debug, Serialize)]
struct CensusControls {
    dynamic_term_count: usize,
    factorial_11: u64,
    expected_labelled_permutations: u64,
    observed_labelled_permutations: u64,
    all_term_receipts_reconciled: bool,
    expected_accumulated_directions: usize,
    observed_accumulated_directions: usize,
}

#[derive(Clone, Debug, Serialize)]
struct PrefixControls {
    maximum_k: usize,
    expected_count: usize,
    observed_count: usize,
    strict_signed_lexicographic_order: bool,
    excludes_accumulated_directions: bool,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
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
    independent_finite_replay: candidate::FiniteReplayReceipt,
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
    selected_accumulated_directions: usize,
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
    prefix_controls: PrefixControls,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    candidate_rehashed_at_end: bool,
    wall_seconds: f64,
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn repo_root() -> Result<PathBuf> {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(4)
        .context("resolve repository root")?
        .canonicalize()
        .context("canonicalize repository root")
}

fn validate_compiled_bytes(root: &Path) -> Result<()> {
    for (compiled, path) in [
        (COMPILED_SOURCE, SOURCE_PATH),
        (COMPILED_CANDIDATE_SOURCE, CANDIDATE_SOURCE_PATH),
        (COMPILED_ENGINE, ENGINE_PATH),
        (COMPILED_CARGO, CARGO_PATH),
        (COMPILED_LOCK, LOCK_PATH),
        (COMPILED_PREREGISTRATION, PREREGISTRATION_PATH),
        (COMPILED_PARENT_SOURCE, PARENT_SOURCE_PATH),
        (COMPILED_PARENT_ENGINE, PARENT_ENGINE_PATH),
        (COMPILED_PARENT_SOURCE_AUDIT, PARENT_SOURCE_AUDIT_PATH),
        (COMPILED_G0117_CARGO, G0117_CARGO_PATH),
        (COMPILED_G0117_LIB, G0117_LIB_PATH),
    ] {
        ensure!(
            sha256_bytes(compiled) == sha256_path(&checked_repo_path(root, path)?)?,
            "running binary was compiled against different bytes: {path}"
        );
    }
    ensure!(
        sha256_bytes(COMPILED_PREREGISTRATION) == PREREGISTRATION_SHA256
            && sha256_bytes(COMPILED_PARENT_SOURCE) == PARENT_SOURCE_SHA256
            && sha256_bytes(COMPILED_PARENT_ENGINE) == PARENT_ENGINE_SHA256
            && sha256_bytes(COMPILED_PARENT_SOURCE_AUDIT) == PARENT_SOURCE_AUDIT_SHA256
            && sha256_bytes(COMPILED_G0117_CARGO) == G0117_CARGO_SHA256
            && sha256_bytes(COMPILED_G0117_LIB) == G0117_LIB_SHA256
            && COMPILED_ENGINE == COMPILED_PARENT_ENGINE,
        "compiled provenance or inherited engine drift"
    );
    Ok(())
}

fn check_binding(root: &Path, binding: &Binding, expected_path: &str) -> Result<()> {
    ensure!(
        binding.path == expected_path,
        "binding path drift: {expected_path}"
    );
    ensure!(
        binding.sha256 == sha256_path(&checked_repo_path(root, expected_path)?)?,
        "binding digest drift: {expected_path}"
    );
    Ok(())
}

fn check_commit_binding(root: &Path, binding: &CommitBinding, expected_path: &str) -> Result<()> {
    check_binding(
        root,
        &Binding {
            path: binding.path.clone(),
            sha256: binding.sha256.clone(),
        },
        expected_path,
    )?;
    ensure!(
        binding.git_commit == git_commit_for_path(root, expected_path)?,
        "binding commit drift: {expected_path}"
    );
    Ok(())
}

fn audit_bindings(receipt: &SourceAuditReceipt) -> [(&'static str, &Binding); 8] {
    [
        (SOURCE_PATH, &receipt.subject.bindings.main_source),
        (
            CANDIDATE_SOURCE_PATH,
            &receipt.subject.bindings.candidate_source,
        ),
        (ENGINE_PATH, &receipt.subject.bindings.engine_source),
        (CARGO_PATH, &receipt.subject.bindings.cargo_manifest),
        (LOCK_PATH, &receipt.subject.bindings.cargo_lock),
        (
            G0117_CARGO_PATH,
            &receipt.subject.bindings.g0117_cargo_manifest,
        ),
        (G0117_LIB_PATH, &receipt.subject.bindings.g0117_lib_source),
        (
            EXECUTABLE_PATH,
            &receipt.subject.bindings.release_executable,
        ),
    ]
}

fn all_audit_checks(checks: &AuditChecks) -> bool {
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
        && checks.engine_byte_identity_with_g0140_verified
        && checks.finite_member_source_audit_gate_verified
        && checks.finite_member_global_manifest_commit_chain_verified
        && checks.scientific_outputs_excluded_from_manifest_bindings
        && checks.dynamic_direct_basis_member_contract_verified
        && checks.global_zero_and_residual_branches_verified
        && checks.complete_label_census_and_end_rehash_verified
        && checks.overwrite_refusal_verified
        && checks.prohibited_scientific_modes_not_run
}

fn validate_source_audit(
    root: &Path,
    expected: &CommitBinding,
    producer: &ProducerBindings,
    g0117_cargo_manifest: &CommitBinding,
    g0117_lib_source: &CommitBinding,
) -> Result<Binding> {
    check_commit_binding(root, expected, SOURCE_AUDIT_PATH)?;
    let receipt: SourceAuditReceipt = strict_json(BufReader::new(File::open(checked_repo_path(
        root,
        SOURCE_AUDIT_PATH,
    )?)?))?;
    ensure!(
        receipt.schema == SOURCE_AUDIT_SCHEMA
            && receipt.verdict == "PASS"
            && receipt.result == SOURCE_AUDIT_RESULT
            && receipt.evidence_class == SOURCE_AUDIT_EVIDENCE
            && receipt.claim_boundary == SOURCE_AUDIT_CLAIM_BOUNDARY
            && receipt.no_claim == SOURCE_AUDIT_NO_CLAIM
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_input_observed
            && !receipt.scientific_output_observed
            && !receipt.scientific_replay_run
            && !receipt.reviewer.agent_name.is_empty()
            && receipt.reviewer.program == "codex"
            && !receipt.reviewer.model.is_empty()
            && receipt.reviewer.same_model_lineage
            && receipt.reviewer.fresh_context
            && receipt.preregistration.path == SOURCE_AUDIT_PREREGISTRATION_PATH
            && receipt
                .preregistration
                .committed_and_pushed_before_subject_source_inspection
            && receipt
                .preregistration
                .committed_and_pushed_before_runtime_checks
            && receipt.subject.git_commit == producer.git_commit
            && receipt
                .subject
                .commit_object_and_working_bytes_equal_for_all_bindings
            && all_audit_checks(&receipt.required_checks),
        "G-0166 source-audit semantic boundary drift"
    );
    ensure!(
        receipt.preregistration.sha256
            == sha256_path(&checked_repo_path(root, SOURCE_AUDIT_PREREGISTRATION_PATH)?)?
            && receipt.preregistration.git_commit
                == git_commit_for_path(root, SOURCE_AUDIT_PREREGISTRATION_PATH)?,
        "G-0166 preregistration custody drift"
    );
    let expected_bindings = [
        producer.main_source.clone(),
        producer.candidate_source.clone(),
        producer.engine_source.clone(),
        producer.cargo_manifest.clone(),
        producer.cargo_lock.clone(),
        Binding {
            path: g0117_cargo_manifest.path.clone(),
            sha256: g0117_cargo_manifest.sha256.clone(),
        },
        Binding {
            path: g0117_lib_source.path.clone(),
            sha256: g0117_lib_source.sha256.clone(),
        },
        producer.release_executable.clone(),
    ];
    for ((path, audited), manifest_binding) in
        audit_bindings(&receipt).into_iter().zip(&expected_bindings)
    {
        check_binding(root, audited, path)?;
        ensure!(
            audited == manifest_binding,
            "G-0166/manifest binding drift: {path}"
        );
    }
    Ok(Binding {
        path: expected.path.clone(),
        sha256: expected.sha256.clone(),
    })
}

fn expected_labelled_permutations(terms: usize) -> Result<u64> {
    u64::try_from(terms)?
        .checked_mul(factorial(N))
        .context("labelled-permutation census overflow")
}

fn validate_global_manifest(
    root: &Path,
    inputs: &ValidatedCandidate,
) -> Result<(Binding, Binding, BTreeMap<String, Binding>)> {
    let path = checked_repo_path(root, GLOBAL_MANIFEST_PATH)?;
    let manifest_binding = Binding {
        path: GLOBAL_MANIFEST_PATH.to_string(),
        sha256: sha256_path(&path)?,
    };
    let manifest: GlobalManifest = strict_json(BufReader::new(File::open(path)?))?;
    let expected_parameters = GlobalParameters {
        n: N,
        records: RECORDS,
        base_rows: BASE_ROWS,
        appended_rows: APPENDED_ROWS,
        rows: ROWS,
        rank: RANK,
        selected_pool_indices: (0..APPENDED_ROWS).collect(),
        inherited_accumulated_directions: INHERITED_DIRECTIONS,
        total_accumulated_directions: ACCUMULATED_DIRECTIONS,
        terms: inputs.candidate.terms.len(),
        threads: THREADS,
        arithmetic: "signed_num_bigint_BigInt".to_string(),
        decision_rule: DECISION_RULE.to_string(),
        labelled_permutations: expected_labelled_permutations(inputs.candidate.terms.len())?,
    };
    ensure!(
        inputs.candidate.schema == FINITE_MEMBER_SCHEMA
            && inputs.candidate.result == FINITE_MEMBER_RESULT
            && inputs.manifest_binding == inputs.finite_manifest_binding
            && inputs.manifest.schema == "max11-g0164-all128-manifest-v1"
            && inputs.finite_replay.residuals_decimal_lf_sha256 == candidate::zero_lf_digest(ROWS)
            && manifest.schema == GLOBAL_MANIFEST_SCHEMA
            && manifest.result == GLOBAL_MANIFEST_RESULT
            && manifest.claim_boundary == CLAIM_BOUNDARY
            && manifest.parameters == expected_parameters
            && manifest.planned_output.path == GLOBAL_OUTPUT_PATH
            && manifest.planned_output.schema == OUTPUT_SCHEMA
            && manifest.planned_output.allowed_results
                == vec![ZERO_RESULT.to_string(), RESIDUAL_RESULT.to_string()]
            && !manifest.scientific_replay_executed
            && !manifest.scientific_output_created,
        "G-0164 global manifest contract drift"
    );
    for (binding, path) in [
        (&manifest.preregistration, PREREGISTRATION_PATH),
        (&manifest.finite_manifest, FINITE_MANIFEST_PATH),
        (&manifest.finite_member, FINITE_MEMBER_PATH),
        (&manifest.g0117_cargo_manifest, G0117_CARGO_PATH),
        (&manifest.g0117_lib_source, G0117_LIB_PATH),
        (
            &manifest.source_audit_preregistration,
            SOURCE_AUDIT_PREREGISTRATION_PATH,
        ),
        (&manifest.source_audit, SOURCE_AUDIT_PATH),
        (&manifest.parent_replay_source, PARENT_SOURCE_PATH),
        (&manifest.parent_replay_engine, PARENT_ENGINE_PATH),
        (&manifest.parent_source_audit, PARENT_SOURCE_AUDIT_PATH),
    ] {
        check_commit_binding(root, binding, path)?;
    }
    ensure!(
        manifest.preregistration.sha256 == PREREGISTRATION_SHA256
            && manifest.finite_manifest.sha256 == FINITE_MANIFEST_SHA256
            && manifest.finite_member.sha256 == FINITE_MEMBER_SHA256
            && manifest.finite_manifest.sha256 == inputs.finite_manifest_binding.sha256
            && manifest.finite_member.sha256 == inputs.candidate_binding.sha256
            && manifest.parent_replay_source.sha256 == PARENT_SOURCE_SHA256
            && manifest.parent_replay_engine.sha256 == PARENT_ENGINE_SHA256
            && manifest.parent_source_audit.sha256 == PARENT_SOURCE_AUDIT_SHA256
            && manifest.g0117_cargo_manifest.sha256 == G0117_CARGO_SHA256
            && manifest.g0117_lib_source.sha256 == G0117_LIB_SHA256,
        "G-0164 global manifest fixed binding drift"
    );
    let producer_paths = [
        (&manifest.producer.main_source, SOURCE_PATH),
        (&manifest.producer.candidate_source, CANDIDATE_SOURCE_PATH),
        (&manifest.producer.engine_source, ENGINE_PATH),
        (&manifest.producer.cargo_manifest, CARGO_PATH),
        (&manifest.producer.cargo_lock, LOCK_PATH),
        (&manifest.producer.release_executable, EXECUTABLE_PATH),
    ];
    for (binding, path) in producer_paths {
        check_binding(root, binding, path)?;
        ensure!(
            git_commit_for_path(root, path)? == manifest.producer.git_commit,
            "producer commit drift: {path}"
        );
    }
    let audit = validate_source_audit(
        root,
        &manifest.source_audit,
        &manifest.producer,
        &manifest.g0117_cargo_manifest,
        &manifest.g0117_lib_source,
    )?;
    let manifest_commit = git_commit_for_path(root, GLOBAL_MANIFEST_PATH)?;
    git_is_ancestor(
        root,
        &manifest.finite_manifest.git_commit,
        &manifest.finite_member.git_commit,
        "finite manifest -> member",
    )?;
    git_is_ancestor(
        root,
        &manifest.finite_member.git_commit,
        &manifest_commit,
        "finite member -> global manifest",
    )?;
    git_is_ancestor(
        root,
        &manifest.g0117_cargo_manifest.git_commit,
        &manifest.producer.git_commit,
        "G-0117 Cargo manifest -> global producer",
    )?;
    git_is_ancestor(
        root,
        &manifest.g0117_lib_source.git_commit,
        &manifest.producer.git_commit,
        "G-0117 library source -> global producer",
    )?;
    git_is_ancestor(
        root,
        &manifest.producer.git_commit,
        &manifest.source_audit_preregistration.git_commit,
        "global source -> audit preregistration",
    )?;
    git_is_ancestor(
        root,
        &manifest.source_audit_preregistration.git_commit,
        &manifest.source_audit.git_commit,
        "audit preregistration -> receipt",
    )?;
    git_is_ancestor(
        root,
        &manifest.source_audit.git_commit,
        &manifest_commit,
        "source audit -> global manifest",
    )?;
    let mut bindings = BTreeMap::new();
    for binding in [
        binding_for_path(root, PREREGISTRATION_PATH)?,
        inputs.finite_manifest_binding.clone(),
        inputs.candidate_binding.clone(),
        manifest.producer.main_source,
        manifest.producer.candidate_source,
        manifest.producer.engine_source,
        manifest.producer.cargo_manifest,
        manifest.producer.cargo_lock,
        manifest.producer.release_executable,
        Binding {
            path: manifest.g0117_cargo_manifest.path,
            sha256: manifest.g0117_cargo_manifest.sha256,
        },
        Binding {
            path: manifest.g0117_lib_source.path,
            sha256: manifest.g0117_lib_source.sha256,
        },
        binding_for_path(root, SOURCE_AUDIT_PREREGISTRATION_PATH)?,
        audit.clone(),
        Binding {
            path: manifest.parent_replay_source.path,
            sha256: manifest.parent_replay_source.sha256,
        },
        Binding {
            path: manifest.parent_replay_engine.path,
            sha256: manifest.parent_replay_engine.sha256,
        },
        Binding {
            path: manifest.parent_source_audit.path,
            sha256: manifest.parent_source_audit.sha256,
        },
    ] {
        ensure!(
            bindings.insert(binding.path.clone(), binding).is_none(),
            "duplicate global custody binding"
        );
    }
    ensure!(
        !bindings.contains_key(GLOBAL_OUTPUT_PATH),
        "global manifest circularly binds output"
    );
    Ok((manifest_binding, audit, bindings))
}

fn validate_current_executable(root: &Path) -> Result<Binding> {
    let current = std::env::current_exe()?.canonicalize()?;
    let expected = checked_repo_path(root, EXECUTABLE_PATH)?;
    ensure!(
        current == expected,
        "preflight/run requires frozen release executable"
    );
    git_commit_for_path(root, EXECUTABLE_PATH)?;
    binding_for_path(root, EXECUTABLE_PATH)
}

fn term_receipt(record: &Record, form: &ExactNormalForm) -> Result<TermNormalFormReceipt> {
    let inactive = N
        .checked_sub(record.active_vertices)
        .context("active vertex census exceeds n")?;
    let multiplicity = factorial(inactive);
    ensure!(
        form.compressed_leaves * multiplicity == form.labelled_permutations
            && form.labelled_permutations == factorial(N),
        "compressed orbit reconciliation failed"
    );
    Ok(TermNormalFormReceipt {
        sequence: record.sequence,
        active_vertices: record.active_vertices,
        compressed_leaves: form.compressed_leaves,
        inactive_label_multiplicity: multiplicity,
        labelled_permutations: form.labelled_permutations,
        hinge_entries: form.hinges.len(),
        normal_form_sha256: normal_form_digest(form, None, None),
        independent_exact_linear_crosscheck: true,
        bounded_kernel_crosscheck: true,
    })
}

fn add_exact(
    aggregate: &mut ExactAggregate,
    record: &Record,
    form: ExactNormalForm,
    coefficient: &BigInt,
) -> Result<()> {
    aggregate.terms += 1;
    aggregate.labelled_permutations_checked += form.labelled_permutations;
    aggregate.hinge_entries_processed += u64::try_from(form.hinges.len())?;
    aggregate.term_receipts.push(term_receipt(record, &form)?);
    for (target, value) in aggregate.linear.iter_mut().zip(form.linear) {
        *target += coefficient * value;
    }
    for (direction, value) in form.hinges {
        *aggregate.hinges.entry(direction).or_default() += coefficient * value;
    }
    Ok(())
}

fn merge_exact(mut left: ExactAggregate, right: ExactAggregate) -> ExactAggregate {
    if left.hinges.len() < right.hinges.len() {
        return merge_exact(right, left);
    }
    left.terms += right.terms;
    left.labelled_permutations_checked += right.labelled_permutations_checked;
    left.hinge_entries_processed += right.hinge_entries_processed;
    for (target, value) in left.linear.iter_mut().zip(right.linear) {
        *target += value;
    }
    for (direction, value) in right.hinges {
        *left.hinges.entry(direction).or_default() += value;
    }
    left.term_receipts.extend(right.term_receipts);
    left
}

fn validate_term_receipts(receipts: &[TermNormalFormReceipt], terms: usize) -> Result<()> {
    ensure!(receipts.len() == terms, "term receipt census drift");
    ensure!(
        receipts.iter().all(|receipt| {
            receipt.active_vertices <= N
                && receipt.compressed_leaves * receipt.inactive_label_multiplicity == factorial(N)
                && receipt.labelled_permutations == factorial(N)
                && receipt.independent_exact_linear_crosscheck
                && receipt.bounded_kernel_crosscheck
                && receipt.normal_form_sha256.len() == 64
        }),
        "term receipt reconciliation failed"
    );
    Ok(())
}

fn direct_accumulated_prices(
    records: &[Record],
    candidate: &DirectBasisMember,
    directions: &[[i8; N]],
) -> Result<Vec<BigInt>> {
    candidate
        .terms
        .par_iter()
        .map(|term| -> Result<Vec<BigInt>> {
            let coefficient = parse_bigint(&term.coefficient)?;
            Ok(
                exact_hinge_coefficients(&records[term.sequence], directions)?
                    .into_iter()
                    .map(|value| &coefficient * value)
                    .collect(),
            )
        })
        .try_reduce(
            || vec![BigInt::from(0); directions.len()],
            |mut left, right| -> Result<Vec<BigInt>> {
                for (target, value) in left.iter_mut().zip(right) {
                    *target += value;
                }
                Ok(left)
            },
        )
}

fn parse_bigint(raw: &str) -> Result<BigInt> {
    ensure!(
        raw == "0" || {
            let digits = raw.strip_prefix('-').unwrap_or(raw);
            !digits.is_empty()
                && !digits.starts_with('0')
                && digits.bytes().all(|byte| byte.is_ascii_digit())
        },
        "noncanonical integer: {raw}"
    );
    BigInt::parse_bytes(raw.as_bytes(), 10).context("parse integer")
}

fn direction_digest(values: &[ExactHinge]) -> String {
    let mut digest = Sha256::new();
    for item in values {
        for coordinate in item.direction {
            digest.update([coordinate as u8]);
        }
    }
    format!("{:x}", digest.finalize())
}

fn coefficient_digest(values: &[ExactHinge]) -> String {
    let mut digest = Sha256::new();
    for item in values {
        digest.update(item.coefficient.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
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

fn residual_digest(
    aggregate: &ExactAggregate,
    form_delta: Option<(&ExactNormalForm, &BigInt)>,
    linear_delta: Option<(usize, &BigInt)>,
) -> String {
    let mut digest = Sha256::new();
    digest.update(b"G0164-ALL128-COMPLETE-EXACT-RESIDUAL-V1\0");
    let mut directions = aggregate.hinges.keys().copied().collect::<BTreeSet<_>>();
    if let Some((form, _)) = form_delta {
        directions.extend(form.hinges.keys().copied());
    }
    for direction in directions {
        let mut value = aggregate
            .hinges
            .get(&direction)
            .cloned()
            .unwrap_or_default();
        if let Some((form, multiplier)) = form_delta
            && let Some(delta) = form.hinges.get(&direction)
        {
            value += multiplier * delta;
        }
        if value != BigInt::from(0) {
            digest.update(b"H\t");
            digest.update(direction.map(|value| value as u8));
            digest.update(b"\t");
            digest.update(value.to_string().as_bytes());
            digest.update(b"\n");
        }
    }
    for coordinate in 0..N {
        let mut value = aggregate.linear[coordinate].clone();
        if let Some((form, multiplier)) = form_delta {
            value += multiplier * &form.linear[coordinate];
        }
        if let Some((index, delta)) = linear_delta
            && coordinate == index
        {
            value += delta;
        }
        if value != BigInt::from(0) {
            digest.update(b"L\t");
            digest.update(coordinate.to_le_bytes());
            digest.update(b"\t");
            digest.update(value.to_string().as_bytes());
            digest.update(b"\n");
        }
    }
    format!("{:x}", digest.finalize())
}

fn residual_summary(
    aggregate: &ExactAggregate,
    form_delta: Option<(&ExactNormalForm, &BigInt)>,
    linear_delta: Option<(usize, &BigInt)>,
) -> (Option<ExactHinge>, Option<ExactLinear>) {
    let mut directions = aggregate.hinges.keys().copied().collect::<BTreeSet<_>>();
    if let Some((form, _)) = form_delta {
        directions.extend(form.hinges.keys().copied());
    }
    let first_hinge = directions.into_iter().find_map(|direction| {
        let mut value = aggregate
            .hinges
            .get(&direction)
            .cloned()
            .unwrap_or_default();
        if let Some((form, multiplier)) = form_delta
            && let Some(delta) = form.hinges.get(&direction)
        {
            value += multiplier * delta;
        }
        (value != BigInt::from(0)).then(|| ExactHinge {
            direction,
            coefficient: value.to_string(),
        })
    });
    let first_linear = (0..N).find_map(|coordinate| {
        let mut value = aggregate.linear[coordinate].clone();
        if let Some((form, multiplier)) = form_delta {
            value += multiplier * &form.linear[coordinate];
        }
        if let Some((index, delta)) = linear_delta
            && coordinate == index
        {
            value += delta;
        }
        (value != BigInt::from(0)).then(|| ExactLinear {
            coordinate,
            coefficient: value.to_string(),
        })
    });
    (first_hinge, first_linear)
}

fn mutation_control(
    name: &'static str,
    aggregate: &ExactAggregate,
    form_delta: Option<(&ExactNormalForm, &BigInt)>,
    linear_delta: Option<(usize, &BigInt)>,
) -> Result<MutationControl> {
    let baseline = residual_digest(aggregate, None, None);
    let mutated = residual_digest(aggregate, form_delta, linear_delta);
    let (hinge, linear) = residual_summary(aggregate, form_delta, linear_delta);
    let detected = baseline != mutated;
    ensure!(detected, "hostile mutation escaped: {name}");
    Ok(MutationControl {
        name,
        first_nonzero_hinge: hinge,
        first_nonzero_linear: linear,
        baseline_sha256: baseline,
        mutated_sha256: mutated,
        detected,
    })
}

fn residual_prefix(aggregate: &ExactAggregate, accumulated: &[[i8; N]]) -> Result<Vec<ExactHinge>> {
    let excluded = accumulated.iter().copied().collect::<HashSet<_>>();
    let output = aggregate
        .hinges
        .iter()
        .collect::<BTreeMap<_, _>>()
        .into_iter()
        .filter(|(direction, value)| **value != BigInt::from(0) && !excluded.contains(*direction))
        .take(RESIDUAL_PREFIX_K)
        .map(|(direction, value)| ExactHinge {
            direction: *direction,
            coefficient: value.to_string(),
        })
        .collect::<Vec<_>>();
    ensure!(
        output
            .windows(2)
            .all(|pair| pair[0].direction < pair[1].direction),
        "residual prefix ordering drift"
    );
    for item in &output {
        validate_direction(&item.direction)?;
        ensure!(item.coefficient != "0", "zero residual prefix item");
    }
    Ok(output)
}

fn source_label(index: usize) -> (&'static str, usize) {
    if index < 68 {
        ("G0128_ACCUMULATED_68", index)
    } else if index < INHERITED_DIRECTIONS {
        ("G0135_STAGE_A_BATCH32", index - 68)
    } else {
        ("G0140_POOL128", index - INHERITED_DIRECTIONS)
    }
}

fn classify_global_result(aggregate: &ExactAggregate) -> (&'static str, bool) {
    let global_zero = aggregate
        .hinges
        .values()
        .all(|value| *value == BigInt::from(0))
        && aggregate
            .linear
            .iter()
            .all(|value| *value == BigInt::from(0));
    (
        if global_zero {
            ZERO_RESULT
        } else {
            RESIDUAL_RESULT
        },
        global_zero,
    )
}

fn self_test() -> Result<()> {
    candidate::self_test()?;
    ensure!(
        expected_labelled_permutations(2)? == 2 * factorial(N),
        "dynamic census self-test failed"
    );
    let zero = ExactAggregate::default();
    let mut linear_only = ExactAggregate::default();
    linear_only.linear[0] = BigInt::from(1);
    let mut aggregate = ExactAggregate::default();
    let direction = [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4];
    aggregate.hinges.insert(direction, BigInt::from(7));
    ensure!(
        classify_global_result(&zero) == (ZERO_RESULT, true)
            && classify_global_result(&linear_only) == (RESIDUAL_RESULT, false)
            && classify_global_result(&aggregate) == (RESIDUAL_RESULT, false)
            && residual_prefix(&linear_only, &[])?.is_empty(),
        "zero/linear-only/hinge-only branch fixture drift"
    );
    let cancellation = BigInt::from(-1);
    let cancelled = mutation_control(
        "self-test-linear-cancellation",
        &linear_only,
        None,
        Some((0, &cancellation)),
    )?;
    ensure!(
        cancelled.detected
            && cancelled.first_nonzero_hinge.is_none()
            && cancelled.first_nonzero_linear.is_none(),
        "exact cancellation mutation was not detected"
    );
    let prefix = residual_prefix(&aggregate, &[])?;
    ensure!(
        prefix.len() == 1 && prefix[0].direction == direction,
        "short residual prefix was rejected"
    );
    let delta = BigInt::from(1);
    mutation_control(
        "self-test-linear-delta",
        &aggregate,
        None,
        Some((0, &delta)),
    )?;
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
    println!(
        "G-0164 global replay outcome-blind static preflight PASS; future manifest/member/output bytes not inspected"
    );
    Ok(())
}

fn full_preflight(manifest_path: &Path, member_path: &Path) -> Result<()> {
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    ensure!(
        manifest_path == Path::new(GLOBAL_MANIFEST_PATH)
            && member_path == Path::new(FINITE_MEMBER_PATH),
        "preflight path drift"
    );
    self_test()?;
    ensure!(
        !root.join(GLOBAL_OUTPUT_PATH).exists(),
        "scientific output exists"
    );
    validate_compiled_bytes(&root)?;
    let inputs = load_and_validate(&root)?;
    let (manifest, audit, _) = validate_global_manifest(&root, &inputs)?;
    let executable = validate_current_executable(&root)?;
    println!(
        "G-0164 global replay preflight PASS: {} basis coordinates, {} nonzero terms, {} accumulated directions; manifest {}; audit {}; executable {}; no output written",
        inputs.candidate.basis_sequences.len(),
        inputs.candidate.terms.len(),
        inputs.accumulated_directions.len(),
        manifest.sha256,
        audit.sha256,
        executable.sha256,
    );
    Ok(())
}

fn run(manifest_path: &Path, member_path: &Path, output_path: &Path) -> Result<()> {
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    ensure!(
        manifest_path == Path::new(GLOBAL_MANIFEST_PATH)
            && member_path == Path::new(FINITE_MEMBER_PATH)
            && output_path == Path::new(GLOBAL_OUTPUT_PATH),
        "scientific invocation path drift"
    );
    let resolved_output_path = root.join(GLOBAL_OUTPUT_PATH);
    ensure!(
        !resolved_output_path.exists(),
        "refusing to overwrite output"
    );
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(THREADS)
        .build_global()
        .context("build fixed G-0164 thread pool")?;
    let started = Instant::now();
    validate_compiled_bytes(&root)?;
    let inputs = load_and_validate(&root)?;
    let (global_manifest, source_audit, mut custody) = validate_global_manifest(&root, &inputs)?;
    let executable = validate_current_executable(&root)?;
    custody.insert(executable.path.clone(), executable.clone());
    ensure!(
        inputs.records.len() == RECORDS
            && inputs.accumulated_directions.len() == ACCUMULATED_DIRECTIONS,
        "validated input census drift"
    );

    let mut aggregate = inputs
        .candidate
        .terms
        .par_iter()
        .map(|term| -> Result<ExactAggregate> {
            let record = &inputs.records[term.sequence];
            let form = validated_full_normal_form(record)?;
            let mut aggregate = ExactAggregate::default();
            add_exact(
                &mut aggregate,
                record,
                form,
                &parse_bigint(&term.coefficient)?,
            )?;
            Ok(aggregate)
        })
        .try_reduce(ExactAggregate::default, |left, right| {
            Ok(merge_exact(left, right))
        })?;
    aggregate
        .term_receipts
        .sort_by_key(|receipt| receipt.sequence);
    ensure!(
        aggregate.terms == inputs.candidate.terms.len()
            && aggregate
                .term_receipts
                .iter()
                .map(|receipt| receipt.sequence)
                .eq(inputs.candidate.terms.iter().map(|term| term.sequence)),
        "term order/census drift"
    );
    validate_term_receipts(&aggregate.term_receipts, inputs.candidate.terms.len())?;
    let labelled_expected = expected_labelled_permutations(inputs.candidate.terms.len())?;
    ensure!(
        aggregate.labelled_permutations_checked == labelled_expected,
        "global labelled census drift"
    );
    let target_subtraction =
        parse_bigint(&inputs.candidate.target_scale)? * BigInt::from(factorial(N));
    aggregate.linear[N - 1] -= &target_subtraction;

    let direct = direct_accumulated_prices(
        &inputs.records,
        &inputs.candidate,
        &inputs.accumulated_directions,
    )?;
    let accumulated_direction_checks = inputs
        .accumulated_directions
        .iter()
        .enumerate()
        .map(|(index, direction)| {
            let aggregate_value = aggregate.hinges.get(direction).cloned().unwrap_or_default();
            let (source, source_index) = source_label(index);
            AccumulatedDirectionCheck {
                index,
                source,
                source_index,
                direction: *direction,
                aggregate_coefficient: aggregate_value.to_string(),
                direct_dp_coefficient: direct[index].to_string(),
                routes_agree: aggregate_value == direct[index],
                exact_zero: aggregate_value == BigInt::from(0) && direct[index] == BigInt::from(0),
            }
        })
        .collect::<Vec<_>>();
    ensure!(
        accumulated_direction_checks
            .iter()
            .all(|check| check.routes_agree && check.exact_zero),
        "global/direct accumulated-row replay failed"
    );
    let all_linear_zero = aggregate
        .linear
        .iter()
        .all(|value| *value == BigInt::from(0));
    let nonzero_hinge_directions = aggregate
        .hinges
        .values()
        .filter(|value| **value != BigInt::from(0))
        .count();
    let (result, global_zero) = classify_global_result(&aggregate);
    let (first_nonzero_hinge, first_nonzero_linear) = residual_summary(&aggregate, None, None);
    ensure!(
        global_zero == (first_nonzero_hinge.is_none() && first_nonzero_linear.is_none()),
        "branch/residual summary drift"
    );
    let prefix = residual_prefix(&aggregate, &inputs.accumulated_directions)?;
    let expected_prefix_count = nonzero_hinge_directions.min(RESIDUAL_PREFIX_K);
    ensure!(
        prefix.len() == expected_prefix_count,
        "residual prefix is not complete up to K"
    );
    let prefix_direction_digest = direction_digest(&prefix);
    let prefix_coefficient_digest = coefficient_digest(&prefix);

    let first_term = inputs
        .candidate
        .terms
        .first()
        .context("missing first term")?;
    let last_term = inputs
        .candidate
        .terms
        .last()
        .context("missing final term")?;
    let first_form = validated_full_normal_form(&inputs.records[first_term.sequence])?;
    let last_form = validated_full_normal_form(&inputs.records[last_term.sequence])?;
    let one = BigInt::from(1);
    let coefficient_plus_one = mutation_control(
        "first_nonzero_coefficient_plus_one",
        &aggregate,
        Some((&first_form, &one)),
        None,
    )?;
    let minus_factorial = -BigInt::from(factorial(N));
    let target_scale_plus_one = mutation_control(
        "target_scale_plus_one",
        &aggregate,
        None,
        Some((N - 1, &minus_factorial)),
    )?;
    let minus_one = BigInt::from(-1);
    let target_coordinate_plus_one = mutation_control(
        "target_coordinate_10_plus_one",
        &aggregate,
        None,
        Some((N - 1, &minus_one)),
    )?;
    let omitted_final_term = mutation_control(
        "omitted_final_nonzero_term",
        &aggregate,
        Some((&last_form, &-parse_bigint(&last_term.coefficient)?)),
        None,
    )?;
    let omitted_direction = first_form
        .hinges
        .keys()
        .copied()
        .min()
        .context("first term has no hinge")?;
    let mut one_hinge = HashMap::new();
    one_hinge.insert(
        omitted_direction,
        first_form.hinges[&omitted_direction].clone(),
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
    let excluded = inputs
        .accumulated_directions
        .iter()
        .copied()
        .collect::<HashSet<_>>();
    let census_controls = CensusControls {
        dynamic_term_count: inputs.candidate.terms.len(),
        factorial_11: factorial(N),
        expected_labelled_permutations: labelled_expected,
        observed_labelled_permutations: aggregate.labelled_permutations_checked,
        all_term_receipts_reconciled: true,
        expected_accumulated_directions: ACCUMULATED_DIRECTIONS,
        observed_accumulated_directions: inputs.accumulated_directions.len(),
    };
    let prefix_controls = PrefixControls {
        maximum_k: RESIDUAL_PREFIX_K,
        expected_count: expected_prefix_count,
        observed_count: prefix.len(),
        strict_signed_lexicographic_order: prefix
            .windows(2)
            .all(|pair| pair[0].direction < pair[1].direction),
        excludes_accumulated_directions: prefix
            .iter()
            .all(|item| !excluded.contains(&item.direction)),
    };
    ensure!(
        census_controls.expected_labelled_permutations
            == census_controls.observed_labelled_permutations
            && census_controls.expected_accumulated_directions
                == census_controls.observed_accumulated_directions
            && prefix_controls.expected_count == prefix_controls.observed_count
            && prefix_controls.strict_signed_lexicographic_order
            && prefix_controls.excludes_accumulated_directions,
        "census/prefix control drift"
    );

    let all_hinge_digest = hinge_digest(&aggregate.hinges, false);
    let nonzero_hinge_digest = hinge_digest(&aggregate.hinges, true);
    let complete_residual_digest = residual_digest(&aggregate, None, None);
    let transcript_digest = sha256_bytes(&serde_json::to_vec(&aggregate.term_receipts)?);
    let output = Output {
        schema: OUTPUT_SCHEMA,
        result,
        claim_boundary: CLAIM_BOUNDARY,
        global_manifest: global_manifest.clone(),
        finite_manifest: inputs.finite_manifest_binding.clone(),
        finite_member: inputs.candidate_binding.clone(),
        preregistration: binding_for_path(&root, PREREGISTRATION_PATH)?,
        producer_source: binding_for_path(&root, SOURCE_PATH)?,
        candidate_source: binding_for_path(&root, CANDIDATE_SOURCE_PATH)?,
        producer_engine: binding_for_path(&root, ENGINE_PATH)?,
        producer_cargo_manifest: binding_for_path(&root, CARGO_PATH)?,
        producer_cargo_lock: binding_for_path(&root, LOCK_PATH)?,
        g0117_cargo_manifest: binding_for_path(&root, G0117_CARGO_PATH)?,
        g0117_lib_source: binding_for_path(&root, G0117_LIB_PATH)?,
        producer_executable: executable,
        source_audit,
        parent_replay_source: binding_for_path(&root, PARENT_SOURCE_PATH)?,
        parent_replay_engine: binding_for_path(&root, PARENT_ENGINE_PATH)?,
        parent_source_audit: binding_for_path(&root, PARENT_SOURCE_AUDIT_PATH)?,
        source_and_audit_bindings: custody,
        candidate_schema: inputs.candidate.schema.clone(),
        candidate_result: inputs.candidate.result.clone(),
        base_rows: inputs.candidate.base_rows,
        appended_rows: inputs.candidate.appended_rows,
        rows: inputs.candidate.rows,
        records: inputs.candidate.records,
        selected_pool_indices: inputs.candidate.selected_pool_indices.clone(),
        selected_directions: inputs.candidate.selected_directions.clone(),
        selected_directions_i8_sha256: inputs.candidate.selected_directions_i8_sha256.clone(),
        rank: inputs.candidate.rank,
        basis_coordinates: inputs.candidate.basis_sequences.len(),
        support_columns: inputs.candidate.support_columns,
        terms: inputs.candidate.terms.len(),
        target_scale: inputs.candidate.target_scale.clone(),
        target_subtraction_coordinate_10: target_subtraction.to_string(),
        finite_all_rational_rows_replayed: inputs.candidate.all_540_rational_rows_replayed,
        finite_all_integer_rows_replayed: inputs.candidate.all_540_primitive_integer_rows_replayed,
        finite_primitive_denominator_clearing: inputs.candidate.primitive_denominator_clearing,
        finite_coefficient_plus_one_mutant_rejected: inputs
            .candidate
            .coefficient_plus_one_mutant
            .rejected,
        independent_finite_replay: inputs.finite_replay.clone(),
        arithmetic: "signed_num_bigint_BigInt_unconditional_exact",
        decision_rule: DECISION_RULE,
        complete_global_replay: true,
        all_hinge_and_linear_residuals_zero: global_zero,
        labelled_permutations_expected: labelled_expected,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        aggregate_hinge_support: aggregate.hinges.len(),
        nonzero_hinge_directions,
        aggregate_hinge_decimal_lf_sha256: all_hinge_digest,
        nonzero_hinge_decimal_lf_sha256: nonzero_hinge_digest,
        complete_residual_decimal_lf_sha256: complete_residual_digest,
        term_normal_form_transcript_sha256: transcript_digest,
        term_normal_forms: aggregate.term_receipts,
        accumulated_direction_checks,
        inherited_accumulated_directions: INHERITED_DIRECTIONS,
        selected_accumulated_directions: APPENDED_ROWS,
        accumulated_direction_count: ACCUMULATED_DIRECTIONS,
        all_accumulated_directions_exact_zero: true,
        linear_residuals_after_target: aggregate.linear.iter().map(ToString::to_string).collect(),
        all_11_linear_residuals_exact_zero: all_linear_zero,
        first_nonzero_hinge,
        first_nonzero_linear,
        residual_prefix_k: if global_zero { 0 } else { RESIDUAL_PREFIX_K },
        residual_prefix_count: prefix.len(),
        residual_prefix_directions_i8_sha256: prefix_direction_digest,
        residual_prefix_exact_residuals_decimal_lf_sha256: prefix_coefficient_digest,
        residual_prefix: prefix,
        no_automatic_next_study: true,
        coefficient_plus_one,
        target_scale_plus_one,
        target_coordinate_plus_one,
        omitted_final_term,
        omitted_first_term_direction,
        census_controls,
        prefix_controls,
        inputs_rehashed_at_end: true,
        manifest_rehashed_at_end: true,
        candidate_rehashed_at_end: true,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let mut bytes = serde_json::to_vec_pretty(&output)?;
    bytes.push(b'\n');

    rehash_snapshot(&root, &inputs.input_snapshot)?;
    ensure!(
        binding_for_path(&root, GLOBAL_MANIFEST_PATH)? == global_manifest
            && binding_for_path(&root, FINITE_MANIFEST_PATH)? == inputs.finite_manifest_binding
            && binding_for_path(&root, FINITE_MEMBER_PATH)? == inputs.candidate_binding,
        "scientific manifest/member drift during global replay"
    );
    for binding in output.source_and_audit_bindings.values() {
        ensure!(
            binding_for_path(&root, &binding.path)? == *binding,
            "source/audit custody drift during global replay: {}",
            binding.path
        );
    }
    publish_exclusive(&resolved_output_path, &bytes)?;
    println!(
        "{}",
        serde_json::json!({
            "result": output.result,
            "terms": output.terms,
            "labelled_permutations_checked": output.labelled_permutations_checked,
            "nonzero_hinge_directions": output.nonzero_hinge_directions,
            "residual_prefix_count": output.residual_prefix_count,
            "complete_residual_decimal_lf_sha256": output.complete_residual_decimal_lf_sha256,
        })
    );
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    match args.as_slice() {
        [_, mode] if mode == "--self-test" => {
            self_test()?;
            println!("G-0164 global replay self-test PASS");
            Ok(())
        }
        [_, mode] if mode == "--preflight-static" => static_preflight(),
        [_, mode, manifest, member] if mode == "--preflight" => {
            full_preflight(Path::new(manifest), Path::new(member))
        }
        [_, mode, manifest, member, output] if mode == "--run" => {
            run(Path::new(manifest), Path::new(member), Path::new(output))
        }
        _ => anyhow::bail!(
            "usage: g0164-stage-b-global-replay --self-test | --preflight-static | --preflight GLOBAL_MANIFEST FINITE_MEMBER | --run GLOBAL_MANIFEST FINITE_MEMBER OUTPUT"
        ),
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn synthetic_contracts_and_short_residual_prefix() {
        super::self_test().expect("G-0164 global replay self-test");
    }
}
