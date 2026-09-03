use anyhow::{Context, Result, bail, ensure};
use flate2::read::GzDecoder;
use max11_colgen::{SignedRecord, SparseColumn};
use max11_colgen_loops::{
    base_atoms, brute_force_branches, generate_column, generate_column_diagonal_sign_mutant,
    generate_column_native, record_from_branches,
};
use rayon::prelude::*;
use rustc_hash::FxHashMap as HashMap;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::env;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

#[derive(Debug)]
struct Args {
    command: String,
    values: std::collections::HashMap<String, String>,
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
        let mut values = std::collections::HashMap::new();
        while let Some(flag) = iterator.next() {
            ensure!(
                flag.starts_with("--"),
                "unexpected positional argument {flag}"
            );
            let value = iterator
                .next()
                .ok_or_else(|| anyhow::anyhow!("missing value for {flag}"))?;
            ensure!(!value.starts_with("--"), "missing value for {flag}");
            ensure!(
                values.insert(flag.clone(), value.clone()).is_none(),
                "duplicate argument {flag}"
            );
        }
        Ok(Self {
            command,
            values,
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

    fn optional_usize(&self, name: &str) -> Result<Option<usize>> {
        self.values
            .get(name)
            .map(|value| {
                value
                    .parse()
                    .with_context(|| format!("invalid integer for {name}"))
            })
            .transpose()
    }

    fn threads(&self) -> Result<usize> {
        let threads = self.usize_or("--threads", 1)?;
        ensure!(
            (1..=4).contains(&threads),
            "threads must lie in 1..=4 for this shared-host bead"
        );
        Ok(threads)
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

fn load_records(path: &Path) -> Result<Vec<SignedRecord>> {
    let mut records = Vec::new();
    for (line_index, line) in open_reader(path)?.lines().enumerate() {
        let line =
            line.with_context(|| format!("reading {} line {}", path.display(), line_index + 1))?;
        if line.trim().is_empty() {
            continue;
        }
        let value: serde_json::Value = serde_json::from_str(&line)
            .with_context(|| format!("decoding {} line {}", path.display(), line_index + 1))?;
        if value.get("record_type").and_then(|item| item.as_str()) == Some("header") {
            continue;
        }
        records.push(serde_json::from_value(value)?);
    }
    ensure!(!records.is_empty(), "record input is empty");
    Ok(records)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Rational {
    numerator: i128,
    denominator: i128,
}

impl Rational {
    const ZERO: Self = Self {
        numerator: 0,
        denominator: 1,
    };

    fn parse(value: &str) -> Result<Self> {
        let (numerator, denominator) = match value.split_once('/') {
            Some((left, right)) => (left.parse()?, right.parse()?),
            None => (value.parse()?, 1),
        };
        Self::new(numerator, denominator)
    }

    fn new(mut numerator: i128, mut denominator: i128) -> Result<Self> {
        ensure!(denominator != 0, "zero rational denominator");
        if denominator < 0 {
            numerator = numerator
                .checked_neg()
                .ok_or_else(|| anyhow::anyhow!("rational sign overflow"))?;
            denominator = -denominator;
        }
        let divisor = gcd_i128(numerator, denominator);
        Ok(Self {
            numerator: numerator / divisor,
            denominator: denominator / divisor,
        })
    }

    fn add(self, other: Self) -> Result<Self> {
        let numerator = self
            .numerator
            .checked_mul(other.denominator)
            .and_then(|left| {
                other
                    .numerator
                    .checked_mul(self.denominator)
                    .and_then(|right| left.checked_add(right))
            })
            .ok_or_else(|| anyhow::anyhow!("rational addition overflow"))?;
        let denominator = self
            .denominator
            .checked_mul(other.denominator)
            .ok_or_else(|| anyhow::anyhow!("rational denominator overflow"))?;
        Self::new(numerator, denominator)
    }

    fn scale(self, value: i64) -> Result<Self> {
        Self::new(
            self.numerator
                .checked_mul(value as i128)
                .ok_or_else(|| anyhow::anyhow!("rational product overflow"))?,
            self.denominator,
        )
    }

    fn is_zero(self) -> bool {
        self.numerator == 0
    }
}

fn gcd_i128(mut left: i128, mut right: i128) -> i128 {
    left = left.abs();
    right = right.abs();
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left.max(1)
}

#[derive(Deserialize)]
struct Certificate {
    n: usize,
    terms: Vec<CertificateTerm>,
}

#[derive(Deserialize)]
struct CertificateTerm {
    coefficient: String,
    pair: Vec<Vec<[usize; 2]>>,
}

fn zero_based_edges(edges: &[[usize; 2]], n: usize) -> Result<Vec<[usize; 2]>> {
    edges
        .iter()
        .map(|&[left, right]| {
            ensure!(
                1 <= left && left <= right && right <= n,
                "certificate edge is out of range"
            );
            Ok([left - 1, right - 1])
        })
        .collect()
}

fn add_column(
    linear: &mut [Rational],
    hinges: &mut HashMap<Vec<i16>, Rational>,
    column: &SparseColumn,
    coefficient: Rational,
) -> Result<()> {
    for (target, &value) in linear.iter_mut().zip(&column.linear) {
        *target = target.add(coefficient.scale(value)?)?;
    }
    for (direction, &value) in &column.hinges {
        let target = hinges.entry(direction.clone()).or_insert(Rational::ZERO);
        *target = target.add(coefficient.scale(value)?)?;
    }
    hinges.retain(|_, value| !value.is_zero());
    Ok(())
}

#[derive(Serialize)]
struct CertificateRow {
    n: usize,
    branch_edge_occurrences: usize,
    terms_checked_denominator: usize,
    loop_bearing_terms: usize,
    minimum_coordinate_hinge_terms: usize,
    literal_permutations_per_term: u64,
    exact_dp_literal_matches: usize,
    exact_max_identity: bool,
    diagonal_sign_mutant_rejected: bool,
    input: String,
    input_sha256: String,
}

fn factorial(n: usize) -> u64 {
    (1..=n as u64).product()
}

fn validate_certificate(path: &Path) -> Result<CertificateRow> {
    let certificate: Certificate = serde_json::from_reader(File::open(path)?)?;
    ensure!(certificate.n <= 8, "certificate brute-force cap exceeded");
    ensure!(!certificate.terms.is_empty(), "certificate has no terms");
    let mut linear = vec![Rational::ZERO; certificate.n];
    let mut hinges: HashMap<Vec<i16>, Rational> = HashMap::default();
    let mut branch_edges = None;
    let mut loop_bearing_terms = 0usize;
    let mut minimum_coordinate_hinge_terms = 0usize;
    let mut literal_matches = 0usize;
    for (term_index, term) in certificate.terms.iter().enumerate() {
        ensure!(
            term.pair.len() == 2,
            "term {term_index}: expected two branches"
        );
        let first = zero_based_edges(&term.pair[0], certificate.n)?;
        let second = zero_based_edges(&term.pair[1], certificate.n)?;
        ensure!(
            first.len() == second.len(),
            "term {term_index}: branch sizes differ"
        );
        match branch_edges {
            None => branch_edges = Some(first.len()),
            Some(value) => ensure!(value == first.len(), "certificate branch size changed"),
        }
        loop_bearing_terms +=
            usize::from(first.iter().chain(&second).any(|edge| edge[0] == edge[1]));
        let (record, common_loops) = record_from_branches(&first, &second, certificate.n)?;
        let dynamic = generate_column(&record, certificate.n, first.len(), common_loops)
            .with_context(|| format!("certificate term {term_index}: dynamic column"))?;
        let literal = brute_force_branches(&first, &second, certificate.n)
            .with_context(|| format!("certificate term {term_index}: literal column"))?;
        ensure!(
            dynamic == literal,
            "certificate term {term_index}: DP/literal mismatch"
        );
        minimum_coordinate_hinge_terms +=
            usize::from(dynamic.hinges.keys().any(|direction| direction[0] != 0));
        literal_matches += 1;
        add_column(
            &mut linear,
            &mut hinges,
            &dynamic,
            Rational::parse(&term.coefficient)?,
        )?;
    }
    linear[certificate.n - 1] = linear[certificate.n - 1].add(Rational::new(-1, 1)?)?;
    let exact_max_identity = linear.iter().all(|value| value.is_zero()) && hinges.is_empty();
    ensure!(
        exact_max_identity,
        "certificate does not sum exactly to MAX_n"
    );

    // Plant one defective implementation across the complete identity.  An
    // invariant rejection or a nonzero residual both count as catching it.
    let diagonal_sign_mutant_rejected = (|| -> Result<bool> {
        let mut mutant_linear = vec![Rational::ZERO; certificate.n];
        let mut mutant_hinges: HashMap<Vec<i16>, Rational> = HashMap::default();
        for term in &certificate.terms {
            let first = zero_based_edges(&term.pair[0], certificate.n)?;
            let second = zero_based_edges(&term.pair[1], certificate.n)?;
            let (record, common_loops) = record_from_branches(&first, &second, certificate.n)?;
            let Ok(column) = generate_column_diagonal_sign_mutant(
                &record,
                certificate.n,
                first.len(),
                common_loops,
            ) else {
                return Ok(true);
            };
            add_column(
                &mut mutant_linear,
                &mut mutant_hinges,
                &column,
                Rational::parse(&term.coefficient)?,
            )?;
        }
        mutant_linear[certificate.n - 1] =
            mutant_linear[certificate.n - 1].add(Rational::new(-1, 1)?)?;
        Ok(!mutant_linear.iter().all(|value| value.is_zero()) || !mutant_hinges.is_empty())
    })()?;
    ensure!(
        diagonal_sign_mutant_rejected,
        "diagonal sign mutant survived"
    );

    Ok(CertificateRow {
        n: certificate.n,
        branch_edge_occurrences: branch_edges.unwrap(),
        terms_checked_denominator: certificate.terms.len(),
        loop_bearing_terms,
        minimum_coordinate_hinge_terms,
        literal_permutations_per_term: factorial(certificate.n),
        exact_dp_literal_matches: literal_matches,
        exact_max_identity,
        diagonal_sign_mutant_rejected,
        input: path.display().to_string(),
        input_sha256: sha256_path(path)?,
    })
}

#[derive(Serialize)]
struct CertificateReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    certificates_passed: usize,
    certificate_denominator: usize,
    templates_checked: usize,
    template_denominator: usize,
    loop_bearing_templates: usize,
    minimum_coordinate_hinge_templates: usize,
    minimum_coordinate_control_passed: usize,
    minimum_coordinate_control_denominator: usize,
    minimum_coordinate_control_d0_hinges: usize,
    exact_max_identities_passed: usize,
    exact_max_identity_denominator: usize,
    diagonal_sign_mutants_rejected: usize,
    diagonal_sign_mutant_denominator: usize,
    rows: Vec<CertificateRow>,
    no_claim: &'static str,
}

fn command_validate_certificates(args: &Args) -> Result<()> {
    let first = args.required_path("--certificate-n5")?;
    let second = args.required_path("--certificate-n7")?;
    let output = args.required_path("--output")?;
    let mut rows = vec![
        validate_certificate(&first)?,
        validate_certificate(&second)?,
    ];
    let expected_dimensions = if let Some(path) = args.values.get("--certificate-n8") {
        rows.push(validate_certificate(Path::new(path))?);
        vec![5, 7, 8]
    } else {
        vec![5, 7]
    };
    ensure!(
        rows.iter().map(|row| row.n).collect::<Vec<_>>() == expected_dimensions,
        "certificate dimensions do not match their flags"
    );
    let templates: usize = rows.iter().map(|row| row.terms_checked_denominator).sum();
    let loop_bearing: usize = rows.iter().map(|row| row.loop_bearing_terms).sum();
    let minimum_hinge_templates: usize = rows
        .iter()
        .map(|row| row.minimum_coordinate_hinge_terms)
        .sum();
    let minimum_first = vec![[0, 0], [0, 2], [3, 4]];
    let minimum_second = vec![[1, 1], [0, 3], [3, 4]];
    let (minimum_record, common_loops) = record_from_branches(&minimum_first, &minimum_second, 5)?;
    let minimum_dynamic = generate_column(&minimum_record, 5, 3, common_loops)?;
    let minimum_literal = brute_force_branches(&minimum_first, &minimum_second, 5)?;
    ensure!(
        minimum_dynamic == minimum_literal,
        "minimum-coordinate control DP/literal mismatch"
    );
    let minimum_d0_hinges = minimum_dynamic
        .hinges
        .keys()
        .filter(|direction| direction[0] != 0)
        .count();
    ensure!(
        minimum_d0_hinges > 0,
        "minimum-coordinate control has no d_0 != 0 hinge"
    );
    let report = CertificateReport {
        schema: "max11-colgen-loops-certificate-controls-v1",
        result: "PASS",
        command: args.invocation.clone(),
        certificates_passed: rows.len(),
        certificate_denominator: rows.len(),
        templates_checked: templates,
        template_denominator: templates,
        loop_bearing_templates: loop_bearing,
        minimum_coordinate_hinge_templates: minimum_hinge_templates,
        minimum_coordinate_control_passed: 1,
        minimum_coordinate_control_denominator: 1,
        minimum_coordinate_control_d0_hinges: minimum_d0_hinges,
        exact_max_identities_passed: rows.iter().filter(|row| row.exact_max_identity).count(),
        exact_max_identity_denominator: rows.len(),
        diagonal_sign_mutants_rejected: rows
            .iter()
            .filter(|row| row.diagonal_sign_mutant_rejected)
            .count(),
        diagonal_sign_mutant_denominator: rows.len(),
        rows,
        no_claim: "These are exact identities for the named pinned upstream certificates and exact column controls for their finite templates. They do not establish a MAX11 identity or completeness of the loop-inclusive enlargement.",
    };
    write_json(&output, &report)?;
    eprintln!(
        "COLGEN_LOOPS_CERTIFICATES_PASS identities={0}/{0} templates={templates}/{templates} mutants={0}/{0}",
        report.certificate_denominator,
    );
    Ok(())
}

#[derive(Serialize)]
struct LooplessParityReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    input: String,
    input_sha256: String,
    n: usize,
    branch_edge_occurrences: usize,
    records_checked: usize,
    record_denominator: usize,
    native_dependency_matches: usize,
    production_dependency_matches: usize,
    threads: usize,
    no_claim: &'static str,
}

fn command_validate_loopless(args: &Args) -> Result<()> {
    let input = args.required_path("--input")?;
    let output = args.required_path("--output")?;
    let n = args.required_usize("--n")?;
    let branch_edges = args.required_usize("--branch-edges")?;
    let threads = args.threads()?;
    let records = load_records(&input)?;
    ensure!(
        records.iter().all(|record| record
            .negative_edges
            .iter()
            .chain(&record.positive_edges)
            .all(|edge| edge[0] < edge[1])),
        "loopless parity input contains a loop"
    );
    let thread_pool = pool(threads)?;
    let outcomes: Vec<Result<(usize, usize)>> = thread_pool.install(|| {
        records
            .par_iter()
            .enumerate()
            .map(|(index, record)| {
                let dependency = max11_colgen::generate_column(record, n, branch_edges)
                    .with_context(|| format!("dependency record {index}"))?;
                let native = generate_column_native(record, n, branch_edges, 0)
                    .with_context(|| format!("native record {index}"))?;
                let production = generate_column(record, n, branch_edges, 0)
                    .with_context(|| format!("production record {index}"))?;
                ensure!(
                    native == dependency,
                    "native/dependency mismatch at record {index}"
                );
                ensure!(
                    production == dependency,
                    "production/dependency mismatch at record {index}"
                );
                Ok((1, 1))
            })
            .collect()
    });
    let (native_matches, production_matches) =
        outcomes
            .into_iter()
            .try_fold((0usize, 0usize), |(native, production), result| {
                let (one_native, one_production) = result?;
                Ok::<_, anyhow::Error>((native + one_native, production + one_production))
            })?;
    let report = LooplessParityReport {
        schema: "max11-colgen-loops-loopless-parity-v1",
        result: "PASS",
        command: args.invocation.clone(),
        input: input.display().to_string(),
        input_sha256: sha256_path(&input)?,
        n,
        branch_edge_occurrences: branch_edges,
        records_checked: records.len(),
        record_denominator: records.len(),
        native_dependency_matches: native_matches,
        production_dependency_matches: production_matches,
        threads,
        no_claim: "Column-for-column parity on this named loopless sample only; the production path delegates every canonical loopless zero-common-loop record to max11-colgen.",
    };
    write_json(&output, &report)?;
    eprintln!(
        "COLGEN_LOOPS_LOOPLESS_PASS native={native_matches}/{} production={production_matches}/{}",
        records.len(),
        records.len()
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

fn write_column(
    writer: &mut impl Write,
    column: &SparseColumn,
    record_index: usize,
    modulus: Option<u64>,
    format: &str,
) -> Result<()> {
    if format == "jsonl" {
        serde_json::to_writer(&mut *writer, &column.output(record_index, modulus)?)?;
        writer.write_all(b"\n")?;
    } else {
        write_binary_column(writer, column, record_index, modulus)?;
    }
    Ok(())
}

fn write_binary_header(
    writer: &mut impl Write,
    n: usize,
    branch_edges: usize,
    modulus: Option<u64>,
    column_count: usize,
) -> Result<()> {
    writer.write_all(b"MCOLGEN1")?;
    writer.write_all(&(n as u16).to_le_bytes())?;
    writer.write_all(&(branch_edges as u16).to_le_bytes())?;
    writer.write_all(&modulus.unwrap_or(0).to_le_bytes())?;
    writer.write_all(&(column_count as u64).to_le_bytes())?;
    Ok(())
}

fn emit_columns(
    columns: Vec<(usize, SparseColumn)>,
    n: usize,
    branch_edges: usize,
    modulus: Option<u64>,
    format: &str,
    output: &Path,
) -> Result<()> {
    ensure!(
        ["jsonl", "binary"].contains(&format),
        "format must be jsonl or binary"
    );
    let mut writer = create_output(output)?;
    if format == "binary" {
        write_binary_header(&mut writer, n, branch_edges, modulus, columns.len())?;
    }
    for (record_index, column) in columns {
        write_column(&mut writer, &column, record_index, modulus, format)?;
    }
    writer.flush()?;
    Ok(())
}

fn command_emit_records(args: &Args) -> Result<()> {
    let input = args.required_path("--input")?;
    let output = args.required_path("--output")?;
    let n = args.required_usize("--n")?;
    let branch_edges = args.required_usize("--branch-edges")?;
    let threads = args.threads()?;
    let format = args.values.get("--format").map_or("jsonl", String::as_str);
    let modulus: Option<u64> = args
        .values
        .get("--modulus")
        .map(|value| value.parse())
        .transpose()?;
    let records = load_records(&input)?;
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    ensure!(
        ["jsonl", "binary"].contains(&format),
        "format must be jsonl or binary"
    );
    let mut writer = create_output(&output)?;
    if format == "binary" {
        write_binary_header(&mut writer, n, branch_edges, modulus, records.len())?;
    }
    let batch_size = threads * 2;
    for batch_start in (0..records.len()).step_by(batch_size) {
        let batch_stop = (batch_start + batch_size).min(records.len());
        let columns: Vec<Result<(usize, SparseColumn)>> = thread_pool.install(|| {
            records[batch_start..batch_stop]
                .par_iter()
                .enumerate()
                .map(|(offset, record)| {
                    let index = batch_start + offset;
                    Ok((
                        record.sequence.unwrap_or(index),
                        generate_column(record, n, branch_edges, 0)
                            .with_context(|| format!("emit record {index}"))?,
                    ))
                })
                .collect()
        });
        for result in columns {
            let (record_index, column) = result?;
            write_column(&mut writer, &column, record_index, modulus, format)?;
        }
    }
    writer.flush()?;
    eprintln!(
        "COLGEN_LOOPS_EMIT_PASS records={} format={format} seconds={:.3}",
        records.len(),
        started.elapsed().as_secs_f64()
    );
    Ok(())
}

#[derive(Deserialize)]
struct UniverseHeader {
    record_type: String,
    schema: String,
    format: String,
    loops_allowed: bool,
    n: usize,
    branch_edge_occurrences: usize,
    expected_record_count: usize,
    padding_convention: String,
}

fn generate_batch(
    thread_pool: &rayon::ThreadPool,
    records: &[(usize, SignedRecord)],
    n: usize,
    branch_edges: usize,
) -> Vec<Result<(usize, SparseColumn)>> {
    thread_pool.install(|| {
        records
            .par_iter()
            .map(|(index, record)| {
                Ok((
                    *index,
                    generate_column(record, n, branch_edges, 0)
                        .with_context(|| format!("emit universe record {index}"))?,
                ))
            })
            .collect()
    })
}

fn flush_batch(
    writer: &mut impl Write,
    thread_pool: &rayon::ThreadPool,
    records: &mut Vec<(usize, SignedRecord)>,
    n: usize,
    branch_edges: usize,
    modulus: Option<u64>,
    format: &str,
) -> Result<()> {
    for result in generate_batch(thread_pool, records, n, branch_edges) {
        let (record_index, column) = result?;
        write_column(writer, &column, record_index, modulus, format)?;
    }
    records.clear();
    Ok(())
}

fn command_emit_universe(args: &Args) -> Result<()> {
    let input = args.required_path("--input")?;
    let output = args.required_path("--output")?;
    let threads = args.threads()?;
    let start = args.usize_or("--start", 0)?;
    let requested_limit = args.optional_usize("--limit")?;
    let format = args.values.get("--format").map_or("jsonl", String::as_str);
    ensure!(
        ["jsonl", "binary"].contains(&format),
        "format must be jsonl or binary"
    );
    let modulus: Option<u64> = args
        .values
        .get("--modulus")
        .map(|value| value.parse())
        .transpose()?;

    let mut reader = open_reader(&input)?;
    let mut line = String::new();
    ensure!(reader.read_line(&mut line)? > 0, "universe input is empty");
    let header: UniverseHeader = serde_json::from_str(&line).context("decoding universe header")?;
    ensure!(
        header.record_type == "header",
        "first universe row is not a header"
    );
    ensure!(
        header.schema == "max11-loop-inclusive-signed-degree5-universe-v1",
        "unexpected universe schema"
    );
    ensure!(header.format == "gzip-jsonl", "unexpected universe format");
    ensure!(header.loops_allowed, "universe header disallows loops");
    ensure!(
        header.n == 11,
        "loop-inclusive enlargement universe must have n=11"
    );
    ensure!(
        header.branch_edge_occurrences == 5,
        "loop-inclusive enlargement universe must have k=5"
    );
    ensure!(
        header.padding_convention == "zero common loops; remaining common padding nonloop",
        "unexpected padding convention"
    );
    ensure!(
        start <= header.expected_record_count,
        "--start exceeds universe size"
    );
    let available = header.expected_record_count - start;
    let selected = requested_limit.unwrap_or(available);
    ensure!(
        selected <= available,
        "--limit exceeds remaining universe records"
    );

    let mut writer = create_output(&output)?;
    if format == "binary" {
        write_binary_header(
            &mut writer,
            header.n,
            header.branch_edge_occurrences,
            modulus,
            selected,
        )?;
    }
    let thread_pool = pool(threads)?;
    let batch_capacity = threads * 2;
    let mut batch = Vec::with_capacity(batch_capacity);
    let mut seen = 0usize;
    let mut emitted = 0usize;
    let started = Instant::now();
    loop {
        line.clear();
        if reader.read_line(&mut line)? == 0 {
            break;
        }
        if line.trim().is_empty() {
            continue;
        }
        let record: SignedRecord = serde_json::from_str(&line)
            .with_context(|| format!("decoding universe record {seen}"))?;
        ensure!(
            record.sequence == Some(seen),
            "non-contiguous universe sequence at {seen}"
        );
        if seen >= start && emitted < selected {
            batch.push((seen, record));
            emitted += 1;
            if batch.len() == batch_capacity {
                flush_batch(
                    &mut writer,
                    &thread_pool,
                    &mut batch,
                    header.n,
                    header.branch_edge_occurrences,
                    modulus,
                    format,
                )?;
            }
        }
        seen += 1;
        if emitted == selected && seen >= start + selected {
            break;
        }
    }
    if !batch.is_empty() {
        flush_batch(
            &mut writer,
            &thread_pool,
            &mut batch,
            header.n,
            header.branch_edge_occurrences,
            modulus,
            format,
        )?;
    }
    ensure!(
        emitted == selected,
        "universe ended before selected range was emitted"
    );
    if start + selected == header.expected_record_count {
        line.clear();
        ensure!(
            reader.read_line(&mut line)? == 0,
            "universe exceeds expected record count"
        );
        ensure!(
            seen == header.expected_record_count,
            "universe record count differs from header"
        );
    }
    writer.flush()?;
    eprintln!(
        "COLGEN_LOOPS_UNIVERSE_EMIT_PASS start={start} records={emitted}/{selected} format={format} seconds={:.3}",
        started.elapsed().as_secs_f64()
    );
    Ok(())
}

fn command_emit_base_atoms(args: &Args) -> Result<()> {
    let output = args.required_path("--output")?;
    let n = args.required_usize("--n")?;
    let branch_edges = args.required_usize("--branch-edges")?;
    let format = args.values.get("--format").map_or("jsonl", String::as_str);
    let modulus = args
        .values
        .get("--modulus")
        .map(|value| value.parse())
        .transpose()?;
    let (nonloops, loops) = base_atoms(n, branch_edges)?;
    emit_columns(
        vec![(0, nonloops), (1, loops)],
        n,
        branch_edges,
        modulus,
        format,
        &output,
    )?;
    eprintln!("COLGEN_LOOPS_BASES_PASS atoms=2/2 format={format}");
    Ok(())
}

fn quantile(sorted: &[usize], numerator: usize, denominator: usize) -> usize {
    sorted[(sorted.len() - 1) * numerator / denominator]
}

#[derive(Serialize)]
struct BenchmarkReport {
    schema: &'static str,
    result: &'static str,
    command: Vec<String>,
    sample: String,
    sample_sha256: String,
    sample_method: &'static str,
    sample_seed: u64,
    sample_size: usize,
    sample_denominator: usize,
    sample_loop_bearing_records: usize,
    sample_sequence_sha256_u64_le: String,
    n: usize,
    branch_edge_occurrences: usize,
    universe_records: usize,
    base_atoms: usize,
    projected_columns: usize,
    threads: usize,
    wall_seconds: f64,
    records_per_second: f64,
    core_seconds_per_column: f64,
    projected_wall_seconds_4_threads: f64,
    projected_wall_seconds_24_vcpus_ideal: f64,
    projected_wall_seconds_64_vcpus_ideal: f64,
    retained_hinges_min: usize,
    retained_hinges_p50: usize,
    retained_hinges_p90: usize,
    retained_hinges_p99: usize,
    retained_hinges_max: usize,
    sampled_hinges_numerator: u64,
    sampled_hinges_denominator: usize,
    minimum_coordinate_hinge_records: usize,
    minimum_coordinate_hinge_record_denominator: usize,
    minimum_coordinate_hinges_numerator: u64,
    minimum_coordinate_hinges_denominator: u64,
    no_claim: &'static str,
}

fn command_benchmark(args: &Args) -> Result<()> {
    let input = args.required_path("--input")?;
    let output = args.required_path("--output")?;
    let n = args.required_usize("--n")?;
    let branch_edges = args.required_usize("--branch-edges")?;
    let universe_records = args.required_usize("--universe-records")?;
    let expected_sample_size = args.usize_or("--expected-sample-size", 1000)?;
    let seed = args.u64_or("--seed", 2_026_090_213)?;
    let threads = args.threads()?;
    let records = load_records(&input)?;
    ensure!(
        records.len() == expected_sample_size,
        "benchmark sample size differs"
    );
    let mut sequence_digest = Sha256::new();
    for (index, record) in records.iter().enumerate() {
        sequence_digest.update((record.sequence.unwrap_or(index) as u64).to_le_bytes());
    }
    let loop_bearing = records
        .iter()
        .filter(|record| {
            record
                .negative_edges
                .iter()
                .chain(&record.positive_edges)
                .any(|edge| edge[0] == edge[1])
        })
        .count();
    let thread_pool = pool(threads)?;
    let started = Instant::now();
    let counts: Vec<Result<(usize, usize)>> = thread_pool.install(|| {
        records
            .par_iter()
            .enumerate()
            .map(|(index, record)| {
                generate_column(record, n, branch_edges, 0)
                    .map(|column| {
                        let minimum_hinges = column
                            .hinges
                            .keys()
                            .filter(|direction| direction[0] != 0)
                            .count();
                        (column.hinges.len(), minimum_hinges)
                    })
                    .with_context(|| format!("benchmark record {index}"))
            })
            .collect()
    });
    let elapsed = started.elapsed().as_secs_f64();
    let outcomes = counts.into_iter().collect::<Result<Vec<_>>>()?;
    let minimum_hinge_records = outcomes
        .iter()
        .filter(|(_, minimum_hinges)| *minimum_hinges > 0)
        .count();
    let minimum_hinge_total = outcomes.iter().try_fold(0u64, |acc, &(_, value)| {
        acc.checked_add(value as u64)
            .ok_or_else(|| anyhow::anyhow!("minimum-coordinate hinge count overflow"))
    })?;
    let mut counts: Vec<usize> = outcomes.into_iter().map(|(count, _)| count).collect();
    counts.sort_unstable();
    let hinge_total = counts.iter().try_fold(0u64, |acc, &value| {
        acc.checked_add(value as u64)
            .ok_or_else(|| anyhow::anyhow!("sample hinge count overflow"))
    })?;
    let projected_columns = universe_records
        .checked_add(2)
        .ok_or_else(|| anyhow::anyhow!("projected column count overflow"))?;
    let core_seconds = elapsed * threads as f64 / records.len() as f64;
    let report = BenchmarkReport {
        schema: "max11-colgen-loops-benchmark-v1",
        result: "PASS",
        command: args.invocation.clone(),
        sample: input.display().to_string(),
        sample_sha256: sha256_path(&input)?,
        sample_method: "uniform without-replacement reservoir sample from all G-0038 orbit records",
        sample_seed: seed,
        sample_size: records.len(),
        sample_denominator: records.len(),
        sample_loop_bearing_records: loop_bearing,
        sample_sequence_sha256_u64_le: format!("{:x}", sequence_digest.finalize()),
        n,
        branch_edge_occurrences: branch_edges,
        universe_records,
        base_atoms: 2,
        projected_columns,
        threads,
        wall_seconds: elapsed,
        records_per_second: records.len() as f64 / elapsed,
        core_seconds_per_column: core_seconds,
        projected_wall_seconds_4_threads: core_seconds * projected_columns as f64 / 4.0,
        projected_wall_seconds_24_vcpus_ideal: core_seconds * projected_columns as f64 / 24.0,
        projected_wall_seconds_64_vcpus_ideal: core_seconds * projected_columns as f64 / 64.0,
        retained_hinges_min: counts[0],
        retained_hinges_p50: quantile(&counts, 50, 100),
        retained_hinges_p90: quantile(&counts, 90, 100),
        retained_hinges_p99: quantile(&counts, 99, 100),
        retained_hinges_max: *counts.last().unwrap(),
        sampled_hinges_numerator: hinge_total,
        sampled_hinges_denominator: records.len(),
        minimum_coordinate_hinge_records: minimum_hinge_records,
        minimum_coordinate_hinge_record_denominator: records.len(),
        minimum_coordinate_hinges_numerator: minimum_hinge_total,
        minimum_coordinate_hinges_denominator: hinge_total,
        no_claim: "Timing and support-size measurements on the named deterministic sample only. The 24/64-vCPU values assume ideal linear scaling and are not measured full passes or MAX11 membership results.",
    };
    write_json(&output, &report)?;
    eprintln!(
        "COLGEN_LOOPS_BENCHMARK_PASS sample={}/{} loops={}/{} seconds={elapsed:.3}",
        records.len(),
        expected_sample_size,
        loop_bearing,
        records.len()
    );
    Ok(())
}

fn usage() -> &'static str {
    "usage:\n  max11-colgen-loops validate-certificates --certificate-n5 FILE --certificate-n7 FILE [--certificate-n8 FILE] --output REPORT\n  max11-colgen-loops validate-loopless --input RECORDS.jsonl --n N --branch-edges K --threads T --output REPORT\n  max11-colgen-loops emit-records --input RECORDS.jsonl --n N --branch-edges K --threads T --format jsonl|binary [--modulus P] --output FILE\n  max11-colgen-loops emit-universe --input G-0038.jsonl.gz --threads T --format jsonl|binary [--modulus P] [--start I] [--limit L] --output FILE\n  max11-colgen-loops emit-base-atoms --n N --branch-edges K --format jsonl|binary [--modulus P] --output FILE\n  max11-colgen-loops benchmark --input SAMPLE.jsonl --n N --branch-edges K --universe-records U --expected-sample-size S --seed N --threads T --output REPORT"
}

fn main() -> Result<()> {
    let args = Args::parse().inspect_err(|_| eprintln!("{}", usage()))?;
    match args.command.as_str() {
        "validate-certificates" => command_validate_certificates(&args),
        "validate-loopless" => command_validate_loopless(&args),
        "emit-records" => command_emit_records(&args),
        "emit-universe" => command_emit_universe(&args),
        "emit-base-atoms" => command_emit_base_atoms(&args),
        "benchmark" => command_benchmark(&args),
        _ => bail!("unknown command {}\n{}", args.command, usage()),
    }
}
