use anyhow::{Context, Result, bail, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{
    CompiledDual, DualFile, SavedTemplate, SparseColumn, Universe, brute_force_column,
    generate_column, mutate_one_sign, record_from_branches, saved_column,
};
use rayon::prelude::*;
use rustc_hash::FxHashSet;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap, HashSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Debug)]
struct Args {
    command: String,
    values: HashMap<String, String>,
    switches: HashSet<String>,
    invocation: Vec<String>,
}

impl Args {
    fn parse() -> Result<Self> {
        let invocation: Vec<String> = env::args().collect();
        let mut iterator = invocation.iter().skip(1);
        let command = iterator
            .next()
            .ok_or_else(|| anyhow::anyhow!("missing command"))?
            .clone();
        let known_switches = ["--bruteforce", "--mutate-one-sign"];
        let mut values = HashMap::new();
        let mut switches = HashSet::new();
        while let Some(flag) = iterator.next() {
            ensure!(
                flag.starts_with("--"),
                "unexpected positional argument {flag}"
            );
            if known_switches.contains(&flag.as_str()) {
                ensure!(switches.insert(flag.clone()), "duplicate switch {flag}");
            } else {
                let value = iterator
                    .next()
                    .ok_or_else(|| anyhow::anyhow!("missing value for {flag}"))?;
                ensure!(!value.starts_with("--"), "missing value for {flag}");
                ensure!(
                    values.insert(flag.clone(), value.clone()).is_none(),
                    "duplicate argument {flag}"
                );
            }
        }
        Ok(Self {
            command,
            values,
            switches,
            invocation,
        })
    }

    fn required_path(&self, name: &str) -> Result<PathBuf> {
        self.values
            .get(name)
            .map(PathBuf::from)
            .ok_or_else(|| anyhow::anyhow!("required argument {name} missing"))
    }

    fn required_usize(&self, name: &str) -> Result<usize> {
        self.values
            .get(name)
            .ok_or_else(|| anyhow::anyhow!("required argument {name} missing"))?
            .parse()
            .with_context(|| format!("invalid integer for {name}"))
    }

    fn usize_or(&self, name: &str, fallback: usize) -> Result<usize> {
        self.values
            .get(name)
            .map(|value| {
                value
                    .parse()
                    .with_context(|| format!("invalid integer for {name}"))
            })
            .transpose()
            .map(|value| value.unwrap_or(fallback))
    }

    fn u64_or(&self, name: &str, fallback: u64) -> Result<u64> {
        self.values
            .get(name)
            .map(|value| {
                value
                    .parse()
                    .with_context(|| format!("invalid integer for {name}"))
            })
            .transpose()
            .map(|value| value.unwrap_or(fallback))
    }

    fn threads(&self) -> Result<usize> {
        let threads = self.usize_or("--threads", 1)?;
        ensure!((1..=16).contains(&threads), "threads must lie in 1..=16");
        Ok(threads)
    }

    fn bool_or(&self, name: &str, fallback: bool) -> Result<bool> {
        self.values
            .get(name)
            .map(|value| match value.as_str() {
                "true" => Ok(true),
                "false" => Ok(false),
                _ => bail!("{name} must be true or false"),
            })
            .transpose()
            .map(|value| value.unwrap_or(fallback))
    }

    fn has(&self, name: &str) -> bool {
        self.switches.contains(name)
    }
}

