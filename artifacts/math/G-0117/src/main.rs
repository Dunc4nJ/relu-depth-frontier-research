use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{N, Record, hinge_coefficient, linear_vector};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::BTreeMap;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const COMPILED_PRODUCER: &[u8] = include_bytes!("main.rs");
const COMPILED_KERNEL: &[u8] = include_bytes!("lib.rs");

#[derive(Deserialize)]
struct PanelInput {
    schema: String,
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct Query {
    schema: String,
    direction: [i8; N],
    expected_records: usize,
    #[serde(default = "default_emit_values")]
    emit_values: bool,
}

fn default_emit_values() -> bool {
    true
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    direction: [i8; N],
    records: usize,
    nonzero_hinge_coefficients: usize,
    maximum_hinge_coefficient: i64,
    hinge_coefficients_i64_le_sha256: String,
    linear_vectors_i64_le_sha256: String,
    hinge_coefficients: Option<Vec<i64>>,
    linear_vectors: Option<Vec<[i64; N]>>,
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

fn digest_i64<'a>(values: impl Iterator<Item = &'a i64>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 4,
        "usage: g0117-global-coordinate-pricer PANEL_INPUT.json QUERY.json OUTPUT.json"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build fixed 12-thread pool")?;
    let input_path = PathBuf::from(&args[1]);
    let query_path = PathBuf::from(&args[2]);
    let output_path = PathBuf::from(&args[3]);
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let started = Instant::now();
    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    let query: Query = serde_json::from_reader(BufReader::new(File::open(&query_path)?))?;
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1",
        "panel-input schema drift"
    );
    ensure!(
        query.schema == "max11-g0117-coordinate-query-v1",
        "query schema drift"
    );
    ensure!(
        input.records.len() == query.expected_records,
        "record census drift"
    );
    ensure!(
        input
            .records
            .iter()
            .enumerate()
            .all(|(index, record)| index == record.sequence),
        "record sequence drift"
    );

    let computed = input
        .records
        .par_iter()
        .map(|record| {
            Ok((
                hinge_coefficient(record, &query.direction)?,
                linear_vector(record)?,
            ))
        })
        .collect::<Result<Vec<_>>>()?;
    let hinge_coefficients = computed.iter().map(|item| item.0).collect::<Vec<_>>();
    let linear_vectors = computed.iter().map(|item| item.1).collect::<Vec<_>>();
    let linear_digest = digest_i64(linear_vectors.iter().flat_map(|row| row.iter()));
    let hinge_digest = digest_i64(hinge_coefficients.iter());
    let producer_path = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/main.rs"));
    let kernel_path = Path::new(concat!(env!("CARGO_MANIFEST_DIR"), "/src/lib.rs"));
    let producer_sha256 = sha256_path(producer_path)?;
    let kernel_sha256 = sha256_path(kernel_path)?;
    ensure!(
        producer_sha256 == sha256_bytes(COMPILED_PRODUCER),
        "running binary was compiled from a different producer source"
    );
    ensure!(
        kernel_sha256 == sha256_bytes(COMPILED_KERNEL),
        "running binary was compiled from a different kernel source"
    );
    let mut bindings = BTreeMap::new();
    bindings.insert("panel_input".to_string(), sha256_path(&input_path)?);
    bindings.insert("query".to_string(), sha256_path(&query_path)?);
    bindings.insert("producer".to_string(), producer_sha256);
    bindings.insert("kernel".to_string(), kernel_sha256);
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve current executable")?)?,
    );
    let output = Output {
        schema: "max11-g0117-coordinate-price-v1",
        result: "EXACT_COORDINATE_PRICES",
        claim_boundary: "One exact ordered-cone hinge row and all linear rows over the frozen finite G-0113 family; not a panel membership, global identity, completeness theorem, or MAX11 result.",
        bindings,
        direction: query.direction,
        records: hinge_coefficients.len(),
        nonzero_hinge_coefficients: hinge_coefficients
            .iter()
            .filter(|value| **value != 0)
            .count(),
        maximum_hinge_coefficient: hinge_coefficients.iter().copied().max().unwrap_or(0),
        hinge_coefficients_i64_le_sha256: hinge_digest,
        linear_vectors_i64_le_sha256: linear_digest,
        hinge_coefficients: query.emit_values.then_some(hinge_coefficients),
        linear_vectors: query.emit_values.then_some(linear_vectors),
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&output_path)?;
    let mut writer = BufWriter::new(file);
    serde_json::to_writer(&mut writer, &output)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}
