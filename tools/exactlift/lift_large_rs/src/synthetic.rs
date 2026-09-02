use crate::modular::BlockFactor;
use crate::rational::{Rational, lcm_u128, reconstruct};
use rayon::prelude::*;
use serde::Serialize;
use std::fs;
use std::time::Instant;

const SCHEMA: &str = "max11-lift-large-synthetic-v1";

#[derive(Clone, Debug)]
pub struct SyntheticConfig {
    pub rank: usize,
    pub union_rows: usize,
    pub planted_support: usize,
    pub denominator_block: usize,
    pub prime: u32,
    pub lu_block: usize,
    pub row_tile: usize,
    pub threads: usize,
    pub seed: u64,
    pub max_steps: usize,
    pub reconstruct_every: usize,
}

#[derive(Debug)]
pub struct DenseCsc16 {
    pub rows: usize,
    pub columns: usize,
    pub column_offsets: Vec<u64>,
    pub row_indices: Vec<u16>,
    pub values: Vec<i16>,
    pub actual_nonzeros: u64,
}

#[derive(Serialize)]
struct ReconstructionAttempt {
    iteration_numerator: usize,
    modulus_bits: u32,
    reconstructed_coordinates_numerator: usize,
    reconstructed_coordinates_denominator: usize,
    candidate_support_numerator: usize,
    candidate_support_denominator: usize,
    exact_check_attempted: bool,
    exact_check_pass: bool,
    reconstruction_seconds: f64,
    exact_check_seconds: f64,
}

#[derive(Serialize)]
pub struct SyntheticReport {
    schema: &'static str,
    verdict: &'static str,
    subject: &'static str,
    rank_denominator: usize,
    union_rows_denominator: usize,
    structural_csc_entries_numerator: u64,
    structural_csc_entries_denominator: u64,
    actual_nonzero_csc_entries_numerator: u64,
    entries_bound: &'static str,
    planted_support_numerator: usize,
    planted_support_denominator: usize,
    planted_denominator_lcm: u128,
    modulus_prime: u32,
    lu_block: usize,
    threads_maximum: usize,
    dense_modular_storage_bytes: u64,
    csc_storage_bytes: u64,
    generation_seconds: f64,
    dense_materialization_seconds: f64,
    lu_total_seconds: f64,
    lu_diagonal_inverse_seconds: f64,
    lu_lower_solve_seconds: f64,
    lu_schur_update_seconds: f64,
    modular_solve_seconds_by_iteration: Vec<f64>,
    csc_matvec_seconds_by_iteration: Vec<f64>,
    iterations_to_reconstruction_numerator: usize,
    reconstruction_attempts: Vec<ReconstructionAttempt>,
    exact_rows_verified_numerator: usize,
    exact_rows_verified_denominator: usize,
    recovered_support_numerator: usize,
    recovered_support_denominator: usize,
    recovered_denominator_lcm: u128,
    mutation_delta: &'static str,
    mutation_nonzero_rows_numerator: usize,
    mutation_rows_checked_denominator: usize,
    max_rss_kib: u64,
    total_seconds: f64,
    no_claim: &'static str,
}

