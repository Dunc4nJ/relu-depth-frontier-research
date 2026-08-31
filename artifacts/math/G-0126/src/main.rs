use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{
    FullNormalForm, N, Record, full_normal_form, hinge_coefficients, validate_direction,
};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];
const K: usize = 32;
const RECORDS: usize = 163_740;
const TERMS: usize = 131;
const OLD_DIRECTIONS: usize = 36;
const EXPECTED_LABELLED_PERMUTATIONS: u64 = 5_229_100_800;
const CANDIDATE_SHA256: &str = "53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036";
const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const KERNEL_SHA256: &str = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6";
const UNIQUENESS_SHA256: &str = "39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17";
const MANIFEST_SHA256: &str = "9234415af8719ea0f46eaf7952d76cab006afe44e4d7e111813fde61e4a5032c";
const SOLVER_SHA256: &str = "dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac";
const TARGET_SCALE: &str = "264010886084977103415797420761461511057729096350532822171032655262573576673600959905395014217297467347581921316792637811198651042601200900728134005150";
const CANDIDATE_SCHEMA: &str = "max11-g0121-full-family-master-result-v1";
const CANDIDATE_RESULT: &str = "FULL_FAMILY_EXACT_Q_MEMBER";
const CANDIDATE_CLAIM: &str = "Exact membership only on the frozen 348-row system over the frozen 163,740-column family; a finite-row candidate for separate complete global replay, not a family-completeness theorem or MAX11 result.";
const SELECTION_RULE: &str = "After target subtraction and 36 carry-forward zero checks, retain every hinge direction nonzero in either field; signed-i8 tuple lexicographic ascending; take first min(32,count).";

const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs");
const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml");
const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock");
const COMPILED_PREREGISTRATION: &[u8] = include_bytes!("../GLOBAL_REPLAY_PREREGISTRATION.md");
const COMPILED_CANDIDATE: &[u8] = include_bytes!("../../G-0121/full_family_master_result_v1.json");
const COMPILED_KERNEL: &[u8] = include_bytes!("../../G-0117/src/lib.rs");
const COMPILED_UNIQUENESS: &[u8] = include_bytes!("../../G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md");

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

#[derive(Default)]
struct ModularAggregate {
    hinges: HashMap<[i8; N], [u64; 2]>,
    linear: [[u64; N]; 2],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
}

struct ExactAggregate {
    hinges: HashMap<[i8; N], BigInt>,
    linear: [BigInt; N],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
}

