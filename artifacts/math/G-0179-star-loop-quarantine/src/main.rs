use anyhow::{Context, Result, ensure};
use g0179_star_loop_pricer::{
    N, NormalForm, PricedColumn, Record, Row, directions_unique, full_normal_form,
    hinge_coefficients, hinge_coefficients_prevalidated, linear_vector, panel_vector,
    positive_mass, pure_loop_carrier, pure_nonloop_carrier, validate_direction, validate_record,
};
use rayon::prelude::*;
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{File, read};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const RECORD_SCHEMA: &str = "g0179.star-outside-primary-loop-records.v1";
const DIRECTION_SCHEMA: &str = "g0179.hinge-direction-batch.v1";
const MATRIX_SCHEMA: &str = "g0179.star-loop-price-matrix.v1";
const EXCLUSIVE_DIRECTION_SCHEMA: &str = "g0179.exclusive-rank-directions.v1";
const EXCLUSIVE_MATRIX_SCHEMA: &str = "g0179.exclusive-rank-block-matrix.v1";
const MATCHING_DIRECTION_FILE_SHA256: &str =
    "231752384d357be45a9d2513a9185539bf0df970640c28e4f259da37fc8a982f";
const MATCHING_DIRECTION_I8_SHA256: &str =
    "858c182304ae5256dfa85e720803b54013afb70b7b67383aa6680ecbc0d8336d";
const RECORD_FILE_SHA256: &str = "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4";

