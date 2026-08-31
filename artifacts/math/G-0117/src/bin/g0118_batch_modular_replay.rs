use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{FullNormalForm, N, Record, full_normal_form};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];
const K: usize = 32;
const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const CANDIDATE_SHA256: &str = "728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b";
const RECHECK_SHA256: &str = "f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f";
const CANDIDATE_PREREGISTRATION_SHA256: &str =
    "ec0d4dc70036c7f1b70cf37040a4c3c875b4217a2fb3c64d1ff2bf39176e351f";
const CANDIDATE_RUNNER_SHA256: &str =
    "8f364f384f070d5e061d8f61afe8374e8af5f5cac268fe3998d5bbf3c187d370";
const CANDIDATE_SCHEMA: &str = "max11-g0118-prefix-exact-cegis-accumulated-v1";
const CANDIDATE_RESULT: &str = "PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS";
const CANDIDATE_CLAIM: &str = "Exact 316-row membership in the frozen prefix-plus-panel-basis subset; not a global identity, full-family decision, family-completeness result, or MAX11 theorem.";
const SELECTION_RULE: &str = "After target subtraction, require accumulated d1..d4 zero in both fields; retain every hinge direction nonzero in either field; signed-i8 tuple lexicographic ascending; take first min(32,count).";
const ACCUMULATED_DIRECTIONS: [[i8; N]; 4] = [
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -3, 2],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1],
];

const COMPILED_PRODUCER: &[u8] = include_bytes!("g0118_batch_modular_replay.rs");
const COMPILED_KERNEL: &[u8] = include_bytes!("../lib.rs");
const COMPILED_UNIQUENESS_LEMMA: &[u8] = include_bytes!("../../NORMAL_FORM_UNIQUENESS_LEMMA.md");
const COMPILED_PREREGISTRATION: &[u8] =
    include_bytes!("../../../G-0118/BATCH32_ITERATION4_PREREGISTRATION.md");
const COMPILED_CANDIDATE: &[u8] =
    include_bytes!("../../../G-0118/prefix_exact_cegis_iteration4_v1.json");
const COMPILED_RECHECK: &[u8] =
    include_bytes!("../../../G-0118/prefix_exact_cegis_iteration4_recheck_v1.json");

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
    schema: String,
    result: String,
    claim_boundary: String,
    bindings: BTreeMap<String, String>,
    preregistration_path: String,
    preregistration_sha256: String,
    runner_sha256: String,
    prefix_sha256: String,
    prefix_records: usize,
    family_sequences: usize,
    manifest_path: String,
    manifest_sha256: String,
    iteration: usize,
    support_sequences: Vec<usize>,
    coordinate_rows: Vec<usize>,
    selected_basis_sha256: String,
    hinge_directions: Vec<[i8; N]>,
    integer_coefficients: Vec<String>,
    target_scale: String,
    terms: Vec<Term>,
    trials: Vec<Value>,
    all_rows_replayed: bool,
    coefficient_plus_one_mutant_rejected: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

#[derive(Default)]
struct Aggregate {
    hinges: HashMap<[i8; N], [u64; 2]>,
    linear: [[u64; N]; 2],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
}

#[derive(Clone, Debug, Serialize, PartialEq, Eq)]
struct Residual {
    direction: [i8; N],
    residues: [u64; 2],
}

#[derive(Serialize)]
struct AccumulatedCheck {
    direction: [i8; N],
    residues: [u64; 2],
    zero_in_both_fields: bool,
}

