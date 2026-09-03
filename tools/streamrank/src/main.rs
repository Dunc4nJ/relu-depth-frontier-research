use anyhow::{Context, Result, bail, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{
    SavedTemplate, SparseColumn, Universe, common_loop_carrier_column, generate_column,
    saved_column,
};
use max11_streamrank::{Echelon, ReducerMetrics, SketchSpec, set_blas_threads};
use rayon::prelude::*;
use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::sync::mpsc::sync_channel;
use std::thread;
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

    fn bool_or(&self, name: &str, default: bool) -> Result<bool> {
        self.values
            .get(name)
            .map(|value| match value.as_str() {
                "true" => Ok(true),
                "false" => Ok(false),
                _ => bail!("invalid {name}; expected true or false"),
            })
            .transpose()
            .map(|value| value.unwrap_or(default))
    }

    fn u32(&self, name: &str) -> Result<u32> {
        self.required(name)?
            .parse()
            .with_context(|| format!("invalid {name}"))
    }

    fn u64(&self, name: &str) -> Result<u64> {
        parse_u64(self.required(name)?)
    }

    fn seeds(&self) -> Result<Vec<u64>> {
        let result: Vec<u64> = self
            .required("--seeds")?
            .split(',')
            .map(parse_u64)
            .collect::<Result<_>>()?;
        ensure!(
            (1..=2).contains(&result.len())
                && result.iter().copied().collect::<HashSet<_>>().len() == result.len(),
            "one or two distinct sketch seeds are required"
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

fn sha256_u64_le(values: &[u64]) -> String {
    let mut hash = Sha256::new();
    for &value in values {
        hash.update(value.to_le_bytes());
    }
    format!("{:x}", hash.finalize())
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
    basis: Echelon,
    matrix_allocation_seconds: f64,
    sketch_seconds: f64,
    reducer_seconds: f64,
    real_entry_visits_numerator: u128,
    max_basis_storage_bytes: usize,
}

impl State {
    fn new(
        seed: u64,
        buckets: usize,
        prime: u32,
        block_size: usize,
        panel_size: usize,
        batch_size: usize,
        backend: &str,
    ) -> Result<Self> {
        Ok(Self {
            spec: SketchSpec::new(seed, buckets)?,
            basis: Echelon::with_backend(
                backend, buckets, prime, block_size, panel_size, batch_size,
            )?,
            matrix_allocation_seconds: 0.0,
            sketch_seconds: 0.0,
            reducer_seconds: 0.0,
            real_entry_visits_numerator: 0,
            max_basis_storage_bytes: 0,
        })
    }

    fn process(&mut self, columns: &[(u64, SparseColumn)], prime: u32) -> Result<()> {
        let allocated_at = Instant::now();
        let mut matrix = vec![0u32; self.spec.buckets * columns.len()];
        self.matrix_allocation_seconds += allocated_at.elapsed().as_secs_f64();
        let sketched_at = Instant::now();
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
        let indices: Vec<u64> = columns.iter().map(|(index, _)| *index).collect();
        self.process_sketched(&mut matrix, &indices)
    }

    fn process_sketched(&mut self, matrix: &mut [u32], indices: &[u64]) -> Result<()> {
        let reduced_at = Instant::now();
        self.basis.process_batch(matrix, indices)?;
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
    panel_size: usize,
    threads: usize,
    backend: String,
    seeds: Vec<u64>,
    include_five_l: bool,
    include_linear_carrier: bool,
    abort_rank_above: Option<usize>,
    abort_rss_kib_above: Option<usize>,
    expected_columns: Option<usize>,
    expected_rank: Option<usize>,
    expected_aug_rank: Option<usize>,
    expected_verdict: Option<String>,
}

impl Config {
    fn from_args(args: &Args) -> Result<Self> {
        let backend = args
            .values
            .get("--backend")
            .cloned()
            .unwrap_or_else(|| "cpu".to_owned());
        ensure!(
            ["cpu", "cuda"].contains(&backend.as_str()),
            "backend must be cpu or cuda"
        );
        let threads = args.usize("--threads")?;
        let thread_limit = if backend == "cuda" { 60 } else { 6 };
        ensure!(
            (1..=thread_limit).contains(&threads),
            "threads must lie in 1..={thread_limit} for backend {backend}"
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
            panel_size: args.usize_or("--rank-panel", 64)?,
            threads,
            backend,
            seeds: args.seeds()?,
            include_five_l: args.bool_or("--include-five-l", false)?,
            include_linear_carrier: args.bool_or("--include-linear-carrier", false)?,
            abort_rank_above: args.optional_usize("--abort-rank-above")?,
            abort_rss_kib_above: args.optional_usize("--abort-rss-kib-above")?,
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
struct BucketResidue {
    bucket: u32,
    residue: u32,
}

#[derive(Clone, Serialize)]
struct LinearCarrierReport {
    label: String,
    branch_edge_occurrences: usize,
    source_index: u64,
    exact_linear_coefficient_each_of_n_coordinates: i64,
    coordinate_count: usize,
    hinge_count: usize,
}

fn linear_carrier(
    n: usize,
    branch_edges: usize,
    source_index: u64,
) -> Result<(LinearCarrierReport, SparseColumn)> {
    let column = common_loop_carrier_column(n, branch_edges)?;
    let coefficient = column.linear[0];
    Ok((
        LinearCarrierReport {
            label: format!("{branch_edges}L"),
            branch_edge_occurrences: branch_edges,
            source_index,
            exact_linear_coefficient_each_of_n_coordinates: coefficient,
            coordinate_count: n,
            hinge_count: 0,
        },
        SparseColumn {
            linear: vec![coefficient; n],
            hinges: Default::default(),
        },
    ))
}

#[derive(Serialize)]
struct SeparatorReport {
    encoding: &'static str,
    length: usize,
    entries: Vec<BucketResidue>,
    dot_target_mod_prime: u32,
    verified_basis_columns_denominator: usize,
}

#[derive(Serialize)]
struct SketchReport {
    sketch: SketchSpec,
    rank_a: usize,
    rank_augmented: usize,
    saturated: bool,
    verdict: String,
    pivot_columns: Vec<u64>,
    pivot_columns_u64_le_sha256: String,
    pivot_buckets: Vec<u32>,
    target_sketch_nonzero: Vec<BucketResidue>,
    left_separator: Option<SeparatorReport>,
    matrix_allocation_seconds: f64,
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
    order_file: Option<String>,
    order_file_sha256: Option<String>,
    five_l_carrier: Option<LinearCarrierReport>,
    linear_loop_carrier: Option<LinearCarrierReport>,
    subject: String,
    n: usize,
    branch_edge_occurrences: usize,
    modulus: u32,
    buckets: usize,
    batch_size: usize,
    gemm_block: usize,
    rank_panel: usize,
    threads: usize,
    backend: String,
    source_column_count: usize,
    source_columns_denominator: usize,
    exact_real_nnz_numerator: u128,
    column_generation_seconds: f64,
    progress: Vec<ProgressPoint>,
    wall_seconds: f64,
    max_rss_kib: Option<u64>,
    expected: ExpectedReport,
    sketches: Vec<SketchReport>,
    no_claim: &'static str,
}

#[derive(Serialize)]
struct ProgressPoint {
    source_columns_processed: usize,
    ranks: Vec<usize>,
    elapsed_seconds: f64,
    cumulative_seconds_per_column: f64,
    #[serde(flatten)]
    phases: BatchPhaseTimes,
}

#[derive(Clone, Copy, Default, Serialize)]
struct BatchPhaseTimes {
    generate_s: f64,
    sketch_s: f64,
    gemm_s: f64,
    host_reduce_s: f64,
    basis_update_s: f64,
    io_s: f64,
    sparse_drop_s: f64,
}

#[derive(Serialize)]
struct AbortSketchReport {
    sketch: SketchSpec,
    rank_a: usize,
    pivot_columns: Vec<u64>,
    pivot_columns_u64_le_sha256: String,
    pivot_buckets: Vec<u32>,
    matrix_allocation_seconds: f64,
    sketch_seconds: f64,
    reducer_seconds: f64,
    real_entry_visits_numerator: u128,
    source_columns_denominator: usize,
    max_basis_storage_bytes: usize,
    reducer_metrics: ReducerMetrics,
}

#[derive(Serialize)]
struct AbortReport {
    schema: &'static str,
    result: &'static str,
    abort_reason: String,
    command: Vec<String>,
    input: String,
    input_sha256: String,
    order_file: Option<String>,
    order_file_sha256: Option<String>,
    five_l_carrier: Option<LinearCarrierReport>,
    linear_loop_carrier: Option<LinearCarrierReport>,
    subject: String,
    n: usize,
    branch_edge_occurrences: usize,
    modulus: u32,
    buckets: usize,
    batch_size: usize,
    gemm_block: usize,
    rank_panel: usize,
    threads: usize,
    backend: String,
    requested_source_column_count: usize,
    source_column_count: usize,
    source_columns_denominator: usize,
    exact_real_nnz_numerator: u128,
    column_generation_seconds: f64,
    progress: Vec<ProgressPoint>,
    wall_seconds: f64,
    current_rss_kib: Option<u64>,
    max_rss_kib: Option<u64>,
    sketches: Vec<AbortSketchReport>,
    no_claim: &'static str,
}

fn status_memory_kib(field: &str) -> Option<u64> {
    let status = fs::read_to_string("/proc/self/status").ok()?;
    status.lines().find_map(|line| {
        line.strip_prefix(field)?
            .split_whitespace()
            .next()?
            .parse()
            .ok()
    })
}

fn max_rss_kib() -> Option<u64> {
    status_memory_kib("VmHWM:")
}

fn current_rss_kib() -> Option<u64> {
    status_memory_kib("VmRSS:")
}

fn abort_reason(config: &Config, states: &[State]) -> Option<String> {
    if let Some(limit) = config.abort_rank_above {
        let observed = states
            .iter()
            .map(|state| state.basis.rank())
            .max()
            .unwrap_or(0);
        if observed > limit {
            return Some(format!("rank {observed} exceeded abort threshold {limit}"));
        }
    }
    if let (Some(limit), Some(observed)) = (config.abort_rss_kib_above, max_rss_kib())
        && observed > limit as u64
    {
        return Some(format!(
            "high-water RSS {observed} KiB exceeded abort threshold {limit} KiB"
        ));
    }
    None
}

#[allow(clippy::too_many_arguments)]
fn finish_abort(
    args: &Args,
    config: &Config,
    input_hash: &str,
    order_file: Option<&str>,
    order_file_sha256: Option<&str>,
    five_l_carrier: Option<LinearCarrierReport>,
    linear_loop_carrier: Option<LinearCarrierReport>,
    subject: &str,
    requested_source_columns: usize,
    source_columns: usize,
    exact_nnz: u128,
    column_generation_seconds: f64,
    progress: Vec<ProgressPoint>,
    started: Instant,
    states: &[State],
    reason: String,
) -> Result<()> {
    let sketches = states
        .iter()
        .map(|state| {
            let pivot_columns = state.basis.pivot_columns().to_vec();
            AbortSketchReport {
                sketch: state.spec.clone(),
                rank_a: state.basis.rank(),
                pivot_columns_u64_le_sha256: sha256_u64_le(&pivot_columns),
                pivot_columns,
                pivot_buckets: state
                    .basis
                    .pivot_rows()
                    .iter()
                    .map(|&row| row as u32)
                    .collect(),
                matrix_allocation_seconds: state.matrix_allocation_seconds,
                sketch_seconds: state.sketch_seconds,
                reducer_seconds: state.reducer_seconds,
                real_entry_visits_numerator: state.real_entry_visits_numerator,
                source_columns_denominator: source_columns,
                max_basis_storage_bytes: state.max_basis_storage_bytes,
                reducer_metrics: state.basis.metrics().clone(),
            }
        })
        .collect();
    let report = AbortReport {
        schema: "max11-streamrank-abort-v1",
        result: "ABORTED_GATE",
        abort_reason: reason,
        command: args.invocation.clone(),
        input: config.input.display().to_string(),
        input_sha256: input_hash.to_owned(),
        order_file: order_file.map(str::to_owned),
        order_file_sha256: order_file_sha256.map(str::to_owned),
        five_l_carrier,
        linear_loop_carrier,
        subject: subject.to_owned(),
        n: config.n,
        branch_edge_occurrences: config.branch_edges,
        modulus: config.prime,
        buckets: config.buckets,
        batch_size: config.batch_size,
        gemm_block: config.block_size,
        rank_panel: config.panel_size,
        threads: config.threads,
        backend: config.backend.clone(),
        requested_source_column_count: requested_source_columns,
        source_column_count: source_columns,
        source_columns_denominator: source_columns,
        exact_real_nnz_numerator: exact_nnz,
        column_generation_seconds,
        progress,
        wall_seconds: started.elapsed().as_secs_f64(),
        current_rss_kib: current_rss_kib(),
        max_rss_kib: max_rss_kib(),
        sketches,
        no_claim: "This is a resource-gated partial modular sketch over the named processed prefix. It does not test the unprocessed columns, exact rational consistency, or unrestricted two-hidden-layer representability.",
    };
    write_json(&config.output, &report)?;
    eprintln!(
        "STREAMRANK_ABORTED columns={} ranks={:?} reason={}",
        source_columns,
        states
            .iter()
            .map(|state| state.basis.rank())
            .collect::<Vec<_>>(),
        report.abort_reason
    );
    Ok(())
}

struct SourceSummary {
    subject: String,
    input_hash: String,
    order_file: Option<String>,
    order_file_sha256: Option<String>,
    five_l_carrier: Option<LinearCarrierReport>,
    linear_loop_carrier: Option<LinearCarrierReport>,
    source_columns: usize,
    exact_nnz: u128,
    column_generation_seconds: f64,
    progress: Vec<ProgressPoint>,
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
        order_file,
        order_file_sha256,
        five_l_carrier,
        linear_loop_carrier,
        source_columns,
        exact_nnz,
        column_generation_seconds,
        progress,
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
        let target_original = target.clone();
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
        let left_separator = if outside {
            let free_row = target
                .iter()
                .position(|&value| value != 0)
                .context("nonmember residual has no nonzero row")?;
            let vector = state.basis.left_separator(free_row)?;
            let dot_target = state.basis.dot_mod(&vector, &target_original)?;
            ensure!(dot_target != 0, "separator does not separate the target");
            Some(SeparatorReport {
                encoding: "sparse-bucket-residues-v1",
                length: config.buckets,
                entries: vector
                    .into_iter()
                    .enumerate()
                    .filter(|(_, residue)| *residue != 0)
                    .map(|(bucket, residue)| BucketResidue {
                        bucket: bucket as u32,
                        residue,
                    })
                    .collect(),
                dot_target_mod_prime: dot_target,
                verified_basis_columns_denominator: rank_a,
            })
        } else {
            None
        };
        let pivot_columns = state.basis.pivot_columns().to_vec();
        sketches.push(SketchReport {
            sketch: state.spec,
            rank_a,
            rank_augmented,
            saturated,
            verdict: verdict.to_owned(),
            pivot_columns_u64_le_sha256: sha256_u64_le(&pivot_columns),
            pivot_columns,
            pivot_buckets: state
                .basis
                .pivot_rows()
                .iter()
                .map(|&row| row as u32)
                .collect(),
            target_sketch_nonzero: target_original
                .into_iter()
                .enumerate()
                .filter(|(_, residue)| *residue != 0)
                .map(|(bucket, residue)| BucketResidue {
                    bucket: bucket as u32,
                    residue,
                })
                .collect(),
            left_separator,
            matrix_allocation_seconds: state.matrix_allocation_seconds,
            sketch_seconds: state.sketch_seconds,
            reducer_seconds: state.reducer_seconds,
            real_entry_visits_numerator: state.real_entry_visits_numerator,
            source_columns_denominator: source_columns,
            max_basis_storage_bytes: state.max_basis_storage_bytes,
            reducer_metrics: state.basis.metrics().clone(),
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
        order_file,
        order_file_sha256,
        five_l_carrier,
        linear_loop_carrier,
        subject,
        n: config.n,
        branch_edge_occurrences: config.branch_edges,
        modulus: config.prime,
        buckets: config.buckets,
        batch_size: config.batch_size,
        gemm_block: config.block_size,
        rank_panel: config.panel_size,
        threads: config.threads,
        backend: config.backend.clone(),
        source_column_count: source_columns,
        source_columns_denominator: source_columns,
        exact_real_nnz_numerator: exact_nnz,
        column_generation_seconds,
        progress,
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
        no_claim: "Ranks and verdicts are over one or two named finite random row sketches modulo one named prime. MEMBER is not exact-Q consistency and no identity has been verified on every real row; NON_MEMBER concerns only the named finite column family and is not an unrestricted two-hidden-layer depth lower bound. Exact lifting or separation is delegated to tools/exactlift.",
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

#[derive(Clone, Copy, Default)]
struct PhaseSnapshot {
    sketch_s: f64,
    reducer_s: f64,
    gemm_s: f64,
    basis_update_s: f64,
}

fn phase_snapshot(states: &[State]) -> PhaseSnapshot {
    states
        .iter()
        .fold(PhaseSnapshot::default(), |mut total, state| {
            total.sketch_s += state.matrix_allocation_seconds + state.sketch_seconds;
            total.reducer_s += state.reducer_seconds;
            total.gemm_s += state.basis.metrics().gemm_seconds;
            total.basis_update_s += state.basis.metrics().basis_update_seconds;
            total
        })
}

fn batch_phases(
    before: PhaseSnapshot,
    after: PhaseSnapshot,
    generate_s: f64,
    io_s: f64,
    sparse_drop_s: f64,
) -> BatchPhaseTimes {
    let sketch_s = after.sketch_s - before.sketch_s;
    let reducer_s = after.reducer_s - before.reducer_s;
    let gemm_s = after.gemm_s - before.gemm_s;
    let basis_update_s = after.basis_update_s - before.basis_update_s;
    BatchPhaseTimes {
        generate_s,
        sketch_s,
        gemm_s,
        host_reduce_s: (reducer_s - gemm_s - basis_update_s).max(0.0),
        basis_update_s,
        io_s,
        sparse_drop_s,
    }
}

fn next_splitmix64(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9e37_79b9_7f4a_7c15);
    let mut value = *state;
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

fn command_sample_order(args: &Args) -> Result<()> {
    let population = args.usize("--population")?;
    let sample_size = args.usize("--sample-size")?;
    let output = args.path("--output")?;
    ensure!(
        (1..=population).contains(&sample_size),
        "sample size lies outside population"
    );
    let mut state = args.u64("--seed")?;
    let mut selected = BTreeSet::new();
    while selected.len() < sample_size {
        selected.insert((next_splitmix64(&mut state) % population as u64) as usize);
    }
    write_json(&output, &selected.into_iter().collect::<Vec<_>>())?;
    Ok(())
}

fn command_saved(args: &Args) -> Result<()> {
    let config = Config::from_args(args)?;
    ensure!(
        !config.include_five_l
            && !config.include_linear_carrier
            && config.abort_rank_above.is_none()
            && config.abort_rss_kib_above.is_none(),
        "carrier and resource-abort options are supported only by run-universe"
    );
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
        .map(|&seed| {
            State::new(
                seed,
                config.buckets,
                config.prime,
                config.block_size,
                config.panel_size,
                config.batch_size,
                &config.backend,
            )
        })
        .collect::<Result<_>>()?;
    let mut reader = open_reader(&config.input)?;
    let mut line = String::new();
    let mut source_index = 0u64;
    let mut selected = 0usize;
    let mut exact_nnz = 0u128;
    let mut column_generation_seconds = 0.0;
    let mut progress = Vec::new();
    let mut batch = Vec::with_capacity(config.batch_size);
    let mut batch_generate_s = 0.0;
    let mut batch_io_s = 0.0;
    loop {
        line.clear();
        let io_at = Instant::now();
        if reader.read_line(&mut line)? == 0 {
            break;
        }
        let template: SavedTemplate = serde_json::from_str(&line)
            .with_context(|| format!("decoding source record {source_index}"))?;
        batch_io_s += io_at.elapsed().as_secs_f64();
        let include = filter == "all" || is_union_spanning_tree(&template, config.n);
        if include {
            let generated_at = Instant::now();
            let column = saved_column(&template, config.n)?;
            let generated_s = generated_at.elapsed().as_secs_f64();
            column_generation_seconds += generated_s;
            batch_generate_s += generated_s;
            exact_nnz += (column.linear.iter().filter(|&&value| value != 0).count()
                + column.hinges.len()) as u128;
            batch.push((source_index, column));
            selected += 1;
            if batch.len() == config.batch_size {
                let phase_before = phase_snapshot(&states);
                process_batch(&mut states, &batch, config.prime)?;
                let phases = batch_phases(
                    phase_before,
                    phase_snapshot(&states),
                    batch_generate_s,
                    batch_io_s,
                    0.0,
                );
                batch.clear();
                let elapsed = started.elapsed().as_secs_f64();
                progress.push(ProgressPoint {
                    source_columns_processed: selected,
                    ranks: states.iter().map(|state| state.basis.rank()).collect(),
                    elapsed_seconds: elapsed,
                    cumulative_seconds_per_column: elapsed / selected as f64,
                    phases,
                });
                eprintln!(
                    "STREAMRANK_PROGRESS columns={selected} ranks={:?} seconds={:.3} generate_s={:.6} sketch_s={:.6} gemm_s={:.6} host_reduce_s={:.6} basis_update_s={:.6} io_s={:.6}",
                    states
                        .iter()
                        .map(|state| state.basis.rank())
                        .collect::<Vec<_>>(),
                    started.elapsed().as_secs_f64(),
                    phases.generate_s,
                    phases.sketch_s,
                    phases.gemm_s,
                    phases.host_reduce_s,
                    phases.basis_update_s,
                    phases.io_s,
                );
                batch_generate_s = 0.0;
                batch_io_s = 0.0;
            }
        }
        source_index += 1;
    }
    if !batch.is_empty() {
        let phase_before = phase_snapshot(&states);
        process_batch(&mut states, &batch, config.prime)?;
        let phases = batch_phases(
            phase_before,
            phase_snapshot(&states),
            batch_generate_s,
            batch_io_s,
            0.0,
        );
        let elapsed = started.elapsed().as_secs_f64();
        progress.push(ProgressPoint {
            source_columns_processed: selected,
            ranks: states.iter().map(|state| state.basis.rank()).collect(),
            elapsed_seconds: elapsed,
            cumulative_seconds_per_column: elapsed / selected as f64,
            phases,
        });
        eprintln!(
            "STREAMRANK_PROGRESS columns={selected} ranks={:?} seconds={:.3} generate_s={:.6} sketch_s={:.6} gemm_s={:.6} host_reduce_s={:.6} basis_update_s={:.6} io_s={:.6}",
            states
                .iter()
                .map(|state| state.basis.rank())
                .collect::<Vec<_>>(),
            started.elapsed().as_secs_f64(),
            phases.generate_s,
            phases.sketch_s,
            phases.gemm_s,
            phases.host_reduce_s,
            phases.basis_update_s,
            phases.io_s,
        );
    }
    finish_run(
        args,
        config,
        SourceSummary {
            subject: format!("saved-system:{filter}"),
            input_hash,
            order_file: None,
            order_file_sha256: None,
            five_l_carrier: None,
            linear_loop_carrier: None,
            source_columns: selected,
            exact_nnz,
            column_generation_seconds,
            progress,
            started,
        },
        states,
    )
}

struct PreparedUniverseBatch {
    stop: usize,
    indices: Vec<u64>,
    matrices: Vec<Vec<u32>>,
    matrix_allocation_s: Vec<f64>,
    sketch_s: Vec<f64>,
    generate_s: f64,
    sparse_drop_s: f64,
    exact_nnz: u128,
}

fn sketch_columns_parallel(
    spec: &SketchSpec,
    columns: &[SparseColumn],
    prime: u32,
    matrix: &mut [u32],
) {
    debug_assert_eq!(matrix.len(), spec.buckets * columns.len());
    matrix
        .par_chunks_mut(spec.buckets)
        .zip(columns.par_iter())
        .for_each(|(output, column)| spec.sketch_column(column, prime, output));
}

#[allow(clippy::too_many_arguments)]
fn prepare_universe_batch(
    universe: &Universe,
    order: &[usize],
    specs: &[SketchSpec],
    prime: u32,
    n: usize,
    branch_edges: usize,
    generation_chunk: usize,
    batch_start: usize,
    batch_stop: usize,
) -> Result<PreparedUniverseBatch> {
    let columns = batch_stop - batch_start;
    let indices = order[batch_start..batch_stop]
        .iter()
        .map(|&index| index as u64)
        .collect();
    let mut matrices = Vec::with_capacity(specs.len());
    let mut matrix_allocation_s = Vec::with_capacity(specs.len());
    for spec in specs {
        let allocated_at = Instant::now();
        matrices.push(vec![0u32; spec.buckets * columns]);
        matrix_allocation_s.push(allocated_at.elapsed().as_secs_f64());
    }
    let mut sketch_s = vec![0.0; specs.len()];
    let mut generate_s = 0.0;
    let mut sparse_drop_s = 0.0;
    let mut exact_nnz = 0u128;
    for chunk_start in (0..columns).step_by(generation_chunk) {
        let chunk_stop = (chunk_start + generation_chunk).min(columns);
        let generated_at = Instant::now();
        let generated: Vec<Result<SparseColumn>> = order
            [batch_start + chunk_start..batch_start + chunk_stop]
            .par_iter()
            .map(|&record_index| generate_column(&universe.records[record_index], n, branch_edges))
            .collect();
        let generated: Vec<SparseColumn> = generated.into_iter().collect::<Result<_>>()?;
        generate_s += generated_at.elapsed().as_secs_f64();
        exact_nnz += generated
            .iter()
            .map(|column| {
                column.linear.iter().filter(|&&value| value != 0).count() + column.hinges.len()
            })
            .sum::<usize>() as u128;
        for (state_index, spec) in specs.iter().enumerate() {
            let sketched_at = Instant::now();
            let buckets = spec.buckets;
            sketch_columns_parallel(
                spec,
                &generated,
                prime,
                &mut matrices[state_index][chunk_start * buckets..chunk_stop * buckets],
            );
            sketch_s[state_index] += sketched_at.elapsed().as_secs_f64();
        }
        let dropped_at = Instant::now();
        generated.into_par_iter().for_each(drop);
        sparse_drop_s += dropped_at.elapsed().as_secs_f64();
    }
    Ok(PreparedUniverseBatch {
        stop: batch_stop,
        indices,
        matrices,
        matrix_allocation_s,
        sketch_s,
        generate_s,
        sparse_drop_s,
        exact_nnz,
    })
}

fn command_universe(args: &Args) -> Result<()> {
    let config = Config::from_args(args)?;
    ensure!(
        !(config.include_five_l && config.include_linear_carrier),
        "--include-five-l and --include-linear-carrier are mutually exclusive"
    );
    if config.include_five_l {
        ensure!(
            config.branch_edges == 5,
            "--include-five-l requires branch size 5"
        );
    }
    set_blas_threads(config.threads)?;
    let input_hash = sha256_path(&config.input)?;
    let universe: Universe = serde_json::from_reader(open_reader(&config.input)?)?;
    ensure!(
        universe.n == config.n && universe.branch_edge_occurrences == config.branch_edges,
        "universe/config dimensions differ"
    );
    ensure!(universe.loopless, "only loopless universes are supported");
    let (order, mut subject, order_file, order_file_sha256) =
        if let Some(path) = args.values.get("--order-file").map(PathBuf::from) {
            ensure!(
                !args.values.contains_key("--start") && !args.values.contains_key("--limit"),
                "--order-file cannot be combined with --start/--limit"
            );
            let hash = sha256_path(&path)?;
            let order: Vec<usize> = serde_json::from_reader(open_reader(&path)?)
                .with_context(|| format!("decoding order file {}", path.display()))?;
            ensure!(!order.is_empty(), "order file is empty");
            ensure!(
                order.iter().all(|&index| index < universe.records.len()),
                "order file contains an out-of-range record index"
            );
            ensure!(
                order.iter().copied().collect::<HashSet<_>>().len() == order.len(),
                "order file contains duplicate record indices"
            );
            (
                order,
                format!("colgen-universe-order:{}", path.display()),
                Some(path.display().to_string()),
                Some(hash),
            )
        } else {
            let start = args.usize_or("--start", 0)?;
            let limit = args.usize_or("--limit", universe.records.len().saturating_sub(start))?;
            let stop = start.checked_add(limit).context("range overflow")?;
            ensure!(
                start < stop && stop <= universe.records.len(),
                "range outside universe"
            );
            (
                (start..stop).collect(),
                format!("colgen-universe-range:[{start},{stop})"),
                None,
                None,
            )
        };
    let limit = order.len();
    let requested_source_columns =
        limit + usize::from(config.include_five_l || config.include_linear_carrier);
    let started = Instant::now();
    let mut states: Vec<State> = config
        .seeds
        .iter()
        .map(|&seed| {
            State::new(
                seed,
                config.buckets,
                config.prime,
                config.block_size,
                config.panel_size,
                config.batch_size,
                &config.backend,
            )
        })
        .collect::<Result<_>>()?;
    let mut exact_nnz = 0u128;
    let mut column_generation_seconds = 0.0;
    let mut progress = Vec::new();
    let specs = states
        .iter()
        .map(|state| state.spec.clone())
        .collect::<Vec<_>>();
    let generation_chunk = config.threads * 2;
    let abort = thread::scope(|scope| -> Result<Option<String>> {
        let (sender, receiver) = sync_channel::<Result<PreparedUniverseBatch>>(1);
        let producer_universe = &universe;
        let producer_order = &order;
        let producer_specs = &specs;
        let batch_size = config.batch_size;
        let prime = config.prime;
        let n = config.n;
        let branch_edges = config.branch_edges;
        scope.spawn(move || {
            for batch_start in (0..limit).step_by(batch_size) {
                let batch_stop = (batch_start + batch_size).min(limit);
                let prepared = prepare_universe_batch(
                    producer_universe,
                    producer_order,
                    producer_specs,
                    prime,
                    n,
                    branch_edges,
                    generation_chunk,
                    batch_start,
                    batch_stop,
                );
                let failed = prepared.is_err();
                if sender.send(prepared).is_err() || failed {
                    break;
                }
            }
        });

        let mut abort = None;
        for prepared in &receiver {
            let mut prepared = match prepared {
                Ok(value) => value,
                Err(error) => {
                    drop(receiver);
                    return Err(error);
                }
            };
            let phase_before = phase_snapshot(&states);
            column_generation_seconds += prepared.generate_s;
            exact_nnz += prepared.exact_nnz;
            for (state_index, (state, matrix)) in
                states.iter_mut().zip(&mut prepared.matrices).enumerate()
            {
                state.matrix_allocation_seconds += prepared.matrix_allocation_s[state_index];
                state.sketch_seconds += prepared.sketch_s[state_index];
                state.real_entry_visits_numerator += prepared.exact_nnz;
                state.process_sketched(matrix, &prepared.indices)?;
            }
            let phases = batch_phases(
                phase_before,
                phase_snapshot(&states),
                prepared.generate_s,
                0.0,
                prepared.sparse_drop_s,
            );
            let elapsed = started.elapsed().as_secs_f64();
            progress.push(ProgressPoint {
                source_columns_processed: prepared.stop,
                ranks: states.iter().map(|state| state.basis.rank()).collect(),
                elapsed_seconds: elapsed,
                cumulative_seconds_per_column: elapsed / prepared.stop as f64,
                phases,
            });
            eprintln!(
                "STREAMRANK_PROGRESS columns={}/{} ranks={:?} seconds={:.3} generate_s={:.6} sketch_s={:.6} gemm_s={:.6} host_reduce_s={:.6} basis_update_s={:.6} io_s={:.6}",
                prepared.stop,
                limit,
                states
                    .iter()
                    .map(|state| state.basis.rank())
                    .collect::<Vec<_>>(),
                started.elapsed().as_secs_f64(),
                phases.generate_s,
                phases.sketch_s,
                phases.gemm_s,
                phases.host_reduce_s,
                phases.basis_update_s,
                phases.io_s,
            );
            if let Some(reason) = abort_reason(&config, &states) {
                abort = Some(reason);
                break;
            }
        }
        drop(receiver);
        Ok(abort)
    })?;
    if let Some(reason) = abort {
        let source_columns = progress
            .last()
            .map(|point| point.source_columns_processed)
            .unwrap_or(0);
        return finish_abort(
            args,
            &config,
            &input_hash,
            order_file.as_deref(),
            order_file_sha256.as_deref(),
            None,
            None,
            &subject,
            requested_source_columns,
            source_columns,
            exact_nnz,
            column_generation_seconds,
            progress,
            started,
            &states,
            reason,
        );
    }
    let mut five_l_carrier = None;
    let mut linear_loop_carrier = None;
    let mut source_columns = limit;
    if config.include_five_l {
        let phase_before = phase_snapshot(&states);
        let generated_at = Instant::now();
        let (descriptor, column) =
            linear_carrier(config.n, config.branch_edges, universe.records.len() as u64)?;
        let generated_s = generated_at.elapsed().as_secs_f64();
        column_generation_seconds += generated_s;
        exact_nnz += column.linear.iter().filter(|&&value| value != 0).count() as u128;
        process_batch(
            &mut states,
            &[(descriptor.source_index, column)],
            config.prime,
        )?;
        let phases = batch_phases(phase_before, phase_snapshot(&states), generated_s, 0.0, 0.0);
        five_l_carrier = Some(descriptor);
        source_columns += 1;
        subject.push_str("+5L");
        let elapsed = started.elapsed().as_secs_f64();
        progress.push(ProgressPoint {
            source_columns_processed: source_columns,
            ranks: states.iter().map(|state| state.basis.rank()).collect(),
            elapsed_seconds: elapsed,
            cumulative_seconds_per_column: elapsed / source_columns as f64,
            phases,
        });
        eprintln!(
            "STREAMRANK_PROGRESS columns={}/{} ranks={:?} seconds={:.3} generate_s={:.6} sketch_s={:.6} gemm_s={:.6} host_reduce_s={:.6} basis_update_s={:.6} io_s={:.6}",
            source_columns,
            requested_source_columns,
            states
                .iter()
                .map(|state| state.basis.rank())
                .collect::<Vec<_>>(),
            started.elapsed().as_secs_f64(),
            phases.generate_s,
            phases.sketch_s,
            phases.gemm_s,
            phases.host_reduce_s,
            phases.basis_update_s,
            phases.io_s,
        );
        if let Some(reason) = abort_reason(&config, &states) {
            return finish_abort(
                args,
                &config,
                &input_hash,
                order_file.as_deref(),
                order_file_sha256.as_deref(),
                five_l_carrier,
                linear_loop_carrier,
                &subject,
                requested_source_columns,
                source_columns,
                exact_nnz,
                column_generation_seconds,
                progress,
                started,
                &states,
                reason,
            );
        }
    } else if config.include_linear_carrier {
        let phase_before = phase_snapshot(&states);
        let generated_at = Instant::now();
        let (descriptor, column) =
            linear_carrier(config.n, config.branch_edges, universe.records.len() as u64)?;
        let generated_s = generated_at.elapsed().as_secs_f64();
        column_generation_seconds += generated_s;
        exact_nnz += column.linear.iter().filter(|&&value| value != 0).count() as u128;
        process_batch(
            &mut states,
            &[(descriptor.source_index, column)],
            config.prime,
        )?;
        let phases = batch_phases(phase_before, phase_snapshot(&states), generated_s, 0.0, 0.0);
        subject.push_str(&format!("+{}", descriptor.label));
        linear_loop_carrier = Some(descriptor);
        source_columns += 1;
        let elapsed = started.elapsed().as_secs_f64();
        progress.push(ProgressPoint {
            source_columns_processed: source_columns,
            ranks: states.iter().map(|state| state.basis.rank()).collect(),
            elapsed_seconds: elapsed,
            cumulative_seconds_per_column: elapsed / source_columns as f64,
            phases,
        });
        eprintln!(
            "STREAMRANK_PROGRESS columns={}/{} ranks={:?} seconds={:.3} generate_s={:.6} sketch_s={:.6} gemm_s={:.6} host_reduce_s={:.6} basis_update_s={:.6} io_s={:.6}",
            source_columns,
            requested_source_columns,
            states
                .iter()
                .map(|state| state.basis.rank())
                .collect::<Vec<_>>(),
            started.elapsed().as_secs_f64(),
            phases.generate_s,
            phases.sketch_s,
            phases.gemm_s,
            phases.host_reduce_s,
            phases.basis_update_s,
            phases.io_s,
        );
        if let Some(reason) = abort_reason(&config, &states) {
            return finish_abort(
                args,
                &config,
                &input_hash,
                order_file.as_deref(),
                order_file_sha256.as_deref(),
                five_l_carrier,
                linear_loop_carrier,
                &subject,
                requested_source_columns,
                source_columns,
                exact_nnz,
                column_generation_seconds,
                progress,
                started,
                &states,
                reason,
            );
        }
    }
    finish_run(
        args,
        config,
        SourceSummary {
            subject,
            input_hash,
            order_file,
            order_file_sha256,
            five_l_carrier,
            linear_loop_carrier,
            source_columns,
            exact_nnz,
            column_generation_seconds,
            progress,
            started,
        },
        states,
    )
}

fn usage() -> &'static str {
    "usage:\n  max11-streamrank run-saved --input FILE.jsonl[.gz] --n N --branch-edges K --filter all|union-trees --modulus P --buckets M --seeds U64[,U64] --batch-size B --gemm-block Q [--rank-panel W] [--backend cpu|cuda] --threads T --output REPORT.json [--expected-columns C --expected-rank R --expected-aug-rank R2 --expected-verdict MEMBER|NON_MEMBER|SATURATED]\n  max11-streamrank run-universe --input UNIVERSE.json[.gz] --n N --branch-edges K --modulus P --buckets M --seeds U64[,U64] --batch-size B --gemm-block Q [--rank-panel W] [--backend cpu|cuda] --threads T --output REPORT.json [--order-file INDICES.json | --start I --limit L] [--include-five-l true | --include-linear-carrier true] [--abort-rank-above R] [--abort-rss-kib-above KIB] [expected arguments]\n  max11-streamrank sample-order --population N --sample-size S --seed U64 --threads 1 --output INDICES.json"
}

fn main() -> Result<()> {
    let args = Args::parse().with_context(usage)?;
    rayon::ThreadPoolBuilder::new()
        .num_threads(args.usize("--threads")?)
        .build_global()?;
    match args.command.as_str() {
        "run-saved" => command_saved(&args),
        "run-universe" => command_universe(&args),
        "sample-order" => command_sample_order(&args),
        other => bail!("unknown command {other}\n{}", usage()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn batch_phase_subtraction_is_explicit_and_nonnegative() {
        let before = PhaseSnapshot {
            sketch_s: 2.0,
            reducer_s: 3.0,
            gemm_s: 0.25,
            basis_update_s: 0.5,
        };
        let after = PhaseSnapshot {
            sketch_s: 7.0,
            reducer_s: 13.0,
            gemm_s: 2.25,
            basis_update_s: 3.5,
        };
        let phases = batch_phases(before, after, 11.0, 0.75, 0.125);
        assert_eq!(phases.generate_s, 11.0);
        assert_eq!(phases.sketch_s, 5.0);
        assert_eq!(phases.gemm_s, 2.0);
        assert_eq!(phases.basis_update_s, 3.0);
        assert_eq!(phases.host_reduce_s, 5.0);
        assert_eq!(phases.io_s, 0.75);
        assert_eq!(phases.sparse_drop_s, 0.125);
    }

    #[test]
    fn parallel_sketch_preserves_serial_column_order() {
        let spec = SketchSpec::new(2026090201, 31).unwrap();
        let columns = vec![
            SparseColumn {
                linear: vec![1, 0, -2],
                hinges: Default::default(),
            },
            SparseColumn {
                linear: vec![0, 3, 1],
                hinges: Default::default(),
            },
            SparseColumn {
                linear: vec![-4, 2, 0],
                hinges: Default::default(),
            },
        ];
        let mut serial = vec![0u32; spec.buckets * columns.len()];
        for (output, column) in serial.chunks_mut(spec.buckets).zip(&columns) {
            spec.sketch_column(column, 1_000_003, output);
        }
        let mut parallel = vec![0u32; serial.len()];
        sketch_columns_parallel(&spec, &columns, 1_000_003, &mut parallel);
        assert_eq!(parallel, serial);
    }

    #[test]
    fn common_loop_carriers_are_exact_all_ones_columns() {
        let (descriptor, column) = linear_carrier(11, 5, 754_017).unwrap();
        assert_eq!(descriptor.source_index, 754_017);
        assert_eq!(descriptor.label, "5L");
        assert_eq!(
            descriptor.exact_linear_coefficient_each_of_n_coordinates,
            18_144_000
        );
        assert_eq!(column.linear, vec![18_144_000; 11]);
        assert!(column.hinges.is_empty());

        let (descriptor, column) = linear_carrier(11, 4, 18_000).unwrap();
        assert_eq!(descriptor.label, "4L");
        assert_eq!(
            descriptor.exact_linear_coefficient_each_of_n_coordinates,
            14_515_200
        );
        assert_eq!(column.linear, vec![14_515_200; 11]);
        assert!(column.hinges.is_empty());
    }
}