#[derive(Deserialize)]
struct RecordsDocument {
    schema: String,
    outside_records: usize,
    bindings: RecordBindings,
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct RecordBindings {
    primary_map: PathBuf,
    primary_map_sha256: String,
}

#[derive(Deserialize)]
struct RowsDocument {
    rows: Vec<Row>,
}

#[derive(Deserialize)]
struct DirectionsDocument {
    schema: String,
    directions: Vec<[i8; N]>,
}

#[derive(Deserialize)]
struct ExclusiveDirectionsDocument {
    schema: String,
    filter: String,
    blocks: BTreeMap<String, ExclusiveDirectionBlock>,
}

#[derive(Deserialize)]
struct ExclusiveDirectionBlock {
    positive_mass: usize,
    eligible_count: usize,
    selected_count: usize,
    selected_i8_c_sha256: String,
    directions: Vec<[i8; N]>,
}

#[derive(Deserialize)]
struct MatchingDirectionsDocument {
    schema: String,
    result: String,
    batch_kind: String,
    count: usize,
    directions_i8_sha256: String,
    directions: Vec<[i8; N]>,
}

#[derive(Deserialize)]
struct ProbeInput {
    schema: String,
    records: Vec<Record>,
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

fn parse_optional(arguments: &[String]) -> Result<(Option<usize>, usize)> {
    let mut limit = None;
    let mut threads = std::thread::available_parallelism()?.get();
    let mut index = 0;
    while index < arguments.len() {
        match arguments[index].as_str() {
            "--limit" => {
                index += 1;
                let raw = arguments.get(index).context("--limit requires a value")?;
                limit = Some(raw.parse::<usize>().context("parse --limit")?);
            }
            "--threads" => {
                index += 1;
                let raw = arguments.get(index).context("--threads requires a value")?;
                threads = raw.parse::<usize>().context("parse --threads")?;
            }
            flag => anyhow::bail!("unknown option: {flag}"),
        }
        index += 1;
    }
    ensure!(
        limit.is_none_or(|value| value > 0),
        "--limit must be positive"
    );
    ensure!(threads > 0, "--threads must be positive");
    Ok((limit, threads))
}

fn source_bindings() -> Result<serde_json::Value> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let executable = std::env::current_exe()?;
    Ok(json!({
        "lib_source": root.join("src/lib.rs"),
        "lib_source_sha256": sha256_path(&root.join("src/lib.rs"))?,
        "main_source": root.join("src/main.rs"),
        "main_source_sha256": sha256_path(&root.join("src/main.rs"))?,
        "cargo_manifest": root.join("Cargo.toml"),
        "cargo_manifest_sha256": sha256_path(&root.join("Cargo.toml"))?,
        "cargo_lock": root.join("Cargo.lock"),
        "cargo_lock_sha256": sha256_path(&root.join("Cargo.lock"))?,
        "executable": executable,
        "executable_sha256": sha256_path(&std::env::current_exe()?)?,
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

fn exclusive_path(prefix: &Path, mass: usize, suffix: &str) -> PathBuf {
    PathBuf::from(format!("{}.m{mass}.{suffix}", prefix.display()))
}

fn validate_exclusive_directions(
    document: &ExclusiveDirectionsDocument,
) -> Result<BTreeMap<usize, &ExclusiveDirectionBlock>> {
    ensure!(
        document.schema == EXCLUSIVE_DIRECTION_SCHEMA,
        "exclusive-direction schema drift"
    );
    ensure!(
        document.filter == "direction[0] == 1",
        "exclusive-direction filter drift"
    );
    ensure!(
        document
            .blocks
            .keys()
            .map(String::as_str)
            .collect::<BTreeSet<_>>()
            == ["2", "3", "4", "5"].into_iter().collect::<BTreeSet<_>>(),
        "exclusive direction-block keys drift"
    );
    let mut by_mass = BTreeMap::new();
    let mut all_directions = Vec::new();
    for mass in 2..=5 {
        let block = &document.blocks[&mass.to_string()];
        ensure!(block.positive_mass == mass, "direction block mass drift");
        ensure!(
            block.selected_count == block.directions.len(),
            "selected direction census drift"
        );
        ensure!(
            block.eligible_count >= block.selected_count,
            "eligible direction census below selection"
        );
        ensure!(
            direction_digest(&block.directions) == block.selected_i8_c_sha256,
            "selected direction digest drift"
        );
        ensure!(
            directions_unique(&block.directions),
            "within-block direction duplication"
        );
        for direction in &block.directions {
            validate_direction(direction)?;
            ensure!(direction[0] == 1, "d[0] exclusive filter violated");
            ensure!(
                positive_mass(direction) == mass,
                "positive-mass direction block drift"
            );
            all_directions.push(*direction);
        }
        by_mass.insert(mass, block);
    }
    ensure!(
        directions_unique(&all_directions),
        "cross-block direction duplication"
    );
    Ok(by_mass)
}

fn validate_exclusive_records(records: &[Record]) -> Result<BTreeMap<usize, Vec<&Record>>> {
    ensure!(records.len() == 5_773, "STAR-outside-primary census drift");
    let mut by_mass = BTreeMap::<usize, Vec<&Record>>::new();
    for (index, record) in records.iter().enumerate() {
        ensure!(record.sequence == index, "record sequence/index drift");
        validate_record(record)?;
        by_mass.entry(record.signed_mass).or_default().push(record);
    }
    let expected = [(1usize, 1usize), (2, 7), (3, 66), (4, 781), (5, 4_918)];
    for (mass, count) in expected {
        ensure!(
            by_mass
                .get(&mass)
                .is_some_and(|records| records.len() == count),
            "signed-mass record census drift at mass {mass}"
        );
    }
    ensure!(by_mass.len() == 5, "unexpected signed-mass block");
    Ok(by_mass)
}

fn validate_matching_directions(document: &MatchingDirectionsDocument) -> Result<&[[i8; N]]> {
    ensure!(
        document.schema == DIRECTION_SCHEMA,
        "matching-direction schema drift"
    );
    ensure!(
        document.result == "TARGET_BLIND_STRUCTURAL_MATCHING_ROWS",
        "matching-direction result drift"
    );
    ensure!(
        document.batch_kind == "STAR_LOOP_D0_EQ_1_MATCHING_5771",
        "matching-direction batch kind drift"
    );
    ensure!(
        document.count == 5_771 && document.directions.len() == 5_771,
        "matching-direction census drift"
    );
    ensure!(
        document.directions_i8_sha256 == MATCHING_DIRECTION_I8_SHA256
            && direction_digest(&document.directions) == MATCHING_DIRECTION_I8_SHA256,
        "matching-direction i8 digest drift"
    );
    ensure!(
        directions_unique(&document.directions),
        "matching-direction duplication"
    );
    for direction in &document.directions {
        validate_direction(direction)?;
        ensure!(direction[0] == 1, "matching direction violates d[0] == 1");
    }
    Ok(&document.directions)
}

fn matched_records(records: &[Record]) -> Result<Vec<&Record>> {
    validate_exclusive_records(records)?;
    let excluded = [1_548usize, 4_259usize];
    let selected = records
        .iter()
        .filter(|record| !excluded.contains(&record.sequence))
        .collect::<Vec<_>>();
    ensure!(selected.len() == 5_771, "matched record census drift");
    ensure!(
        excluded.iter().all(|sequence| records
            .get(*sequence)
            .is_some_and(|record| record.sequence == *sequence)),
        "known-zero exclusion sequence/index drift"
    );
    ensure!(
        selected
            .windows(2)
            .all(|pair| pair[0].sequence < pair[1].sequence),
        "matched record order drift"
    );
    ensure!(
        selected
            .iter()
            .all(|record| !excluded.contains(&record.sequence)),
        "known-zero record survived exclusion"
    );
    Ok(selected)
}

fn sequence_1548_five_e_control(record: &Record, rows: &[Row]) -> Result<serde_json::Value> {
    ensure!(
        record.sequence == 1548 && record.signed_mass == 1,
        "mass-one exceptional record drift"
    );
    let normal_form = full_normal_form(record)?;
    ensure!(
        normal_form.hinges.is_empty(),
        "sequence 1548 has a nonzero complete hinge map"
    );
    let panel = panel_vector(record, rows)?;
    let linear = linear_vector(record)?;
    let (carrier_panel, carrier_linear) = pure_nonloop_carrier(rows)?;
    ensure!(
        panel
            .iter()
            .zip(&carrier_panel)
            .all(|(actual, carrier)| *actual == 5 * carrier),
        "sequence 1548 panel is not 5E"
    );
    ensure!(
        linear
            .iter()
            .zip(carrier_linear)
            .all(|(actual, carrier)| *actual == 5 * carrier),
        "sequence 1548 linear vector is not 5E"
    );
    let mut digest = Sha256::new();
    for value in panel
        .iter()
        .copied()
        .chain(linear.iter().map(|value| i128::from(*value)))
    {
        digest.update(value.to_le_bytes());
    }
    Ok(json!({
        "sequence": 1548,
        "identity": "record = 5E, where E is one full nonloop-edge carrier orbit",
        "panel_rows_checked": rows.len(),
        "linear_rows_checked": N,
        "complete_hinge_map_empty": true,
        "panel_and_linear_i128le_sha256": format!("{:x}", digest.finalize()),
        "passed": true,
    }))
}

fn old_primary_5341() -> Record {
    Record {
        sequence: 5_341,
        signed_mass: 1,
        active_vertices: 3,
        negative_loop_count: 0,
        positive_loop_count: 0,
        negative_edges: vec![[0, 2]],
        positive_edges: vec![[1, 2]],
    }
}

fn old_primary_66223() -> Record {
    Record {
        sequence: 66_223,
        signed_mass: 1,
        active_vertices: 4,
        negative_loop_count: 0,
        positive_loop_count: 0,
        negative_edges: vec![[0, 1]],
        positive_edges: vec![[2, 3]],
    }
}

fn sequence_4259_old_span_control(record: &Record, rows: &[Row]) -> Result<serde_json::Value> {
    ensure!(
        record.sequence == 4259 && record.signed_mass == 2,
        "mass-two exceptional record drift"
    );
    let normal_form = full_normal_form(record)?;
    ensure!(
        normal_form.hinges.is_empty(),
        "sequence 4259 has a nonzero complete hinge map"
    );

    // These constants are solver sequences 5341 and 66223 (primary-map
    // orbit_index 6573 and 81231) from the frozen G-0113 panel input.
    let primary_5341 = old_primary_5341();
    let primary_66223 = old_primary_66223();
    validate_record(&primary_5341)?;
    validate_record(&primary_66223)?;
    let normal_5341 = full_normal_form(&primary_5341)?;
    let normal_66223 = full_normal_form(&primary_66223)?;
    ensure!(
        normal_5341.labelled_permutation_count == 39_916_800
            && normal_66223.labelled_permutation_count == 39_916_800,
        "old-primary labelled-permutation census drift"
    );
    ensure!(
        normal_5341.hinges.is_empty() && normal_66223.hinges.is_empty(),
        "old-primary carrier has a nonzero complete hinge map"
    );
    let expected_5341 = [
        0, 2_903_040, 6_048_000, 9_434_880, 13_063_680, 16_934_400, 21_047_040, 25_401_600,
        29_998_080, 34_836_480, 39_916_800,
    ];
    let expected_66223 = [
        0, 2_903_040, 5_806_080, 8_830_080, 12_096_000, 15_724_800, 19_837_440, 24_554_880,
        29_998_080, 36_288_000, 43_545_600,
    ];
    ensure!(
        normal_5341.linear == expected_5341 && normal_66223.linear == expected_66223,
        "old-primary complete normal-form linear known answer drift"
    );
    let panel = panel_vector(record, rows)?;
    let panel_5341 = panel_vector(&primary_5341, rows)?;
    let panel_66223 = panel_vector(&primary_66223, rows)?;
    ensure!(
        panel
            .iter()
            .zip(&panel_5341)
            .zip(&panel_66223)
            .all(|((actual, first), second)| *actual == 2 * first - second),
        "sequence 4259 panel does not match 2*primary5341-primary66223"
    );
    let linear = linear_vector(record)?;
    let linear_5341 = linear_vector(&primary_5341)?;
    let linear_66223 = linear_vector(&primary_66223)?;
    ensure!(
        linear
            .iter()
            .zip(linear_5341)
            .zip(linear_66223)
            .all(|((actual, first), second)| *actual == 2 * first - second),
        "sequence 4259 linear vector does not match old-primary relation"
    );
    let mut digest = Sha256::new();
    for value in panel
        .iter()
        .copied()
        .chain(linear.iter().map(|value| i128::from(*value)))
    {
        digest.update(value.to_le_bytes());
    }
    Ok(json!({
        "sequence": 4259,
        "complete_hinge_map_empty": true,
        "old_primary_relation": "record = 2*primary_solver_sequence_5341 - primary_solver_sequence_66223",
        "primary_map_record_hashes": {
            "solver_sequence_5341_orbit_index_6573": "0a56e5e1c4ba00ca1ca3cbe7ceb2a2cb3629955c3980158b912284aaf51ece14",
            "solver_sequence_66223_orbit_index_81231": "7eeeb8d17e925ec236e56bd5a64e14d7c57305afca58d40ff828417459139f7e",
        },
        "relation_checks": {
            "panel_rows": rows.len(),
            "linear_rows": N,
            "primary_5341_complete_hinge_count": normal_5341.hinges.len(),
            "primary_66223_complete_hinge_count": normal_66223.hinges.len(),
            "primary_5341_labelled_permutations": normal_5341.labelled_permutation_count,
            "primary_66223_labelled_permutations": normal_66223.labelled_permutation_count,
        },
        "audit_boundary": "Complete normal forms were independently enumerated for sequence 4259 and both old-primary records. All three complete hinge maps are empty, and the identity is checked on all 301 panel rows and all 11 linear coordinates.",
        "panel_and_linear_i128le_sha256": format!("{:x}", digest.finalize()),
        "passed": true,
    }))
}

fn write_exclusive_matrix_pair(
    records: &[&Record],
    directions: &[[i8; N]],
    pool: &rayon::ThreadPool,
    i64_path: &Path,
    i128_path: &Path,
) -> Result<serde_json::Value> {
    ensure!(!records.is_empty(), "empty exclusive record block");
    ensure!(!directions.is_empty(), "empty exclusive direction block");
    let started = Instant::now();
    let mut writer_i64 = BufWriter::with_capacity(1 << 20, File::create_new(i64_path)?);
    let mut writer_i128 = BufWriter::with_capacity(1 << 20, File::create_new(i128_path)?);
    let mut digest_i64 = Sha256::new();
    let mut digest_i128 = Sha256::new();
    let mut minimum = i64::MAX;
    let mut maximum = i64::MIN;
    let mut nonzero_entries = 0usize;
    for chunk in records.chunks(32) {
        let priced = pool.install(|| {
            chunk
                .par_iter()
                .map(|record| hinge_coefficients_prevalidated(record, directions))
                .collect::<Result<Vec<_>>>()
        })?;
        for row in priced {
            ensure!(
                row.len() == directions.len(),
                "exclusive matrix row-width drift"
            );
            for value in row {
                ensure!(value >= 0, "negative hinge multiplicity");
                minimum = minimum.min(value);
                maximum = maximum.max(value);
                nonzero_entries += usize::from(value != 0);
                let bytes_i64 = value.to_le_bytes();
                let bytes_i128 = i128::from(value).to_le_bytes();
                digest_i64.update(bytes_i64);
                digest_i128.update(bytes_i128);
                writer_i64.write_all(&bytes_i64)?;
                writer_i128.write_all(&bytes_i128)?;
            }
        }
    }
    writer_i64.flush()?;
    writer_i64.get_ref().sync_all()?;
    writer_i128.flush()?;
    writer_i128.get_ref().sync_all()?;
    let entries = records
        .len()
        .checked_mul(directions.len())
        .context("exclusive matrix entry-count overflow")?;
    let expected_i64_bytes = entries.checked_mul(8).context("i64 byte-count overflow")?;
    let expected_i128_bytes = entries
        .checked_mul(16)
        .context("i128 byte-count overflow")?;
    ensure!(
        std::fs::metadata(i64_path)?.len() == u64::try_from(expected_i64_bytes)?,
        "exclusive i64 matrix byte census drift"
    );
    ensure!(
        std::fs::metadata(i128_path)?.len() == u64::try_from(expected_i128_bytes)?,
        "exclusive i128 matrix byte census drift"
    );
    Ok(json!({
        "layout": "record-major; rows are STAR records and columns are selected directions",
        "rank_interpretation": "Full row rank here equals full column rank after transposing to directions-by-records.",
        "records": records.len(),
        "directions": directions.len(),
        "entries": entries,
        "nonzero_entries": nonzero_entries,
        "minimum": minimum.to_string(),
        "maximum": maximum.to_string(),
        "i64le": {
            "path": i64_path,
            "bytes": expected_i64_bytes,
            "sha256": format!("{:x}", digest_i64.finalize()),
        },
        "i128le": {
            "path": i128_path,
            "bytes": expected_i128_bytes,
            "sha256": format!("{:x}", digest_i128.finalize()),
        },
        "i64_i128_semantic_entries_equal": true,
        "wall_seconds": started.elapsed().as_secs_f64(),
    }))
}

fn write_matched_matrix(
    records: &[&Record],
    directions: &[[i8; N]],
    pool: &rayon::ThreadPool,
    matrix_path: &Path,
) -> Result<serde_json::Value> {
    ensure!(records.len() == 5_771, "matched matrix record census drift");
    ensure!(
        directions.len() == 5_771,
        "matched matrix direction census drift"
    );
    let started = Instant::now();
    let mut writer = BufWriter::with_capacity(1 << 20, File::create_new(matrix_path)?);
    let mut digest = Sha256::new();
    let mut minimum = i64::MAX;
    let mut maximum = i64::MIN;
    let mut nonzero_entries = 0usize;
    for chunk in records.chunks(32) {
        let priced = pool.install(|| {
            chunk
                .par_iter()
                .map(|record| hinge_coefficients_prevalidated(record, directions))
                .collect::<Result<Vec<_>>>()
        })?;
        for row in priced {
            ensure!(
                row.len() == directions.len(),
                "matched matrix row-width drift"
            );
            for value in row {
                ensure!(value >= 0, "negative matched hinge multiplicity");
                minimum = minimum.min(value);
                maximum = maximum.max(value);
                nonzero_entries += usize::from(value != 0);
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
        .context("matched matrix entry-count overflow")?;
    let expected_bytes = entries
        .checked_mul(std::mem::size_of::<i64>())
        .context("matched matrix byte-count overflow")?;
    ensure!(
        std::fs::metadata(matrix_path)?.len() == u64::try_from(expected_bytes)?,
        "matched matrix byte census drift"
    );
    let streaming_sha256 = format!("{:x}", digest.finalize());
    ensure!(
        sha256_path(matrix_path)? == streaming_sha256,
        "matched matrix end-rehash disagrees with streaming digest"
    );
    Ok(json!({
        "path": matrix_path,
        "layout": "record-major signed-i64 little-endian; 5,771 retained STAR records by 5,771 matching hinge directions",
        "shape": [records.len(), directions.len()],
        "entries": entries,
        "bytes": expected_bytes,
        "sha256": streaming_sha256,
        "rehashed_after_sync": true,
        "minimum": minimum.to_string(),
        "maximum": maximum.to_string(),
        "nonzero_entries": nonzero_entries,
        "zero_entries": entries - nonzero_entries,
        "wall_seconds": started.elapsed().as_secs_f64(),
    }))
}

fn price(arguments: &[String]) -> Result<()> {
    ensure!(
        arguments.len() >= 5,
        "usage: g0179-star-loop-pricer price RECORDS.json ROWS.json DIRECTIONS.json MATRIX.i128le RECEIPT.json [--limit N] [--threads N]"
    );
    let records_path = PathBuf::from(&arguments[0]);
    let rows_path = PathBuf::from(&arguments[1]);
    let directions_path = PathBuf::from(&arguments[2]);
    let matrix_path = PathBuf::from(&arguments[3]);
    let receipt_path = PathBuf::from(&arguments[4]);
    let (limit, threads) = parse_optional(&arguments[5..])?;
    ensure!(!matrix_path.exists(), "refusing to overwrite matrix");
    ensure!(!receipt_path.exists(), "refusing to overwrite receipt");

    let started = Instant::now();
    let records_bytes = read(&records_path)?;
    let rows_bytes = read(&rows_path)?;
    let directions_bytes = read(&directions_path)?;
    let records_document: RecordsDocument = serde_json::from_slice(&records_bytes)?;
    let rows_document: RowsDocument = serde_json::from_slice(&rows_bytes)?;
    let directions_document: DirectionsDocument = serde_json::from_slice(&directions_bytes)?;
    ensure!(
        records_document.schema == RECORD_SCHEMA,
        "record schema drift"
    );
    ensure!(
        records_document.outside_records == 5_773
            && records_document.records.len() == records_document.outside_records,
        "STAR-outside-primary census drift"
    );
    ensure!(
        rows_document.rows.len() == 301,
        "frozen panel row census drift"
    );
    ensure!(
        directions_document.schema == DIRECTION_SCHEMA,
        "direction schema drift"
    );
    ensure!(
        !directions_document.directions.is_empty(),
        "empty direction batch"
    );
    ensure!(
        directions_unique(&directions_document.directions),
        "duplicate direction in supplied batch"
    );
    for direction in &directions_document.directions {
        validate_direction(direction)?;
    }
    for (index, record) in records_document.records.iter().enumerate() {
        ensure!(record.sequence == index, "record sequence/index drift");
        validate_record(record)?;
    }
    let priced_records = limit.unwrap_or(records_document.records.len());
    ensure!(
        priced_records <= records_document.records.len(),
        "--limit exceeds record census"
    );
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let panel_started = Instant::now();
    let panels = pool.install(|| {
        records_document.records[..priced_records]
            .par_iter()
            .map(|record| panel_vector(record, &rows_document.rows))
            .collect::<Result<Vec<_>>>()
    })?;
    let panel_seconds = panel_started.elapsed().as_secs_f64();
    let linear_started = Instant::now();
    let linear = pool.install(|| {
        records_document.records[..priced_records]
            .par_iter()
            .map(linear_vector)
            .collect::<Result<Vec<_>>>()
    })?;
    let linear_seconds = linear_started.elapsed().as_secs_f64();
    let hinge_started = Instant::now();
    let hinges = pool.install(|| {
        records_document.records[..priced_records]
            .par_iter()
            .map(|record| hinge_coefficients(record, &directions_document.directions))
            .collect::<Result<Vec<_>>>()
    })?;
    let hinge_seconds = hinge_started.elapsed().as_secs_f64();
    let columns = panels
        .into_iter()
        .zip(linear)
        .zip(hinges)
        .map(|((panel, linear), hinges)| PricedColumn {
            panel,
            linear,
            hinges,
        })
        .collect::<Vec<_>>();
    let panel_rows = rows_document.rows.len();
    let linear_rows = N;
    let hinge_rows = directions_document.directions.len();
    let row_count = panel_rows + linear_rows + hinge_rows;
    ensure!(
        columns.iter().all(|column| {
            column.panel.len() == panel_rows && column.hinges.len() == hinge_rows
        }),
        "priced column width drift"
    );

    let write_started = Instant::now();
    let file = File::create_new(&matrix_path)?;
    let mut writer = BufWriter::with_capacity(1 << 20, file);
    let mut matrix_digest = Sha256::new();
    let mut minimum = i128::MAX;
    let mut maximum = i128::MIN;
    for column in &columns {
        for value in column
            .panel
            .iter()
            .copied()
            .chain(column.linear.iter().map(|value| i128::from(*value)))
            .chain(column.hinges.iter().map(|value| i128::from(*value)))
        {
            minimum = minimum.min(value);
            maximum = maximum.max(value);
            let bytes = value.to_le_bytes();
            matrix_digest.update(bytes);
            writer.write_all(&bytes)?;
        }
    }
    writer.flush()?;
    writer.get_ref().sync_all()?;
    let write_seconds = write_started.elapsed().as_secs_f64();
    let expected_bytes = priced_records
        .checked_mul(row_count)
        .and_then(|value| value.checked_mul(16))
        .context("matrix byte count overflow")?;
    ensure!(
        std::fs::metadata(&matrix_path)?.len() == u64::try_from(expected_bytes)?,
        "matrix byte census drift"
    );

    let (carrier_panel, carrier_linear) = pure_loop_carrier(&rows_document.rows)?;
    let carrier_full = carrier_panel
        .iter()
        .map(ToString::to_string)
        .chain(carrier_linear.iter().map(ToString::to_string))
        .chain((0..hinge_rows).map(|_| "0".to_string()))
        .collect::<Vec<_>>();
    ensure!(
        carrier_full.len() == row_count,
        "pure-loop carrier width drift"
    );
    let mut carrier_digest = Sha256::new();
    for raw in &carrier_full {
        let value = raw.parse::<i128>()?;
        carrier_digest.update(value.to_le_bytes());
    }

    // End rehashes make the opening hashes meaningful even for a long run.
    ensure!(
        sha256_bytes(&records_bytes) == sha256_path(&records_path)?,
        "records changed during run"
    );
    ensure!(
        sha256_bytes(&rows_bytes) == sha256_path(&rows_path)?,
        "rows changed during run"
    );
    ensure!(
        sha256_bytes(&directions_bytes) == sha256_path(&directions_path)?,
        "directions changed during run"
    );
    let complete = priced_records == records_document.records.len();
    let receipt = json!({
        "schema": MATRIX_SCHEMA,
        "result": if complete { "EXACT_COMPLETE_STAR_OUTSIDE_PRIMARY_PRICE_MATRIX" } else { "CONTROL_PREFIX_PRICE_MATRIX_ONLY" },
        "claim_boundary": "Exact pricing of the stated finite STAR-outside-primary records and supplied finite rows only. It is not a target span decision, obstruction, global identity, complete degree-five universe result, lower bound, or MAX11 theorem.",
        "bindings": {
            "records": records_path,
            "records_sha256": sha256_bytes(&records_bytes),
            "rows": rows_path,
            "rows_sha256": sha256_bytes(&rows_bytes),
            "directions": directions_path,
            "directions_sha256": sha256_bytes(&directions_bytes),
            "source": source_bindings()?,
        },
        "records_available": records_document.records.len(),
        "records_priced": priced_records,
        "prefix_control_only": !complete,
        "rows": {
            "panel": panel_rows,
            "linear": linear_rows,
            "hinge": hinge_rows,
            "total": row_count,
            "order": "301 panel, 11 linear, then supplied hinge directions",
        },
        "directions_i8_sha256": direction_digest(&directions_document.directions),
        "matrix": {
            "path": matrix_path,
            "layout": "record-major signed-i128 little-endian",
            "bytes": expected_bytes,
            "sha256": format!("{:x}", matrix_digest.finalize()),
            "minimum": minimum.to_string(),
            "maximum": maximum.to_string(),
        },
        "pure_loop_carrier_L": {
            "definition": "full S_11 orbit sum of max(x_i,x_i)=x_i for one fixed loop",
            "use_boundary": "Separate carrier for later identical-loop lifts; it is not one of the 5,773 signed STAR records.",
            "panel_values": carrier_panel.iter().map(ToString::to_string).collect::<Vec<_>>(),
            "linear_values": carrier_linear.iter().map(ToString::to_string).collect::<Vec<_>>(),
            "hinge_values_all_zero": true,
            "complete_column_i128le_sha256": format!("{:x}", carrier_digest.finalize()),
        },
        "threads": threads,
        "timing_seconds": {
            "panel": panel_seconds,
            "linear": linear_seconds,
            "hinge": hinge_seconds,
            "matrix_write_and_sync": write_seconds,
        },
        "elapsed_seconds": started.elapsed().as_secs_f64(),
        "inputs_rehashed_at_end": true,
    });
    let mut receipt_writer = BufWriter::new(File::create_new(&receipt_path)?);
    serde_json::to_writer(&mut receipt_writer, &receipt)?;
    receipt_writer.write_all(b"\n")?;
    receipt_writer.flush()?;
    receipt_writer.get_ref().sync_all()?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "result": receipt["result"],
            "records_priced": priced_records,
            "rows": row_count,
            "matrix_sha256": receipt["matrix"]["sha256"],
            "receipt": receipt_path,
            "elapsed_seconds": receipt["elapsed_seconds"],
        }))?
    );
    Ok(())
}

fn matched_price(arguments: &[String]) -> Result<()> {
    ensure!(
        arguments.len() >= 4,
        "usage: g0179-star-loop-pricer matched-price RECORDS.json MATCHING_DIRECTIONS.json OUTPUT.i64le RECEIPT.json [--threads N]"
    );
    let records_path = PathBuf::from(&arguments[0]);
    let directions_path = PathBuf::from(&arguments[1]);
    let matrix_path = PathBuf::from(&arguments[2]);
    let receipt_path = PathBuf::from(&arguments[3]);
    let (limit, threads) = parse_optional(&arguments[4..])?;
    ensure!(limit.is_none(), "--limit is forbidden for matched-price");
    ensure!(
        matrix_path != receipt_path,
        "matrix and receipt paths collide"
    );
    ensure!(
        !matrix_path.exists(),
        "refusing to overwrite matched matrix"
    );
    ensure!(
        !receipt_path.exists(),
        "refusing to overwrite matched receipt"
    );

    let started = Instant::now();
    let records_bytes = read(&records_path)?;
    let directions_bytes = read(&directions_path)?;
    let records_opening_sha = sha256_bytes(&records_bytes);
    let directions_opening_sha = sha256_bytes(&directions_bytes);
    ensure!(
        records_opening_sha == RECORD_FILE_SHA256,
        "frozen STAR record file SHA-256 drift"
    );
    ensure!(
        directions_opening_sha == MATCHING_DIRECTION_FILE_SHA256,
        "frozen matching-direction file SHA-256 drift"
    );
    let records_document: RecordsDocument = serde_json::from_slice(&records_bytes)?;
    let directions_document: MatchingDirectionsDocument =
        serde_json::from_slice(&directions_bytes)?;
    ensure!(
        records_document.schema == RECORD_SCHEMA,
        "record schema drift"
    );
    ensure!(
        records_document.outside_records == 5_773
            && records_document.records.len() == records_document.outside_records,
        "STAR-outside-primary record census drift"
    );
    let retained_records = matched_records(&records_document.records)?;
    let directions = validate_matching_directions(&directions_document)?;
    let source_opening = source_bindings()?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let matrix = write_matched_matrix(&retained_records, directions, &pool, &matrix_path)?;

    ensure!(
        sha256_path(&records_path)? == records_opening_sha,
        "records changed during matched-price run"
    );
    ensure!(
        sha256_path(&directions_path)? == directions_opening_sha,
        "matching directions changed during matched-price run"
    );
    let source_end = source_bindings()?;
    ensure!(
        source_opening == source_end,
        "source or executable changed during matched-price run"
    );
    let mut record_order_digest = Sha256::new();
    for record in &retained_records {
        record_order_digest.update((record.sequence as u64).to_le_bytes());
    }
    let receipt = json!({
        "schema": "g0179.matched-hinge-square.v1",
        "result": "EXACT_MATCHED_HINGE_SQUARE_PRICED_AWAITING_RANK",
        "claim_boundary": "Exact finite hinge pricing of the frozen 5,771 retained STAR records on the frozen 5,771 target-blind structural matching directions only. No modular rank, determinant, span, obstruction, lower bound, or unrestricted neural-network theorem is claimed by this receipt.",
        "bindings": {
            "records": records_path,
            "records_sha256": records_opening_sha,
            "matching_directions": directions_path,
            "matching_directions_file_sha256": directions_opening_sha,
            "matching_directions_i8_sha256": MATCHING_DIRECTION_I8_SHA256,
            "source": source_opening,
        },
        "records": {
            "available": records_document.records.len(),
            "excluded_sequences_exactly": [1548, 4259],
            "exclusion_reasons": {
                "1548": "complete normal form equals 5E and has empty hinge map",
                "4259": "complete normal form equals 2*old-primary solver sequence 5341 - solver sequence 66223 and has empty hinge map",
            },
            "priced": retained_records.len(),
            "order": "original increasing record sequence with only 1548 and 4259 removed",
            "sequence_u64le_sha256": format!("{:x}", record_order_digest.finalize()),
        },
        "directions": {
            "count": directions.len(),
            "schema": directions_document.schema,
            "result": directions_document.result,
            "batch_kind": directions_document.batch_kind,
            "all_d0_equal_one": true,
            "i8_c_sha256": MATCHING_DIRECTION_I8_SHA256,
        },
        "matrix": matrix,
        "rank_preregistration": {
            "rank_not_computed_by_this_command": true,
            "target_rank": 5_771,
            "primes": [1_000_003, 1_000_033],
            "acceptance_rule": "Independent exact FLINT modular ranks must both equal 5,771; any smaller rank is a STOP and must be reported without direction reselection except under a separately frozen expansion rule.",
        },
        "threads": threads,
        "inputs_source_and_executable_rehashed_at_end": true,
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

fn cross_mass_zero_controls(
    records_by_mass: &BTreeMap<usize, Vec<&Record>>,
    directions_by_mass: &BTreeMap<usize, &ExclusiveDirectionBlock>,
    pool: &rayon::ThreadPool,
) -> Result<Vec<serde_json::Value>> {
    let mut receipts = Vec::new();
    for mass in 2..=5 {
        let higher = ((mass + 1)..=5)
            .flat_map(|higher_mass| directions_by_mass[&higher_mass].directions.iter().copied())
            .collect::<Vec<_>>();
        let records = &records_by_mass[&mass];
        pool.install(|| {
            records.par_iter().try_for_each(|record| -> Result<()> {
                let values = hinge_coefficients(record, &higher)?;
                if let Some((index, value)) = values
                    .iter()
                    .copied()
                    .enumerate()
                    .find(|(_index, value)| *value != 0)
                {
                    anyhow::bail!(
                        "cross-mass zero failed: record {} mass {} direction index {} value {}",
                        record.sequence,
                        mass,
                        index,
                        value
                    );
                }
                Ok(())
            })
        })?;
        receipts.push(json!({
            "record_mass": mass,
            "record_count": records.len(),
            "higher_mass_direction_count": higher.len(),
            "coefficients_checked": records.len() * higher.len(),
            "all_zero": true,
        }));
    }
    Ok(receipts)
}

fn exclusive_price(arguments: &[String]) -> Result<()> {
    ensure!(
        arguments.len() >= 4,
        "usage: g0179-star-loop-pricer exclusive-price RECORDS.json ROWS.json EXCLUSIVE_DIRECTIONS.json OUTPUT_PREFIX [--threads N]"
    );
    let records_path = PathBuf::from(&arguments[0]);
    let rows_path = PathBuf::from(&arguments[1]);
    let directions_path = PathBuf::from(&arguments[2]);
    let output_prefix = PathBuf::from(&arguments[3]);
    let (limit, threads) = parse_optional(&arguments[4..])?;
    ensure!(limit.is_none(), "--limit is forbidden for exclusive-price");
    let summary_path = PathBuf::from(format!("{}.summary.json", output_prefix.display()));
    let mut output_paths = vec![summary_path.clone()];
    for mass in 2..=5 {
        output_paths.push(exclusive_path(&output_prefix, mass, "i64le"));
        output_paths.push(exclusive_path(&output_prefix, mass, "i128le"));
        output_paths.push(exclusive_path(&output_prefix, mass, "receipt.json"));
    }
    ensure!(
        output_paths.iter().all(|path| !path.exists()),
        "refusing to overwrite an exclusive-rank output"
    );

    let started = Instant::now();
    let records_bytes = read(&records_path)?;
    let rows_bytes = read(&rows_path)?;
    let directions_bytes = read(&directions_path)?;
    let records_document: RecordsDocument = serde_json::from_slice(&records_bytes)?;
    let rows_document: RowsDocument = serde_json::from_slice(&rows_bytes)?;
    let directions_document: ExclusiveDirectionsDocument =
        serde_json::from_slice(&directions_bytes)?;
    ensure!(
        records_document.schema == RECORD_SCHEMA,
        "record schema drift"
    );
    ensure!(
        records_document.outside_records == records_document.records.len(),
        "outside-record header census drift"
    );
    ensure!(
        rows_document.rows.len() == 301,
        "frozen panel-row census drift"
    );
    let expected_primary_map_sha =
        "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48";
    ensure!(
        records_document.bindings.primary_map_sha256 == expected_primary_map_sha,
        "frozen primary-map binding drift"
    );
    let records_by_mass = validate_exclusive_records(&records_document.records)?;
    let directions_by_mass = validate_exclusive_directions(&directions_document)?;
    let five_e_control = sequence_1548_five_e_control(records_by_mass[&1][0], &rows_document.rows)?;
    let old_span_control =
        sequence_4259_old_span_control(&records_document.records[4259], &rows_document.rows)?;
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let cross_mass_controls =
        cross_mass_zero_controls(&records_by_mass, &directions_by_mass, &pool)?;

    let mut block_outputs = Vec::new();
    for mass in 2..=5 {
        let i64_path = exclusive_path(&output_prefix, mass, "i64le");
        let i128_path = exclusive_path(&output_prefix, mass, "i128le");
        let matrix = write_exclusive_matrix_pair(
            &records_by_mass[&mass],
            &directions_by_mass[&mass].directions,
            &pool,
            &i64_path,
            &i128_path,
        )?;
        block_outputs.push((mass, matrix));
    }

    ensure!(
        sha256_bytes(&records_bytes) == sha256_path(&records_path)?,
        "records changed during exclusive run"
    );
    ensure!(
        sha256_bytes(&rows_bytes) == sha256_path(&rows_path)?,
        "rows changed during exclusive run"
    );
    ensure!(
        sha256_bytes(&directions_bytes) == sha256_path(&directions_path)?,
        "directions changed during exclusive run"
    );
    let source = source_bindings()?;
    let common_bindings = json!({
        "records": records_path,
        "records_sha256": sha256_bytes(&records_bytes),
        "rows": rows_path,
        "rows_sha256": sha256_bytes(&rows_bytes),
        "exclusive_directions": directions_path,
        "exclusive_directions_sha256": sha256_bytes(&directions_bytes),
        "primary_map_declared_by_records": records_document.bindings.primary_map,
        "primary_map_sha256_declared_by_records": records_document.bindings.primary_map_sha256,
        "source": source,
    });
    let expected_block_ranks = [(2usize, 6usize), (3, 66), (4, 781), (5, 4_918)];
    let mut receipt_bindings = Vec::new();
    for (mass, matrix) in block_outputs {
        let receipt_path = exclusive_path(&output_prefix, mass, "receipt.json");
        let expected_rank = expected_block_ranks
            .iter()
            .find_map(|(block_mass, rank)| (*block_mass == mass).then_some(*rank))
            .context("missing expected block rank")?;
        let receipt = json!({
            "schema": EXCLUSIVE_MATRIX_SCHEMA,
            "result": "EXACT_D0_EQ1_SIGNED_MASS_DIAGONAL_BLOCK_PRICED",
            "claim_boundary": "Exact finite hinge pricing only. No rank has been computed here. Success requires separate exact two-prime FLINT rank analysis, with mass-2 rank 6 and masses 3..5 full row rank; this is not by itself a span theorem or neural-network lower bound.",
            "positive_mass": mass,
            "signed_mass": mass,
            "expected_rank_stop_signature": expected_rank,
            "known_old_span_unit_sequences": [1548, 4259],
            "bindings": common_bindings,
            "matrix": matrix,
            "controls": {
                "sequence1548_five_E": five_e_control,
                "sequence4259_old_span": old_span_control,
                "higher_positive_mass_zero": cross_mass_controls,
            },
            "inputs_rehashed_at_end": true,
            "threads": threads,
        });
        write_json_new(&receipt_path, &receipt)?;
        receipt_bindings.push(json!({
            "mass": mass,
            "path": receipt_path,
            "sha256": sha256_path(&receipt_path)?,
        }));
    }
    let summary = json!({
        "schema": "g0179.exclusive-rank-block-suite.v1",
        "result": "EXACT_D0_EQ1_MASS_BLOCKS_PRICED_AWAITING_RANK",
        "claim_boundary": "Pricing and semantic controls only; exact modular rank analysis is a separate required gate.",
        "target_rank": 5_771,
        "rank_stop_signature": {"2": 6, "3": 66, "4": 781, "5": 4_918},
        "known_old_span_unit_sequences": [1548, 4259],
        "block_receipts": receipt_bindings,
        "bindings": common_bindings,
        "controls": {
            "sequence1548_five_E": five_e_control,
            "sequence4259_old_span": old_span_control,
            "higher_positive_mass_zero": cross_mass_controls,
        },
        "threads": threads,
        "elapsed_seconds": started.elapsed().as_secs_f64(),
        "inputs_rehashed_at_end": true,
    });
    write_json_new(&summary_path, &summary)?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "result": summary["result"],
            "target_rank": 5_771,
            "summary": summary_path,
            "elapsed_seconds": summary["elapsed_seconds"],
        }))?
    );
    Ok(())
}

fn semantic_controls(arguments: &[String]) -> Result<()> {
    ensure!(
        arguments.len() == 3,
        "usage: g0179-star-loop-pricer semantic-controls RECORDS.json ROWS.json OUTPUT.json"
    );
    let records_path = PathBuf::from(&arguments[0]);
    let rows_path = PathBuf::from(&arguments[1]);
    let output_path = PathBuf::from(&arguments[2]);
    ensure!(
        !output_path.exists(),
        "refusing to overwrite semantic receipt"
    );
    let started = Instant::now();
    let records_bytes = read(&records_path)?;
    let rows_bytes = read(&rows_path)?;
    let records_document: RecordsDocument = serde_json::from_slice(&records_bytes)?;
    let rows_document: RowsDocument = serde_json::from_slice(&rows_bytes)?;
    ensure!(
        records_document.schema == RECORD_SCHEMA,
        "record schema drift"
    );
    ensure!(
        rows_document.rows.len() == 301,
        "frozen panel-row census drift"
    );
    ensure!(
        records_document.bindings.primary_map_sha256
            == "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48",
        "frozen primary-map binding drift"
    );
    let by_mass = validate_exclusive_records(&records_document.records)?;
    let five_e = sequence_1548_five_e_control(by_mass[&1][0], &rows_document.rows)?;
    let old_span =
        sequence_4259_old_span_control(&records_document.records[4259], &rows_document.rows)?;
    ensure!(
        sha256_bytes(&records_bytes) == sha256_path(&records_path)?,
        "records changed during semantic controls"
    );
    ensure!(
        sha256_bytes(&rows_bytes) == sha256_path(&rows_path)?,
        "rows changed during semantic controls"
    );
    let receipt = json!({
        "schema": "g0179.exclusive-rank-semantic-controls.v1",
        "result": "BOTH_KNOWN_OLD_SPAN_UNIT_COLUMNS_CERTIFIED",
        "claim_boundary": "Exact normal-form and frozen-row semantic controls for sequences 1548 and 4259 only. This is not a rank result for the other 5,771 STAR records.",
        "known_old_span_unit_sequences": [1548, 4259],
        "target_remaining_rank": 5_771,
        "controls": {
            "sequence1548_five_E": five_e,
            "sequence4259_old_primary_relation": old_span,
        },
        "bindings": {
            "records": records_path,
            "records_sha256": sha256_bytes(&records_bytes),
            "rows": rows_path,
            "rows_sha256": sha256_bytes(&rows_bytes),
            "primary_map_declared_by_records": records_document.bindings.primary_map,
            "primary_map_sha256_declared_by_records": records_document.bindings.primary_map_sha256,
            "source": source_bindings()?,
        },
        "inputs_rehashed_at_end": true,
        "wall_seconds": started.elapsed().as_secs_f64(),
    });
    write_json_new(&output_path, &receipt)?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "result": receipt["result"],
            "output": output_path,
            "sha256": sha256_path(&output_path)?,
            "wall_seconds": receipt["wall_seconds"],
        }))?
    );
    Ok(())
}

