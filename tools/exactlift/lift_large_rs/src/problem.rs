use crate::crt;
use crate::modular::BlockFactor;
use crate::rational::{Rational, lcm_u128, reconstruct};
use rayon::prelude::*;
use serde::Serialize;
use std::fs::{self, File};
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};
use std::time::Instant;

const MAGIC: &[u8; 8] = b"ELIFTQ01";

#[derive(Debug)]
pub struct ExactProblem {
    pub rows: usize,
    pub columns: usize,
    pub column_offsets: Vec<u64>,
    pub row_indices: Vec<u32>,
    pub values: Vec<i32>,
    pub selected_rows: Vec<u32>,
    pub rhs: Vec<i64>,
    pub source_indices: Vec<u64>,
}

#[derive(Clone, Debug)]
pub struct SolveConfig {
    pub input: PathBuf,
    pub prime: u32,
    pub lu_block: usize,
    pub row_tile: usize,
    pub threads: usize,
    pub max_steps: usize,
    pub reconstruct_every: usize,
    pub candidate_support_limit: usize,
    pub crt_primes: Vec<u32>,
}

#[derive(Serialize)]
struct Coefficient {
    source_index: u64,
    numerator: String,
    denominator: String,
}

#[derive(Serialize)]
struct Attempt {
    method: &'static str,
    iteration_or_prime_count_numerator: usize,
    modulus_bits: u32,
    reconstructed_coordinates_numerator: usize,
    reconstructed_coordinates_denominator: usize,
    candidate_support_numerator: usize,
    candidate_support_denominator: usize,
    exact_check_attempted: bool,
    exact_check_pass: bool,
}

#[derive(Serialize)]
pub struct ProblemReport {
    schema: &'static str,
    verdict: &'static str,
    input: String,
    rows_checked_denominator: usize,
    columns_denominator: usize,
    csc_nonzeros_numerator: usize,
    selected_minor_rows_numerator: usize,
    selected_minor_rows_denominator: usize,
    prime: u32,
    threads_maximum: usize,
    dense_modular_storage_bytes: u64,
    csc_storage_bytes: u64,
    lu_total_seconds: f64,
    lu_diagonal_inverse_seconds: f64,
    lu_lower_solve_seconds: f64,
    lu_schur_update_seconds: f64,
    modular_solve_seconds_by_iteration: Vec<f64>,
    csc_matvec_seconds_by_iteration: Vec<f64>,
    crt_primes_attempted: Vec<u32>,
    crt_factor_seconds: Vec<f64>,
    crt_solve_seconds: Vec<f64>,
    recovery_method: &'static str,
    iterations_to_reconstruction_numerator: usize,
    attempts: Vec<Attempt>,
    recovered_support_numerator: usize,
    recovered_support_denominator: usize,
    recovered_denominator_lcm: String,
    exact_rows_verified_numerator: usize,
    exact_rows_verified_denominator: usize,
    mutation_delta: &'static str,
    mutation_nonzero_rows_numerator: usize,
    mutation_rows_checked_denominator: usize,
    max_rss_kib: u64,
    total_seconds: f64,
    coefficients: Vec<Coefficient>,
    no_claim: &'static str,
}

fn read_exact_array<const N: usize>(reader: &mut impl Read) -> Result<[u8; N], String> {
    let mut bytes = [0_u8; N];
    reader.read_exact(&mut bytes).map_err(|error| error.to_string())?;
    Ok(bytes)
}

fn read_u32(reader: &mut impl Read) -> Result<u32, String> {
    Ok(u32::from_le_bytes(read_exact_array(reader)?))
}

fn read_u64(reader: &mut impl Read) -> Result<u64, String> {
    Ok(u64::from_le_bytes(read_exact_array(reader)?))
}

fn read_i32(reader: &mut impl Read) -> Result<i32, String> {
    Ok(i32::from_le_bytes(read_exact_array(reader)?))
}

