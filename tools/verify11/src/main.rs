use anyhow::{Context, Result, bail, ensure};
use max11_verify11::{
    Analysis, Certificate, Term, analyze_certificate, mutate_coefficient, mutate_endpoint,
};
use serde::Serialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{HashMap, HashSet};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};

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
            .context("missing command (verify, analyze, sample, mutate-coefficient, mutate-endpoint, or generate-synthetic)")?
            .clone();
        let known_switches = ["--literal-check", "--loopless"];
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
                    .with_context(|| format!("missing value for {flag}"))?;
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

    fn required_path(&self, flag: &str) -> Result<PathBuf> {
        self.values
            .get(flag)
            .map(PathBuf::from)
            .with_context(|| format!("required argument {flag} missing"))
    }

    fn required_usize(&self, flag: &str) -> Result<usize> {
        self.values
            .get(flag)
            .with_context(|| format!("required argument {flag} missing"))?
            .parse()
            .with_context(|| format!("invalid integer for {flag}"))
    }

    fn u64_or(&self, flag: &str, fallback: u64) -> Result<u64> {
        self.values
            .get(flag)
            .map(|value| {
                value
                    .parse()
                    .with_context(|| format!("invalid integer for {flag}"))
            })
            .transpose()
            .map(|value| value.unwrap_or(fallback))
    }

    fn usize_or(&self, flag: &str, fallback: usize) -> Result<usize> {
        self.values
            .get(flag)
            .map(|value| {
                value
                    .parse()
                    .with_context(|| format!("invalid integer for {flag}"))
            })
            .transpose()
            .map(|value| value.unwrap_or(fallback))
    }

    fn has(&self, flag: &str) -> bool {
        self.switches.contains(flag)
    }
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

fn read_certificate(path: &Path) -> Result<Certificate> {
    serde_json::from_reader(BufReader::new(
        File::open(path).with_context(|| format!("opening {}", path.display()))?,
    ))
    .with_context(|| format!("decoding {}", path.display()))
}

fn create_writer(path: &Path) -> Result<BufWriter<File>> {
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let destination = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(path)
        .with_context(|| format!("refusing to overwrite {}", path.display()))?;
    Ok(BufWriter::new(destination))
}

fn write_json<T: Serialize>(path: &Path, value: &T) -> Result<()> {
    let mut writer = create_writer(path)?;
    serde_json::to_writer_pretty(&mut writer, value)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    Ok(())
}

#[derive(Serialize)]
struct VerificationReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    input: String,
    input_sha256: String,
    n: usize,
    terms_total: usize,
    terms_nonzero: usize,
    dp_columns_checked: usize,
    literal_dp_matches: usize,
    literal_dp_match_denominator: usize,
    permutations_per_literal_term: Option<u64>,
    threads: usize,
    coefficient_common_denominator: String,
    arithmetic: &'static str,
    primes: Vec<u64>,
    linear_rows: usize,
    bad_linear_rows: usize,
    hinge_rows_union: usize,
    bad_hinge_rows: usize,
    first_bad_linear: Option<max11_verify11::Residual>,
    first_bad_hinge: Option<max11_verify11::Residual>,
    emitted_hinge_entries: u64,
    compute_wall_seconds: f64,
    effective_wall_seconds_per_term: f64,
    projected_wall_seconds_5000_terms: f64,
    dp_worker_seconds: f64,
    literal_worker_seconds: f64,
    semantics: &'static str,
    no_claim: &'static str,
}