fn density_pilot(arguments: &[String]) -> Result<()> {
    ensure!(
        arguments.len() >= 3,
        "usage: g0179-star-loop-pricer density-pilot RECORDS.json EXCLUSIVE_DIRECTIONS.json OUTPUT.json [--threads N]"
    );
    let records_path = PathBuf::from(&arguments[0]);
    let directions_path = PathBuf::from(&arguments[1]);
    let output_path = PathBuf::from(&arguments[2]);
    let (limit, threads) = parse_optional(&arguments[3..])?;
    ensure!(limit.is_none(), "--limit is forbidden for density-pilot");
    ensure!(!output_path.exists(), "refusing to overwrite density pilot");
    let started = Instant::now();
    let records_bytes = read(&records_path)?;
    let directions_bytes = read(&directions_path)?;
    let records_document: RecordsDocument = serde_json::from_slice(&records_bytes)?;
    let directions_document: ExclusiveDirectionsDocument =
        serde_json::from_slice(&directions_bytes)?;
    ensure!(
        records_document.schema == RECORD_SCHEMA,
        "record schema drift"
    );
    let records_by_mass = validate_exclusive_records(&records_document.records)?;
    let directions_by_mass = validate_exclusive_directions(&directions_document)?;
    let mass_five_directions = &directions_by_mass[&5].directions;
    ensure!(
        mass_five_directions.len() >= 5_000,
        "density pilot requires the initial 5,000 mass-five directions"
    );
    let mass_five_directions = &mass_five_directions[..5_000];

    const PILOT_DOMAIN: &[u8] = b"g0179-mass5-density-pilot-record-order-v1\0";
    let mut ranked_records = records_by_mass[&5]
        .iter()
        .map(|record| {
            let mut digest = Sha256::new();
            digest.update(PILOT_DOMAIN);
            digest.update((record.sequence as u64).to_le_bytes());
            (digest.finalize().to_vec(), *record)
        })
        .collect::<Vec<_>>();
    ranked_records.sort_by(|first, second| {
        first
            .0
            .cmp(&second.0)
            .then_with(|| first.1.sequence.cmp(&second.1.sequence))
    });
    let pilot_records = ranked_records
        .into_iter()
        .take(64)
        .map(|(_rank, record)| record)
        .collect::<Vec<_>>();
    ensure!(
        pilot_records.len() == 64,
        "mass-five pilot record census drift"
    );
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let priced = pool.install(|| {
        pilot_records
            .par_iter()
            .map(|record| hinge_coefficients(record, mass_five_directions))
            .collect::<Result<Vec<_>>>()
    })?;
    let mut matrix_digest = Sha256::new();
    let mut columns = Vec::with_capacity(pilot_records.len());
    let mut counts = Vec::with_capacity(pilot_records.len());
    for (record, values) in pilot_records.iter().zip(&priced) {
        let mut column_digest = Sha256::new();
        let mut maximum = 0i64;
        let mut nonzero = 0usize;
        for value in values {
            let bytes = value.to_le_bytes();
            matrix_digest.update(bytes);
            column_digest.update(bytes);
            maximum = maximum.max(*value);
            nonzero += usize::from(*value != 0);
        }
        counts.push(nonzero);
        columns.push(json!({
            "sequence": record.sequence,
            "active_vertices": record.active_vertices,
            "nonzero_directions": nonzero,
            "maximum_coefficient": maximum,
            "column_i64le_sha256": format!("{:x}", column_digest.finalize()),
        }));
    }
    let mut sorted_counts = counts.clone();
    sorted_counts.sort_unstable();
    let median_twice = sorted_counts[31] + sorted_counts[32];
    let zero_sequences = pilot_records
        .iter()
        .zip(&counts)
        .filter_map(|(record, count)| (*count == 0).then_some(record.sequence))
        .collect::<Vec<_>>();
    let result = if zero_sequences.is_empty() {
        "NO_ZERO_COLUMN_IN_HASH_RANKED_MASS5_DENSITY_PILOT"
    } else {
        "ZERO_COLUMN_FOUND_HASH_UNIFORM_FULL_RUN_BLOCKED"
    };
    ensure!(
        sha256_bytes(&records_bytes) == sha256_path(&records_path)?,
        "records changed during density pilot"
    );
    ensure!(
        sha256_bytes(&directions_bytes) == sha256_path(&directions_path)?,
        "directions changed during density pilot"
    );
    let receipt = json!({
        "schema": "g0179.mass5-density-pilot.v1",
        "result": result,
        "claim_boundary": "Density/support diagnostic on exactly 64 target-blind SHA-ranked mass-five STAR records and the initial 5,000 target-blind d[0]=1 mass-five directions. No full-family coverage or rank conclusion follows.",
        "launch_gate": {
            "full_hash_uniform_block_run_allowed_by_zero_column_check": zero_sequences.is_empty(),
            "rule": "Any zero pilot column blocks the full hash-uniform run and requires column-aware deterministic direction harvesting.",
        },
        "record_selection": {
            "domain_ascii_nul_terminated": String::from_utf8_lossy(&PILOT_DOMAIN[..PILOT_DOMAIN.len()-1]),
            "rule": "64 smallest SHA256(domain || sequence_u64le), tie by sequence",
            "available_mass5_records": records_by_mass[&5].len(),
            "selected_records": pilot_records.len(),
            "sequences": pilot_records.iter().map(|record| record.sequence).collect::<Vec<_>>(),
        },
        "directions": {
            "positive_mass": 5,
            "count": mass_five_directions.len(),
            "i8_c_sha256": direction_digest(mass_five_directions),
        },
        "density": {
            "minimum_nonzero_directions": sorted_counts[0],
            "median_nonzero_directions_numerator": median_twice,
            "median_nonzero_directions_denominator": 2,
            "maximum_nonzero_directions": sorted_counts[63],
            "zero_column_count": zero_sequences.len(),
            "zero_column_sequences": zero_sequences,
            "columns": columns,
        },
        "record_major_i64le_sha256": format!("{:x}", matrix_digest.finalize()),
        "bindings": {
            "records": records_path,
            "records_sha256": sha256_bytes(&records_bytes),
            "exclusive_directions": directions_path,
            "exclusive_directions_sha256": sha256_bytes(&directions_bytes),
            "source": source_bindings()?,
        },
        "threads": threads,
        "inputs_rehashed_at_end": true,
        "wall_seconds": started.elapsed().as_secs_f64(),
    });
    write_json_new(&output_path, &receipt)?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "result": result,
            "minimum": sorted_counts[0],
            "median_numerator": median_twice,
            "median_denominator": 2,
            "maximum": sorted_counts[63],
            "zero_columns": receipt["density"]["zero_column_count"],
            "output": output_path,
        }))?
    );
    Ok(())
}