fn pool(threads: usize) -> Result<rayon::ThreadPool> {
    Ok(rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?)
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut source = File::open(path).with_context(|| format!("opening {}", path.display()))?;
    let mut digest = Sha256::new();
    let mut block = [0u8; 1 << 20];
    loop {
        let count = source.read(&mut block)?;
        if count == 0 {
            break;
        }
        digest.update(&block[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn open_reader(path: &Path) -> Result<Box<dyn BufRead>> {
    let source = File::open(path).with_context(|| format!("opening {}", path.display()))?;
    if path.extension().is_some_and(|extension| extension == "gz") {
        Ok(Box::new(BufReader::new(GzDecoder::new(BufReader::new(
            source,
        )))))
    } else {
        Ok(Box::new(BufReader::new(source)))
    }
}

fn load_json<T: for<'de> Deserialize<'de>>(path: &Path) -> Result<T> {
    serde_json::from_reader(open_reader(path)?)
        .with_context(|| format!("decoding {}", path.display()))
}

fn create_output(path: &Path) -> Result<BufWriter<File>> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let file = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .with_context(|| format!("refusing to overwrite output {}", path.display()))?;
    Ok(BufWriter::new(file))
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    let mut writer = create_output(path)?;
    serde_json::to_writer_pretty(&mut writer, value)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    Ok(())
}

fn validate_universe(universe: &Universe) -> Result<()> {
    ensure!(
        universe.loopless,
        "this generator currently refuses loop records"
    );
    ensure!((2..=16).contains(&universe.n), "universe n is unsupported");
    ensure!(
        universe
            .records
            .iter()
            .all(|record| record.active_vertices <= universe.n),
        "universe contains an out-of-range active vertex count"
    );
    Ok(())
}

#[derive(Serialize)]
struct TemplateValidationReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    input: String,
    input_sha256: String,
    n: usize,
    branch_edge_occurrences: usize,
    templates_checked: usize,
    exact_sparse_matches: usize,
    literal_permutation_matches: usize,
    literal_permutations_per_template: Option<u64>,
    threads: usize,
    wall_seconds: f64,
    convention_map: &'static str,
    no_claim: &'static str,
}

fn compare_columns(index: usize, expected: &SparseColumn, actual: &SparseColumn) -> Result<()> {
    if expected.linear != actual.linear {
        bail!(
            "template {index}: linear mismatch expected={:?} actual={:?}",
            expected.linear,
            actual.linear
        );
    }
    if expected.hinges != actual.hinges {
        let keys: BTreeSet<_> = expected.hinges.keys().chain(actual.hinges.keys()).collect();
        let first = keys
            .into_iter()
            .find(|key| expected.hinges.get(*key) != actual.hinges.get(*key));
        bail!(
            "template {index}: hinge mismatch expected_nnz={} actual_nnz={} first={:?}",
            expected.hinges.len(),
            actual.hinges.len(),
            first.map(|key| (key, expected.hinges.get(key), actual.hinges.get(key)))
        );
    }
    Ok(())
}

fn validate_template_batch(
    batch: Vec<(usize, SavedTemplate)>,
    n: usize,
    branch_edges: usize,
    literal: bool,
    mutate: bool,
    thread_pool: &rayon::ThreadPool,
) -> Result<(usize, usize)> {
    let results: Vec<Result<(usize, usize)>> = thread_pool.install(|| {
        batch
            .into_par_iter()
            .map(|(index, template)| {
                let expected = saved_column(&template, n)?;
                let mut record = record_from_branches(&template.a, &template.b, n)?;
                if mutate && record.signed_mass > 0 {
                    record = mutate_one_sign(&record)
                        .with_context(|| format!("template {index}: cannot plant sign mutant"))?;
                }
                let actual = generate_column(&record, n, branch_edges)
                    .with_context(|| format!("template {index}: generating column"))?;
                compare_columns(index, &expected, &actual)?;
                if literal {
                    let brute =
                        brute_force_column(&record, n, branch_edges).with_context(|| {
                            format!("template {index}: literal permutation control")
                        })?;
                    compare_columns(index, &brute, &actual)?;
                }
                Ok((1, usize::from(literal)))
            })
            .collect()
    });
    results
        .into_iter()
        .try_fold((0, 0), |(exact, brute), result| {
            let (one_exact, one_brute) = result?;
            Ok((exact + one_exact, brute + one_brute))
        })
}

fn command_validate_templates(args: &Args) -> Result<()> {
    let input = args.required_path("--input")?;
    let output = args.required_path("--output")?;
    let n = args.required_usize("--n")?;
    let branch_edges = args.required_usize("--branch-edges")?;
    let threads = args.threads()?;
    let literal = args.has("--bruteforce");
    let mutate = args.has("--mutate-one-sign");
    ensure!(
        !literal || n <= 7,
        "all-order literal controls are intentionally capped at n=7"
    );
    let input_hash = sha256_path(&input)?;
    let mut reader = open_reader(&input)?;
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    let mut line = String::new();
    let mut batch = Vec::with_capacity(threads * 2);
    let mut index = 0usize;
    let mut exact_matches = 0usize;
    let mut literal_matches = 0usize;
    loop {
        line.clear();
        let count = reader.read_line(&mut line)?;
        if count == 0 {
            break;
        }
        ensure!(
            !line.trim().is_empty(),
            "blank template line at index {index}"
        );
        let template: SavedTemplate =
            serde_json::from_str(&line).with_context(|| format!("decoding template {index}"))?;
        batch.push((index, template));
        index += 1;
        if batch.len() == threads * 2 {
            let (exact, brute) = validate_template_batch(
                std::mem::take(&mut batch),
                n,
                branch_edges,
                literal,
                mutate,
                &thread_pool,
            )?;
            exact_matches += exact;
            literal_matches += brute;
            if index.is_multiple_of(1000) {
                eprintln!(
                    "COLGEN_VALIDATE templates={index} seconds={:.3}",
                    started.elapsed().as_secs_f64()
                );
            }
        }
    }
    if !batch.is_empty() {
        let (exact, brute) =
            validate_template_batch(batch, n, branch_edges, literal, mutate, &thread_pool)?;
        exact_matches += exact;
        literal_matches += brute;
    }
    ensure!(index > 0, "template input was empty");
    ensure!(exact_matches == index, "exact template census mismatch");
    ensure!(
        !literal || literal_matches == index,
        "literal control census mismatch"
    );
    let report = TemplateValidationReport {
        schema: "max11-colgen-template-validation-v1",
        result: "PASS",
        command: args.invocation.clone(),
        input: input.display().to_string(),
        input_sha256: input_hash,
        n,
        branch_edge_occurrences: branch_edges,
        templates_checked: index,
        exact_sparse_matches: exact_matches,
        literal_permutation_matches: literal_matches,
        literal_permutations_per_template: literal.then(|| (1..=n as u64).product()),
        threads,
        wall_seconds: started.elapsed().as_secs_f64(),
        convention_map: "W=B-A. Python's lexicographically smaller back-degree word is the fixed symmetrized A-branch base plus w on exactly the permutations whose first nonzero w entry is negative; ReLU(-z)=ReLU(z)-z. Primitive retained hinge directions and gcd multiplicities are then identical.",
        no_claim: "Exact column agreement for this finite template file only; no MAX11 membership, rational identity, ansatz completeness, or unrestricted two-hidden-layer result.",
    };
    write_json(&output, &report)?;
    eprintln!(
        "COLGEN_VALIDATE_PASS templates={index} output={}",
        output.display()
    );
    Ok(())
}

fn splitmix64(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9e3779b97f4a7c15);
    let mut value = *state;
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
    value ^ (value >> 31)
}

fn sampled_indices(total: usize, sample_size: usize, seed: u64) -> Result<Vec<usize>> {
    ensure!(
        (1..=total).contains(&sample_size),
        "sample size lies outside subject"
    );
    let mut state = seed;
    let mut selected = BTreeSet::new();
    while selected.len() < sample_size {
        selected.insert((splitmix64(&mut state) % total as u64) as usize);
    }
    Ok(selected.into_iter().collect())
}

fn quantile(sorted: &[usize], numerator: usize, denominator: usize) -> usize {
    let index = (sorted.len() - 1) * numerator / denominator;
    sorted[index]
}

#[derive(Serialize)]
struct BenchmarkReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    universe: String,
    universe_sha256: String,
    universe_schema: String,
    universe_records: usize,
    sample_method: &'static str,
    sample_seed: u64,
    sample_size_denominator: usize,
    sampled_indices_sha256_u64_le: String,
    threads: usize,
    wall_seconds: f64,
    records_per_second: f64,
    seconds_per_column: f64,
    retained_hinges_min: usize,
    retained_hinges_p50: usize,
    retained_hinges_p90: usize,
    retained_hinges_p99: usize,
    retained_hinges_max: usize,
    sampled_total_nnz: u64,
    mean_nnz_numerator: u64,
    mean_nnz_denominator: usize,
    extrapolated_total_nnz_numerator: u128,
    extrapolated_total_nnz_denominator: usize,
    extrapolated_wall_seconds_on_six_threads: f64,
    no_claim: &'static str,
}