fn splitmix64(mut state: u64) -> u64 {
    state = state.wrapping_add(0x9e37_79b9_7f4a_7c15);
    state = (state ^ (state >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    state = (state ^ (state >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    state ^ (state >> 31)
}

#[inline]
fn mixing_value(seed: u64, row: usize, column: usize) -> i16 {
    let state = seed
        ^ (row as u64).wrapping_mul(0xd6e8_feb8_6659_fd93)
        ^ (column as u64).wrapping_mul(0xa076_1d64_78bd_642f);
    (splitmix64(state) % 601) as i16 - 300
}

#[inline]
fn synthetic_entry(config: &SyntheticConfig, row: usize, column: usize) -> i16 {
    let current = mixing_value(config.seed, row, column) as i32;
    if column < config.planted_support {
        let previous = if column % config.denominator_block == 0 {
            0
        } else {
            mixing_value(config.seed, row, column - 1) as i32
        };
        (2 * current + previous) as i16
    } else {
        current as i16
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

fn planted_solution(config: &SyntheticConfig) -> Vec<Rational> {
    let mut result = vec![Rational { numerator: 0, denominator: 1 }; config.rank];
    for start in (0..config.planted_support).step_by(config.denominator_block) {
        let width = config.denominator_block.min(config.planted_support - start);
        for local in 0..width {
            let exponent = width - local;
            result[start + local] = Rational {
                numerator: if exponent % 2 == 1 { 1 } else { -1 },
                denominator: 1_i128 << exponent,
            };
        }
    }
    result
}

fn rhs(config: &SyntheticConfig) -> Vec<i128> {
    (0..config.union_rows)
        .into_par_iter()
        .map(|row| {
            (config.denominator_block - 1..config.planted_support)
                .step_by(config.denominator_block)
                .map(|column| mixing_value(config.seed, row, column) as i128)
                .sum()
        })
        .collect()
}

fn generate_csc(config: &SyntheticConfig) -> DenseCsc16 {
    assert!(config.union_rows <= u16::MAX as usize);
    let total = config.rank * config.union_rows;
    let mut row_indices = vec![0_u16; total];
    let mut values = vec![0_i16; total];
    let actual_nonzeros: u64 = row_indices
        .par_chunks_mut(config.union_rows)
        .zip(values.par_chunks_mut(config.union_rows))
        .enumerate()
        .map(|(column, (rows, column_values))| {
            let mut count = 0_u64;
            for row in 0..config.union_rows {
                rows[row] = row as u16;
                let value = synthetic_entry(config, row, column);
                column_values[row] = value;
                count += u64::from(value != 0);
            }
            count
        })
        .sum();
    let column_offsets = (0..=config.rank)
        .map(|column| (column * config.union_rows) as u64)
        .collect();
    DenseCsc16 {
        rows: config.union_rows,
        columns: config.rank,
        column_offsets,
        row_indices,
        values,
        actual_nonzeros,
    }
}

fn dense_modular(config: &SyntheticConfig) -> Vec<u32> {
    let p = config.prime as i32;
    let mut dense = vec![0_u32; config.rank * config.rank];
    dense
        .par_chunks_mut(config.rank)
        .enumerate()
        .for_each(|(row, output)| {
            for (column, value) in output.iter_mut().enumerate() {
                *value = (synthetic_entry(config, row, column) as i32).rem_euclid(p) as u32;
            }
        });
    dense
}

impl DenseCsc16 {
    fn matvec_digits(&self, digits: &[u32]) -> Vec<i128> {
        assert_eq!(digits.len(), self.columns);
        (0..self.columns)
            .into_par_iter()
            .fold(
                || vec![0_i128; self.rows],
                |mut accumulator, column| {
                    let digit = digits[column] as i128;
                    if digit == 0 {
                        return accumulator;
                    }
                    let start = self.column_offsets[column] as usize;
                    let end = self.column_offsets[column + 1] as usize;
                    for position in start..end {
                        accumulator[self.row_indices[position] as usize] +=
                            self.values[position] as i128 * digit;
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
        assert_eq!(scaled.len(), self.columns);
        (0..self.columns)
            .into_par_iter()
            .fold(
                || vec![0_i128; self.rows],
                |mut accumulator, column| {
                    let coefficient = scaled[column];
                    if coefficient == 0 {
                        return accumulator;
                    }
                    let start = self.column_offsets[column] as usize;
                    let end = self.column_offsets[column + 1] as usize;
                    for position in start..end {
                        accumulator[self.row_indices[position] as usize] +=
                            self.values[position] as i128 * coefficient;
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

fn candidate_common_scale(candidate: &[Rational]) -> Option<(u128, Vec<i128>)> {
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

fn verify_candidate(csc: &DenseCsc16, rhs: &[i128], candidate: &[Rational]) -> (bool, usize) {
    let Some((denominator, scaled)) = candidate_common_scale(candidate) else {
        return (false, 0);
    };
    let product = csc.exact_scaled_matvec(&scaled);
    let failures = product
        .iter()
        .zip(rhs)
        .filter(|(left, right)| **left != **right * denominator as i128)
        .count();
    (failures == 0, failures)
}

pub fn run(config: &SyntheticConfig) -> Result<SyntheticReport, String> {
    if config.rank == 0
        || config.union_rows < config.rank
        || config.planted_support == 0
        || config.planted_support > config.rank
        || config.denominator_block == 0
        || config.planted_support % config.denominator_block != 0
    {
        return Err("invalid synthetic dimensions/support".to_string());
    }
    rayon::ThreadPoolBuilder::new()
        .num_threads(config.threads)
        .build_global()
        .map_err(|error| error.to_string())?;
    let total_started = Instant::now();
    let phase = Instant::now();
    let csc = generate_csc(config);
    let right_hand_side = rhs(config);
    let generation_seconds = phase.elapsed().as_secs_f64();

    let phase = Instant::now();
    let dense = dense_modular(config);
    let dense_materialization_seconds = phase.elapsed().as_secs_f64();
    let factor = BlockFactor::factor(
        dense,
        config.rank,
        config.lu_block,
        config.prime,
        config.threads,
        config.row_tile,
    )?;

    let mut residual = right_hand_side.clone();
    let mut residue = vec![0_u128; config.rank];
    let mut modulus = 1_u128;
    let mut solve_seconds = Vec::new();
    let mut matvec_seconds = Vec::new();
    let mut attempts = Vec::new();
    let mut recovered = None;
    let mut recovered_iteration = 0;

    for iteration in 1..=config.max_steps {
        let solve_started = Instant::now();
        let rhs_modular: Vec<u32> = residual[..config.rank]
            .iter()
            .map(|value| value.rem_euclid(config.prime as i128) as u32)
            .collect();
        let digit = factor.solve(&rhs_modular)?;
        solve_seconds.push(solve_started.elapsed().as_secs_f64());
        for (value, &new_digit) in residue.iter_mut().zip(&digit) {
            *value += modulus * new_digit as u128;
        }
        modulus = modulus
            .checked_mul(config.prime as u128)
            .ok_or_else(|| "p-adic modulus overflow".to_string())?;

        let matvec_started = Instant::now();
        let product = csc.matvec_digits(&digit);
        for row in 0..config.union_rows {
            let difference = residual[row] - product[row];
            if difference.rem_euclid(config.prime as i128) != 0 {
                return Err(format!("nondivisible Dixon residual at iteration {iteration}, row {row}"));
            }
            residual[row] = difference / config.prime as i128;
        }
        matvec_seconds.push(matvec_started.elapsed().as_secs_f64());

        if iteration % config.reconstruct_every != 0 {
            continue;
        }
        let reconstruction_started = Instant::now();
        let reconstructed: Vec<Option<Rational>> = residue
            .iter()
            .map(|&value| reconstruct(value, modulus))
            .collect();
        let reconstructed_count = reconstructed.iter().filter(|value| value.is_some()).count();
        let candidate: Vec<Rational> = reconstructed.iter().filter_map(|value| *value).collect();
        let candidate_support = candidate.iter().filter(|value| value.numerator != 0).count();
        let reconstruction_seconds = reconstruction_started.elapsed().as_secs_f64();
        let exact_check_attempted = reconstructed_count == config.rank
            && candidate_support <= config.planted_support * 2;
        let exact_started = Instant::now();
        let exact_check_pass = exact_check_attempted
            && verify_candidate(&csc, &right_hand_side, &candidate).0;
        let exact_check_seconds = if exact_check_attempted {
            exact_started.elapsed().as_secs_f64()
        } else {
            0.0
        };
        attempts.push(ReconstructionAttempt {
            iteration_numerator: iteration,
            modulus_bits: 128 - modulus.leading_zeros(),
            reconstructed_coordinates_numerator: reconstructed_count,
            reconstructed_coordinates_denominator: config.rank,
            candidate_support_numerator: candidate_support,
            candidate_support_denominator: config.rank,
            exact_check_attempted,
            exact_check_pass,
            reconstruction_seconds,
            exact_check_seconds,
        });
        if exact_check_pass {
            recovered = Some(candidate);
            recovered_iteration = iteration;
            break;
        }
    }
    let recovered = recovered.ok_or_else(|| "early rational reconstruction did not verify".to_string())?;
    let expected = planted_solution(config);
    if recovered != expected {
        return Err("verified solution differs from planted unique solution".to_string());
    }
    let recovered_support = recovered.iter().filter(|value| value.numerator != 0).count();
    let recovered_lcm = candidate_common_scale(&recovered)
        .ok_or_else(|| "denominator LCM overflow".to_string())?
        .0;
    let mut mutated = recovered.clone();
    mutated[0].numerator += mutated[0].denominator;
    let (mutation_pass, mutation_failures) = verify_candidate(&csc, &right_hand_side, &mutated);
    if mutation_pass || mutation_failures == 0 {
        return Err("planted mutation unexpectedly passed".to_string());
    }

    let structural = (config.rank * config.union_rows) as u64;
    let report = SyntheticReport {
        schema: SCHEMA,
        verdict: "PASS",
        subject: "dense non-block-diagonal A=L*B with hidden bidiagonal denominator blocks",
        rank_denominator: config.rank,
        union_rows_denominator: config.union_rows,
        structural_csc_entries_numerator: structural,
        structural_csc_entries_denominator: structural,
        actual_nonzero_csc_entries_numerator: csc.actual_nonzeros,
        entries_bound: "every integer matrix entry lies in [-900,900]",
        planted_support_numerator: config.planted_support,
        planted_support_denominator: config.rank,
        planted_denominator_lcm: expected
            .iter()
            .map(|value| value.denominator as u128)
            .fold(1, |left, right| lcm_u128(left, right).unwrap()),
        modulus_prime: config.prime,
        lu_block: config.lu_block,
        threads_maximum: config.threads,
        dense_modular_storage_bytes: (config.rank * config.rank * size_of::<u32>()) as u64,
        csc_storage_bytes: (csc.values.len() * size_of::<i16>()
            + csc.row_indices.len() * size_of::<u16>()
            + csc.column_offsets.len() * size_of::<u64>()) as u64,
        generation_seconds,
        dense_materialization_seconds,
        lu_total_seconds: factor.timings.total.as_secs_f64(),
        lu_diagonal_inverse_seconds: factor.timings.diagonal_inverse.as_secs_f64(),
        lu_lower_solve_seconds: factor.timings.lower_solve.as_secs_f64(),
        lu_schur_update_seconds: factor.timings.schur_update.as_secs_f64(),
        modular_solve_seconds_by_iteration: solve_seconds,
        csc_matvec_seconds_by_iteration: matvec_seconds,
        iterations_to_reconstruction_numerator: recovered_iteration,
        reconstruction_attempts: attempts,
        exact_rows_verified_numerator: config.union_rows,
        exact_rows_verified_denominator: config.union_rows,
        recovered_support_numerator: recovered_support,
        recovered_support_denominator: config.rank,
        recovered_denominator_lcm: recovered_lcm,
        mutation_delta: "+1/1 at coordinate 0",
        mutation_nonzero_rows_numerator: mutation_failures,
        mutation_rows_checked_denominator: config.union_rows,
        max_rss_kib: max_rss_kib(),
        total_seconds: total_started.elapsed().as_secs_f64(),
        no_claim: "This is a finite synthetic dense known-answer control, not an n=11 matrix and not evidence of MAX11 membership.",
    };
    Ok(report)
}
