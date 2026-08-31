use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{
    N, Record, full_normal_form, hinge_coefficients, validate_direction,
};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Write};
use std::path::{Component, Path, PathBuf};
use std::time::Instant;

const K: usize = 32;
const RECORDS: usize = 163_740;
const TERMS: usize = 132;
const ROWS: usize = 380;
const SELECTED_SLOTS: usize = 176;
const ZERO_SELECTED_COEFFICIENTS: usize = 44;
const CARRY_DIRECTIONS: usize = 68;
const MAX_TERM_SEQUENCE: usize = 161;
const THREADS: usize = 12;
const HINGE_ENTRIES: usize = K * RECORDS;
const EXPECTED_LABELLED_PERMUTATIONS: u64 = 5_269_017_600;
const EXPECTED_HINGE_ENTRIES_PROCESSED: u64 = 4_579_906;
const EXPECTED_AGGREGATE_HINGE_SUPPORT: usize = 163_036;
const EXPECTED_NONZERO_HINGE_DIRECTIONS: usize = 162_929;
const SCREENING_PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];

const PANEL_INPUT_PATH: &str = "artifacts/math/G-0113/panel_solver_input_v1.json";
const CANDIDATE_PATH: &str = "artifacts/math/G-0128/full_family_master_result_v2.json";
const CANDIDATE_MANIFEST_PATH: &str = "artifacts/math/G-0128/full_family_master_manifest_v2.json";
const CANDIDATE_SOLVER_PATH: &str = "artifacts/math/G-0128/full_family_master_v2.py";
const STAGE_A_RECEIPT_PATH: &str = "artifacts/math/G-0135/batch32_global_replay_v1.json";
const SHARED_MANIFEST_PATH: &str = "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json";
const OUTPUT_PATH: &str = "artifacts/math/G-0135/batch32_coordinate_prices_v1.json";
const STAGE_A_SOURCE_PATH: &str = "artifacts/math/G-0135/src/main.rs";
const STAGE_B_SOURCE_PATH: &str = "artifacts/math/G-0135/stage_b_pricer/src/main.rs";
const STAGE_B_CARGO_MANIFEST_PATH: &str = "artifacts/math/G-0135/stage_b_pricer/Cargo.toml";
const STAGE_B_CARGO_LOCK_PATH: &str = "artifacts/math/G-0135/stage_b_pricer/Cargo.lock";
const G0135_PREREGISTRATION_PATH: &str = "artifacts/math/G-0135/PREREGISTRATION.md";
const KERNEL_PATH: &str = "artifacts/math/G-0117/src/lib.rs";
const G0132_RECEIPT_PATH: &str = "artifacts/math/G-0132/member_global_normal_form_replay_v1.json";
const G0132_MANIFEST_PATH: &str =
    "artifacts/math/G-0132/member_global_normal_form_manifest_v1.json";
const G0134_RECEIPT_PATH: &str =
    "artifacts/reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json";
const G0127_SOURCE_PATH: &str = "artifacts/math/G-0127/src/main.rs";
const G0127_RECEIPT_PATH: &str = "artifacts/math/G-0127/batch32_coordinate_prices_v1.json";

const PANEL_INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const CANDIDATE_SHA256: &str = "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838";
const CANDIDATE_MANIFEST_SHA256: &str =
    "79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec";
const CANDIDATE_SOLVER_SHA256: &str =
    "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8";
const KERNEL_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";
const G0135_PREREGISTRATION_SHA256: &str =
    "ca9ed1930a8b7539d92d7651caadd06c6bd77742ce11adff682af9ac067fe5ec";
const G0132_RECEIPT_SHA256: &str =
    "d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50";
const G0132_MANIFEST_SHA256: &str =
    "b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732";
const G0134_RECEIPT_SHA256: &str =
    "a00aaca7aeb8f960d6fa5a264b72a13c797ae30a75c4eec5eaa90a5a455e2f56";
const G0127_SOURCE_SHA256: &str =
    "68a9062fa28a5ad5da614634066685cc7e66f709fe6309f553317b483ba23cd8";
const G0127_RECEIPT_SHA256: &str =
    "c4c5d59b13820027c81bd4e0b74c67027da851f0a6f90bd941484eb9c4533946";
const EXPECTED_AGGREGATE_HINGE_SHA256: &str =
    "955a80d8d6ecab4afd873249e764595dcb750e7d1b5385044d6f5c2b19b55c5c";
const EXPECTED_NONZERO_HINGE_SHA256: &str =
    "ff51e40c67556bdf813797620e6994ba3d6312f1222c00ed8a44617337ec66c2";
const EXPECTED_TERM_TRANSCRIPT_SHA256: &str =
    "5b4efbbd4cca06252545c89e52503b20ba332cd59eeb477d05d09a5a688a62ba";
const TARGET_SCALE: &str = "2289393005496338240468982655090335335732668690900751540287809289663720291914849699943112917639850352050294840444775090516901570116753181129941246082620";
const EXPECTED_FIRST_DIRECTION: [i8; N] = [0, 0, 0, 0, 0, 0, 1, -3, -2, 1, 3];
const EXPECTED_FIRST_COEFFICIENT: &str = "363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360";

const CANDIDATE_SCHEMA: &str = "max11-g0128-full-family-master-result-v2";
const CANDIDATE_RESULT: &str = "FULL_FAMILY_380ROW_EXACT_Q_MEMBER";
const CANDIDATE_CLAIM: &str = "Exact membership only on the frozen 380-row system over the frozen 163,740-column family; a finite-row candidate for separate complete global replay, not a family-completeness theorem, global MAX11 identity, lower bound, or Lean theorem.";
const STAGE_A_SCHEMA: &str = "max11-g0135-batch32-global-replay-v1";
const STAGE_A_RESULT: &str = "EXACT_RESIDUAL_BATCH";
const SHARED_MANIFEST_SCHEMA: &str = "max11-g0135-batch32-global-replay-manifest-v1";
const OUTPUT_SCHEMA: &str = "max11-g0135-batch32-coordinate-prices-v1";
const OUTPUT_RESULT: &str = "EXACT_FULL_FAMILY_BATCH32_COORDINATES";
const OUTPUT_CLAIM: &str = "Exact 32-row ordered-cone hinge coordinates over the frozen 163,740-record family, in deterministic G-0135 Stage-A order, with arbitrary-precision old-member dot bridges. This is Stage-C restricted-master input only, not a membership decision, family-completeness theorem, global MAX11 identity, lower bound, or Lean theorem.";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../../PREREGISTRATION.md");
const COMPILED_CANDIDATE: &[u8] =
    include_bytes!("../../../G-0128/full_family_master_result_v2.json");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../../G-0117/src/lib.rs");
