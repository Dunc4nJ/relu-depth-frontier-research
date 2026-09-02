use anyhow::{Context, Result, bail, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{SavedTemplate, SparseColumn, Universe, generate_column, saved_column};
use max11_streamrank::{DenseEchelon, ReducerMetrics, SketchSpec, set_blas_threads};
use rayon::prelude::*;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Debug)]
struct Args {
    command: String,
    values: HashMap<String, String>,
    invocation: Vec<String>,
}

impl Args {
    fn parse() -> Result<Self> {
        let invocation: Vec<String> = env::args().collect();
        let mut items = invocation.iter().skip(1);
        let command = items.next().context("missing command")?.clone();
        let mut values = HashMap::new();
        while let Some(flag) = items.next() {
            ensure!(
                flag.starts_with("--"),
                "unexpected positional argument {flag}"
            );
            let value = items
                .next()
                .with_context(|| format!("missing value for {flag}"))?;
            ensure!(!value.starts_with("--"), "missing value for {flag}");
            ensure!(
                values.insert(flag.clone(), value.clone()).is_none(),
                "duplicate {flag}"
            );
        }
        Ok(Self {
            command,
            values,
            invocation,
        })
    }

    fn required(&self, name: &str) -> Result<&str> {
        self.values
            .get(name)
            .map(String::as_str)
            .with_context(|| format!("required argument {name} missing"))
    }

    fn path(&self, name: &str) -> Result<PathBuf> {
        Ok(PathBuf::from(self.required(name)?))
    }

    fn usize(&self, name: &str) -> Result<usize> {
        self.required(name)?
            .parse()
            .with_context(|| format!("invalid {name}"))
    }

    fn usize_or(&self, name: &str, default: usize) -> Result<usize> {
        self.values
            .get(name)
            .map(|value| value.parse().with_context(|| format!("invalid {name}")))
            .transpose()
            .map(|value| value.unwrap_or(default))
    }

    fn optional_usize(&self, name: &str) -> Result<Option<usize>> {
        self.values
            .get(name)
            .map(|value| value.parse().with_context(|| format!("invalid {name}")))
            .transpose()
    }

    fn u32(&self, name: &str) -> Result<u32> {
        self.required(name)?
            .parse()
            .with_context(|| format!("invalid {name}"))
    }

    fn seeds(&self) -> Result<Vec<u64>> {
        let result: Vec<u64> = self
            .required("--seeds")?
            .split(',')
            .map(parse_u64)
            .collect::<Result<_>>()?;
        ensure!(
            result.len() == 2 && result[0] != result[1],
            "exactly two distinct sketch seeds are required"
        );
        Ok(result)
    }
}

fn parse_u64(value: &str) -> Result<u64> {
    if let Some(hex) = value.strip_prefix("0x") {
        Ok(u64::from_str_radix(hex, 16)?)
    } else {
        Ok(value.parse()?)
    }
}

fn open_reader(path: &Path) -> Result<Box<dyn BufRead>> {
    let file = File::open(path).with_context(|| format!("opening {}", path.display()))?;
    if path.extension().is_some_and(|extension| extension == "gz") {
        Ok(Box::new(BufReader::new(GzDecoder::new(BufReader::new(
            file,
        )))))
    } else {
        Ok(Box::new(BufReader::new(file)))
    }
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut input = File::open(path)?;
    let mut hash = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    loop {
        let count = input.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        hash.update(&buffer[..count]);
    }
    Ok(format!("{:x}", hash.finalize()))
}

fn create_output(path: &Path) -> Result<BufWriter<File>> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .with_context(|| format!("refusing to overwrite {}", path.display()))?;
    Ok(BufWriter::new(file))
}

fn write_json(path: &Path, value: &impl Serialize) -> Result<()> {
    let mut output = create_output(path)?;
    serde_json::to_writer_pretty(&mut output, value)?;
    output.write_all(b"\n")?;
    output.flush()?;
    Ok(())
}