fn command_benchmark(args: &Args) -> Result<()> {
    let input = args.required_path("--universe")?;
    let output = args.required_path("--output")?;
    let threads = args.threads()?;
    let sample_size = args.usize_or("--sample-size", 1000)?;
    let seed = args.u64_or("--seed", 20_260_902)?;
    let input_hash = sha256_path(&input)?;
    let universe: Universe = load_json(&input)?;
    validate_universe(&universe)?;
    let indices = sampled_indices(universe.records.len(), sample_size, seed)?;
    let mut index_digest = Sha256::new();
    for &index in &indices {
        index_digest.update((index as u64).to_le_bytes());
    }
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    let columns: Vec<Result<usize>> = thread_pool.install(|| {
        indices
            .par_iter()
            .map(|&index| {
                generate_column(
                    &universe.records[index],
                    universe.n,
                    universe.branch_edge_occurrences,
                )
                .map(|column| column.hinges.len())
                .with_context(|| format!("benchmark record {index}"))
            })
            .collect()
    });
    let elapsed = started.elapsed().as_secs_f64();
    let mut counts: Vec<usize> = columns.into_iter().collect::<Result<_>>()?;
    counts.sort_unstable();
    let sampled_total: u64 = counts.iter().try_fold(0u64, |acc, &value| {
        acc.checked_add(value as u64)
            .ok_or_else(|| anyhow::anyhow!("sampled nnz overflow"))
    })?;
    let report = BenchmarkReport {
        schema: "max11-colgen-benchmark-v1",
        result: "PASS",
        command: args.invocation.clone(),
        universe: input.display().to_string(),
        universe_sha256: input_hash,
        universe_schema: universe.schema,
        universe_records: universe.records.len(),
        sample_method: "without-replacement SplitMix64 indices, then sorted for stable subject access",
        sample_seed: seed,
        sample_size_denominator: sample_size,
        sampled_indices_sha256_u64_le: format!("{:x}", index_digest.finalize()),
        threads,
        wall_seconds: elapsed,
        records_per_second: sample_size as f64 / elapsed,
        seconds_per_column: elapsed * threads as f64 / sample_size as f64,
        retained_hinges_min: counts[0],
        retained_hinges_p50: quantile(&counts, 50, 100),
        retained_hinges_p90: quantile(&counts, 90, 100),
        retained_hinges_p99: quantile(&counts, 99, 100),
        retained_hinges_max: *counts.last().unwrap(),
        sampled_total_nnz: sampled_total,
        mean_nnz_numerator: sampled_total,
        mean_nnz_denominator: sample_size,
        extrapolated_total_nnz_numerator: sampled_total as u128 * universe.records.len() as u128,
        extrapolated_total_nnz_denominator: sample_size,
        extrapolated_wall_seconds_on_six_threads: elapsed * universe.records.len() as f64
            / sample_size as f64
            * threads as f64
            / 6.0,
        no_claim: "Timing and support-size measurements on the named deterministic sample only. Extrapolations are ratios with the stated denominator, not a completed census or a MAX11 span decision.",
    };
    write_json(&output, &report)?;
    eprintln!("COLGEN_BENCHMARK_PASS sample={sample_size} seconds={elapsed:.3}");
    Ok(())
}

