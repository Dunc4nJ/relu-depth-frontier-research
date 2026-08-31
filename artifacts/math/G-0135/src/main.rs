use anyhow::{Context, Result, bail, ensure};
use g0117_global_coordinate_pricer::{
    FullNormalForm, N, Record, active_direction, full_normal_form, linear_vector,
    validate_direction,
};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap, HashSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Write};
use std::path::{Component, Path, PathBuf};
use std::process::Command;
use std::time::Instant;

const SCREENING_PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];
const RECORDS: usize = 163_740;
const ROWS: usize = 380;
const TERMS: usize = 132;
const SELECTED_SLOTS: usize = 176;
const ZERO_SELECTED_COEFFICIENTS: usize = 44;
const CARRY_DIRECTIONS: usize = 68;
const BATCH_K: usize = 32;
const MAX_TERM_SEQUENCE: usize = 161;
const THREADS: usize = 12;
const EXPECTED_LABELLED_PERMUTATIONS: u64 = 5_269_017_600;
const EXPECTED_HINGE_ENTRIES_PROCESSED: u64 = 4_579_906;
const EXPECTED_AGGREGATE_HINGE_SUPPORT: usize = 163_036;
const EXPECTED_NONZERO_HINGE_DIRECTIONS: usize = 162_929;
const PINNED_HINGE_ABS_BOUND: i64 = 199_584_000;
const PINNED_LINEAR_ABS_BOUND: i64 = 235_872_000;

const PANEL_INPUT_PATH: &str = "artifacts/math/G-0113/panel_solver_input_v1.json";
const CANDIDATE_PATH: &str = "artifacts/math/G-0128/full_family_master_result_v2.json";
const PRIOR_REPLAY_RESULT_PATH: &str =
    "artifacts/math/G-0132/member_global_normal_form_replay_v1.json";
const PRIOR_REPLAY_MANIFEST_PATH: &str =
    "artifacts/math/G-0132/member_global_normal_form_manifest_v1.json";
const MEMBER_RESULT_PATH: &str = "artifacts/math/G-0135/batch32_global_replay_v1.json";
const MEMBER_MANIFEST_PATH: &str = "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json";
const NONMEMBER_RESULT_PATH: &str = "artifacts/math/G-0135/full_degree5_separator_pricing_v1.json";
const SOURCE_AUDIT_RECEIPT_PATH: &str =
    "artifacts/reviews/G-0136-g0135-source/SOURCE_AUDIT_RECEIPT.json";
const SOURCE_AUDIT_REPORT_PATH: &str =
    "artifacts/reviews/G-0136-g0135-source/SOURCE_AUDIT_REPORT.md";
const SOURCE_AUDIT_SELF_TEST_PATH: &str =
    "artifacts/reviews/G-0136-g0135-source/SELF_TEST_RECEIPT.json";
const SOURCE_AUDIT_PROBE_SOURCE_PATH: &str =
    "artifacts/reviews/G-0136-g0135-source/independent_probe.py";
const SOURCE_AUDIT_PROBE_RECEIPT_PATH: &str =
    "artifacts/reviews/G-0136-g0135-source/INDEPENDENT_PROBE_RECEIPT.json";

const CANDIDATE_SHA256: &str = "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838";
const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const KERNEL_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";
const UNIQUENESS_SHA256: &str = "39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17";
const CANDIDATE_MANIFEST_SHA256: &str =
    "79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec";
const CANDIDATE_SOLVER_SHA256: &str =
    "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8";
const CANDIDATE_PREREGISTRATION_SHA256: &str =
    "ed33f3349780c1e73d64b1a9a75e2a070ae554bd1313dc081187a8d2554e5a9f";
const CANDIDATE_SOURCE_AUDIT_SHA256: &str =
    "049a0a85bfec5b3ab053208da825a173dbd16302af72004c47f54a906a2ae4ed";
const MODEL_BOUNDARY_AUDIT_SHA256: &str =
    "53f90bacf3271ffb94174eb1a7e6bc5a525b36d86bb722ef2c595f111043bfdf";
const G0131_PREREGISTRATION_SHA256: &str =
    "74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799";
const G0131_CHECKER_SHA256: &str =
    "41b4b5d0266ea8b3724dd93938013d02829bbf1bf16ba3be2655369014fece7a";
const G0131_RECEIPT_SHA256: &str =
    "0159910b476b1cac9ea0e8f6ad05e16e061036b361efc8b2f5a3a1aa02c09926";
const G0131_REPORT_SHA256: &str =
    "15f3f0f8bd4952d7773effa393a5cecbd0d6f74895ded134efeb5e3701ebb197";
const G0135_PREREGISTRATION_SHA256: &str =
    "ca9ed1930a8b7539d92d7651caadd06c6bd77742ce11adff682af9ac067fe5ec";
const G0135_PREREGISTRATION_COMMIT: &str = "30b285dadc05825b7cd4ecb37b19f9d2299f1afb";
const G0136_PREREGISTRATION_SHA256: &str =
    "ec8004a00549d205827c283a3d0f3665ebb4260ddc2964c9654869afd0fee66d";
const G0134_PREREGISTRATION_SHA256: &str =
    "5f0ec755c8aa96bccde392be97e3189f6eb1fc9dfbff508a5ced13ecd9fca6d2";
const G0134_CHECKER_SHA256: &str =
    "40109063ed2210b3a9ba11d52618d28e55eac9e5da7146d4bb0377b8da6fa9ee";
const G0134_RECEIPT_SHA256: &str =
    "a00aaca7aeb8f960d6fa5a264b72a13c797ae30a75c4eec5eaa90a5a455e2f56";
const G0134_REPORT_SHA256: &str =
    "98f592ccf0e4541fd596aea7691561342c761cb1e168a2fa1f1bec22c260d9f4";
const G0134_RESULT_AUDIT_COMMIT: &str = "47f969c82def124994f9db12b3d18fa34535fb3b";
const AUDITED_ANCESTOR_SHA256: &str =
    "dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac";
const TARGET_SCALE: &str = "2289393005496338240468982655090335335732668690900751540287809289663720291914849699943112917639850352050294840444775090516901570116753181129941246082620";
const SELECTED_U64LE_SHA256: &str =
    "4584a7f87748b976f86734308efa4abb621e4caab5fa973673faf6aa0a913bc7";
const TERM_SUPPORT_U64LE_SHA256: &str =
    "dda733b9e2f52e0abcd95dd7f98809425e1d9743a9339156ac5d54a29491716d";
const COEFFICIENT_DECIMAL_LF_SHA256: &str =
    "2a581d6f48513e2aea9863f9394a5c922c544f8a29f50e25257a024024b96420";
const PRIOR_REPLAY_RESULT_SHA256: &str =
    "d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50";
const PRIOR_REPLAY_MANIFEST_SHA256: &str =
    "b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732";
const EXPECTED_AGGREGATE_HINGE_SHA256: &str =
    "955a80d8d6ecab4afd873249e764595dcb750e7d1b5385044d6f5c2b19b55c5c";
const EXPECTED_NONZERO_HINGE_SHA256: &str =
    "ff51e40c67556bdf813797620e6994ba3d6312f1222c00ed8a44617337ec66c2";
const EXPECTED_TERM_TRANSCRIPT_SHA256: &str =
    "5b4efbbd4cca06252545c89e52503b20ba332cd59eeb477d05d09a5a688a62ba";
const EXPECTED_FIRST_DIRECTION: [i8; N] = [0, 0, 0, 0, 0, 0, 1, -3, -2, 1, 3];
const EXPECTED_FIRST_COEFFICIENT: &str = "363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360";

const CANDIDATE_SCHEMA: &str = "max11-g0128-full-family-master-result-v2";
const CANDIDATE_RESULT: &str = "FULL_FAMILY_380ROW_EXACT_Q_MEMBER";
const CANDIDATE_CLAIM: &str = "Exact membership only on the frozen 380-row system over the frozen 163,740-column family; a finite-row candidate for separate complete global replay, not a family-completeness theorem, global MAX11 identity, lower bound, or Lean theorem.";
const EXACT_DECISION_RULE: &str =
    "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate";
const SOURCE_AUDIT_BOUNDARY: &str = "T1 source clearance for this exact committed producer and executable only; no scientific manifest or output was observed, and no mathematical result is promoted by this receipt.";
const GLOBAL_CLAIM_BOUNDARY: &str = "This exact replay re-confirms the frozen G-0128 132-term candidate's global residual and deterministically selects its first 32 signed-lexicographic nonzero hinge rows. It refutes only that coefficient vector and supplies constraints for a separate exact 412-row solve; it does not prove family nonmembership, completeness, an unrestricted theorem, a lower bound, or a Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../PREREGISTRATION.md");
const COMPILED_CANDIDATE: &[u8] = include_bytes!("../../G-0128/full_family_master_result_v2.json");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../G-0117/src/lib.rs");
const COMPILED_UNIQUENESS: &[u8] = include_bytes!("../../G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md");

const FROZEN_DIRECT_BINDINGS: &[(&str, &str, &str)] = &[
    ("candidate_result", CANDIDATE_PATH, CANDIDATE_SHA256),
    (
        "candidate_manifest",
        "artifacts/math/G-0128/full_family_master_manifest_v2.json",
        CANDIDATE_MANIFEST_SHA256,
    ),
    (
        "candidate_solver",
        "artifacts/math/G-0128/full_family_master_v2.py",
        CANDIDATE_SOLVER_SHA256,
    ),
    (
        "candidate_preregistration",
        "artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md",
        CANDIDATE_PREREGISTRATION_SHA256,
    ),
    (
        "candidate_source_audit",
        "artifacts/reviews/G-0128-round2-master/AUDIT_VERDICT.md",
        CANDIDATE_SOURCE_AUDIT_SHA256,
    ),
    (
        "model_boundary_audit",
        "artifacts/reviews/G-0130-model-boundary/AUDIT_VERDICT.md",
        MODEL_BOUNDARY_AUDIT_SHA256,
    ),
    (
        "finite_audit_preregistration",
        "artifacts/reviews/G-0131-g0128-result/PREREGISTRATION.md",
        G0131_PREREGISTRATION_SHA256,
    ),
    (
        "finite_audit_checker",
        "artifacts/reviews/G-0131-g0128-result/replay_member_cleanroom.py",
        G0131_CHECKER_SHA256,
    ),
    (
        "finite_audit_receipt",
        "artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json",
        G0131_RECEIPT_SHA256,
    ),
    (
        "finite_audit_report",
        "artifacts/reviews/G-0131-g0128-result/REPORT.md",
        G0131_REPORT_SHA256,
    ),
    (
        "g0135_preregistration",
        "artifacts/math/G-0135/PREREGISTRATION.md",
        G0135_PREREGISTRATION_SHA256,
    ),
    (
        "source_audit_preregistration",
        "artifacts/reviews/G-0136-g0135-source/PREREGISTRATION.md",
        G0136_PREREGISTRATION_SHA256,
    ),
    (
        "result_audit_preregistration",
        "artifacts/reviews/G-0134-g0132-result/PREREGISTRATION.md",
        G0134_PREREGISTRATION_SHA256,
    ),
    (
        "prior_global_replay_result",
        PRIOR_REPLAY_RESULT_PATH,
        PRIOR_REPLAY_RESULT_SHA256,
    ),
    (
        "prior_global_replay_manifest",
        PRIOR_REPLAY_MANIFEST_PATH,
        PRIOR_REPLAY_MANIFEST_SHA256,
    ),
    (
        "prior_result_audit_checker",
        "artifacts/reviews/G-0134-g0132-result/cleanroom_residual_reprice.py",
        G0134_CHECKER_SHA256,
    ),
    (
        "prior_result_audit_receipt",
        "artifacts/reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json",
        G0134_RECEIPT_SHA256,
    ),
    (
        "prior_result_audit_report",
        "artifacts/reviews/G-0134-g0132-result/REPORT.md",
        G0134_REPORT_SHA256,
    ),
    (
        "loop_inclusive_schema",
        "artifacts/math/G-0028/LOOP_INCLUSIVE_SIGNED_W_SCHEMA.md",
        "5652b1136a56294ef6fdbba164e66dd489c86a66675901b45e9a2ed5ab0cc40c",
    ),
    (
        "degree5_transfer_readme",
        "artifacts/math/G-0044/README.md",
        "7a7b763dbfba826b2366139176f6b26611c8f1eac0df8f26fd68fa1b928730cb",
    ),
    (
        "denominator_streamer",
        "artifacts/math/G-0038/stream_loop_inclusive_denominator.py",
        "c22c29072f1b046a76c6d3767f7054efa44852fbdb88ae506ba561c5781a1acf",
    ),
    (
        "denominator_manifest",
        "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json",
        "1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640",
    ),
    (
        "denominator_stream",
        "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz",
        "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd",
    ),
    (
        "denominator_independent_census",
        "artifacts/cleanroom/G-0038/independent_loop_inclusive_census.py",
        "16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb",
    ),
    (
        "denominator_independent_census_receipt",
        "artifacts/cleanroom/G-0038/independent_loop_inclusive_census_v1.json",
        "98469e1cdaaaeac411db16439bbc7f2226b9416ee32d9df1e78f214c2cda0078",
    ),
    (
        "denominator_stream_verifier",
        "artifacts/cleanroom/G-0038/verify_loop_inclusive_denominator_stream.py",
        "215e7eb359d01078131e3266487f35658cf922f1285d33dec972f51f9e33d165",
    ),
    (
        "denominator_stream_verification",
        "artifacts/cleanroom/G-0038/loop_inclusive_signed_degree5_stream_verification_v1.json",
        "8379177a8597fcfca9e291fd354289af4950976b32d8238b44caa4a2035cf542",
    ),
];

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

