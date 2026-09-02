use anyhow::{Context, Result, bail, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{SavedTemplate, SparseColumn, Universe, generate_column, saved_column};
use max11_price_universe::{CompiledSeparator, PRIMES, PriceSummary, PriceWriter, sha256_path};
use rayon::prelude::*;
use serde_json::{Value, json};
use std::collections::HashMap;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Debug)]
struct Args {
    command: String,
    values: HashMap<String, String>,
}

impl Args {
    fn parse() -> Result<Self> {
        let mut raw = std::env::args().skip(1);
        let command = raw.next().context("missing command")?;
        let mut values = HashMap::new();
        while let Some(key) = raw.next() {
            ensure!(
                key.starts_with("--"),
                "unexpected positional argument {key}"
            );
            let value = raw
                .next()
                .with_context(|| format!("missing value for {key}"))?;
            ensure!(
                values.insert(key.clone(), value).is_none(),
                "duplicate argument {key}"
            );
        }
        Ok(Self { command, values })
    }

    fn required_path(&self, name: &str) -> Result<PathBuf> {
        self.values
            .get(name)
            .map(PathBuf::from)
            .with_context(|| format!("missing {name}"))
    }

    fn usize_or(&self, name: &str, default: usize) -> Result<usize> {
        self.values
            .get(name)
            .map(|value| value.parse().with_context(|| format!("invalid {name}")))
            .transpose()
            .map(|value| value.unwrap_or(default))
    }

    fn boolean_or(&self, name: &str, default: bool) -> Result<bool> {
        self.values
            .get(name)
            .map(|value| match value.as_str() {
                "true" => Ok(true),
                "false" => Ok(false),
                _ => bail!("{name} must be true or false"),
            })
            .transpose()
            .map(|value| value.unwrap_or(default))
    }
}

fn open_reader(path: &Path) -> Result<Box<dyn Read>> {
    let file = File::open(path).with_context(|| format!("opening {}", path.display()))?;
    if path.extension().is_some_and(|extension| extension == "gz") {
        Ok(Box::new(GzDecoder::new(file)))
    } else {
        Ok(Box::new(file))
    }
}

fn write_report(path: &Path, report: &Value) -> Result<()> {
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    let mut output = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .with_context(|| format!("creating report {}", path.display()))?;
    serde_json::to_writer_pretty(&mut output, report)?;
    output.write_all(b"\n")?;
    Ok(())
}

fn peak_rss_kib() -> Option<u64> {
    std::fs::read_to_string("/proc/self/status")
        .ok()?
        .lines()
        .find_map(|line| line.strip_prefix("VmHWM:"))?
        .split_whitespace()
        .next()?
        .parse()
        .ok()
}

fn common_report(
    command: &str,
    separator_path: &Path,
    separator: &CompiledSeparator,
    violator_path: &Path,
    summary: PriceSummary,
    input: Value,
    elapsed: f64,
    generation_seconds: f64,
) -> Result<Value> {
    ensure!(
        summary.modular_agreement == [summary.evaluated, summary.evaluated],
        "modular agreement denominator mismatch"
    );
    Ok(json!({
        "schema": "max11-exact-price-universe-v1",
        "verdict": "PASS",
        "command": command,
        "input": input,
        "separator": separator_path,
        "separator_sha256": sha256_path(separator_path)?,
        "n": separator.n,
        "integer_scaled_common_denominator": separator.denominator_text(),
        "columns_evaluated_denominator": summary.evaluated,
        "annihilated_columns_numerator": summary.annihilated,
        "violating_columns_numerator": summary.violating,
        "i128_to_bigint_promoted_columns_numerator": summary.promoted_columns,
        "exact_price_vector_encoding": "MPRICEV1",
        "exact_price_vector_sha256": summary.vector_sha256,
        "violators": violator_path,
        "violators_sha256": summary.violators_sha256,
        "violators_bytes": summary.violators_bytes,
        "modular_cross_checks": [
            {"prime": PRIMES[0], "agreement_numerator": summary.modular_agreement[0], "agreement_denominator": summary.evaluated},
            {"prime": PRIMES[1], "agreement_numerator": summary.modular_agreement[1], "agreement_denominator": summary.evaluated},
        ],
        "generation_seconds": generation_seconds,
        "total_seconds": elapsed,
        "columns_per_second_denominator": elapsed,
        "columns_per_second_numerator": summary.evaluated,
        "peak_rss_kib": peak_rss_kib(),
        "no_claim": "Exact prices only over the named finite evaluated columns; this is not a MAX11 membership or unrestricted depth result."
    }))
}

