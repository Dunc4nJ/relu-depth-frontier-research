use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const MAGIC_MCOLGEN: &[u8; 8] = b"MCOLGEN1";
const MAGIC_PROBLEM_I64: &[u8; 8] = b"ELIFTQ02";
const ALGORITHM: &str = "splitmix64-chain-v1-one-bucket-random-sign";

#[derive(Deserialize)]
struct PivotDocument {
    schema: String,
    input: String,
    input_sha256: String,
    n: usize,
    branch_edge_occurrences: usize,
    modulus: u32,
    sketches: Vec<PivotSketch>,
}

#[derive(Deserialize)]
struct PivotSketch {
    rank_a: usize,
    rank_augmented: usize,
    verdict: String,
    pivot_columns: Vec<u64>,
    pivot_columns_u64_le_sha256: String,
    pivot_buckets: Vec<u32>,
    target_sketch_nonzero: Vec<BucketResidue>,
    sketch: SketchSpec,
}

#[derive(Deserialize)]
struct SketchSpec {
    algorithm: String,
    seed: u64,
    buckets: usize,
}

#[derive(Deserialize)]
struct BucketResidue {
    bucket: u32,
    residue: u32,
}

#[derive(Serialize)]
struct BatchCustody {
    path: String,
    bytes: u64,
    records: u64,
    sha256: String,
}

#[derive(Serialize)]
pub struct BuildReport {
    schema: &'static str,
    verdict: &'static str,
    pivot_report: String,
    pivot_report_sha256: String,
    source_universe: String,
    source_universe_sha256: String,
    sketch_algorithm: String,
    sketch_seed: u64,
    sketch_buckets_denominator: usize,
    pivot_columns_numerator: usize,
    pivot_columns_denominator: usize,
    pivot_columns_u64_le_sha256: String,
    pivot_buckets_numerator: usize,
    pivot_buckets_denominator: usize,
    target_sketch_bucket: u32,
    target_sketch_residue_mod_report_prime: u32,
    report_prime: u32,
    exact_batches: Vec<BatchCustody>,
    exact_batch_records_numerator: usize,
    exact_batch_records_denominator: usize,
    union_hinge_rows_denominator: usize,
    linear_rows_denominator: usize,
    real_rows_denominator: usize,
    sketch_rows_denominator: usize,
    combined_rows_denominator: usize,
    real_csc_nonzeros_numerator: u64,
    sketch_minor_csc_nonzeros_numerator: u64,
    combined_csc_nonzeros_numerator: u64,
    sketch_entry_abs_max: u64,
    problem: String,
    problem_schema: &'static str,
    problem_bytes: u64,
    problem_sha256: String,
    build_seconds: f64,
    no_claim: &'static str,
}

struct HashingReader<R> {
    inner: R,
    digest: Sha256,
}

impl<R: Read> HashingReader<R> {
    fn new(inner: R) -> Self {
        Self {
            inner,
            digest: Sha256::new(),
        }
    }

    fn finish(self) -> String {
        format!("{:x}", self.digest.finalize())
    }
}

impl<R: Read> Read for HashingReader<R> {
    fn read(&mut self, buffer: &mut [u8]) -> std::io::Result<usize> {
        let count = self.inner.read(buffer)?;
        self.digest.update(&buffer[..count]);
        Ok(count)
    }
}

fn exact<const N: usize>(reader: &mut impl Read) -> Result<[u8; N], String> {
    let mut output = [0_u8; N];
    reader
        .read_exact(&mut output)
        .map_err(|error| error.to_string())?;
    Ok(output)
}

fn u16_le(reader: &mut impl Read) -> Result<u16, String> {
    Ok(u16::from_le_bytes(exact(reader)?))
}

fn u64_le(reader: &mut impl Read) -> Result<u64, String> {
    Ok(u64::from_le_bytes(exact(reader)?))
}

fn i16_le(reader: &mut impl Read) -> Result<i16, String> {
    Ok(i16::from_le_bytes(exact(reader)?))
}

fn i64_le(reader: &mut impl Read) -> Result<i64, String> {
    Ok(i64::from_le_bytes(exact(reader)?))
}