#[derive(Serialize)]
struct ScanReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    universe: String,
    universe_sha256: String,
    universe_schema: String,
    universe_records_available: usize,
    scan_start_inclusive: usize,
    scan_stop_exclusive: usize,
    records_scanned_denominator: usize,
    complete_subject: bool,
    threads: usize,
    wall_seconds: f64,
    records_per_second: f64,
    total_nnz: u64,
    distinct_retained_hinge_directions: usize,
    retained_hinges_min: usize,
    retained_hinges_p50: usize,
    retained_hinges_p90: usize,
    retained_hinges_p99: usize,
    retained_hinges_max: usize,
    no_claim: &'static str,
}

fn command_scan(args: &Args) -> Result<()> {
    let input = args.required_path("--universe")?;
    let output = args.required_path("--output")?;
    let threads = args.threads()?;
    let input_hash = sha256_path(&input)?;
    let universe: Universe = load_json(&input)?;
    validate_universe(&universe)?;
    let start = args.usize_or("--start", 0)?;
    let limit = args.usize_or("--limit", universe.records.len().saturating_sub(start))?;
    let stop = start
        .checked_add(limit)
        .ok_or_else(|| anyhow::anyhow!("scan range overflow"))?;
    ensure!(
        start < stop && stop <= universe.records.len(),
        "scan range outside universe"
    );
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    let mut union: FxHashSet<Vec<i16>> = FxHashSet::default();
    let mut counts = Vec::with_capacity(limit);
    let mut total_nnz = 0u64;
    let batch_size = threads * 2;
    for batch_start in (start..stop).step_by(batch_size) {
        let batch_stop = (batch_start + batch_size).min(stop);
        let columns: Vec<Result<SparseColumn>> = thread_pool.install(|| {
            universe.records[batch_start..batch_stop]
                .par_iter()
                .enumerate()
                .map(|(offset, record)| {
                    generate_column(record, universe.n, universe.branch_edge_occurrences)
                        .with_context(|| format!("scan record {}", batch_start + offset))
                })
                .collect()
        });
        for result in columns {
            let column = result?;
            let nnz = column.hinges.len();
            total_nnz = total_nnz
                .checked_add(nnz as u64)
                .ok_or_else(|| anyhow::anyhow!("total nnz overflow"))?;
            counts.push(nnz);
            union.extend(column.hinges.into_keys());
        }
        let completed = batch_stop - start;
        if completed % 1000 < batch_size || batch_stop == stop {
            eprintln!(
                "COLGEN_SCAN records={completed}/{limit} union={} nnz={total_nnz} seconds={:.3}",
                union.len(),
                started.elapsed().as_secs_f64()
            );
        }
    }
    let elapsed = started.elapsed().as_secs_f64();
    counts.sort_unstable();
    let report = ScanReport {
        schema: "max11-colgen-support-scan-v1",
        result: "PASS",
        command: args.invocation.clone(),
        universe: input.display().to_string(),
        universe_sha256: input_hash,
        universe_schema: universe.schema,
        universe_records_available: universe.records.len(),
        scan_start_inclusive: start,
        scan_stop_exclusive: stop,
        records_scanned_denominator: limit,
        complete_subject: start == 0 && stop == universe.records.len(),
        threads,
        wall_seconds: elapsed,
        records_per_second: limit as f64 / elapsed,
        total_nnz,
        distinct_retained_hinge_directions: union.len(),
        retained_hinges_min: counts[0],
        retained_hinges_p50: quantile(&counts, 50, 100),
        retained_hinges_p90: quantile(&counts, 90, 100),
        retained_hinges_p99: quantile(&counts, 99, 100),
        retained_hinges_max: *counts.last().unwrap(),
        no_claim: "This is an exact support census only over the named finite serialized loopless signed-W subject and range. It is not a MAX11 membership result, rational identity, separator, ansatz completeness statement, or unrestricted depth lower bound.",
    };
    write_json(&output, &report)?;
    eprintln!(
        "COLGEN_SCAN_PASS records={limit} union={} nnz={total_nnz}",
        union.len()
    );
    Ok(())
}