fn read_i64(reader: &mut impl Read) -> Result<i64, String> {
    Ok(i64::from_le_bytes(read_exact_array(reader)?))
}

impl ExactProblem {
    pub fn read(path: &Path) -> Result<Self, String> {
        let mut reader = BufReader::with_capacity(
            8 * 1024 * 1024,
            File::open(path).map_err(|error| error.to_string())?,
        );
        if &read_exact_array::<8>(&mut reader)? != MAGIC {
            return Err("invalid ELIFTQ01 magic".to_string());
        }
        let rows = read_u32(&mut reader)? as usize;
        let columns = read_u32(&mut reader)? as usize;
        let selected = read_u32(&mut reader)? as usize;
        let nnz = read_u64(&mut reader)? as usize;
        if rows < columns || selected != columns || columns == 0 {
            return Err("invalid exact-lift dimensions".to_string());
        }
        let mut column_offsets = Vec::with_capacity(columns + 1);
        for _ in 0..=columns {
            column_offsets.push(read_u64(&mut reader)?);
        }
        if column_offsets.first() != Some(&0)
            || column_offsets.last().copied() != Some(nnz as u64)
            || column_offsets.windows(2).any(|pair| pair[0] > pair[1])
        {
            return Err("invalid CSC column offsets".to_string());
        }
        let mut row_indices = Vec::with_capacity(nnz);
        for _ in 0..nnz {
            let row = read_u32(&mut reader)?;
            if row as usize >= rows {
                return Err("CSC row index outside row universe".to_string());
            }
            row_indices.push(row);
        }
        let mut values = Vec::with_capacity(nnz);
        for _ in 0..nnz {
            values.push(read_i32(&mut reader)?);
        }
        let mut selected_rows = Vec::with_capacity(columns);
        let mut seen = vec![false; rows];
        for _ in 0..columns {
            let row = read_u32(&mut reader)?;
            if row as usize >= rows || seen[row as usize] {
                return Err("invalid/repeated selected row".to_string());
            }
            seen[row as usize] = true;
            selected_rows.push(row);
        }
        let mut rhs = Vec::with_capacity(rows);
        for _ in 0..rows {
            rhs.push(read_i64(&mut reader)?);
        }
        let mut source_indices = Vec::with_capacity(columns);
        for _ in 0..columns {
            source_indices.push(read_u64(&mut reader)?);
        }
        let mut trailing = [0_u8; 1];
        if reader.read(&mut trailing).map_err(|error| error.to_string())? != 0 {
            return Err("trailing bytes after exact-lift problem".to_string());
        }
        Ok(Self {
            rows,
            columns,
            column_offsets,
            row_indices,
            values,
            selected_rows,
            rhs,
            source_indices,
        })
    }

    pub(crate) fn dense_modular(&self, prime: u32) -> Vec<u32> {
        let mut selected_position = vec![usize::MAX; self.rows];
        for (position, &row) in self.selected_rows.iter().enumerate() {
            selected_position[row as usize] = position;
        }
        let mut dense = vec![0_u32; self.columns * self.columns];
        for column in 0..self.columns {
            let start = self.column_offsets[column] as usize;
            let end = self.column_offsets[column + 1] as usize;
            for position in start..end {
                let selected = selected_position[self.row_indices[position] as usize];
                if selected != usize::MAX {
                    dense[selected * self.columns + column] =
                        self.values[position].rem_euclid(prime as i32) as u32;
                }
            }
        }
        dense
    }

    pub(crate) fn selected_rhs_mod(&self, residual: &[i128], prime: u32) -> Vec<u32> {
        self.selected_rows
            .iter()
            .map(|&row| residual[row as usize].rem_euclid(prime as i128) as u32)
            .collect()
    }

