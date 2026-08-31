use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{FullNormalForm, N, Record, full_normal_form};
use num_bigint::BigInt;
use num_traits::Zero;
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

const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const POSTPROCESSOR_SHA256: &str =
    "07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48";
const V2_CERTIFICATE_SCHEMA: &str = "max11-g0117-global-replay-certificate-v2";
const V2_CLAIM_BOUNDARY: &str = "Denominator-cleared exact-Q finite-panel seed for complete global replay; not a global identity, family-completeness theorem, or MAX11 result.";
const COMPILED_PRODUCER: &[u8] = include_bytes!("global_exact_replay.rs");
const COMPILED_KERNEL: &[u8] = include_bytes!("../lib.rs");
const COMPILED_PREREGISTRATION: &[u8] =
    include_bytes!("../../EXACT_GLOBAL_REPLAY_PREREGISTRATION.md");
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
    claim_boundary: String,
    #[serde(default)]
    source_exact_postprocess: Option<SourceExactPostprocess>,
    #[serde(default)]
    source_cegis: Option<SourceCegis>,
    #[serde(default)]
    source_prefix_cegis: Option<SourcePrefixCegis>,
    target_scale: String,
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
            linear: std::array::from_fn(|_| BigInt::zero()),
            terms: 0,
            hinge_entries_processed: 0,
            labelled_permutations_checked: 0,
        }
    }
}

#[derive(Serialize)]
struct FirstHingeResidual {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Serialize)]
struct FirstLinearResidual {
    coordinate: usize,
    coefficient: String,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    certificate_schema: String,
    source_provenance_sha256: String,
    target_scale: String,
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations_checked: u64,
    aggregate_hinge_support_including_zeros: usize,
    exact_nonzero_hinge_directions: usize,
    first_hinge_residual: Option<FirstHingeResidual>,
    linear_residuals: [String; N],
    first_linear_residual: Option<FirstLinearResidual>,
    all_hinge_and_linear_residuals_exactly_zero: bool,
    wall_seconds: f64,
}

struct ValidatedCertificate {
    target_scale: BigInt,
    source_sha256: String,
    evidence_bindings: BTreeMap<String, String>,
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
    BigInt::parse_bytes(raw.as_bytes(), 10).context("parse arbitrary-precision integer")
}

