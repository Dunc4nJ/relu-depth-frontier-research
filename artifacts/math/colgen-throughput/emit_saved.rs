//! Gate harness: emit generated saved templates in the documented MCOLGEN1 format.
//!
//! Usage: emit-saved INPUT.jsonl.gz N BRANCH_EDGES THREADS EXPECTED_COUNT OUTPUT

use anyhow::{Context, Result, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{
    ColumnOutput, SavedTemplate, generate_column, record_from_branches, saved_column,
};
use rayon::prelude::*;
use std::env;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Write};
use std::path::Path;
use std::time::Instant;

fn write_column(writer: &mut impl Write, output: ColumnOutput) -> Result<()> {
    writer.write_all(&(output.record_index as u64).to_le_bytes())?;
    for value in output.linear {
        writer.write_all(&value.to_le_bytes())?;
    }
    writer.write_all(&(output.hinges.len() as u64).to_le_bytes())?;
    for hinge in output.hinges {
        for value in hinge.direction {
            writer.write_all(&value.to_le_bytes())?;
        }
        writer.write_all(&hinge.coefficient.to_le_bytes())?;
    }
    Ok(())
}

fn main() -> Result<()> {
    let args = env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 7,
        "usage: emit-saved INPUT.jsonl.gz N BRANCH_EDGES THREADS EXPECTED_COUNT OUTPUT"
    );
    let input = Path::new(&args[1]);
    let n: usize = args[2].parse()?;
    let branch_edges: usize = args[3].parse()?;
    let threads: usize = args[4].parse()?;
    let expected_count: usize = args[5].parse()?;
    let output = Path::new(&args[6]);
    ensure!((1..=16).contains(&threads), "threads must lie in 1..=16");

    let source = File::open(input).with_context(|| format!("opening {}", input.display()))?;
    let mut reader = BufReader::new(GzDecoder::new(BufReader::new(source)));
    let destination = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(output)
        .with_context(|| format!("refusing to overwrite {}", output.display()))?;
    let mut writer = BufWriter::new(destination);
    writer.write_all(b"MCOLGEN1")?;
    writer.write_all(&(n as u16).to_le_bytes())?;
    writer.write_all(&(branch_edges as u16).to_le_bytes())?;
    writer.write_all(&0u64.to_le_bytes())?;
    writer.write_all(&(expected_count as u64).to_le_bytes())?;

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let started = Instant::now();
    let batch_size = threads * 2;
    let mut emitted = 0usize;
    let mut line = String::new();
    loop {
        let mut batch = Vec::with_capacity(batch_size);
        while batch.len() < batch_size {
            line.clear();
            if reader.read_line(&mut line)? == 0 {
                break;
            }
            let template: SavedTemplate = serde_json::from_str(&line)
                .with_context(|| format!("decoding template {emitted}"))?;
            batch.push((emitted + batch.len(), template));
        }
        if batch.is_empty() {
            break;
        }
        let generated: Vec<Result<(usize, max11_colgen::SparseColumn)>> = pool.install(|| {
            batch
                .par_iter()
                .map(|(index, template)| {
                    let record = record_from_branches(&template.a, &template.b, n)
                        .with_context(|| format!("record {index}"))?;
                    let column = generate_column(&record, n, branch_edges)
                        .with_context(|| format!("generate record {index}"))?;
                    let expected = saved_column(template, n)
                        .with_context(|| format!("saved record {index}"))?;
                    ensure!(
                        column == expected,
                        "record {index}: generated column mismatch"
                    );
                    Ok((*index, column))
                })
                .collect()
        });
        for result in generated {
            let (index, column) = result?;
            write_column(&mut writer, column.output(index, None)?)?;
            emitted += 1;
        }
    }
    ensure!(
        emitted == expected_count,
        "saved template count mismatch: {emitted}/{expected_count}"
    );
    writer.flush()?;
    eprintln!(
        "EMIT_SAVED_PASS records={emitted}/{expected_count} wall_seconds={:.9}",
        started.elapsed().as_secs_f64()
    );
    Ok(())
}