const COMPILED_G0132_RECEIPT: &[u8] =
    include_bytes!("../../../G-0132/member_global_normal_form_replay_v1.json");
const COMPILED_G0134_RECEIPT: &[u8] =
    include_bytes!("../../../../reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json");
const COMPILED_G0127_SOURCE: &[u8] = include_bytes!("../../../G-0127/src/main.rs");

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
struct SharedManifest {
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
    planned_outputs: BTreeMap<String, Value>,
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

#[allow(dead_code)]
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
    bounded_pinned_kernel_crosscheck: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CarryForwardCheck {
    index: usize,
    direction: [i8; N],
    coefficient: String,
    exact_zero: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct MutationControl {
    name: String,
    first_nonzero_hinge: Option<ExactHinge>,
    first_nonzero_linear: Option<ExactLinear>,
    unmutated_residual_decimal_lf_sha256: String,
    mutated_residual_decimal_lf_sha256: String,
    changed_from_unmutated: bool,
    rejected: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct CensusControls {
    per_term_generated_equals_visited_equals_accepted: bool,
    zero_skipped_unclassified_failed: bool,
    omitted_final_term_rejected: bool,
    omitted_last_orbit_contribution_rejected: bool,
    omitted_active_direction_changed_terminal_residual: bool,
    omitted_linear_coordinate_changed_terminal_residual: bool,
    screening_prime_collision_found_exactly: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct SelectionControls {
    exact_batch_count: bool,
    strict_signed_lexicographic_order: bool,
    first_direction_matches_g0132: bool,
    first_coefficient_matches_g0132: bool,
    direction_reordering_changes_digest: bool,
    residual_plus_one_changes_digest: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct StageAReceipt {
    schema: String,
    result: String,
    claim_boundary: String,
    manifest_path: String,
    manifest_sha256: String,
    bindings: BTreeMap<String, Binding>,
    candidate_schema: String,
    candidate_result: String,
    target_scale: String,
    target_subtraction_coordinate_10: String,
    arithmetic: String,
    decision_rule: String,
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
    selected_count_mutant_rejected: bool,
    selection_order_mutant_rejected: bool,
    selection_duplicate_mutant_rejected: bool,
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
    bindings: BTreeMap<String, Binding>,
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
    rows: Vec<PriceRow>,
    input_mutation_controls: InputMutationControls,
    coefficient_plus_one_mutant: CoefficientPlusOneMutant,
    inputs_rehashed_at_end: bool,
    wall_seconds: f64,
}

struct ValidatedInputs {
    panel: PanelInput,
    candidate: Candidate,
    receipt: StageAReceipt,
    manifest: SharedManifest,
    custody: BTreeMap<String, String>,
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
    let strings = values.iter().map(ToString::to_string).collect::<Vec<_>>();
    decimal_lf_digest(strings.iter().map(String::as_str))
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
    ensure!(canonical_integer(raw), "noncanonical integer");
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
            && candidate.claim_boundary == CANDIDATE_CLAIM
            && candidate.rows == ROWS
            && candidate.records == RECORDS
            && candidate.rank == SELECTED_SLOTS
            && candidate.augmented_rank == SELECTED_SLOTS,
        "candidate identity drift"
    );
    ensure!(
        candidate.manifest_path == CANDIDATE_MANIFEST_PATH
            && candidate.manifest_sha256 == CANDIDATE_MANIFEST_SHA256
            && candidate.solver_sha256 == CANDIDATE_SOLVER_SHA256
            && candidate.audited_ancestor_sha256
                == "dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac",
        "candidate provenance drift"
    );
    ensure!(
        candidate.target_scale == TARGET_SCALE
            && canonical_positive_integer(&candidate.target_scale),
        "candidate target-scale drift"
    );
    ensure!(
        candidate.all_380_rows_replayed
            && candidate.coefficient_plus_one_mutant_rejected
            && candidate.prior_candidate_rejected_on_all_32_new_rows,
        "candidate exact-row controls are not green"
    );
    ensure!(
        candidate.maximum_rss_kib > 0
            && candidate.wall_seconds > 0.0
            && [
                &candidate.new_exact_residuals_decimal_lf_sha256,
                &candidate.new_selected_prefix_i8_u64_le_sha256,
                &candidate.old_batch_residuals_decimal_lf_sha256,
                &candidate.selected_basis_i128le_sha256,
            ]
            .into_iter()
            .all(|digest| canonical_sha256(digest)),
        "candidate resource or digest receipt drift"
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
            )?,
        "candidate term projection drift"
    );
    ensure!(
        candidate.terms.len() == TERMS,
        "candidate term census drift"
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
            .is_some_and(|term| term.sequence == 0),
        "candidate mutant anchor drift"
    );
    validate_strict_axis(
        &candidate.coordinate_rows,
        SELECTED_SLOTS,
        ROWS,
        "candidate coordinate-row axis",
    )?;
    ensure!(
        candidate.hinge_directions.len() == CARRY_DIRECTIONS,
        "candidate carry-direction census drift"
    );
    let mut carried = HashSet::new();
    for direction in &candidate.hinge_directions {
        validate_direction(direction)?;
        ensure!(
            carried.insert(*direction),
            "duplicate candidate carry direction"
        );
    }
    ensure!(candidate.trials.len() == 21, "candidate trial census drift");
    ensure!(
        candidate
            .trials
            .iter()
            .enumerate()
            .all(|(iteration, trial)| trial.iteration == iteration),
        "candidate trial order drift"
    );
    Ok(())
}

fn validate_selected(
    selected: &[ExactHinge],
    expected_direction_digest: &str,
    expected_residual_digest: &str,
    carried_directions: &[[i8; N]],
    require_g0134_first: bool,
) -> Result<()> {
    ensure!(selected.len() == K, "selected direction census drift");
    ensure!(
        selected
            .windows(2)
            .all(|window| window[0].direction < window[1].direction),
        "selected direction order/uniqueness drift"
    );
    let carried = carried_directions.iter().copied().collect::<BTreeSet<_>>();
    let mut seen = BTreeSet::new();
    for item in selected {
        validate_direction(&item.direction)?;
        ensure!(seen.insert(item.direction), "duplicate selected direction");
        ensure!(
            !carried.contains(&item.direction),
            "selected direction duplicates carried row"
        );
        ensure!(
            canonical_integer(&item.coefficient) && item.coefficient != "0",
            "selected residual is not canonical nonzero decimal"
        );
    }
    ensure!(
        selected_direction_digest(selected) == expected_direction_digest,
        "selected signed-byte digest drift"
    );
    ensure!(
        decimal_lf_digest(selected.iter().map(|item| item.coefficient.as_str()))
            == expected_residual_digest,
        "selected residual decimal-LF digest drift"
    );
    if require_g0134_first {
        let first = selected
            .first()
            .context("selected batch missing first row")?;
        ensure!(
            first.direction == EXPECTED_FIRST_DIRECTION
                && first.coefficient == EXPECTED_FIRST_COEFFICIENT,
            "G-0134 first residual drift"
        );
    }
    Ok(())
}

fn validate_mutation_control(control: &MutationControl, expected_name: &str) -> Result<()> {
    ensure!(
        control.name == expected_name
            && control.rejected
            && control.changed_from_unmutated
            && canonical_sha256(&control.unmutated_residual_decimal_lf_sha256)
            && canonical_sha256(&control.mutated_residual_decimal_lf_sha256)
            && control.unmutated_residual_decimal_lf_sha256
                != control.mutated_residual_decimal_lf_sha256
            && (control.first_nonzero_hinge.is_some() || control.first_nonzero_linear.is_some()),
        "Stage-A mutation control drift: {expected_name}"
    );
    Ok(())
}

fn validate_term_receipts(receipts: &[TermNormalFormReceipt], candidate: &Candidate) -> Result<()> {
    ensure!(receipts.len() == TERMS, "Stage-A term receipt census drift");
    let mut labelled = 0u64;
    for (receipt, term) in receipts.iter().zip(&candidate.terms) {
        ensure!(
            receipt.sequence == term.sequence
                && receipt.active_vertices <= N
                && !receipt.enumeration_mode.is_empty()
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
                && receipt.hinge_entries > 0
                && canonical_sha256(&receipt.normal_form_sha256)
                && receipt.scientific_coefficient_arithmetic == "signed_num_bigint_BigInt"
                && receipt.independent_exact_linear_crosscheck
                && receipt.bounded_pinned_kernel_crosscheck,
            "Stage-A term normal-form receipt drift at sequence {}",
            term.sequence
        );
        labelled = labelled
            .checked_add(receipt.accepted_labelled_permutations)
            .context("Stage-A term receipt census overflow")?;
    }
    ensure!(
        labelled == EXPECTED_LABELLED_PERMUTATIONS,
        "Stage-A labelled-permutation transcript drift"
    );
    Ok(())
}

fn validate_stage_a_receipt(
    receipt: &StageAReceipt,
    candidate: &Candidate,
    manifest: &SharedManifest,
    manifest_sha256: &str,
) -> Result<()> {
    ensure!(
        receipt.schema == STAGE_A_SCHEMA
            && receipt.result == STAGE_A_RESULT
            && !receipt.claim_boundary.is_empty()
            && receipt.manifest_path == SHARED_MANIFEST_PATH
            && receipt.manifest_sha256 == manifest_sha256
            && receipt.bindings == manifest.bindings,
        "Stage-A identity, manifest, or binding drift"
    );
    ensure!(
        receipt.candidate_schema == candidate.schema
            && receipt.candidate_result == candidate.result
            && receipt.target_scale == candidate.target_scale
            && parse_bigint(&receipt.target_subtraction_coordinate_10)?
                == parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N))
            && receipt.arithmetic == "signed_num_bigint_BigInt_unconditional_exact"
            && receipt.decision_rule
                == "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate"
            && receipt.screening_primes_control_only == SCREENING_PRIMES,
        "Stage-A candidate or arithmetic bridge drift"
    );
    ensure!(
        receipt.complete_global_replay
            && !receipt.all_hinge_and_linear_residuals_zero
            && receipt.terms == TERMS
            && receipt.hinge_entries_processed == EXPECTED_HINGE_ENTRIES_PROCESSED
            && receipt.labelled_permutations_checked == EXPECTED_LABELLED_PERMUTATIONS
            && receipt.aggregate_hinge_support == EXPECTED_AGGREGATE_HINGE_SUPPORT
            && receipt.nonzero_hinge_directions == EXPECTED_NONZERO_HINGE_DIRECTIONS
            && receipt.aggregate_hinge_decimal_lf_sha256 == EXPECTED_AGGREGATE_HINGE_SHA256
            && receipt.nonzero_hinge_decimal_lf_sha256 == EXPECTED_NONZERO_HINGE_SHA256
            && receipt.term_normal_form_transcript_sha256 == EXPECTED_TERM_TRANSCRIPT_SHA256
            && receipt.prior_g0132_reconciled
            && receipt.inputs_rehashed_at_end
            && receipt.wall_seconds > 0.0,
        "Stage-A exact G-0132 reconciliation drift"
    );
    validate_term_receipts(&receipt.term_normal_forms, candidate)?;
    ensure!(
        receipt.carry_forward_checks.len() == CARRY_DIRECTIONS
            && receipt.first_carry_forward_failure.is_none(),
        "Stage-A carry-forward census drift"
    );
    for (index, (check, direction)) in receipt
        .carry_forward_checks
        .iter()
        .zip(&candidate.hinge_directions)
        .enumerate()
    {
        ensure!(
            check.index == index
                && check.direction == *direction
                && check.coefficient == "0"
                && check.exact_zero,
            "Stage-A carried-row reconciliation drift at {index}"
        );
    }
    ensure!(
        receipt.linear_residuals_after_target.len() == N
            && receipt
                .linear_residuals_after_target
                .iter()
                .all(|value| value == "0")
            && receipt.first_nonzero_linear.is_none(),
        "Stage-A exact linear reconciliation drift"
    );
    let expected_first = ExactHinge {
        direction: EXPECTED_FIRST_DIRECTION,
        coefficient: EXPECTED_FIRST_COEFFICIENT.to_string(),
    };
    ensure!(
        receipt.first_nonzero_hinge.as_ref() == Some(&expected_first)
            && receipt.batch_k == K
            && receipt.selected_count == K,
        "Stage-A first residual or Batch32 census drift"
    );
    validate_selected(
        &receipt.selected,
        &receipt.selected_directions_i8_sha256,
        &receipt.selected_exact_residuals_decimal_lf_sha256,
        &candidate.hinge_directions,
        true,
    )?;
    let selection = &receipt.selection_controls;
    ensure!(
        selection.exact_batch_count
            && selection.strict_signed_lexicographic_order
            && selection.first_direction_matches_g0132
            && selection.first_coefficient_matches_g0132
            && selection.direction_reordering_changes_digest
            && selection.residual_plus_one_changes_digest,
        "Stage-A selection controls are not green"
    );
    for (control, name) in [
        (
            &receipt.first_coefficient_plus_one,
            "first_nonzero_coefficient_plus_one",
        ),
        (
            &receipt.final_coefficient_plus_one,
            "final_nonzero_coefficient_plus_one",
        ),
        (&receipt.target_scale_plus_one, "target_scale_plus_one"),
        (
            &receipt.target_coordinate_10_plus_one,
            "target_coordinate_10_plus_one",
        ),
        (&receipt.omitted_final_term, "omitted_final_nonzero_term"),
        (
            &receipt.omitted_first_term_active_direction,
            "omitted_first_term_active_direction",
        ),
        (
            &receipt.omitted_first_term_linear_coordinate,
            "omitted_first_term_linear_coordinate",
        ),
    ] {
        validate_mutation_control(control, name)?;
    }
    let census = &receipt.census_controls;
    ensure!(
        census.per_term_generated_equals_visited_equals_accepted
            && census.zero_skipped_unclassified_failed
            && census.omitted_final_term_rejected
            && census.omitted_last_orbit_contribution_rejected
            && census.omitted_active_direction_changed_terminal_residual
            && census.omitted_linear_coordinate_changed_terminal_residual
            && census.screening_prime_collision_found_exactly,
        "Stage-A census controls are not green"
    );
    Ok(())
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
        .with_context(|| format!("missing u64 at {pointer}"))
}

fn json_bool(value: &Value, pointer: &str) -> Result<bool> {
    value
        .pointer(pointer)
        .and_then(Value::as_bool)
        .with_context(|| format!("missing bool at {pointer}"))
}

fn json_direction(value: &Value, pointer: &str) -> Result<[i8; N]> {
    let raw = value
        .pointer(pointer)
        .and_then(Value::as_array)
        .with_context(|| format!("missing direction at {pointer}"))?;
    ensure!(raw.len() == N, "direction width drift at {pointer}");
    let coordinates = raw
        .iter()
        .map(|coordinate| {
            let coordinate = coordinate
                .as_i64()
                .context("direction coordinate is not i64")?;
            i8::try_from(coordinate).context("direction coordinate exceeds i8")
        })
        .collect::<Result<Vec<_>>>()?;
    coordinates
        .try_into()
        .map_err(|_| anyhow::anyhow!("direction width conversion failed"))
}

fn validate_immutable_ancestor_receipts(root: &Path) -> Result<()> {
    let g0132: Value = serde_json::from_reader(BufReader::new(File::open(checked_repo_path(
        root,
        G0132_RECEIPT_PATH,
    )?)?))?;
    ensure!(
        json_string(&g0132, "/schema")? == "max11-g0132-member-global-normal-form-replay-v1"
            && json_string(&g0132, "/result")? == "MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL"
            && json_u64(&g0132, "/terms")? == TERMS as u64
            && json_u64(&g0132, "/hinge_entries_processed")? == EXPECTED_HINGE_ENTRIES_PROCESSED
            && json_u64(&g0132, "/labelled_permutations_checked")?
                == EXPECTED_LABELLED_PERMUTATIONS
            && json_u64(&g0132, "/aggregate_hinge_support")?
                == EXPECTED_AGGREGATE_HINGE_SUPPORT as u64
            && json_u64(&g0132, "/nonzero_hinge_directions")?
                == EXPECTED_NONZERO_HINGE_DIRECTIONS as u64
            && json_direction(&g0132, "/first_nonzero_hinge/direction")?
                == EXPECTED_FIRST_DIRECTION
            && json_string(&g0132, "/first_nonzero_hinge/coefficient")?
                == EXPECTED_FIRST_COEFFICIENT
            && g0132
                .pointer("/first_nonzero_linear")
                .is_some_and(Value::is_null),
        "immutable G-0132 receipt drift"
    );

    let g0134: Value = serde_json::from_reader(BufReader::new(File::open(checked_repo_path(
        root,
        G0134_RECEIPT_PATH,
    )?)?))?;
    ensure!(
        json_string(&g0134, "/schema")? == "max11-g0134-cleanroom-residual-reprice-v1"
            && json_string(&g0134, "/verdict")? == "CONSISTENT_RESIDUAL"
            && json_string(&g0134, "/mode")? == "full"
            && json_u64(&g0134, "/terms")? == TERMS as u64
            && json_u64(&g0134, "/labelled_permutations_reconciled")?
                == EXPECTED_LABELLED_PERMUTATIONS
            && json_bool(&g0134, "/exact_match")?
            && json_bool(&g0134, "/nonzero")?
            && json_string(&g0134, "/lexicographic_first")? == "VERIFIED"
            && json_direction(&g0134, "/direction")? == EXPECTED_FIRST_DIRECTION
            && json_string(&g0134, "/independent_coefficient")? == EXPECTED_FIRST_COEFFICIENT
            && json_string(&g0134, "/reported_coefficient")? == EXPECTED_FIRST_COEFFICIENT
            && json_string(&g0134, "/target_scale")? == TARGET_SCALE,
        "immutable G-0134 result audit drift"
    );
    Ok(())
}

fn validate_compiled_and_static(root: &Path) -> Result<()> {
    for (raw, compiled) in [
        (STAGE_B_SOURCE_PATH, COMPILED_SOURCE),
        (STAGE_B_CARGO_MANIFEST_PATH, COMPILED_MANIFEST),
        (STAGE_B_CARGO_LOCK_PATH, COMPILED_LOCK),
    ] {
        ensure!(
            sha256_path(&checked_repo_path(root, raw)?)? == sha256_bytes(compiled),
            "running binary was compiled from different bytes: {raw}"
        );
    }
    for (raw, expected, compiled) in [
        (
            G0135_PREREGISTRATION_PATH,
            G0135_PREREGISTRATION_SHA256,
            COMPILED_PREREGISTRATION,
        ),
        (CANDIDATE_PATH, CANDIDATE_SHA256, COMPILED_CANDIDATE),
        (KERNEL_PATH, KERNEL_SHA256, COMPILED_KERNEL),
        (
            G0132_RECEIPT_PATH,
            G0132_RECEIPT_SHA256,
            COMPILED_G0132_RECEIPT,
        ),
        (
            G0134_RECEIPT_PATH,
            G0134_RECEIPT_SHA256,
            COMPILED_G0134_RECEIPT,
        ),
        (
            G0127_SOURCE_PATH,
            G0127_SOURCE_SHA256,
            COMPILED_G0127_SOURCE,
        ),
    ] {
        ensure!(
            sha256_bytes(compiled) == expected
                && sha256_path(&checked_repo_path(root, raw)?)? == expected,
            "immutable compiled binding drift: {raw}"
        );
    }
    make_expected_binding(root, PANEL_INPUT_PATH, PANEL_INPUT_SHA256)?;
    make_expected_binding(root, CANDIDATE_MANIFEST_PATH, CANDIDATE_MANIFEST_SHA256)?;
    make_expected_binding(root, CANDIDATE_SOLVER_PATH, CANDIDATE_SOLVER_SHA256)?;
    make_expected_binding(root, G0132_MANIFEST_PATH, G0132_MANIFEST_SHA256)?;
    make_expected_binding(root, G0127_RECEIPT_PATH, G0127_RECEIPT_SHA256)?;
    validate_immutable_ancestor_receipts(root)
}

fn validate_git_hash(raw: &str, name: &str) -> Result<()> {
    ensure!(
        raw.len() == 40 && raw.bytes().all(|byte| byte.is_ascii_hexdigit()),
        "invalid {name} Git commit"
    );
    Ok(())
}

fn manifest_binding<'a>(manifest: &'a SharedManifest, raw: &str) -> Option<&'a Binding> {
    manifest
        .bindings
        .values()
        .chain(manifest.transitive_inputs.iter())
        .find(|binding| binding.path == raw)
}

