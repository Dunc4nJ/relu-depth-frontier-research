use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Seek, SeekFrom, Write};
use std::path::{Component, Path, PathBuf};
use std::time::Instant;

const RECORDS: usize = 163_740;
const PANEL_ROWS: usize = 301;
const APPENDED_ROWS: usize = 12;
const ROWS: usize = PANEL_ROWS + APPENDED_ROWS;
const N: usize = 11;
const ENTRY_BYTES: usize = 16;
const COLUMN_BYTES: usize = PANEL_ROWS * ENTRY_BYTES;
const CACHE_BYTES: u64 = (RECORDS * COLUMN_BYTES) as u64;
const PRIMES: [u32; 2] = [2_000_081, 3_000_017];
const TARGET_FACTORIAL: i128 = 39_916_800;
const DIRECTION: [i8; N] = [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4];

const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const ROWS_SHA256: &str = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c";
const PANEL_SCAN_SHA256: &str = "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e";
const CACHE_PAYLOAD_SHA256: &str =
    "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b";
const COORDINATE_OUTPUT_SHA256: &str =
    "c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071";
const COORDINATE_QUERY_SHA256: &str =
    "4b624bb28d3eb095c5fbfd2c434fca2840d4b020c89ba777cfac291f8e5bbab5";
const HINGE_STREAM_I64_SHA256: &str =
    "c812bb4833289cbc79c68b0bf41ce8e36fbf263e822a0761a24a05877103a22c";
const LINEAR_STREAM_I64_SHA256: &str =
    "84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51";
const RANK_SOURCE_SHA256: &str = "006968bbf4f428e4fa492d06b61b43d64b25e5febcc0751ec81c07d90a399994";
const V3_PREREGISTRATION_SHA256: &str =
    "57c43026da21ead61e9fc0a7330e763809e9bd565ce7854eef03ef14803a2c46";

const COMPILED_PRODUCER: &[u8] = include_bytes!("fresh_q_cegis.rs");
const COMPILED_RANK: &[u8] = include_bytes!("../../../G-0113/src/rank.rs");
const COMPILED_V3_PREREGISTRATION: &[u8] =
    include_bytes!("../../ITERATION1_V3_CERTIFICATE_PREREGISTRATION.md");

#[path = "../../../G-0113/src/rank.rs"]
#[allow(dead_code)]
mod rank;

#[derive(Deserialize)]
struct PanelInput {
    schema: String,
    target: Vec<i128>,
}

#[derive(Deserialize)]
struct CacheManifest {
    schema: String,
    result: String,
    bindings: BTreeMap<String, String>,
    records: usize,
    rows: usize,
    entry_bytes: usize,
    payload_bytes: u64,
    layout: String,
    integer_width: String,
    endianness: String,
    data_sha256: String,
}

#[derive(Deserialize)]
struct PanelPrimeReport {
    prime: u32,
    union_rank: usize,
    union_target_member: bool,
    selected_sequences: Vec<usize>,
}

#[derive(Deserialize)]
struct PanelScan {
    schema: String,
    result: String,
    records: usize,
    all_vectors_i128_le_sha256: String,
    primes: Vec<PanelPrimeReport>,
}

#[derive(Deserialize)]
struct CoordinateOutput {
    schema: String,
    result: String,
    bindings: BTreeMap<String, String>,
    direction: [i8; N],
    records: usize,
    hinge_coefficients_i64_le_sha256: String,
    linear_vectors_i64_le_sha256: String,
    hinge_coefficients: Option<Vec<i64>>,
    linear_vectors: Option<Vec<[i64; N]>>,
}

#[derive(Serialize)]
struct AccumulatedRow {
    descriptor: String,
    values_i128_le_sha256: String,
    target: String,
}

#[derive(Serialize)]
struct AccumulatedRowsDocument {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    rows: usize,
    columns: usize,
    descriptors_sha256: String,
    targets_i128_le_sha256: String,
    ordered_rows: Vec<AccumulatedRow>,
}