    pub(crate) fn matvec_digits(&self, digits: &[u32]) -> Vec<i128> {
        (0..self.columns)
            .into_par_iter()
            .fold(
                || vec![0_i128; self.rows],
                |mut accumulator, column| {
                    let digit = digits[column] as i128;
                    if digit != 0 {
                        for position in self.column_offsets[column] as usize
                            ..self.column_offsets[column + 1] as usize
                        {
                            accumulator[self.row_indices[position] as usize] +=
                                self.values[position] as i128 * digit;
                        }
                    }
                    accumulator
                },
            )
            .reduce(
                || vec![0_i128; self.rows],
                |mut left, right| {
                    for (target, value) in left.iter_mut().zip(right) {
                        *target += value;
                    }
                    left
                },
            )
    }

    fn exact_scaled_matvec(&self, scaled: &[i128]) -> Vec<i128> {
        (0..self.columns)
            .into_par_iter()
            .fold(
                || vec![0_i128; self.rows],
                |mut accumulator, column| {
                    let coefficient = scaled[column];
                    if coefficient != 0 {
                        for position in self.column_offsets[column] as usize
                            ..self.column_offsets[column + 1] as usize
                        {
                            accumulator[self.row_indices[position] as usize] +=
                                self.values[position] as i128 * coefficient;
                        }
                    }
                    accumulator
                },
            )
            .reduce(
                || vec![0_i128; self.rows],
                |mut left, right| {
                    for (target, value) in left.iter_mut().zip(right) {
                        *target += value;
                    }
                    left
                },
            )
    }
}

fn max_rss_kib() -> u64 {
    fs::read_to_string("/proc/self/status")
        .ok()
        .and_then(|text| {
            text.lines().find_map(|line| {
                line.strip_prefix("VmHWM:")?
                    .split_whitespace()
                    .next()?
                    .parse::<u64>()
                    .ok()
            })
        })
        .unwrap_or(0)
}

fn common_scale(candidate: &[Rational]) -> Option<(u128, Vec<i128>)> {
    let mut denominator = 1_u128;
    for value in candidate {
        denominator = lcm_u128(denominator, value.denominator as u128)?;
    }
    if denominator > i128::MAX as u128 {
        return None;
    }
    let scaled = candidate
        .iter()
        .map(|value| value.numerator * (denominator / value.denominator as u128) as i128)
        .collect();
    Some((denominator, scaled))
}

fn verify(problem: &ExactProblem, candidate: &[Rational]) -> (bool, usize, u128) {
    let Some((denominator, scaled)) = common_scale(candidate) else {
        return (false, 0, 0);
    };
    let product = problem.exact_scaled_matvec(&scaled);
    let failures = product
        .iter()
        .zip(&problem.rhs)
        .filter(|(left, right)| **left != **right as i128 * denominator as i128)
        .count();
    (failures == 0, failures, denominator)
}

fn try_reconstruct(
    problem: &ExactProblem,
    residue: &[u128],
    modulus: u128,
    support_limit: usize,
    method: &'static str,
    count: usize,
    attempts: &mut Vec<Attempt>,
) -> Option<Vec<Rational>> {
    let reconstructed: Vec<Option<Rational>> = residue
        .iter()
        .map(|&value| reconstruct(value, modulus))
        .collect();
    let reconstructed_count = reconstructed.iter().filter(|value| value.is_some()).count();
    let candidate: Vec<Rational> = reconstructed.iter().filter_map(|value| *value).collect();
    let support = candidate.iter().filter(|value| value.numerator != 0).count();
    let exact_check_attempted = reconstructed_count == problem.columns && support <= support_limit;
    let exact_check_pass = exact_check_attempted && verify(problem, &candidate).0;
    attempts.push(Attempt {
        method,
        iteration_or_prime_count_numerator: count,
        modulus_bits: 128 - modulus.leading_zeros(),
        reconstructed_coordinates_numerator: reconstructed_count,
        reconstructed_coordinates_denominator: problem.columns,
        candidate_support_numerator: support,
        candidate_support_denominator: problem.columns,
        exact_check_attempted,
        exact_check_pass,
    });
    exact_check_pass.then_some(candidate)
}