fn validate_manifest_bindings(root: &Path, manifest: &SharedManifest) -> Result<()> {
    let mut paths = HashSet::new();
    for (label, binding) in &manifest.bindings {
        ensure!(!label.trim().is_empty(), "empty manifest binding label");
        ensure!(
            canonical_sha256(&binding.sha256),
            "noncanonical manifest binding digest: {label}"
        );
        let resolved = checked_repo_path(root, &binding.path)?;
        ensure!(
            paths.insert(resolved),
            "duplicate resolved manifest binding"
        );
        ensure!(
            sha256_path(&checked_repo_path(root, &binding.path)?)? == binding.sha256,
            "manifest binding drift: {label}"
        );
    }
    for binding in &manifest.transitive_inputs {
        ensure!(
            canonical_sha256(&binding.sha256),
            "noncanonical transitive binding digest"
        );
        let resolved = checked_repo_path(root, &binding.path)?;
        ensure!(
            paths.insert(resolved),
            "duplicate resolved transitive binding"
        );
        ensure!(
            sha256_path(&checked_repo_path(root, &binding.path)?)? == binding.sha256,
            "transitive binding drift: {}",
            binding.path
        );
    }
    Ok(())
}

fn validate_shared_manifest(
    root: &Path,
    manifest: &SharedManifest,
    receipt: &StageAReceipt,
) -> Result<()> {
    ensure!(
        manifest.schema == SHARED_MANIFEST_SCHEMA
            && manifest.selected_branch == "MEMBER"
            && manifest.output_path == STAGE_A_RECEIPT_PATH,
        "shared manifest identity drift"
    );
    validate_git_hash(
        &manifest.preregistration_git_commit,
        "manifest preregistration",
    )?;
    validate_git_hash(&manifest.producer_git_commit, "Stage-A producer")?;
    validate_git_hash(&manifest.source_audit_git_commit, "source audit")?;
    ensure!(
        manifest.stage_order
            == [
                "A_REPLAY_SELECT",
                "B_PRICE",
                "C_MASTER",
                "D_GLOBAL_REPLAY_IF_MEMBER",
            ],
        "shared-manifest stage order drift"
    );
    let planned_b = manifest
        .planned_outputs
        .get("B")
        .context("shared manifest has no planned Stage-B output")?;
    ensure!(
        json_string(planned_b, "/path")? == OUTPUT_PATH
            && json_string(planned_b, "/schema")? == OUTPUT_SCHEMA,
        "shared-manifest Stage-B output contract drift"
    );
    let parameters = &manifest.parameters;
    ensure!(
        parameters.n == N
            && parameters.rows == ROWS
            && parameters.records == RECORDS
            && parameters.terms == TERMS
            && parameters.batch_k == K
            && parameters.selected_slots == SELECTED_SLOTS
            && parameters.carry_directions == CARRY_DIRECTIONS
            && parameters.target_coordinate == N - 1
            && parameters.labelled_permutations == EXPECTED_LABELLED_PERMUTATIONS
            && parameters.threads == THREADS
            && parameters.arithmetic == "signed_num_bigint_BigInt_unconditional_exact"
            && parameters.decision_rule
                == "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate",
        "shared-manifest parameter drift"
    );
    ensure!(
        !manifest.environment.os.is_empty()
            && !manifest.environment.arch.is_empty()
            && !manifest.environment.rustc_verbose.is_empty()
            && manifest.environment.available_parallelism > 0,
        "shared-manifest environment drift"
    );
    validate_manifest_bindings(root, manifest)?;
    ensure!(
        receipt.bindings == manifest.bindings,
        "Stage-A receipt does not carry every direct manifest binding"
    );

    let executable = relative_executable(root)?;
    for required in [
        STAGE_A_SOURCE_PATH,
        STAGE_B_SOURCE_PATH,
        STAGE_B_CARGO_MANIFEST_PATH,
        STAGE_B_CARGO_LOCK_PATH,
        G0135_PREREGISTRATION_PATH,
        PANEL_INPUT_PATH,
        CANDIDATE_PATH,
        CANDIDATE_MANIFEST_PATH,
        CANDIDATE_SOLVER_PATH,
        KERNEL_PATH,
        G0132_RECEIPT_PATH,
        G0132_MANIFEST_PATH,
        G0134_RECEIPT_PATH,
        G0127_SOURCE_PATH,
        G0127_RECEIPT_PATH,
        executable.as_str(),
    ] {
        let binding = manifest_binding(manifest, required)
            .with_context(|| format!("shared manifest missing required binding: {required}"))?;
        ensure!(
            sha256_path(&checked_repo_path(root, required)?)? == binding.sha256,
            "required shared-manifest binding drift: {required}"
        );
    }
    Ok(())
}