#[derive(Clone, Debug, Deserialize, PartialEq, Eq, Serialize)]
#[serde(deny_unknown_fields)]
struct Term {
    sequence: usize,
    coefficient: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct Trial {
    iteration: usize,
    rank: usize,
    augmented_rank: usize,
    result: String,
    columns_scanned: Option<usize>,
    first_violating_price: Option<String>,
    first_violating_sequence: Option<usize>,
    separator_free_row: Option<usize>,
    separator_target_pairing: Option<String>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Candidate {
    all_380_rows_replayed: bool,
    audited_ancestor_sha256: String,
    augmented_rank: usize,
    claim_boundary: String,
    coefficient_plus_one_mutant_rejected: bool,
    coordinate_rows: Vec<usize>,
    hinge_directions: Vec<[i8; N]>,
    integer_coefficients: Vec<String>,
    manifest_path: String,
    manifest_sha256: String,
    maximum_rss_kib: u64,
    new_exact_residuals_decimal_lf_sha256: String,
    new_selected_prefix_i8_u64_le_sha256: String,
    old_batch_residuals_decimal_lf_sha256: String,
    prior_candidate_rejected_on_all_32_new_rows: bool,
    rank: usize,
    records: usize,
    result: String,
    rows: usize,
    schema: String,
    selected_basis_i128le_sha256: String,
    selected_sequences: Vec<usize>,
    solver_sha256: String,
    support_sequences: Vec<usize>,
    target_scale: String,
    terms: Vec<Term>,
    trials: Vec<Trial>,
    wall_seconds: f64,
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

#[derive(Clone, Debug)]
struct ExactNormalForm {
    linear: [BigInt; N],
    hinges: HashMap<[i8; N], BigInt>,
    labelled_permutations: u64,
    compressed_leaves: u64,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Binding {
    path: String,
    sha256: String,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct CommitBinding {
    path: String,
    sha256: String,
    git_commit: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditSubject {
    source: CommitBinding,
    cargo_manifest: Binding,
    cargo_lock: Binding,
    executable: Binding,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditSelfTest {
    command: String,
    status: String,
    receipt: Binding,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditArtifacts {
    report: Binding,
    self_test_receipt: Binding,
    independent_probe_source: Binding,
    independent_probe_receipt: Binding,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceAuditReceipt {
    schema: String,
    verdict: String,
    subject: SourceAuditSubject,
    frozen_inputs: BTreeMap<String, Binding>,
    self_test: SourceAuditSelfTest,
    independent_probe: SourceAuditSelfTest,
    audit_artifacts: SourceAuditArtifacts,
    scientific_manifest_observed: bool,
    scientific_output_observed: bool,
    promotion_boundary: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
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

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ManifestEnvironment {
    os: String,
    arch: String,
    rustc_verbose: String,
    available_parallelism: usize,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
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
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
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
    bounded_pinned_kernel_crosscheck: bool,
}

#[derive(Serialize)]
struct CarryForwardCheck {
    index: usize,
    direction: [i8; N],
    coefficient: String,
    exact_zero: bool,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
struct ExactLinear {
    coordinate: usize,
    coefficient: String,
}

#[derive(Serialize)]
struct MutationControl {
    name: &'static str,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
    unmutated_residual_decimal_lf_sha256: String,
    mutated_residual_decimal_lf_sha256: String,
    changed_from_unmutated: bool,
    rejected: bool,
}

#[derive(Serialize)]
struct CensusControls {
    per_term_generated_equals_visited_equals_accepted: bool,
    zero_skipped_unclassified_failed: bool,
    omitted_final_term_rejected: bool,
    omitted_last_orbit_contribution_rejected: bool,
    omitted_active_direction_changed_terminal_residual: bool,
    omitted_linear_coordinate_changed_terminal_residual: bool,
    screening_prime_collision_found_exactly: bool,
}

#[derive(Serialize)]
struct SelectionControls {
    exact_batch_count: bool,
    strict_signed_lexicographic_order: bool,
    first_direction_matches_g0132: bool,
    first_coefficient_matches_g0132: bool,
    direction_reordering_changes_digest: bool,
    residual_plus_one_changes_digest: bool,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    manifest_path: &'static str,
    manifest_sha256: String,
    bindings: BTreeMap<String, Binding>,
    candidate_schema: String,
    candidate_result: String,
    target_scale: String,
    target_subtraction_coordinate_10: String,
    arithmetic: &'static str,
    decision_rule: &'static str,
    screening_primes_control_only: [u64; 2],
    complete_global_replay: bool,
    all_hinge_and_linear_residuals_zero: bool,
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_directions: usize,
    aggregate_hinge_decimal_lf_sha256: String,
    nonzero_hinge_decimal_lf_sha256: String,
    term_normal_form_transcript_sha256: String,
    term_normal_forms: Vec<TermNormalFormReceipt>,
    carry_forward_checks: Vec<CarryForwardCheck>,
    first_carry_forward_failure: Option<usize>,
    linear_residuals_after_target: Vec<String>,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
    prior_g0132_reconciled: bool,
    batch_k: usize,
    selected_count: usize,
    selected_directions_i8_sha256: String,
    selected_exact_residuals_decimal_lf_sha256: String,
    selected: Vec<ExactHinge>,
    selection_controls: SelectionControls,
    first_coefficient_plus_one: MutationControl,
    final_coefficient_plus_one: MutationControl,
    target_scale_plus_one: MutationControl,
    target_coordinate_10_plus_one: MutationControl,
    omitted_final_term: MutationControl,
    omitted_first_term_active_direction: MutationControl,
    omitted_first_term_linear_coordinate: MutationControl,
    census_controls: CensusControls,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
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

fn decimal_mod(raw: &str, prime: u64) -> Result<u64> {
    ensure!(canonical_integer(raw), "noncanonical integer");
    let (negative, digits) = raw
        .strip_prefix('-')
        .map_or((false, raw), |remaining| (true, remaining));
    let mut value = 0u64;
    for digit in digits.bytes() {
        value = (value * 10 + u64::from(digit - b'0')) % prime;
    }
    Ok(if negative && value != 0 {
        prime - value
    } else {
        value
    })
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

fn repo_root() -> Result<PathBuf> {
    let crate_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    crate_dir
        .ancestors()
        .nth(3)
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
    let path = checked_repo_path(root, raw)?;
    Ok(Binding {
        path: raw.to_string(),
        sha256: sha256_path(&path)?,
    })
}

fn make_expected_binding(root: &Path, raw: &str, expected: &str) -> Result<Binding> {
    let binding = make_binding(root, raw)?;
    ensure!(binding.sha256 == expected, "binding drift: {raw}");
    Ok(binding)
}

fn relative_executable(root: &Path) -> Result<String> {
    let executable = std::env::current_exe()?.canonicalize()?;
    ensure!(
        executable.starts_with(root),
        "executable must be inside repository"
    );
    let relative = executable.strip_prefix(root)?;
    ensure!(
        relative
            .components()
            .all(|component| matches!(component, Component::Normal(_))),
        "executable path is not canonical"
    );
    Ok(relative.to_string_lossy().into_owned())
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

fn publish_exclusive_with_branch_guard(
    path: &Path,
    bytes: &[u8],
    forbidden_paths: &[&str],
) -> Result<()> {
    ensure!(
        forbidden_paths.iter().all(|raw| !Path::new(raw).exists()),
        "opposite or premature branch output exists before publication"
    );
    publish_exclusive(path, bytes)?;
    if let Some(forbidden) = forbidden_paths.iter().find(|raw| Path::new(**raw).exists()) {
        let parent = path.parent().unwrap_or_else(|| Path::new("."));
        std::fs::remove_file(path).context("rollback publication after branch race")?;
        File::open(parent)
            .and_then(|directory| directory.sync_all())
            .context("sync rollback after branch race")?;
        bail!("opposite or premature branch output raced publication: {forbidden}");
    }
    Ok(())
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
        values.windows(2).all(|pair| pair[0] < pair[1]),
        "{name} is not strictly increasing"
    );
    ensure!(
        values.last().is_some_and(|value| *value < upper),
        "{name} outside range"
    );
    Ok(())
}

fn validate_term_structure(terms: &[Term], records: usize, maximum_sequence: usize) -> Result<()> {
    validate_strict_axis(
        &terms.iter().map(|term| term.sequence).collect::<Vec<_>>(),
        TERMS,
        records,
        "term support",
    )?;
    ensure!(
        terms
            .last()
            .is_some_and(|term| term.sequence == maximum_sequence),
        "final supported sequence drift"
    );
    ensure!(
        terms.iter().all(|term| canonical_integer(&term.coefficient)
            && term.coefficient != "0"
            && term.sequence <= maximum_sequence),
        "candidate coefficient or sequence drift"
    );
    Ok(())
}

fn u64le_digest(values: impl IntoIterator<Item = usize>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((value as u64).to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn decimal_lf_digest(values: impl IntoIterator<Item = String>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn normal_form_digest(
    form: &ExactNormalForm,
    omitted_hinge: Option<[i8; N]>,
    omitted_linear: Option<usize>,
) -> String {
    let mut digest = Sha256::new();
    digest.update(b"G0132-EXACT-NORMAL-FORM-V2\0");
    digest.update(form.labelled_permutations.to_le_bytes());
    digest.update(form.compressed_leaves.to_le_bytes());
    for (coordinate, value) in form.linear.iter().enumerate() {
        if omitted_linear == Some(coordinate) {
            continue;
        }
        digest.update([coordinate as u8]);
        digest.update(value.to_string().as_bytes());
        digest.update(b"\n");
    }
    let ordered = form.hinges.iter().collect::<BTreeMap<_, _>>();
    for (direction, value) in ordered {
        if omitted_hinge.as_ref() == Some(direction) {
            continue;
        }
        for coordinate in direction {
            digest.update([*coordinate as u8]);
        }
        digest.update(value.to_string().as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn gcd_i64(mut first: i64, mut second: i64) -> i64 {
    first = first.abs();
    second = second.abs();
    while second != 0 {
        (first, second) = (second, first % second);
    }
    first
}

fn exact_increments(record: &Record) -> Result<Vec<Vec<i8>>> {
    ensure!(record.signed_mass <= 5, "signed mass exceeds degree");
    ensure!(record.active_vertices <= N, "active support exceeds n");
    ensure!(
        record.negative_edges.len() == record.signed_mass
            && record.positive_edges.len() == record.signed_mass,
        "edge mass mismatch"
    );
    let active = record.active_vertices;
    let mut matrix = vec![vec![0i8; active]; active];
    for (sign, edges) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        for &[u, v] in edges {
            ensure!(u < v && v < active, "record must be compact and loopless");
            matrix[u][v] = matrix[u][v]
                .checked_add(sign)
                .context("increment matrix overflow")?;
            matrix[v][u] = matrix[v][u]
                .checked_add(sign)
                .context("increment matrix overflow")?;
        }
    }
    let mut output = vec![vec![0i8; 1usize << active]; active];
    for vertex in 0..active {
        for mask in 1usize..(1usize << active) {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            output[vertex][mask] = output[vertex][mask ^ bit]
                .checked_add(matrix[vertex][other])
                .context("increment table overflow")?;
        }
    }
    Ok(output)
}

#[allow(clippy::too_many_arguments)]
fn enumerate_exact_words(
    rank: usize,
    active: usize,
    mask: usize,
    inactive_used: usize,
    table: &[Vec<i8>],
    word: &mut [i8; N],
    word_counts: &mut HashMap<[i8; N], u64>,
    compressed_leaves: &mut u64,
) -> Result<()> {
    if rank == N {
        *compressed_leaves = compressed_leaves
            .checked_add(1)
            .context("compressed-leaf census overflow")?;
        let count = word_counts.entry(*word).or_default();
        *count = count.checked_add(1).context("word multiplicity overflow")?;
        return Ok(());
    }
    if inactive_used < N - active {
        word[rank] = 0;
        enumerate_exact_words(
            rank + 1,
            active,
            mask,
            inactive_used + 1,
            table,
            word,
            word_counts,
            compressed_leaves,
        )?;
    }
    for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
        let bit = 1usize << vertex;
        if mask & bit == 0 {
            word[rank] = increments_for_vertex[mask];
            enumerate_exact_words(
                rank + 1,
                active,
                mask | bit,
                inactive_used,
                table,
                word,
                word_counts,
                compressed_leaves,
            )?;
        }
    }
    Ok(())
}

fn exact_full_normal_form(record: &Record) -> Result<ExactNormalForm> {
    let table = exact_increments(record)?;
    let inactive_multiplier = factorial(N - record.active_vertices);
    let mut word_counts = HashMap::<[i8; N], u64>::new();
    let mut compressed_leaves = 0u64;
    enumerate_exact_words(
        0,
        record.active_vertices,
        0,
        0,
        &table,
        &mut [0; N],
        &mut word_counts,
        &mut compressed_leaves,
    )?;
    let labelled_permutations = compressed_leaves
        .checked_mul(inactive_multiplier)
        .context("labelled-permutation census overflow")?;
    ensure!(
        labelled_permutations == factorial(N),
        "full permutation census mismatch"
    );

    let mut linear: [BigInt; N] = std::array::from_fn(|rank| {
        BigInt::from(10u8) * BigInt::from(rank) * BigInt::from(factorial(N - 2))
    });
    let mut hinges = HashMap::<[i8; N], BigInt>::new();
    for (word, compressed_multiplicity) in word_counts {
        let labelled_multiplicity =
            BigInt::from(compressed_multiplicity) * BigInt::from(inactive_multiplier);
        let Some(first) = word.iter().copied().find(|value| *value != 0) else {
            continue;
        };
        if first < 0 {
            for (coordinate, value) in linear.iter_mut().zip(word.iter()) {
                *coordinate += BigInt::from(*value) * &labelled_multiplicity;
            }
        }
        let divisor = word
            .iter()
            .fold(0i64, |current, value| gcd_i64(current, i64::from(*value)));
        ensure!(divisor > 0, "nonzero word has zero gcd");
        let sign = if first > 0 { 1i64 } else { -1i64 };
        let mut direction = [0i8; N];
        for (oriented, value) in direction.iter_mut().zip(word.iter()) {
            *oriented = i8::try_from(sign * i64::from(*value) / divisor)
                .context("primitive direction exceeds i8")?;
        }
        if active_direction(&direction) {
            *hinges.entry(direction).or_default() += BigInt::from(divisor) * &labelled_multiplicity;
        }
    }
    Ok(ExactNormalForm {
        linear,
        hinges,
        labelled_permutations,
        compressed_leaves,
    })
}

fn next_sign(status: usize, increment: i8) -> usize {
    if status != 0 || increment == 0 {
        status
    } else if increment > 0 {
        1
    } else {
        2
    }
}

fn exact_linear_vector(record: &Record) -> Result<[BigInt; N]> {
    let table = exact_increments(record)?;
    let active = record.active_vertices;
    let inactive = N - active;
    let states = 1usize << active;
    let mut current = vec![[0u64; 3]; states];
    current[0][0] = 1;
    let mut correction: [BigInt; N] = std::array::from_fn(|_| BigInt::from(0));
    for (rank, correction_at_rank) in correction.iter_mut().enumerate() {
        let mut next = vec![[0u64; 3]; states];
        for (mask, counts) in current.iter().enumerate() {
            let placed = mask.count_ones() as usize;
            if placed > rank {
                continue;
            }
            let inactive_used = rank - placed;
            for (status, count) in counts.iter().copied().enumerate() {
                if count == 0 {
                    continue;
                }
                if inactive_used < inactive {
                    next[mask][status] = next[mask][status]
                        .checked_add(count)
                        .context("linear DP count overflow")?;
                }
                for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
                    let bit = 1usize << vertex;
                    if mask & bit != 0 {
                        continue;
                    }
                    let increment = increments_for_vertex[mask];
                    let new_mask = mask | bit;
                    let new_status = next_sign(status, increment);
                    next[new_mask][new_status] = next[new_mask][new_status]
                        .checked_add(count)
                        .context("linear DP count overflow")?;
                    if new_status == 2 {
                        let remaining_slots = N - rank - 1;
                        let remaining_active = active - new_mask.count_ones() as usize;
                        let remaining_inactive = remaining_slots - remaining_active;
                        let completions =
                            factorial(remaining_slots) / factorial(remaining_inactive);
                        *correction_at_rank += BigInt::from(count)
                            * BigInt::from(increment)
                            * BigInt::from(completions);
                    }
                }
            }
        }
        current = next;
    }
    let injection_count = current[(1usize << active) - 1]
        .iter()
        .try_fold(0u64, |total, count| total.checked_add(*count))
        .context("linear injection census overflow")?;
    ensure!(
        injection_count
            .checked_mul(factorial(inactive))
            .context("linear labelled census overflow")?
            == factorial(N),
        "linear rank-injection census mismatch"
    );
    let inactive_multiplier = BigInt::from(factorial(inactive));
    Ok(std::array::from_fn(|rank| {
        BigInt::from(10u8) * BigInt::from(rank) * BigInt::from(factorial(N - 2))
            + &correction[rank] * &inactive_multiplier
    }))
}

fn exact_matching_injections(
    table: &[Vec<i8>],
    active: usize,
    direction: &[i8; N],
    scale: i8,
) -> Result<u64> {
    let full = (1usize << active) - 1;
    let inactive = N - active;
    let mut current = vec![0u64; 1usize << active];
    current[0] = 1;
    for (rank, coordinate) in direction.iter().copied().enumerate() {
        let expected = i16::from(scale) * i16::from(coordinate);
        let mut next = vec![0u64; 1usize << active];
        for (mask, count) in current.iter().copied().enumerate() {
            if count == 0 {
                continue;
            }
            let placed = mask.count_ones() as usize;
            if placed > rank {
                continue;
            }
            let inactive_used = rank - placed;
            if expected == 0 && inactive_used < inactive {
                next[mask] = next[mask]
                    .checked_add(count)
                    .context("hinge DP count overflow")?;
            }
            for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
                let bit = 1usize << vertex;
                if mask & bit == 0 && i16::from(increments_for_vertex[mask]) == expected {
                    next[mask | bit] = next[mask | bit]
                        .checked_add(count)
                        .context("hinge DP count overflow")?;
                }
            }
        }
        current = next;
    }
    Ok(current[full])
}

fn exact_hinge_coefficients(record: &Record, directions: &[[i8; N]]) -> Result<Vec<BigInt>> {
    for direction in directions {
        validate_direction(direction)?;
    }
    let table = exact_increments(record)?;
    directions
        .iter()
        .map(|direction| {
            let mut coefficient = BigInt::from(0);
            for scale in -5i8..=5 {
                if scale == 0 {
                    continue;
                }
                coefficient += BigInt::from(scale.unsigned_abs())
                    * BigInt::from(exact_matching_injections(
                        &table,
                        record.active_vertices,
                        direction,
                        scale,
                    )?);
            }
            Ok(coefficient * BigInt::from(factorial(N - record.active_vertices)))
        })
        .collect()
}

fn exact_matches_pinned(record: &Record, exact: &ExactNormalForm) -> Result<()> {
    let pinned: FullNormalForm = full_normal_form(record)?;
    let pinned_linear = linear_vector(record)?;
    ensure!(
        pinned
            .hinges
            .values()
            .all(|value| value.unsigned_abs() <= PINNED_HINGE_ABS_BOUND as u64)
            && pinned
                .linear
                .iter()
                .all(|value| value.unsigned_abs() <= PINNED_LINEAR_ABS_BOUND as u64)
            && pinned_linear
                .iter()
                .all(|value| value.unsigned_abs() <= PINNED_LINEAR_ABS_BOUND as u64),
        "pinned diagnostic kernel exceeded its proved frozen-domain bound"
    );
    ensure!(
        pinned.labelled_permutations == exact.labelled_permutations,
        "pinned/exact permutation census disagreement"
    );
    ensure!(
        pinned
            .linear
            .iter()
            .zip(exact.linear.iter())
            .all(|(pinned_value, exact_value)| BigInt::from(*pinned_value) == *exact_value),
        "pinned/exact linear disagreement"
    );
    ensure!(
        pinned_linear
            .iter()
            .zip(exact.linear.iter())
            .all(|(pinned_value, exact_value)| BigInt::from(*pinned_value) == *exact_value),
        "pinned-direct/exact linear disagreement"
    );
    let pinned_hinges = pinned
        .hinges
        .into_iter()
        .map(|(direction, value)| (direction, BigInt::from(value)))
        .collect::<HashMap<_, _>>();
    ensure!(
        pinned_hinges == exact.hinges,
        "pinned/exact hinge disagreement"
    );
    Ok(())
}

fn validated_full_normal_form(record: &Record) -> Result<ExactNormalForm> {
    let form = exact_full_normal_form(record)?;
    ensure!(
        form.labelled_permutations == factorial(N),
        "term permutation census drift"
    );
    ensure!(
        form.linear == exact_linear_vector(record)?,
        "independent exact linear route disagreement"
    );
    for direction in form.hinges.keys() {
        validate_direction(direction)?;
    }
    exact_matches_pinned(record, &form)?;
    Ok(form)
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
        bounded_pinned_kernel_crosscheck: true,
    })
}

fn validate_term_receipts(receipts: &[TermNormalFormReceipt]) -> Result<()> {
    ensure!(receipts.len() == TERMS, "term receipt census drift");
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
                && receipt.bounded_pinned_kernel_crosscheck
                && receipt.normal_form_sha256.len() == 64
                && receipt
                    .normal_form_sha256
                    .bytes()
                    .all(|byte| byte.is_ascii_hexdigit()),
            "term receipt reconciliation failed at sequence {}",
            receipt.sequence
        );
        total = total
            .checked_add(receipt.visited_labelled_permutations)
            .context("term receipt total overflow")?;
    }
    ensure!(
        total == EXPECTED_LABELLED_PERMUTATIONS,
        "global labelled-permutation receipt drift"
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
    aggregate.labelled_permutations_checked += form.labelled_permutations;
    aggregate.hinge_entries_processed += form.hinges.len() as u64;
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

fn direct_carry_prices(input: &PanelInput, candidate: &Candidate) -> Result<Vec<BigInt>> {
    candidate
        .terms
        .par_iter()
        .map(|term| -> Result<Vec<BigInt>> {
            let coefficient = parse_bigint(&term.coefficient)?;
            let prices = exact_hinge_coefficients(
                &input.records[term.sequence],
                &candidate.hinge_directions,
            )?;
            ensure!(
                prices.len() == CARRY_DIRECTIONS,
                "direct carry-price width drift"
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
                    "carry reduction width drift"
                );
                for (total, contribution) in left.iter_mut().zip(right) {
                    *total += contribution;
                }
                Ok(left)
            },
        )
}

fn hinge_digest(hinges: &HashMap<[i8; N], BigInt>, nonzero_only: bool) -> String {
    let mut digest = Sha256::new();
    let ordered = hinges.iter().collect::<BTreeMap<_, _>>();
    for (direction, coefficient) in ordered {
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
    let mut digest = Sha256::new();
    for item in selected {
        digest.update(item.coefficient.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn select_residual_batch(
    aggregate: &ExactAggregate,
    carried_directions: &[[i8; N]],
) -> Result<Vec<ExactHinge>> {
    ensure!(
        aggregate
            .linear
            .iter()
            .all(|value| *value == BigInt::from(0)),
        "nonzero linear residual invalidates Batch32 protocol"
    );
    let carried = carried_directions.iter().copied().collect::<HashSet<_>>();
    let selected = aggregate
        .hinges
        .iter()
        .collect::<BTreeMap<_, _>>()
        .into_iter()
        .filter(|(_, coefficient)| **coefficient != BigInt::from(0))
        .take(BATCH_K)
        .map(|(direction, coefficient)| ExactHinge {
            direction: *direction,
            coefficient: coefficient.to_string(),
        })
        .collect::<Vec<_>>();
    ensure!(
        selected.len() == BATCH_K,
        "fewer than 32 eligible residual rows"
    );
    ensure!(
        selected
            .windows(2)
            .all(|window| window[0].direction < window[1].direction),
        "selected residual order is not strict signed lexicographic"
    );
    for item in &selected {
        validate_direction(&item.direction)?;
        ensure!(
            !carried.contains(&item.direction),
            "nonzero selected residual duplicates an accumulated row"
        );
        ensure!(
            canonical_integer(&item.coefficient) && item.coefficient != "0",
            "selected residual coefficient is not canonical nonzero decimal"
        );
    }
    Ok(selected)
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
    digest.update(b"G0132-COMPLETE-EXACT-RESIDUAL-V1\0");
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
    let unmutated_residual_decimal_lf_sha256 = residual_digest(aggregate, None, None);
    let mutated_residual_decimal_lf_sha256 = residual_digest(aggregate, form_delta, linear_delta);
    let changed_from_unmutated =
        mutated_residual_decimal_lf_sha256 != unmutated_residual_decimal_lf_sha256;
    let (first_nonzero_hinge, first_nonzero_linear) =
        residual_summary(aggregate, form_delta, linear_delta);
    let rejected = first_nonzero_hinge.is_some() || first_nonzero_linear.is_some();
    ensure!(
        rejected && changed_from_unmutated,
        "hostile mutation survived or was observationally inert: {name}"
    );
    Ok(MutationControl {
        name,
        first_nonzero_hinge,
        first_nonzero_linear,
        unmutated_residual_decimal_lf_sha256,
        mutated_residual_decimal_lf_sha256,
        changed_from_unmutated,
        rejected,
    })
}

fn json_string<'a>(value: &'a Value, pointer: &str) -> Result<&'a str> {
    value
        .pointer(pointer)
        .and_then(Value::as_str)
        .with_context(|| format!("missing string at {pointer}"))
}

fn json_u64(value: &Value, pointer: &str) -> Result<u64> {
    value
        .pointer(pointer)
        .and_then(Value::as_u64)
        .with_context(|| format!("missing integer at {pointer}"))
}

fn json_bool(value: &Value, pointer: &str) -> Result<bool> {
    value
        .pointer(pointer)
        .and_then(Value::as_bool)
        .with_context(|| format!("missing boolean at {pointer}"))
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
        "record-order drift"
    );
    Ok(())
}

fn validate_planted_known_answer(input: &PanelInput) -> Result<()> {
    let direction = [0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1];
    validate_direction(&direction)?;
    let records = [&input.records[0], &input.records[1]];
    let direct = records
        .iter()
        .map(|record| {
            exact_hinge_coefficients(record, &[direction]).map(|values| values[0].clone())
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        BigInt::from(7) * &direct[0] - BigInt::from(6) * &direct[1] == BigInt::from(662_784)
            && BigInt::from(8) * &direct[0] - BigInt::from(6) * &direct[1] == BigInt::from(786_432),
        "planted direct-coordinate control drift"
    );

    let mut planted = ExactAggregate::default();
    add_exact(
        &mut planted,
        records[0],
        validated_full_normal_form(records[0])?,
        &BigInt::from(7),
    )?;
    add_exact(
        &mut planted,
        records[1],
        validated_full_normal_form(records[1])?,
        &BigInt::from(-6),
    )?;
    planted.linear[N - 1] -= BigInt::from(14u8) * BigInt::from(factorial(N));
    let (first_hinge, _) = residual_summary(&planted, None, None);
    let first_hinge = first_hinge.context("planted full normal form unexpectedly zero")?;
    ensure!(
        first_hinge.direction == direction && first_hinge.coefficient == "662784",
        "planted full-normal-form route drift"
    );

    let mut mutant = ExactAggregate::default();
    add_exact(
        &mut mutant,
        records[0],
        validated_full_normal_form(records[0])?,
        &BigInt::from(8),
    )?;
    add_exact(
        &mut mutant,
        records[1],
        validated_full_normal_form(records[1])?,
        &BigInt::from(-6),
    )?;
    mutant.linear[N - 1] -= BigInt::from(14u8) * BigInt::from(factorial(N));
    let (mutant_hinge, _) = residual_summary(&mutant, None, None);
    let mutant_hinge = mutant_hinge.context("planted coefficient mutant unexpectedly zero")?;
    ensure!(
        mutant_hinge.direction == direction && mutant_hinge.coefficient == "786432",
        "planted coefficient mutant route drift"
    );
    Ok(())
}

fn validate_candidate(candidate: &Candidate) -> Result<()> {
    ensure!(
        candidate.schema == CANDIDATE_SCHEMA
            && candidate.result == CANDIDATE_RESULT
            && candidate.claim_boundary == CANDIDATE_CLAIM
            && candidate.rows == ROWS
            && candidate.records == RECORDS
            && candidate.rank == SELECTED_SLOTS
            && candidate.augmented_rank == SELECTED_SLOTS,
        "candidate identity drift"
    );
    ensure!(
        candidate.manifest_path == "artifacts/math/G-0128/full_family_master_manifest_v2.json"
            && candidate.manifest_sha256 == CANDIDATE_MANIFEST_SHA256
            && candidate.solver_sha256 == CANDIDATE_SOLVER_SHA256
            && candidate.audited_ancestor_sha256 == AUDITED_ANCESTOR_SHA256,
        "candidate provenance drift"
    );
    ensure!(
        candidate.target_scale == TARGET_SCALE
            && canonical_positive_integer(&candidate.target_scale),
        "target scale drift"
    );
    ensure!(
        candidate.all_380_rows_replayed
            && candidate.coefficient_plus_one_mutant_rejected
            && candidate.prior_candidate_rejected_on_all_32_new_rows,
        "candidate exact-row controls not green"
    );
    ensure!(
        candidate.maximum_rss_kib > 0 && candidate.wall_seconds > 0.0,
        "resource receipt drift"
    );
    for digest in [
        &candidate.new_exact_residuals_decimal_lf_sha256,
        &candidate.new_selected_prefix_i8_u64_le_sha256,
        &candidate.old_batch_residuals_decimal_lf_sha256,
        &candidate.selected_basis_i128le_sha256,
    ] {
        ensure!(
            digest.len() == 64 && digest.bytes().all(|byte| byte.is_ascii_hexdigit()),
            "candidate digest drift"
        );
    }

    validate_strict_axis(
        &candidate.selected_sequences,
        SELECTED_SLOTS,
        RECORDS,
        "selected sequence axis",
    )?;
    ensure!(
        candidate.support_sequences == candidate.selected_sequences,
        "selected/support axis drift"
    );
    ensure!(
        candidate.integer_coefficients.len() == SELECTED_SLOTS
            && candidate
                .integer_coefficients
                .iter()
                .filter(|value| value.as_str() == "0")
                .count()
                == ZERO_SELECTED_COEFFICIENTS,
        "coefficient-slot census drift"
    );
    ensure!(
        candidate.terms
            == nonzero_term_projection(
                &candidate.selected_sequences,
                &candidate.integer_coefficients,
            )?,
        "candidate nonzero term projection drift"
    );
    validate_term_structure(&candidate.terms, RECORDS, MAX_TERM_SEQUENCE)?;
    ensure!(
        u64le_digest(candidate.selected_sequences.iter().copied()) == SELECTED_U64LE_SHA256
            && u64le_digest(candidate.terms.iter().map(|term| term.sequence))
                == TERM_SUPPORT_U64LE_SHA256
            && decimal_lf_digest(candidate.integer_coefficients.iter().cloned())
                == COEFFICIENT_DECIMAL_LF_SHA256,
        "candidate canonical digest drift"
    );
    let primitive_gcd = candidate.integer_coefficients.iter().try_fold(
        parse_bigint(&candidate.target_scale)?,
        |gcd, coefficient| Ok::<_, anyhow::Error>(bigint_gcd(gcd, parse_bigint(coefficient)?)),
    )?;
    ensure!(
        primitive_gcd == BigInt::from(1),
        "certificate is not primitive"
    );

    validate_strict_axis(
        &candidate.coordinate_rows,
        SELECTED_SLOTS,
        ROWS,
        "coordinate row axis",
    )?;
    ensure!(
        candidate.hinge_directions.len() == CARRY_DIRECTIONS,
        "carry-direction census drift"
    );
    let mut directions = HashSet::new();
    for direction in &candidate.hinge_directions {
        validate_direction(direction)?;
        ensure!(directions.insert(*direction), "duplicate carry direction");
    }

    ensure!(candidate.trials.len() == 21, "rank-trial census drift");
    for (iteration, trial) in candidate.trials.iter().enumerate() {
        ensure!(trial.iteration == iteration, "rank-trial order drift");
        if iteration < 20 {
            ensure!(
                trial.rank == 156 + iteration
                    && trial.augmented_rank == 157 + iteration
                    && trial.result == "SEPARATOR_VIOLATED"
                    && trial.columns_scanned == Some(143 + iteration)
                    && trial.first_violating_sequence == Some(142 + iteration)
                    && trial.separator_free_row.is_some()
                    && trial
                        .first_violating_price
                        .as_deref()
                        .is_some_and(|value| canonical_integer(value) && value != "0")
                    && trial
                        .separator_target_pairing
                        .as_deref()
                        .is_some_and(|value| canonical_integer(value) && value != "0"),
                "nonterminal rank-trial drift"
            );
        } else {
            ensure!(
                trial.rank == 176
                    && trial.augmented_rank == 176
                    && trial.result == "EXACT_Q_MEMBER"
                    && trial.columns_scanned.is_none()
                    && trial.first_violating_sequence.is_none()
                    && trial.first_violating_price.is_none()
                    && trial.separator_free_row.is_none()
                    && trial.separator_target_pairing.is_none(),
                "terminal rank-trial drift"
            );
        }
    }
    Ok(())
}

fn validate_finite_audit(root: &Path, candidate: &Candidate) -> Result<()> {
    let path = checked_repo_path(
        root,
        "artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json",
    )?;
    ensure!(
        sha256_path(&path)? == G0131_RECEIPT_SHA256,
        "finite audit drift"
    );
    let receipt: Value = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    ensure!(
        json_string(&receipt, "/schema")? == "max11-g0131-cleanroom-380row-member-audit-v1"
            && json_string(&receipt, "/verdict")? == "CONSISTENT_MEMBER"
            && json_string(&receipt, "/mathematical_certificate_verdict")? == "CONSISTENT",
        "finite audit verdict drift"
    );
    for (pointer, expected) in [
        ("/dimensions/rows", ROWS as u64),
        ("/dimensions/family_records", RECORDS as u64),
        ("/dimensions/selected_columns", SELECTED_SLOTS as u64),
        ("/dimensions/nonzero_terms", TERMS as u64),
        (
            "/dimensions/zero_selected_coefficients",
            ZERO_SELECTED_COEFFICIENTS as u64,
        ),
        ("/dimensions/rank_trials", 21),
        (
            "/selected_basis/coordinate_square_rank",
            SELECTED_SLOTS as u64,
        ),
    ] {
        ensure!(
            json_u64(&receipt, pointer)? == expected,
            "finite audit dimension drift"
        );
    }
    ensure!(
        json_bool(&receipt, "/identity/all_380_rows_zero")?
            && json_bool(&receipt, "/identity/coordinate_square_solve_zero")?
            && json_bool(&receipt, "/mutant/rejected")?
            && json_bool(&receipt, "/selected_basis/matches_reported")?
            && json_bool(&receipt, "/normalization/target_scale_positive")?
            && json_u64(&receipt, "/normalization/coefficient_and_scale_gcd")? == 1
            && json_string(&receipt, "/normalization/target_scale")? == candidate.target_scale
            && json_string(
                &receipt,
                "/selected_basis/full_380_by_176_row_major_i128le_sha256",
            )? == candidate.selected_basis_i128le_sha256,
        "finite audit certificate drift"
    );
    let trials = receipt
        .pointer("/rank_trials")
        .and_then(Value::as_array)
        .context("finite audit rank trials missing")?;
    ensure!(trials.len() == 21, "finite audit rank-trial census drift");
    ensure!(
        trials
            .last()
            .and_then(|value| value.get("rank"))
            .and_then(Value::as_u64)
            == Some(176)
            && trials
                .last()
                .and_then(|value| value.get("augmented_rank"))
                .and_then(Value::as_u64)
                == Some(176),
        "finite audit terminal rank drift"
    );
    Ok(())
}

fn validate_prior_result_audit(root: &Path) -> Result<()> {
    let relative_path = "artifacts/reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json";
    let path = checked_repo_path(root, relative_path)?;
    ensure!(
        sha256_path(&path)? == G0134_RECEIPT_SHA256
            && git_commit_for_path(root, relative_path)? == G0134_RESULT_AUDIT_COMMIT,
        "G-0134 result-audit custody drift"
    );
    let receipt: Value = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    ensure!(
        json_string(&receipt, "/schema")? == "max11-g0134-cleanroom-residual-reprice-v1"
            && json_string(&receipt, "/verdict")? == "CONSISTENT_RESIDUAL"
            && json_string(&receipt, "/mode")? == "full"
            && json_u64(&receipt, "/terms")? == TERMS as u64
            && json_u64(&receipt, "/labelled_permutations_reconciled")?
                == EXPECTED_LABELLED_PERMUTATIONS
            && json_u64(&receipt, "/earlier_degree_five_directions_checked")? == 336
            && json_bool(&receipt, "/exact_match")?
            && json_bool(&receipt, "/nonzero")?
            && json_string(&receipt, "/lexicographic_first")? == "VERIFIED"
            && json_string(&receipt, "/independent_coefficient")? == EXPECTED_FIRST_COEFFICIENT
            && json_string(&receipt, "/reported_coefficient")? == EXPECTED_FIRST_COEFFICIENT
            && json_string(&receipt, "/hinge_target_contribution")? == "0"
            && json_string(&receipt, "/target_scale")? == TARGET_SCALE,
        "G-0134 result-audit verdict or exact scalar drift"
    );
    let direction = receipt
        .pointer("/direction")
        .and_then(Value::as_array)
        .context("G-0134 audited direction missing")?
        .iter()
        .map(|value| {
            value
                .as_i64()
                .context("G-0134 direction coordinate invalid")
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        direction
            == EXPECTED_FIRST_DIRECTION
                .iter()
                .map(|coordinate| i64::from(*coordinate))
                .collect::<Vec<_>>(),
        "G-0134 audited direction drift"
    );
    let carried = receipt
        .pointer("/carry_forward_checks")
        .and_then(Value::as_array)
        .context("G-0134 carry checks missing")?;
    let linears = receipt
        .pointer("/linear_residuals_after_target")
        .and_then(Value::as_array)
        .context("G-0134 linear checks missing")?;
    ensure!(
        carried.len() == CARRY_DIRECTIONS
            && carried
                .iter()
                .all(|entry| { entry.get("coefficient").and_then(Value::as_str) == Some("0") })
            && linears.len() == N
            && linears.iter().all(|value| value.as_str() == Some("0"))
            && receipt.pointer("/hashes_at_start") == receipt.pointer("/hashes_at_end")
            && json_bool(&receipt, "/custody/at_end_identical")?
            && json_bool(
                &receipt,
                "/controls/record_omission_or_reorder_rejected_by_full_sequence_census",
            )?
            && json_bool(&receipt, "/controls/reported_coefficient_plus_one_rejected")?
            && json_bool(&receipt, "/controls/negative_direction_rejected")?
            && json_bool(&receipt, "/controls/nonprimitive_direction_rejected")?,
        "G-0134 result-audit carry, linear, custody, or mutant drift"
    );
    Ok(())
}

fn load_transitive_inputs(root: &Path) -> Result<Vec<Binding>> {
    let manifest_path = checked_repo_path(
        root,
        "artifacts/math/G-0128/full_family_master_manifest_v2.json",
    )?;
    ensure!(
        sha256_path(&manifest_path)? == CANDIDATE_MANIFEST_SHA256,
        "candidate manifest drift"
    );
    let manifest: Value = serde_json::from_reader(BufReader::new(File::open(manifest_path)?))?;
    ensure!(
        json_string(&manifest, "/schema")? == "max11-g0128-full-family-master-manifest-v2"
            && json_u64(&manifest, "/rows")? == ROWS as u64
            && json_u64(&manifest, "/records")? == RECORDS as u64,
        "candidate manifest metadata drift"
    );
    let entries = manifest
        .pointer("/expected_inputs")
        .and_then(Value::as_array)
        .context("candidate transitive inputs missing")?;
    ensure!(entries.len() == 41, "transitive-input census drift");
    let mut seen_paths = HashSet::new();
    let mut seen_resolved = HashSet::new();
    let mut output = Vec::with_capacity(entries.len());
    for entry in entries {
        let path = entry
            .get("path")
            .and_then(Value::as_str)
            .context("transitive path missing")?;
        let expected = entry
            .get("sha256")
            .and_then(Value::as_str)
            .context("transitive sha missing")?;
        ensure!(
            seen_paths.insert(path.to_string()),
            "duplicate transitive path"
        );
        let resolved = checked_repo_path(root, path)?;
        ensure!(
            seen_resolved.insert(resolved.clone()),
            "resolved duplicate transitive path"
        );
        let actual = sha256_path(&resolved)?;
        ensure!(actual == expected, "transitive binding drift: {path}");
        output.push(Binding {
            path: path.to_string(),
            sha256: actual,
        });
    }
    ensure!(
        output
            .iter()
            .any(|binding| binding.path == PANEL_INPUT_PATH && binding.sha256 == INPUT_SHA256)
            && output
                .iter()
                .any(|binding| binding.path == "artifacts/math/G-0117/src/lib.rs"
                    && binding.sha256 == KERNEL_SHA256)
            && output.iter().any(|binding| binding.path
                == "artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md"
                && binding.sha256 == UNIQUENESS_SHA256),
        "required transitive binding missing"
    );
    Ok(output)
}

fn validate_compiled_and_static(root: &Path) -> Result<()> {
    ensure!(
        sha256_bytes(COMPILED_SOURCE)
            == sha256_path(&checked_repo_path(
                root,
                "artifacts/math/G-0135/src/main.rs"
            )?)?,
        "running binary was compiled from different source"
    );
    ensure!(
        sha256_bytes(COMPILED_MANIFEST)
            == sha256_path(&checked_repo_path(
                root,
                "artifacts/math/G-0135/Cargo.toml"
            )?)?,
        "running binary was compiled from different Cargo manifest"
    );
    ensure!(
        sha256_bytes(COMPILED_LOCK)
            == sha256_path(&checked_repo_path(
                root,
                "artifacts/math/G-0135/Cargo.lock"
            )?)?,
        "running binary was compiled from different Cargo lockfile"
    );
    ensure!(
        sha256_bytes(COMPILED_PREREGISTRATION) == G0135_PREREGISTRATION_SHA256
            && sha256_bytes(COMPILED_CANDIDATE) == CANDIDATE_SHA256
            && sha256_bytes(COMPILED_KERNEL) == KERNEL_SHA256
            && sha256_bytes(COMPILED_UNIQUENESS) == UNIQUENESS_SHA256,
        "compiled scientific input drift"
    );
    for (_, path, expected) in FROZEN_DIRECT_BINDINGS {
        make_expected_binding(root, path, expected)?;
    }
    Ok(())
}

fn load_and_validate_inputs(
    root: &Path,
    input_path: &Path,
    candidate_path: &Path,
) -> Result<(PanelInput, Candidate, Vec<Binding>)> {
    ensure!(
        input_path == Path::new(PANEL_INPUT_PATH),
        "panel path drift"
    );
    ensure!(
        candidate_path == Path::new(CANDIDATE_PATH),
        "candidate path drift"
    );
    validate_compiled_and_static(root)?;
    ensure!(
        sha256_path(&checked_repo_path(root, PANEL_INPUT_PATH)?)? == INPUT_SHA256
            && sha256_path(&checked_repo_path(root, CANDIDATE_PATH)?)? == CANDIDATE_SHA256,
        "primary input binding drift"
    );
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(
        checked_repo_path(root, PANEL_INPUT_PATH)?,
    )?))?;
    let candidate: Candidate = serde_json::from_reader(BufReader::new(File::open(
        checked_repo_path(root, CANDIDATE_PATH)?,
    )?))?;
    validate_panel(&input)?;
    validate_planted_known_answer(&input)?;
    validate_candidate(&candidate)?;
    validate_finite_audit(root, &candidate)?;
    validate_prior_result_audit(root)?;
    let transitive = load_transitive_inputs(root)?;
    Ok((input, candidate, transitive))
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

fn validate_source_audit(
    root: &Path,
    source: &Binding,
    cargo_manifest: &Binding,
    cargo_lock: &Binding,
    executable: &Binding,
    transitive_inputs: &[Binding],
) -> Result<()> {
    let path = checked_repo_path(root, SOURCE_AUDIT_RECEIPT_PATH)?;
    let receipt: SourceAuditReceipt = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    ensure!(
        receipt.schema == "max11-g0133-g0135-source-audit-receipt-v1"
            && receipt.verdict == "PASS"
            && !receipt.scientific_manifest_observed
            && !receipt.scientific_output_observed
            && receipt.promotion_boundary == SOURCE_AUDIT_BOUNDARY,
        "source audit did not clear exact source"
    );
    let source_commit = git_commit_for_path(root, &source.path)?;
    ensure!(
        receipt.subject.source
            == CommitBinding {
                path: source.path.clone(),
                sha256: source.sha256.clone(),
                git_commit: source_commit,
            }
            && receipt.subject.cargo_manifest == *cargo_manifest
            && receipt.subject.cargo_lock == *cargo_lock
            && receipt.subject.executable == *executable,
        "source audit subject binding mismatch"
    );

    let expected_frozen = FROZEN_DIRECT_BINDINGS
        .iter()
        .map(|(_, path, sha256)| ((*path).to_string(), (*sha256).to_string()))
        .chain(
            transitive_inputs
                .iter()
                .map(|binding| (binding.path.clone(), binding.sha256.clone())),
        )
        .collect::<BTreeSet<_>>();
    let observed_frozen = receipt
        .frozen_inputs
        .values()
        .map(|binding| (binding.path.clone(), binding.sha256.clone()))
        .collect::<BTreeSet<_>>();
    ensure!(
        receipt.frozen_inputs.len() == expected_frozen.len() && observed_frozen == expected_frozen,
        "source audit frozen-input set mismatch"
    );
    let mut resolved_inputs = HashSet::new();
    for binding in receipt.frozen_inputs.values() {
        let resolved = checked_repo_path(root, &binding.path)?;
        ensure!(
            resolved_inputs.insert(resolved.clone()) && sha256_path(&resolved)? == binding.sha256,
            "source audit frozen input is duplicated or stale"
        );
    }

    let expected_report = make_binding(root, SOURCE_AUDIT_REPORT_PATH)?;
    let expected_self_test = make_binding(root, SOURCE_AUDIT_SELF_TEST_PATH)?;
    let expected_probe_source = make_binding(root, SOURCE_AUDIT_PROBE_SOURCE_PATH)?;
    let expected_probe_receipt = make_binding(root, SOURCE_AUDIT_PROBE_RECEIPT_PATH)?;
    let mut audit_paths = HashSet::new();
    let artifacts = [
        &receipt.audit_artifacts.report,
        &receipt.audit_artifacts.self_test_receipt,
        &receipt.audit_artifacts.independent_probe_source,
        &receipt.audit_artifacts.independent_probe_receipt,
    ];
    ensure!(
        receipt.audit_artifacts.report == expected_report
            && receipt.audit_artifacts.self_test_receipt == expected_self_test
            && receipt.audit_artifacts.independent_probe_source == expected_probe_source
            && receipt.audit_artifacts.independent_probe_receipt == expected_probe_receipt
            && receipt.self_test.status == "PASS"
            && receipt.self_test.command == format!("{} --self-test", executable.path)
            && receipt.self_test.receipt == receipt.audit_artifacts.self_test_receipt
            && receipt.independent_probe.status == "PASS"
            && !receipt.independent_probe.command.trim().is_empty()
            && receipt
                .independent_probe
                .command
                .contains(SOURCE_AUDIT_PROBE_SOURCE_PATH)
            && receipt.independent_probe.receipt
                == receipt.audit_artifacts.independent_probe_receipt,
        "source audit self-test or independent-probe binding mismatch"
    );
    for artifact in artifacts {
        ensure!(
            artifact
                .path
                .starts_with("artifacts/reviews/G-0136-g0135-source/")
                && artifact.path != SOURCE_AUDIT_RECEIPT_PATH,
            "source audit artifact outside review directory"
        );
        let resolved = checked_repo_path(root, &artifact.path)?;
        ensure!(
            audit_paths.insert(resolved.clone()) && sha256_path(&resolved)? == artifact.sha256,
            "source audit artifact is duplicated or stale"
        );
        git_commit_for_path(root, &artifact.path)?;
    }
    Ok(())
}

fn manifest_environment() -> Result<ManifestEnvironment> {
    let rustc = Command::new("rustc").arg("-Vv").output()?;
    ensure!(rustc.status.success(), "rustc environment query failed");
    Ok(ManifestEnvironment {
        os: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
        rustc_verbose: String::from_utf8(rustc.stdout)?.trim().to_string(),
        available_parallelism: std::thread::available_parallelism()?.get(),
    })
}

fn expected_manifest(root: &Path, transitive_inputs: Vec<Binding>) -> Result<StudyManifest> {
    let executable_path = relative_executable(root)?;
    let source = make_binding(root, "artifacts/math/G-0135/src/main.rs")?;
    let cargo_manifest = make_binding(root, "artifacts/math/G-0135/Cargo.toml")?;
    let cargo_lock = make_binding(root, "artifacts/math/G-0135/Cargo.lock")?;
    let executable = make_binding(root, &executable_path)?;
    validate_source_audit(
        root,
        &source,
        &cargo_manifest,
        &cargo_lock,
        &executable,
        &transitive_inputs,
    )?;

    let mut bindings = BTreeMap::new();
    for (label, path, expected) in FROZEN_DIRECT_BINDINGS {
        ensure!(
            bindings
                .insert(
                    (*label).to_string(),
                    make_expected_binding(root, path, expected)?
                )
                .is_none(),
            "duplicate direct binding label"
        );
    }
    bindings.insert("producer".to_string(), source);
    bindings.insert("cargo_manifest".to_string(), cargo_manifest);
    bindings.insert("cargo_lock".to_string(), cargo_lock);
    bindings.insert("executable".to_string(), executable);
    bindings.insert(
        "source_audit_receipt".to_string(),
        make_binding(root, SOURCE_AUDIT_RECEIPT_PATH)?,
    );

    let mut resolved = HashSet::new();
    for binding in bindings.values().chain(transitive_inputs.iter()) {
        let path = checked_repo_path(root, &binding.path)?;
        ensure!(resolved.insert(path), "duplicate resolved manifest input");
        ensure!(
            sha256_path(&checked_repo_path(root, &binding.path)?)? == binding.sha256,
            "manifest binding changed during construction"
        );
    }

    Ok(StudyManifest {
        schema: "max11-g0135-batch32-global-replay-manifest-v1".to_string(),
        selected_branch: "MEMBER".to_string(),
        output_path: MEMBER_RESULT_PATH.to_string(),
        preregistration_git_commit: G0135_PREREGISTRATION_COMMIT.to_string(),
        producer_git_commit: git_commit_for_path(root, "artifacts/math/G-0135/src/main.rs")?,
        source_audit_git_commit: git_commit_for_path(root, SOURCE_AUDIT_RECEIPT_PATH)?,
        bindings,
        transitive_inputs,
        parameters: ManifestParameters {
            n: N,
            rows: ROWS,
            records: RECORDS,
            terms: TERMS,
            batch_k: BATCH_K,
            selected_slots: SELECTED_SLOTS,
            carry_directions: CARRY_DIRECTIONS,
            target_coordinate: N - 1,
            labelled_permutations: EXPECTED_LABELLED_PERMUTATIONS,
            threads: THREADS,
            arithmetic: "signed_num_bigint_BigInt_unconditional_exact".to_string(),
            decision_rule: EXACT_DECISION_RULE.to_string(),
        },
        environment: manifest_environment()?,
    })
}

fn self_test() -> Result<()> {
    for valid in ["0", "1", "-1", "12345678901234567890"] {
        ensure!(canonical_integer(valid), "valid integer rejected");
    }
    for invalid in ["", "-", "+1", "00", "01", "-0", "-01", "1/2", " 1"] {
        ensure!(!canonical_integer(invalid), "invalid integer accepted");
    }
    ensure!(
        canonical_positive_integer("1")
            && !canonical_positive_integer("0")
            && !canonical_positive_integer("-1")
            && decimal_mod("-1", 7)? == 6,
        "canonical integer control drift"
    );
    ensure!(
        validate_strict_axis(&[0, 2], 2, 3, "fixture").is_ok()
            && validate_strict_axis(&[0, 0], 2, 3, "duplicate fixture").is_err()
            && validate_strict_axis(&[2, 0], 2, 3, "reordered fixture").is_err()
            && nonzero_term_projection(
                &[0, 1, 2],
                &["1".to_string(), "0".to_string(), "-3".to_string()],
            )? == vec![
                Term {
                    sequence: 0,
                    coefficient: "1".to_string(),
                },
                Term {
                    sequence: 2,
                    coefficient: "-3".to_string(),
                },
            ]
            && serde_json::from_str::<Term>(r#"{"sequence":0,"coefficient":"1","extra":2}"#,)
                .is_err(),
        "axis, projection, or unknown-field control drift"
    );

    let record = Record {
        sequence: 0,
        signed_mass: 3,
        active_vertices: 6,
        negative_edges: vec![[0, 1], [1, 2], [3, 4]],
        positive_edges: vec![[0, 2], [2, 5], [4, 5]],
    };
    let form = validated_full_normal_form(&record)?;
    ensure!(
        !form.hinges.is_empty(),
        "known nonzero normal form missing hinges"
    );
    let directions = form.hinges.keys().copied().collect::<Vec<_>>();
    let coordinate_route = exact_hinge_coefficients(&record, &directions)?;
    ensure!(
        directions
            .iter()
            .zip(coordinate_route)
            .all(|(direction, value)| form.hinges[direction] == value)
            && form.linear == exact_linear_vector(&record)?,
        "independent normal-form route disagreement"
    );
    let receipt = term_receipt(&record, &form)?;
    ensure!(
        receipt.compressed_leaves_generated == receipt.compressed_leaves_visited
            && receipt.compressed_leaves_visited == receipt.compressed_leaves_accepted
            && receipt.compressed_leaves_accepted * receipt.inactive_label_multiplicity
                == factorial(N)
            && receipt.skipped_labelled_permutations == 0
            && receipt.unclassified_labelled_permutations == 0
            && receipt.failed_labelled_permutations == 0,
        "term census control drift"
    );
    let complete_receipts = vec![receipt; TERMS];
    validate_term_receipts(&complete_receipts)?;
    let mut final_only_orbit_mutant = complete_receipts;
    final_only_orbit_mutant
        .last_mut()
        .context("final-only orbit fixture missing")?
        .visited_labelled_permutations -= 1;
    ensure!(
        validate_term_receipts(&final_only_orbit_mutant).is_err(),
        "final-only orbit discrepancy escaped the production census validator"
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

    let first_direction = form.hinges.keys().copied().min().context("known hinge")?;
    let mut reversed = first_direction;
    for coordinate in &mut reversed {
        *coordinate = -*coordinate;
    }
    let mut doubled = first_direction;
    for coordinate in &mut doubled {
        *coordinate *= 2;
    }
    let mut inactive = [0i8; N];
    inactive[0] = 1;
    inactive[1] = -1;
    ensure!(
        validate_direction(&reversed).is_err()
            && validate_direction(&doubled).is_err()
            && validate_direction(&inactive).is_err(),
        "direction sign/gcd/active-prefix mutant escaped"
    );

    let mut swapped = record.clone();
    std::mem::swap(&mut swapped.negative_edges, &mut swapped.positive_edges);
    let swapped_form = validated_full_normal_form(&swapped)?;
    ensure!(
        normal_form_digest(&form, None, None) == normal_form_digest(&swapped_form, None, None),
        "correct branch swap lost pair-max invariance"
    );
    let permutation = [1usize, 0, 2, 3, 4, 5];
    let relabel_edges = |edges: &[[usize; 2]]| {
        edges
            .iter()
            .map(|edge| {
                let mut mapped = [permutation[edge[0]], permutation[edge[1]]];
                mapped.sort();
                mapped
            })
            .collect::<Vec<_>>()
    };
    let relabelled = Record {
        sequence: record.sequence,
        signed_mass: record.signed_mass,
        active_vertices: record.active_vertices,
        negative_edges: relabel_edges(&record.negative_edges),
        positive_edges: relabel_edges(&record.positive_edges),
    };
    ensure!(
        normal_form_digest(&form, None, None)
            == normal_form_digest(&validated_full_normal_form(&relabelled)?, None, None),
        "active-vertex relabelling invariance drift"
    );
    let mut orientation_mutant = swapped_form.linear;
    orientation_mutant[0] += BigInt::from(1);
    ensure!(
        orientation_mutant != form.linear,
        "linear orientation mutant escaped"
    );
    let orientation_delta = BigInt::from(1);
    let orientation_control = mutation_control(
        "linear_orientation_plus_one_fixture",
        &zero,
        None,
        Some((0, &orientation_delta)),
    )?;
    ensure!(
        orientation_control.rejected
            && orientation_control.changed_from_unmutated
            && mutation_control(
                "linear_orientation_noop_fixture",
                &zero,
                None,
                Some((0, &BigInt::from(0))),
            )
            .is_err(),
        "linear orientation terminal-path mutant control drift"
    );

    let mut residual_base = ExactAggregate::default();
    residual_base
        .hinges
        .insert(first_direction, BigInt::from(9));
    let residual_base_control = mutation_control(
        "residual_base_late_coordinate_fixture",
        &residual_base,
        None,
        Some((N - 1, &BigInt::from(1))),
    )?;
    ensure!(
        residual_base_control.changed_from_unmutated,
        "mutation was hidden behind an earlier base residual"
    );

    let mut selection_fixture = ExactAggregate::default();
    for (index, direction) in form.hinges.keys().copied().take(BATCH_K + 1).enumerate() {
        selection_fixture
            .hinges
            .insert(direction, BigInt::from(index + 1));
    }
    ensure!(
        selection_fixture.hinges.len() == BATCH_K + 1,
        "Batch32 fixture has insufficient hinge support"
    );
    let selection = select_residual_batch(&selection_fixture, &[])?;
    let direction_digest = selected_direction_digest(&selection);
    let residual_digest = selected_residual_digest(&selection);
    let mut reordered_selection = selection.clone();
    reordered_selection.swap(0, 1);
    let mut coefficient_mutant = selection.clone();
    coefficient_mutant[0].coefficient =
        (parse_bigint(&coefficient_mutant[0].coefficient)? + BigInt::from(1)).to_string();
    ensure!(
        selection.len() == BATCH_K
            && selection
                .windows(2)
                .all(|window| window[0].direction < window[1].direction)
            && selected_direction_digest(&reordered_selection) != direction_digest
            && selected_residual_digest(&coefficient_mutant) != residual_digest
            && select_residual_batch(&selection_fixture, &[selection[0].direction]).is_err(),
        "Batch32 selection/order/digest/carried-row control drift"
    );

    let base_digest = normal_form_digest(&form, None, None);
    ensure!(
        base_digest != normal_form_digest(&form, Some(first_direction), None)
            && base_digest != normal_form_digest(&form, None, Some(N - 1)),
        "omitted normal-form coordinate escaped digest"
    );
    let collision = BigInt::from(SCREENING_PRIMES[0]) * BigInt::from(SCREENING_PRIMES[1]);
    ensure!(
        decimal_mod(&collision.to_string(), SCREENING_PRIMES[0])? == 0
            && decimal_mod(&collision.to_string(), SCREENING_PRIMES[1])? == 0
            && collision != BigInt::from(0),
        "screening-prime collision control drift"
    );

    let mut target_fixture = ExactAggregate::default();
    target_fixture.linear[N - 1] = BigInt::from(factorial(N));
    target_fixture.linear[N - 1] -= BigInt::from(factorial(N));
    let (target_hinge, target_linear) = residual_summary(&target_fixture, None, None);
    ensure!(
        target_hinge.is_none() && target_linear.is_none(),
        "exact target subtraction drift"
    );
    mutation_control(
        "target_coordinate_plus_one_fixture",
        &target_fixture,
        None,
        Some((N - 1, &BigInt::from(1))),
    )?;

    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0135-publish-self-test-{}-{unique}",
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
    std::fs::remove_dir(&temporary_directory)?;
    Ok(())
}

fn preflight(input_path: PathBuf, candidate_path: PathBuf) -> Result<()> {
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let (_, candidate, transitive) = load_and_validate_inputs(&root, &input_path, &candidate_path)?;
    ensure!(
        candidate.terms.len() == TERMS && transitive.len() == 41,
        "preflight census drift"
    );
    println!(
        "G-0135 preflight PASS: finite member admitted; {} terms; {} transitive inputs",
        candidate.terms.len(),
        transitive.len()
    );
    Ok(())
}

fn build_manifest(
    input_path: PathBuf,
    candidate_path: PathBuf,
    manifest_path: PathBuf,
) -> Result<()> {
    ensure!(
        manifest_path == Path::new(MEMBER_MANIFEST_PATH),
        "manifest path drift"
    );
    ensure!(!manifest_path.exists(), "refusing to overwrite manifest");
    ensure!(
        !Path::new(MEMBER_RESULT_PATH).exists(),
        "member output already exists"
    );
    ensure!(
        !Path::new(NONMEMBER_RESULT_PATH).exists(),
        "unselected output exists"
    );
    self_test()?;
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let (_, _, transitive) = load_and_validate_inputs(&root, &input_path, &candidate_path)?;
    let manifest = expected_manifest(&root, transitive)?;
    let mut serialized = serde_json::to_vec_pretty(&manifest)?;
    serialized.push(b'\n');
    let (_, _, end_transitive) = load_and_validate_inputs(&root, &input_path, &candidate_path)?;
    ensure!(
        manifest == expected_manifest(&root, end_transitive)?,
        "input/source drift during manifest pre-serialization"
    );
    publish_exclusive_with_branch_guard(
        &manifest_path,
        &serialized,
        &[MEMBER_RESULT_PATH, NONMEMBER_RESULT_PATH],
    )?;
    println!(
        "{}",
        serde_json::json!({
            "result": "MEMBER_MANIFEST_FROZEN",
            "path": MEMBER_MANIFEST_PATH,
            "sha256": sha256_bytes(&serialized),
        })
    );
    Ok(())
}

fn run(
    input_path: PathBuf,
    candidate_path: PathBuf,
    manifest_path: PathBuf,
    output_path: PathBuf,
) -> Result<()> {
    ensure!(
        manifest_path == Path::new(MEMBER_MANIFEST_PATH),
        "manifest path drift"
    );
    ensure!(
        output_path == Path::new(MEMBER_RESULT_PATH),
        "output path drift"
    );
    ensure!(!output_path.exists(), "refusing to overwrite output");
    ensure!(
        !Path::new(NONMEMBER_RESULT_PATH).exists(),
        "unselected output exists"
    );
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(THREADS)
        .build_global()
        .context("build fixed replay thread pool")?;
    let started = Instant::now();
    let root = repo_root()?;
    ensure!(
        std::env::current_dir()?.canonicalize()? == root,
        "run from repository root"
    );
    let (input, candidate, transitive) =
        load_and_validate_inputs(&root, &input_path, &candidate_path)?;
    let manifest_sha_start = sha256_path(&checked_repo_path(&root, MEMBER_MANIFEST_PATH)?)?;
    let manifest: StudyManifest = serde_json::from_reader(BufReader::new(File::open(
        checked_repo_path(&root, MEMBER_MANIFEST_PATH)?,
    )?))?;
    let expected_start = expected_manifest(&root, transitive)?;
    ensure!(manifest == expected_start, "scientific manifest drift");

    let mut aggregate = candidate
        .terms
        .par_iter()
        .map(|term| -> Result<ExactAggregate> {
            let record = &input.records[term.sequence];
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
    ensure!(aggregate.terms == TERMS, "exact term census drift");
    ensure!(
        aggregate.labelled_permutations_checked == EXPECTED_LABELLED_PERMUTATIONS,
        "exact labelled-permutation census drift"
    );
    ensure!(
        aggregate
            .term_receipts
            .iter()
            .map(|receipt| receipt.sequence)
            .eq(candidate.terms.iter().map(|term| term.sequence)),
        "term receipt order drift"
    );
    validate_term_receipts(&aggregate.term_receipts)?;
    let target_subtraction = parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N));
    aggregate.linear[N - 1] -= &target_subtraction;

    let (first_nonzero_hinge, first_nonzero_linear) = residual_summary(&aggregate, None, None);
    let all_zero = first_nonzero_hinge.is_none() && first_nonzero_linear.is_none();
    let result = "EXACT_RESIDUAL_BATCH";
    let nonzero_hinges = aggregate
        .hinges
        .values()
        .filter(|coefficient| **coefficient != BigInt::from(0))
        .count();
    let direct_carry = direct_carry_prices(&input, &candidate)?;
    let carry_forward_checks = candidate
        .hinge_directions
        .iter()
        .enumerate()
        .map(|(index, direction)| -> Result<CarryForwardCheck> {
            let coefficient = aggregate.hinges.get(direction).cloned().unwrap_or_default();
            ensure!(
                coefficient == direct_carry[index],
                "full-normal-form/direct-DP carry replay disagreement at {index}"
            );
            Ok(CarryForwardCheck {
                index,
                direction: *direction,
                coefficient: coefficient.to_string(),
                exact_zero: coefficient == BigInt::from(0),
            })
        })
        .collect::<Result<Vec<_>>>()?;
    let first_carry_forward_failure = carry_forward_checks
        .iter()
        .position(|check| !check.exact_zero);
    ensure!(
        first_carry_forward_failure.is_none(),
        "frozen 68-direction replay control failed"
    );

    let first_term = &candidate.terms[0];
    let final_term = candidate.terms.last().context("final term missing")?;
    let first_form = validated_full_normal_form(&input.records[first_term.sequence])?;
    let final_form = validated_full_normal_form(&input.records[final_term.sequence])?;
    let one = BigInt::from(1);
    let negative_first_coefficient = -parse_bigint(&first_term.coefficient)?;
    let negative_final_coefficient = -parse_bigint(&final_term.coefficient)?;
    let negative_factorial = -BigInt::from(factorial(N));
    let negative_one = BigInt::from(-1);
    let first_coefficient_plus_one = mutation_control(
        "first_nonzero_coefficient_plus_one",
        &aggregate,
        Some((&first_form, &one)),
        None,
    )?;
    let final_coefficient_plus_one = mutation_control(
        "final_nonzero_coefficient_plus_one",
        &aggregate,
        Some((&final_form, &one)),
        None,
    )?;
    let target_scale_plus_one = mutation_control(
        "target_scale_plus_one",
        &aggregate,
        None,
        Some((N - 1, &negative_factorial)),
    )?;
    let target_coordinate_10_plus_one = mutation_control(
        "target_coordinate_10_plus_one",
        &aggregate,
        None,
        Some((N - 1, &negative_one)),
    )?;
    let omitted_final_term = mutation_control(
        "omitted_final_nonzero_term",
        &aggregate,
        Some((&final_form, &negative_final_coefficient)),
        None,
    )?;
    let omitted_direction = first_form
        .hinges
        .keys()
        .copied()
        .min()
        .context("first term has no active hinge direction")?;
    let omitted_direction_value = first_form
        .hinges
        .get(&omitted_direction)
        .context("deterministic omitted direction disappeared")?;
    let mut single_hinge = HashMap::new();
    single_hinge.insert(omitted_direction, omitted_direction_value.clone());
    let omitted_direction_form = ExactNormalForm {
        linear: std::array::from_fn(|_| BigInt::from(0)),
        hinges: single_hinge,
        labelled_permutations: factorial(N),
        compressed_leaves: factorial(N),
    };
    let omitted_first_term_active_direction = mutation_control(
        "omitted_first_term_active_direction",
        &aggregate,
        Some((&omitted_direction_form, &negative_first_coefficient)),
        None,
    )?;
    let omitted_linear_coordinate = first_form
        .linear
        .iter()
        .position(|value| *value != BigInt::from(0))
        .context("first term has no nonzero linear coordinate")?;
    let mut single_linear: [BigInt; N] = std::array::from_fn(|_| BigInt::from(0));
    single_linear[omitted_linear_coordinate] = first_form.linear[omitted_linear_coordinate].clone();
    let omitted_linear_form = ExactNormalForm {
        linear: single_linear,
        hinges: HashMap::new(),
        labelled_permutations: factorial(N),
        compressed_leaves: factorial(N),
    };
    let omitted_first_term_linear_coordinate = mutation_control(
        "omitted_first_term_linear_coordinate",
        &aggregate,
        Some((&omitted_linear_form, &negative_first_coefficient)),
        None,
    )?;

    let all_hinge_digest = hinge_digest(&aggregate.hinges, false);
    let nonzero_hinge_digest = hinge_digest(&aggregate.hinges, true);
    let term_transcript = serde_json::to_vec(&aggregate.term_receipts)?;
    let term_transcript_digest = sha256_bytes(&term_transcript);
    let prior_g0132_reconciled = !all_zero
        && first_nonzero_linear.is_none()
        && first_nonzero_hinge.as_ref()
            == Some(&ExactHinge {
                direction: EXPECTED_FIRST_DIRECTION,
                coefficient: EXPECTED_FIRST_COEFFICIENT.to_string(),
            })
        && aggregate.terms == TERMS
        && aggregate.hinge_entries_processed == EXPECTED_HINGE_ENTRIES_PROCESSED
        && aggregate.labelled_permutations_checked == EXPECTED_LABELLED_PERMUTATIONS
        && aggregate.hinges.len() == EXPECTED_AGGREGATE_HINGE_SUPPORT
        && nonzero_hinges == EXPECTED_NONZERO_HINGE_DIRECTIONS
        && all_hinge_digest == EXPECTED_AGGREGATE_HINGE_SHA256
        && nonzero_hinge_digest == EXPECTED_NONZERO_HINGE_SHA256
        && term_transcript_digest == EXPECTED_TERM_TRANSCRIPT_SHA256;
    ensure!(
        prior_g0132_reconciled,
        "G-0132 exact replay reconciliation failed"
    );

    let selected = select_residual_batch(&aggregate, &candidate.hinge_directions)?;
    let selected_directions_i8_sha256 = selected_direction_digest(&selected);
    let selected_exact_residuals_decimal_lf_sha256 = selected_residual_digest(&selected);
    let mut reordered = selected.clone();
    reordered.swap(0, 1);
    let mut residual_mutant = selected.clone();
    residual_mutant[0].coefficient =
        (parse_bigint(&residual_mutant[0].coefficient)? + BigInt::from(1)).to_string();
    let selection_controls = SelectionControls {
        exact_batch_count: selected.len() == BATCH_K,
        strict_signed_lexicographic_order: selected
            .windows(2)
            .all(|window| window[0].direction < window[1].direction),
        first_direction_matches_g0132: selected[0].direction == EXPECTED_FIRST_DIRECTION,
        first_coefficient_matches_g0132: selected[0].coefficient == EXPECTED_FIRST_COEFFICIENT,
        direction_reordering_changes_digest: selected_direction_digest(&reordered)
            != selected_directions_i8_sha256,
        residual_plus_one_changes_digest: selected_residual_digest(&residual_mutant)
            != selected_exact_residuals_decimal_lf_sha256,
    };
    ensure!(
        selection_controls.exact_batch_count
            && selection_controls.strict_signed_lexicographic_order
            && selection_controls.first_direction_matches_g0132
            && selection_controls.first_coefficient_matches_g0132
            && selection_controls.direction_reordering_changes_digest
            && selection_controls.residual_plus_one_changes_digest,
        "Batch32 selection control failed"
    );
    let mut omitted_orbit_receipts = aggregate.term_receipts.clone();
    omitted_orbit_receipts
        .last_mut()
        .context("final term receipt missing")?
        .visited_labelled_permutations -= 1;
    let census_controls = CensusControls {
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
        omitted_final_term_rejected: omitted_final_term.rejected,
        omitted_last_orbit_contribution_rejected: validate_term_receipts(&omitted_orbit_receipts)
            .is_err(),
        omitted_active_direction_changed_terminal_residual: omitted_first_term_active_direction
            .rejected
            && omitted_first_term_active_direction.changed_from_unmutated,
        omitted_linear_coordinate_changed_terminal_residual: omitted_first_term_linear_coordinate
            .rejected
            && omitted_first_term_linear_coordinate.changed_from_unmutated,
        screening_prime_collision_found_exactly: {
            let collision = BigInt::from(SCREENING_PRIMES[0]) * BigInt::from(SCREENING_PRIMES[1]);
            decimal_mod(&collision.to_string(), SCREENING_PRIMES[0])? == 0
                && decimal_mod(&collision.to_string(), SCREENING_PRIMES[1])? == 0
                && collision != BigInt::from(0)
        },
    };
    ensure!(
        census_controls.per_term_generated_equals_visited_equals_accepted
            && census_controls.zero_skipped_unclassified_failed
            && census_controls.omitted_final_term_rejected
            && census_controls.omitted_last_orbit_contribution_rejected
            && census_controls.omitted_active_direction_changed_terminal_residual
            && census_controls.omitted_linear_coordinate_changed_terminal_residual
            && census_controls.screening_prime_collision_found_exactly,
        "census or hostile control failed"
    );

    let output = Output {
        schema: "max11-g0135-batch32-global-replay-v1",
        result,
        claim_boundary: GLOBAL_CLAIM_BOUNDARY,
        manifest_path: MEMBER_MANIFEST_PATH,
        manifest_sha256: manifest_sha_start.clone(),
        bindings: manifest.bindings.clone(),
        candidate_schema: candidate.schema.clone(),
        candidate_result: candidate.result.clone(),
        target_scale: candidate.target_scale.clone(),
        target_subtraction_coordinate_10: target_subtraction.to_string(),
        arithmetic: "signed_num_bigint_BigInt_unconditional_exact",
        decision_rule: EXACT_DECISION_RULE,
        screening_primes_control_only: SCREENING_PRIMES,
        complete_global_replay: true,
        all_hinge_and_linear_residuals_zero: all_zero,
        terms: aggregate.terms,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        aggregate_hinge_support: aggregate.hinges.len(),
        nonzero_hinge_directions: nonzero_hinges,
        aggregate_hinge_decimal_lf_sha256: all_hinge_digest,
        nonzero_hinge_decimal_lf_sha256: nonzero_hinge_digest,
        term_normal_form_transcript_sha256: term_transcript_digest,
        term_normal_forms: aggregate.term_receipts,
        carry_forward_checks,
        first_carry_forward_failure,
        linear_residuals_after_target: aggregate.linear.iter().map(ToString::to_string).collect(),
        first_nonzero_hinge,
        first_nonzero_linear,
        prior_g0132_reconciled,
        batch_k: BATCH_K,
        selected_count: selected.len(),
        selected_directions_i8_sha256,
        selected_exact_residuals_decimal_lf_sha256,
        selected,
        selection_controls,
        first_coefficient_plus_one,
        final_coefficient_plus_one,
        target_scale_plus_one,
        target_coordinate_10_plus_one,
        omitted_final_term,
        omitted_first_term_active_direction,
        omitted_first_term_linear_coordinate,
        census_controls,
        inputs_rehashed_at_end: true,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let stdout = serde_json::json!({
        "result": output.result,
        "terms": output.terms,
        "labelled_permutations_checked": output.labelled_permutations_checked,
        "nonzero_hinge_directions": output.nonzero_hinge_directions,
        "first_nonzero_hinge": output.first_nonzero_hinge,
        "first_nonzero_linear": output.first_nonzero_linear,
        "selected_count": output.selected_count,
        "selected_directions_i8_sha256": output.selected_directions_i8_sha256,
        "selected_exact_residuals_decimal_lf_sha256": output.selected_exact_residuals_decimal_lf_sha256,
    });
    let mut serialized = serde_json::to_vec_pretty(&output)?;
    serialized.push(b'\n');
    let (_, end_candidate, end_transitive) =
        load_and_validate_inputs(&root, &input_path, &candidate_path)?;
    ensure!(
        end_candidate.terms == candidate.terms,
        "candidate changed during replay"
    );
    let expected_end = expected_manifest(&root, end_transitive)?;
    ensure!(manifest == expected_end, "input/source drift during replay");
    let manifest_sha_end = sha256_path(&checked_repo_path(&root, MEMBER_MANIFEST_PATH)?)?;
    ensure!(
        manifest_sha_start == manifest_sha_end,
        "manifest drift during replay"
    );
    publish_exclusive_with_branch_guard(&output_path, &serialized, &[NONMEMBER_RESULT_PATH])?;
    println!("{stdout}");
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() == 2 && args[1] == "--self-test" {
        self_test()?;
        println!("G-0135 self-test PASS");
        return Ok(());
    }
    if args.len() == 4 && args[1] == "--preflight" {
        return preflight(PathBuf::from(&args[2]), PathBuf::from(&args[3]));
    }
    if args.len() == 5 && args[1] == "--build-manifest" {
        return build_manifest(
            PathBuf::from(&args[2]),
            PathBuf::from(&args[3]),
            PathBuf::from(&args[4]),
        );
    }
    ensure!(
        args.len() == 5,
        "usage: g0135-batch32-global-replay --self-test | --preflight PANEL CANDIDATE | --build-manifest PANEL CANDIDATE MANIFEST | PANEL CANDIDATE MANIFEST OUTPUT"
    );
    run(
        PathBuf::from(&args[1]),
        PathBuf::from(&args[2]),
        PathBuf::from(&args[3]),
        PathBuf::from(&args[4]),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn producer_self_test() {
        self_test().unwrap();
    }

    #[test]
    #[ignore = "near-frontier 10-active-vertex BigInt/pinned cross-route control"]
    fn maximum_support_bigint_matches_pinned() {
        let record = Record {
            sequence: usize::MAX,
            signed_mass: 5,
            active_vertices: 10,
            negative_edges: vec![[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]],
            positive_edges: vec![[0, 9], [1, 2], [3, 4], [5, 6], [7, 8]],
        };
        let exact = exact_full_normal_form(&record).unwrap();
        assert_eq!(exact.compressed_leaves, factorial(N));
        assert_eq!(exact.labelled_permutations, factorial(N));
        assert_eq!(exact.linear, exact_linear_vector(&record).unwrap());
        exact_matches_pinned(&record, &exact).unwrap();
    }
}