fn is_union_spanning_tree(template: &SavedTemplate, n: usize) -> bool {
    let edges: HashSet<[usize; 2]> = template.a.iter().chain(&template.b).copied().collect();
    if edges.len() != n - 1 {
        return false;
    }
    let mut adjacency = vec![Vec::new(); n];
    for [a, b] in edges {
        if a == b || b >= n {
            return false;
        }
        adjacency[a].push(b);
        adjacency[b].push(a);
    }
    let mut seen = vec![false; n];
    seen[0] = true;
    let mut stack = vec![0usize];
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

#[derive(Debug)]
struct State {
    spec: SketchSpec,
    basis: DenseEchelon,
    sketch_seconds: f64,
    reducer_seconds: f64,
    real_entry_visits_numerator: u128,
    max_basis_storage_bytes: usize,
}

impl State {
    fn new(seed: u64, buckets: usize, prime: u32, block_size: usize) -> Result<Self> {
        Ok(Self {
            spec: SketchSpec::new(seed, buckets)?,
            basis: DenseEchelon::new(buckets, prime, block_size)?,
            sketch_seconds: 0.0,
            reducer_seconds: 0.0,
            real_entry_visits_numerator: 0,
            max_basis_storage_bytes: 0,
        })
    }

    fn process(&mut self, columns: &[(u64, SparseColumn)], prime: u32) -> Result<()> {
        let sketched_at = Instant::now();
        let mut matrix = vec![0u32; self.spec.buckets * columns.len()];
        for (position, (_, column)) in columns.iter().enumerate() {
            self.spec.sketch_column(
                column,
                prime,
                &mut matrix[position * self.spec.buckets..(position + 1) * self.spec.buckets],
            );
            self.real_entry_visits_numerator +=
                (column.linear.iter().filter(|&&value| value != 0).count() + column.hinges.len())
                    as u128;
        }
        self.sketch_seconds += sketched_at.elapsed().as_secs_f64();
        let reduced_at = Instant::now();
        let indices: Vec<u64> = columns.iter().map(|(index, _)| *index).collect();
        self.basis.process_batch(&mut matrix, &indices)?;
        self.reducer_seconds += reduced_at.elapsed().as_secs_f64();
        self.max_basis_storage_bytes = self.max_basis_storage_bytes.max(self.basis.storage_bytes());
        Ok(())
    }
}

#[derive(Debug)]
struct Config {
    input: PathBuf,
    output: PathBuf,
    n: usize,
    branch_edges: usize,
    prime: u32,
    buckets: usize,
    batch_size: usize,
    block_size: usize,
    threads: usize,
    seeds: Vec<u64>,
    expected_columns: Option<usize>,
    expected_rank: Option<usize>,
    expected_aug_rank: Option<usize>,
    expected_verdict: Option<String>,
}

impl Config {
    fn from_args(args: &Args) -> Result<Self> {
        let threads = args.usize("--threads")?;
        ensure!(
            (1..=6).contains(&threads),
            "threads must lie in 1..=6 on this shared host"
        );
        let batch_size = args.usize("--batch-size")?;
        ensure!(
            (1..=1024).contains(&batch_size),
            "batch size must lie in 1..=1024"
        );
        Ok(Self {
            input: args.path("--input")?,
            output: args.path("--output")?,
            n: args.usize("--n")?,
            branch_edges: args.usize("--branch-edges")?,
            prime: args.u32("--modulus")?,
            buckets: args.usize("--buckets")?,
            batch_size,
            block_size: args.usize("--gemm-block")?,
            threads,
            seeds: args.seeds()?,
            expected_columns: args.optional_usize("--expected-columns")?,
            expected_rank: args.optional_usize("--expected-rank")?,
            expected_aug_rank: args.optional_usize("--expected-aug-rank")?,
            expected_verdict: args.values.get("--expected-verdict").cloned(),
        })
    }
}

#[derive(Serialize)]
struct ExpectedReport {
    source_columns: Option<usize>,
    rank_a: Option<usize>,
    rank_augmented: Option<usize>,
    verdict: Option<String>,
    exact_match: bool,
}

#[derive(Serialize)]
struct SketchReport {
    sketch: SketchSpec,
    rank_a: usize,
    rank_augmented: usize,
    saturated: bool,
    verdict: String,
    pivot_columns: Vec<u64>,
    pivot_buckets: Vec<u32>,
    sketch_seconds: f64,
    reducer_seconds: f64,
    real_entry_visits_numerator: u128,
    source_columns_denominator: usize,
    max_basis_storage_bytes: usize,
    reducer_metrics: ReducerMetrics,
}

#[derive(Serialize)]
struct Report {
    schema: &'static str,
    result: String,
    command: Vec<String>,
    input: String,
    input_sha256: String,
    subject: String,
    n: usize,
    branch_edge_occurrences: usize,
    modulus: u32,
    buckets: usize,
    batch_size: usize,
    gemm_block: usize,
    threads: usize,
    source_columns_denominator: usize,
    exact_real_nnz_numerator: u128,
    wall_seconds: f64,
    max_rss_kib: Option<u64>,
    expected: ExpectedReport,
    sketches: Vec<SketchReport>,
    no_claim: &'static str,
}

fn max_rss_kib() -> Option<u64> {
    let status = fs::read_to_string("/proc/self/status").ok()?;
    status.lines().find_map(|line| {
        line.strip_prefix("VmHWM:")?
            .split_whitespace()
            .next()?
            .parse()
            .ok()
    })
}

struct SourceSummary {
    subject: String,
    input_hash: String,
    source_columns: usize,
    exact_nnz: u128,
    started: Instant,
}

fn finish_run(
    args: &Args,
    config: Config,
    source: SourceSummary,
    states: Vec<State>,
) -> Result<()> {
    let SourceSummary {
        subject,
        input_hash,
        source_columns,
        exact_nnz,
        started,
    } = source;
    let mut sketches = Vec::new();
    for mut state in states {
        let rank_a = state.basis.rank();
        let saturated = rank_a == config.buckets;
        let mut target = vec![0u32; config.buckets];
        let target_column = SparseColumn {
            linear: (0..config.n)
                .map(|rank| i64::from(rank + 1 == config.n))
                .collect(),
            hinges: Default::default(),
        };
        state
            .spec
            .sketch_column(&target_column, config.prime, &mut target);
        if !saturated {
            state.basis.reduce_only(&mut target)?;
        }
        let outside = !saturated && target.iter().any(|&value| value != 0);
        let rank_augmented = rank_a + usize::from(outside);
        let verdict = if saturated {
            "SATURATED"
        } else if outside {
            "NON_MEMBER"
        } else {
            "MEMBER"
        };
        sketches.push(SketchReport {
            sketch: state.spec,
            rank_a,
            rank_augmented,
            saturated,
            verdict: verdict.to_owned(),
            pivot_columns: state.basis.pivot_columns().to_vec(),
            pivot_buckets: state
                .basis
                .pivot_rows()
                .iter()
                .map(|&row| row as u32)
                .collect(),
            sketch_seconds: state.sketch_seconds,
            reducer_seconds: state.reducer_seconds,
            real_entry_visits_numerator: state.real_entry_visits_numerator,
            source_columns_denominator: source_columns,
            max_basis_storage_bytes: state.max_basis_storage_bytes,
            reducer_metrics: state.basis.metrics,
        });
    }
    let exact_match = config
        .expected_columns
        .is_none_or(|value| value == source_columns)
        && config
            .expected_rank
            .is_none_or(|value| sketches.iter().all(|item| item.rank_a == value))
        && config
            .expected_aug_rank
            .is_none_or(|value| sketches.iter().all(|item| item.rank_augmented == value))
        && config
            .expected_verdict
            .as_ref()
            .is_none_or(|value| sketches.iter().all(|item| &item.verdict == value));
    let has_expectation = config.expected_columns.is_some()
        || config.expected_rank.is_some()
        || config.expected_aug_rank.is_some()
        || config.expected_verdict.is_some();
    let report = Report {
        schema: "max11-streamrank-pivots-v1",
        result: if has_expectation {
            if exact_match {
                "CONTROL_PASS"
            } else {
                "CONTROL_FAIL"
            }
        } else {
            "OBSERVATION"
        }
        .to_owned(),
        command: args.invocation.clone(),
        input: config.input.display().to_string(),
        input_sha256: input_hash,
        subject,
        n: config.n,
        branch_edge_occurrences: config.branch_edges,
        modulus: config.prime,
        buckets: config.buckets,
        batch_size: config.batch_size,
        gemm_block: config.block_size,
        threads: config.threads,
        source_columns_denominator: source_columns,
        exact_real_nnz_numerator: exact_nnz,
        wall_seconds: started.elapsed().as_secs_f64(),
        max_rss_kib: max_rss_kib(),
        expected: ExpectedReport {
            source_columns: config.expected_columns,
            rank_a: config.expected_rank,
            rank_augmented: config.expected_aug_rank,
            verdict: config.expected_verdict,
            exact_match,
        },
        sketches,
        no_claim: "Ranks and verdicts are over two named finite random row sketches modulo one named prime. MEMBER is not exact-Q consistency and no identity has been verified on every real row; NON_MEMBER concerns only the named finite column family and is not an unrestricted two-hidden-layer depth lower bound. Exact lifting or separation is delegated to tools/exactlift.",
    };
    write_json(&config.output, &report)?;
    ensure!(
        exact_match,
        "known-answer control failed; report was preserved"
    );
    eprintln!(
        "STREAMRANK_{} columns={} ranks={:?} seconds={:.3}",
        report.result,
        source_columns,
        report
            .sketches
            .iter()
            .map(|item| (item.rank_a, item.rank_augmented))
            .collect::<Vec<_>>(),
        report.wall_seconds
    );
    Ok(())
}

fn process_batch(states: &mut [State], batch: &[(u64, SparseColumn)], prime: u32) -> Result<()> {
    for state in states {
        state.process(batch, prime)?;
    }
    Ok(())
}

fn command_saved(args: &Args) -> Result<()> {
    let config = Config::from_args(args)?;
    let filter = args.required("--filter")?;
    ensure!(
        ["all", "union-trees"].contains(&filter),
        "filter must be all or union-trees"
    );
    set_blas_threads(config.threads)?;
    let input_hash = sha256_path(&config.input)?;
    let started = Instant::now();
    let mut states: Vec<State> = config
        .seeds
        .iter()
        .map(|&seed| State::new(seed, config.buckets, config.prime, config.block_size))
        .collect::<Result<_>>()?;
    let mut reader = open_reader(&config.input)?;
    let mut line = String::new();
    let mut source_index = 0u64;
    let mut selected = 0usize;
    let mut exact_nnz = 0u128;
    let mut batch = Vec::with_capacity(config.batch_size);
    loop {
        line.clear();
        if reader.read_line(&mut line)? == 0 {
            break;
        }
        let template: SavedTemplate = serde_json::from_str(&line)
            .with_context(|| format!("decoding source record {source_index}"))?;
        let include = filter == "all" || is_union_spanning_tree(&template, config.n);
        if include {
            let column = saved_column(&template, config.n)?;
            exact_nnz += (column.linear.iter().filter(|&&value| value != 0).count()
                + column.hinges.len()) as u128;
            batch.push((source_index, column));
            selected += 1;
            if batch.len() == config.batch_size {
                process_batch(&mut states, &batch, config.prime)?;
                batch.clear();
                eprintln!(
                    "STREAMRANK_PROGRESS columns={selected} ranks={:?} seconds={:.3}",
                    states
                        .iter()
                        .map(|state| state.basis.rank())
                        .collect::<Vec<_>>(),
                    started.elapsed().as_secs_f64()
                );
            }
        }
        source_index += 1;
    }
    if !batch.is_empty() {
        process_batch(&mut states, &batch, config.prime)?;
    }
    finish_run(
        args,
        config,
        SourceSummary {
            subject: format!("saved-system:{filter}"),
            input_hash,
            source_columns: selected,
            exact_nnz,
            started,
        },
        states,
    )
}

fn command_universe(args: &Args) -> Result<()> {
    let config = Config::from_args(args)?;
    set_blas_threads(config.threads)?;
    let input_hash = sha256_path(&config.input)?;
    let universe: Universe = serde_json::from_reader(open_reader(&config.input)?)?;
    ensure!(
        universe.n == config.n && universe.branch_edge_occurrences == config.branch_edges,
        "universe/config dimensions differ"
    );
    ensure!(universe.loopless, "only loopless universes are supported");
    let start = args.usize_or("--start", 0)?;
    let limit = args.usize_or("--limit", universe.records.len().saturating_sub(start))?;
    let stop = start.checked_add(limit).context("range overflow")?;
    ensure!(
        start < stop && stop <= universe.records.len(),
        "range outside universe"
    );
    let started = Instant::now();
    let mut states: Vec<State> = config
        .seeds
        .iter()
        .map(|&seed| State::new(seed, config.buckets, config.prime, config.block_size))
        .collect::<Result<_>>()?;
    let mut exact_nnz = 0u128;
    for batch_start in (start..stop).step_by(config.batch_size) {
        let batch_stop = (batch_start + config.batch_size).min(stop);
        let generated: Vec<Result<(u64, SparseColumn)>> = universe.records[batch_start..batch_stop]
            .par_iter()
            .enumerate()
            .map(|(offset, record)| {
                Ok((
                    (batch_start + offset) as u64,
                    generate_column(record, config.n, config.branch_edges)?,
                ))
            })
            .collect();
        let batch: Vec<(u64, SparseColumn)> = generated.into_iter().collect::<Result<_>>()?;
        exact_nnz += batch
            .iter()
            .map(|(_, column)| {
                column.linear.iter().filter(|&&value| value != 0).count() + column.hinges.len()
            })
            .sum::<usize>() as u128;
        process_batch(&mut states, &batch, config.prime)?;
        eprintln!(
            "STREAMRANK_PROGRESS columns={}/{} ranks={:?} seconds={:.3}",
            batch_stop - start,
            limit,
            states
                .iter()
                .map(|state| state.basis.rank())
                .collect::<Vec<_>>(),
            started.elapsed().as_secs_f64()
        );
    }
    finish_run(
        args,
        config,
        SourceSummary {
            subject: format!("colgen-universe-range:[{start},{stop})"),
            input_hash,
            source_columns: limit,
            exact_nnz,
            started,
        },
        states,
    )
}

fn usage() -> &'static str {
    "usage:\n  max11-streamrank run-saved --input FILE.jsonl[.gz] --n N --branch-edges K --filter all|union-trees --modulus P --buckets M --seeds U64,U64 --batch-size B --gemm-block Q --threads T --output REPORT.json [--expected-columns C --expected-rank R --expected-aug-rank R2 --expected-verdict MEMBER|NON_MEMBER|SATURATED]\n  max11-streamrank run-universe --input UNIVERSE.json[.gz] --n N --branch-edges K --modulus P --buckets M --seeds U64,U64 --batch-size B --gemm-block Q --threads T --output REPORT.json [--start I --limit L and expected arguments]"
}

fn main() -> Result<()> {
    let args = Args::parse().with_context(usage)?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(args.usize("--threads")?)
        .build_global()?;
    match args.command.as_str() {
        "run-saved" => command_saved(&args),
        "run-universe" => command_universe(&args),
        other => bail!("unknown command {other}\n{}", usage()),
    }
}
