use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{
    N, Record, full_normal_form, hinge_coefficients, linear_vector, validate_direction,
};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const K: usize = 32;
const RECORDS: usize = 163_740;
const TERMS: usize = 131;
const HINGE_ENTRIES: usize = K * RECORDS;
const LINEAR_ENTRIES: usize = RECORDS * N;
const PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];
const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const RECEIPT_SHA256: &str = "bd0410d861978956502e9d4c4fc1cd159565f2e170d70509abd0f3eb21b771ea";
const CANDIDATE_SHA256: &str = "53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036";
const KERNEL_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";
const G0126_PREREG_SHA256: &str =
    "d6dd969ae558c7e36eb420c1fa4fa2c1254875eeff073b8580809b6a50a2fadb";
const G0126_SOURCE_SHA256: &str =
    "a59f51ed491d50fb8d8e3e93e1a0f53dbc351a67a84fc2ae1f51bd18f74991f3";
const G0126_EXECUTABLE_SHA256: &str =
    "ae7f64ce737d8f12d9f4a3d5695fe8ded4b5a89720eff8a0f5a537b2126bfa28";
const ANCESTOR_SOURCE_SHA256: &str =
    "35cabc07a3e6a50366c584c737493b393b202092d64f0951a37dde4f515d3058";
const ANCESTOR_REVIEW_SHA256: &str =
    "e7905d258ed05e004c51b449494c9cd7094e967cdf3c29380646f55caaf2b569";
const SELECTED_SHA256: &str = "0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e";
const EXACT_RESIDUALS_SHA256: &str =
    "000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b";
const EXPECTED_LINEAR_SHA256: &str =
    "84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51";
const TARGET_SCALE: &str = "264010886084977103415797420761461511057729096350532822171032655262573576673600959905395014217297467347581921316792637811198651042601200900728134005150";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] =
    include_bytes!("../BATCH32_COORDINATE_PRICING_PREREGISTRATION.md");
const COMPILED_RECEIPT: &[u8] = include_bytes!("../../G-0126/global_replay_v1.json");
const COMPILED_CANDIDATE: &[u8] = include_bytes!("../../G-0121/full_family_master_result_v1.json");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../G-0117/src/lib.rs");
const COMPILED_G0126_PREREGISTRATION: &[u8] =
    include_bytes!("../../G-0126/GLOBAL_REPLAY_PREREGISTRATION.md");
const COMPILED_G0126_SOURCE: &[u8] = include_bytes!("../../G-0126/src/main.rs");
const COMPILED_ANCESTOR_SOURCE: &[u8] =
    include_bytes!("../../G-0117/src/bin/g0118_batch_coordinate_pricer.rs");
