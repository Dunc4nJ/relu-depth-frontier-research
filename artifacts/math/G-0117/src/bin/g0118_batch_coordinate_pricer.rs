use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{
    N, Record, hinge_coefficients, linear_vector, validate_direction,
};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const K: usize = 32;
const RECORDS: usize = 163_740;
const TERMS: usize = 102;
const PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];
const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const CANDIDATE_SHA256: &str = "728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b";
const RECHECK_SHA256: &str = "f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f";
const CANDIDATE_SCHEMA: &str = "max11-g0118-prefix-exact-cegis-accumulated-v1";
const CANDIDATE_RESULT: &str = "PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS";
const SELECTION_RULE: &str = "After target subtraction, require accumulated d1..d4 zero in both fields; retain every hinge direction nonzero in either field; signed-i8 tuple lexicographic ascending; take first min(32,count).";
const ACCUMULATED_DIRECTIONS: [[i8; N]; 4] = [
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -3, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1],
];

const COMPILED_PRODUCER: &[u8] = include_bytes!("g0118_batch_coordinate_pricer.rs");
const COMPILED_REPLAY_PRODUCER: &[u8] = include_bytes!("g0118_batch_modular_replay.rs");
const COMPILED_KERNEL: &[u8] = include_bytes!("../lib.rs");
const COMPILED_UNIQUENESS_LEMMA: &[u8] = include_bytes!("../../NORMAL_FORM_UNIQUENESS_LEMMA.md");
const COMPILED_PREREGISTRATION: &[u8] =
    include_bytes!("../../../G-0118/BATCH32_ITERATION4_PREREGISTRATION.md");

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
struct Residual {
    direction: [i8; N],
    residues: [u64; 2],
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AccumulatedCheck {
    direction: [i8; N],
    residues: [u64; 2],
    zero_in_both_fields: bool,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct MutantControl {
    sequence: usize,
    coefficient_delta: String,
    accumulated_rows_all_zero: bool,
    linear_residues_match: bool,
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
    accumulated_row_checks: Vec<AccumulatedCheck>,
    linear_residues_after_target: [[u64; N]; 2],
    all_hinge_and_linear_residues_zero: [bool; 2],
    selected_count: usize,
    selected_prefix_i8_u64_le_sha256: String,
    selected: Vec<Residual>,
    coefficient_plus_one_mutant: MutantControl,
    wall_seconds: f64,
}

#[derive(Serialize)]
struct PriceRow {
    direction: [i8; N],
    modular_residues: [u64; 2],
    nonzero_hinge_coefficients: usize,
    maximum_hinge_coefficient: i64,
    hinge_coefficients_i64_le_sha256: String,
    hinge_coefficients: Vec<i64>,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    batch_k: usize,
    records: usize,
    selected_count: usize,
    directions: Vec<[i8; N]>,
    modular_residues: Vec<[u64; 2]>,
    direction_major_hinge_i64_le_sha256: String,
    linear_vectors_i64_le_sha256: String,
    rows: Vec<PriceRow>,
    linear_vectors: Vec<[i64; N]>,
    wall_seconds: f64,
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

fn validate_transitive_bindings(
    bindings: &BTreeMap<String, String>,
    replay_producer_sha256: &str,
    kernel_sha256: &str,
    preregistration_sha256: &str,
    uniqueness_sha256: &str,
    replay_executable_sha256: &str,
) -> Result<()> {
    ensure!(bindings.len() == 8, "replay binding-key census drift");
    for (key, expected) in [
        ("panel_input", INPUT_SHA256),
        ("candidate", CANDIDATE_SHA256),
        ("candidate_recheck", RECHECK_SHA256),
        ("producer", replay_producer_sha256),
        ("kernel", kernel_sha256),
        ("preregistration", preregistration_sha256),
        ("normal_form_uniqueness", uniqueness_sha256),
        ("executable", replay_executable_sha256),
    ] {
        ensure!(
            bindings.get(key).map(String::as_str) == Some(expected),
            "replay {key} binding drift"
        );
    }
    Ok(())
}

fn validate_receipt(
    receipt: &ReplayReceipt,
    replay_producer_sha256: &str,
    kernel_sha256: &str,
    preregistration_sha256: &str,
    uniqueness_sha256: &str,
    replay_executable_sha256: &str,
) -> Result<()> {
    ensure!(
        receipt.schema == "max11-g0118-batch32-global-modular-replay-v1"
            && receipt.result == "BATCH_RESIDUAL_PREFIX_SELECTED",
        "replay receipt identity drift"
    );
    ensure!(
        receipt.claim_boundary
            == "A nonzero two-prime residual exactly refutes candidate 4; selected rows are deterministic finite-family CEGIS inputs. Two-prime zero remains a screen. No outcome proves family completeness or MAX11.",
        "replay claim boundary drift"
    );
    validate_transitive_bindings(
        &receipt.bindings,
        replay_producer_sha256,
        kernel_sha256,
        preregistration_sha256,
        uniqueness_sha256,
        replay_executable_sha256,
    )?;
    ensure!(
        receipt.candidate_schema == CANDIDATE_SCHEMA
            && receipt.candidate_result == CANDIDATE_RESULT,
        "replay candidate identity drift"
    );
    ensure!(
        receipt.primes == PRIMES
            && receipt.batch_k == K
            && receipt.selection_rule == SELECTION_RULE
            && receipt.complete_global_replay
            && receipt.terms == TERMS,
        "replay protocol drift"
    );
    ensure!(
        receipt.labelled_permutations_checked == TERMS as u64 * (1..=N as u64).product::<u64>(),
        "replay permutation census drift"
    );
    ensure!(
        receipt.accumulated_row_checks.len() == ACCUMULATED_DIRECTIONS.len()
            && receipt
                .accumulated_row_checks
                .iter()
                .zip(ACCUMULATED_DIRECTIONS)
                .all(|(check, direction)| {
                    check.direction == direction
                        && check.residues == [0, 0]
                        && check.zero_in_both_fields
                }),
        "accumulated-row receipt drift"
    );
    ensure!(
        receipt.all_hinge_and_linear_residues_zero != [true, true],
        "two-prime-zero receipt cannot be priced as a refutation"
    );
    ensure!(
        receipt.selected_count == receipt.selected.len()
            && receipt.selected_count == K.min(receipt.nonzero_hinge_residue_directions)
            && receipt.selected_count > 0,
        "selected-prefix census drift"
    );
    let directions = receipt
        .selected
        .iter()
        .map(|residual| residual.direction)
        .collect::<Vec<_>>();
    ensure!(
        directions.windows(2).all(|window| window[0] < window[1])
            && directions.iter().copied().collect::<BTreeSet<_>>().len() == directions.len(),
        "selected directions are not strictly signed-lexicographic"
    );
    ensure!(
        receipt
            .selected
            .iter()
            .all(|residual| residual.residues != [0, 0]),
        "selected zero-residual direction"
    );
    ensure!(
        digest_selected(&receipt.selected) == receipt.selected_prefix_i8_u64_le_sha256,
        "selected-prefix digest drift"
    );
    ensure!(
        receipt.coefficient_plus_one_mutant.coefficient_delta == "+1"
            && receipt.coefficient_plus_one_mutant.rejected,
        "mutant control drift"
    );
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

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 4,
        "usage: g0118_batch_coordinate_pricer PANEL_INPUT.json REPLAY_RECEIPT.json OUTPUT.json"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let input_path = PathBuf::from(&args[1]);
    let replay_path = PathBuf::from(&args[2]);
    let output_path = PathBuf::from(&args[3]);
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let started = Instant::now();

    let input_sha256 = sha256_path(&input_path)?;
    ensure!(input_sha256 == INPUT_SHA256, "panel-input binding drift");
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let receipt: ReplayReceipt =
        serde_json::from_reader(BufReader::new(File::open(&replay_path)?))?;
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1",
        "panel-input schema drift"
    );
    ensure!(
        input.control_sequences == [0, 1, 284, 5_341, 30_223, 133_449, 134_301]
            && input.primes == [2_000_081, 3_000_017]
            && input.rows_path == "artifacts/math/G-0111/dual_rows_v1.json"
            && input.target.len() == 301,
        "panel-input auxiliary metadata drift"
    );
    ensure!(input.records.len() == RECORDS, "record census drift");
    ensure!(
        input
            .records
            .iter()
            .enumerate()
            .all(|(sequence, record)| record.sequence == sequence),
        "record sequence drift"
    );

    let producer_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/bin/g0118_batch_coordinate_pricer.rs"
    ));
    let replay_producer_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/bin/g0118_batch_modular_replay.rs"
    ));
    let kernel_path = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/lib.rs"));
    let uniqueness_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/NORMAL_FORM_UNIQUENESS_LEMMA.md"
    ));
    let preregistration_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/../G-0118/BATCH32_ITERATION4_PREREGISTRATION.md"
    ));
    let current_executable = std::env::current_exe().context("resolve current executable")?;
    let replay_executable_path = current_executable
        .parent()
        .context("resolve release executable directory")?
        .join("g0118_batch_modular_replay");
    let producer_sha256 = sha256_path(producer_path)?;
    let replay_producer_sha256 = sha256_path(replay_producer_path)?;
    let kernel_sha256 = sha256_path(kernel_path)?;
    let uniqueness_sha256 = sha256_path(uniqueness_path)?;
    let preregistration_sha256 = sha256_path(preregistration_path)?;
    let replay_executable_sha256 = sha256_path(&replay_executable_path)?;
    ensure!(
        producer_sha256 == sha256_bytes(COMPILED_PRODUCER),
        "running binary was compiled from a different producer source"
    );
    ensure!(
        replay_producer_sha256 == sha256_bytes(COMPILED_REPLAY_PRODUCER),
        "running binary was compiled against a different replay producer"
    );
    ensure!(
        kernel_sha256 == sha256_bytes(COMPILED_KERNEL),
        "running binary was compiled from a different kernel source"
    );
    ensure!(
        uniqueness_sha256 == sha256_bytes(COMPILED_UNIQUENESS_LEMMA),
        "running binary was compiled against a different uniqueness lemma"
    );
    ensure!(
        preregistration_sha256 == sha256_bytes(COMPILED_PREREGISTRATION),
        "running binary was compiled against a different preregistration"
    );
    validate_receipt(
        &receipt,
        &replay_producer_sha256,
        &kernel_sha256,
        &preregistration_sha256,
        &uniqueness_sha256,
        &replay_executable_sha256,
    )?;

    let directions = receipt
        .selected
        .iter()
        .map(|residual| residual.direction)
        .collect::<Vec<_>>();
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
    let linear_vectors = computed.iter().map(|item| item.1).collect::<Vec<_>>();
    let record_major = computed.into_iter().map(|item| item.0).collect::<Vec<_>>();
    let direction_major = transpose_record_major(record_major, directions.len())?;
    ensure!(
        direction_major
            .iter()
            .all(|row| row.len() == input.records.len()),
        "direction-major record census drift"
    );

    let complete_hinge_digest = digest_i64(direction_major.iter().flat_map(|row| row.iter()));
    let linear_digest = digest_i64(linear_vectors.iter().flat_map(|row| row.iter()));
    let rows = receipt
        .selected
        .iter()
        .zip(direction_major)
        .map(|(residual, coefficients)| PriceRow {
            direction: residual.direction,
            modular_residues: residual.residues,
            nonzero_hinge_coefficients: coefficients.iter().filter(|value| **value != 0).count(),
            maximum_hinge_coefficient: coefficients.iter().copied().max().unwrap_or(0),
            hinge_coefficients_i64_le_sha256: digest_i64(coefficients.iter()),
            hinge_coefficients: coefficients,
        })
        .collect::<Vec<_>>();

    let mut bindings = BTreeMap::new();
    bindings.insert("panel_input".to_string(), input_sha256);
    bindings.insert("candidate".to_string(), CANDIDATE_SHA256.to_string());
    bindings.insert("candidate_recheck".to_string(), RECHECK_SHA256.to_string());
    bindings.insert("replay_receipt".to_string(), sha256_path(&replay_path)?);
    bindings.insert("replay_producer".to_string(), replay_producer_sha256);
    bindings.insert("producer".to_string(), producer_sha256);
    bindings.insert("kernel".to_string(), kernel_sha256);
    bindings.insert("normal_form_uniqueness".to_string(), uniqueness_sha256);
    bindings.insert("preregistration".to_string(), preregistration_sha256);
    bindings.insert("executable".to_string(), sha256_path(&current_executable)?);
    let output = Output {
        schema: "max11-g0118-batch32-coordinate-price-v1",
        result: "EXACT_BATCH_COORDINATE_PRICES",
        claim_boundary: "Thirty-two or fewer exact ordered-cone hinge rows and all linear rows over the frozen 163,740-column family; finite-family CEGIS input, not a membership decision, completeness theorem, or MAX11 result.",
        bindings,
        batch_k: K,
        records: input.records.len(),
        selected_count: rows.len(),
        directions,
        modular_residues: receipt
            .selected
            .iter()
            .map(|residual| residual.residues)
            .collect(),
        direction_major_hinge_i64_le_sha256: complete_hinge_digest,
        linear_vectors_i64_le_sha256: linear_digest,
        rows,
        linear_vectors,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let destination = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output_path)?;
    let mut writer = BufWriter::new(destination);
    serde_json::to_writer(&mut writer, &output)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    println!(
        "{{\"schema\":\"{}\",\"result\":\"{}\",\"selected_count\":{},\"records\":{},\"hinge_sha256\":\"{}\",\"linear_sha256\":\"{}\",\"wall_seconds\":{}}}",
        output.schema,
        output.result,
        output.selected_count,
        output.records,
        output.direction_major_hinge_i64_le_sha256,
        output.linear_vectors_i64_le_sha256,
        output.wall_seconds
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn transpose_preserves_both_axes() {
        let output = transpose_record_major(vec![vec![1, 2, 3], vec![4, 5, 6]], 3).unwrap();
        assert_eq!(output, vec![vec![1, 4], vec![2, 5], vec![3, 6]]);
        assert!(transpose_record_major(vec![vec![1], vec![2, 3]], 2).is_err());
    }

    #[test]
    fn signed_i64_digest_rejects_reordering_and_sign_change() {
        let first = [1i64, -2, 3];
        let reordered = [1i64, 3, -2];
        let sign_changed = [1i64, 2, 3];
        assert_ne!(digest_i64(first.iter()), digest_i64(reordered.iter()));
        assert_ne!(digest_i64(first.iter()), digest_i64(sign_changed.iter()));
    }

    #[test]
    fn selected_digest_rejects_residue_mutation() {
        let first = Residual {
            direction: [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
            residues: [1, 2],
        };
        let mut second = first.clone();
        second.residues[1] += 1;
        assert_ne!(digest_selected(&[first]), digest_selected(&[second]));
    }

    #[test]
    fn transitive_binding_mutant_is_rejected() {
        let mut bindings = BTreeMap::from([
            ("panel_input".to_string(), INPUT_SHA256.to_string()),
            ("candidate".to_string(), CANDIDATE_SHA256.to_string()),
            ("candidate_recheck".to_string(), RECHECK_SHA256.to_string()),
            ("producer".to_string(), "replay-producer".to_string()),
            ("kernel".to_string(), "kernel".to_string()),
            ("preregistration".to_string(), "preregistration".to_string()),
            (
                "normal_form_uniqueness".to_string(),
                "uniqueness".to_string(),
            ),
            ("executable".to_string(), "replay-executable".to_string()),
        ]);
        assert!(
            validate_transitive_bindings(
                &bindings,
                "replay-producer",
                "kernel",
                "preregistration",
                "uniqueness",
                "replay-executable",
            )
            .is_ok()
        );
        bindings.insert("candidate_recheck".to_string(), "mutant".to_string());
        assert!(
            validate_transitive_bindings(
                &bindings,
                "replay-producer",
                "kernel",
                "preregistration",
                "uniqueness",
                "replay-executable",
            )
            .is_err()
        );
    }
}
