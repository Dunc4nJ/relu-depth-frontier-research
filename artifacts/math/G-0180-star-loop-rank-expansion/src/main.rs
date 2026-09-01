use anyhow::{Context, Result, ensure};
use g0179_star_loop_pricer::{
    N, Record, directions_unique, hinge_coefficients_prevalidated, validate_direction,
    validate_record,
};
use rayon::prelude::*;
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::fs::{File, read};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const RECORD_SCHEMA: &str = "g0179.star-outside-primary-loop-records.v1";
const DIRECTION_SCHEMA: &str = "g0180.star-loop-rank-expansion-directions.v1";
const RECORD_FILE_SHA256: &str = "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4";
const DIRECTION_FILE_SHA256: &str =
    "546f0a248816487f104fe609261667ade9ef7823d3f38a6dadc70a2a5ca8da16";
const ALL_DIRECTION_I8_SHA256: &str =
    "973ed1a113beb8ed79d01cdbb3391e4fcdb9c94749082264acdebfd0f78340f8";
const PREFIX_480_I8_SHA256: &str =
    "3d83256a9c755a84a2b8b873f5baecc8e8e991c6007dcf2e108dbb9a07b37e5e";
const PREFIX_1024_I8_SHA256: &str =
    "197da75ae725a389d57934b2cb7ba81446420420ac7a60f7d0204b2e2c259323";
const INTRINSIC_RELATION_SHA256: &str =
    "c2fe511b628169929cce87fc116ab7fde09defc5746d1e40663660502d2ad6fa";
const EXCLUDED_SEQUENCES: [usize; 4] = [1_548, 3_140, 4_259, 5_656];
const PRICE_DIRECTIONS: usize = 1_024;

