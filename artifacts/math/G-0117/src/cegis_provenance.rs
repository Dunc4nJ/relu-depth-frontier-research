use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{N, Record, hinge_coefficient, linear_vector};
use num_bigint::BigInt;
use num_traits::{One, Signed, Zero};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::File;
use std::io::{BufReader, Read, Seek, SeekFrom};
use std::path::{Component, Path, PathBuf};

pub const V3_SCHEMA: &str = "max11-g0117-global-replay-certificate-v3";
pub const V3_CLAIM_BOUNDARY: &str = "Denominator-cleared fresh-Q member of the exact accumulated G-0117 CEGIS rows for complete global replay; not a global identity, family-completeness theorem, or MAX11 result.";

const RESULT_SCHEMA: &str = "max11-g0117-fresh-q-cegis-result-v1";
const RESULT_MEMBER: &str = "FRESH_Q_MEMBER_ALL_ROWS_REPLAYED";
const RESULT_CLAIM_BOUNDARY: &str = "Exact-Q membership on the complete accumulated 313-row iteration-1 system only; not a global identity, family-completeness theorem, or MAX11 result.";
const RECORDS: usize = 163_740;
const PANEL_ROWS: usize = 301;
const ROWS: usize = 313;
const ENTRY_BYTES: usize = 16;
const COLUMN_BYTES: usize = PANEL_ROWS * ENTRY_BYTES;
const CACHE_BYTES: u64 = (RECORDS * COLUMN_BYTES) as u64;
const DIRECTION: [i8; N] = [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4];
const V3_PREREGISTRATION_SHA256: &str =
    "57c43026da21ead61e9fc0a7330e763809e9bd565ce7854eef03ef14803a2c46";
const V3_PATH_ADDENDUM_SHA256: &str =
    "10756e6f9fd36d797dd52917523605ff4807fb13780164ed04547f83f75c9a4b";

const COMPILED_VALIDATOR: &[u8] = include_bytes!("cegis_provenance.rs");
const COMPILED_FRESH_SCANNER: &[u8] = include_bytes!("bin/fresh_q_cegis.rs");
const COMPILED_V3_PREREGISTRATION: &[u8] =
    include_bytes!("../ITERATION1_V3_CERTIFICATE_PREREGISTRATION.md");
const COMPILED_V3_PATH_ADDENDUM: &[u8] =
    include_bytes!("../ITERATION1_V3_CERTIFICATE_PATH_ADDENDUM.md");