fn probe(arguments: &[String]) -> Result<()> {
    ensure!(
        arguments.len() == 2,
        "usage: g0179-star-loop-pricer probe INPUT.json OUTPUT.json"
    );
    let input_path = PathBuf::from(&arguments[0]);
    let output_path = PathBuf::from(&arguments[1]);
    ensure!(!output_path.exists(), "refusing to overwrite probe output");
    let input_bytes = read(&input_path)?;
    let input: ProbeInput = serde_json::from_slice(&input_bytes)?;
    ensure!(
        input.schema == "max11-g0109-normal-form-input-v1",
        "probe schema drift"
    );
    ensure!(!input.records.is_empty(), "no probe records");
    let normal_forms = input
        .records
        .iter()
        .map(full_normal_form)
        .collect::<Result<Vec<NormalForm>>>()?;
    let output = json!({
        "schema": "g0179-loop-normal-form-probe-v1",
        "claim_boundary": "Exact normal forms for supplied probe records only.",
        "bindings": {
            "input": input_path,
            "input_sha256": sha256_bytes(&input_bytes),
            "source": source_bindings()?,
        },
        "normal_forms": normal_forms,
    });
    let mut writer = BufWriter::new(File::create_new(&output_path)?);
    serde_json::to_writer(&mut writer, &output)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    Ok(())
}