#[derive(Deserialize)]
struct RecordsDocument {
    schema: String,
    outside_records: usize,
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct DirectionOrder {
    all_count: usize,
    all_i8_sha256: String,
}

#[derive(Deserialize)]
struct DirectionGate {
    name: String,
    prefix_count: usize,
    i8_sha256: String,
}

#[derive(Deserialize)]
struct DirectionsDocument {
    schema: String,
    result: String,
    order: DirectionOrder,
    gates: Vec<DirectionGate>,
    directions: Vec<[i8; N]>,
}

fn sha256_bytes(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn sha256_path(path: &Path) -> Result<String> {
    Ok(sha256_bytes(
        &read(path).with_context(|| format!("read {}", path.display()))?,
    ))
}

fn direction_digest(directions: &[[i8; N]]) -> String {
    let mut digest = Sha256::new();
    for direction in directions {
        digest.update(direction.map(|value| value as u8));
    }
    format!("{:x}", digest.finalize())
}

fn parse_threads(arguments: &[String]) -> Result<usize> {
    if arguments.is_empty() {
        return Ok(std::thread::available_parallelism()?.get());
    }
    ensure!(
        arguments.len() == 2 && arguments[0] == "--threads",
        "expected only --threads N"
    );
    let threads = arguments[1].parse::<usize>().context("parse --threads")?;
    ensure!(threads > 0, "--threads must be positive");
    Ok(threads)
}

fn retained_records(records: &[Record]) -> Result<Vec<&Record>> {
    ensure!(records.len() == 5_773, "STAR record census drift");
    for (index, record) in records.iter().enumerate() {
        ensure!(record.sequence == index, "record sequence/index drift");
        validate_record(record)?;
    }
    let retained = records
        .iter()
        .filter(|record| !EXCLUDED_SEQUENCES.contains(&record.sequence))
        .collect::<Vec<_>>();
    ensure!(retained.len() == 5_769, "quotient record census drift");
    ensure!(
        retained
            .windows(2)
            .all(|pair| pair[0].sequence < pair[1].sequence),
        "quotient record order drift"
    );
    Ok(retained)
}

fn validate_directions(document: &DirectionsDocument) -> Result<&[[i8; N]]> {
    ensure!(
        document.schema == DIRECTION_SCHEMA,
        "direction schema drift"
    );
    ensure!(
        document.result == "NESTED_480_AND_1024_EXPANSION_FROZEN_BEFORE_STAR_PRICING",
        "direction result drift"
    );
    ensure!(
        document.order.all_count == 10_890
            && document.directions.len() == 10_890
            && document.order.all_i8_sha256 == ALL_DIRECTION_I8_SHA256
            && direction_digest(&document.directions) == ALL_DIRECTION_I8_SHA256,
        "full direction-order drift"
    );
    ensure!(
        directions_unique(&document.directions),
        "duplicate expansion direction"
    );
    for direction in &document.directions {
        validate_direction(direction)?;
        ensure!(direction[0] == 1, "expansion direction violates d0=1");
    }
    let gates = document
        .gates
        .iter()
        .map(|gate| {
            (
                gate.name.as_str(),
                gate.prefix_count,
                gate.i8_sha256.as_str(),
            )
        })
        .collect::<Vec<_>>();
    ensure!(
        gates
            == vec![
                ("hash-prefix-480", 480, PREFIX_480_I8_SHA256),
                ("rank-directed-1024", 1_024, PREFIX_1024_I8_SHA256),
            ],
        "direction gate drift"
    );
    ensure!(
        direction_digest(&document.directions[..480]) == PREFIX_480_I8_SHA256
            && direction_digest(&document.directions[..PRICE_DIRECTIONS]) == PREFIX_1024_I8_SHA256,
        "direction prefix digest drift"
    );
    Ok(&document.directions[..PRICE_DIRECTIONS])
}

fn source_bindings() -> Result<serde_json::Value> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let executable = std::env::current_exe()?.canonicalize()?;
    let manifest = root.join("Cargo.toml");
    let lock = root.join("Cargo.lock");
    let main = root.join("src/main.rs");
    let dependency_lib = root.join("../G-0179-star-loop-quarantine/src/lib.rs");
    Ok(json!({
        "cargo_manifest": manifest,
        "cargo_manifest_sha256": sha256_path(&manifest)?,
        "cargo_lock": lock,
        "cargo_lock_sha256": sha256_path(&lock)?,
        "main_source": main,
        "main_source_sha256": sha256_path(&main)?,
        "g0179_dependency_lib": dependency_lib,
        "g0179_dependency_lib_sha256": sha256_path(&dependency_lib)?,
        "executable": executable,
        "executable_sha256": sha256_path(&executable)?,
    }))
}

fn write_matrix(
    records: &[&Record],
    directions: &[[i8; N]],
    threads: usize,
    output: &Path,
) -> Result<serde_json::Value> {
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let started = Instant::now();
    let mut writer = BufWriter::with_capacity(1 << 20, File::create_new(output)?);
    let mut digest = Sha256::new();
    let mut minimum = i64::MAX;
    let mut maximum = i64::MIN;
    let mut nonzero = 0usize;
    for chunk in records.chunks(32) {
        let priced = pool.install(|| {
            chunk
                .par_iter()
                .map(|record| hinge_coefficients_prevalidated(record, directions))
                .collect::<Result<Vec<_>>>()
        })?;
        for row in priced {
            ensure!(row.len() == directions.len(), "matrix row-width drift");
            for value in row {
                ensure!(value >= 0, "negative hinge multiplicity");
                minimum = minimum.min(value);
                maximum = maximum.max(value);
                nonzero += usize::from(value != 0);
                let bytes = value.to_le_bytes();
                digest.update(bytes);
                writer.write_all(&bytes)?;
            }
        }
    }
    writer.flush()?;
    writer.get_ref().sync_all()?;
    let entries = records
        .len()
        .checked_mul(directions.len())
        .context("entry-count overflow")?;
    let bytes = entries.checked_mul(8).context("byte-count overflow")?;
    ensure!(
        std::fs::metadata(output)?.len() == u64::try_from(bytes)?,
        "matrix byte census drift"
    );
    let streaming_sha256 = format!("{:x}", digest.finalize());
    ensure!(
        sha256_path(output)? == streaming_sha256,
        "matrix end-rehash drift"
    );
    Ok(json!({
        "path": output,
        "layout": "record-major signed-i64 little-endian; quotient STAR records by expansion directions",
        "shape": [records.len(), directions.len()],
        "entries": entries,
        "bytes": bytes,
        "sha256": streaming_sha256,
        "minimum": minimum.to_string(),
        "maximum": maximum.to_string(),
        "nonzero_entries": nonzero,
        "zero_entries": entries - nonzero,
        "rehashed_after_sync": true,
        "wall_seconds": started.elapsed().as_secs_f64(),
    }))
}

fn write_json_new(path: &Path, value: &serde_json::Value) -> Result<()> {
    let mut writer = BufWriter::new(File::create_new(path)?);
    serde_json::to_writer(&mut writer, value)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    writer.get_ref().sync_all()?;
    Ok(())
}

fn main() -> Result<()> {
    let arguments = std::env::args().skip(1).collect::<Vec<_>>();
    ensure!(
        arguments.len() >= 6,
        "usage: g0180-star-loop-expansion-pricer price-prefix-1024 RECORDS.json DIRECTIONS.json INTRINSIC_RELATIONS.json MATRIX.i64le RECEIPT.json [--threads N]"
    );
    ensure!(
        arguments[0] == "price-prefix-1024",
        "expected price-prefix-1024 subcommand"
    );
    let records_path = PathBuf::from(&arguments[1]);
    let directions_path = PathBuf::from(&arguments[2]);
    let relations_path = PathBuf::from(&arguments[3]);
    let matrix_path = PathBuf::from(&arguments[4]);
    let receipt_path = PathBuf::from(&arguments[5]);
    let threads = parse_threads(&arguments[6..])?;
    ensure!(
        matrix_path != receipt_path,
        "matrix and receipt paths collide"
    );
    ensure!(
        !matrix_path.exists() && !receipt_path.exists(),
        "refusing overwrite"
    );

    let started = Instant::now();
    let records_bytes = read(&records_path)?;
    let directions_bytes = read(&directions_path)?;
    let relations_bytes = read(&relations_path)?;
    let opening = json!({
        "records": sha256_bytes(&records_bytes),
        "directions": sha256_bytes(&directions_bytes),
        "intrinsic_relations": sha256_bytes(&relations_bytes),
    });
    ensure!(
        opening["records"] == RECORD_FILE_SHA256,
        "record file hash drift"
    );
    ensure!(
        opening["directions"] == DIRECTION_FILE_SHA256,
        "direction file hash drift"
    );
    ensure!(
        opening["intrinsic_relations"] == INTRINSIC_RELATION_SHA256,
        "relation receipt hash drift"
    );

    let records_document: RecordsDocument = serde_json::from_slice(&records_bytes)?;
    ensure!(
        records_document.schema == RECORD_SCHEMA,
        "record schema drift"
    );
    ensure!(
        records_document.outside_records == 5_773,
        "outside-record census drift"
    );
    let directions_document: DirectionsDocument = serde_json::from_slice(&directions_bytes)?;
    let records = retained_records(&records_document.records)?;
    let directions = validate_directions(&directions_document)?;
    let source_opening = source_bindings()?;
    let matrix = write_matrix(&records, directions, threads, &matrix_path)?;

    ensure!(
        sha256_path(&records_path)? == RECORD_FILE_SHA256,
        "records changed during pricing"
    );
    ensure!(
        sha256_path(&directions_path)? == DIRECTION_FILE_SHA256,
        "directions changed during pricing"
    );
    ensure!(
        sha256_path(&relations_path)? == INTRINSIC_RELATION_SHA256,
        "relations changed during pricing"
    );
    ensure!(
        source_bindings()? == source_opening,
        "source or executable changed during pricing"
    );
    let mut sequence_digest = Sha256::new();
    for record in &records {
        sequence_digest.update((record.sequence as u64).to_le_bytes());
    }
    let receipt = json!({
        "schema": "g0180.quotient-expansion-price-matrix.v1",
        "result": "EXACT_5769_BY_1024_EXPANSION_PRICED_AWAITING_AUGMENTED_RANK",
        "claim_boundary": "Exact finite pricing after quotienting two independently certified O-relations. No rank, complete-kernel classification, target membership, representability theorem, or neural-network lower bound is claimed by this receipt.",
        "bindings": {
            "records": records_path,
            "records_sha256": RECORD_FILE_SHA256,
            "directions": directions_path,
            "directions_sha256": DIRECTION_FILE_SHA256,
            "intrinsic_relations": relations_path,
            "intrinsic_relations_sha256": INTRINSIC_RELATION_SHA256,
            "source": source_opening,
        },
        "quotient_records": {
            "available": records_document.records.len(),
            "excluded_sequences_exactly": EXCLUDED_SEQUENCES,
            "retained": records.len(),
            "sequence_u64le_sha256": format!("{:x}", sequence_digest.finalize()),
            "interpretation": "1548 and 4259 are in O; 3140 duplicates 22; 5656 has the same O-coset as 2986.",
        },
        "directions": {
            "priced_prefix": PRICE_DIRECTIONS,
            "prefix_480_i8_sha256": PREFIX_480_I8_SHA256,
            "prefix_1024_i8_sha256": PREFIX_1024_I8_SHA256,
            "full_frozen_order_count": 10_890,
            "full_frozen_order_i8_sha256": ALL_DIRECTION_I8_SHA256,
            "all_priced_directions_unique_primitive_active_d0_eq_1": true,
        },
        "matrix": matrix,
        "rank_gate": {
            "base_matrix_sha256": "0e7236e06adc906f2859338b12848e6fc04156963d1567de84dd1e83784162ad",
            "base_rank_mod_both_frozen_primes": 5_291,
            "target_quotient_row_rank": 5_769,
            "prefixes": [480, 1_024],
            "primes": [1_000_003, 1_000_033],
            "rank_not_computed_by_this_command": true,
        },
        "threads": threads,
        "all_inputs_source_and_executable_rehashed_at_end": true,
        "elapsed_seconds": started.elapsed().as_secs_f64(),
    });
    write_json_new(&receipt_path, &receipt)?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "result": receipt["result"],
            "shape": receipt["matrix"]["shape"],
            "matrix_sha256": receipt["matrix"]["sha256"],
            "receipt": receipt_path,
            "elapsed_seconds": receipt["elapsed_seconds"],
        }))?
    );
    Ok(())
}