#[derive(Deserialize)]
struct ExpectedField {
    label: String,
    modulus: u64,
    nonzero_price_count: usize,
    zero_price_count: usize,
    residue_vector_int64_le_sha256: String,
}

#[derive(Deserialize)]
struct ExpectedPriceReport {
    fields: Vec<ExpectedField>,
}

#[derive(Serialize)]
struct PriceFieldReport {
    label: String,
    modulus: u64,
    nonzero_price_count: usize,
    zero_price_count: usize,
    residue_vector_int64_le_sha256: String,
    expected_nonzero_price_count: usize,
    expected_zero_price_count: usize,
    expected_residue_vector_int64_le_sha256: String,
    exact_match: bool,
}

#[derive(Serialize)]
struct PriceValidationReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    universe: String,
    universe_sha256: String,
    dual: String,
    dual_sha256: String,
    expected_report: String,
    expected_report_sha256: String,
    records_checked_denominator: usize,
    threads: usize,
    wall_seconds: f64,
    records_per_second: f64,
    fields: Vec<PriceFieldReport>,
    no_claim: &'static str,
}

fn command_validate_prices(args: &Args) -> Result<()> {
    let universe_path = args.required_path("--universe")?;
    let dual_path = args.required_path("--dual")?;
    let expected_path = args.required_path("--expected-report")?;
    let output = args.required_path("--output")?;
    let threads = args.threads()?;
    let universe_hash = sha256_path(&universe_path)?;
    let dual_hash = sha256_path(&dual_path)?;
    let expected_hash = sha256_path(&expected_path)?;
    let universe: Universe = load_json(&universe_path)?;
    validate_universe(&universe)?;
    let dual_file: DualFile = load_json(&dual_path)?;
    ensure!(
        dual_file.n == universe.n
            && dual_file.branch_edge_occurrences == universe.branch_edge_occurrences,
        "dual and subject dimensions differ"
    );
    let dual = CompiledDual::new(dual_file)?;
    let expected: ExpectedPriceReport = load_json(&expected_path)?;
    ensure!(
        expected.fields.len() == dual.fields.len(),
        "expected field count differs"
    );
    for (actual, expected_field) in dual.fields.iter().zip(&expected.fields) {
        ensure!(
            actual.label == expected_field.label && actual.modulus == expected_field.modulus,
            "expected field identity differs"
        );
    }
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    let prices: Vec<Result<Vec<u64>>> = thread_pool.install(|| {
        universe
            .records
            .par_iter()
            .enumerate()
            .map(|(index, record)| {
                let column = generate_column(record, universe.n, universe.branch_edge_occurrences)
                    .with_context(|| format!("price validation record {index}"))?;
                Ok(dual.price(&column))
            })
            .collect()
    });
    let prices: Vec<Vec<u64>> = prices.into_iter().collect::<Result<_>>()?;
    let elapsed = started.elapsed().as_secs_f64();
    let mut fields = Vec::new();
    for (field_index, expected_field) in expected.fields.into_iter().enumerate() {
        let mut digest = Sha256::new();
        let mut nonzero = 0usize;
        for row in &prices {
            let residue = row[field_index];
            nonzero += usize::from(residue != 0);
            digest.update((residue as i64).to_le_bytes());
        }
        let vector_hash = format!("{:x}", digest.finalize());
        let zero = prices.len() - nonzero;
        let exact_match = nonzero == expected_field.nonzero_price_count
            && zero == expected_field.zero_price_count
            && vector_hash == expected_field.residue_vector_int64_le_sha256;
        fields.push(PriceFieldReport {
            label: expected_field.label,
            modulus: expected_field.modulus,
            nonzero_price_count: nonzero,
            zero_price_count: zero,
            residue_vector_int64_le_sha256: vector_hash,
            expected_nonzero_price_count: expected_field.nonzero_price_count,
            expected_zero_price_count: expected_field.zero_price_count,
            expected_residue_vector_int64_le_sha256: expected_field.residue_vector_int64_le_sha256,
            exact_match,
        });
    }
    ensure!(
        fields.iter().all(|field| field.exact_match),
        "frozen price vector mismatch"
    );
    let report = PriceValidationReport {
        schema: "max11-colgen-g0028-price-validation-v1",
        result: "PASS",
        command: args.invocation.clone(),
        universe: universe_path.display().to_string(),
        universe_sha256: universe_hash,
        dual: dual_path.display().to_string(),
        dual_sha256: dual_hash,
        expected_report: expected_path.display().to_string(),
        expected_report_sha256: expected_hash,
        records_checked_denominator: universe.records.len(),
        threads,
        wall_seconds: elapsed,
        records_per_second: universe.records.len() as f64 / elapsed,
        fields,
        no_claim: "Reproduction of two frozen modular scalar-price vectors for this finite registered record stream only. It is not exact-Q verification, a MAX11 identity, a span decision, or completeness for arbitrary two-hidden-layer networks.",
    };
    write_json(&output, &report)?;
    eprintln!(
        "COLGEN_PRICES_PASS records={} seconds={elapsed:.3}",
        universe.records.len()
    );
    Ok(())
}