fn main() -> Result<()> {
    let arguments = std::env::args().skip(1).collect::<Vec<_>>();
    let (command, rest) = arguments
        .split_first()
        .context("expected price or probe subcommand")?;
    match command.as_str() {
        "price" => price(rest),
        "matched-price" => matched_price(rest),
        "exclusive-price" => exclusive_price(rest),
        "semantic-controls" => semantic_controls(rest),
        "density-pilot" => density_pilot(rest),
        "probe" => probe(rest),
        _ => anyhow::bail!(
            "unknown subcommand {command}; expected price, matched-price, exclusive-price, semantic-controls, density-pilot, or probe"
        ),
    }
}

#[cfg(test)]
mod binary_tests {
    use super::*;

    #[test]
    fn frozen_matched_square_inputs_and_exclusions_validate() {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let record_bytes = read(manifest_dir.join("star_outside_primary_records.json")).unwrap();
        let direction_bytes = read(manifest_dir.join("matching5771_directions.json")).unwrap();
        assert_eq!(sha256_bytes(&record_bytes), RECORD_FILE_SHA256);
        assert_eq!(
            sha256_bytes(&direction_bytes),
            MATCHING_DIRECTION_FILE_SHA256
        );
        let records: RecordsDocument = serde_json::from_slice(&record_bytes).unwrap();
        let directions: MatchingDirectionsDocument =
            serde_json::from_slice(&direction_bytes).unwrap();
        let retained = matched_records(&records.records).unwrap();
        let validated_directions = validate_matching_directions(&directions).unwrap();
        assert_eq!(retained.len(), 5_771);
        assert_eq!(validated_directions.len(), 5_771);
        assert!(!retained.iter().any(|record| record.sequence == 1_548));
        assert!(!retained.iter().any(|record| record.sequence == 4_259));
        assert_eq!(5_771usize * 5_771 * 8, 266_435_528);
    }
}
