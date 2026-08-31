use crate::cegis_provenance::CertificateTerm;
use anyhow::{Context, Result, ensure};
use num_bigint::BigInt;
use num_traits::Zero;
use serde::Deserialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::File;
use std::io::Read;
use std::path::{Component, Path, PathBuf};

pub const G0118_V3_SCHEMA: &str = "max11-g0118-global-replay-certificate-v3";
pub const G0118_V3_CLAIM_BOUNDARY: &str = "Denominator-cleared exact 314-row G-0118 prefix member admitted to complete global replay; not a global identity, subset/full-family completeness theorem, or MAX11 result.";

const RESULT_SCHEMA: &str = "max11-g0118-prefix-exact-cegis-iteration2-v1";
const RESULT_MEMBER: &str = "PREFIX_EXACT_Q_MEMBER_ALL_314_ROWS";
const RESULT_BOUNDARY: &str = "Exact 314-row membership in the frozen prefix-plus-panel-basis subset; not a global identity, full-family decision, family-completeness result, or MAX11 theorem.";
const RECORDS: usize = 163_740;
const ROWS: usize = 314;
const FAMILY_SEQUENCES: usize = 40_003;
const SUPPORT_RANK: usize = 123;
const PREFIX_RECORDS: usize = 40_000;
const PREFIX_BYTES: u64 = 192_640_000;
const PREFIX_SHA256: &str = "d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde";
const SPEC_SHA256: &str = "bde1936ab2eeb03cc211eea83d42aef26eff48d8add1e045fe192804087ffa58";
const DIRECTIONS: [[i8; 11]; 2] = [
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3],
];

