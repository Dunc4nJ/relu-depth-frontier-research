use anyhow::{Context, Result, ensure};
use bytemuck::try_cast_slice;
use memmap2::{Mmap, MmapOptions};
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const ALGORITHM: &str = "splitmix64-index-v1-one-bucket-random-sign";

fn arg(args: &[String], name: &str) -> Result<String> {
    let position = args
        .iter()
        .position(|item| item == name)
        .with_context(|| format!("missing {name}"))?;
    args.get(position + 1)
        .cloned()
        .with_context(|| format!("missing value for {name}"))
}

fn splitmix64(mut value: u64) -> u64 {
    value = value.wrapping_add(0x9e37_79b9_7f4a_7c15);
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

fn row_bucket(seed: u64, buckets: usize, row: u32) -> (usize, i64) {
    let state = splitmix64(seed ^ 0x7365_636f_6e64_0001 ^ row as u64);
    let bucket_hash = splitmix64(state ^ 0xa076_1d64_78bd_642f);
    let sign_hash = splitmix64(state ^ 0xe703_7ed1_a0b4_28db);
    (
        (bucket_hash % buckets as u64) as usize,
        if sign_hash & 1 == 0 { 1 } else { -1 },
    )
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut reader = BufReader::with_capacity(8 << 20, File::open(path)?);
    let mut digest = Sha256::new();
    let mut buffer = vec![0u8; 8 << 20];
    loop {
        let count = reader.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn create_new(path: &Path) -> Result<File> {
    Ok(OpenOptions::new().write(true).create_new(true).open(path)?)
}

fn mmap(path: &Path) -> Result<Mmap> {
    // SAFETY: the input matrices are immutable for the lifetime of this process.
    Ok(unsafe { MmapOptions::new().map(&File::open(path)?)? })
}

fn file_path(input: &Path, files: &serde_json::Map<String, Value>, name: &str) -> Result<PathBuf> {
    let record = files
        .get(name)
        .with_context(|| format!("missing file record {name}"))?;
    let relative = record["path"]
        .as_str()
        .with_context(|| format!("bad path for {name}"))?;
    let path = input.join(relative);
    ensure!(
        path.metadata()?.len() == record["bytes"].as_u64().context("bad byte count")?,
        "{name} byte mismatch"
    );
    ensure!(
        sha256_path(&path)? == record["sha256"].as_str().context("bad SHA")?,
        "{name} SHA mismatch"
    );
    Ok(path)
}

fn write_u32(writer: &mut impl Write, value: u32) -> Result<()> {
    writer.write_all(&value.to_le_bytes())?;
    Ok(())
}
fn write_u64(writer: &mut impl Write, value: u64) -> Result<()> {
    writer.write_all(&value.to_le_bytes())?;
    Ok(())
}
fn write_i64(writer: &mut impl Write, value: i64) -> Result<()> {
    writer.write_all(&value.to_le_bytes())?;
    Ok(())
}

fn max_rss_kib() -> Option<u64> {
    fs::read_to_string("/proc/self/status")
        .ok()?
        .lines()
        .find_map(|line| {
            line.strip_prefix("VmHWM:")?
                .split_whitespace()
                .next()?
                .parse()
                .ok()
        })
}

struct Column {
    entries: Vec<(u32, i64)>,
}

fn main() -> Result<()> {
    ensure!(
        cfg!(target_endian = "little"),
        "binary matrices require a little-endian host"
    );
    let args: Vec<String> = env::args().collect();
    let input = PathBuf::from(arg(&args, "--input-dir")?);
    let output = PathBuf::from(arg(&args, "--output-dir")?);
    let seed: u64 = arg(&args, "--seed")?.parse()?;
    let buckets: usize = arg(&args, "--buckets")?.parse()?;
    let threads: usize = arg(&args, "--threads")?.parse()?;
    ensure!(
        buckets > 0 && buckets <= u32::MAX as usize,
        "bad bucket count"
    );
    ensure!(threads > 0 && threads <= 16, "threads must be 1..=16");
    ensure!(
        !output.exists(),
        "refusing to overwrite {}",
        output.display()
    );
    fs::create_dir_all(&output)?;
    let started = Instant::now();

    let report_path = input.join("matrix.json");
    let report: Value = serde_json::from_reader(BufReader::new(File::open(&report_path)?))?;
    ensure!(report["verdict"] == "PASS", "input report is not PASS");
    let rows = report["rows_denominator"]
        .as_u64()
        .context("missing rows")? as usize;
    let columns = report["columns_denominator"]
        .as_u64()
        .context("missing columns")? as usize;
    let input_nnz = report["nonzeros_denominator"]
        .as_u64()
        .context("missing nnz")? as usize;
    let files = report["files"].as_object().context("missing files")?;
    let paths: HashMap<&str, PathBuf> = ["start", "index", "value", "source", "target"]
        .into_iter()
        .map(|name| Ok((name, file_path(&input, files, name)?)))
        .collect::<Result<_>>()?;
    let start_map = mmap(&paths["start"])?;
    let index_map = mmap(&paths["index"])?;
    let value_map = mmap(&paths["value"])?;
    let source_map = mmap(&paths["source"])?;
    let target_map = mmap(&paths["target"])?;
    let starts: &[u64] = try_cast_slice(&start_map[..])
        .map_err(|error| anyhow::anyhow!("unaligned start array: {error:?}"))?;
    let indices: &[u32] = try_cast_slice(&index_map[..])
        .map_err(|error| anyhow::anyhow!("unaligned index array: {error:?}"))?;
    let values: &[i64] = try_cast_slice(&value_map[..])
        .map_err(|error| anyhow::anyhow!("unaligned value array: {error:?}"))?;
    let sources: &[u64] = try_cast_slice(&source_map[..])
        .map_err(|error| anyhow::anyhow!("unaligned source array: {error:?}"))?;
    let target: &[i64] = try_cast_slice(&target_map[..])
        .map_err(|error| anyhow::anyhow!("unaligned target array: {error:?}"))?;
    ensure!(
        starts.len() == columns + 1 && starts[columns] as usize == input_nnz,
        "bad starts"
    );
    ensure!(
        indices.len() == input_nnz && values.len() == input_nnz,
        "bad entries"
    );
    ensure!(
        sources.len() == columns && target.len() == rows,
        "bad source/target arrays"
    );
    ensure!(
        indices.iter().all(|&row| (row as usize) < rows),
        "row index out of bounds"
    );

    let row_map: Vec<(usize, i64)> = (0..rows)
        .map(|row| row_bucket(seed, buckets, row as u32))
        .collect();
    let mut sketched_target = vec![0i64; buckets];
    for (row, &coefficient) in target.iter().enumerate() {
        let (bucket, sign) = row_map[row];
        sketched_target[bucket] = sketched_target[bucket]
            .checked_add(
                coefficient
                    .checked_mul(sign)
                    .context("target product overflow")?,
            )
            .context("target sum overflow")?;
    }

    let index_path = output.join("index.u32le");
    let value_path = output.join("value.i64le");
    let mut index_writer = BufWriter::with_capacity(16 << 20, create_new(&index_path)?);
    let mut value_writer = BufWriter::with_capacity(16 << 20, create_new(&value_path)?);
    let mut output_starts = Vec::with_capacity(columns + 1);
    output_starts.push(0u64);
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let batch_size = threads * 4;
    for begin_column in (0..columns).step_by(batch_size) {
        let end_column = (begin_column + batch_size).min(columns);
        let batch: Vec<Result<Column>> = pool.install(|| {
            (begin_column..end_column)
                .into_par_iter()
                .map(|column| {
                    let mut accumulated = vec![0i64; buckets];
                    let begin = starts[column] as usize;
                    let end = starts[column + 1] as usize;
                    for cursor in begin..end {
                        let (bucket, sign) = row_map[indices[cursor] as usize];
                        accumulated[bucket] = accumulated[bucket]
                            .checked_add(
                                values[cursor]
                                    .checked_mul(sign)
                                    .context("entry product overflow")?,
                            )
                            .context("entry sum overflow")?;
                    }
                    Ok(Column {
                        entries: accumulated
                            .into_iter()
                            .enumerate()
                            .filter_map(|(row, value)| (value != 0).then_some((row as u32, value)))
                            .collect(),
                    })
                })
                .collect()
        });
        for column in batch {
            let column = column?;
            for (row, value) in &column.entries {
                write_u32(&mut index_writer, *row)?;
                write_i64(&mut value_writer, *value)?;
            }
            output_starts
                .push(output_starts.last().copied().unwrap() + column.entries.len() as u64);
        }
        if end_column % 1024 < batch_size || end_column == columns {
            eprintln!(
                "DOWNSKETCH columns={end_column}/{columns} nnz={} seconds={:.3}",
                output_starts.last().unwrap(),
                started.elapsed().as_secs_f64()
            );
        }
    }
    index_writer.flush()?;
    value_writer.flush()?;
    drop(index_writer);
    drop(value_writer);

    let start_path = output.join("start.u64le");
    let source_path = output.join("source.u64le");
    let target_path = output.join("target.i64le");
    let mut writer = BufWriter::new(create_new(&start_path)?);
    for &value in &output_starts {
        write_u64(&mut writer, value)?;
    }
    writer.flush()?;
    let mut writer = BufWriter::new(create_new(&source_path)?);
    for &value in sources {
        write_u64(&mut writer, value)?;
    }
    writer.flush()?;
    let mut writer = BufWriter::new(create_new(&target_path)?);
    for &value in &sketched_target {
        write_i64(&mut writer, value)?;
    }
    writer.flush()?;

    let mut output_files = serde_json::Map::new();
    for (name, path) in [
        ("start", &start_path),
        ("index", &index_path),
        ("value", &value_path),
        ("source", &source_path),
        ("target", &target_path),
    ] {
        output_files.insert(
            name.to_string(),
            json!({
                "path": path.file_name().unwrap().to_string_lossy(),
                "bytes": path.metadata()?.len(),
                "sha256": sha256_path(path)?,
            }),
        );
    }
    let output_nnz = *output_starts.last().unwrap();
    let output_report = json!({
        "schema": "max11-sparse-lp-csc-v1",
        "verdict": "PASS",
        "method": "exact secondary CountSketch of every row in the checked input CSC",
        "system": report.get("system"),
        "system_sha256": report.get("system_sha256"),
        "n": report.get("n"),
        "input_matrix_report": report_path,
        "input_matrix_report_sha256": sha256_path(&report_path)?,
        "rows_numerator": buckets,
        "rows_denominator": buckets,
        "columns_numerator": columns,
        "columns_denominator": columns,
        "nonzeros_numerator": output_nnz,
        "nonzeros_denominator": output_nnz,
        "input_nonzeros_visited_numerator": input_nnz,
        "input_nonzeros_visited_denominator": input_nnz,
        "secondary_sketch_algorithm": ALGORITHM,
        "secondary_sketch_seed": seed,
        "files": output_files,
        "build_seconds": started.elapsed().as_secs_f64(),
        "max_rss_kib": max_rss_kib(),
        "no_claim": "This exact secondary sketch is an LP search system. Any candidate must pass the full primary sketch, exact rational lift, and every-real-row verification."
    });
    fs::write(
        output.join("matrix.json"),
        serde_json::to_string_pretty(&output_report)? + "\n",
    )?;
    println!("{}", serde_json::to_string_pretty(&output_report)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn secondary_hash_known_answers() {
        assert_eq!(row_bucket(2026090301, 1024, 0), (53, 1));
        assert_eq!(row_bucket(2026090301, 1024, 15_903), (844, -1));
    }
}