fn read_u16(reader: &mut impl Read) -> Result<u16> {
    let mut bytes = [0u8; 2];
    reader.read_exact(&mut bytes)?;
    Ok(u16::from_le_bytes(bytes))
}

fn read_u64(reader: &mut impl Read) -> Result<u64> {
    let mut bytes = [0u8; 8];
    reader.read_exact(&mut bytes)?;
    Ok(u64::from_le_bytes(bytes))
}

fn read_i64(reader: &mut impl Read) -> Result<i64> {
    let mut bytes = [0u8; 8];
    reader.read_exact(&mut bytes)?;
    Ok(i64::from_le_bytes(bytes))
}

fn command_mcolgen(args: &Args) -> Result<()> {
    let started = Instant::now();
    let input = args.required_path("--input")?;
    let separator_path = args.required_path("--separator")?;
    let violators = args.required_path("--violators")?;
    let output = args.required_path("--output")?;
    let separator = CompiledSeparator::from_path(&separator_path)?;
    let input_sha256 = sha256_path(&input)?;
    let mut reader = BufReader::new(File::open(&input)?);
    let mut magic = [0u8; 8];
    reader.read_exact(&mut magic)?;
    ensure!(&magic == b"MCOLGEN1", "invalid MCOLGEN1 magic");
    let n = read_u16(&mut reader)? as usize;
    let branch_edges = read_u16(&mut reader)? as usize;
    let modulus = read_u64(&mut reader)?;
    let count = read_u64(&mut reader)?;
    ensure!(modulus == 0, "exact pricing refuses modular MCOLGEN1 input");
    ensure!(n == separator.n, "MCOLGEN1 n differs from separator");
    let mut writer = PriceWriter::create(n, &separator.denominator, &violators)?;
    for record in 0..count {
        let source_index =
            read_u64(&mut reader).with_context(|| format!("record {record} index"))?;
        let mut price = separator.start_price();
        for rank in 0..n {
            price.add_linear(rank, read_i64(&mut reader)?)?;
        }
        let hinge_count = read_u64(&mut reader)?;
        ensure!(
            hinge_count <= 10_000_000,
            "implausible MCOLGEN1 hinge count"
        );
        let mut direction = vec![0i16; n];
        for _ in 0..hinge_count {
            for value in &mut direction {
                let mut bytes = [0u8; 2];
                reader.read_exact(&mut bytes)?;
                *value = i16::from_le_bytes(bytes);
            }
            price.add_hinge(&direction, read_i64(&mut reader)?)?;
        }
        writer.record(source_index, price.finish()?)?;
    }
    let mut trailing = [0u8; 1];
    ensure!(
        reader.read(&mut trailing)? == 0,
        "MCOLGEN1 has trailing bytes"
    );
    let summary = writer.finish()?;
    let elapsed = started.elapsed().as_secs_f64();
    let report = common_report(
        "price-mcolgen",
        &separator_path,
        &separator,
        &violators,
        summary,
        json!({
            "path": input,
            "sha256": input_sha256,
            "format": "MCOLGEN1",
            "branch_edge_occurrences": branch_edges,
            "header_records_denominator": count,
        }),
        elapsed,
        0.0,
    )?;
    write_report(&output, &report)
}