fn snapshot_insert(
    snapshot: &mut BTreeMap<String, String>,
    path: String,
    sha256: String,
) -> Result<()> {
    if let Some(previous) = snapshot.insert(path.clone(), sha256.clone()) {
        ensure!(previous == sha256, "conflicting custody digest for {path}");
    }
    Ok(())
}

fn custody_snapshot(
    root: &Path,
    manifest: &SharedManifest,
    manifest_sha256: &str,
    stage_a_sha256: &str,
) -> Result<BTreeMap<String, String>> {
    let mut snapshot = BTreeMap::new();
    snapshot_insert(
        &mut snapshot,
        SHARED_MANIFEST_PATH.to_string(),
        manifest_sha256.to_string(),
    )?;
    snapshot_insert(
        &mut snapshot,
        STAGE_A_RECEIPT_PATH.to_string(),
        stage_a_sha256.to_string(),
    )?;
    for binding in manifest
        .bindings
        .values()
        .chain(manifest.transitive_inputs.iter())
    {
        snapshot_insert(&mut snapshot, binding.path.clone(), binding.sha256.clone())?;
    }
    for raw in [
        PANEL_INPUT_PATH,
        CANDIDATE_PATH,
        CANDIDATE_MANIFEST_PATH,
        CANDIDATE_SOLVER_PATH,
        STAGE_B_SOURCE_PATH,
        STAGE_B_CARGO_MANIFEST_PATH,
        STAGE_B_CARGO_LOCK_PATH,
        G0135_PREREGISTRATION_PATH,
        KERNEL_PATH,
        G0132_RECEIPT_PATH,
        G0132_MANIFEST_PATH,
        G0134_RECEIPT_PATH,
        G0127_SOURCE_PATH,
        G0127_RECEIPT_PATH,
    ] {
        snapshot_insert(
            &mut snapshot,
            raw.to_string(),
            sha256_path(&checked_repo_path(root, raw)?)?,
        )?;
    }
    let executable = relative_executable(root)?;
    snapshot_insert(
        &mut snapshot,
        executable.clone(),
        sha256_path(&checked_repo_path(root, &executable)?)?,
    )?;
    Ok(snapshot)
}