#[derive(Serialize)]
struct FreshPrimeReport {
    prime: u32,
    base_panel_rank: usize,
    quotient_rank: usize,
    full_rank: usize,
    target_member: bool,
    base_selected_sequences: Vec<usize>,
    quotient_selected_sequences: Vec<usize>,
    selected_sequences: Vec<usize>,
    base_coordinate_rows: Vec<usize>,
    quotient_target: Vec<u32>,
}

#[derive(Serialize)]
struct FreshScanOutput {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    records_scanned: usize,
    rows: usize,
    panel_rows: usize,
    appended_rows: usize,
    direction: [i8; N],
    primes: Vec<FreshPrimeReport>,
    modular_ranks_agree: bool,
    modular_target_decisions_agree: bool,
    all_columns_reopened: bool,
    old_support_only: bool,
    wall_seconds: f64,
}

fn source_path(relative: &str) -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join(relative)
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut file = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    loop {
        let read = file.read(&mut buffer)?;
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

fn require_hash(path: &Path, expected: &str, label: &str) -> Result<String> {
    let observed = sha256_path(path)?;
    ensure!(observed == expected, "{label} binding drift");
    Ok(observed)
}

fn check_compiled_sources() -> Result<BTreeMap<String, String>> {
    let producer_path = source_path("src/bin/fresh_q_cegis.rs");
    let rank_path = source_path("../G-0113/src/rank.rs");
    let preregistration_path = source_path("ITERATION1_V3_CERTIFICATE_PREREGISTRATION.md");
    let producer = sha256_path(&producer_path)?;
    ensure!(
        producer == sha256_bytes(COMPILED_PRODUCER),
        "running binary was compiled from a different producer"
    );
    let rank = require_hash(&rank_path, RANK_SOURCE_SHA256, "rank source")?;
    ensure!(
        rank == sha256_bytes(COMPILED_RANK),
        "compiled rank source drift"
    );
    let preregistration = require_hash(
        &preregistration_path,
        V3_PREREGISTRATION_SHA256,
        "v3 preregistration",
    )?;
    ensure!(
        preregistration == sha256_bytes(COMPILED_V3_PREREGISTRATION),
        "compiled v3 preregistration drift"
    );
    Ok(BTreeMap::from([
        ("producer".to_string(), producer),
        ("rank_source".to_string(), rank),
        ("v3_preregistration".to_string(), preregistration),
    ]))
}

fn canonical_relative_path(path: &Path) -> bool {
    !path.is_absolute()
        && path
            .components()
            .all(|component| matches!(component, Component::Normal(_) | Component::CurDir))
}

fn digest_i64<'a>(values: impl Iterator<Item = &'a i64>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn descriptor_digest(descriptors: impl Iterator<Item = String>) -> String {
    let mut digest = Sha256::new();
    for descriptor in descriptors {
        digest.update((descriptor.len() as u64).to_le_bytes());
        digest.update(descriptor.as_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn target_digest(target: &[i128]) -> String {
    let mut digest = Sha256::new();
    for value in target {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn add_mod(left: u32, right: u32, prime: u32) -> u32 {
    ((u64::from(left) + u64::from(right)) % u64::from(prime)) as u32
}

fn sub_mod(left: u32, right: u32, prime: u32) -> u32 {
    ((u64::from(left) + u64::from(prime) - u64::from(right)) % u64::from(prime)) as u32
}

fn mul_mod(left: u32, right: u32, prime: u32) -> u32 {
    ((u64::from(left) * u64::from(right)) % u64::from(prime)) as u32
}

fn pow_mod(mut base: u32, mut exponent: u32, prime: u32) -> u32 {
    let mut output = 1u32;
    while exponent > 0 {
        if exponent & 1 == 1 {
            output = mul_mod(output, base, prime);
        }
        base = mul_mod(base, base, prime);
        exponent >>= 1;
    }
    output
}

fn reduce(value: i128, prime: u32) -> u32 {
    value.rem_euclid(i128::from(prime)) as u32
}

fn pivot_columns(mut rows: Vec<Vec<u32>>, prime: u32) -> Result<Vec<usize>> {
    let row_count = rows.len();
    ensure!(row_count > 0, "empty modular matrix");
    let columns = rows[0].len();
    ensure!(rows.iter().all(|row| row.len() == columns), "ragged matrix");
    let mut pivots = Vec::with_capacity(row_count);
    for column in 0..columns {
        if pivots.len() == row_count {
            break;
        }
        let pivot_row = pivots.len();
        let Some(found) = (pivot_row..row_count).find(|row| rows[*row][column] != 0) else {
            continue;
        };
        rows.swap(pivot_row, found);
        let inverse = pow_mod(rows[pivot_row][column], prime - 2, prime);
        for value in &mut rows[pivot_row][column..] {
            *value = mul_mod(*value, inverse, prime);
        }
        let normalized = rows[pivot_row].clone();
        for (row_index, row) in rows.iter_mut().enumerate() {
            if row_index == pivot_row || row[column] == 0 {
                continue;
            }
            let factor = row[column];
            for position in column..columns {
                row[position] = sub_mod(
                    row[position],
                    mul_mod(factor, normalized[position], prime),
                    prime,
                );
            }
        }
        pivots.push(column);
    }
    ensure!(pivots.len() == row_count, "basis lost modular rank");
    Ok(pivots)
}

fn invert(mut matrix: Vec<Vec<u32>>, prime: u32) -> Result<Vec<Vec<u32>>> {
    let size = matrix.len();
    ensure!(
        size > 0 && matrix.iter().all(|row| row.len() == size),
        "not square"
    );
    for (row, values) in matrix.iter_mut().enumerate() {
        values.extend((0..size).map(|column| u32::from(row == column)));
    }
    for column in 0..size {
        let found = (column..size)
            .find(|row| matrix[*row][column] != 0)
            .context("singular modular basis")?;
        matrix.swap(column, found);
        let inverse = pow_mod(matrix[column][column], prime - 2, prime);
        for value in &mut matrix[column] {
            *value = mul_mod(*value, inverse, prime);
        }
        let normalized = matrix[column].clone();
        for (row_index, row) in matrix.iter_mut().enumerate() {
            if row_index == column || row[column] == 0 {
                continue;
            }
            let factor = row[column];
            for position in 0..2 * size {
                row[position] = sub_mod(
                    row[position],
                    mul_mod(factor, normalized[position], prime),
                    prime,
                );
            }
        }
    }
    Ok(matrix.into_iter().map(|row| row[size..].to_vec()).collect())
}

fn matrix_product(left: &[Vec<u32>], right: &[Vec<u32>], prime: u32) -> Vec<Vec<u32>> {
    let inner = right.len();
    let columns = right[0].len();
    left.iter()
        .map(|row| {
            (0..columns)
                .map(|column| {
                    row.iter()
                        .zip(right.iter().take(inner))
                        .fold(0u32, |sum, (one, two)| {
                            add_mod(sum, mul_mod(*one, two[column], prime), prime)
                        })
                })
                .collect()
        })
        .collect()
}

fn matrix_vector(matrix: &[Vec<u32>], vector: &[u32], prime: u32) -> Vec<u32> {
    matrix
        .iter()
        .map(|row| {
            row.iter().zip(vector).fold(0u32, |sum, (one, two)| {
                add_mod(sum, mul_mod(*one, *two, prime), prime)
            })
        })
        .collect()
}

fn read_column_at(file: &mut File, sequence: usize) -> Result<Vec<i128>> {
    let offset = sequence
        .checked_mul(COLUMN_BYTES)
        .context("cache offset overflow")? as u64;
    file.seek(SeekFrom::Start(offset))?;
    let mut raw = vec![0u8; COLUMN_BYTES];
    file.read_exact(&mut raw)?;
    Ok(raw
        .chunks_exact(ENTRY_BYTES)
        .map(|chunk| i128::from_le_bytes(chunk.try_into().unwrap()))
        .collect())
}

fn appended_column(coordinate: &CoordinateOutput, sequence: usize) -> Vec<i128> {
    let linear = coordinate.linear_vectors.as_ref().unwrap()[sequence];
    let hinge = coordinate.hinge_coefficients.as_ref().unwrap()[sequence];
    linear
        .into_iter()
        .map(i128::from)
        .chain(std::iter::once(i128::from(hinge)))
        .collect()
}

struct QuotientSetup {
    base_sequences: Vec<usize>,
    coordinate_rows: Vec<usize>,
    transport: Vec<Vec<u32>>,
}

fn quotient_setup(
    cache: &mut File,
    coordinate: &CoordinateOutput,
    base_sequences: &[usize],
    prime: u32,
) -> Result<QuotientSetup> {
    let basis = base_sequences
        .iter()
        .map(|sequence| read_column_at(cache, *sequence))
        .collect::<Result<Vec<_>>>()?;
    let transposed = basis
        .iter()
        .map(|column| column.iter().map(|value| reduce(*value, prime)).collect())
        .collect::<Vec<Vec<u32>>>();
    let coordinate_rows = pivot_columns(transposed, prime)?;
    let square = coordinate_rows
        .iter()
        .map(|row| {
            basis
                .iter()
                .map(|column| reduce(column[*row], prime))
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let inverse = invert(square, prime)?;
    let appended_basis = (0..APPENDED_ROWS)
        .map(|row| {
            base_sequences
                .iter()
                .map(|sequence| reduce(appended_column(coordinate, *sequence)[row], prime))
                .collect::<Vec<_>>()
        })
        .collect::<Vec<_>>();
    let transport = matrix_product(&appended_basis, &inverse, prime);
    Ok(QuotientSetup {
        base_sequences: base_sequences.to_vec(),
        coordinate_rows,
        transport,
    })
}

fn quotient_residual(
    panel: &[i128],
    appended: &[i128],
    setup: &QuotientSetup,
    prime: u32,
) -> Vec<u32> {
    let coordinates = setup
        .coordinate_rows
        .iter()
        .map(|row| reduce(panel[*row], prime))
        .collect::<Vec<_>>();
    let predicted = matrix_vector(&setup.transport, &coordinates, prime);
    appended
        .iter()
        .zip(predicted)
        .map(|(actual, expected)| sub_mod(reduce(*actual, prime), expected, prime))
        .collect()
}

fn write_json_exclusive<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| format!("refusing to overwrite {}", path.display()))?;
    let mut writer = BufWriter::new(file);
    serde_json::to_writer_pretty(&mut writer, value)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    Ok(())
}

#[allow(clippy::too_many_arguments)]
fn scan(
    input_path: &Path,
    panel_rows_path: &Path,
    cache_path: &Path,
    manifest_path: &Path,
    panel_scan_path: &Path,
    coordinate_path: &Path,
    accumulated_rows_path: &Path,
    output_path: &Path,
) -> Result<()> {
    ensure!(
        accumulated_rows_path != output_path
            && !accumulated_rows_path.exists()
            && !output_path.exists(),
        "refusing to overwrite or alias outputs"
    );
    let started = Instant::now();
    let mut bindings = check_compiled_sources()?;
    bindings.insert(
        "panel_input".to_string(),
        require_hash(input_path, INPUT_SHA256, "panel input")?,
    );
    bindings.insert(
        "panel_rows".to_string(),
        require_hash(panel_rows_path, ROWS_SHA256, "panel rows")?,
    );
    bindings.insert(
        "cache_payload".to_string(),
        require_hash(cache_path, CACHE_PAYLOAD_SHA256, "cache payload")?,
    );
    bindings.insert("cache_manifest".to_string(), sha256_path(manifest_path)?);
    bindings.insert(
        "panel_scan".to_string(),
        require_hash(panel_scan_path, PANEL_SCAN_SHA256, "panel scan")?,
    );
    bindings.insert(
        "coordinate_output".to_string(),
        require_hash(
            coordinate_path,
            COORDINATE_OUTPUT_SHA256,
            "coordinate output",
        )?,
    );
    bindings.insert(
        "executable".to_string(),
        sha256_path(&std::env::current_exe().context("resolve executable")?)?,
    );

    let input: PanelInput = serde_json::from_reader(BufReader::new(File::open(input_path)?))?;
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1" && input.target.len() == PANEL_ROWS,
        "input schema/target drift"
    );
    let manifest: CacheManifest =
        serde_json::from_reader(BufReader::new(File::open(manifest_path)?))?;
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
            && manifest.data_sha256 == CACHE_PAYLOAD_SHA256,
        "cache manifest drift"
    );
    ensure!(
        manifest.bindings.get("input").map(String::as_str) == Some(INPUT_SHA256)
            && manifest.bindings.get("rows").map(String::as_str) == Some(ROWS_SHA256),
        "cache manifest transitive binding drift"
    );
    ensure!(
        File::open(cache_path)?.metadata()?.len() == CACHE_BYTES,
        "cache payload size drift"
    );

    let panel_scan: PanelScan =
        serde_json::from_reader(BufReader::new(File::open(panel_scan_path)?))?;
    ensure!(
        panel_scan.schema == "max11-g0113-panel-scan-v1"
            && panel_scan.result == "MODULAR_MEMBER_PENDING_EXACT_Q"
            && panel_scan.records == RECORDS
            && panel_scan.all_vectors_i128_le_sha256 == CACHE_PAYLOAD_SHA256
            && panel_scan.primes.len() == 2,
        "panel scan drift"
    );
    let coordinate: CoordinateOutput =
        serde_json::from_reader(BufReader::new(File::open(coordinate_path)?))?;
    ensure!(
        coordinate.schema == "max11-g0117-coordinate-price-v1"
            && coordinate.result == "EXACT_COORDINATE_PRICES"
            && coordinate.direction == DIRECTION
            && coordinate.records == RECORDS
            && coordinate.bindings.get("panel_input").map(String::as_str) == Some(INPUT_SHA256)
            && coordinate.bindings.get("query").map(String::as_str)
                == Some(COORDINATE_QUERY_SHA256)
            && coordinate.hinge_coefficients_i64_le_sha256 == HINGE_STREAM_I64_SHA256
            && coordinate.linear_vectors_i64_le_sha256 == LINEAR_STREAM_I64_SHA256,
        "coordinate output drift"
    );
    let hinges = coordinate
        .hinge_coefficients
        .as_ref()
        .context("coordinate output omitted hinge values")?;
    let linears = coordinate
        .linear_vectors
        .as_ref()
        .context("coordinate output omitted linear values")?;
    ensure!(
        hinges.len() == RECORDS
            && linears.len() == RECORDS
            && digest_i64(hinges.iter()) == HINGE_STREAM_I64_SHA256
            && digest_i64(linears.iter().flat_map(|row| row.iter())) == LINEAR_STREAM_I64_SHA256,
        "coordinate stream replay drift"
    );

    let mut cache = File::open(cache_path)?;
    let mut setups = Vec::new();
    for (&prime, report) in PRIMES.iter().zip(&panel_scan.primes) {
        ensure!(
            report.prime == prime
                && report.union_rank == 115
                && report.union_target_member
                && report.selected_sequences.len() == 115,
            "panel modular basis drift"
        );
        setups.push(quotient_setup(
            &mut cache,
            &coordinate,
            &report.selected_sequences,
            prime,
        )?);
    }

    let mut quotient_oracles = PRIMES
        .iter()
        .map(|prime| rank::LeftAnnihilator::new(APPENDED_ROWS, *prime))
        .collect::<Vec<_>>();
    let mut panel_row_digests = (0..PANEL_ROWS).map(|_| Sha256::new()).collect::<Vec<_>>();
    let mut reader = BufReader::with_capacity(1 << 20, File::open(cache_path)?);
    let mut raw = vec![0u8; COLUMN_BYTES];
    for sequence in 0..RECORDS {
        reader.read_exact(&mut raw)?;
        let panel = raw
            .chunks_exact(ENTRY_BYTES)
            .enumerate()
            .map(|(row, chunk)| {
                panel_row_digests[row].update(chunk);
                i128::from_le_bytes(chunk.try_into().unwrap())
            })
            .collect::<Vec<_>>();
        let appended = appended_column(&coordinate, sequence);
        for ((prime, setup), oracle) in PRIMES.iter().zip(&setups).zip(&mut quotient_oracles) {
            let residual = quotient_residual(&panel, &appended, setup, *prime);
            oracle.ingest_mod(sequence, &residual);
        }
        if sequence % 10_000 == 0 || sequence + 1 == RECORDS {
            eprintln!("G0117_FRESH_SCAN_PROGRESS {}/{}", sequence + 1, RECORDS);
        }
    }
    ensure!(reader.read(&mut [0u8; 1])? == 0, "cache trailing bytes");

    let mut target = input.target.clone();
    target.extend([0i128; N]);
    *target.last_mut().unwrap() = TARGET_FACTORIAL;
    target.push(0);
    ensure!(target.len() == ROWS, "target dimension drift");
    let appended_target = &target[PANEL_ROWS..];
    let mut fresh_reports = Vec::new();
    for (((&prime, setup), oracle), panel_report) in PRIMES
        .iter()
        .zip(&setups)
        .zip(&quotient_oracles)
        .zip(&panel_scan.primes)
    {
        let quotient_target = quotient_residual(&input.target, appended_target, setup, prime);
        let target_member = oracle.contains_mod(&quotient_target);
        let quotient_selected = oracle.selected_sequences().to_vec();
        let mut selected = setup.base_sequences.clone();
        selected.extend(&quotient_selected);
        ensure!(
            selected.iter().copied().collect::<BTreeSet<_>>().len() == selected.len(),
            "duplicate selected sequence"
        );
        fresh_reports.push(FreshPrimeReport {
            prime,
            base_panel_rank: panel_report.union_rank,
            quotient_rank: oracle.rank(),
            full_rank: panel_report.union_rank + oracle.rank(),
            target_member,
            base_selected_sequences: setup.base_sequences.clone(),
            quotient_selected_sequences: quotient_selected,
            selected_sequences: selected,
            base_coordinate_rows: setup.coordinate_rows.clone(),
            quotient_target,
        });
    }

    let mut ordered_rows = Vec::with_capacity(ROWS);
    for (row, digest) in panel_row_digests.into_iter().enumerate() {
        ordered_rows.push(AccumulatedRow {
            descriptor: format!("panel:{row}"),
            values_i128_le_sha256: format!("{:x}", digest.finalize()),
            target: target[row].to_string(),
        });
    }
    for coordinate_index in 0..N {
        let mut digest = Sha256::new();
        for vector in linears {
            digest.update(i128::from(vector[coordinate_index]).to_le_bytes());
        }
        ordered_rows.push(AccumulatedRow {
            descriptor: format!("linear:{coordinate_index}"),
            values_i128_le_sha256: format!("{:x}", digest.finalize()),
            target: target[PANEL_ROWS + coordinate_index].to_string(),
        });
    }
    let mut hinge_digest = Sha256::new();
    for value in hinges {
        hinge_digest.update(i128::from(*value).to_le_bytes());
    }
    ordered_rows.push(AccumulatedRow {
        descriptor: "hinge:0,0,0,0,0,0,0,0,1,-5,4".to_string(),
        values_i128_le_sha256: format!("{:x}", hinge_digest.finalize()),
        target: "0".to_string(),
    });
    ensure!(ordered_rows.len() == ROWS, "row document census drift");
    let descriptors_sha256 =
        descriptor_digest(ordered_rows.iter().map(|row| row.descriptor.clone()));
    let targets_sha256 = target_digest(&target);
    let row_document = AccumulatedRowsDocument {
        schema: "max11-g0117-accumulated-rows-v1",
        result: "EXACT_ORDERED_ROWS_BOUND",
        claim_boundary: "The exact accumulated finite row system for iteration 1; not a Q membership decision, global identity, completeness theorem, or MAX11 result.",
        bindings: bindings.clone(),
        rows: ROWS,
        columns: RECORDS,
        descriptors_sha256,
        targets_i128_le_sha256: targets_sha256,
        ordered_rows,
    };
    write_json_exclusive(accumulated_rows_path, &row_document)?;
    bindings.insert(
        "accumulated_rows".to_string(),
        sha256_path(accumulated_rows_path)?,
    );
    let ranks_agree = fresh_reports[0].full_rank == fresh_reports[1].full_rank;
    let decisions_agree = fresh_reports[0].target_member == fresh_reports[1].target_member;
    let result = if !ranks_agree || !decisions_agree {
        "MODULAR_DISAGREEMENT"
    } else if fresh_reports[0].target_member {
        "TWO_PRIME_MEMBER_PENDING_EXACT_Q"
    } else {
        "MODULAR_MISS_PENDING_EXACT_Q_COLUMN_GENERATION"
    };
    let output = FreshScanOutput {
        schema: "max11-g0117-fresh-modular-scan-v1",
        result,
        claim_boundary: "Two fresh modular quotient scans over all 163,740 columns of the exact 313-row iteration-1 system. Modular membership or nonmembership is not a Q decision, global identity, family-completeness theorem, or MAX11 result.",
        bindings,
        records_scanned: RECORDS,
        rows: ROWS,
        panel_rows: PANEL_ROWS,
        appended_rows: APPENDED_ROWS,
        direction: DIRECTION,
        primes: fresh_reports,
        modular_ranks_agree: ranks_agree,
        modular_target_decisions_agree: decisions_agree,
        all_columns_reopened: true,
        old_support_only: false,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    write_json_exclusive(output_path, &output)?;
    println!("{}", serde_json::to_string(&output)?);
    Ok(())
}

fn self_test() -> Result<()> {
    let digest_values = [1i64, -2i64];
    ensure!(
        digest_i64(digest_values.iter())
            == "ad47ab1aede0a7b8af007a36d82ccbbee709bec1066af6f44fed82bd2cb490ed",
        "i64 stream hashing is not the frozen single-update convention"
    );
    for prime in PRIMES {
        let matrix = vec![vec![1, 2, 0], vec![0, 1, 1], vec![2, 0, 1]];
        let inverse = invert(matrix.clone(), prime)?;
        let identity = matrix_product(&matrix, &inverse, prime);
        ensure!(
            identity == vec![vec![1, 0, 0], vec![0, 1, 0], vec![0, 0, 1]],
            "inverse control failed"
        );

        // Old support has only residual zero.  Reopening the family finds
        // sequence 1, after which the target residual is a member.
        let mut oracle = rank::LeftAnnihilator::new(2, prime);
        oracle.ingest_mod(0, &[0, 0]);
        ensure!(!oracle.contains_mod(&[1, 0]), "frozen-support plant failed");
        oracle.ingest_mod(1, &[1, 0]);
        ensure!(oracle.contains_mod(&[1, 0]), "full-family reopening failed");
    }
    let descriptors = ["panel:0".to_string(), "linear:0".to_string()];
    let forward = descriptor_digest(descriptors.clone().into_iter());
    let reverse = descriptor_digest(descriptors.into_iter().rev());
    ensure!(forward != reverse, "row reorder mutant escaped");
    ensure!(canonical_relative_path(Path::new(
        "artifacts/math/G-0117/x"
    )));
    ensure!(!canonical_relative_path(Path::new("../x")));
    println!(
        "fresh-q-cegis-scan-self-test: PASS (support reopening, inverse, reorder, path controls)"
    );
    Ok(())
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    match args.as_slice() {
        [_, command] if command == "--self-test" => self_test(),
        [
            _,
            command,
            input,
            panel_rows,
            cache,
            manifest,
            panel_scan,
            coordinate,
            accumulated_rows,
            output,
        ] if command == "scan" => scan(
            Path::new(input),
            Path::new(panel_rows),
            Path::new(cache),
            Path::new(manifest),
            Path::new(panel_scan),
            Path::new(coordinate),
            Path::new(accumulated_rows),
            Path::new(output),
        ),
        _ => anyhow::bail!(
            "usage: fresh_q_cegis --self-test | scan INPUT ROWS CACHE MANIFEST PANEL_SCAN COORDINATE ACCUMULATED_ROWS OUTPUT"
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hostile_controls() {
        self_test().unwrap();
    }
}