fn report_from_analysis(
    args: &Args,
    input: &Path,
    input_hash: String,
    threads: usize,
    analysis: Analysis,
) -> VerificationReport {
    let per_term = analysis.compute_wall_seconds / analysis.terms_total as f64;
    VerificationReport {
        schema: "max11-verify11-report-v1",
        result: if analysis.verified { "OK" } else { "FAIL" },
        command: args.invocation.clone(),
        input: input.display().to_string(),
        input_sha256: input_hash,
        n: analysis.n,
        terms_total: analysis.terms_total,
        terms_nonzero: analysis.nonzero_terms,
        dp_columns_checked: analysis.dp_columns_checked,
        literal_dp_matches: analysis.literal_dp_matches,
        literal_dp_match_denominator: if analysis.permutations_per_literal_term.is_some() {
            analysis.terms_total
        } else {
            0
        },
        permutations_per_literal_term: analysis.permutations_per_literal_term,
        threads,
        coefficient_common_denominator: analysis.coefficient_common_denominator,
        arithmetic: "exact integer accumulation after exact rational denominator clearing; i128 fast path with automatic BigInt promotion",
        primes: Vec::new(),
        linear_rows: analysis.linear_rows,
        bad_linear_rows: analysis.bad_linear_rows,
        hinge_rows_union: analysis.hinge_rows_union,
        bad_hinge_rows: analysis.bad_hinge_rows,
        first_bad_linear: analysis.first_bad_linear,
        first_bad_hinge: analysis.first_bad_hinge,
        emitted_hinge_entries: analysis.emitted_hinge_entries,
        compute_wall_seconds: analysis.compute_wall_seconds,
        effective_wall_seconds_per_term: per_term,
        projected_wall_seconds_5000_terms: per_term * 5000.0,
        dp_worker_seconds: analysis.dp_worker_seconds,
        literal_worker_seconds: analysis.literal_worker_seconds,
        semantics: "For each symmetrized term, base/other are the lexicographically sorted left/right ordered-cone forms; direction=other-base; directions nonpositive on the cone are dropped; retained directions are gcd-primitive; target linear form is x_n.",
        no_claim: "This checks one supplied finite exact certificate. It does not establish MAX11 membership unless that certificate is an exact positive witness, and no failed or synthetic input establishes nonmembership or any unrestricted depth lower bound.",
    }
}

fn command_analyze(args: &Args, require_ok: bool) -> Result<()> {
    let input = args.required_path("--certificate")?;
    let output = args.required_path("--output")?;
    let threads = args.usize_or("--threads", 1)?;
    let input_hash = sha256_path(&input)?;
    let certificate = read_certificate(&input)?;
    let analysis = analyze_certificate(&certificate, threads, args.has("--literal-check"))?;
    let verified = analysis.verified;
    let report = report_from_analysis(args, &input, input_hash, threads, analysis);
    write_json(&output, &report)?;
    eprintln!(
        "VERIFY11_{} terms={}/{} literal={}/{} seconds={:.6} output={}",
        report.result,
        report.dp_columns_checked,
        report.terms_total,
        report.literal_dp_matches,
        report.literal_dp_match_denominator,
        report.compute_wall_seconds,
        output.display()
    );
    if require_ok && !verified {
        bail!("certificate verification failed (report written)");
    }
    Ok(())
}

fn command_mutate(args: &Args, coefficient: bool) -> Result<()> {
    let input = args.required_path("--certificate")?;
    let output = args.required_path("--output")?;
    let mut certificate = read_certificate(&input)?;
    if coefficient {
        mutate_coefficient(&mut certificate)?;
    } else {
        mutate_endpoint(&mut certificate)?;
    }
    write_json(&output, &certificate)?;
    eprintln!(
        "VERIFY11_MUTANT kind={} output={}",
        if coefficient {
            "coefficient-plus-one"
        } else {
            "endpoint-change"
        },
        output.display()
    );
    Ok(())
}

#[derive(Clone, Copy)]
struct SplitMix64(u64);

impl SplitMix64 {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(0x9e3779b97f4a7c15);
        let mut value = self.0;
        value = (value ^ (value >> 30)).wrapping_mul(0xbf58476d1ce4e5b9);
        value = (value ^ (value >> 27)).wrapping_mul(0x94d049bb133111eb);
        value ^ (value >> 31)
    }

    fn below(&mut self, bound: usize) -> usize {
        (self.next() % bound as u64) as usize
    }
}

#[derive(Serialize)]
struct SampleMetadata {
    source: String,
    source_sha256: String,
    seed: u64,
    selected_terms: usize,
    source_terms: usize,
    selected_indices_zero_based: Vec<usize>,
}

#[derive(Serialize)]
struct SampledCertificate {
    n: usize,
    terms: Vec<Term>,
    #[serde(rename = "_sample")]
    sample: SampleMetadata,
}