impl Default for ExactAggregate {
    fn default() -> Self {
        Self {
            hinges: HashMap::new(),
            linear: std::array::from_fn(|_| BigInt::from(0)),
            terms: 0,
            hinge_entries_processed: 0,
            labelled_permutations_checked: 0,
        }
    }
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
struct Residual {
    direction: [i8; N],
    residues: [u64; 2],
}

#[derive(Serialize)]
struct CarryForwardCheck {
    index: usize,
    direction: [i8; N],
    residues: [u64; 2],
    zero_in_both_fields: bool,
}

#[derive(Serialize)]
struct ExactPrice {
    direction: [i8; N],
    modular_residues: [u64; 2],
    exact_residual: String,
}

#[derive(Serialize)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Serialize)]
struct ExactLinear {
    coordinate: usize,
    coefficient: String,
}

#[derive(Serialize)]
struct ExactReplay {
    performed: bool,
    result: &'static str,
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_directions: usize,
    first_nonzero_hinge: Option<ExactHinge>,
    linear_residuals_after_target: Vec<String>,
    first_nonzero_linear: Option<ExactLinear>,
}

#[derive(Serialize)]
struct MutantControl {
    sequence: usize,
    coefficient_delta: &'static str,
    carry_forward_residues_match: bool,
    linear_residues_match: bool,
    nonzero_hinge_count_matches: bool,
    selected_prefix_matches: bool,
    rejected: bool,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    candidate_schema: String,
    candidate_result: String,
    target_scale: String,
    primes: [u64; 2],
    batch_k: usize,
    selection_rule: &'static str,
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
    exact_selected_prices: Vec<ExactPrice>,
    first_nonzero_linear: Option<ExactLinear>,
    exact_replay: ExactReplay,
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

fn validate_term_structure(terms: &[Term], records: usize, maximum_sequence: usize) -> Result<()> {
    let mut previous = None;
    for term in terms {
        ensure!(term.sequence < records, "term outside family");
        ensure!(
            term.sequence <= maximum_sequence,
            "term outside frozen sequence bound"
        );
        ensure!(
            previous.is_none_or(|value| term.sequence > value),
            "term sequences not strictly increasing"
        );
        ensure!(
            canonical_integer(&term.coefficient) && term.coefficient != "0",
            "candidate coefficient drift"
        );
        previous = Some(term.sequence);
    }
    Ok(())
}

fn validated_full_normal_form(record: &Record) -> Result<FullNormalForm> {
    let form = full_normal_form(record)?;
    for direction in form.hinges.keys() {
        validate_direction(direction)?;
    }
    Ok(form)
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

fn add_modular(aggregate: &mut ModularAggregate, form: FullNormalForm, coefficient: [u64; 2]) {
    aggregate.terms += 1;
    aggregate.labelled_permutations_checked += form.labelled_permutations;
    aggregate.hinge_entries_processed += form.hinges.len() as u64;
    for (field, &prime) in PRIMES.iter().enumerate() {
        for (rank, &value) in form.linear.iter().enumerate() {
            let residue = value.rem_euclid(prime as i64) as u64;
            aggregate.linear[field][rank] =
                (aggregate.linear[field][rank] + coefficient[field] * residue) % prime;
        }
    }
    for (direction, value) in form.hinges {
        let entry = aggregate.hinges.entry(direction).or_default();
        for (field, &prime) in PRIMES.iter().enumerate() {
            let residue = value.rem_euclid(prime as i64) as u64;
            entry[field] = (entry[field] + coefficient[field] * residue) % prime;
        }
    }
}

fn merge_modular(mut left: ModularAggregate, right: ModularAggregate) -> ModularAggregate {
    if left.hinges.len() < right.hinges.len() {
        return merge_modular(right, left);
    }
    left.terms += right.terms;
    left.labelled_permutations_checked += right.labelled_permutations_checked;
    left.hinge_entries_processed += right.hinge_entries_processed;
    for (field, &prime) in PRIMES.iter().enumerate() {
        for rank in 0..N {
            left.linear[field][rank] =
                (left.linear[field][rank] + right.linear[field][rank]) % prime;
        }
    }
    for (direction, residues) in right.hinges {
        let entry = left.hinges.entry(direction).or_default();
        for (field, &prime) in PRIMES.iter().enumerate() {
            entry[field] = (entry[field] + residues[field]) % prime;
        }
    }
    left
}

fn add_exact(aggregate: &mut ExactAggregate, form: FullNormalForm, coefficient: &BigInt) {
    aggregate.terms += 1;
    aggregate.labelled_permutations_checked += form.labelled_permutations;
    aggregate.hinge_entries_processed += form.hinges.len() as u64;
    for (rank, value) in form.linear.into_iter().enumerate() {
        aggregate.linear[rank] += coefficient * BigInt::from(value);
    }
    for (direction, value) in form.hinges {
        *aggregate.hinges.entry(direction).or_default() += coefficient * BigInt::from(value);
    }
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
    left
}

fn residuals_with_additive(
    hinges: &HashMap<[i8; N], [u64; 2]>,
    additive: Option<&FullNormalForm>,
) -> Vec<Residual> {
    let mut keys = hinges.keys().copied().collect::<BTreeSet<_>>();
    if let Some(form) = additive {
        keys.extend(form.hinges.keys().copied());
    }
    keys.into_iter()
        .filter_map(|direction| {
            let mut residues = hinges.get(&direction).copied().unwrap_or_default();
            if let Some(value) = additive.and_then(|form| form.hinges.get(&direction)) {
                for (field, &prime) in PRIMES.iter().enumerate() {
                    residues[field] =
                        (residues[field] + value.rem_euclid(prime as i64) as u64) % prime;
                }
            }
            (residues != [0, 0]).then_some(Residual {
                direction,
                residues,
            })
        })
        .collect()
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

fn exact_prices(
    input: &PanelInput,
    candidate: &Candidate,
    selected: &[Residual],
) -> Result<(Vec<ExactPrice>, String)> {
    if selected.is_empty() {
        return Ok((Vec::new(), sha256_bytes(b"")));
    }
    let directions = selected
        .iter()
        .map(|item| item.direction)
        .collect::<Vec<_>>();
    let mut totals = vec![BigInt::from(0); directions.len()];
    for term in &candidate.terms {
        let coefficient = parse_bigint(&term.coefficient)?;
        let prices = hinge_coefficients(&input.records[term.sequence], &directions)?;
        ensure!(prices.len() == directions.len(), "exact-price width drift");
        for (total, price) in totals.iter_mut().zip(prices) {
            *total += &coefficient * BigInt::from(price);
        }
    }
    let mut digest = Sha256::new();
    let mut output = Vec::with_capacity(selected.len());
    for (item, exact) in selected.iter().zip(totals) {
        let raw = exact.to_string();
        let reductions = [decimal_mod(&raw, PRIMES[0])?, decimal_mod(&raw, PRIMES[1])?];
        ensure!(
            reductions == item.residues,
            "exact selected-price modular bridge failed"
        );
        ensure!(exact != BigInt::from(0), "selected exact residual is zero");
        digest.update(raw.as_bytes());
        digest.update(b"\n");
        output.push(ExactPrice {
            direction: item.direction,
            modular_residues: item.residues,
            exact_residual: raw,
        });
    }
    Ok((output, format!("{:x}", digest.finalize())))
}

fn exact_linear_residual(
    input: &PanelInput,
    candidate: &Candidate,
    coordinate: usize,
) -> Result<BigInt> {
    let mut total = BigInt::from(0);
    for term in &candidate.terms {
        let coefficient = parse_bigint(&term.coefficient)?;
        let form = validated_full_normal_form(&input.records[term.sequence])?;
        total += coefficient * BigInt::from(form.linear[coordinate]);
    }
    if coordinate == N - 1 {
        total -= parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N));
    }
    Ok(total)
}

fn exact_full_replay(input: &PanelInput, candidate: &Candidate) -> Result<ExactReplay> {
    let mut aggregate = candidate
        .terms
        .par_iter()
        .map(|term| -> Result<ExactAggregate> {
            let coefficient = parse_bigint(&term.coefficient)?;
            let form = validated_full_normal_form(&input.records[term.sequence])?;
            let mut output = ExactAggregate::default();
            add_exact(&mut output, form, &coefficient);
            Ok(output)
        })
        .try_reduce(
            ExactAggregate::default,
            |left, right| -> Result<ExactAggregate> { Ok(merge_exact(left, right)) },
        )?;
    ensure!(aggregate.terms == TERMS, "exact replay term census drift");
    ensure!(
        aggregate.labelled_permutations_checked == EXPECTED_LABELLED_PERMUTATIONS,
        "exact replay permutation census drift"
    );
    aggregate.linear[N - 1] -= parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N));
    let aggregate_hinge_support = aggregate.hinges.len();
    let nonzero = aggregate
        .hinges
        .iter()
        .filter(|(_, coefficient)| **coefficient != BigInt::from(0))
        .map(|(direction, coefficient)| (*direction, coefficient.clone()))
        .collect::<BTreeMap<_, _>>();
    let first_nonzero_hinge = nonzero
        .iter()
        .next()
        .map(|(direction, coefficient)| ExactHinge {
            direction: *direction,
            coefficient: coefficient.to_string(),
        });
    let linear_residuals = aggregate
        .linear
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    let first_nonzero_linear = aggregate
        .linear
        .iter()
        .enumerate()
        .find(|(_, value)| **value != BigInt::from(0))
        .map(|(coordinate, value)| ExactLinear {
            coordinate,
            coefficient: value.to_string(),
        });
    let result = if first_nonzero_hinge.is_none() && first_nonzero_linear.is_none() {
        "EXACT_GLOBAL_NORMAL_FORM_ZERO"
    } else {
        "EXACT_GLOBAL_NORMAL_FORM_RESIDUAL"
    };
    Ok(ExactReplay {
        performed: true,
        result,
        terms: aggregate.terms,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        aggregate_hinge_support,
        nonzero_hinge_directions: nonzero.len(),
        first_nonzero_hinge,
        linear_residuals_after_target: linear_residuals,
        first_nonzero_linear,
    })
}