fn write_binary_column(
    writer: &mut impl Write,
    column: &SparseColumn,
    record_index: usize,
    modulus: Option<u64>,
) -> Result<()> {
    let output = column.output(record_index, modulus)?;
    writer.write_all(&(record_index as u64).to_le_bytes())?;
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

fn five_l_column(n: usize, branch_edges: usize) -> Result<SparseColumn> {
    ensure!(branch_edges == 5, "--include-five-l requires branch size 5");
    let factorial = (1..n).try_fold(1i64, |product, value| {
        product
            .checked_mul(i64::try_from(value)?)
            .context("5L factorial overflow")
    })?;
    let coefficient = 5i64
        .checked_mul(factorial)
        .context("5L coefficient overflow")?;
    Ok(SparseColumn {
        linear: vec![coefficient; n],
        hinges: Default::default(),
    })
}

fn command_emit(args: &Args) -> Result<()> {
    let input = args.required_path("--universe")?;
    let output = args.required_path("--output")?;
    let format = args
        .values
        .get("--format")
        .map(String::as_str)
        .unwrap_or("jsonl");
    ensure!(
        ["jsonl", "binary"].contains(&format),
        "format must be jsonl or binary"
    );
    let threads = args.threads()?;
    let modulus: Option<u64> = args
        .values
        .get("--modulus")
        .map(|value| value.parse())
        .transpose()?;
    let include_five_l = args.bool_or("--include-five-l", false)?;
    let universe: Universe = load_json(&input)?;
    validate_universe(&universe)?;
    let order: Vec<usize> = if let Some(path) = args.values.get("--order-file").map(PathBuf::from) {
        ensure!(
            !args.values.contains_key("--start") && !args.values.contains_key("--limit"),
            "--order-file cannot be combined with --start/--limit"
        );
        let order: Vec<usize> = load_json(&path)?;
        ensure!(!order.is_empty(), "order file is empty");
        ensure!(
            order.iter().all(|&index| index < universe.records.len()),
            "order file contains an out-of-range universe index"
        );
        ensure!(
            order.iter().copied().collect::<HashSet<_>>().len() == order.len(),
            "order file contains duplicate universe indices"
        );
        order
    } else {
        let start = args.usize_or("--start", 0)?;
        let limit = args.usize_or("--limit", universe.records.len().saturating_sub(start))?;
        let stop = start
            .checked_add(limit)
            .ok_or_else(|| anyhow::anyhow!("emit range overflow"))?;
        ensure!(
            start < stop && stop <= universe.records.len(),
            "emit range outside universe"
        );
        (start..stop).collect()
    };
    let output_count = order.len() + usize::from(include_five_l);
    let mut writer = create_output(&output)?;
    if format == "binary" {
        writer.write_all(b"MCOLGEN1")?;
        writer.write_all(&(universe.n as u16).to_le_bytes())?;
        writer.write_all(&(universe.branch_edge_occurrences as u16).to_le_bytes())?;
        writer.write_all(&modulus.unwrap_or(0).to_le_bytes())?;
        writer.write_all(&(output_count as u64).to_le_bytes())?;
    }
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    let batch_size = threads * 2;
    for batch_start in (0..order.len()).step_by(batch_size) {
        let batch_stop = (batch_start + batch_size).min(order.len());
        let columns: Vec<Result<(usize, SparseColumn)>> = thread_pool.install(|| {
            order[batch_start..batch_stop]
                .par_iter()
                .map(|&index| {
                    Ok((
                        index,
                        generate_column(
                            &universe.records[index],
                            universe.n,
                            universe.branch_edge_occurrences,
                        )
                        .with_context(|| format!("emit record {index}"))?,
                    ))
                })
                .collect()
        });
        for result in columns {
            let (index, column) = result?;
            if format == "jsonl" {
                serde_json::to_writer(&mut writer, &column.output(index, modulus)?)?;
                writer.write_all(b"\n")?;
            } else {
                write_binary_column(&mut writer, &column, index, modulus)?;
            }
        }
    }
    if include_five_l {
        let source_index = universe.records.len();
        let column = five_l_column(universe.n, universe.branch_edge_occurrences)?;
        if format == "jsonl" {
            serde_json::to_writer(&mut writer, &column.output(source_index, modulus)?)?;
            writer.write_all(b"\n")?;
        } else {
            write_binary_column(&mut writer, &column, source_index, modulus)?;
        }
    }
    writer.flush()?;
    eprintln!(
        "COLGEN_EMIT_PASS records={output_count} seconds={:.3} output={}",
        started.elapsed().as_secs_f64(),
        output.display()
    );
    Ok(())
}

fn usage() -> &'static str {
    "usage:\n  max11-colgen validate-templates --input FILE.jsonl[.gz] --n N --branch-edges K --threads N --output REPORT.json [--bruteforce] [--mutate-one-sign]\n  max11-colgen validate-prices --universe FILE.json.gz --dual FILE.json --expected-report FILE.json --threads N --output REPORT.json\n  max11-colgen benchmark --universe FILE.json.gz --sample-size 1000 --seed N --threads N --output REPORT.json\n  max11-colgen scan-universe --universe FILE.json.gz --threads N --output REPORT.json [--start N --limit N]\n  max11-colgen emit-universe --universe FILE.json.gz --threads N --output FILE --format jsonl|binary [--modulus P] [--order-file INDICES.json | --start N --limit N] [--include-five-l true]"
}

fn main() -> Result<()> {
    let args = Args::parse().with_context(usage)?;
    match args.command.as_str() {
        "validate-templates" => command_validate_templates(&args),
        "validate-prices" => command_validate_prices(&args),
        "benchmark" => command_benchmark(&args),
        "scan-universe" => command_scan(&args),
        "emit-universe" => command_emit(&args),
        other => bail!("unknown command {other}\n{}", usage()),
    }
}
