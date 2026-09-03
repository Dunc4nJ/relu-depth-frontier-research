use anyhow::{Context, Result, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{Universe, generate_column};
use rayon::prelude::*;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    result: &'static str,
    universe: String,
    universe_sha256: String,
    order_file: String,
    order_file_sha256: String,
    threads: usize,
    columns_denominator: usize,
    total_linear_entries: usize,
    total_hinge_entries: usize,
    wall_seconds: f64,
    columns_per_second: f64,
    no_claim: &'static str,
}

fn sha256(path: &Path) -> Result<String> {
    let mut reader = BufReader::new(File::open(path)?);
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    loop {
        let count = reader.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn main() -> Result<()> {
    let mut args = std::env::args().skip(1);
    let universe_path = PathBuf::from(args.next().context("missing universe")?);
    let order_path = PathBuf::from(args.next().context("missing order file")?);
    let threads: usize = args.next().context("missing threads")?.parse()?;
    ensure!(args.next().is_none(), "unexpected trailing argument");
    ensure!((1..=16).contains(&threads), "threads must lie in 1..=16");

    let universe: Universe = serde_json::from_reader(GzDecoder::new(BufReader::new(
        File::open(&universe_path)?,
    )))?;
    let order: Vec<usize> = serde_json::from_reader(BufReader::new(File::open(&order_path)?))?;
    ensure!(!order.is_empty(), "empty order");
    ensure!(
        order.iter().all(|&index| index < universe.records.len()),
        "order index out of range"
    );

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let started = Instant::now();
    let sizes: Vec<Result<(usize, usize)>> = pool.install(|| {
        order
            .par_iter()
            .map(|&index| {
                let column = generate_column(
                    &universe.records[index],
                    universe.n,
                    universe.branch_edge_occurrences,
                )?;
                Ok((column.linear.len(), column.hinges.len()))
            })
            .collect()
    });
    let sizes: Vec<(usize, usize)> = sizes.into_iter().collect::<Result<_>>()?;
    let wall_seconds = started.elapsed().as_secs_f64();
    let report = Report {
        schema: "max11-colgen-generation-benchmark-v1",
        result: "PASS",
        universe: universe_path.display().to_string(),
        universe_sha256: sha256(&universe_path)?,
        order_file: order_path.display().to_string(),
        order_file_sha256: sha256(&order_path)?,
        threads,
        columns_denominator: sizes.len(),
        total_linear_entries: sizes.iter().map(|value| value.0).sum(),
        total_hinge_entries: sizes.iter().map(|value| value.1).sum(),
        wall_seconds,
        columns_per_second: sizes.len() as f64 / wall_seconds,
        no_claim: "This is a throughput measurement over the named finite input prefix. It is not a MAX11 verdict, identity, completeness statement, or depth lower bound.",
    };
    serde_json::to_writer_pretty(std::io::stdout().lock(), &report)?;
    println!();
    Ok(())
}