#[derive(Serialize)]
struct MutantControl {
    sequence: usize,
    coefficient_delta: &'static str,
    accumulated_rows_all_zero: bool,
    linear_residues_match: bool,
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
    accumulated_row_checks: Vec<AccumulatedCheck>,
    linear_residues_after_target: [[u64; N]; 2],
    all_hinge_and_linear_residues_zero: [bool; 2],
    selected_count: usize,
    selected_prefix_i8_u64_le_sha256: String,
    selected: Vec<Residual>,
    coefficient_plus_one_mutant: MutantControl,
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

fn nonzero_term_projection(sequences: &[usize], coefficients: &[String]) -> Result<Vec<Term>> {
    ensure!(
        sequences.len() == coefficients.len(),
        "basis coefficient census drift"
    );
    ensure!(
        coefficients
            .iter()
            .all(|coefficient| canonical_integer(coefficient)),
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

fn decimal_mod(raw: &str, prime: u64) -> Result<u64> {
    ensure!(canonical_integer(raw), "noncanonical integer");
    let (negative, digits) = raw
        .strip_prefix('-')
        .map_or((false, raw), |remainder| (true, remainder));
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

fn add_term(aggregate: &mut Aggregate, form: FullNormalForm, coefficient: [u64; 2]) {
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

fn merge(mut left: Aggregate, right: Aggregate) -> Aggregate {
    if left.hinges.len() < right.hinges.len() {
        return merge(right, left);
    }
    left.terms += right.terms;
    left.hinge_entries_processed += right.hinge_entries_processed;
    left.labelled_permutations_checked += right.labelled_permutations_checked;
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

fn selected_prefix(
    hinges: &HashMap<[i8; N], [u64; 2]>,
    additive_form: Option<&FullNormalForm>,
) -> Vec<Residual> {
    let mut keys = hinges.keys().copied().collect::<BTreeSet<_>>();
    if let Some(form) = additive_form {
        keys.extend(form.hinges.keys().copied());
    }
    keys.into_iter()
        .filter_map(|direction| {
            let mut residues = hinges.get(&direction).copied().unwrap_or_default();
            if let Some(value) = additive_form.and_then(|form| form.hinges.get(&direction)) {
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
        .take(K)
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

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 5,
        "usage: g0118_batch_modular_replay PANEL_INPUT.json CANDIDATE.json RECHECK.json OUTPUT.json"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let input_path = PathBuf::from(&args[1]);
    let candidate_path = PathBuf::from(&args[2]);
    let recheck_path = PathBuf::from(&args[3]);
    let output_path = PathBuf::from(&args[4]);
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let started = Instant::now();

    let input_sha256 = sha256_path(&input_path)?;
    let candidate_sha256 = sha256_path(&candidate_path)?;
    let recheck_sha256 = sha256_path(&recheck_path)?;
    ensure!(input_sha256 == INPUT_SHA256, "panel-input binding drift");
    ensure!(
        candidate_sha256 == CANDIDATE_SHA256,
        "candidate binding drift"
    );
    ensure!(recheck_sha256 == RECHECK_SHA256, "recheck binding drift");
    ensure!(
        candidate_sha256 == sha256_bytes(COMPILED_CANDIDATE),
        "binary was compiled against a different candidate"
    );
    ensure!(
        recheck_sha256 == sha256_bytes(COMPILED_RECHECK),
        "binary was compiled against a different recheck"
    );

    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let candidate: Candidate =
        serde_json::from_reader(BufReader::new(File::open(&candidate_path)?))?;
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
    ensure!(input.records.len() == 163_740, "record census drift");
    ensure!(
        input
            .records
            .iter()
            .enumerate()
            .all(|(sequence, record)| record.sequence == sequence),
        "record sequence drift"
    );
    ensure!(
        candidate.schema == CANDIDATE_SCHEMA
            && candidate.result == CANDIDATE_RESULT
            && candidate.claim_boundary == CANDIDATE_CLAIM,
        "candidate identity drift"
    );
    ensure!(
        candidate.preregistration_sha256 == CANDIDATE_PREREGISTRATION_SHA256
            && candidate.runner_sha256 == CANDIDATE_RUNNER_SHA256,
        "candidate producer provenance drift"
    );
    ensure!(
        candidate
            .bindings
            .get("artifacts/math/G-0113/panel_solver_input_v1.json")
            == Some(&input_sha256),
        "candidate panel binding drift"
    );
    ensure!(candidate.iteration == 4, "candidate iteration drift");
    ensure!(candidate.terms.len() == 102, "candidate term census drift");
    ensure!(
        candidate.hinge_directions == ACCUMULATED_DIRECTIONS,
        "candidate accumulated-direction drift"
    );
    ensure!(
        candidate.all_rows_replayed && candidate.coefficient_plus_one_mutant_rejected,
        "candidate exact-replay controls failed"
    );
    ensure!(
        canonical_positive_integer(&candidate.target_scale),
        "candidate target scale drift"
    );
    ensure!(
        candidate.terms
            == nonzero_term_projection(
                &candidate.support_sequences,
                &candidate.integer_coefficients,
            )?,
        "candidate term projection drift"
    );
    let mut seen = vec![false; input.records.len()];
    for term in &candidate.terms {
        ensure!(term.sequence < input.records.len(), "term outside family");
        ensure!(!seen[term.sequence], "duplicate term sequence");
        ensure!(
            canonical_integer(&term.coefficient) && term.coefficient != "0",
            "candidate coefficient drift"
        );
        seen[term.sequence] = true;
    }

    let mut aggregate = candidate
        .terms
        .par_iter()
        .map(|term| -> Result<Aggregate> {
            let coefficient = [
                decimal_mod(&term.coefficient, PRIMES[0])?,
                decimal_mod(&term.coefficient, PRIMES[1])?,
            ];
            let form = full_normal_form(&input.records[term.sequence])?;
            let mut output = Aggregate::default();
            add_term(&mut output, form, coefficient);
            Ok(output)
        })
        .try_reduce(Aggregate::default, |left, right| -> Result<Aggregate> {
            Ok(merge(left, right))
        })?;
    ensure!(
        aggregate.terms == candidate.terms.len(),
        "term census drift"
    );
    ensure!(
        aggregate.labelled_permutations_checked
            == candidate.terms.len() as u64 * (1..=N as u64).product::<u64>(),
        "permutation census drift"
    );

    let target = (1..=N as u64).product::<u64>();
    for (field, &prime) in PRIMES.iter().enumerate() {
        let scaled_target = (target % prime) * decimal_mod(&candidate.target_scale, prime)? % prime;
        aggregate.linear[field][N - 1] =
            (aggregate.linear[field][N - 1] + prime - scaled_target) % prime;
    }
    let accumulated_row_checks = ACCUMULATED_DIRECTIONS
        .iter()
        .map(|direction| {
            let residues = aggregate.hinges.get(direction).copied().unwrap_or_default();
            AccumulatedCheck {
                direction: *direction,
                residues,
                zero_in_both_fields: residues == [0, 0],
            }
        })
        .collect::<Vec<_>>();
    ensure!(
        accumulated_row_checks
            .iter()
            .all(|check| check.zero_in_both_fields),
        "accumulated-row replay defect"
    );

    let nonzero_hinges = aggregate
        .hinges
        .values()
        .filter(|residues| **residues != [0, 0])
        .count();
    let selected = selected_prefix(&aggregate.hinges, None);
    ensure!(
        selected.len() == K.min(nonzero_hinges),
        "selected-prefix census drift"
    );
    let all_zero = std::array::from_fn(|field| {
        aggregate
            .hinges
            .values()
            .all(|residues| residues[field] == 0)
            && aggregate.linear[field].iter().all(|value| *value == 0)
    });

    let mutant_form = full_normal_form(&input.records[candidate.terms[0].sequence])?;
    let mutant_accumulated_all_zero = ACCUMULATED_DIRECTIONS.iter().all(|direction| {
        let base = aggregate.hinges.get(direction).copied().unwrap_or_default();
        let added = mutant_form
            .hinges
            .get(direction)
            .copied()
            .unwrap_or_default();
        PRIMES.iter().enumerate().all(|(field, &prime)| {
            (base[field] + added.rem_euclid(prime as i64) as u64).is_multiple_of(prime)
        })
    });
    let mut mutant_linear = aggregate.linear;
    for (field, &prime) in PRIMES.iter().enumerate() {
        for (rank, &value) in mutant_form.linear.iter().enumerate() {
            mutant_linear[field][rank] =
                (mutant_linear[field][rank] + value.rem_euclid(prime as i64) as u64) % prime;
        }
    }
    let mutant_selected = selected_prefix(&aggregate.hinges, Some(&mutant_form));
    let mutant_linear_matches = mutant_linear == aggregate.linear;
    let mutant_selected_matches = mutant_selected == selected;
    let mutant_rejected =
        !mutant_accumulated_all_zero || !mutant_linear_matches || !mutant_selected_matches;
    ensure!(mutant_rejected, "planted +1 coefficient mutant survived");

    let producer_path = Path::new(concat!(
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
    let producer_sha256 = sha256_path(producer_path)?;
    let kernel_sha256 = sha256_path(kernel_path)?;
    let uniqueness_sha256 = sha256_path(uniqueness_path)?;
    let preregistration_sha256 = sha256_path(preregistration_path)?;
    ensure!(
        producer_sha256 == sha256_bytes(COMPILED_PRODUCER),
        "running binary was compiled from a different producer source"
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

    let mut bindings = BTreeMap::new();
    bindings.insert("panel_input".to_string(), input_sha256);
    bindings.insert("candidate".to_string(), candidate_sha256);
    bindings.insert("candidate_recheck".to_string(), recheck_sha256);
    bindings.insert("producer".to_string(), producer_sha256);
    bindings.insert("kernel".to_string(), kernel_sha256);
    bindings.insert("normal_form_uniqueness".to_string(), uniqueness_sha256);
    bindings.insert("preregistration".to_string(), preregistration_sha256);
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve current executable")?)?,
    );
    let result = if all_zero == [true, true] {
        "TWO_PRIME_ZERO_PENDING_EXACT_REPLAY"
    } else {
        "BATCH_RESIDUAL_PREFIX_SELECTED"
    };
    let output = Output {
        schema: "max11-g0118-batch32-global-modular-replay-v1",
        result,
        claim_boundary: "A nonzero two-prime residual exactly refutes candidate 4; selected rows are deterministic finite-family CEGIS inputs. Two-prime zero remains a screen. No outcome proves family completeness or MAX11.",
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
        accumulated_row_checks,
        linear_residues_after_target: aggregate.linear,
        all_hinge_and_linear_residues_zero: all_zero,
        selected_count: selected.len(),
        selected_prefix_i8_u64_le_sha256: digest_selected(&selected),
        selected,
        coefficient_plus_one_mutant: MutantControl {
            sequence: candidate.terms[0].sequence,
            coefficient_delta: "+1",
            accumulated_rows_all_zero: mutant_accumulated_all_zero,
            linear_residues_match: mutant_linear_matches,
            selected_prefix_matches: mutant_selected_matches,
            rejected: mutant_rejected,
        },
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let destination = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(output_path)?;
    let mut writer = BufWriter::new(destination);
    serde_json::to_writer_pretty(&mut writer, &output)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_integer_parser_is_fail_closed() {
        for valid in ["0", "1", "-1", "12345678901234567890"] {
            assert!(canonical_integer(valid));
        }
        for invalid in ["", "-", "+1", "00", "01", "-0", "-01", "1/2", " 1"] {
            assert!(!canonical_integer(invalid));
        }
    }

    #[test]
    fn selected_prefix_is_signed_lexicographic_and_bounded() {
        let mut hinges = HashMap::new();
        let first = [0, 0, 0, 0, 0, 0, 0, 1, -2, 0, 1];
        let second = [0, 0, 0, 0, 0, 0, 0, 1, -1, -1, 1];
        hinges.insert(second, [1, 0]);
        hinges.insert(first, [0, 1]);
        hinges.insert([1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0], [0, 0]);
        let selected = selected_prefix(&hinges, None);
        assert_eq!(selected.len(), 2);
        assert_eq!(selected[0].direction, first);
        assert_eq!(selected[1].direction, second);
    }

    #[test]
    fn selected_digest_rejects_reordering_and_residue_mutation() {
        let mut values = vec![
            Residual {
                direction: [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
                residues: [1, 2],
            },
            Residual {
                direction: [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3],
                residues: [3, 4],
            },
        ];
        let expected = digest_selected(&values);
        values.swap(0, 1);
        assert_ne!(digest_selected(&values), expected);
        values.swap(0, 1);
        values[0].residues[0] += 1;
        assert_ne!(digest_selected(&values), expected);
    }

    #[test]
    fn nonzero_term_projection_filters_only_canonical_zeroes() {
        let sequences = [3, 7, 9];
        let coefficients = ["5".to_string(), "0".to_string(), "-2".to_string()];
        let expected = vec![
            Term {
                sequence: 3,
                coefficient: "5".to_string(),
            },
            Term {
                sequence: 9,
                coefficient: "-2".to_string(),
            },
        ];
        assert_eq!(
            nonzero_term_projection(&sequences, &coefficients).unwrap(),
            expected
        );
        let mut zero_to_plus_one = coefficients.clone();
        zero_to_plus_one[1] = "1".to_string();
        assert_ne!(
            nonzero_term_projection(&sequences, &zero_to_plus_one).unwrap(),
            expected
        );
        assert!(
            nonzero_term_projection(&sequences, &["5".into(), "00".into(), "-2".into()]).is_err()
        );
    }
}