const COMPILED_ANCESTOR_REVIEW: &[u8] =
    include_bytes!("../../../reviews/G-0118-iteration4-batch/review_v1.json");

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
    all_rows_replayed: bool,
    batch_exact_residuals_decimal_lf_sha256: String,
    claim_boundary: String,
    coefficient_plus_one_mutant_rejected: bool,
    coordinate_rows: Vec<usize>,
    hinge_directions: Vec<[i8; N]>,
    integer_coefficients: Vec<String>,
    manifest_path: String,
    manifest_sha256: String,
    maximum_rss_kib: u64,
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
    trials: Vec<Value>,
    wall_seconds: f64,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct Residual {
    direction: [i8; N],
    residues: [u64; 2],
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CarryForwardCheck {
    index: usize,
    direction: [i8; N],
    residues: [u64; 2],
    zero_in_both_fields: bool,
}

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactPriceReceipt {
    direction: [i8; N],
    modular_residues: [u64; 2],
    exact_residual: String,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ExactReplayReceipt {
    performed: bool,
    result: String,
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_directions: usize,
    first_nonzero_hinge: Option<Value>,
    linear_residuals_after_target: Vec<String>,
    first_nonzero_linear: Option<Value>,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ReceiptMutant {
    sequence: usize,
    coefficient_delta: String,
    carry_forward_residues_match: bool,
    linear_residues_match: bool,
    nonzero_hinge_count_matches: bool,
    selected_prefix_matches: bool,
    rejected: bool,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ReplayReceipt {
    schema: String,
    result: String,
    claim_boundary: String,
    bindings: BTreeMap<String, String>,
    candidate_schema: String,
    candidate_result: String,
    target_scale: String,
    primes: [u64; 2],
    batch_k: usize,
    selection_rule: String,
    complete_global_replay: bool,
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_residue_directions: usize,
    carry_forward_checks: Vec<CarryForwardCheck>,
    first_carry_forward_failure: Option<usize>,
    linear_residues_after_target: [[u64; N]; 2],
    all_hinge_and_linear_residues_zero: [bool; 2],
    selected_count: usize,
    selected_prefix_i8_u64_le_sha256: String,
    selected: Vec<Residual>,
    exact_selected_prices_decimal_lf_sha256: String,
    exact_selected_prices: Vec<ExactPriceReceipt>,
    first_nonzero_linear: Option<Value>,
    exact_replay: ExactReplayReceipt,
    coefficient_plus_one_mutant: ReceiptMutant,
    wall_seconds: f64,
}

#[derive(Serialize)]
struct PriceRow {
    direction: [i8; N],
    modular_residues: [u64; 2],
    records: usize,
    nonzero_hinge_coefficients: usize,
    minimum_hinge_coefficient: i64,
    maximum_hinge_coefficient: i64,
    maximum_absolute_hinge_coefficient: u64,
    hinge_coefficients_i64_le_sha256: String,
    exact_candidate_residual: String,
    hinge_coefficients: Vec<i64>,
}

#[derive(Serialize)]
struct MutantControl {
    sequence: usize,
    coefficient_delta: &'static str,
    hinge_dot_receipt_changed: bool,
    linear_dot_receipt_changed: bool,
    rejected: bool,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    batch_k: usize,
    records: usize,
    hinge_entries: usize,
    linear_entries: usize,
    selected_count: usize,
    selected_prefix_i8_u64_le_sha256: String,
    directions: Vec<[i8; N]>,
    modular_residues: Vec<[u64; 2]>,
    direction_major_hinge_i64_le_sha256: String,
    linear_vectors_i64_le_sha256: String,
    exact_candidate_residuals_decimal_lf_sha256: String,
    exact_candidate_residuals: Vec<String>,
    exact_candidate_linear_dots: Vec<String>,
    rows: Vec<PriceRow>,
    linear_vectors: Vec<[i64; N]>,
    coefficient_plus_one_mutant: MutantControl,
    wall_seconds: f64,
}

fn factorial(value: usize) -> u64 {
    (1..=value as u64).product()
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut source = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 16];
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

fn digest_i64<'a>(values: impl Iterator<Item = &'a i64>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn digest_selected(selected: &[Residual]) -> String {
    let mut digest = Sha256::new();
    for residual in selected {
        for coordinate in residual.direction {
            digest.update(coordinate.to_le_bytes());
        }
        for residue in residual.residues {
            digest.update(residue.to_le_bytes());
        }
    }
    format!("{:x}", digest.finalize())
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

fn publish_exclusive(path: &Path, bytes: &[u8]) -> Result<()> {
    ensure!(!path.exists(), "refusing to overwrite output");
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
    std::fs::remove_file(&temporary).context("remove exclusive temporary output link")?;
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

fn validate_candidate(candidate: &Candidate) -> Result<()> {
    ensure!(
        candidate.schema == "max11-g0121-full-family-master-result-v1"
            && candidate.result == "FULL_FAMILY_EXACT_Q_MEMBER"
            && candidate.claim_boundary
                == "Exact membership only on the frozen 348-row system over the frozen 163,740-column family; a finite-row candidate for separate complete global replay, not a family-completeness theorem or MAX11 result."
            && candidate.rows == 348
            && candidate.records == RECORDS,
        "candidate identity drift"
    );
    ensure!(
        candidate.target_scale == TARGET_SCALE
            && canonical_positive_integer(&candidate.target_scale),
        "candidate target scale drift"
    );
    ensure!(
        candidate.all_rows_replayed && candidate.coefficient_plus_one_mutant_rejected,
        "candidate row controls are not green"
    );
    ensure!(
        candidate.terms.len() == TERMS,
        "candidate term census drift"
    );
    ensure!(
        candidate.terms
            == nonzero_term_projection(
                &candidate.support_sequences,
                &candidate.integer_coefficients,
            )?,
        "candidate term projection drift"
    );
    let mut previous = None;
    for term in &candidate.terms {
        ensure!(term.sequence < RECORDS, "term sequence outside family");
        ensure!(
            term.sequence <= 141,
            "nonzero term outside frozen 0..141 support"
        );
        ensure!(
            previous.is_none_or(|value| term.sequence > value),
            "term order/uniqueness drift"
        );
        ensure!(
            canonical_integer(&term.coefficient) && term.coefficient != "0",
            "candidate coefficient drift"
        );
        previous = Some(term.sequence);
    }
    ensure!(
        candidate
            .terms
            .first()
            .is_some_and(|term| term.sequence == 0),
        "coefficient mutant anchor drift"
    );
    Ok(())
}

fn validate_receipt(receipt: &ReplayReceipt, candidate: &Candidate) -> Result<()> {
    ensure!(
        receipt.schema == "max11-g0126-global-replay-v1"
            && receipt.result == "GLOBAL_MODULAR_RESIDUAL"
            && receipt.claim_boundary
                == "A modular or exact nonzero residual refutes only the bound 131-term candidate. Exact global zero would establish the frozen symmetric orbit identity, pending independent replay and architecture compilation; no result proves family completeness, an unrestricted lower bound, induction, or a Lean theorem.",
        "G-0126 receipt identity drift"
    );
    ensure!(
        receipt.bindings.len() == 12,
        "G-0126 binding-key census drift"
    );
    for (key, expected) in [
        ("candidate", CANDIDATE_SHA256),
        ("panel_input", INPUT_SHA256),
        ("producer", G0126_SOURCE_SHA256),
        ("executable", G0126_EXECUTABLE_SHA256),
        ("kernel", KERNEL_SHA256),
        ("preregistration", G0126_PREREG_SHA256),
        (
            "cargo_lock",
            "316421f8f8907349b9fb9b54a10ebe6bd4c3d4ddb9b44bc0294ff382f96dd45f",
        ),
        (
            "cargo_manifest",
            "14300697a23f010c349bcd2581f62ce85f1efa3b5a759c70d94b7894a8dedb6a",
        ),
        (
            "master_manifest",
            "9234415af8719ea0f46eaf7952d76cab006afe44e4d7e111813fde61e4a5032c",
        ),
        (
            "master_solver",
            "dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac",
        ),
        (
            "normal_form_uniqueness",
            "39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17",
        ),
        (
            "output_protocol",
            "pre-serialized_same-directory_O_EXCL_temp_then_atomic_no-overwrite_hard-link_after_all_controls_and_end_binding_recheck",
        ),
    ] {
        ensure!(
            receipt.bindings.get(key).map(String::as_str) == Some(expected),
            "G-0126 {key} binding drift"
        );
    }
    ensure!(
        receipt.candidate_schema == candidate.schema
            && receipt.candidate_result == candidate.result
            && receipt.target_scale == candidate.target_scale
            && receipt.primes == PRIMES
            && receipt.batch_k == K
            && receipt.complete_global_replay
            && receipt.terms == TERMS
            && receipt.hinge_entries_processed == 4_667_940
            && receipt.labelled_permutations_checked == 5_229_100_800
            && receipt.aggregate_hinge_support == 178_145
            && receipt.nonzero_hinge_residue_directions == 178_040,
        "G-0126 replay census/protocol drift"
    );
    ensure!(
        receipt.carry_forward_checks.len() == candidate.hinge_directions.len()
            && receipt
                .carry_forward_checks
                .iter()
                .zip(&candidate.hinge_directions)
                .enumerate()
                .all(|(index, (check, direction))| {
                    check.index == index
                        && check.direction == *direction
                        && check.residues == [0, 0]
                        && check.zero_in_both_fields
                })
            && receipt.first_carry_forward_failure.is_none(),
        "G-0126 carry-forward receipt drift"
    );
    ensure!(
        receipt.linear_residues_after_target == [[0; N]; 2]
            && receipt.all_hinge_and_linear_residues_zero == [false, false]
            && receipt.first_nonzero_linear.is_none(),
        "G-0126 linear receipt drift"
    );
    ensure!(
        receipt.selected_count == K
            && receipt.selected.len() == K
            && receipt.exact_selected_prices.len() == K
            && receipt.selected_prefix_i8_u64_le_sha256 == SELECTED_SHA256
            && digest_selected(&receipt.selected) == SELECTED_SHA256,
        "G-0126 selected census/digest drift"
    );
    let directions = receipt
        .selected
        .iter()
        .map(|residual| residual.direction)
        .collect::<Vec<_>>();
    ensure!(
        directions.windows(2).all(|window| window[0] < window[1])
            && directions.iter().copied().collect::<BTreeSet<_>>().len() == K,
        "G-0126 selected order/uniqueness drift"
    );
    for residual in &receipt.selected {
        validate_direction(&residual.direction)?;
        ensure!(residual.residues != [0, 0], "selected zero residue");
    }
    let mut exact_digest = Sha256::new();
    for (selected, exact) in receipt.selected.iter().zip(&receipt.exact_selected_prices) {
        ensure!(
            exact.direction == selected.direction
                && exact.modular_residues == selected.residues
                && canonical_integer(&exact.exact_residual)
                && exact.exact_residual != "0",
            "G-0126 exact selected price drift"
        );
        ensure!(
            [
                decimal_mod(&exact.exact_residual, PRIMES[0])?,
                decimal_mod(&exact.exact_residual, PRIMES[1])?,
            ] == selected.residues,
            "G-0126 exact selected modular bridge drift"
        );
        exact_digest.update(exact.exact_residual.as_bytes());
        exact_digest.update(b"\n");
    }
    ensure!(
        receipt.exact_selected_prices_decimal_lf_sha256 == EXACT_RESIDUALS_SHA256
            && format!("{:x}", exact_digest.finalize()) == EXACT_RESIDUALS_SHA256,
        "G-0126 exact selected price digest drift"
    );
    ensure!(
        !receipt.exact_replay.performed
            && receipt.exact_replay.result == "NOT_TRIGGERED_MODULAR_NONZERO"
            && receipt.coefficient_plus_one_mutant.sequence == 0
            && receipt.coefficient_plus_one_mutant.coefficient_delta == "+1"
            && receipt.coefficient_plus_one_mutant.rejected,
        "G-0126 control/branch drift"
    );
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

fn exact_dot(row: &[i64], terms: &[(usize, BigInt)]) -> BigInt {
    terms
        .iter()
        .fold(BigInt::from(0), |total, (sequence, coefficient)| {
            total + coefficient * BigInt::from(row[*sequence])
        })
}

fn exact_linear_dots(linear_vectors: &[[i64; N]], terms: &[(usize, BigInt)]) -> Vec<BigInt> {
    (0..N)
        .map(|coordinate| {
            terms
                .iter()
                .fold(BigInt::from(0), |total, (sequence, coefficient)| {
                    total + coefficient * BigInt::from(linear_vectors[*sequence][coordinate])
                })
        })
        .collect()
}

fn binding_snapshot(
    input_path: &Path,
    receipt_path: &Path,
    candidate_path: &Path,
) -> Result<BTreeMap<String, String>> {
    let input_sha = sha256_path(input_path)?;
    let receipt_sha = sha256_path(receipt_path)?;
    let candidate_sha = sha256_path(candidate_path)?;
    ensure!(input_sha == INPUT_SHA256, "panel-input binding drift");
    ensure!(
        receipt_sha == RECEIPT_SHA256,
        "G-0126 receipt binding drift"
    );
    ensure!(candidate_sha == CANDIDATE_SHA256, "candidate binding drift");
    ensure!(
        receipt_sha == sha256_bytes(COMPILED_RECEIPT),
        "binary was compiled against a different G-0126 receipt"
    );
    ensure!(
        candidate_sha == sha256_bytes(COMPILED_CANDIDATE),
        "binary was compiled against a different candidate"
    );

    let crate_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let paths = BTreeMap::from([
        ("producer", crate_dir.join("src/main.rs")),
        ("cargo_manifest", crate_dir.join("Cargo.toml")),
        ("cargo_lock", crate_dir.join("Cargo.lock")),
        (
            "preregistration",
            crate_dir.join("BATCH32_COORDINATE_PRICING_PREREGISTRATION.md"),
        ),
        ("kernel", crate_dir.join("../G-0117/src/lib.rs")),
        (
            "g0126_preregistration",
            crate_dir.join("../G-0126/GLOBAL_REPLAY_PREREGISTRATION.md"),
        ),
        ("g0126_producer", crate_dir.join("../G-0126/src/main.rs")),
        (
            "g0126_executable",
            crate_dir.join("../G-0126/target/release/g0126-global-replay"),
        ),
        (
            "audited_ancestor_producer",
            crate_dir.join("../G-0117/src/bin/g0118_batch_coordinate_pricer.rs"),
        ),
        (
            "audited_ancestor_review",
            crate_dir.join("../../reviews/G-0118-iteration4-batch/review_v1.json"),
        ),
    ]);
    let mut hashes = BTreeMap::new();
    for (key, path) in &paths {
        hashes.insert((*key).to_string(), sha256_path(path)?);
    }
    ensure!(
        hashes["producer"] == sha256_bytes(COMPILED_SOURCE),
        "running binary was compiled from different source"
    );
    ensure!(
        hashes["cargo_manifest"] == sha256_bytes(COMPILED_MANIFEST),
        "running binary was compiled from different manifest"
    );
    ensure!(
        hashes["cargo_lock"] == sha256_bytes(COMPILED_LOCK),
        "running binary was compiled from different lockfile"
    );
    ensure!(
        hashes["preregistration"] == sha256_bytes(COMPILED_PREREGISTRATION),
        "running binary was compiled against different preregistration"
    );
    ensure!(
        hashes["kernel"] == KERNEL_SHA256 && hashes["kernel"] == sha256_bytes(COMPILED_KERNEL),
        "kernel binding drift"
    );
    ensure!(
        hashes["g0126_preregistration"] == G0126_PREREG_SHA256
            && hashes["g0126_preregistration"] == sha256_bytes(COMPILED_G0126_PREREGISTRATION),
        "G-0126 preregistration binding drift"
    );
    ensure!(
        hashes["g0126_producer"] == G0126_SOURCE_SHA256
            && hashes["g0126_producer"] == sha256_bytes(COMPILED_G0126_SOURCE),
        "G-0126 producer binding drift"
    );
    ensure!(
        hashes["g0126_executable"] == G0126_EXECUTABLE_SHA256,
        "G-0126 executable binding drift"
    );
    ensure!(
        hashes["audited_ancestor_producer"] == ANCESTOR_SOURCE_SHA256
            && hashes["audited_ancestor_producer"] == sha256_bytes(COMPILED_ANCESTOR_SOURCE),
        "audited ancestor source binding drift"
    );
    ensure!(
        hashes["audited_ancestor_review"] == ANCESTOR_REVIEW_SHA256
            && hashes["audited_ancestor_review"] == sha256_bytes(COMPILED_ANCESTOR_REVIEW),
        "audited ancestor review binding drift"
    );
    hashes.insert("panel_input".to_string(), input_sha);
    hashes.insert("g0126_receipt".to_string(), receipt_sha);
    hashes.insert("candidate".to_string(), candidate_sha);
    hashes.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve current executable")?)?,
    );
    Ok(hashes)
}

fn self_test() -> Result<()> {
    for valid in ["0", "1", "-1", "12345678901234567890"] {
        ensure!(canonical_integer(valid), "valid integer rejected");
    }
    for invalid in ["", "-", "+1", "00", "01", "-0", "-01", "1/2", " 1"] {
        ensure!(!canonical_integer(invalid), "invalid integer accepted");
    }
    ensure!(
        decimal_mod("-15", 7)? == 6 && decimal_mod("15", 7)? == 1,
        "signed modular reduction drift"
    );
    ensure!(
        !canonical_positive_integer("0")
            && !canonical_positive_integer("-1")
            && canonical_positive_integer("1"),
        "positive integer validation drift"
    );
    ensure!(
        serde_json::from_str::<Term>(r#"{"sequence":0,"coefficient":"1","extra":2}"#).is_err(),
        "unknown term field accepted"
    );

    let transposed = transpose_record_major(vec![vec![1, 2, 3], vec![4, 5, 6]], 3)?;
    ensure!(
        transposed == vec![vec![1, 4], vec![2, 5], vec![3, 6]],
        "transpose drift"
    );
    ensure!(
        transpose_record_major(vec![vec![1], vec![2, 3]], 2).is_err(),
        "row truncation/width mutant escaped"
    );
    let signed = [1i64, -2, 3];
    let reordered = [1i64, 3, -2];
    let sign_changed = [1i64, 2, 3];
    ensure!(
        digest_i64(signed.iter()) != digest_i64(reordered.iter())
            && digest_i64(signed.iter()) != digest_i64(sign_changed.iter()),
        "signed stream order/sign mutant escaped"
    );

    let mut direction = [0i8; N];
    direction[7..].copy_from_slice(&[1, -4, 3, 0]);
    validate_direction(&direction)?;
    let selected = Residual {
        direction,
        residues: [1, 2],
    };
    let mut residue_mutant = selected.clone();
    residue_mutant.residues[1] += 1;
    ensure!(
        digest_selected(std::slice::from_ref(&selected))
            != digest_selected(std::slice::from_ref(&residue_mutant)),
        "selected residue mutant escaped"
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
        form.labelled_permutations == factorial(N) && !form.hinges.is_empty(),
        "known-answer normal form drift"
    );
    let mut directions = form.hinges.keys().copied().collect::<Vec<_>>();
    directions.sort();
    directions.truncate(8);
    let prices = hinge_coefficients(&record, &directions)?;
    ensure!(
        directions
            .iter()
            .zip(prices)
            .all(|(candidate_direction, value)| form.hinges[candidate_direction] == value),
        "known-answer hinge coordinate bridge drift"
    );
    ensure!(
        linear_vector(&record)? == form.linear,
        "known-answer linear coordinate bridge drift"
    );

    let terms = vec![(0usize, BigInt::from(7)), (2usize, BigInt::from(-3))];
    let row = [5i64, 11, -2];
    let base = exact_dot(&row, &terms);
    let hinge_mutant = &base + BigInt::from(row[0]);
    ensure!(base != hinge_mutant, "hinge dot mutant escaped");
    let linear_rows = vec![[1i64; N], [2i64; N], [3i64; N]];
    let linear_base = exact_linear_dots(&linear_rows, &terms);
    let linear_mutant = linear_base
        .iter()
        .zip(linear_rows[0])
        .map(|(value, additive)| value + BigInt::from(additive))
        .collect::<Vec<_>>();
    ensure!(linear_base != linear_mutant, "linear dot mutant escaped");

    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0127-publish-self-test-{}-{unique}",
        std::process::id()
    ));
    std::fs::create_dir(&temporary_directory)?;
    let publication = temporary_directory.join("receipt.json");
    publish_exclusive(&publication, b"complete\n")?;
    ensure!(
        std::fs::read(&publication)? == b"complete\n"
            && publish_exclusive(&publication, b"mutant\n").is_err(),
        "exclusive publication control failed"
    );
    std::fs::remove_file(&publication)?;
    std::fs::remove_dir(&temporary_directory)?;
    Ok(())
}

fn run(
    input_path: PathBuf,
    receipt_path: PathBuf,
    candidate_path: PathBuf,
    output_path: PathBuf,
) -> Result<()> {
    ensure!(!output_path.exists(), "refusing to overwrite output");
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let started = Instant::now();

    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let receipt: ReplayReceipt =
        serde_json::from_reader(BufReader::new(File::open(&receipt_path)?))?;
    let candidate: Candidate =
        serde_json::from_reader(BufReader::new(File::open(&candidate_path)?))?;
    validate_panel(&input)?;
    validate_candidate(&candidate)?;
    validate_receipt(&receipt, &candidate)?;
    let mut bindings = binding_snapshot(&input_path, &receipt_path, &candidate_path)?;

    let directions = receipt
        .selected
        .iter()
        .map(|residual| residual.direction)
        .collect::<Vec<_>>();
    ensure!(directions.len() == K, "direction census drift");
    for direction in &directions {
        validate_direction(direction)?;
    }

    let computed = input
        .records
        .par_iter()
        .map(|record| {
            Ok((
                hinge_coefficients(record, &directions)?,
                linear_vector(record)?,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(computed.len() == RECORDS, "computed record census drift");
    let linear_vectors = computed.iter().map(|item| item.1).collect::<Vec<_>>();
    let record_major = computed.into_iter().map(|item| item.0).collect::<Vec<_>>();
    let direction_major = transpose_record_major(record_major, K)?;
    ensure!(
        direction_major.len() == K
            && direction_major.iter().all(|row| row.len() == RECORDS)
            && direction_major.iter().map(Vec::len).sum::<usize>() == HINGE_ENTRIES
            && linear_vectors.len() == RECORDS
            && linear_vectors.len() * N == LINEAR_ENTRIES,
        "coordinate dimensions drift"
    );

    let complete_hinge_digest = digest_i64(direction_major.iter().flat_map(|row| row.iter()));
    let linear_digest = digest_i64(linear_vectors.iter().flat_map(|row| row.iter()));
    ensure!(
        linear_digest == EXPECTED_LINEAR_SHA256,
        "linear known-answer digest drift"
    );

    let exact_terms = candidate
        .terms
        .iter()
        .map(|term| Ok((term.sequence, parse_bigint(&term.coefficient)?)))
        .collect::<Result<Vec<_>>>()?;
    let exact_dots = direction_major
        .iter()
        .map(|row| exact_dot(row, &exact_terms))
        .collect::<Vec<_>>();
    ensure!(exact_dots.len() == K, "exact hinge dot census drift");
    let mut exact_dot_digest = Sha256::new();
    let mut exact_dot_strings = Vec::with_capacity(K);
    for ((dot, selected), expected) in exact_dots
        .iter()
        .zip(&receipt.selected)
        .zip(&receipt.exact_selected_prices)
    {
        let raw = dot.to_string();
        ensure!(
            dot != &BigInt::from(0)
                && raw == expected.exact_residual
                && expected.direction == selected.direction
                && expected.modular_residues == selected.residues,
            "exact candidate hinge-dot bridge drift"
        );
        ensure!(
            [decimal_mod(&raw, PRIMES[0])?, decimal_mod(&raw, PRIMES[1])?] == selected.residues,
            "exact candidate hinge-dot modular bridge drift"
        );
        exact_dot_digest.update(raw.as_bytes());
        exact_dot_digest.update(b"\n");
        exact_dot_strings.push(raw);
    }
    let exact_dot_digest = format!("{:x}", exact_dot_digest.finalize());
    ensure!(
        exact_dot_digest == EXACT_RESIDUALS_SHA256,
        "exact candidate hinge-dot stream digest drift"
    );

    let exact_linear = exact_linear_dots(&linear_vectors, &exact_terms);
    let target_linear = parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N));
    ensure!(
        exact_linear.len() == N
            && exact_linear[..N - 1]
                .iter()
                .all(|value| value == &BigInt::from(0))
            && exact_linear[N - 1] == target_linear,
        "exact candidate linear-dot target bridge drift"
    );

    let mutant_hinge = exact_dots
        .iter()
        .zip(&direction_major)
        .map(|(base, row)| base + BigInt::from(row[0]))
        .collect::<Vec<_>>();
    let mutant_linear = exact_linear
        .iter()
        .zip(linear_vectors[0])
        .map(|(base, additive)| base + BigInt::from(additive))
        .collect::<Vec<_>>();
    let hinge_mutant_changed = mutant_hinge != exact_dots;
    let linear_mutant_changed = mutant_linear != exact_linear;
    let mutant_rejected = hinge_mutant_changed || linear_mutant_changed;
    ensure!(mutant_rejected, "planted +1 coefficient mutant survived");

    let rows = receipt
        .selected
        .iter()
        .zip(direction_major)
        .zip(exact_dot_strings.iter())
        .map(|((residual, coefficients), exact_residual)| {
            let minimum = coefficients.iter().copied().min().unwrap_or(0);
            let maximum = coefficients.iter().copied().max().unwrap_or(0);
            let maximum_absolute = coefficients
                .iter()
                .map(|value| value.unsigned_abs())
                .max()
                .unwrap_or(0);
            PriceRow {
                direction: residual.direction,
                modular_residues: residual.residues,
                records: coefficients.len(),
                nonzero_hinge_coefficients: coefficients
                    .iter()
                    .filter(|value| **value != 0)
                    .count(),
                minimum_hinge_coefficient: minimum,
                maximum_hinge_coefficient: maximum,
                maximum_absolute_hinge_coefficient: maximum_absolute,
                hinge_coefficients_i64_le_sha256: digest_i64(coefficients.iter()),
                exact_candidate_residual: exact_residual.clone(),
                hinge_coefficients: coefficients,
            }
        })
        .collect::<Vec<_>>();
    ensure!(rows.len() == K, "output row census drift");

    let end_bindings = binding_snapshot(&input_path, &receipt_path, &candidate_path)?;
    ensure!(
        bindings == end_bindings,
        "input/source drift during pricing"
    );
    bindings.insert(
        "output_protocol".to_string(),
        "pre-serialized_same-directory_O_EXCL_temp_then_atomic_no-overwrite_hard-link_after_all_controls_and_end_binding_recheck".to_string(),
    );

    let output = Output {
        schema: "max11-g0127-batch32-coordinate-prices-v1",
        result: "EXACT_FULL_FAMILY_BATCH32_COORDINATES",
        claim_boundary: "Exact 32-row ordered-cone hinge coordinates and all 11 linear coordinates over the frozen 163,740-record family, with candidate dot-product bridges. This is restricted-master input only, not a membership decision, family-completeness theorem, global MAX11 identity, lower bound, or Lean theorem.",
        bindings,
        batch_k: K,
        records: RECORDS,
        hinge_entries: HINGE_ENTRIES,
        linear_entries: LINEAR_ENTRIES,
        selected_count: K,
        selected_prefix_i8_u64_le_sha256: SELECTED_SHA256.to_string(),
        directions,
        modular_residues: receipt
            .selected
            .iter()
            .map(|residual| residual.residues)
            .collect(),
        direction_major_hinge_i64_le_sha256: complete_hinge_digest,
        linear_vectors_i64_le_sha256: linear_digest,
        exact_candidate_residuals_decimal_lf_sha256: exact_dot_digest,
        exact_candidate_residuals: exact_dot_strings,
        exact_candidate_linear_dots: exact_linear.iter().map(ToString::to_string).collect(),
        rows,
        linear_vectors,
        coefficient_plus_one_mutant: MutantControl {
            sequence: 0,
            coefficient_delta: "+1",
            hinge_dot_receipt_changed: hinge_mutant_changed,
            linear_dot_receipt_changed: linear_mutant_changed,
            rejected: mutant_rejected,
        },
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let stdout = format!(
        "{{\"schema\":\"{}\",\"result\":\"{}\",\"records\":{},\"selected_count\":{},\"hinge_sha256\":\"{}\",\"linear_sha256\":\"{}\",\"exact_dot_sha256\":\"{}\",\"wall_seconds\":{}}}",
        output.schema,
        output.result,
        output.records,
        output.selected_count,
        output.direction_major_hinge_i64_le_sha256,
        output.linear_vectors_i64_le_sha256,
        output.exact_candidate_residuals_decimal_lf_sha256,
        output.wall_seconds
    );
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
        println!("G-0127 self-test PASS");
        return Ok(());
    }
    ensure!(
        args.len() == 5,
        "usage: g0127-batch-coordinate-pricer PANEL_INPUT.json G0126_RECEIPT.json CANDIDATE.json OUTPUT.json | --self-test"
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
    fn producer_self_test_passes() {
        self_test().unwrap();
    }

    #[test]
    fn large_signed_decimal_reduces_exactly() {
        for raw in [
            "123456789012345678901234567890",
            "-123456789012345678901234567890",
        ] {
            let exact = parse_bigint(raw).unwrap();
            for prime in PRIMES {
                let modulus = BigInt::from(prime);
                let mut expected = &exact % &modulus;
                if expected < BigInt::from(0) {
                    expected += &modulus;
                }
                assert_eq!(
                    decimal_mod(raw, prime).unwrap(),
                    expected.to_string().parse::<u64>().unwrap()
                );
            }
        }
    }
}