fn command_sample(args: &Args) -> Result<()> {
    let input = args.required_path("--certificate")?;
    let output = args.required_path("--output")?;
    let selected_terms = args.required_usize("--terms")?;
    let seed = args.u64_or("--seed", 20260902)?;
    let input_hash = sha256_path(&input)?;
    let certificate = read_certificate(&input)?;
    ensure!(selected_terms > 0, "sample size must be positive");
    ensure!(
        selected_terms <= certificate.terms.len(),
        "sample size exceeds source term count"
    );
    let mut random = SplitMix64(seed);
    let mut indices: Vec<usize> = (0..certificate.terms.len()).collect();
    for position in 0..selected_terms {
        let swap = position + random.below(indices.len() - position);
        indices.swap(position, swap);
    }
    indices.truncate(selected_terms);
    indices.sort_unstable();
    let terms = indices
        .iter()
        .map(|index| certificate.terms[*index].clone())
        .collect();
    let source_terms = certificate.terms.len();
    let sampled = SampledCertificate {
        n: certificate.n,
        terms,
        sample: SampleMetadata {
            source: input.display().to_string(),
            source_sha256: input_hash,
            seed,
            selected_terms,
            source_terms,
            selected_indices_zero_based: indices,
        },
    };
    write_json(&output, &sampled)?;
    eprintln!(
        "VERIFY11_SAMPLE terms={selected_terms}/{source_terms} seed={seed} output={}",
        output.display()
    );
    Ok(())
}

fn synthetic_side(
    random: &mut SplitMix64,
    edges: &[[usize; 2]],
    branch_edges: usize,
) -> Vec<[usize; 2]> {
    (0..branch_edges)
        .map(|_| edges[random.below(edges.len())])
        .collect()
}

fn command_generate_synthetic(args: &Args) -> Result<()> {
    let output = args.required_path("--output")?;
    let n = args.required_usize("--n")?;
    let terms = args.required_usize("--terms")?;
    let branch_edges = args.required_usize("--branch-edges")?;
    let seed = args.u64_or("--seed", 20260902)?;
    ensure!((2..=16).contains(&n), "n must lie in 2..=16");
    ensure!(terms > 0, "synthetic term count must be positive");
    ensure!(branch_edges > 0, "synthetic branch size must be positive");
    let loopless = args.has("--loopless");
    let edges: Vec<[usize; 2]> = (1..=n)
        .flat_map(|first| {
            let start = if loopless { first + 1 } else { first };
            (start..=n).map(move |second| [first, second])
        })
        .collect();
    ensure!(!edges.is_empty(), "synthetic edge universe is empty");
    let mut random = SplitMix64(seed);
    let mut generated = Vec::with_capacity(terms);
    for index in 0..terms {
        let numerator = if index.is_multiple_of(2) { 1 } else { -1 };
        let denominator = 1 + index % 7;
        generated.push(Term {
            coefficient: Value::String(format!("{numerator}/{denominator}")),
            pair: vec![
                synthetic_side(&mut random, &edges, branch_edges),
                synthetic_side(&mut random, &edges, branch_edges),
            ],
        });
    }
    let certificate = Certificate {
        n,
        terms: generated,
    };
    write_json(&output, &certificate)?;
    eprintln!(
        "VERIFY11_SYNTHETIC n={n} terms={terms} branch_edges={branch_edges} loopless={loopless} seed={seed} output={}",
        output.display()
    );
    Ok(())
}

fn run() -> Result<()> {
    let args = Args::parse()?;
    match args.command.as_str() {
        "verify" => command_analyze(&args, true),
        "analyze" => command_analyze(&args, false),
        "sample" => command_sample(&args),
        "mutate-coefficient" => command_mutate(&args, true),
        "mutate-endpoint" => command_mutate(&args, false),
        "generate-synthetic" => command_generate_synthetic(&args),
        other => bail!("unknown command {other}"),
    }
}

fn main() {
    if let Err(error) = run() {
        eprintln!("VERIFY11_ERROR: {error:#}");
        std::process::exit(1);
    }
}
