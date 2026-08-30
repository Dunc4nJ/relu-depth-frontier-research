use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{FullNormalForm, N, Record, full_normal_form};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];

#[derive(Deserialize)]
struct PanelInput {
    schema: String,
    records: Vec<Record>,
}

#[derive(Clone, Deserialize)]
struct CertificateTerm {
    sequence: usize,
    coefficient: String,
}

#[derive(Deserialize)]
struct Certificate {
    schema: String,
    terms: Vec<CertificateTerm>,
}

#[derive(Default)]
struct Aggregate {
    hinges: HashMap<[i8; N], [u64; 2]>,
    linear: [[u64; N]; 2],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
}

#[derive(Serialize)]
struct FirstResidual {
    direction: [i8; N],
    residues: [u64; 2],
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    primes: [u64; 2],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support: usize,
    nonzero_hinge_residue_directions: usize,
    first_hinge_residual: Option<FirstResidual>,
    linear_residues_after_target: [[u64; N]; 2],
    all_hinge_and_linear_residues_zero: [bool; 2],
    wall_seconds: f64,
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut source = File::open(path)?;
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

fn decimal_mod(raw: &str, prime: u64) -> Result<u64> {
    ensure!(!raw.is_empty(), "empty integer");
    let (negative, digits) = raw
        .strip_prefix('-')
        .map_or((false, raw), |remainder| (true, remainder));
    ensure!(
        !digits.is_empty() && digits.bytes().all(|byte| byte.is_ascii_digit()),
        "malformed integer"
    );
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

fn modular_power(mut base: u64, mut exponent: u64, prime: u64) -> u64 {
    let mut output = 1u64;
    while exponent > 0 {
        if exponent & 1 == 1 {
            output = (output * base) % prime;
        }
        base = (base * base) % prime;
        exponent >>= 1;
    }
    output
}

fn fraction_mod(raw: &str, prime: u64) -> Result<u64> {
    let mut pieces = raw.split('/');
    let numerator = pieces.next().context("missing numerator")?;
    let denominator = pieces.next().unwrap_or("1");
    ensure!(pieces.next().is_none(), "malformed rational");
    let numerator = decimal_mod(numerator, prime)?;
    let denominator = decimal_mod(denominator, prime)?;
    ensure!(
        denominator != 0,
        "coefficient denominator vanishes modulo prime"
    );
    Ok((numerator * modular_power(denominator, prime - 2, prime)) % prime)
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

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 4,
        "usage: global_modular_replay PANEL_INPUT.json CERTIFICATE.json OUTPUT.json"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let input_path = PathBuf::from(&args[1]);
    let certificate_path = PathBuf::from(&args[2]);
    let output_path = PathBuf::from(&args[3]);
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let started = Instant::now();
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let certificate: Certificate =
        serde_json::from_reader(BufReader::new(File::open(&certificate_path)?))?;
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1",
        "panel-input schema drift"
    );
    ensure!(
        certificate.schema == "max11-g0117-global-replay-certificate-v1",
        "certificate schema drift"
    );
    ensure!(!certificate.terms.is_empty(), "empty certificate");
    ensure!(
        input
            .records
            .iter()
            .enumerate()
            .all(|(sequence, record)| record.sequence == sequence),
        "record sequence drift"
    );
    let mut seen = vec![false; input.records.len()];
    for term in &certificate.terms {
        ensure!(
            term.sequence < input.records.len(),
            "sequence outside family"
        );
        ensure!(!seen[term.sequence], "duplicate certificate sequence");
        seen[term.sequence] = true;
    }

    let aggregate = certificate
        .terms
        .par_iter()
        .map(|term| -> Result<Aggregate> {
            let coefficient = [
                fraction_mod(&term.coefficient, PRIMES[0])?,
                fraction_mod(&term.coefficient, PRIMES[1])?,
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
        aggregate.terms == certificate.terms.len(),
        "term census drift"
    );
    ensure!(
        aggregate.labelled_permutations_checked
            == certificate.terms.len() as u64 * (1..=N as u64).product::<u64>(),
        "permutation census drift"
    );

    let mut linear = aggregate.linear;
    let target = (1..=N as u64).product::<u64>();
    for (field, &prime) in PRIMES.iter().enumerate() {
        linear[field][N - 1] = (linear[field][N - 1] + prime - target % prime) % prime;
    }
    let first = aggregate
        .hinges
        .iter()
        .filter(|(_, residues)| residues[0] != 0 || residues[1] != 0)
        .min_by_key(|(direction, _)| *direction)
        .map(|(direction, residues)| FirstResidual {
            direction: *direction,
            residues: *residues,
        });
    let nonzero_hinges = aggregate
        .hinges
        .values()
        .filter(|residues| residues[0] != 0 || residues[1] != 0)
        .count();
    let all_zero = std::array::from_fn(|field| {
        aggregate
            .hinges
            .values()
            .all(|residues| residues[field] == 0)
            && linear[field].iter().all(|value| *value == 0)
    });
    let result = if all_zero == [true, true] {
        "TWO_PRIME_ZERO_PENDING_EXACT_BOUND"
    } else {
        "EXACT_GLOBAL_IDENTITY_REFUTED_BY_MODULAR_RESIDUAL"
    };
    let mut bindings = BTreeMap::new();
    bindings.insert("panel_input".to_string(), sha256_path(&input_path)?);
    bindings.insert("certificate".to_string(), sha256_path(&certificate_path)?);
    bindings.insert(
        "kernel".to_string(),
        sha256_path(Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/src/lib.rs"
        )))?,
    );
    bindings.insert(
        "producer".to_string(),
        sha256_path(Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/src/bin/global_modular_replay.rs"
        )))?,
    );
    let output = Output {
        schema: "max11-g0117-global-modular-replay-v1",
        result,
        claim_boundary: "A nonzero modular residual exactly refutes this rational seed as a global identity. Two-prime zero is not an exact-Q identity and requires a deterministic integer bound or exact replay. Neither outcome proves family completeness or all-n.",
        bindings,
        primes: PRIMES,
        terms: aggregate.terms,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        aggregate_hinge_support: aggregate.hinges.len(),
        nonzero_hinge_residue_directions: nonzero_hinges,
        first_hinge_residual: first,
        linear_residues_after_target: linear,
        all_hinge_and_linear_residues_zero: all_zero,
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