fn validate_inputs(
    input_path: &Path,
    candidate_path: &Path,
    input: &PanelInput,
    candidate: &Candidate,
) -> Result<BTreeMap<String, String>> {
    let input_sha = sha256_path(input_path)?;
    let candidate_sha = sha256_path(candidate_path)?;
    ensure!(input_sha == INPUT_SHA256, "panel-input binding drift");
    ensure!(candidate_sha == CANDIDATE_SHA256, "candidate binding drift");
    ensure!(
        candidate_sha == sha256_bytes(COMPILED_CANDIDATE),
        "binary was compiled against a different candidate"
    );
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
    ensure!(
        candidate.schema == CANDIDATE_SCHEMA
            && candidate.result == CANDIDATE_RESULT
            && candidate.claim_boundary == CANDIDATE_CLAIM
            && candidate.rows == 348
            && candidate.records == RECORDS,
        "candidate identity drift"
    );
    ensure!(
        candidate.manifest_path == "artifacts/math/G-0121/full_family_master_manifest_v1.json"
            && candidate.manifest_sha256 == MANIFEST_SHA256
            && candidate.solver_sha256 == SOLVER_SHA256,
        "candidate provenance drift"
    );
    ensure!(
        candidate.target_scale == TARGET_SCALE
            && canonical_positive_integer(&candidate.target_scale),
        "target scale drift"
    );
    ensure!(
        candidate.all_rows_replayed && candidate.coefficient_plus_one_mutant_rejected,
        "candidate exact-row controls not green"
    );
    ensure!(
        candidate.terms.len() == TERMS,
        "candidate term census drift"
    );
    ensure!(
        candidate.hinge_directions.len() == OLD_DIRECTIONS,
        "old-direction census drift"
    );
    for direction in &candidate.hinge_directions {
        validate_direction(direction)?;
    }
    ensure!(
        candidate.terms
            == nonzero_term_projection(
                &candidate.support_sequences,
                &candidate.integer_coefficients,
            )?,
        "candidate nonzero term projection drift"
    );
    validate_term_structure(&candidate.terms, RECORDS, 141)?;

    let manifest_path = Path::new(&candidate.manifest_path);
    let solver_path = Path::new("artifacts/math/G-0123/full_family_master.py");
    ensure!(
        sha256_path(manifest_path)? == MANIFEST_SHA256,
        "master manifest drift"
    );
    ensure!(
        sha256_path(solver_path)? == SOLVER_SHA256,
        "master solver drift"
    );

    let crate_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let source_path = crate_dir.join("src/main.rs");
    let manifest_source_path = crate_dir.join("Cargo.toml");
    let lock_path = crate_dir.join("Cargo.lock");
    let preregistration_path = crate_dir.join("GLOBAL_REPLAY_PREREGISTRATION.md");
    let kernel_path = crate_dir.join("../G-0117/src/lib.rs");
    let uniqueness_path = crate_dir.join("../G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md");

    let source_sha = sha256_path(&source_path)?;
    let manifest_source_sha = sha256_path(&manifest_source_path)?;
    let lock_sha = sha256_path(&lock_path)?;
    let preregistration_sha = sha256_path(&preregistration_path)?;
    let kernel_sha = sha256_path(&kernel_path)?;
    let uniqueness_sha = sha256_path(&uniqueness_path)?;
    ensure!(
        source_sha == sha256_bytes(COMPILED_SOURCE),
        "running binary was compiled from different producer source"
    );
    ensure!(
        manifest_source_sha == sha256_bytes(COMPILED_MANIFEST),
        "running binary was compiled from different Cargo manifest"
    );
    ensure!(
        lock_sha == sha256_bytes(COMPILED_LOCK),
        "running binary was compiled from different Cargo lockfile"
    );
    ensure!(
        preregistration_sha == sha256_bytes(COMPILED_PREREGISTRATION),
        "running binary was compiled against a different preregistration"
    );
    ensure!(
        kernel_sha == KERNEL_SHA256 && kernel_sha == sha256_bytes(COMPILED_KERNEL),
        "kernel binding drift"
    );
    ensure!(
        uniqueness_sha == UNIQUENESS_SHA256 && uniqueness_sha == sha256_bytes(COMPILED_UNIQUENESS),
        "normal-form uniqueness binding drift"
    );

    let mut bindings = BTreeMap::new();
    bindings.insert("candidate".to_string(), candidate_sha);
    bindings.insert("panel_input".to_string(), input_sha);
    bindings.insert("master_manifest".to_string(), MANIFEST_SHA256.to_string());
    bindings.insert("master_solver".to_string(), SOLVER_SHA256.to_string());
    bindings.insert("producer".to_string(), source_sha);
    bindings.insert("cargo_manifest".to_string(), manifest_source_sha);
    bindings.insert("cargo_lock".to_string(), lock_sha);
    bindings.insert("preregistration".to_string(), preregistration_sha);
    bindings.insert("kernel".to_string(), kernel_sha);
    bindings.insert("normal_form_uniqueness".to_string(), uniqueness_sha);
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve current executable")?)?,
    );
    Ok(bindings)
}

