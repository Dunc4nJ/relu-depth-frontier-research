use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const RECORDS: usize = 163_740;
const ROWS: usize = 301;
const ENTRY_BYTES: usize = 16;
const PAYLOAD_BYTES: u64 = (RECORDS * ROWS * ENTRY_BYTES) as u64;

const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const ROWS_SHA256: &str = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c";
const EVALUATOR_SHA256: &str = "875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd";
const EVALUATOR_GATE_SHA256: &str =
    "94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310";
const CORRECTED_SCAN_PRODUCER_SHA256: &str =
    "8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f";
const COMPLETED_SCAN_SHA256: &str =
    "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e";
const PREREGISTRATION_SHA256: &str =
    "ac6cecfe4702866d8177dbeefd81b71a3933578a6f88b1f9cbcbc12f0cfb1022";
const EXPECTED_PAYLOAD_SHA256: &str =
    "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b";
const EXPECTED_ORDERED_VECTOR_DIGESTS_SHA256: &str =
    "0d6dadb15a8e72cf37c119c2d73f0750e38f5708f09a98c48f36b4f44b59815b";

const COMPILED_PRODUCER: &[u8] = include_bytes!("full_family_cache.rs");
const COMPILED_EVALUATOR: &[u8] = include_bytes!("../../../G-0116/src/main.rs");
const COMPILED_SCAN_PRODUCER: &[u8] = include_bytes!("../../../G-0113/src/main.rs");
const COMPILED_PREREGISTRATION: &[u8] =
    include_bytes!("../../FULL_FAMILY_CEGIS_PREREGISTRATION.md");

mod frozen_evaluator {
    #![allow(dead_code)]
    #![allow(clippy::needless_range_loop)]

    include!("../../../G-0116/src/main.rs");

    #[derive(Debug)]
    pub struct Census {
        pub records: usize,
        pub rows: usize,
        pub value_minimum: i128,
        pub value_maximum: i128,
    }

    pub fn stream_panel_vectors(
        input_path: &Path,
        rows_path: &Path,
        mut observe: impl FnMut(usize, &[i128]) -> Result<()>,
    ) -> Result<Census> {
        let input: Input = serde_json::from_reader(BufReader::new(File::open(input_path)?))?;
        ensure!(
            input.schema == "max11-g0113-panel-solver-input-v1",
            "input schema drift"
        );
        ensure!(
            input.rows_path == "artifacts/math/G-0111/dual_rows_v1.json",
            "bound row path drift"
        );
        ensure!(input.records.len() == super::RECORDS, "record count drift");
        ensure!(
            input
                .records
                .iter()
                .enumerate()
                .all(|(index, record)| index == record.sequence),
            "record sequence drift"
        );
        let rows_document: RowsDocument =
            serde_json::from_reader(BufReader::new(File::open(rows_path)?))?;
        ensure!(
            rows_document.schema == "max11-g0111-actual-dual-rows-v1",
            "row schema drift"
        );
        ensure!(rows_document.rows.len() == super::ROWS, "row count drift");

        let mut minimum = i128::MAX;
        let mut maximum = i128::MIN;
        for (sequence, record) in input.records.iter().enumerate() {
            let edges = signed_edges(record, false)?;
            let (histogram, _) = cycle_cut_histogram(record, &edges)?;
            let vector = panel_vector(&histogram, record.active_vertices, &rows_document.rows)?;
            ensure!(vector.len() == super::ROWS, "panel-vector dimension drift");
            for &value in &vector {
                minimum = minimum.min(value);
                maximum = maximum.max(value);
            }
            observe(sequence, &vector)?;
        }
        Ok(Census {
            records: input.records.len(),
            rows: rows_document.rows.len(),
            value_minimum: minimum,
            value_maximum: maximum,
        })
    }
}

#[derive(Debug, Deserialize)]
struct ScanReport {
    result: String,
    bindings: BTreeMap<String, String>,
    records: usize,
    all_vectors_i128_le_sha256: String,
    ordered_vector_digests_sha256: String,
    control_vector_sha256: BTreeMap<usize, String>,
    value_minimum: i128,
    value_maximum: i128,
}

#[derive(Debug, Deserialize, Serialize)]
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

