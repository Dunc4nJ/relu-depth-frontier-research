use anyhow::{Result, ensure};
use max11_colgen::SparseColumn;
use rayon::prelude::*;
use serde::Serialize;
use std::time::Instant;

const CBLAS_COL_MAJOR: i32 = 102;
const CBLAS_NO_TRANS: i32 = 111;

unsafe extern "C" {
    fn cblas_dgemm(
        layout: i32,
        trans_a: i32,
        trans_b: i32,
        m: i32,
        n: i32,
        k: i32,
        alpha: f64,
        a: *const f64,
        lda: i32,
        b: *const f64,
        ldb: i32,
        beta: f64,
        c: *mut f64,
        ldc: i32,
    );
    fn openblas_set_num_threads(num_threads: i32);
}

pub fn set_blas_threads(threads: usize) -> Result<()> {
    ensure!((1..=64).contains(&threads), "invalid OpenBLAS thread count");
    unsafe { openblas_set_num_threads(i32::try_from(threads)?) };
    Ok(())
}

fn splitmix64(mut value: u64) -> u64 {
    value = value.wrapping_add(0x9e37_79b9_7f4a_7c15);
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

#[derive(Clone, Debug, Serialize)]
pub struct SketchSpec {
    pub algorithm: &'static str,
    pub seed: u64,
    pub buckets: usize,
}

impl SketchSpec {
    pub fn new(seed: u64, buckets: usize) -> Result<Self> {
        ensure!(
            buckets > 0 && buckets <= u32::MAX as usize,
            "invalid bucket count"
        );
        Ok(Self {
            algorithm: "splitmix64-chain-v1-one-bucket-random-sign",
            seed,
            buckets,
        })
    }

    fn finish(&self, state: u64) -> (usize, bool) {
        let bucket_hash = splitmix64(state ^ 0xa076_1d64_78bd_642f);
        let sign_hash = splitmix64(state ^ 0xe703_7ed1_a0b4_28db);
        (
            (bucket_hash % self.buckets as u64) as usize,
            sign_hash & 1 == 0,
        )
    }

    pub fn linear_row(&self, n: usize, rank: usize) -> (usize, bool) {
        let state = splitmix64(
            self.seed ^ 0x6c69_6e65_6172_0001 ^ (n as u64).wrapping_mul(0x9e37_79b9) ^ rank as u64,
        );
        self.finish(state)
    }

    pub fn hinge_row(&self, direction: &[i16]) -> (usize, bool) {
        let mut state = splitmix64(
            self.seed ^ 0x6869_6e67_6500_0001 ^ (direction.len() as u64).wrapping_mul(0x9e37_79b9),
        );
        for (index, &coordinate) in direction.iter().enumerate() {
            let encoded = coordinate as u16 as u64;
            state =
                splitmix64(state ^ encoded ^ (index as u64).wrapping_mul(0xd6e8_feb8_6659_fd93));
        }
        self.finish(state)
    }

    pub fn sketch_column(&self, column: &SparseColumn, prime: u32, output: &mut [u32]) {
        debug_assert_eq!(output.len(), self.buckets);
        output.fill(0);
        for (rank, &coefficient) in column.linear.iter().enumerate() {
            if coefficient != 0 {
                let (bucket, positive) = self.linear_row(column.linear.len(), rank);
                add_signed(&mut output[bucket], coefficient, positive, prime);
            }
        }
        for (direction, &coefficient) in &column.hinges {
            if coefficient != 0 {
                let (bucket, positive) = self.hinge_row(direction);
                add_signed(&mut output[bucket], coefficient, positive, prime);
            }
        }
    }
}

fn add_signed(target: &mut u32, value: i64, positive: bool, prime: u32) {
    let residue = (value as i128).rem_euclid(prime as i128) as u32;
    if positive {
        let sum = *target + residue;
        *target = if sum >= prime { sum - prime } else { sum };
    } else {
        *target = if *target >= residue {
            *target - residue
        } else {
            *target + prime - residue
        };
    }
}

fn mod_inverse(value: u32, prime: u32) -> u32 {
    let (mut old_r, mut r) = (value as i64, prime as i64);
    let (mut old_s, mut s) = (1i64, 0i64);
    while r != 0 {
        let quotient = old_r / r;
        (old_r, r) = (r, old_r - quotient * r);
        (old_s, s) = (s, old_s - quotient * s);
    }
    assert_eq!(old_r, 1, "pivot is not invertible modulo the named prime");
    old_s.rem_euclid(prime as i64) as u32
}

#[derive(Clone, Copy, Debug)]
struct Modulus {
    value: u32,
    reciprocal: u64,
}

impl Modulus {
    fn new(value: u32) -> Self {
        Self {
            value,
            reciprocal: ((1u128 << 64) / value as u128) as u64,
        }
    }

    fn reduce_u64(self, input: u64) -> u32 {
        let quotient = ((input as u128 * self.reciprocal as u128) >> 64) as u64;
        let mut remainder = input - quotient * self.value as u64;
        if remainder >= self.value as u64 {
            remainder -= self.value as u64;
        }
        debug_assert!(remainder < self.value as u64);
        remainder as u32
    }

    fn reduce_i64(self, input: i64) -> u32 {
        let remainder = self.reduce_u64(input.unsigned_abs());
        if input < 0 && remainder != 0 {
            self.value - remainder
        } else {
            remainder
        }
    }
}

fn scale_mod(vector: &mut [u32], factor: u32, modulus: Modulus) {
    vector.par_iter_mut().for_each(|value| {
        *value = modulus.reduce_u64(*value as u64 * factor as u64);
    });
}

fn subtract_multiple(target: &mut [u32], source: &[u32], factor: u32, modulus: Modulus) {
    debug_assert_eq!(target.len(), source.len());
    target.iter_mut().zip(source).for_each(|(left, &right)| {
        let product = modulus.reduce_u64(right as u64 * factor as u64);
        *left = if *left >= product {
            *left - product
        } else {
            *left + modulus.value - product
        };
    });
}

#[derive(Clone, Debug, Default, Serialize)]
pub struct ReducerMetrics {
    pub gemm_calls: u64,
    pub gemm_scalar_products_numerator: u128,
    pub gemm_seconds: f64,
    pub pack_seconds: f64,
    pub modular_reduce_seconds: f64,
    pub basis_maintenance_scalar_products_numerator: u128,
}

#[derive(Debug)]
pub struct DenseEchelon {
    rows: usize,
    prime: u32,
    modulus: Modulus,
    block_size: usize,
    basis: Vec<u32>,
    pivot_rows: Vec<usize>,
    pivot_columns: Vec<u64>,
    occupied: Vec<bool>,
    pub metrics: ReducerMetrics,
}

impl DenseEchelon {
    pub fn new(rows: usize, prime: u32, block_size: usize) -> Result<Self> {
        ensure!(rows > 0, "rank engine needs at least one row");
        ensure!(is_prime(prime), "modulus {prime} is not prime");
        ensure!(prime < (1 << 20), "prime must be below 2^20");
        ensure!(block_size > 0, "GEMM block must be positive");
        let worst = block_size as u128 * (prime as u128 - 1).pow(2) + prime as u128;
        ensure!(
            worst < (1u128 << 53),
            "GEMM block violates exact-binary64 accumulation bound"
        );
        Ok(Self {
            rows,
            prime,
            modulus: Modulus::new(prime),
            block_size,
            basis: Vec::new(),
            pivot_rows: Vec::new(),
            pivot_columns: Vec::new(),
            occupied: vec![false; rows],
            metrics: ReducerMetrics::default(),
        })
    }

    pub fn rank(&self) -> usize {
        self.pivot_rows.len()
    }

    pub fn storage_bytes(&self) -> usize {
        self.basis.len() * std::mem::size_of::<u32>()
    }

    pub fn pivot_rows(&self) -> &[usize] {
        &self.pivot_rows
    }

    pub fn pivot_columns(&self) -> &[u64] {
        &self.pivot_columns
    }

    fn reduce_existing(&mut self, matrix: &mut [u32], columns: usize) -> Result<()> {
        ensure!(matrix.len() == self.rows * columns, "batch shape mismatch");
        for start in (0..self.rank()).step_by(self.block_size) {
            let count = (self.rank() - start).min(self.block_size);
            let packed_at = Instant::now();
            let mut packed_basis = vec![0f64; self.rows * count];
            packed_basis
                .par_chunks_mut(self.rows)
                .enumerate()
                .for_each(|(local, packed)| {
                    let source =
                        &self.basis[(start + local) * self.rows..(start + local + 1) * self.rows];
                    packed
                        .iter_mut()
                        .zip(source)
                        .for_each(|(to, &from)| *to = from as f64);
                });
            let mut coefficients = vec![0f64; count * columns];
            coefficients
                .par_chunks_mut(count)
                .enumerate()
                .for_each(|(column, values)| {
                    for (local, value) in values.iter_mut().enumerate() {
                        *value = matrix[column * self.rows + self.pivot_rows[start + local]] as f64;
                    }
                });
            let mut dense: Vec<f64> = matrix.par_iter().map(|&value| value as f64).collect();
            self.metrics.pack_seconds += packed_at.elapsed().as_secs_f64();
            let gemm_at = Instant::now();
            unsafe {
                cblas_dgemm(
                    CBLAS_COL_MAJOR,
                    CBLAS_NO_TRANS,
                    CBLAS_NO_TRANS,
                    i32::try_from(self.rows)?,
                    i32::try_from(columns)?,
                    i32::try_from(count)?,
                    -1.0,
                    packed_basis.as_ptr(),
                    i32::try_from(self.rows)?,
                    coefficients.as_ptr(),
                    i32::try_from(count)?,
                    1.0,
                    dense.as_mut_ptr(),
                    i32::try_from(self.rows)?,
                );
            }
            self.metrics.gemm_seconds += gemm_at.elapsed().as_secs_f64();
            self.metrics.gemm_calls += 1;
            self.metrics.gemm_scalar_products_numerator +=
                self.rows as u128 * count as u128 * columns as u128;
            let reduce_at = Instant::now();
            let modulus = self.modulus;
            matrix
                .par_iter_mut()
                .zip(dense.par_iter())
                .for_each(|(output, &value)| {
                    let integer = value as i64;
                    debug_assert_eq!(integer as f64, value);
                    *output = modulus.reduce_i64(integer);
                });
            self.metrics.modular_reduce_seconds += reduce_at.elapsed().as_secs_f64();
        }
        Ok(())
    }

    pub fn reduce_only(&mut self, vector: &mut [u32]) -> Result<()> {
        self.reduce_existing(vector, 1)
    }

    pub fn process_batch(&mut self, matrix: &mut [u32], source_columns: &[u64]) -> Result<()> {
        let columns = source_columns.len();
        ensure!(matrix.len() == self.rows * columns, "batch shape mismatch");
        self.reduce_existing(matrix, columns)?;
        for column in 0..columns {
            let range = column * self.rows..(column + 1) * self.rows;
            for &pivot in &self.pivot_rows {
                ensure!(
                    matrix[range.start + pivot] == 0,
                    "nonzero at an existing pivot after reduction"
                );
            }
            let Some(pivot) =
                (0..self.rows).find(|&row| !self.occupied[row] && matrix[range.start + row] != 0)
            else {
                continue;
            };
            let inverse = mod_inverse(matrix[range.start + pivot], self.prime);
            scale_mod(&mut matrix[range.clone()], inverse, self.modulus);
            let vector = matrix[range.clone()].to_vec();

            let block_start = self.rank() / self.block_size * self.block_size;
            let prior_in_block = self.rank() - block_start;
            if prior_in_block > 0 {
                let modulus = self.modulus;
                let rows = self.rows;
                self.basis[block_start * rows..]
                    .par_chunks_mut(rows)
                    .for_each(|basis_column| {
                        let factor = basis_column[pivot];
                        if factor != 0 {
                            subtract_multiple(basis_column, &vector, factor, modulus);
                        }
                    });
                self.metrics.basis_maintenance_scalar_products_numerator +=
                    self.rows as u128 * prior_in_block as u128;
            }

            self.basis.extend_from_slice(&vector);
            self.pivot_rows.push(pivot);
            self.pivot_columns.push(source_columns[column]);
            self.occupied[pivot] = true;

            if column + 1 < columns {
                let modulus = self.modulus;
                let rows = self.rows;
                matrix[(column + 1) * rows..]
                    .par_chunks_mut(rows)
                    .for_each(|later| {
                        let factor = later[pivot];
                        if factor != 0 {
                            subtract_multiple(later, &vector, factor, modulus);
                        }
                    });
                self.metrics.basis_maintenance_scalar_products_numerator +=
                    self.rows as u128 * (columns - column - 1) as u128;
            }
        }
        Ok(())
    }
}

pub fn is_prime(value: u32) -> bool {
    if value < 2 {
        return false;
    }
    if value.is_multiple_of(2) {
        return value == 2;
    }
    let mut divisor = 3u32;
    while divisor as u64 * divisor as u64 <= value as u64 {
        if value.is_multiple_of(divisor) {
            return false;
        }
        divisor += 2;
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    fn scalar_rank(mut columns: Vec<Vec<u32>>, rows: usize, prime: u32) -> usize {
        let modulus = Modulus::new(prime);
        let mut pivots = vec![false; rows];
        let mut basis: Vec<Vec<u32>> = Vec::new();
        let mut pivot_rows = Vec::new();
        for vector in &mut columns {
            for (known, &pivot) in basis.iter().zip(&pivot_rows) {
                let factor = vector[pivot];
                if factor != 0 {
                    subtract_multiple(vector, known, factor, modulus);
                }
            }
            if let Some(pivot) = (0..rows).find(|&row| !pivots[row] && vector[row] != 0) {
                let inverse = mod_inverse(vector[pivot], prime);
                scale_mod(vector, inverse, modulus);
                pivots[pivot] = true;
                pivot_rows.push(pivot);
                basis.push(vector.clone());
            }
        }
        basis.len()
    }

    #[test]
    fn blocked_basis_matches_scalar_rank() {
        set_blas_threads(1).unwrap();
        let rows = 17;
        let prime = 101;
        let mut columns = Vec::new();
        for column in 0..31 {
            columns.push(
                (0..rows)
                    .map(|row| {
                        ((column * 19 + row * 23 + column * row * 7 + 3) % prime as usize) as u32
                    })
                    .collect::<Vec<_>>(),
            );
        }
        let expected = scalar_rank(columns.clone(), rows, prime);
        let mut engine = DenseEchelon::new(rows, prime, 5).unwrap();
        for start in (0..columns.len()).step_by(7) {
            let stop = (start + 7).min(columns.len());
            let mut batch = Vec::new();
            for column in &columns[start..stop] {
                batch.extend_from_slice(column);
            }
            engine
                .process_batch(&mut batch, &(start as u64..stop as u64).collect::<Vec<_>>())
                .unwrap();
        }
        assert_eq!(engine.rank(), expected);
        for block in (0..engine.rank()).step_by(engine.block_size) {
            let stop = (block + engine.block_size).min(engine.rank());
            for left in block..stop {
                for right in block..stop {
                    assert_eq!(
                        engine.basis[left * rows + engine.pivot_rows[right]],
                        u32::from(left == right)
                    );
                }
            }
        }
    }

    #[test]
    fn sketch_is_deterministic_and_seeded() {
        let a = SketchSpec::new(11, 97).unwrap();
        let b = SketchSpec::new(12, 97).unwrap();
        assert_eq!(a.hinge_row(&[1, -1, 0]), a.hinge_row(&[1, -1, 0]));
        assert_ne!(a.hinge_row(&[1, -1, 0]), b.hinge_row(&[1, -1, 0]));
        assert_ne!(
            a.linear_row(10, 9),
            a.hinge_row(&[0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
        );
    }

    #[test]
    fn rejects_unsafe_binary64_block() {
        assert!(DenseEchelon::new(10, 1_000_033, 10_000).is_err());
        assert!(DenseEchelon::new(10, 1_000_033, 4_096).is_ok());
    }

    #[test]
    fn barrett_reduction_matches_division() {
        for prime in [101u32, 1_000_003, 1_000_033] {
            let modulus = Modulus::new(prime);
            for value in [
                0u64,
                1,
                prime as u64 - 1,
                prime as u64,
                prime as u64 * prime as u64,
                (1u64 << 53) - 1,
            ] {
                assert_eq!(modulus.reduce_u64(value), (value % prime as u64) as u32);
                let signed = -(value as i64);
                assert_eq!(
                    modulus.reduce_i64(signed),
                    signed.rem_euclid(prime as i64) as u32
                );
            }
        }
    }
}
