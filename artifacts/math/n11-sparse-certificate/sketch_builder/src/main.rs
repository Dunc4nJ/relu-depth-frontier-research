use anyhow::{Context, Result, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{SparseColumn, Universe, generate_column};
use rayon::prelude::*;
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const ALGORITHM: &str = "splitmix64-chain-v1-one-bucket-random-sign";

fn arg(args: &[String], name: &str) -> Result<String> {
    let position = args.iter().position(|item| item == name).with_context(|| format!("missing {name}"))?;
    args.get(position + 1).cloned().with_context(|| format!("missing value for {name}"))
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
    ((bucket_hash % buckets as u64) as usize, if sign_hash & 1 == 0 { 1 } else { -1 })
}

fn linear_bucket(seed: u64, buckets: usize, n: usize, rank: usize) -> (usize, i64) {
    let state = splitmix64(seed ^ 0x6c69_6e65_6172_0001 ^ (n as u64).wrapping_mul(0x9e37_79b9) ^ rank as u64);
    finish(state, buckets)
}

fn hinge_bucket(seed: u64, buckets: usize, direction: &[i16]) -> (usize, i64) {
    let mut state = splitmix64(seed ^ 0x6869_6e67_6500_0001 ^ (direction.len() as u64).wrapping_mul(0x9e37_79b9));
    for (index, &coordinate) in direction.iter().enumerate() {
        state = splitmix64(state ^ coordinate as u16 as u64 ^ (index as u64).wrapping_mul(0xd6e8_feb8_6659_fd93));
    }
    finish(state, buckets)
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut reader = BufReader::with_capacity(8 << 20, File::open(path)?);
    let mut digest = Sha256::new();
    let mut buffer = vec![0u8; 8 << 20];
    loop {
        let count = reader.read(&mut buffer)?;
        if count == 0 { break; }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn load_json(path: &Path) -> Result<Value> {
    let file = File::open(path)?;
    let reader: Box<dyn Read> = if path.extension().is_some_and(|x| x == "gz") {
        Box::new(GzDecoder::new(file))
    } else {
        Box::new(file)
    };
    Ok(serde_json::from_reader(BufReader::new(reader))?)
}

fn load_universe(path: &Path) -> Result<Universe> {
    Ok(serde_json::from_value(load_json(path)?)?)
}

fn create_new(path: &Path) -> Result<File> {
    Ok(OpenOptions::new().write(true).create_new(true).open(path)?)
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
    fs::read_to_string("/proc/self/status").ok()?.lines().find_map(|line| {
        line.strip_prefix("VmHWM:")?.split_whitespace().next()?.parse().ok()
    })
}

struct Sketched {
    source: u64,
    entries: Vec<(u32, i64)>,
    real_nnz: u64,
}

fn sketch_column(
    source: usize,
    column: SparseColumn,
    seed: u64,
    buckets: usize,
    positions: &[i32],
) -> Result<Sketched> {
    let rows = positions.iter().filter(|&&x| x >= 0).count();
    let mut values = vec![0i64; rows];
    let mut seen = vec![false; rows];
    let mut touched = Vec::new();
    let mut real_nnz = 0u64;
    let mut add = |bucket: usize, sign: i64, coefficient: i64| -> Result<()> {
        if coefficient == 0 { return Ok(()); }
        real_nnz += 1;
        let position = positions[bucket];
        if position < 0 { return Ok(()); }
        let position = position as usize;
        if !seen[position] {
            seen[position] = true;
            touched.push(position);
        }
        values[position] = values[position]
            .checked_add(coefficient.checked_mul(sign).context("sketch product overflow")?)
            .context("sketch sum overflow")?;
        Ok(())
    };
    for (rank, &coefficient) in column.linear.iter().enumerate() {
        let (bucket, sign) = linear_bucket(seed, buckets, column.linear.len(), rank);
        add(bucket, sign, coefficient)?;
    }
    for (direction, &coefficient) in &column.hinges {
        let (bucket, sign) = hinge_bucket(seed, buckets, direction);
        add(bucket, sign, coefficient)?;
    }
    touched.sort_unstable();
    let entries = touched.into_iter().filter_map(|position| {
        let value = values[position];
        (value != 0).then_some((position as u32, value))
    }).collect();
    Ok(Sketched { source: source as u64, entries, real_nnz })
}

fn main() -> Result<()> {
    let args: Vec<String> = env::args().collect();
    let universe_path = PathBuf::from(arg(&args, "--universe")?);
    let order_path = PathBuf::from(arg(&args, "--order-file")?);
    let pivot_path = PathBuf::from(arg(&args, "--pivot-report")?);
    let output = PathBuf::from(arg(&args, "--output-dir")?);
    let threads: usize = arg(&args, "--threads")?.parse()?;
    let include_five_l = arg(&args, "--include-five-l")?.parse::<bool>()?;
    ensure!(threads > 0 && threads <= 16, "threads must be 1..=16");
    ensure!(!output.exists(), "refusing to overwrite {}", output.display());
    fs::create_dir_all(&output)?;
    let started = Instant::now();

    let universe = load_universe(&universe_path)?;
    let order: Vec<usize> = serde_json::from_value(load_json(&order_path)?)?;
    ensure!(!order.is_empty(), "empty order");
    ensure!(order.iter().all(|&i| i < universe.records.len()), "order index out of range");
    ensure!(order.iter().copied().collect::<HashSet<_>>().len() == order.len(), "duplicate order index");
    let pivot = load_json(&pivot_path)?;
    ensure!(pivot["schema"] == "max11-streamrank-pivots-v1", "bad pivot schema");
    ensure!(pivot["input_sha256"].as_str() == Some(&sha256_path(&universe_path)?), "universe SHA mismatch");
    ensure!(pivot["order_file_sha256"].as_str() == Some(&sha256_path(&order_path)?), "order SHA mismatch");
    ensure!(pivot["n"].as_u64() == Some(universe.n as u64), "n mismatch");
    ensure!(pivot["branch_edge_occurrences"].as_u64() == Some(universe.branch_edge_occurrences as u64), "branch size mismatch");
    let sketch = &pivot["sketches"][0];
    ensure!(sketch["verdict"] == "MEMBER", "pivot sketch is not MEMBER");
    ensure!(sketch["rank_a"] == sketch["rank_augmented"], "pivot ranks differ");
    let spec = &sketch["sketch"];
    ensure!(spec["algorithm"] == ALGORITHM, "unsupported sketch algorithm");
    let seed = spec["seed"].as_u64().context("missing seed")?;
    let buckets = spec["buckets"].as_u64().context("missing buckets")? as usize;
    let pivot_buckets: Vec<u32> = serde_json::from_value(sketch["pivot_buckets"].clone())?;
    let rows = pivot_buckets.len();
    ensure!(rows == sketch["rank_a"].as_u64().context("missing rank")? as usize, "pivot bucket/rank mismatch");
    ensure!(pivot_buckets.iter().copied().collect::<HashSet<_>>().len() == rows, "duplicate pivot buckets");
    let mut positions = vec![-1i32; buckets];
    for (position, &bucket) in pivot_buckets.iter().enumerate() {
        ensure!((bucket as usize) < buckets, "pivot bucket out of range");
        positions[bucket as usize] = position as i32;
    }
    let (target_bucket, target_sign) = linear_bucket(seed, buckets, universe.n, universe.n - 1);
    let target_position = positions[target_bucket];
    ensure!(target_position >= 0, "pivot buckets omit target bucket");
    let expected_target = sketch["target_sketch_nonzero"].as_array().context("missing target")?;
    let report_prime = pivot["modulus"].as_u64().context("missing modulus")?;
    ensure!(expected_target.len() == 1, "target sketch is not one-sparse");
    ensure!(expected_target[0]["bucket"].as_u64() == Some(target_bucket as u64), "target bucket mismatch");
    ensure!(expected_target[0]["residue"].as_u64() == Some(target_sign.rem_euclid(report_prime as i64) as u64), "target residue mismatch");

    let index_path = output.join("index.u32le");
    let value_path = output.join("value.i64le");
    let mut index_writer = BufWriter::with_capacity(16 << 20, create_new(&index_path)?);
    let mut value_writer = BufWriter::with_capacity(16 << 20, create_new(&value_path)?);
    let mut starts = Vec::with_capacity(order.len() + usize::from(include_five_l) + 1);
    let mut sources = Vec::with_capacity(order.len() + usize::from(include_five_l));
    starts.push(0u64);
    let pool = rayon::ThreadPoolBuilder::new().num_threads(threads).build()?;
    let batch_size = threads * 2;
    let mut real_nnz = 0u64;
    let mut sketch_abs_max = 0u64;
    for begin in (0..order.len()).step_by(batch_size) {
        let end = (begin + batch_size).min(order.len());
        let batch: Vec<Result<Sketched>> = pool.install(|| order[begin..end].par_iter().map(|&source| {
            let column = generate_column(&universe.records[source], universe.n, universe.branch_edge_occurrences)
                .with_context(|| format!("generate source {source}"))?;
            sketch_column(source, column, seed, buckets, &positions)
        }).collect());
        for result in batch {
            let column = result?;
            for (row, value) in &column.entries {
                write_u32(&mut index_writer, *row)?;
                write_i64(&mut value_writer, *value)?;
                sketch_abs_max = sketch_abs_max.max(value.unsigned_abs());
            }
            real_nnz += column.real_nnz;
            sources.push(column.source);
            starts.push(starts.last().copied().unwrap() + column.entries.len() as u64);
        }
        if end % 1024 < batch_size || end == order.len() {
            eprintln!("SPARSE_SKETCH columns={}/{} nnz={} real_nnz={} seconds={:.3}", end, order.len() + usize::from(include_five_l), starts.last().unwrap(), real_nnz, started.elapsed().as_secs_f64());
        }
    }
    if include_five_l {
        ensure!(universe.branch_edge_occurrences == 5, "5L requires branch size five");
        let coefficient = 5i64 * (1..universe.n as i64).product::<i64>();
        let column = SparseColumn { linear: vec![coefficient; universe.n], hinges: Default::default() };
        let sketched = sketch_column(universe.records.len(), column, seed, buckets, &positions)?;
        for (row, value) in &sketched.entries {
            write_u32(&mut index_writer, *row)?;
            write_i64(&mut value_writer, *value)?;
            sketch_abs_max = sketch_abs_max.max(value.unsigned_abs());
        }
        real_nnz += sketched.real_nnz;
        sources.push(sketched.source);
        starts.push(starts.last().copied().unwrap() + sketched.entries.len() as u64);
    }
    index_writer.flush()?;
    value_writer.flush()?;
    drop(index_writer);
    drop(value_writer);
    let columns = sources.len();
    let expected_columns = pivot["source_columns_denominator"].as_u64().context("missing source denominator")? as usize;
    ensure!(columns == expected_columns, "built {columns}/{expected_columns} columns");
    let expected_real_nnz = pivot["exact_real_nnz_numerator"].as_u64().context("missing exact nnz")?;
    ensure!(real_nnz == expected_real_nnz, "real nnz {real_nnz}/{expected_real_nnz}");

    let start_path = output.join("start.u64le");
    let source_path = output.join("source.u64le");
    let target_path = output.join("target.i64le");
    let mut writer = BufWriter::new(create_new(&start_path)?);
    for value in &starts { write_u64(&mut writer, *value)?; }
    writer.flush()?;
    let mut writer = BufWriter::new(create_new(&source_path)?);
    for value in &sources { write_u64(&mut writer, *value)?; }
    writer.flush()?;
    let mut writer = BufWriter::new(create_new(&target_path)?);
    for row in 0..rows { write_i64(&mut writer, if row == target_position as usize { target_sign } else { 0 })?; }
    writer.flush()?;

    let mut files = serde_json::Map::new();
    for (name, path) in [("start", &start_path), ("index", &index_path), ("value", &value_path), ("source", &source_path), ("target", &target_path)] {
        files.insert(name.to_string(), json!({"path": path.file_name().unwrap(), "bytes": path.metadata()?.len(), "sha256": sha256_path(path)?}));
    }
    let report = json!({
        "schema": "max11-sparse-lp-csc-v1",
        "verdict": "PASS",
        "method": "exact CountSketch restriction of every F2 forest-pair column to the F2 pivot buckets",
        "universe": universe_path,
        "universe_sha256": sha256_path(&universe_path)?,
        "order_file": order_path,
        "order_file_sha256": sha256_path(&order_path)?,
        "pivot_report": pivot_path,
        "pivot_report_sha256": sha256_path(&pivot_path)?,
        "n": universe.n,
        "rows_numerator": rows,
        "rows_denominator": rows,
        "columns_numerator": columns,
        "columns_denominator": columns,
        "nonzeros_numerator": starts.last().unwrap(),
        "nonzeros_denominator": starts.last().unwrap(),
        "exact_real_nonzeros_visited_numerator": real_nnz,
        "exact_real_nonzeros_visited_denominator": expected_real_nnz,
        "sketch_algorithm": ALGORITHM,
        "sketch_seed": seed,
        "sketch_buckets_denominator": buckets,
        "pivot_buckets_numerator": rows,
        "pivot_buckets_denominator": rows,
        "target_bucket": target_bucket,
        "target_sign": target_sign,
        "sketch_entry_abs_max": sketch_abs_max,
        "include_five_l": include_five_l,
        "files": files,
        "build_seconds": started.elapsed().as_secs_f64(),
        "max_rss_kib": max_rss_kib(),
        "no_claim": "This exact row sketch is an LP search system. It is not an identity until a rational candidate is verified on every real support-union row."
    });
    fs::write(output.join("matrix.json"), serde_json::to_string_pretty(&report)? + "\n")?;
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hash_known_answers() {
        assert_eq!(linear_bucket(2026090201, 64000, 11, 10), (47568, -1));
        assert_eq!(hinge_bucket(2026090201, 64000, &[1, -1, 0]), (3184, -1));
    }
}