fn splitmix64(mut value: u64) -> u64 {
    value = value.wrapping_add(0x9e37_79b9_7f4a_7c15);
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

fn finish(state: u64, buckets: usize) -> (usize, i64) {
    let bucket_hash = splitmix64(state ^ 0xa076_1d64_78bd_642f);
    let sign_hash = splitmix64(state ^ 0xe703_7ed1_a0b4_28db);
    (
        (bucket_hash % buckets as u64) as usize,
        if sign_hash & 1 == 0 { 1 } else { -1 },
    )
}

fn linear_bucket(seed: u64, buckets: usize, n: usize, rank: usize) -> (usize, i64) {
    let state = splitmix64(
        seed ^ 0x6c69_6e65_6172_0001 ^ (n as u64).wrapping_mul(0x9e37_79b9) ^ rank as u64,
    );
    finish(state, buckets)
}

fn hinge_bucket(seed: u64, buckets: usize, direction: &[i16]) -> (usize, i64) {
    let mut state = splitmix64(
        seed ^ 0x6869_6e67_6500_0001 ^ (direction.len() as u64).wrapping_mul(0x9e37_79b9),
    );
    for (index, &coordinate) in direction.iter().enumerate() {
        state = splitmix64(
            state ^ coordinate as u16 as u64 ^ (index as u64).wrapping_mul(0xd6e8_feb8_6659_fd93),
        );
    }
    finish(state, buckets)
}

fn sha256_path(path: &Path) -> Result<String, String> {
    let mut source =
        BufReader::with_capacity(8 << 20, File::open(path).map_err(|e| e.to_string())?);
    let mut digest = Sha256::new();
    let mut buffer = vec![0_u8; 8 << 20];
    loop {
        let count = source.read(&mut buffer).map_err(|e| e.to_string())?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn sha256_u64_le(values: &[u64]) -> String {
    let mut digest = Sha256::new();
    for &value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn create_new(path: &Path) -> Result<File, String> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|error| format!("refusing to overwrite {}: {error}", path.display()))
}

fn write_u32(writer: &mut impl Write, value: u32) -> Result<(), String> {
    writer
        .write_all(&value.to_le_bytes())
        .map_err(|e| e.to_string())
}

fn write_u64(writer: &mut impl Write, value: u64) -> Result<(), String> {
    writer
        .write_all(&value.to_le_bytes())
        .map_err(|e| e.to_string())
}

fn write_i64(writer: &mut impl Write, value: i64) -> Result<(), String> {
    writer
        .write_all(&value.to_le_bytes())
        .map_err(|e| e.to_string())
}

fn batch_paths(directory: &Path) -> Result<Vec<PathBuf>, String> {
    let mut paths: Vec<_> = fs::read_dir(directory)
        .map_err(|e| e.to_string())?
        .map(|entry| entry.map(|item| item.path()).map_err(|e| e.to_string()))
        .collect::<Result<_, _>>()?;
    paths.retain(|path| {
        path.file_name()
            .and_then(|name| name.to_str())
            .is_some_and(|name| name.starts_with("batch-") && name.ends_with(".mcolgen1"))
    });
    paths.sort();
    if paths.is_empty() {
        return Err("batch directory contains no batch-*.mcolgen1 files".to_string());
    }
    Ok(paths)
}

fn add_sketch(
    values: &mut [i64],
    epochs: &mut [u32],
    touched: &mut Vec<usize>,
    epoch: u32,
    position: usize,
    summand: i64,
) -> Result<(), String> {
    if epochs[position] != epoch {
        epochs[position] = epoch;
        values[position] = 0;
        touched.push(position);
    }
    values[position] = values[position]
        .checked_add(summand)
        .ok_or_else(|| "exact sketch entry exceeds i64".to_string())?;
    Ok(())
}

pub fn build(
    pivot_report: &Path,
    sketch_index: usize,
    batch_directory: &Path,
    output: &Path,
    report_path: &Path,
) -> Result<BuildReport, String> {
    let started = Instant::now();
    let pivot_sha = sha256_path(pivot_report)?;
    let document: PivotDocument = serde_json::from_reader(BufReader::new(
        File::open(pivot_report).map_err(|e| e.to_string())?,
    ))
    .map_err(|e| e.to_string())?;
    if document.schema != "max11-streamrank-pivots-v1" {
        return Err("unsupported pivot schema".to_string());
    }
    let record = document
        .sketches
        .get(sketch_index)
        .ok_or_else(|| "sketch index out of range".to_string())?;
    if record.verdict != "MEMBER" || record.rank_a != record.rank_augmented {
        return Err("sketch-member construction requires equal-rank MEMBER".to_string());
    }
    let rank = record.rank_a;
    if record.pivot_columns.len() != rank || record.pivot_buckets.len() != rank {
        return Err("pivot column/bucket counts do not equal rank".to_string());
    }
    if sha256_u64_le(&record.pivot_columns) != record.pivot_columns_u64_le_sha256 {
        return Err("pivot column SHA-256 mismatch".to_string());
    }
    if record.sketch.algorithm != ALGORITHM {
        return Err("unsupported sketch algorithm".to_string());
    }
    if record
        .pivot_buckets
        .iter()
        .any(|&bucket| bucket as usize >= record.sketch.buckets)
        || record
            .pivot_buckets
            .iter()
            .copied()
            .collect::<HashSet<_>>()
            .len()
            != rank
    {
        return Err("pivot buckets are repeated or out of range".to_string());
    }
    let pivot_bucket_position: HashMap<u32, usize> = record
        .pivot_buckets
        .iter()
        .enumerate()
        .map(|(position, &bucket)| (bucket, position))
        .collect();
    let (target_bucket, target_sign) = linear_bucket(
        record.sketch.seed,
        record.sketch.buckets,
        document.n,
        document.n - 1,
    );
    let target_residue = target_sign.rem_euclid(document.modulus as i64) as u32;
    if record.target_sketch_nonzero.len() != 1
        || record.target_sketch_nonzero[0].bucket as usize != target_bucket
        || record.target_sketch_nonzero[0].residue != target_residue
    {
        return Err("exact target sketch does not reproduce pivot report".to_string());
    }
    let target_position = *pivot_bucket_position
        .get(&(target_bucket as u32))
        .ok_or_else(|| "MEMBER pivot buckets omit the nonzero target bucket".to_string())?;

    let row_spool_path = output.with_extension("rows.tmp");
    let value_spool_path = output.with_extension("values.tmp");
    let mut row_spool = BufWriter::with_capacity(16 << 20, create_new(&row_spool_path)?);
    let mut value_spool = BufWriter::with_capacity(16 << 20, create_new(&value_spool_path)?);
    let mut offsets = Vec::with_capacity(rank + 1);
    offsets.push(0_u64);
    let mut union_hinges: HashMap<Vec<i16>, u32> = HashMap::new();
    let mut source_indices = Vec::with_capacity(rank);
    let mut sketch_values = vec![0_i64; rank];
    let mut sketch_epochs = vec![0_u32; rank];
    let mut touched = Vec::with_capacity(rank);
    let mut exact_batches = Vec::new();
    let mut real_nnz = 0_u64;
    let mut sketch_nnz = 0_u64;
    let mut sketch_abs_max = 0_u64;
    let mut column_position = 0_usize;

    for batch_path in batch_paths(batch_directory)? {
        let bytes = batch_path.metadata().map_err(|e| e.to_string())?.len();
        let hashing = HashingReader::new(File::open(&batch_path).map_err(|e| e.to_string())?);
        let mut reader = BufReader::with_capacity(16 << 20, hashing);
        if &exact::<8>(&mut reader)? != MAGIC_MCOLGEN {
            return Err(format!(
                "{} has invalid MCOLGEN1 magic",
                batch_path.display()
            ));
        }
        let n = u16_le(&mut reader)? as usize;
        let branch_edges = u16_le(&mut reader)? as usize;
        let modulus = u64_le(&mut reader)?;
        let count = u64_le(&mut reader)?;
        if (n, branch_edges, modulus) != (document.n, document.branch_edge_occurrences, 0) {
            return Err(format!(
                "{} has incompatible dimensions/modulus",
                batch_path.display()
            ));
        }
        for _ in 0..count {
            if column_position >= rank {
                return Err("exact batches contain more records than pivots".to_string());
            }
            let source_index = u64_le(&mut reader)?;
            if source_index != record.pivot_columns[column_position] {
                return Err(format!(
                    "pivot order mismatch at column {column_position}: {source_index} != {}",
                    record.pivot_columns[column_position]
                ));
            }
            source_indices.push(source_index);
            touched.clear();
            let epoch = u32::try_from(column_position + 1).map_err(|e| e.to_string())?;
            let mut real_entries: Vec<(u32, i64)> = Vec::new();
            for linear_rank in 0..n {
                let coefficient = i64_le(&mut reader)?;
                if coefficient == 0 {
                    continue;
                }
                let (bucket, sign) =
                    linear_bucket(record.sketch.seed, record.sketch.buckets, n, linear_rank);
                if let Some(&position) = pivot_bucket_position.get(&(bucket as u32)) {
                    add_sketch(
                        &mut sketch_values,
                        &mut sketch_epochs,
                        &mut touched,
                        epoch,
                        position,
                        coefficient
                            .checked_mul(sign)
                            .ok_or("linear sketch overflow")?,
                    )?;
                }
                real_entries.push((
                    u32::try_from(rank + linear_rank).map_err(|e| e.to_string())?,
                    coefficient,
                ));
            }
            let hinge_count = u64_le(&mut reader)?;
            real_entries.reserve(usize::try_from(hinge_count).map_err(|e| e.to_string())?);
            for _ in 0..hinge_count {
                let mut direction = Vec::with_capacity(n);
                for _ in 0..n {
                    direction.push(i16_le(&mut reader)?);
                }
                let coefficient = i64_le(&mut reader)?;
                if coefficient == 0 {
                    continue;
                }
                let (bucket, sign) =
                    hinge_bucket(record.sketch.seed, record.sketch.buckets, &direction);
                if let Some(&position) = pivot_bucket_position.get(&(bucket as u32)) {
                    add_sketch(
                        &mut sketch_values,
                        &mut sketch_epochs,
                        &mut touched,
                        epoch,
                        position,
                        coefficient
                            .checked_mul(sign)
                            .ok_or("hinge sketch overflow")?,
                    )?;
                }
                let next_hinge = u32::try_from(union_hinges.len()).map_err(|e| e.to_string())?;
                let hinge_id = *union_hinges.entry(direction).or_insert(next_hinge);
                let row = u32::try_from(rank + n)
                    .map_err(|e| e.to_string())?
                    .checked_add(hinge_id)
                    .ok_or("real row index overflow")?;
                real_entries.push((row, coefficient));
            }
            touched.sort_unstable();
            let mut column_nnz = 0_u64;
            for &position in &touched {
                let value = sketch_values[position];
                if value == 0 {
                    continue;
                }
                write_u32(&mut row_spool, position as u32)?;
                write_i64(&mut value_spool, value)?;
                sketch_nnz += 1;
                column_nnz += 1;
                sketch_abs_max = sketch_abs_max.max(value.unsigned_abs());
            }
            for (row, value) in real_entries {
                write_u32(&mut row_spool, row)?;
                write_i64(&mut value_spool, value)?;
                real_nnz += 1;
                column_nnz += 1;
            }
            offsets.push(offsets.last().copied().unwrap() + column_nnz);
            column_position += 1;
            if column_position % 256 == 0 || column_position == rank {
                eprintln!(
                    "SKETCH_MEMBER_BUILD columns={column_position}/{rank} hinges={} nnz={} seconds={:.3}",
                    union_hinges.len(),
                    offsets.last().unwrap(),
                    started.elapsed().as_secs_f64()
                );
            }
        }
        let mut trailing = [0_u8; 1];
        if reader.read(&mut trailing).map_err(|e| e.to_string())? != 0 {
            return Err(format!("{} has trailing bytes", batch_path.display()));
        }
        let digest = reader.into_inner().finish();
        exact_batches.push(BatchCustody {
            path: batch_path.display().to_string(),
            bytes,
            records: count,
            sha256: digest,
        });
    }
    if column_position != rank {
        return Err(format!(
            "exact batches contain {column_position}/{rank} pivot records"
        ));
    }
    row_spool.flush().map_err(|e| e.to_string())?;
    value_spool.flush().map_err(|e| e.to_string())?;
    drop(row_spool);
    drop(value_spool);

    let real_rows = union_hinges.len() + document.n;
    let rows = rank
        .checked_add(real_rows)
        .ok_or("combined row count overflow")?;
    let nnz = *offsets.last().unwrap();
    let mut writer = BufWriter::with_capacity(16 << 20, create_new(output)?);
    writer
        .write_all(MAGIC_PROBLEM_I64)
        .map_err(|e| e.to_string())?;
    write_u32(&mut writer, u32::try_from(rows).map_err(|e| e.to_string())?)?;
    write_u32(&mut writer, u32::try_from(rank).map_err(|e| e.to_string())?)?;
    write_u32(&mut writer, u32::try_from(rank).map_err(|e| e.to_string())?)?;
    write_u64(&mut writer, nnz)?;
    for &offset in &offsets {
        write_u64(&mut writer, offset)?;
    }
    std::io::copy(
        &mut BufReader::with_capacity(
            16 << 20,
            File::open(&row_spool_path).map_err(|e| e.to_string())?,
        ),
        &mut writer,
    )
    .map_err(|e| e.to_string())?;
    std::io::copy(
        &mut BufReader::with_capacity(
            16 << 20,
            File::open(&value_spool_path).map_err(|e| e.to_string())?,
        ),
        &mut writer,
    )
    .map_err(|e| e.to_string())?;
    for row in 0..rank {
        write_u32(&mut writer, row as u32)?;
    }
    for row in 0..rows {
        let value = if row == target_position {
            target_sign
        } else if row == rank + document.n - 1 {
            1
        } else {
            0
        };
        write_i64(&mut writer, value)?;
    }
    for &source_index in &source_indices {
        write_u64(&mut writer, source_index)?;
    }
    writer.flush().map_err(|e| e.to_string())?;
    drop(writer);
    fs::remove_file(&row_spool_path).map_err(|e| e.to_string())?;
    fs::remove_file(&value_spool_path).map_err(|e| e.to_string())?;

    let problem_bytes = output.metadata().map_err(|e| e.to_string())?.len();
    let problem_sha = sha256_path(output)?;
    let report = BuildReport {
        schema: "max11-sketch-member-problem-v1",
        verdict: "PASS",
        pivot_report: pivot_report.display().to_string(),
        pivot_report_sha256: pivot_sha,
        source_universe: document.input,
        source_universe_sha256: document.input_sha256,
        sketch_algorithm: record.sketch.algorithm.clone(),
        sketch_seed: record.sketch.seed,
        sketch_buckets_denominator: record.sketch.buckets,
        pivot_columns_numerator: rank,
        pivot_columns_denominator: rank,
        pivot_columns_u64_le_sha256: record.pivot_columns_u64_le_sha256.clone(),
        pivot_buckets_numerator: rank,
        pivot_buckets_denominator: rank,
        target_sketch_bucket: target_bucket as u32,
        target_sketch_residue_mod_report_prime: target_residue,
        report_prime: document.modulus,
        exact_batch_records_numerator: column_position,
        exact_batch_records_denominator: rank,
        exact_batches,
        union_hinge_rows_denominator: union_hinges.len(),
        linear_rows_denominator: document.n,
        real_rows_denominator: real_rows,
        sketch_rows_denominator: rank,
        combined_rows_denominator: rows,
        real_csc_nonzeros_numerator: real_nnz,
        sketch_minor_csc_nonzeros_numerator: sketch_nnz,
        combined_csc_nonzeros_numerator: nnz,
        sketch_entry_abs_max: sketch_abs_max,
        problem: output.display().to_string(),
        problem_schema: "ELIFTQ02",
        problem_bytes,
        problem_sha256: problem_sha,
        build_seconds: started.elapsed().as_secs_f64(),
        no_claim: "This only constructs the exact named sketch minor plus all support-union verification rows; it is not an identity until the exact rational solver verifies every combined row.",
    };
    let mut report_writer = BufWriter::new(create_new(report_path)?);
    serde_json::to_writer_pretty(&mut report_writer, &report).map_err(|e| e.to_string())?;
    report_writer.write_all(b"\n").map_err(|e| e.to_string())?;
    report_writer.flush().map_err(|e| e.to_string())?;
    Ok(report)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sketch_hash_known_answers_match_python_replay() {
        assert_eq!(linear_bucket(2026090201, 64000, 11, 10), (47568, -1));
        assert_eq!(hinge_bucket(2026090201, 64000, &[1, -1, 0]), (3184, -1));
    }
}