fn load_static_inputs(
    root: &Path,
    input_path: &Path,
    candidate_path: &Path,
) -> Result<(PanelInput, Candidate)> {
    ensure!(
        input_path == Path::new(PANEL_INPUT_PATH),
        "panel path drift"
    );
    ensure!(
        candidate_path == Path::new(CANDIDATE_PATH),
        "candidate path drift"
    );
    validate_compiled_and_static(root)?;
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(
        checked_repo_path(root, PANEL_INPUT_PATH)?,
    )?))?;
    let candidate: Candidate = serde_json::from_reader(BufReader::new(File::open(
        checked_repo_path(root, CANDIDATE_PATH)?,
    )?))?;
    validate_panel(&input)?;
    validate_candidate(&candidate)?;
    Ok((input, candidate))
}

fn load_and_validate_inputs(
    root: &Path,
    input_path: &Path,
    receipt_path: &Path,
    candidate_path: &Path,
    manifest_path: &Path,
) -> Result<ValidatedInputs> {
    ensure!(
        receipt_path == Path::new(STAGE_A_RECEIPT_PATH),
        "Stage-A receipt path drift"
    );
    ensure!(
        manifest_path == Path::new(SHARED_MANIFEST_PATH),
        "shared manifest path drift"
    );
    let (panel, candidate) = load_static_inputs(root, input_path, candidate_path)?;
    let manifest_resolved = checked_repo_path(root, SHARED_MANIFEST_PATH)?;
    let receipt_resolved = checked_repo_path(root, STAGE_A_RECEIPT_PATH)?;
    let manifest_sha256 = sha256_path(&manifest_resolved)?;
    let stage_a_sha256 = sha256_path(&receipt_resolved)?;
    let manifest: SharedManifest =
        serde_json::from_reader(BufReader::new(File::open(manifest_resolved)?))?;
    let receipt: StageAReceipt =
        serde_json::from_reader(BufReader::new(File::open(receipt_resolved)?))?;
    validate_shared_manifest(root, &manifest, &receipt)?;
    validate_stage_a_receipt(&receipt, &candidate, &manifest, &manifest_sha256)?;
    let custody = custody_snapshot(root, &manifest, &manifest_sha256, &stage_a_sha256)?;
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
    candidate: &Candidate,
) -> Result<InputMutationControls> {
    let validate = |selected: &[ExactHinge]| {
        validate_selected(
            selected,
            &receipt.selected_directions_i8_sha256,
            &receipt.selected_exact_residuals_decimal_lf_sha256,
            &candidate.hinge_directions,
            true,
        )
    };

    let mut count_mutant = receipt.selected.clone();
    count_mutant.pop();
    let selected_count_mutant_rejected = validate(&count_mutant).is_err();

    let mut order_mutant = receipt.selected.clone();
    order_mutant.swap(0, 1);
    let selection_order_mutant_rejected = validate(&order_mutant).is_err();

    let mut duplicate_mutant = receipt.selected.clone();
    duplicate_mutant[1] = duplicate_mutant[0].clone();
    let selection_duplicate_mutant_rejected = validate(&duplicate_mutant).is_err();

    let mut invalid_direction_mutant = receipt.selected.clone();
    for coordinate in &mut invalid_direction_mutant[0].direction {
        *coordinate = -*coordinate;
    }
    let direction_invalidity_mutant_rejected = validate(&invalid_direction_mutant).is_err();

    let mut residual_mutant = receipt.selected.clone();
    residual_mutant[0].coefficient =
        (parse_bigint(&residual_mutant[0].coefficient)? + BigInt::from(1)).to_string();
    let residual_plus_one_mutant_rejected = validate(&residual_mutant).is_err();

    let record_census_truncation_rejected = validate_record_axis(
        records[..records.len() - 1]
            .iter()
            .map(|record| record.sequence),
        RECORDS,
    )
    .is_err();
    let record_order_mutant_rejected = validate_record_axis(
        records
            .iter()
            .enumerate()
            .map(|(index, record)| match index {
                0 => records[1].sequence,
                1 => records[0].sequence,
                _ => record.sequence,
            }),
        RECORDS,
    )
    .is_err();
    let all_rejected = selected_count_mutant_rejected
        && selection_order_mutant_rejected
        && selection_duplicate_mutant_rejected
        && direction_invalidity_mutant_rejected
        && residual_plus_one_mutant_rejected
        && record_census_truncation_rejected
        && record_order_mutant_rejected;
    ensure!(all_rejected, "Stage-B input mutation control escaped");
    Ok(InputMutationControls {
        selected_count_mutant_rejected,
        selection_order_mutant_rejected,
        selection_duplicate_mutant_rejected,
        direction_invalidity_mutant_rejected,
        residual_plus_one_mutant_rejected,
        record_census_truncation_rejected,
        record_order_mutant_rejected,
        all_rejected,
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
        serde_json::from_str::<Term>(r#"{"sequence":0,"coefficient":"1","extra":2}"#).is_err(),
        "unknown term field accepted"
    );

    let transposed = transpose_record_major(vec![vec![1, 2, 3], vec![4, 5, 6]], 3)?;
    ensure!(
        transposed == vec![vec![1, 4], vec![2, 5], vec![3, 6]],
        "direction-major transpose drift"
    );
    ensure!(
        transpose_record_major(vec![vec![1], vec![2, 3]], 2).is_err(),
        "coordinate census mutant escaped"
    );
    let signed = [1i64, -2, 3];
    let reordered = [1i64, 3, -2];
    let sign_mutant = [1i64, 2, 3];
    ensure!(
        digest_i64(signed.iter()) != digest_i64(reordered.iter())
            && digest_i64(signed.iter()) != digest_i64(sign_mutant.iter()),
        "signed i64 stream mutant escaped"
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
        "known-answer normal form lacks Batch32 support"
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
        "audited hinge kernel/full-normal-form bridge drift"
    );

    let selected = directions[..K]
        .iter()
        .enumerate()
        .map(|(index, direction)| ExactHinge {
            direction: *direction,
            coefficient: (index + 1).to_string(),
        })
        .collect::<Vec<_>>();
    let direction_digest = selected_direction_digest(&selected);
    let residual_digest = decimal_lf_digest(selected.iter().map(|item| item.coefficient.as_str()));
    validate_selected(&selected, &direction_digest, &residual_digest, &[], false)?;

    let mut count_mutant = selected.clone();
    count_mutant.pop();
    let mut order_mutant = selected.clone();
    order_mutant.swap(0, 1);
    let mut duplicate_mutant = selected.clone();
    duplicate_mutant[1] = duplicate_mutant[0].clone();
    let mut direction_mutant = selected.clone();
    for coordinate in &mut direction_mutant[0].direction {
        *coordinate = -*coordinate;
    }
    let mut residual_mutant = selected.clone();
    residual_mutant[0].coefficient = "2".to_string();
    ensure!(
        validate_selected(
            &count_mutant,
            &direction_digest,
            &residual_digest,
            &[],
            false
        )
        .is_err()
            && validate_selected(
                &order_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false
            )
            .is_err()
            && validate_selected(
                &duplicate_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false,
            )
            .is_err()
            && validate_selected(
                &direction_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false,
            )
            .is_err()
            && validate_selected(
                &residual_mutant,
                &direction_digest,
                &residual_digest,
                &[],
                false,
            )
            .is_err(),
        "selection/order/direction/residual mutant escaped"
    );

    ensure!(
        validate_record_axis([0, 1, 2], 3).is_ok()
            && validate_record_axis([0, 1], 3).is_err()
            && validate_record_axis([1, 0, 2], 3).is_err(),
        "record census/order mutant escaped"
    );
    let terms = vec![(0usize, BigInt::from(7)), (2usize, BigInt::from(-3))];
    let row = [5i64, 11, -2];
    let dot = exact_dot(&row, &terms);
    let coefficient_mutant = &dot + BigInt::from(row[0]);
    ensure!(
        dot != coefficient_mutant,
        "coefficient-plus-one mutant escaped"
    );
    ensure!(
        decimal_lf_digest(["1", "-2"].into_iter()) != decimal_lf_digest(["1", "-1"].into_iter()),
        "decimal-LF residual mutant escaped"
    );

    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0135-stage-b-publish-self-test-{}-{unique}",
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
        "G-0135 Stage-B static preflight PASS: {} records; {} candidate terms; future Stage-A receipt not consumed",
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
    let controls =
        make_input_mutation_controls(&inputs.panel.records, &inputs.receipt, &inputs.candidate)?;
    ensure!(controls.all_rejected, "preflight mutation-control drift");
    println!(
        "G-0135 Stage-B preflight PASS: {} records; {} selected directions; all shared-manifest bindings verified",
        inputs.panel.records.len(),
        inputs.receipt.selected.len()
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
        make_input_mutation_controls(&inputs.panel.records, &inputs.receipt, &inputs.candidate)?;
    let directions = inputs
        .receipt
        .selected
        .iter()
        .map(|item| item.direction)
        .collect::<Vec<_>>();
    ensure!(directions.len() == K, "pricing direction census drift");

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
        "exact coordinate dimensions drift"
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
        .zip(&inputs.receipt.selected)
        .enumerate()
    {
        ensure!(
            canonical_integer(dot) && dot != "0" && dot == &selected.coefficient,
            "exact candidate dot disagrees with Stage-A residual at row {index}"
        );
    }
    let exact_dot_digest = decimal_lf_digest(exact_dot_strings.iter().map(String::as_str));
    ensure!(
        exact_dot_digest == inputs.receipt.selected_exact_residuals_decimal_lf_sha256,
        "exact candidate-dot decimal-LF digest drift"
    );

    let mutant_term = inputs
        .candidate
        .terms
        .iter()
        .find(|term| direction_major.iter().any(|row| row[term.sequence] != 0))
        .context("no candidate coefficient can exercise a selected Stage-B row")?;
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
    let coefficient_mutant_rejected = changed_rows > 0 && mutant_dot_digest != exact_dot_digest;
    ensure!(
        coefficient_mutant_rejected,
        "candidate coefficient-plus-one mutant survived"
    );
    let coefficient_plus_one_mutant = CoefficientPlusOneMutant {
        sequence: mutant_term.sequence,
        coefficient_delta: "+1",
        baseline_exact_dots_decimal_lf_sha256: exact_dot_digest.clone(),
        mutated_exact_dots_decimal_lf_sha256: mutant_dot_digest,
        changed_rows,
        rejected: coefficient_mutant_rejected,
    };

    let rows = inputs
        .receipt
        .selected
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

    validate_manifest_bindings(&root, &inputs.manifest)?;
    let manifest_sha_end = sha256_path(&checked_repo_path(&root, SHARED_MANIFEST_PATH)?)?;
    let stage_a_sha_end = sha256_path(&checked_repo_path(&root, STAGE_A_RECEIPT_PATH)?)?;
    let custody_end =
        custody_snapshot(&root, &inputs.manifest, &manifest_sha_end, &stage_a_sha_end)?;
    ensure!(
        inputs.custody == custody_end,
        "input/source custody drift during Stage-B pricing"
    );
    let manifest_sha256 = inputs
        .custody
        .get(SHARED_MANIFEST_PATH)
        .context("manifest missing from custody snapshot")?
        .clone();
    let stage_a_receipt = make_binding(&root, STAGE_A_RECEIPT_PATH)?;
    let candidate_binding = make_expected_binding(&root, CANDIDATE_PATH, CANDIDATE_SHA256)?;
    let output = Output {
        schema: OUTPUT_SCHEMA,
        result: OUTPUT_RESULT,
        claim_boundary: OUTPUT_CLAIM,
        manifest_path: SHARED_MANIFEST_PATH,
        manifest_sha256,
        bindings: inputs.manifest.bindings.clone(),
        stage_a_receipt,
        candidate: candidate_binding,
        batch_k: K,
        records: RECORDS,
        hinge_entries: HINGE_ENTRIES,
        selected_count: K,
        selected_directions_i8_sha256: inputs.receipt.selected_directions_i8_sha256.clone(),
        selected_exact_residuals_decimal_lf_sha256: inputs
            .receipt
            .selected_exact_residuals_decimal_lf_sha256
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
        "selected_count": output.selected_count,
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
        println!("G-0135 Stage-B self-test PASS");
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
        "usage: g0135-stage-b-batch32-coordinate-pricer --self-test | --preflight-static PANEL CANDIDATE | --preflight PANEL STAGE_A_RECEIPT CANDIDATE SHARED_MANIFEST | PANEL STAGE_A_RECEIPT CANDIDATE SHARED_MANIFEST OUTPUT"
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
        assert_eq!(HINGE_ENTRIES, 5_239_680);
        assert_eq!(HINGE_ENTRIES, K.checked_mul(RECORDS).unwrap());
    }

    #[test]
    fn arbitrary_precision_dot_does_not_narrow() {
        let huge = parse_bigint(
            "363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360",
        )
        .unwrap();
        let row = [i64::MAX, i64::MIN + 1];
        let terms = [(0usize, huge.clone()), (1usize, -huge)];
        let dot = exact_dot(&row, &terms);
        assert!(dot.to_string().len() > 150);
    }
}