fn sha256_path(path: &Path) -> Result<String> {
    let mut input = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    loop {
        let read = input.read(&mut buffer)?;
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

fn source_path(relative: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(relative)
}

fn require_hash(path: &Path, expected: &str, label: &str) -> Result<String> {
    let observed = sha256_path(path)?;
    ensure!(observed == expected, "{label} binding drift");
    Ok(observed)
}

fn check_compiled_sources() -> Result<BTreeMap<String, String>> {
    let producer_path = source_path("src/bin/full_family_cache.rs");
    let evaluator_path = source_path("../G-0116/src/main.rs");
    let scan_producer_path = source_path("../G-0113/src/main.rs");
    let preregistration_path = source_path("FULL_FAMILY_CEGIS_PREREGISTRATION.md");

    let producer = sha256_path(&producer_path)?;
    ensure!(
        producer == sha256_bytes(COMPILED_PRODUCER),
        "running binary was compiled from a different cache producer"
    );
    let evaluator = require_hash(&evaluator_path, EVALUATOR_SHA256, "frozen evaluator")?;
    ensure!(
        evaluator == sha256_bytes(COMPILED_EVALUATOR),
        "compiled evaluator bytes drift"
    );
    let scan_producer = require_hash(
        &scan_producer_path,
        CORRECTED_SCAN_PRODUCER_SHA256,
        "corrected scan producer",
    )?;
    ensure!(
        scan_producer == sha256_bytes(COMPILED_SCAN_PRODUCER),
        "compiled scan producer bytes drift"
    );
    let preregistration = require_hash(
        &preregistration_path,
        PREREGISTRATION_SHA256,
        "full-family preregistration",
    )?;
    ensure!(
        preregistration == sha256_bytes(COMPILED_PREREGISTRATION),
        "compiled preregistration bytes drift"
    );

    Ok(BTreeMap::from([
        ("producer".to_string(), producer),
        ("evaluator".to_string(), evaluator),
        ("corrected_scan_producer".to_string(), scan_producer),
        ("preregistration".to_string(), preregistration),
    ]))
}

fn validate_scan(path: &Path) -> Result<ScanReport> {
    require_hash(path, COMPLETED_SCAN_SHA256, "completed corrected scan")?;
    let report: ScanReport = serde_json::from_reader(BufReader::new(File::open(path)?))?;
    ensure!(
        report.result == "MODULAR_MEMBER_PENDING_EXACT_Q",
        "completed scan result drift"
    );
    ensure!(report.records == RECORDS, "completed scan census drift");
    ensure!(
        report.bindings.get("input").map(String::as_str) == Some(INPUT_SHA256)
            && report.bindings.get("rows").map(String::as_str) == Some(ROWS_SHA256)
            && report.bindings.get("evaluator").map(String::as_str) == Some(EVALUATOR_SHA256)
            && report.bindings.get("evaluator_report").map(String::as_str)
                == Some(EVALUATOR_GATE_SHA256)
            && report.bindings.get("producer").map(String::as_str)
                == Some(CORRECTED_SCAN_PRODUCER_SHA256),
        "completed scan transitive binding drift"
    );
    ensure!(
        report.all_vectors_i128_le_sha256 == EXPECTED_PAYLOAD_SHA256,
        "completed scan vector digest drift"
    );
    ensure!(
        report.ordered_vector_digests_sha256 == EXPECTED_ORDERED_VECTOR_DIGESTS_SHA256,
        "completed scan ordered-vector digest drift"
    );
    ensure!(
        report.control_vector_sha256.len() == 8,
        "control census drift"
    );
    Ok(report)
}

fn validate_payload_shape_and_hash(
    payload: &[u8],
    records: usize,
    rows: usize,
    expected: &str,
) -> Result<()> {
    let expected_bytes = records
        .checked_mul(rows)
        .and_then(|value| value.checked_mul(ENTRY_BYTES))
        .context("payload dimension overflow")?;
    ensure!(payload.len() == expected_bytes, "payload size mismatch");
    ensure!(sha256_bytes(payload) == expected, "payload digest mismatch");
    Ok(())
}

fn write_manifest_exclusive(path: &Path, manifest: &CacheManifest) -> Result<()> {
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| format!("refusing to overwrite {}", path.display()))?;
    let mut writer = BufWriter::new(file);
    serde_json::to_writer_pretty(&mut writer, manifest)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    Ok(())
}

fn build(
    input_path: &Path,
    rows_path: &Path,
    gate_path: &Path,
    scan_path: &Path,
    payload_path: &Path,
    manifest_path: &Path,
) -> Result<()> {
    ensure!(payload_path != manifest_path, "cache paths must differ");
    ensure!(
        !payload_path.exists() && !manifest_path.exists(),
        "refusing to overwrite cache output"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let started = Instant::now();
    let mut bindings = check_compiled_sources()?;
    bindings.insert(
        "input".to_string(),
        require_hash(input_path, INPUT_SHA256, "panel input")?,
    );
    bindings.insert(
        "rows".to_string(),
        require_hash(rows_path, ROWS_SHA256, "panel rows")?,
    );
    bindings.insert(
        "evaluator_gate".to_string(),
        require_hash(gate_path, EVALUATOR_GATE_SHA256, "evaluator gate")?,
    );
    bindings.insert(
        "completed_scan".to_string(),
        require_hash(scan_path, COMPLETED_SCAN_SHA256, "completed corrected scan")?,
    );
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve executable")?)?,
    );
    let scan = validate_scan(scan_path)?;

    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(payload_path)
        .with_context(|| format!("refusing to overwrite {}", payload_path.display()))?;
    let mut writer = BufWriter::with_capacity(1 << 20, file);
    let mut all_vectors = Sha256::new();
    let mut ordered_vector_digests = Sha256::new();
    let mut controls = BTreeMap::<usize, String>::new();
    let census =
        frozen_evaluator::stream_panel_vectors(input_path, rows_path, |sequence, vector| {
            let mut vector_digest = Sha256::new();
            for value in vector {
                let bytes = value.to_le_bytes();
                writer.write_all(&bytes)?;
                all_vectors.update(bytes);
                vector_digest.update(bytes);
            }
            let vector_digest = vector_digest.finalize();
            ordered_vector_digests.update(vector_digest);
            if scan.control_vector_sha256.contains_key(&sequence) {
                controls.insert(sequence, format!("{vector_digest:x}"));
            }
            if sequence % 5_000 == 0 || sequence + 1 == RECORDS {
                eprintln!("G0117_CACHE_PROGRESS {}/{}", sequence + 1, RECORDS);
            }
            Ok(())
        })?;
    writer.flush()?;
    writer.get_ref().sync_all()?;

    let data_sha256 = format!("{:x}", all_vectors.finalize());
    let ordered_sha256 = format!("{:x}", ordered_vector_digests.finalize());
    ensure!(
        census.records == RECORDS && census.rows == ROWS,
        "cache census drift"
    );
    ensure!(
        writer.get_ref().metadata()?.len() == PAYLOAD_BYTES,
        "cache payload-size drift"
    );
    ensure!(
        data_sha256 == scan.all_vectors_i128_le_sha256 && data_sha256 == EXPECTED_PAYLOAD_SHA256,
        "cache data does not reproduce completed scan"
    );
    ensure!(
        ordered_sha256 == scan.ordered_vector_digests_sha256
            && ordered_sha256 == EXPECTED_ORDERED_VECTOR_DIGESTS_SHA256,
        "ordered-vector stream does not reproduce completed scan"
    );
    ensure!(
        controls == scan.control_vector_sha256,
        "control vectors drift"
    );
    ensure!(
        census.value_minimum == scan.value_minimum && census.value_maximum == scan.value_maximum,
        "cache value range drift"
    );

    let manifest = CacheManifest {
        schema: "max11-g0117-full-family-panel-cache-v1".to_string(),
        result: "EXACT_PANEL_CACHE_REPRODUCED".to_string(),
        claim_boundary: "Exact sequence-major cache of the frozen 301-row finite panel over 163,740 columns; not a global identity, Q membership decision, family-completeness theorem, or MAX11 result.".to_string(),
        bindings,
        records: RECORDS,
        rows: ROWS,
        entry_bytes: ENTRY_BYTES,
        payload_bytes: PAYLOAD_BYTES,
        layout: "sequence-major: offset=((sequence*301)+row)*16".to_string(),
        integer_width: "signed i128".to_string(),
        endianness: "little".to_string(),
        data_sha256,
        ordered_vector_digests_sha256: ordered_sha256,
        control_vector_sha256: controls,
        value_minimum: census.value_minimum,
        value_maximum: census.value_maximum,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    write_manifest_exclusive(manifest_path, &manifest)?;
    println!("{}", serde_json::to_string(&manifest)?);
    Ok(())
}

fn verify(
    input_path: &Path,
    rows_path: &Path,
    gate_path: &Path,
    scan_path: &Path,
    payload_path: &Path,
    manifest_path: &Path,
) -> Result<()> {
    let current_sources = check_compiled_sources()?;
    let scan = validate_scan(scan_path)?;
    let manifest: CacheManifest =
        serde_json::from_reader(BufReader::new(File::open(manifest_path)?))?;
    ensure!(
        manifest.schema == "max11-g0117-full-family-panel-cache-v1"
            && manifest.result == "EXACT_PANEL_CACHE_REPRODUCED",
        "manifest schema/result drift"
    );
    ensure!(
        manifest.records == RECORDS
            && manifest.rows == ROWS
            && manifest.entry_bytes == ENTRY_BYTES
            && manifest.payload_bytes == PAYLOAD_BYTES
            && manifest.layout == "sequence-major: offset=((sequence*301)+row)*16"
            && manifest.integer_width == "signed i128"
            && manifest.endianness == "little",
        "manifest layout drift"
    );
    for (name, digest) in current_sources {
        ensure!(
            manifest.bindings.get(&name) == Some(&digest),
            "{name} drift"
        );
    }
    for (name, path, expected) in [
        ("input", input_path, INPUT_SHA256),
        ("rows", rows_path, ROWS_SHA256),
        ("evaluator_gate", gate_path, EVALUATOR_GATE_SHA256),
        ("completed_scan", scan_path, COMPLETED_SCAN_SHA256),
    ] {
        let observed = require_hash(path, expected, name)?;
        ensure!(
            manifest.bindings.get(name) == Some(&observed),
            "{name} drift"
        );
    }
    let executable = sha256_path(&std::env::current_exe()?)?;
    ensure!(
        manifest.bindings.get("executable") == Some(&executable),
        "cache verifier executable drift"
    );
    ensure!(
        File::open(payload_path)?.metadata()?.len() == PAYLOAD_BYTES,
        "payload size mismatch"
    );
    let observed_payload = sha256_path(payload_path)?;
    ensure!(
        observed_payload == manifest.data_sha256
            && observed_payload == scan.all_vectors_i128_le_sha256
            && observed_payload == EXPECTED_PAYLOAD_SHA256,
        "payload digest mismatch"
    );
    ensure!(
        manifest.ordered_vector_digests_sha256 == scan.ordered_vector_digests_sha256
            && manifest.control_vector_sha256 == scan.control_vector_sha256
            && manifest.value_minimum == scan.value_minimum
            && manifest.value_maximum == scan.value_maximum,
        "manifest scientific payload drift"
    );
    println!(
        "{}",
        serde_json::json!({
            "schema": "max11-g0117-full-family-panel-cache-verification-v1",
            "result": "PASS",
            "payload_sha256": observed_payload,
            "records": RECORDS,
            "rows": ROWS,
            "payload_bytes": PAYLOAD_BYTES,
        })
    );
    Ok(())
}

fn self_test() -> Result<()> {
    let values = [1i128, -2, 3, 4, -5, 6];
    let payload = values
        .iter()
        .flat_map(|value| value.to_le_bytes())
        .collect::<Vec<_>>();
    let digest = sha256_bytes(&payload);
    validate_payload_shape_and_hash(&payload, 2, 3, &digest)?;

    let mut truncated = payload.clone();
    truncated.pop();
    ensure!(
        validate_payload_shape_and_hash(&truncated, 2, 3, &digest).is_err(),
        "truncation mutant escaped"
    );
    let mut byte_mutant = payload.clone();
    byte_mutant[17] ^= 1;
    ensure!(
        validate_payload_shape_and_hash(&byte_mutant, 2, 3, &digest).is_err(),
        "byte mutant escaped"
    );
    let transposed_values = [1i128, 4, -2, -5, 3, 6];
    let transposed = transposed_values
        .iter()
        .flat_map(|value| value.to_le_bytes())
        .collect::<Vec<_>>();
    ensure!(
        validate_payload_shape_and_hash(&transposed, 2, 3, &digest).is_err(),
        "transpose mutant escaped"
    );
    let reversed_values = [3i128, -2, 1, 6, -5, 4];
    let reversed = reversed_values
        .iter()
        .flat_map(|value| value.to_le_bytes())
        .collect::<Vec<_>>();
    ensure!(
        validate_payload_shape_and_hash(&reversed, 2, 3, &digest).is_err(),
        "column-reversal mutant escaped"
    );
    println!("full-family-cache-self-test: PASS (4 hostile mutations rejected)");
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    match args.as_slice() {
        [_, command] if command == "--self-test" => self_test(),
        [_, command, input, rows, gate, scan, payload, manifest] if command == "build" => build(
            Path::new(input),
            Path::new(rows),
            Path::new(gate),
            Path::new(scan),
            Path::new(payload),
            Path::new(manifest),
        ),
        [_, command, input, rows, gate, scan, payload, manifest] if command == "verify" => verify(
            Path::new(input),
            Path::new(rows),
            Path::new(gate),
            Path::new(scan),
            Path::new(payload),
            Path::new(manifest),
        ),
        _ => anyhow::bail!(
            "usage: full_family_cache --self-test | (build|verify) INPUT ROWS GATE SCAN PAYLOAD MANIFEST"
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn payload_mutants_are_rejected() {
        self_test().unwrap();
    }
}