fn self_test() -> Result<()> {
    for valid in ["0", "1", "-1", "12345678901234567890"] {
        ensure!(canonical_integer(valid), "valid integer rejected");
    }
    for invalid in ["", "-", "+1", "00", "01", "-0", "-01", "1/2", " 1"] {
        ensure!(!canonical_integer(invalid), "invalid integer accepted");
    }
    ensure!(
        decimal_mod("-1", 7)? == 6,
        "negative modular reduction drift"
    );
    ensure!(
        decimal_mod("15", 7)? == 1,
        "positive modular reduction drift"
    );
    ensure!(
        !canonical_positive_integer("0")
            && !canonical_positive_integer("-1")
            && canonical_positive_integer("1"),
        "positive target-scale validation drift"
    );

    let valid_terms = vec![
        Term {
            sequence: 0,
            coefficient: "1".to_string(),
        },
        Term {
            sequence: 2,
            coefficient: "-3".to_string(),
        },
    ];
    validate_term_structure(&valid_terms, 3, 2)?;
    let structural_mutants = [
        vec![valid_terms[0].clone(), valid_terms[0].clone()],
        vec![valid_terms[1].clone(), valid_terms[0].clone()],
        vec![
            valid_terms[0].clone(),
            Term {
                sequence: 3,
                coefficient: "1".to_string(),
            },
        ],
        vec![
            valid_terms[0].clone(),
            Term {
                sequence: 2,
                coefficient: "0".to_string(),
            },
        ],
        vec![
            valid_terms[0].clone(),
            Term {
                sequence: 2,
                coefficient: "01".to_string(),
            },
        ],
    ];
    ensure!(
        structural_mutants
            .iter()
            .all(|terms| validate_term_structure(terms, 3, 2).is_err()),
        "structural term mutant escaped"
    );
    ensure!(
        nonzero_term_projection(
            &[0, 1, 2],
            &["1".to_string(), "0".to_string(), "-3".to_string()]
        )? == valid_terms,
        "zero-padded term projection drift"
    );
    ensure!(
        serde_json::from_str::<Term>(r#"{"sequence":0,"coefficient":"1","extra":2}"#).is_err(),
        "unknown term field accepted"
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
        form.labelled_permutations == factorial(N),
        "known-answer permutation census drift"
    );
    ensure!(!form.hinges.is_empty(), "known-answer hinge support empty");
    let mut directions = form.hinges.keys().copied().collect::<Vec<_>>();
    directions.sort();
    directions.truncate(8);
    let prices = hinge_coefficients(&record, &directions)?;
    ensure!(
        directions
            .iter()
            .zip(prices)
            .all(|(direction, value)| form.hinges[direction] == value),
        "known-answer coordinate bridge drift"
    );
    for direction in &directions {
        validate_direction(direction)?;
    }
    let mut reversed = directions[0];
    for coordinate in &mut reversed {
        *coordinate = -*coordinate;
    }
    let mut nonzero_sum = directions[0];
    nonzero_sum[N - 1] += 1;
    ensure!(
        validate_direction(&reversed).is_err() && validate_direction(&nonzero_sum).is_err(),
        "invalid direction mutant escaped"
    );

    let mut base_modular = ModularAggregate::default();
    add_modular(
        &mut base_modular,
        validated_full_normal_form(&record)?,
        [7, 7],
    );
    let mut coefficient_mutant = ModularAggregate::default();
    add_modular(
        &mut coefficient_mutant,
        validated_full_normal_form(&record)?,
        [8, 8],
    );
    ensure!(
        base_modular.hinges != coefficient_mutant.hinges,
        "hinge coefficient mutant escaped"
    );
    ensure!(
        base_modular.linear != coefficient_mutant.linear,
        "linear coefficient mutant escaped"
    );
    let mut hinge_only_mutant = base_modular.hinges.clone();
    let hinge_key = *hinge_only_mutant.keys().next().context("sample hinge")?;
    let old_hinge_residue = hinge_only_mutant[&hinge_key][0];
    hinge_only_mutant
        .get_mut(&hinge_key)
        .context("sample hinge")?[0] = (old_hinge_residue + 1) % PRIMES[0];
    ensure!(
        hinge_only_mutant != base_modular.hinges,
        "independent hinge-only mutant escaped"
    );
    let mut linear_only_mutant = base_modular.linear;
    linear_only_mutant[0][0] = (linear_only_mutant[0][0] + 1) % PRIMES[0];
    ensure!(
        linear_only_mutant != base_modular.linear,
        "independent linear-only mutant escaped"
    );

    let mut synthetic = HashMap::new();
    let mut first = [0i8; N];
    first[7..].copy_from_slice(&[1, -2, 0, 1]);
    let mut second = [0i8; N];
    second[7..].copy_from_slice(&[1, -3, 1, 1]);
    synthetic.insert(second, [1, 0]);
    synthetic.insert(first, [2, 0]);
    let residuals = residuals_with_additive(&synthetic, None);
    ensure!(
        residuals
            .iter()
            .map(|item| item.direction)
            .collect::<Vec<_>>()
            == vec![second, first],
        "signed lexicographic selection drift"
    );
    ensure!(
        digest_selected(&residuals) != digest_selected(&residuals[..1]),
        "selected digest mutation escaped"
    );
    let exact = BigInt::from(-15);
    ensure!(
        decimal_mod(&exact.to_string(), 7)? == 6,
        "exact modular bridge drift"
    );
    ensure!(
        BigInt::from(5) + BigInt::from(-5) == BigInt::from(0),
        "synthetic exact cancellation drift"
    );
    ensure!(
        BigInt::from(factorial(N)) - BigInt::from(factorial(N)) == BigInt::from(0),
        "target subtraction drift"
    );
    let unique = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)?
        .as_nanos();
    let temporary_directory = std::env::temp_dir().join(format!(
        "g0126-publish-self-test-{}-{unique}",
        std::process::id()
    ));
    std::fs::create_dir(&temporary_directory)?;
    let publication = temporary_directory.join("receipt.json");
    publish_exclusive(&publication, b"complete\n")?;
    ensure!(
        std::fs::read(&publication)? == b"complete\n",
        "exclusive publication byte drift"
    );
    ensure!(
        publish_exclusive(&publication, b"mutant\n").is_err(),
        "exclusive overwrite mutant escaped"
    );
    std::fs::remove_file(&publication)?;
    std::fs::remove_dir(&temporary_directory)?;
    Ok(())
}