fn is_union_spanning_tree(template: &SavedTemplate, n: usize) -> bool {
    let mut edges = std::collections::BTreeSet::new();
    edges.extend(template.a.iter().copied());
    edges.extend(template.b.iter().copied());
    if edges.len() != n - 1 || edges.iter().any(|edge| edge[0] == edge[1]) {
        return false;
    }
    let mut adjacency = vec![Vec::new(); n];
    for [first, second] in edges {
        if first >= n || second >= n {
            return false;
        }
        adjacency[first].push(second);
        adjacency[second].push(first);
    }
    let mut seen = vec![false; n];
    let mut stack = vec![0usize];
    seen[0] = true;
    while let Some(vertex) = stack.pop() {
        for &neighbor in &adjacency[vertex] {
            if !seen[neighbor] {
                seen[neighbor] = true;
                stack.push(neighbor);
            }
        }
    }
    seen.into_iter().all(|value| value)
}

fn command_saved(args: &Args) -> Result<()> {
    let started = Instant::now();
    let input = args.required_path("--input")?;
    let separator_path = args.required_path("--separator")?;
    let violators = args.required_path("--violators")?;
    let output = args.required_path("--output")?;
    let filter = args
        .values
        .get("--filter")
        .map(String::as_str)
        .unwrap_or("all");
    ensure!(
        ["all", "union-trees"].contains(&filter),
        "unsupported saved filter"
    );
    let separator = CompiledSeparator::from_path(&separator_path)?;
    let input_sha256 = sha256_path(&input)?;
    let reader = BufReader::new(open_reader(&input)?);
    let mut writer = PriceWriter::create(separator.n, &separator.denominator, &violators)?;
    let generation_started = Instant::now();
    let mut source_columns = 0u64;
    let mut selected_columns = 0u64;
    for (source_index, line) in reader.lines().enumerate() {
        let line = line.with_context(|| format!("reading saved column {source_index}"))?;
        let template: SavedTemplate = serde_json::from_str(&line)
            .with_context(|| format!("decoding saved column {source_index}"))?;
        source_columns += 1;
        if filter == "union-trees" && !is_union_spanning_tree(&template, separator.n) {
            continue;
        }
        let column = saved_column(&template, separator.n)?;
        writer.record(source_index as u64, separator.price_sparse(&column)?)?;
        selected_columns += 1;
    }
    let generation_seconds = generation_started.elapsed().as_secs_f64();
    let summary = writer.finish()?;
    ensure!(
        summary.evaluated == selected_columns,
        "saved selection count mismatch"
    );
    let elapsed = started.elapsed().as_secs_f64();
    let report = common_report(
        "price-saved",
        &separator_path,
        &separator,
        &violators,
        summary,
        json!({
            "path": input,
            "sha256": input_sha256,
            "format": "saved-system-jsonl",
            "filter": filter,
            "source_columns_denominator": source_columns,
            "selected_columns_denominator": selected_columns,
        }),
        elapsed,
        generation_seconds,
    )?;
    write_report(&output, &report)
}

fn checked_factorial(n: usize) -> Result<i64> {
    (1..=n).try_fold(1i64, |product, value| {
        product
            .checked_mul(value as i64)
            .context("factorial overflow")
    })
}