#[derive(Clone, Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CertificateTerm {
    pub sequence: usize,
    pub coefficient: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CegisPaths {
    pub panel_input: String,
    pub panel_rows: String,
    pub cache_manifest: String,
    pub cache_payload: String,
    pub accumulated_rows: String,
    pub modular_scan: String,
    pub solver_source: String,
    pub solver_executable: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CegisBindings {
    pub panel_input: String,
    pub panel_rows: String,
    pub cache_manifest: String,
    pub cache_payload: String,
    pub accumulated_rows: String,
    pub modular_scan: String,
    pub solver_source: String,
    pub solver_executable: String,
}

#[derive(Debug, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CegisReceipt {
    pub rows: usize,
    pub columns: usize,
    pub descriptors_sha256: String,
    pub targets_sha256: String,
    pub selected_sequences_sha256: String,
    pub selected_basis_sha256: String,
    pub exact_replay_sha256: String,
    pub all_rows_replayed: bool,
    pub coefficient_mutant_rejected: bool,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct SourceCegis {
    pub sha256: String,
    pub result_path: String,
    pub schema: String,
    pub result: String,
    pub paths: CegisPaths,
    pub bindings: CegisBindings,
    pub receipt: CegisReceipt,
}

pub struct ValidatedCegis {
    pub target_scale: BigInt,
    pub source_sha256: String,
    pub evidence_bindings: BTreeMap<String, String>,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct FreshResult {
    schema: String,
    result: String,
    claim_boundary: String,
    paths: CegisPaths,
    bindings: CegisBindings,
    receipt: CegisReceipt,
    modular_scan_result: String,
    initial_selected_sequences: Vec<usize>,
    support_sequences: Vec<usize>,
    coordinate_rows: Vec<usize>,
    selected_basis_columns: Vec<Vec<i128>>,
    coefficients: Vec<String>,
    fresh_target_scale: String,
    integer_coefficients: Vec<String>,
    trials: Vec<serde_json::Value>,
    planted_controls: BTreeMap<String, bool>,
    wall_seconds: f64,
    maximum_rss_kib: u64,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct CacheManifest {
    schema: String,
    result: String,
    claim_boundary: String,
    bindings: BTreeMap<String, String>,
    records: usize,
    rows: usize,
    entry_bytes: usize,
    payload_bytes: u64,
    layout: String,
    integer_width: String,
    endianness: String,
    data_sha256: String,
    ordered_vector_digests_sha256: String,
    control_vector_sha256: BTreeMap<usize, String>,
    value_minimum: i128,
    value_maximum: i128,
    wall_seconds: f64,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AccumulatedRow {
    descriptor: String,
    values_i128_le_sha256: String,
    target: String,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct AccumulatedRows {
    schema: String,
    result: String,
    claim_boundary: String,
    bindings: BTreeMap<String, String>,
    rows: usize,
    columns: usize,
    descriptors_sha256: String,
    targets_i128_le_sha256: String,
    ordered_rows: Vec<AccumulatedRow>,
}

#[allow(dead_code)]
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct ModularScan {
    schema: String,
    result: String,
    claim_boundary: String,
    bindings: BTreeMap<String, String>,
    records_scanned: usize,
    rows: usize,
    panel_rows: usize,
    appended_rows: usize,
    direction: [i8; N],
    primes: Vec<serde_json::Value>,
    modular_ranks_agree: bool,
    modular_target_decisions_agree: bool,
    all_columns_reopened: bool,
    old_support_only: bool,
    wall_seconds: f64,
}

struct Rational {
    numerator: BigInt,
    denominator: BigInt,
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

fn gcd(mut left: BigInt, mut right: BigInt) -> BigInt {
    left = left.abs();
    right = right.abs();
    while !right.is_zero() {
        let remainder = &left % &right;
        left = right;
        right = remainder;
    }
    left
}

fn lcm(left: &BigInt, right: &BigInt) -> BigInt {
    (left / gcd(left.clone(), right.clone())) * right
}

fn parse_rational(raw: &str) -> Result<Rational> {
    let mut pieces = raw.split('/');
    let numerator_raw = pieces.next().context("missing rational numerator")?;
    let denominator_raw = pieces.next();
    ensure!(pieces.next().is_none(), "malformed rational");
    let numerator = parse_bigint(numerator_raw)?;
    let denominator = if let Some(raw) = denominator_raw {
        ensure!(
            canonical_positive_integer(raw),
            "noncanonical rational denominator"
        );
        let value = parse_bigint(raw)?;
        ensure!(
            value != BigInt::one(),
            "integer rational must omit denominator one"
        );
        value
    } else {
        BigInt::one()
    };
    ensure!(
        gcd(numerator.clone(), denominator.clone()) == BigInt::one(),
        "rational is not reduced"
    );
    ensure!(
        !numerator.is_zero() || denominator == BigInt::one(),
        "zero rational must be serialized as zero"
    );
    Ok(Rational {
        numerator,
        denominator,
    })
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
    let resolved = root.join(relative);
    ensure!(
        resolved.exists(),
        "bound path is missing: {}",
        resolved.display()
    );
    Ok(resolved)
}

fn descriptor_digest(values: impl IntoIterator<Item = String>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((value.len() as u64).to_le_bytes());
        digest.update(value.as_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn i128_digest(values: impl IntoIterator<Item = i128>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn u64_digest(values: impl IntoIterator<Item = usize>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((value as u64).to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn string_digest<'a>(values: impl IntoIterator<Item = &'a str>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((value.len() as u64).to_le_bytes());
        digest.update(value.as_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn check_compiled_evidence() -> Result<BTreeMap<String, String>> {
    let manifest = Path::new(env!("CARGO_MANIFEST_DIR"));
    let validator_path = manifest.join("src/cegis_provenance.rs");
    let scanner_path = manifest.join("src/bin/fresh_q_cegis.rs");
    let preregistration_path = manifest.join("ITERATION1_V3_CERTIFICATE_PREREGISTRATION.md");
    let addendum_path = manifest.join("ITERATION1_V3_CERTIFICATE_PATH_ADDENDUM.md");
    let validator = sha256_path(&validator_path)?;
    let scanner = sha256_path(&scanner_path)?;
    let preregistration = sha256_path(&preregistration_path)?;
    let addendum = sha256_path(&addendum_path)?;
    ensure!(
        validator == sha256_bytes(COMPILED_VALIDATOR),
        "v3 validator source drift"
    );
    ensure!(
        scanner == sha256_bytes(COMPILED_FRESH_SCANNER),
        "fresh scanner source drift"
    );
    ensure!(
        preregistration == V3_PREREGISTRATION_SHA256
            && preregistration == sha256_bytes(COMPILED_V3_PREREGISTRATION),
        "v3 preregistration drift"
    );
    ensure!(
        addendum == V3_PATH_ADDENDUM_SHA256 && addendum == sha256_bytes(COMPILED_V3_PATH_ADDENDUM),
        "v3 path addendum drift"
    );
    Ok(BTreeMap::from([
        ("v3_validator".to_string(), validator),
        ("fresh_modular_scanner".to_string(), scanner),
        ("v3_preregistration".to_string(), preregistration),
        ("v3_path_addendum".to_string(), addendum),
    ]))
}

fn validate_selected_basis(
    cache_path: &Path,
    result: &FreshResult,
    records: &[Record],
) -> Result<()> {
    ensure!(
        records.len() == RECORDS,
        "record census drift in v3 validation"
    );
    let support = result.support_sequences.len();
    ensure!(support > 0, "empty selected basis");
    ensure!(
        result.selected_basis_columns.len() == support
            && result.coefficients.len() == support
            && result.integer_coefficients.len() == support
            && result.coordinate_rows.len() == support,
        "selected basis dimension drift"
    );
    ensure!(
        result
            .selected_basis_columns
            .iter()
            .all(|column| column.len() == ROWS),
        "selected basis row dimension drift"
    );
    ensure!(
        result
            .support_sequences
            .windows(2)
            .all(|pair| pair[0] < pair[1])
            && result
                .support_sequences
                .iter()
                .all(|sequence| *sequence < RECORDS),
        "selected sequence order/range drift"
    );
    ensure!(
        result.coordinate_rows.iter().all(|row| *row < ROWS)
            && result
                .coordinate_rows
                .iter()
                .copied()
                .collect::<BTreeSet<_>>()
                .len()
                == support,
        "coordinate-row order/range drift"
    );

    let mut cache = File::open(cache_path)?;
    let mut raw = [0u8; COLUMN_BYTES];
    for (column_index, &sequence) in result.support_sequences.iter().enumerate() {
        cache.seek(SeekFrom::Start((sequence * COLUMN_BYTES) as u64))?;
        cache.read_exact(&mut raw)?;
        let stored = &result.selected_basis_columns[column_index];
        for (row, bytes) in raw.chunks_exact(ENTRY_BYTES).enumerate() {
            let value = i128::from_le_bytes(bytes.try_into().expect("fixed i128 width"));
            ensure!(stored[row] == value, "selected panel basis column drift");
        }
        let linear = linear_vector(&records[sequence])?;
        for (coordinate, value) in linear.into_iter().enumerate() {
            ensure!(
                stored[PANEL_ROWS + coordinate] == i128::from(value),
                "selected linear basis column drift"
            );
        }
        ensure!(
            stored[ROWS - 1] == i128::from(hinge_coefficient(&records[sequence], &DIRECTION)?),
            "selected hinge basis column drift"
        );
    }
    Ok(())
}

fn path_entries<'a>(
    paths: &'a CegisPaths,
    bindings: &'a CegisBindings,
) -> [(&'static str, &'a str, &'a str); 8] {
    [
        ("panel_input", &paths.panel_input, &bindings.panel_input),
        ("panel_rows", &paths.panel_rows, &bindings.panel_rows),
        (
            "cache_manifest",
            &paths.cache_manifest,
            &bindings.cache_manifest,
        ),
        (
            "cache_payload",
            &paths.cache_payload,
            &bindings.cache_payload,
        ),
        (
            "accumulated_rows",
            &paths.accumulated_rows,
            &bindings.accumulated_rows,
        ),
        ("modular_scan", &paths.modular_scan, &bindings.modular_scan),
        (
            "solver_source",
            &paths.solver_source,
            &bindings.solver_source,
        ),
        (
            "solver_executable",
            &paths.solver_executable,
            &bindings.solver_executable,
        ),
    ]
}

pub fn validate_v3(
    source: &SourceCegis,
    certificate_terms: &[CertificateTerm],
    certificate_target_scale: &str,
    panel_input_sha256: &str,
    records: &[Record],
) -> Result<ValidatedCegis> {
    ensure!(
        source.schema == RESULT_SCHEMA && source.result == RESULT_MEMBER,
        "v3 source result identity drift"
    );
    ensure!(
        canonical_sha256(&source.sha256),
        "v3 source result hash drift"
    );
    ensure!(
        canonical_positive_integer(certificate_target_scale),
        "v3 target scale must be a canonical positive integer"
    );
    let root = workspace_root()?;
    let mut actual_paths = BTreeMap::new();
    for (name, relative, expected) in path_entries(&source.paths, &source.bindings) {
        ensure!(
            canonical_sha256(expected),
            "v3 {name} binding is not a SHA-256"
        );
        let actual = safe_relative(&root, relative)?;
        ensure!(sha256_path(&actual)? == expected, "v3 {name} binding drift");
        actual_paths.insert(name, actual);
    }
    ensure!(
        source.bindings.panel_input == panel_input_sha256,
        "v3 panel-input binding drift"
    );

    let result_path = safe_relative(&root, &source.result_path)?;
    ensure!(
        sha256_path(&result_path)? == source.sha256,
        "v3 fresh-Q result binding drift"
    );
    let result: FreshResult = serde_json::from_reader(BufReader::new(File::open(&result_path)?))?;
    ensure!(
        result.schema == source.schema
            && result.result == source.result
            && result.claim_boundary == RESULT_CLAIM_BOUNDARY,
        "v3 fresh-Q result identity/boundary drift"
    );
    ensure!(
        result.paths == source.paths
            && result.bindings == source.bindings
            && result.receipt == source.receipt,
        "v3 duplicated source provenance drift"
    );
    ensure!(
        matches!(
            result.modular_scan_result.as_str(),
            "TWO_PRIME_MEMBER_PENDING_EXACT_Q" | "MODULAR_MISS_PENDING_EXACT_Q_COLUMN_GENERATION"
        ),
        "v3 modular-scan decision drift"
    );
    ensure!(
        result.planted_controls.get("old_support_freeze_rejected") == Some(&true)
            && result.planted_controls.get("stale_target_scale_rejected") == Some(&true),
        "v3 planted CEGIS controls failed"
    );

    let cache_path = &actual_paths["cache_payload"];
    ensure!(
        cache_path.metadata()?.len() == CACHE_BYTES,
        "v3 cache size drift"
    );
    let manifest: CacheManifest =
        serde_json::from_reader(BufReader::new(File::open(&actual_paths["cache_manifest"])?))?;
    ensure!(
        manifest.schema == "max11-g0117-full-family-panel-cache-v1"
            && manifest.result == "EXACT_PANEL_CACHE_REPRODUCED"
            && manifest.records == RECORDS
            && manifest.rows == PANEL_ROWS
            && manifest.entry_bytes == ENTRY_BYTES
            && manifest.payload_bytes == CACHE_BYTES
            && manifest.layout == "sequence-major: offset=((sequence*301)+row)*16"
            && manifest.integer_width == "signed i128"
            && manifest.endianness == "little"
            && manifest.data_sha256 == source.bindings.cache_payload
            && manifest.bindings.get("input") == Some(&source.bindings.panel_input)
            && manifest.bindings.get("rows") == Some(&source.bindings.panel_rows),
        "v3 cache manifest drift"
    );

    let row_document: AccumulatedRows = serde_json::from_reader(BufReader::new(File::open(
        &actual_paths["accumulated_rows"],
    )?))?;
    ensure!(
        row_document.schema == "max11-g0117-accumulated-rows-v1"
            && row_document.result == "EXACT_ORDERED_ROWS_BOUND"
            && row_document.rows == ROWS
            && row_document.columns == RECORDS
            && row_document.ordered_rows.len() == ROWS,
        "v3 accumulated-row document drift"
    );
    let expected_descriptors = (0..PANEL_ROWS)
        .map(|row| format!("panel:{row}"))
        .chain((0..N).map(|row| format!("linear:{row}")))
        .chain(std::iter::once("hinge:0,0,0,0,0,0,0,0,1,-5,4".to_string()))
        .collect::<Vec<_>>();
    ensure!(
        row_document
            .ordered_rows
            .iter()
            .map(|row| &row.descriptor)
            .eq(expected_descriptors.iter()),
        "v3 accumulated-row descriptor order drift"
    );
    let targets = row_document
        .ordered_rows
        .iter()
        .map(|row| {
            ensure!(
                canonical_integer(&row.target),
                "noncanonical accumulated-row target"
            );
            ensure!(
                canonical_sha256(&row.values_i128_le_sha256),
                "row-value digest drift"
            );
            row.target
                .parse::<i128>()
                .context("accumulated-row target exceeds i128")
        })
        .collect::<Result<Vec<_>>>()?;
    let descriptors_sha256 = descriptor_digest(expected_descriptors);
    let targets_sha256 = i128_digest(targets.iter().copied());
    ensure!(
        row_document.descriptors_sha256 == descriptors_sha256
            && row_document.targets_i128_le_sha256 == targets_sha256
            && source.receipt.descriptors_sha256 == descriptors_sha256
            && source.receipt.targets_sha256 == targets_sha256,
        "v3 accumulated-row receipt drift"
    );
    ensure!(
        row_document.bindings.get("panel_input") == Some(&source.bindings.panel_input)
            && row_document.bindings.get("panel_rows") == Some(&source.bindings.panel_rows)
            && row_document.bindings.get("cache_manifest") == Some(&source.bindings.cache_manifest)
            && row_document.bindings.get("cache_payload") == Some(&source.bindings.cache_payload),
        "v3 accumulated-row transitive binding drift"
    );

    let modular_scan: ModularScan =
        serde_json::from_reader(BufReader::new(File::open(&actual_paths["modular_scan"])?))?;
    ensure!(
        modular_scan.schema == "max11-g0117-fresh-modular-scan-v1"
            && modular_scan.result == result.modular_scan_result
            && modular_scan.records_scanned == RECORDS
            && modular_scan.rows == ROWS
            && modular_scan.panel_rows == PANEL_ROWS
            && modular_scan.appended_rows == ROWS - PANEL_ROWS
            && modular_scan.direction == DIRECTION
            && modular_scan.primes.len() == 2
            && modular_scan.modular_ranks_agree
            && modular_scan.modular_target_decisions_agree
            && modular_scan.all_columns_reopened
            && !modular_scan.old_support_only
            && modular_scan.bindings.get("accumulated_rows")
                == Some(&source.bindings.accumulated_rows)
            && modular_scan.bindings.get("panel_input") == Some(&source.bindings.panel_input)
            && modular_scan.bindings.get("panel_rows") == Some(&source.bindings.panel_rows)
            && modular_scan.bindings.get("cache_manifest") == Some(&source.bindings.cache_manifest)
            && modular_scan.bindings.get("cache_payload") == Some(&source.bindings.cache_payload),
        "v3 fresh modular-scan provenance drift"
    );

    validate_selected_basis(cache_path, &result, records)?;
    ensure!(
        source.receipt.rows == ROWS
            && source.receipt.columns == RECORDS
            && source.receipt.all_rows_replayed
            && source.receipt.coefficient_mutant_rejected,
        "v3 receipt census/control drift"
    );
    ensure!(
        source.receipt.selected_sequences_sha256
            == u64_digest(result.support_sequences.iter().copied()),
        "v3 selected-sequence digest drift"
    );
    let selected_basis_sha256 = i128_digest((0..ROWS).flat_map(|row| {
        result
            .selected_basis_columns
            .iter()
            .map(move |column| column[row])
    }));
    ensure!(
        source.receipt.selected_basis_sha256 == selected_basis_sha256,
        "v3 selected-basis digest drift"
    );

    let rational_coefficients = result
        .coefficients
        .iter()
        .map(|value| parse_rational(value))
        .collect::<Result<Vec<_>>>()?;
    let recomputed_scale = rational_coefficients
        .iter()
        .fold(BigInt::one(), |scale, value| {
            lcm(&scale, &value.denominator)
        });
    let target_scale = parse_bigint(certificate_target_scale)?;
    ensure!(
        recomputed_scale == target_scale && result.fresh_target_scale == certificate_target_scale,
        "v3 target scale was not freshly recomputed"
    );
    let integer_coefficients = result
        .integer_coefficients
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    for ((rational, integer), raw) in rational_coefficients
        .iter()
        .zip(&integer_coefficients)
        .zip(&result.integer_coefficients)
    {
        let expected = &rational.numerator * (&target_scale / &rational.denominator);
        ensure!(
            &expected == integer && expected.to_string() == *raw,
            "v3 integer coefficient drift"
        );
    }
    let expected_terms = result
        .support_sequences
        .iter()
        .copied()
        .zip(&integer_coefficients)
        .filter(|(_, coefficient)| !coefficient.is_zero())
        .collect::<Vec<_>>();
    ensure!(
        certificate_terms.len() == expected_terms.len(),
        "v3 certificate term census drift"
    );
    for (term, (sequence, coefficient)) in certificate_terms.iter().zip(expected_terms) {
        ensure!(
            term.sequence == sequence
                && canonical_integer(&term.coefficient)
                && term.coefficient != "0"
                && parse_bigint(&term.coefficient)? == *coefficient,
            "v3 certificate terms do not match fresh-Q result"
        );
    }

    for (row, &target) in targets.iter().enumerate() {
        let lhs = integer_coefficients
            .iter()
            .zip(&result.selected_basis_columns)
            .fold(BigInt::zero(), |sum, (coefficient, column)| {
                sum + coefficient * BigInt::from(column[row])
            });
        ensure!(
            lhs == &target_scale * BigInt::from(target),
            "v3 exact accumulated-row replay failed"
        );
    }
    let exact_replay_sha256 = string_digest(
        row_document
            .ordered_rows
            .iter()
            .map(|row| row.target.as_str()),
    );
    ensure!(
        source.receipt.exact_replay_sha256 == exact_replay_sha256,
        "v3 exact replay receipt drift"
    );
    let first_nonzero = integer_coefficients
        .iter()
        .position(|coefficient| !coefficient.is_zero())
        .context("v3 integer solution is identically zero")?;
    ensure!(
        result.selected_basis_columns[first_nonzero]
            .iter()
            .any(|value| *value != 0),
        "v3 coefficient-plus-one mutant escaped"
    );

    let mut evidence_bindings = check_compiled_evidence()?;
    let scanner_sha256 = evidence_bindings["fresh_modular_scanner"].clone();
    ensure!(
        row_document.bindings.get("producer") == Some(&scanner_sha256)
            && modular_scan.bindings.get("producer") == Some(&scanner_sha256)
            && row_document.bindings.get("v3_preregistration")
                == Some(&evidence_bindings["v3_preregistration"])
            && modular_scan.bindings.get("v3_preregistration")
                == Some(&evidence_bindings["v3_preregistration"])
            && row_document.bindings.get("v3_path_addendum")
                == Some(&evidence_bindings["v3_path_addendum"])
            && modular_scan.bindings.get("v3_path_addendum")
                == Some(&evidence_bindings["v3_path_addendum"]),
        "v3 scanner source/preregistration binding drift"
    );
    evidence_bindings.insert("fresh_q_result".to_string(), source.sha256.clone());
    Ok(ValidatedCegis {
        target_scale,
        source_sha256: source.sha256.clone(),
        evidence_bindings,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_rational_parser_is_fail_closed() {
        for accepted in ["0", "1", "-1", "2/3", "-5/7"] {
            assert!(parse_rational(accepted).is_ok(), "{accepted}");
        }
        for rejected in ["", "+1", "00", "-0", "1/1", "2/4", "0/3", "1/-2", "1/0"] {
            assert!(parse_rational(rejected).is_err(), "{rejected}");
        }
    }

    #[test]
    fn ordered_digests_reject_reordering() {
        assert_ne!(
            descriptor_digest(["panel:0".to_string(), "panel:1".to_string()]),
            descriptor_digest(["panel:1".to_string(), "panel:0".to_string()])
        );
        assert_ne!(u64_digest([1, 2]), u64_digest([2, 1]));
        assert_ne!(i128_digest([1, -2]), i128_digest([-2, 1]));
    }
}
