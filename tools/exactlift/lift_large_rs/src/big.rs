use crate::modular::BlockFactor;
use crate::problem::{ExactProblem, SolveConfig};
use num_bigint::{BigInt, BigUint};
use num_integer::Integer;
use num_traits::{One, Signed, Zero};
use serde::Serialize;
use std::fs;
use std::time::Instant;

#[derive(Clone, Debug, Eq, PartialEq)]
struct BigRational {
    numerator: BigInt,
    denominator: BigInt,
}

#[derive(Serialize)]
struct Coefficient {
    source_index: u64,
    numerator: String,
    denominator: String,
}

#[derive(Serialize)]
struct Attempt {
    iteration_numerator: usize,
    modulus_bits: u64,
    reconstructed_coordinates_numerator: usize,
    reconstructed_coordinates_denominator: usize,
    exact_check_pass: bool,
}

#[derive(Serialize)]
pub struct BigReport {
    schema: &'static str,
    verdict: &'static str,
    input: String,
    rows_checked_denominator: usize,
    columns_denominator: usize,
    csc_nonzeros_numerator: usize,
    prime: u32,
    threads_maximum: usize,
    lu_total_seconds: f64,
    modular_solve_seconds_by_iteration: Vec<f64>,
    csc_matvec_seconds_by_iteration: Vec<f64>,
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

fn reconstruct(residue: &BigUint, modulus: &BigUint) -> Option<BigRational> {
    if residue.is_zero() {
        return Some(BigRational {
            numerator: BigInt::zero(),
            denominator: BigInt::one(),
        });
    }
    let bound = (modulus >> 1_usize).sqrt();
    let bound_i = BigInt::from(bound);
    let mut old_r = BigInt::from(modulus.clone());
    let mut r = BigInt::from(residue.clone());
    let mut old_t = BigInt::zero();
    let mut t = BigInt::one();
    while r.abs() > bound_i {
        if r.is_zero() {
            return None;
        }
        let quotient = &old_r / &r;
        (old_r, r) = (r.clone(), old_r - &quotient * &r);
        (old_t, t) = (t.clone(), old_t - quotient * &t);
    }
    if t.is_zero() || t.abs() > bound_i || r.gcd(&t) != BigInt::one() {
        return None;
    }
    let (numerator, denominator) = if t.is_negative() { (-r, -t) } else { (r, t) };
    let modulus_i = BigInt::from(modulus.clone());
    let residue_i = BigInt::from(residue.clone());
    if (&numerator - residue_i * &denominator).mod_floor(&modulus_i) != BigInt::zero() {
        return None;
    }
    Some(BigRational {
        numerator,
        denominator,
    })
}

fn common_scale(candidate: &[BigRational]) -> (BigInt, Vec<BigInt>) {
    let denominator = candidate.iter().fold(BigInt::one(), |current, value| {
        current.lcm(&value.denominator)
    });
    let scaled = candidate
        .iter()
        .map(|value| &value.numerator * (&denominator / &value.denominator))
        .collect();
    (denominator, scaled)
}

fn verify(problem: &ExactProblem, candidate: &[BigRational]) -> (bool, usize, BigInt) {
    let (denominator, scaled) = common_scale(candidate);
    let mut product = vec![BigInt::zero(); problem.rows];
    for (column, coefficient) in scaled.iter().enumerate() {
        if coefficient.is_zero() {
            continue;
        }
        for position in
            problem.column_offsets[column] as usize..problem.column_offsets[column + 1] as usize
        {
            product[problem.row_indices[position] as usize] +=
                coefficient * problem.values[position];
        }
    }
    let failures = product
        .iter()
        .zip(&problem.rhs)
        .filter(|(left, right)| **left != &denominator * **right)
        .count();
    (failures == 0, failures, denominator)
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

pub fn solve(config: &SolveConfig) -> Result<BigReport, String> {
    if config.max_steps == 0 {
        return Err("big reconstruction needs at least one step".to_string());
    }
    let started = Instant::now();
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
    let mut residues = vec![BigUint::zero(); problem.columns];
    let mut modulus = BigUint::one();
    let prime_big = BigUint::from(config.prime);
    let mut solve_seconds = Vec::new();
    let mut matvec_seconds = Vec::new();
    let mut attempts = Vec::new();
    let mut recovered = None;
    let mut recovered_iteration = 0;
    for iteration in 1..=config.max_steps {
        let phase = Instant::now();
        let digit = factor.solve(&problem.selected_rhs_mod(&residual, config.prime))?;
        solve_seconds.push(phase.elapsed().as_secs_f64());
        for (value, &new_digit) in residues.iter_mut().zip(&digit) {
            *value += &modulus * new_digit;
        }
        modulus *= &prime_big;
        let phase = Instant::now();
        let product = problem.matvec_digits(&digit);
        for row in 0..problem.rows {
            let difference = residual[row] - product[row];
            if difference.rem_euclid(config.prime as i128) != 0 {
                return Err(format!(
                    "nondivisible big-Dixon residual at iteration {iteration}"
                ));
            }
            residual[row] = difference / config.prime as i128;
        }
        matvec_seconds.push(phase.elapsed().as_secs_f64());
        if iteration % config.reconstruct_every != 0 {
            continue;
        }
        let reconstructed: Vec<Option<BigRational>> = residues
            .iter()
            .map(|value| reconstruct(value, &modulus))
            .collect();
        let count = reconstructed.iter().filter(|value| value.is_some()).count();
        let candidate: Vec<BigRational> = reconstructed.iter().filter_map(Clone::clone).collect();
        let exact_check_pass = count == problem.columns && verify(&problem, &candidate).0;
        attempts.push(Attempt {
            iteration_numerator: iteration,
            modulus_bits: modulus.bits(),
            reconstructed_coordinates_numerator: count,
            reconstructed_coordinates_denominator: problem.columns,
            exact_check_pass,
        });
        if exact_check_pass {
            recovered = Some(candidate);
            recovered_iteration = iteration;
            break;
        }
    }
    let recovered =
        recovered.ok_or_else(|| "big rational reconstruction did not verify".to_string())?;
    let (pass, failures, denominator) = verify(&problem, &recovered);
    if !pass || failures != 0 {
        return Err("big final verification failed".to_string());
    }
    let support = recovered
        .iter()
        .filter(|value| !value.numerator.is_zero())
        .count();
    let mut mutated = recovered.clone();
    let first = mutated
        .iter()
        .position(|value| !value.numerator.is_zero())
        .ok_or_else(|| "zero recovered vector".to_string())?;
    let mutation_delta = mutated[first].denominator.clone();
    mutated[first].numerator += mutation_delta;
    let (mutation_pass, mutation_failures, _) = verify(&problem, &mutated);
    if mutation_pass || mutation_failures == 0 {
        return Err("big +1 mutation unexpectedly passed".to_string());
    }
    let coefficients = recovered
        .iter()
        .zip(&problem.source_indices)
        .filter(|(value, _)| !value.numerator.is_zero())
        .map(|(value, &source_index)| Coefficient {
            source_index,
            numerator: value.numerator.to_string(),
            denominator: value.denominator.to_string(),
        })
        .collect();
    Ok(BigReport {
        schema: "max11-lift-large-big-result-v1",
        verdict: "PASS",
        input: config.input.display().to_string(),
        rows_checked_denominator: problem.rows,
        columns_denominator: problem.columns,
        csc_nonzeros_numerator: problem.values.len(),
        prime: config.prime,
        threads_maximum: config.threads,
        lu_total_seconds: factor.timings.total.as_secs_f64(),
        modular_solve_seconds_by_iteration: solve_seconds,
        csc_matvec_seconds_by_iteration: matvec_seconds,
        iterations_to_reconstruction_numerator: recovered_iteration,
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
        total_seconds: started.elapsed().as_secs_f64(),
        coefficients,
        no_claim: "Arbitrary-precision reconstruction concerns only the named finite input matrix.",
    })
}