pub fn solve(config: &SolveConfig) -> Result<ProblemReport, String> {
    if !crt::is_prime(config.prime) || config.prime >= 65_536 {
        return Err("prime must be prime and below 65536 for exact f64 block products".to_string());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(config.threads)
        .build_global()
        .map_err(|error| error.to_string())?;
    let total_started = Instant::now();
    let problem = ExactProblem::read(&config.input)?;
    let dense = problem.dense_modular(config.prime);
    let factor = BlockFactor::factor(
        dense,
        problem.columns,
        config.lu_block,
        config.prime,
        config.threads,
        config.row_tile,
    )?;
    let mut residual: Vec<i128> = problem.rhs.iter().map(|&value| value as i128).collect();
    let mut residue = vec![0_u128; problem.columns];
    let mut modulus = 1_u128;
    let mut solve_seconds = Vec::new();
    let mut matvec_seconds = Vec::new();
    let mut attempts = Vec::new();
    let mut recovered = None;
    let mut recovered_count = 0;
    let mut recovery_method = "dixon-early-rational-reconstruction";
    let mut crt_primes_attempted = Vec::new();
    let mut crt_factor_seconds = Vec::new();
    let mut crt_solve_seconds = Vec::new();

    for iteration in 1..=config.max_steps {
        let phase = Instant::now();
        let digit = factor.solve(&problem.selected_rhs_mod(&residual, config.prime))?;
        solve_seconds.push(phase.elapsed().as_secs_f64());
        for (value, &new_digit) in residue.iter_mut().zip(&digit) {
            *value += modulus * new_digit as u128;
        }
        modulus = modulus
            .checked_mul(config.prime as u128)
            .ok_or_else(|| "p-adic modulus overflow".to_string())?;
        let phase = Instant::now();
        let product = problem.matvec_digits(&digit);
        for row in 0..problem.rows {
            let difference = residual[row] - product[row];
            if difference.rem_euclid(config.prime as i128) != 0 {
                return Err(format!("nondivisible Dixon residual at iteration {iteration}, row {row}"));
            }
            residual[row] = difference / config.prime as i128;
        }
        matvec_seconds.push(phase.elapsed().as_secs_f64());
        if iteration % config.reconstruct_every == 0
            && let Some(candidate) = try_reconstruct(
                &problem,
                &residue,
                modulus,
                config.candidate_support_limit,
                "dixon",
                iteration,
                &mut attempts,
            )
        {
            recovered = Some(candidate);
            recovered_count = iteration;
            break;
        }
    }
    let factor_timings = factor.timings.clone();
    drop(factor);

    if recovered.is_none() && !config.crt_primes.is_empty() {
        recovery_method = "multi-modular-crt-fallback";
        residue.fill(0);
        modulus = 1;
        for (index, &prime) in config.crt_primes.iter().enumerate() {
            if !crt::is_prime(prime) || prime >= 65_536 || modulus % prime as u128 == 0 {
                return Err(format!("invalid/repeated CRT prime {prime}"));
            }
            let phase = Instant::now();
            let dense = problem.dense_modular(prime);
            let one_prime = BlockFactor::factor(
                dense,
                problem.columns,
                config.lu_block,
                prime,
                config.threads,
                config.row_tile,
            )?;
            crt_factor_seconds.push(phase.elapsed().as_secs_f64());
            let rhs: Vec<u32> = problem
                .selected_rows
                .iter()
                .map(|&row| problem.rhs[row as usize].rem_euclid(prime as i64) as u32)
                .collect();
            let phase = Instant::now();
            let solution = one_prime.solve(&rhs)?;
            crt_solve_seconds.push(phase.elapsed().as_secs_f64());
            crt_primes_attempted.push(prime);
            for (value, next) in residue.iter_mut().zip(solution) {
                *value = crt::combine(*value, modulus, next, prime)
                    .ok_or_else(|| "CRT combination overflow/noninvertibility".to_string())?;
            }
            modulus = modulus
                .checked_mul(prime as u128)
                .ok_or_else(|| "CRT modulus overflow".to_string())?;
            if let Some(candidate) = try_reconstruct(
                &problem,
                &residue,
                modulus,
                config.candidate_support_limit,
                "crt",
                index + 1,
                &mut attempts,
            ) {
                recovered = Some(candidate);
                recovered_count = index + 1;
                break;
            }
        }
    }
    let recovered = recovered.ok_or_else(|| "no rational reconstruction verified".to_string())?;
    let (passed, failures, denominator) = verify(&problem, &recovered);
    if !passed || failures != 0 {
        return Err("final exact verification failed".to_string());
    }
    let support = recovered.iter().filter(|value| value.numerator != 0).count();
    let mut mutated = recovered.clone();
    let mutation_index = mutated
        .iter()
        .position(|value| value.numerator != 0)
        .ok_or_else(|| "zero solution cannot satisfy nonzero exact-lift control".to_string())?;
    mutated[mutation_index].numerator += mutated[mutation_index].denominator;
    let (mutation_pass, mutation_failures, _) = verify(&problem, &mutated);
    if mutation_pass || mutation_failures == 0 {
        return Err("+1 mutation unexpectedly passed".to_string());
    }
    let coefficients = recovered
        .iter()
        .zip(&problem.source_indices)
        .filter(|(value, _)| value.numerator != 0)
        .map(|(value, &source_index)| Coefficient {
            source_index,
            numerator: value.numerator.to_string(),
            denominator: value.denominator.to_string(),
        })
        .collect();
    Ok(ProblemReport {
        schema: "max11-lift-large-result-v1",
        verdict: "PASS",
        input: config.input.display().to_string(),
        rows_checked_denominator: problem.rows,
        columns_denominator: problem.columns,
        csc_nonzeros_numerator: problem.values.len(),
        selected_minor_rows_numerator: problem.selected_rows.len(),
        selected_minor_rows_denominator: problem.columns,
        prime: config.prime,
        threads_maximum: config.threads,
        dense_modular_storage_bytes: (problem.columns * problem.columns * size_of::<u32>()) as u64,
        csc_storage_bytes: (problem.column_offsets.len() * size_of::<u64>()
            + problem.row_indices.len() * size_of::<u32>()
            + problem.values.len() * size_of::<i32>()) as u64,
        lu_total_seconds: factor_timings.total.as_secs_f64(),
        lu_diagonal_inverse_seconds: factor_timings.diagonal_inverse.as_secs_f64(),
        lu_lower_solve_seconds: factor_timings.lower_solve.as_secs_f64(),
        lu_schur_update_seconds: factor_timings.schur_update.as_secs_f64(),
        modular_solve_seconds_by_iteration: solve_seconds,
        csc_matvec_seconds_by_iteration: matvec_seconds,
        crt_primes_attempted,
        crt_factor_seconds,
        crt_solve_seconds,
        recovery_method,
        iterations_to_reconstruction_numerator: recovered_count,
        attempts,
        recovered_support_numerator: support,
        recovered_support_denominator: problem.columns,
        recovered_denominator_lcm: denominator.to_string(),
        exact_rows_verified_numerator: problem.rows,
        exact_rows_verified_denominator: problem.rows,
        mutation_delta: "+1/1 at first nonzero coordinate",
        mutation_nonzero_rows_numerator: mutation_failures,
        mutation_rows_checked_denominator: problem.rows,
        max_rss_kib: max_rss_kib(),
        total_seconds: total_started.elapsed().as_secs_f64(),
        coefficients,
        no_claim: "This exact result concerns only the named finite input matrix; it does not decide MAX11.",
    })
}