fn run(input_path: PathBuf, candidate_path: PathBuf, output_path: PathBuf) -> Result<()> {
    ensure!(!output_path.exists(), "refusing to overwrite output");
    self_test()?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let started = Instant::now();
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let candidate: Candidate =
        serde_json::from_reader(BufReader::new(File::open(&candidate_path)?))?;
    let mut bindings = validate_inputs(&input_path, &candidate_path, &input, &candidate)?;

    let mut aggregate = candidate
        .terms
        .par_iter()
        .map(|term| -> Result<ModularAggregate> {
            let coefficient = [
                decimal_mod(&term.coefficient, PRIMES[0])?,
                decimal_mod(&term.coefficient, PRIMES[1])?,
            ];
            let form = validated_full_normal_form(&input.records[term.sequence])?;
            let mut output = ModularAggregate::default();
            add_modular(&mut output, form, coefficient);
            Ok(output)
        })
        .try_reduce(
            ModularAggregate::default,
            |left, right| -> Result<ModularAggregate> { Ok(merge_modular(left, right)) },
        )?;
    ensure!(aggregate.terms == TERMS, "modular term census drift");
    ensure!(
        aggregate.labelled_permutations_checked == EXPECTED_LABELLED_PERMUTATIONS,
        "modular permutation census drift"
    );
    let target = factorial(N);
    for (field, &prime) in PRIMES.iter().enumerate() {
        let scaled_target = (target % prime) * decimal_mod(&candidate.target_scale, prime)? % prime;
        aggregate.linear[field][N - 1] =
            (aggregate.linear[field][N - 1] + prime - scaled_target) % prime;
    }

    let carry_forward_checks = candidate
        .hinge_directions
        .iter()
        .enumerate()
        .map(|(index, direction)| {
            let residues = aggregate.hinges.get(direction).copied().unwrap_or_default();
            CarryForwardCheck {
                index,
                direction: *direction,
                residues,
                zero_in_both_fields: residues == [0, 0],
            }
        })
        .collect::<Vec<_>>();
    let first_carry_forward_failure = carry_forward_checks
        .iter()
        .position(|check| !check.zero_in_both_fields);

    let residuals = residuals_with_additive(&aggregate.hinges, None);
    let nonzero_hinges = residuals.len();
    let diagnostic_selected = residuals.iter().take(K).cloned().collect::<Vec<_>>();
    let selected = if first_carry_forward_failure.is_none() {
        ensure!(
            diagnostic_selected.len() == K.min(nonzero_hinges),
            "selected-prefix census drift"
        );
        diagnostic_selected.clone()
    } else {
        Vec::new()
    };
    let selected_digest = digest_selected(&selected);
    let all_zero = std::array::from_fn(|field| {
        aggregate
            .hinges
            .values()
            .all(|residues| residues[field] == 0)
            && aggregate.linear[field].iter().all(|value| *value == 0)
    });

    let mutant_form = validated_full_normal_form(&input.records[candidate.terms[0].sequence])?;
    let base_carry_residues = carry_forward_checks
        .iter()
        .map(|check| check.residues)
        .collect::<Vec<_>>();
    let mutant_carry_residues = candidate
        .hinge_directions
        .iter()
        .map(|direction| {
            let base = aggregate.hinges.get(direction).copied().unwrap_or_default();
            let added = mutant_form
                .hinges
                .get(direction)
                .copied()
                .unwrap_or_default();
            std::array::from_fn(|field| {
                (base[field] + added.rem_euclid(PRIMES[field] as i64) as u64) % PRIMES[field]
            })
        })
        .collect::<Vec<[u64; 2]>>();
    let mutant_carry_matches = mutant_carry_residues == base_carry_residues;
    let mut mutant_linear = aggregate.linear;
    for (field, &prime) in PRIMES.iter().enumerate() {
        for (rank, &value) in mutant_form.linear.iter().enumerate() {
            mutant_linear[field][rank] =
                (mutant_linear[field][rank] + value.rem_euclid(prime as i64) as u64) % prime;
        }
    }
    let mutant_residuals = residuals_with_additive(&aggregate.hinges, Some(&mutant_form));
    let mutant_selected = mutant_residuals.iter().take(K).cloned().collect::<Vec<_>>();
    let mutant_linear_matches = mutant_linear == aggregate.linear;
    let mutant_nonzero_matches = mutant_residuals.len() == nonzero_hinges;
    let mutant_selected_matches = mutant_selected == diagnostic_selected;
    let mutant_rejected = !mutant_carry_matches
        || !mutant_linear_matches
        || !mutant_nonzero_matches
        || !mutant_selected_matches;
    ensure!(mutant_rejected, "planted +1 coefficient mutant survived");

    let (exact_selected_prices, exact_price_digest) = exact_prices(&input, &candidate, &selected)?;
    let first_nonzero_linear_index = if first_carry_forward_failure.is_none() && nonzero_hinges == 0
    {
        (0..N).find(|&coordinate| {
            aggregate.linear[0][coordinate] != 0 || aggregate.linear[1][coordinate] != 0
        })
    } else {
        None
    };
    let first_nonzero_linear = if let Some(coordinate) = first_nonzero_linear_index {
        let exact = exact_linear_residual(&input, &candidate, coordinate)?;
        let raw = exact.to_string();
        ensure!(
            [decimal_mod(&raw, PRIMES[0])?, decimal_mod(&raw, PRIMES[1])?]
                == [
                    aggregate.linear[0][coordinate],
                    aggregate.linear[1][coordinate]
                ],
            "exact linear modular bridge failed"
        );
        Some(ExactLinear {
            coordinate,
            coefficient: raw,
        })
    } else {
        None
    };

    let exact_replay = if all_zero == [true, true] && first_carry_forward_failure.is_none() {
        exact_full_replay(&input, &candidate)?
    } else {
        ExactReplay {
            performed: false,
            result: "NOT_TRIGGERED_MODULAR_NONZERO",
            terms: 0,
            hinge_entries_processed: 0,
            labelled_permutations_checked: 0,
            aggregate_hinge_support: 0,
            nonzero_hinge_directions: 0,
            first_nonzero_hinge: None,
            linear_residuals_after_target: Vec::new(),
            first_nonzero_linear: None,
        }
    };

    let result = if first_carry_forward_failure.is_some() {
        "CARRY_FORWARD_REPLAY_DEFECT"
    } else if nonzero_hinges != 0 || first_nonzero_linear.is_some() {
        "GLOBAL_MODULAR_RESIDUAL"
    } else {
        exact_replay.result
    };
    ensure!(
        result != "NOT_TRIGGERED_MODULAR_NONZERO",
        "terminal two-prime-zero result forbidden"
    );

    // Recheck all binding-clean source inputs after the expensive computation.
    let end_bindings = validate_inputs(&input_path, &candidate_path, &input, &candidate)?;
    ensure!(bindings == end_bindings, "input/source drift during replay");
    bindings.insert(
        "output_protocol".to_string(),
        "pre-serialized_same-directory_O_EXCL_temp_then_atomic_no-overwrite_hard-link_after_all_controls_and_end_binding_recheck".to_string(),
    );

    let output = Output {
        schema: "max11-g0126-global-replay-v1",
        result,
        claim_boundary: "A modular or exact nonzero residual refutes only the bound 131-term candidate. Exact global zero would establish the frozen symmetric orbit identity, pending independent replay and architecture compilation; no result proves family completeness, an unrestricted lower bound, induction, or a Lean theorem.",
        bindings,
        candidate_schema: candidate.schema,
        candidate_result: candidate.result,
        target_scale: candidate.target_scale,
        primes: PRIMES,
        batch_k: K,
        selection_rule: SELECTION_RULE,
        complete_global_replay: true,
        terms: aggregate.terms,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        aggregate_hinge_support: aggregate.hinges.len(),
        nonzero_hinge_residue_directions: nonzero_hinges,
        carry_forward_checks,
        first_carry_forward_failure,
        linear_residues_after_target: aggregate.linear,
        all_hinge_and_linear_residues_zero: all_zero,
        selected_count: selected.len(),
        selected_prefix_i8_u64_le_sha256: selected_digest,
        selected,
        exact_selected_prices_decimal_lf_sha256: exact_price_digest,
        exact_selected_prices,
        first_nonzero_linear,
        exact_replay,
        coefficient_plus_one_mutant: MutantControl {
            sequence: candidate.terms[0].sequence,
            coefficient_delta: "+1",
            carry_forward_residues_match: mutant_carry_matches,
            linear_residues_match: mutant_linear_matches,
            nonzero_hinge_count_matches: mutant_nonzero_matches,
            selected_prefix_matches: mutant_selected_matches,
            rejected: mutant_rejected,
        },
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let stdout = serde_json::to_string(&output)?;
    let mut serialized = serde_json::to_vec_pretty(&output)?;
    serialized.push(b'\n');
    publish_exclusive(&output_path, &serialized)?;
    println!("{stdout}");
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    if args.len() == 2 && args[1] == "--self-test" {
        self_test()?;
        println!("G-0126 self-test PASS");
        return Ok(());
    }
    ensure!(
        args.len() == 4,
        "usage: g0126-global-replay PANEL_INPUT.json CANDIDATE.json OUTPUT.json | --self-test"
    );
    run(
        PathBuf::from(&args[1]),
        PathBuf::from(&args[2]),
        PathBuf::from(&args[3]),
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
    fn exact_decimal_bridge_handles_large_signed_values() {
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