const COMPILED_VALIDATOR: &[u8] = include_bytes!("g0118_provenance.rs");
const COMPILED_SPEC: &[u8] =
    include_bytes!("../../G-0118/ITERATION2_GLOBAL_REPLAY_V3_ADAPTER_SPEC.md");

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PrefixReceipt {
    pub rows: usize,
    pub family_sequences: usize,
    pub support_rank: usize,
    pub selected_basis_sha256: String,
    pub all_rows_replayed: bool,
    pub coefficient_mutant_rejected: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourcePrefixCegis {
    pub sha256: String,
    pub result_path: String,
    pub schema: String,
    pub result: String,
    pub recheck_sha256: String,
    pub recheck_path: String,
    pub preregistration_sha256: String,
    pub preregistration_path: String,
    pub runner_sha256: String,
    pub runner_path: String,
    pub solver_executable_sha256: String,
    pub solver_executable_path: String,
    pub cache_prefix_path: String,
    pub cache_prefix_bytes: u64,
    pub cache_prefix_sha256: String,
    pub adapter_spec_sha256: String,
    pub adapter_spec_path: String,
    pub bindings: BTreeMap<String, String>,
    pub receipt: PrefixReceipt,
}

pub struct ValidatedPrefix {
    pub target_scale: BigInt,
    pub source_sha256: String,
    pub evidence_bindings: BTreeMap<String, String>,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PrefixResult {
    schema: String,
    result: String,
    claim_boundary: String,
    bindings: BTreeMap<String, String>,
    preregistration_sha256: String,
    runner_sha256: String,
    prefix_sha256: String,
    prefix_records: usize,
    family_sequences: usize,
    support_sequences: Vec<usize>,
    coordinate_rows: Vec<usize>,
    selected_basis_sha256: String,
    hinge_directions: [[i8; 11]; 2],
    integer_coefficients: Vec<String>,
    target_scale: String,
    terms: Vec<CertificateTerm>,
    trials: Vec<Value>,
    all_314_rows_replayed: bool,
    coefficient_plus_one_mutant_rejected: bool,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

fn workspace_root() -> Result<PathBuf> {
    Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .and_then(Path::parent)
        .and_then(Path::parent)
        .map(Path::to_path_buf)
        .context("resolve repository root")
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

fn sha256_prefix(path: &Path, bytes: u64) -> Result<String> {
    let mut source = File::open(path).with_context(|| format!("open {}", path.display()))?;
    ensure!(
        source.metadata()?.len() >= bytes,
        "cache prefix is truncated"
    );
    let mut remaining = bytes;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    while remaining > 0 {
        let limit = usize::try_from(remaining.min(buffer.len() as u64))?;
        source.read_exact(&mut buffer[..limit])?;
        digest.update(&buffer[..limit]);
        remaining -= limit as u64;
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
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

fn safe_relative(root: &Path, raw: &str) -> Result<PathBuf> {
    let relative = Path::new(raw);
    ensure!(
        !raw.is_empty() && !relative.is_absolute(),
        "path must be relative"
    );
    ensure!(
        relative
            .components()
            .all(|component| matches!(component, Component::Normal(_))),
        "path is not canonical or contains traversal"
    );
    let output = root.join(relative);
    ensure!(
        output.exists(),
        "bound path is missing: {}",
        output.display()
    );
    Ok(output)
}

fn load_value_and_result(path: &Path) -> Result<(Value, PrefixResult)> {
    let value: Value = serde_json::from_reader(File::open(path)?)?;
    let result = serde_json::from_value(value.clone())?;
    Ok((value, result))
}

fn decision_projection(mut value: Value) -> Result<Value> {
    let object = value
        .as_object_mut()
        .context("prefix result is not an object")?;
    ensure!(object.remove("wall_seconds").is_some(), "missing wall time");
    ensure!(object.remove("maximum_rss_kib").is_some(), "missing RSS");
    Ok(value)
}

fn validate_source_file(
    root: &Path,
    relative: &str,
    expected: &str,
    label: &str,
) -> Result<PathBuf> {
    ensure!(canonical_sha256(expected), "{label} is not a SHA-256");
    let path = safe_relative(root, relative)?;
    ensure!(sha256_path(&path)? == expected, "{label} binding drift");
    Ok(path)
}

pub fn validate_g0118_v3(
    source: &SourcePrefixCegis,
    certificate_terms: &[CertificateTerm],
    certificate_target_scale: &str,
    panel_input_sha256: &str,
    records: usize,
) -> Result<ValidatedPrefix> {
    ensure!(records == RECORDS, "record census drift");
    ensure!(
        source.schema == RESULT_SCHEMA && source.result == RESULT_MEMBER,
        "G-0118 source identity drift"
    );
    ensure!(
        canonical_positive_integer(certificate_target_scale),
        "G-0118 target scale is not a canonical positive integer"
    );
    let root = workspace_root()?;
    let primary_path = validate_source_file(&root, &source.result_path, &source.sha256, "primary")?;
    let recheck_path = validate_source_file(
        &root,
        &source.recheck_path,
        &source.recheck_sha256,
        "recheck",
    )?;
    let preregistration_path = validate_source_file(
        &root,
        &source.preregistration_path,
        &source.preregistration_sha256,
        "preregistration",
    )?;
    let runner_path =
        validate_source_file(&root, &source.runner_path, &source.runner_sha256, "runner")?;
    let executable_path = validate_source_file(
        &root,
        &source.solver_executable_path,
        &source.solver_executable_sha256,
        "solver executable",
    )?;
    let spec_path = validate_source_file(
        &root,
        &source.adapter_spec_path,
        &source.adapter_spec_sha256,
        "adapter spec",
    )?;
    ensure!(
        source.adapter_spec_sha256 == SPEC_SHA256 && sha256_bytes(COMPILED_SPEC) == SPEC_SHA256,
        "compiled adapter spec drift"
    );
    let cache_path = safe_relative(&root, &source.cache_prefix_path)?;
    ensure!(
        source.cache_prefix_bytes == PREFIX_BYTES
            && source.cache_prefix_sha256 == PREFIX_SHA256
            && sha256_prefix(&cache_path, PREFIX_BYTES)? == PREFIX_SHA256,
        "cache prefix binding drift"
    );

    let expected_binding_paths = BTreeSet::from([
        "artifacts/math/G-0113/panel_retained_columns_v1.json".to_string(),
        "artifacts/math/G-0113/panel_scan_v1.json".to_string(),
        "artifacts/math/G-0113/panel_solver_input_v1.json".to_string(),
        "artifacts/math/G-0117/fresh_q_cegis_exact.py".to_string(),
        "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json".to_string(),
        "artifacts/math/G-0118/iteration2_residual_coordinate_v1.json".to_string(),
        "artifacts/math/G-0118/prefix_exact_cegis.py".to_string(),
        "artifacts/math/G-0118/prefix_exact_cegis_v1.json".to_string(),
        "artifacts/math/G-0118/prefix_global_modular_replay_v1.json".to_string(),
    ]);
    ensure!(
        source.bindings.keys().cloned().collect::<BTreeSet<_>>() == expected_binding_paths,
        "G-0118 source binding path census drift"
    );
    for (relative, expected) in &source.bindings {
        validate_source_file(&root, relative, expected, "transitive input")?;
    }
    ensure!(
        source
            .bindings
            .get("artifacts/math/G-0113/panel_solver_input_v1.json")
            .is_some_and(|hash| hash == panel_input_sha256),
        "G-0118 panel input binding drift"
    );

    let (primary_value, primary) = load_value_and_result(&primary_path)?;
    let (recheck_value, recheck) = load_value_and_result(&recheck_path)?;
    ensure!(
        decision_projection(primary_value)? == decision_projection(recheck_value)?,
        "G-0118 deterministic recheck disagrees"
    );
    for result in [&primary, &recheck] {
        ensure!(
            result.schema == source.schema
                && result.result == source.result
                && result.claim_boundary == RESULT_BOUNDARY
                && result.bindings == source.bindings
                && result.preregistration_sha256 == source.preregistration_sha256
                && result.runner_sha256 == source.runner_sha256
                && result.prefix_sha256 == source.cache_prefix_sha256
                && result.prefix_records == PREFIX_RECORDS
                && result.family_sequences == FAMILY_SEQUENCES
                && result.hinge_directions == DIRECTIONS
                && result.all_314_rows_replayed
                && result.coefficient_plus_one_mutant_rejected,
            "G-0118 exact-result receipt drift"
        );
        ensure!(
            result.support_sequences.len() == SUPPORT_RANK
                && result
                    .support_sequences
                    .windows(2)
                    .all(|pair| pair[0] < pair[1])
                && result
                    .support_sequences
                    .iter()
                    .all(|sequence| *sequence < RECORDS)
                && result.coordinate_rows.len() == SUPPORT_RANK
                && result.coordinate_rows.iter().all(|row| *row < ROWS)
                && result
                    .coordinate_rows
                    .iter()
                    .copied()
                    .collect::<BTreeSet<_>>()
                    .len()
                    == SUPPORT_RANK,
            "G-0118 support/coordinate receipt drift"
        );
        ensure!(
            canonical_sha256(&result.selected_basis_sha256)
                && result.selected_basis_sha256 == source.receipt.selected_basis_sha256,
            "G-0118 selected-basis binding drift"
        );
    }
    ensure!(
        source.receipt.rows == ROWS
            && source.receipt.family_sequences == FAMILY_SEQUENCES
            && source.receipt.support_rank == SUPPORT_RANK
            && source.receipt.all_rows_replayed
            && source.receipt.coefficient_mutant_rejected,
        "G-0118 source receipt drift"
    );
    ensure!(
        primary.target_scale == certificate_target_scale
            && recheck.target_scale == certificate_target_scale
            && primary.terms == certificate_terms
            && recheck.terms == certificate_terms,
        "G-0118 certificate scale/term adapter drift"
    );
    ensure!(
        primary.integer_coefficients.len() == SUPPORT_RANK,
        "G-0118 integer coefficient census drift"
    );
    let parsed_integers = primary
        .integer_coefficients
        .iter()
        .map(|raw| parse_bigint(raw))
        .collect::<Result<Vec<_>>>()?;
    let expected_terms = primary
        .support_sequences
        .iter()
        .copied()
        .zip(&parsed_integers)
        .filter(|(_, coefficient)| !coefficient.is_zero())
        .collect::<Vec<_>>();
    ensure!(
        expected_terms.len() == certificate_terms.len(),
        "G-0118 nonzero term census drift"
    );
    for (term, (sequence, coefficient)) in certificate_terms.iter().zip(expected_terms) {
        ensure!(
            term.sequence == sequence
                && term.coefficient != "0"
                && canonical_integer(&term.coefficient)
                && parse_bigint(&term.coefficient)? == *coefficient,
            "G-0118 certificate terms differ from exact result"
        );
    }
    let target_scale = parse_bigint(certificate_target_scale)?;

    let validator_path = Path::new(env!("CARGO_MANIFEST_DIR")).join("src/g0118_provenance.rs");
    let validator_sha256 = sha256_path(&validator_path)?;
    ensure!(
        validator_sha256 == sha256_bytes(COMPILED_VALIDATOR),
        "G-0118 validator source drift"
    );
    Ok(ValidatedPrefix {
        target_scale,
        source_sha256: source.sha256.clone(),
        evidence_bindings: BTreeMap::from([
            ("g0118_primary_result".to_string(), source.sha256.clone()),
            ("g0118_recheck".to_string(), source.recheck_sha256.clone()),
            (
                "g0118_preregistration".to_string(),
                source.preregistration_sha256.clone(),
            ),
            ("g0118_runner".to_string(), source.runner_sha256.clone()),
            (
                "g0118_solver_executable".to_string(),
                source.solver_executable_sha256.clone(),
            ),
            (
                "g0118_cache_prefix".to_string(),
                source.cache_prefix_sha256.clone(),
            ),
            (
                "g0118_adapter_spec".to_string(),
                source.adapter_spec_sha256.clone(),
            ),
            ("g0118_provenance_validator".to_string(), validator_sha256),
            (
                "g0118_preregistration_path".to_string(),
                sha256_path(&preregistration_path)?,
            ),
            ("g0118_runner_path".to_string(), sha256_path(&runner_path)?),
            (
                "g0118_executable_path".to_string(),
                sha256_path(&executable_path)?,
            ),
            ("g0118_spec_path".to_string(), sha256_path(&spec_path)?),
        ]),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decision_projection_ignores_only_runtime_fields() {
        let first = serde_json::json!({"result":"x","wall_seconds":1.0,"maximum_rss_kib":2});
        let second = serde_json::json!({"result":"x","wall_seconds":9.0,"maximum_rss_kib":8});
        assert_eq!(
            decision_projection(first).unwrap(),
            decision_projection(second).unwrap()
        );
        let mutant = serde_json::json!({"result":"y","wall_seconds":9.0,"maximum_rss_kib":8});
        assert_ne!(
            decision_projection(
                serde_json::json!({"result":"x","wall_seconds":1.0,"maximum_rss_kib":2})
            )
            .unwrap(),
            decision_projection(mutant).unwrap()
        );
    }
}