fn command_universe(args: &Args) -> Result<()> {
    let started = Instant::now();
    let universe_path = args.required_path("--universe")?;
    let separator_path = args.required_path("--separator")?;
    let violators = args.required_path("--violators")?;
    let output = args.required_path("--output")?;
    let threads = args.usize_or("--threads", 1)?;
    ensure!((1..=6).contains(&threads), "--threads must lie in 1..=6");
    let include_five_l = args.boolean_or("--include-five-l", false)?;
    let include_target = args.boolean_or("--include-target", false)?;
    let separator = CompiledSeparator::from_path(&separator_path)?;
    let universe_sha256 = sha256_path(&universe_path)?;
    let universe: Universe = serde_json::from_reader(open_reader(&universe_path)?)?;
    ensure!(
        universe.loopless,
        "price-universe requires a loopless universe"
    );
    ensure!(
        universe.n == separator.n,
        "universe n differs from separator"
    );
    let start = args.usize_or("--start", 0)?;
    let default_limit = universe.records.len().saturating_sub(start);
    let limit = args.usize_or("--limit", default_limit)?;
    let stop = start
        .checked_add(limit)
        .context("universe range overflow")?;
    ensure!(
        start < stop && stop <= universe.records.len(),
        "universe range is invalid"
    );
    ensure!(
        !(include_five_l || include_target) || (start == 0 && stop == universe.records.len()),
        "carriers/target may be appended only to a complete universe range"
    );
    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let mut writer = PriceWriter::create(separator.n, &separator.denominator, &violators)?;
    let mut generation_seconds = 0.0;
    let chunk_size = threads * 2;
    for chunk_start in (start..stop).step_by(chunk_size) {
        let chunk_stop = (chunk_start + chunk_size).min(stop);
        let generation_started = Instant::now();
        let generated: Vec<Result<(u64, SparseColumn)>> = pool.install(|| {
            universe.records[chunk_start..chunk_stop]
                .par_iter()
                .enumerate()
                .map(|(offset, record)| {
                    let index = chunk_start + offset;
                    Ok((
                        index as u64,
                        generate_column(record, universe.n, universe.branch_edge_occurrences)
                            .with_context(|| format!("generating universe record {index}"))?,
                    ))
                })
                .collect()
        });
        let generated = generated.into_iter().collect::<Result<Vec<_>>>()?;
        generation_seconds += generation_started.elapsed().as_secs_f64();
        for (source_index, column) in generated {
            writer.record(source_index, separator.price_sparse(&column)?)?;
        }
    }
    let mut five_l_index = None;
    if include_five_l {
        let source_index = universe.records.len() as u64;
        let coefficient = i64::try_from(universe.branch_edge_occurrences)?
            .checked_mul(checked_factorial(universe.n - 1)?)
            .context("5L carrier coefficient overflow")?;
        let column = SparseColumn {
            linear: vec![coefficient; universe.n],
            hinges: Default::default(),
        };
        writer.record(source_index, separator.price_sparse(&column)?)?;
        five_l_index = Some(source_index);
    }
    let mut target_index = None;
    if include_target {
        let source_index = universe.records.len() as u64 + u64::from(include_five_l);
        let mut linear = vec![0; universe.n];
        linear[universe.n - 1] = 1;
        writer.record(
            source_index,
            separator.price_sparse(&SparseColumn {
                linear,
                hinges: Default::default(),
            })?,
        )?;
        target_index = Some(source_index);
    }
    let summary = writer.finish()?;
    let elapsed = started.elapsed().as_secs_f64();
    let report = common_report(
        "price-universe",
        &separator_path,
        &separator,
        &violators,
        summary,
        json!({
            "path": universe_path,
            "sha256": universe_sha256,
            "format": "max11-colgen Universe",
            "universe_records_denominator": universe.records.len(),
            "range_start": start,
            "range_stop": stop,
            "range_records_denominator": limit,
            "branch_edge_occurrences": universe.branch_edge_occurrences,
            "threads_maximum": threads,
            "five_l_carrier_source_index": five_l_index,
            "target_source_index": target_index,
        }),
        elapsed,
        generation_seconds,
    )?;
    write_report(&output, &report)
}

fn usage() -> &'static str {
    "usage:\n  max11-price-universe price-mcolgen --input FILE --separator FILE --violators FILE --output REPORT\n  max11-price-universe price-saved --input FILE.jsonl[.gz] --separator FILE --filter all|union-trees --violators FILE --output REPORT\n  max11-price-universe price-universe --universe FILE.json[.gz] --separator FILE --threads 1..6 [--start N --limit N] [--include-five-l true] [--include-target true] --violators FILE --output REPORT"
}

fn main() {
    let result = Args::parse().and_then(|args| match args.command.as_str() {
        "price-mcolgen" => command_mcolgen(&args),
        "price-saved" => command_saved(&args),
        "price-universe" => command_universe(&args),
        other => bail!("unknown command {other}\n{}", usage()),
    });
    if let Err(error) = result {
        eprintln!("ERROR: {error:#}\n{}", usage());
        std::process::exit(2);
    }
}
