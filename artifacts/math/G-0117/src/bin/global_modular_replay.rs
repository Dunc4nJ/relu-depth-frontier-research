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

#[path = "../cegis_provenance.rs"]
mod cegis_provenance;
#[path = "../g0118_provenance.rs"]
mod g0118_provenance;

use cegis_provenance::{CertificateTerm, SourceCegis, V3_CLAIM_BOUNDARY, V3_SCHEMA};
use g0118_provenance::{G0118_V3_CLAIM_BOUNDARY, G0118_V3_SCHEMA, SourcePrefixCegis};

const PRIMES: [u64; 2] = [1_000_000_007, 1_000_000_009];
const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const POSTPROCESSOR_SHA256: &str =
    "07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48";
const V2_CLAIM_BOUNDARY: &str = "Denominator-cleared exact-Q finite-panel seed for complete global replay; not a global identity, family-completeness theorem, or MAX11 result.";
const COMPILED_PRODUCER: &[u8] = include_bytes!("global_modular_replay.rs");
const COMPILED_KERNEL: &[u8] = include_bytes!("../lib.rs");
const COMPILED_UNIQUENESS_LEMMA: &[u8] = include_bytes!("../../NORMAL_FORM_UNIQUENESS_LEMMA.md");

#[derive(Deserialize)]
struct PanelInput {
    schema: String,
    records: Vec<Record>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Certificate {
    schema: String,
    #[serde(default)]
    claim_boundary: Option<String>,
    #[serde(default)]
    source_exact_postprocess: Option<SourceExactPostprocess>,
    #[serde(default)]
    source_cegis: Option<SourceCegis>,
    #[serde(default)]
    source_prefix_cegis: Option<SourcePrefixCegis>,
    #[serde(default)]
    target_scale: Option<String>,
    terms: Vec<CertificateTerm>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceExactPostprocess {
    sha256: String,
    schema: String,
    result: String,
    bindings: SourceBindings,
    verification: SourceVerification,
}

#[derive(Deserialize, PartialEq)]
#[serde(deny_unknown_fields)]
struct SourceBindings {
    input: String,
    rows: String,
    report: String,
    retained: String,
    producer: String,
    preregistration: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct SourceVerification {
    decision_projection_recomputed: bool,
    postprocess_sha256: String,
    python_executable_sha256: String,
    actual_artifact_bindings: SourceBindings,
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
    certificate_schema: String,
    source_provenance_sha256: Option<String>,
    target_scale: String,
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

fn sha256_bytes(value: &[u8]) -> String {
    format!("{:x}", Sha256::digest(value))
}

fn canonical_sha256(raw: &str) -> bool {
    raw.len() == 64
        && raw
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
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
    let input_sha256 = sha256_path(&input_path)?;
    ensure!(input_sha256 == INPUT_SHA256, "panel-input binding drift");
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let certificate: Certificate =
        serde_json::from_reader(BufReader::new(File::open(&certificate_path)?))?;
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1",
        "panel-input schema drift"
    );
    ensure!(
        certificate.schema == "max11-g0117-global-replay-certificate-v1"
            || certificate.schema == "max11-g0117-global-replay-certificate-v2"
            || certificate.schema == V3_SCHEMA
            || certificate.schema == G0118_V3_SCHEMA,
        "certificate schema drift"
    );
    ensure!(!certificate.terms.is_empty(), "empty certificate");
    let mut v3_evidence_bindings = BTreeMap::new();
    let (target_scale, source_provenance_sha256) = match certificate.schema.as_str() {
        "max11-g0117-global-replay-certificate-v1" => {
            ensure!(
                certificate.target_scale.is_none(),
                "v1 certificate must have implicit target scale one"
            );
            ensure!(
                certificate.claim_boundary.is_none()
                    && certificate.source_exact_postprocess.is_none()
                    && certificate.source_cegis.is_none()
                    && certificate.source_prefix_cegis.is_none(),
                "v1 certificate contains v2 provenance fields"
            );
            ("1".to_string(), None)
        }
        "max11-g0117-global-replay-certificate-v2" => {
            ensure!(
                certificate.source_cegis.is_none() && certificate.source_prefix_cegis.is_none(),
                "v2 contains newer provenance"
            );
            ensure!(
                certificate.claim_boundary.as_deref() == Some(V2_CLAIM_BOUNDARY),
                "v2 claim boundary drift"
            );
            let source = certificate
                .source_exact_postprocess
                .as_ref()
                .context("v2 certificate missing exact-postprocess provenance")?;
            ensure!(
                canonical_sha256(&source.sha256),
                "v2 source postprocess hash drift"
            );
            ensure!(
                source.schema == "max11-g0113-panel-exact-postprocess-v1"
                    && source.result == "EXACT_Q_MEMBER_FINITE_PANEL",
                "v2 source exact-postprocess identity drift"
            );
            ensure!(
                source.bindings.input == input_sha256
                    && source.bindings.producer == POSTPROCESSOR_SHA256,
                "v2 source input/producer binding drift"
            );
            ensure!(
                source.verification.decision_projection_recomputed
                    && source.verification.postprocess_sha256 == source.sha256
                    && canonical_sha256(&source.verification.python_executable_sha256)
                    && source.verification.actual_artifact_bindings == source.bindings,
                "v2 source clean-recomputation binding drift"
            );
            for value in [
                &source.bindings.rows,
                &source.bindings.report,
                &source.bindings.retained,
                &source.bindings.preregistration,
            ] {
                ensure!(canonical_sha256(value), "v2 source binding hash drift");
            }
            let value = certificate
                .target_scale
                .as_deref()
                .context("v2 certificate missing target scale")?;
            ensure!(
                canonical_positive_integer(value),
                "v2 target scale must be a canonical positive integer"
            );
            for term in &certificate.terms {
                ensure!(
                    canonical_integer(&term.coefficient) && term.coefficient != "0",
                    "v2 coefficients must be nonzero canonical integers"
                );
            }
            (value.to_string(), Some(source.sha256.clone()))
        }
        V3_SCHEMA => {
            ensure!(
                certificate.claim_boundary.as_deref() == Some(V3_CLAIM_BOUNDARY),
                "v3 claim boundary drift"
            );
            ensure!(
                certificate.source_exact_postprocess.is_none()
                    && certificate.source_prefix_cegis.is_none(),
                "G-0117 v3 contains another provenance shape"
            );
            let source = certificate
                .source_cegis
                .as_ref()
                .context("v3 certificate missing fresh-Q provenance")?;
            let value = certificate
                .target_scale
                .as_deref()
                .context("v3 certificate missing target scale")?;
            let validated = cegis_provenance::validate_v3(
                source,
                &certificate.terms,
                value,
                &input_sha256,
                &input.records,
            )?;
            v3_evidence_bindings = validated.evidence_bindings;
            (
                validated.target_scale.to_string(),
                Some(validated.source_sha256),
            )
        }
        G0118_V3_SCHEMA => {
            ensure!(
                certificate.claim_boundary.as_deref() == Some(G0118_V3_CLAIM_BOUNDARY),
                "G-0118 v3 claim boundary drift"
            );
            ensure!(
                certificate.source_exact_postprocess.is_none()
                    && certificate.source_cegis.is_none(),
                "G-0118 v3 contains another provenance shape"
            );
            let source = certificate
                .source_prefix_cegis
                .as_ref()
                .context("G-0118 v3 missing prefix-CEGIS provenance")?;
            let value = certificate
                .target_scale
                .as_deref()
                .context("G-0118 v3 missing target scale")?;
            let validated = g0118_provenance::validate_g0118_v3(
                source,
                &certificate.terms,
                value,
                &input_sha256,
                input.records.len(),
            )?;
            v3_evidence_bindings = validated.evidence_bindings;
            (
                validated.target_scale.to_string(),
                Some(validated.source_sha256),
            )
        }
        _ => unreachable!(),
    };
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
        let scaled_target = (target % prime) * decimal_mod(&target_scale, prime)? % prime;
        linear[field][N - 1] = (linear[field][N - 1] + prime - scaled_target) % prime;
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
    let producer_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/bin/global_modular_replay.rs"
    ));
    let kernel_path = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/lib.rs"));
    let uniqueness_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/NORMAL_FORM_UNIQUENESS_LEMMA.md"
    ));
    let producer_sha256 = sha256_path(producer_path)?;
    let kernel_sha256 = sha256_path(kernel_path)?;
    let uniqueness_sha256 = sha256_path(uniqueness_path)?;
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
    let mut bindings = BTreeMap::new();
    bindings.insert("panel_input".to_string(), input_sha256);
    bindings.insert("certificate".to_string(), sha256_path(&certificate_path)?);
    bindings.insert("kernel".to_string(), kernel_sha256);
    bindings.insert("producer".to_string(), producer_sha256);
    bindings.insert("normal_form_uniqueness".to_string(), uniqueness_sha256);
    bindings.extend(v3_evidence_bindings);
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve current executable")?)?,
    );
    let output = Output {
        schema: "max11-g0117-global-modular-replay-v1",
        result,
        claim_boundary: "A nonzero modular residual exactly refutes this rational seed as a global identity. Two-prime zero is not an exact-Q identity and requires a deterministic integer bound or exact replay. Neither outcome proves family completeness or all-n.",
        bindings,
        certificate_schema: certificate.schema,
        source_provenance_sha256,
        target_scale,
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_integer_parser_is_fail_closed() {
        for accepted in ["0", "1", "-1", "14", "-600000000000000000000"] {
            assert!(canonical_integer(accepted));
        }
        for rejected in ["", "+1", "00", "01", "-0", "-01", "1/2", " 1", "1 "] {
            assert!(!canonical_integer(rejected));
        }
        assert!(canonical_positive_integer("14"));
        for rejected in ["0", "-1", "01", "1/2"] {
            assert!(!canonical_positive_integer(rejected));
        }
    }

    #[test]
    fn denominator_clearing_is_fieldwise_equivalent() {
        for prime in PRIMES {
            let scale = decimal_mod("14", prime).unwrap();
            assert_eq!(
                fraction_mod("1/2", prime).unwrap() * scale % prime,
                decimal_mod("7", prime).unwrap()
            );
            assert_eq!(
                fraction_mod("-3/7", prime).unwrap() * scale % prime,
                decimal_mod("-6", prime).unwrap()
            );
            let target = (1..=N as u64).product::<u64>() % prime;
            assert_eq!(target * scale % prime, target * 14 % prime);
            assert_ne!(
                (decimal_mod("7", prime).unwrap() + 1) % prime,
                decimal_mod("7", prime).unwrap()
            );
        }
    }
}