fn validate_certificate(
    certificate: &Certificate,
    input_sha256: &str,
    records: &[Record],
) -> Result<ValidatedCertificate> {
    ensure!(!certificate.terms.is_empty(), "empty certificate");
    ensure!(
        canonical_positive_integer(&certificate.target_scale),
        "target scale must be a canonical positive integer"
    );
    let mut seen = vec![false; records.len()];
    for term in &certificate.terms {
        ensure!(term.sequence < records.len(), "sequence outside family");
        ensure!(!seen[term.sequence], "duplicate certificate sequence");
        seen[term.sequence] = true;
        ensure!(
            canonical_integer(&term.coefficient) && term.coefficient != "0",
            "coefficient must be a nonzero canonical integer"
        );
        parse_bigint(&term.coefficient)?;
    }
    match certificate.schema.as_str() {
        V2_CERTIFICATE_SCHEMA => {
            ensure!(
                certificate.claim_boundary == V2_CLAIM_BOUNDARY,
                "v2 claim boundary drift"
            );
            ensure!(
                certificate.source_cegis.is_none() && certificate.source_prefix_cegis.is_none(),
                "v2 contains newer provenance"
            );
            let source = certificate
                .source_exact_postprocess
                .as_ref()
                .context("v2 certificate missing exact-postprocess provenance")?;
            ensure!(
                canonical_sha256(&source.sha256),
                "source postprocess hash drift"
            );
            ensure!(
                source.schema == "max11-g0113-panel-exact-postprocess-v1"
                    && source.result == "EXACT_Q_MEMBER_FINITE_PANEL",
                "source exact-postprocess identity drift"
            );
            ensure!(
                source.bindings.input == input_sha256
                    && source.bindings.producer == POSTPROCESSOR_SHA256,
                "source input/producer binding drift"
            );
            for value in [
                &source.bindings.rows,
                &source.bindings.report,
                &source.bindings.retained,
                &source.bindings.preregistration,
            ] {
                ensure!(
                    canonical_sha256(value),
                    "source artifact binding hash drift"
                );
            }
            ensure!(
                source.verification.decision_projection_recomputed
                    && source.verification.postprocess_sha256 == source.sha256
                    && canonical_sha256(&source.verification.python_executable_sha256)
                    && source.verification.actual_artifact_bindings == source.bindings,
                "source clean-recomputation binding drift"
            );
            Ok(ValidatedCertificate {
                target_scale: parse_bigint(&certificate.target_scale)?,
                source_sha256: source.sha256.clone(),
                evidence_bindings: BTreeMap::new(),
            })
        }
        V3_SCHEMA => {
            ensure!(
                certificate.claim_boundary == V3_CLAIM_BOUNDARY,
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
            let validated = cegis_provenance::validate_v3(
                source,
                &certificate.terms,
                &certificate.target_scale,
                input_sha256,
                records,
            )?;
            Ok(ValidatedCertificate {
                target_scale: validated.target_scale,
                source_sha256: validated.source_sha256,
                evidence_bindings: validated.evidence_bindings,
            })
        }
        G0118_V3_SCHEMA => {
            ensure!(
                certificate.claim_boundary == G0118_V3_CLAIM_BOUNDARY,
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
            let validated = g0118_provenance::validate_g0118_v3(
                source,
                &certificate.terms,
                &certificate.target_scale,
                input_sha256,
                records.len(),
            )?;
            Ok(ValidatedCertificate {
                target_scale: validated.target_scale,
                source_sha256: validated.source_sha256,
                evidence_bindings: validated.evidence_bindings,
            })
        }
        _ => anyhow::bail!("certificate schema drift"),
    }
}

fn add_term(aggregate: &mut ExactAggregate, form: FullNormalForm, coefficient: &BigInt) {
    aggregate.terms += 1;
    aggregate.labelled_permutations_checked += form.labelled_permutations;
    aggregate.hinge_entries_processed += form.hinges.len() as u64;
    for (rank, value) in form.linear.into_iter().enumerate() {
        aggregate.linear[rank] += coefficient * BigInt::from(value);
    }
    for (direction, value) in form.hinges {
        *aggregate
            .hinges
            .entry(direction)
            .or_insert_with(BigInt::zero) += coefficient * BigInt::from(value);
    }
}

fn merge(mut left: ExactAggregate, right: ExactAggregate) -> ExactAggregate {
    if left.hinges.len() < right.hinges.len() {
        return merge(right, left);
    }
    left.terms += right.terms;
    left.hinge_entries_processed += right.hinge_entries_processed;
    left.labelled_permutations_checked += right.labelled_permutations_checked;
    for (target, value) in left.linear.iter_mut().zip(right.linear) {
        *target += value;
    }
    for (direction, value) in right.hinges {
        *left.hinges.entry(direction).or_insert_with(BigInt::zero) += value;
    }
    left
}

fn subtract_target(aggregate: &mut ExactAggregate, target_scale: &BigInt) {
    let factorial = (1..=N as u64).product::<u64>();
    aggregate.linear[N - 1] -= target_scale * BigInt::from(factorial);
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 4,
        "usage: global_exact_replay PANEL_INPUT.json CERTIFICATE_V2_OR_V3.json OUTPUT.json"
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
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1",
        "panel-input schema drift"
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
    let certificate: Certificate =
        serde_json::from_reader(BufReader::new(File::open(&certificate_path)?))?;
    let validated = validate_certificate(&certificate, &input_sha256, &input.records)?;
    let target_scale = validated.target_scale;

    let mut aggregate = certificate
        .terms
        .par_iter()
        .map(|term| -> Result<ExactAggregate> {
            let coefficient = parse_bigint(&term.coefficient)?;
            let form = full_normal_form(&input.records[term.sequence])?;
            let mut output = ExactAggregate::default();
            add_term(&mut output, form, &coefficient);
            Ok(output)
        })
        .try_reduce(
            ExactAggregate::default,
            |left, right| -> Result<ExactAggregate> { Ok(merge(left, right)) },
        )?;
    ensure!(
        aggregate.terms == certificate.terms.len(),
        "term census drift"
    );
    ensure!(
        aggregate.labelled_permutations_checked
            == certificate.terms.len() as u64 * (1..=N as u64).product::<u64>(),
        "permutation census drift"
    );
    subtract_target(&mut aggregate, &target_scale);

    let first_hinge = aggregate
        .hinges
        .iter()
        .filter(|(_, coefficient)| !coefficient.is_zero())
        .min_by_key(|(direction, _)| *direction)
        .map(|(direction, coefficient)| FirstHingeResidual {
            direction: *direction,
            coefficient: coefficient.to_string(),
        });
    let nonzero_hinges = aggregate
        .hinges
        .values()
        .filter(|coefficient| !coefficient.is_zero())
        .count();
    let first_linear = aggregate
        .linear
        .iter()
        .enumerate()
        .find(|(_, coefficient)| !coefficient.is_zero())
        .map(|(coordinate, coefficient)| FirstLinearResidual {
            coordinate,
            coefficient: coefficient.to_string(),
        });
    let exact_zero = nonzero_hinges == 0 && first_linear.is_none();

    let producer_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/src/bin/global_exact_replay.rs"
    ));
    let kernel_path = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/lib.rs"));
    let preregistration_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/EXACT_GLOBAL_REPLAY_PREREGISTRATION.md"
    ));
    let uniqueness_path = Path::new(concat!(
        env!("CARGO_MANIFEST_DIR"),
        "/NORMAL_FORM_UNIQUENESS_LEMMA.md"
    ));
    let producer_sha256 = sha256_path(producer_path)?;
    let kernel_sha256 = sha256_path(kernel_path)?;
    let preregistration_sha256 = sha256_path(preregistration_path)?;
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
        preregistration_sha256 == sha256_bytes(COMPILED_PREREGISTRATION),
        "running binary was compiled against a different preregistration"
    );
    ensure!(
        uniqueness_sha256 == sha256_bytes(COMPILED_UNIQUENESS_LEMMA),
        "running binary was compiled against a different uniqueness lemma"
    );
    let mut bindings = BTreeMap::new();
    bindings.insert("panel_input".to_string(), input_sha256);
    bindings.insert("certificate".to_string(), sha256_path(&certificate_path)?);
    bindings.insert("producer".to_string(), producer_sha256);
    bindings.insert("kernel".to_string(), kernel_sha256);
    bindings.insert("preregistration".to_string(), preregistration_sha256);
    bindings.insert("normal_form_uniqueness".to_string(), uniqueness_sha256);
    bindings.extend(validated.evidence_bindings);
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve current executable")?)?,
    );
    let output = Output {
        schema: "max11-g0117-global-exact-replay-v1",
        result: if exact_zero {
            "EXACT_GLOBAL_NORMAL_FORM_ZERO"
        } else {
            "EXACT_GLOBAL_NORMAL_FORM_RESIDUAL"
        },
        claim_boundary: "Exact integer replay of one denominator-cleared certificate over the fixed G-0113 family. Zero is an ordered-chamber normal-form identity pending symmetry and architecture compilation; nonzero is a normal-form residual pending the separately reviewed uniqueness lemma. Neither outcome proves family completeness or all-n.",
        bindings,
        certificate_schema: certificate.schema,
        source_provenance_sha256: validated.source_sha256,
        target_scale: target_scale.to_string(),
        terms: aggregate.terms,
        hinge_entries_processed: aggregate.hinge_entries_processed,
        labelled_permutations_checked: aggregate.labelled_permutations_checked,
        aggregate_hinge_support_including_zeros: aggregate.hinges.len(),
        exact_nonzero_hinge_directions: nonzero_hinges,
        first_hinge_residual: first_hinge,
        linear_residuals: std::array::from_fn(|index| aggregate.linear[index].to_string()),
        first_linear_residual: first_linear,
        all_hinge_and_linear_residuals_exactly_zero: exact_zero,
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

    fn synthetic_form(direction: [i8; N], hinge: i64, linear_last: i64) -> FullNormalForm {
        let mut hinges = HashMap::new();
        hinges.insert(direction, hinge);
        let mut linear = [0i64; N];
        linear[N - 1] = linear_last;
        FullNormalForm {
            linear,
            hinges,
            labelled_permutations: (1..=N as u64).product(),
        }
    }

    #[test]
    fn exact_accumulator_has_positive_and_negative_controls() {
        let direction = [0, 1, -2, 1, 0, 0, 0, 0, 0, 0, 0];
        let factorial = (1..=N as u64).product::<u64>() as i64;
        let mut zero = ExactAggregate::default();
        add_term(
            &mut zero,
            synthetic_form(direction, 3, factorial),
            &BigInt::from(2),
        );
        add_term(
            &mut zero,
            synthetic_form(direction, 3, 0),
            &BigInt::from(-2),
        );
        subtract_target(&mut zero, &BigInt::from(2));
        assert!(zero.hinges.values().all(Zero::is_zero));
        assert!(zero.linear.iter().all(Zero::is_zero));

        let mut hinge_mutant = ExactAggregate::default();
        add_term(
            &mut hinge_mutant,
            synthetic_form(direction, 3, factorial),
            &BigInt::from(2),
        );
        add_term(
            &mut hinge_mutant,
            synthetic_form(direction, 3, 0),
            &BigInt::from(-1),
        );
        subtract_target(&mut hinge_mutant, &BigInt::from(2));
        assert_eq!(hinge_mutant.hinges[&direction], BigInt::from(3));

        let mut linear_mutant = ExactAggregate::default();
        add_term(
            &mut linear_mutant,
            synthetic_form(direction, 0, factorial),
            &BigInt::from(2),
        );
        subtract_target(&mut linear_mutant, &BigInt::from(1));
        assert_eq!(linear_mutant.linear[N - 1], BigInt::from(factorial));
    }

    #[test]
    fn integer_and_unknown_field_parsers_are_fail_closed() {
        for accepted in ["0", "1", "-1", "999999999999999999999999999999999"] {
            assert!(canonical_integer(accepted));
            assert!(parse_bigint(accepted).is_ok());
        }
        for rejected in ["", "+1", "00", "01", "-0", "1/2", " 1"] {
            assert!(!canonical_integer(rejected));
            assert!(parse_bigint(rejected).is_err());
        }
        let unknown = r#"{
            "schema":"max11-g0117-global-replay-certificate-v2",
            "claim_boundary":"x",
            "source_exact_postprocess":{},
            "target_scale":"1",
            "terms":[],
            "unknown":1
        }"#;
        assert!(serde_json::from_str::<Certificate>(unknown).is_err());
    }
}
