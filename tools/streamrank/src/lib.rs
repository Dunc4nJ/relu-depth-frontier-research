use anyhow::{Result, ensure};
use max11_colgen::SparseColumn;
use rayon::prelude::*;
use serde::Serialize;
use std::time::Instant;

#[cfg(feature = "cuda")]
mod cuda;
#[cfg(feature = "cuda")]
pub use cuda::CudaDenseEchelon;

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
    pub old_basis_gemm_calls: u64,
    pub old_basis_gemm_scalar_products_numerator: u128,
    pub old_basis_gemm_seconds: f64,
    pub panel_future_gemm_calls: u64,
    pub panel_future_gemm_scalar_products_numerator: u128,
    pub panel_future_gemm_seconds: f64,
    pub panel_basis_gemm_calls: u64,
    pub panel_basis_gemm_scalar_products_numerator: u128,
    pub panel_basis_gemm_seconds: f64,
    pub gpu_peak_allocated_bytes: u64,
    pub gpu_host_to_device_bytes_numerator: u128,
    pub gpu_device_to_host_bytes_numerator: u128,
    pub gpu_transfer_seconds: f64,
}

#[derive(Clone, Copy)]
enum GemmKind {
    OldBasis,
    PanelFuture,
    PanelBasis,
}

struct GemmObservation {
    scalar_products: u128,
    pack_seconds: f64,
    gemm_seconds: f64,
    modular_reduce_seconds: f64,
}

fn delayed_modular_dgemm_subtract(
    target: &mut [u32],
    columns: usize,
    source: &[u32],
    source_columns: usize,
    coefficients: &[u32],
    rows: usize,
    modulus: Modulus,
) -> Result<GemmObservation> {
    ensure!(target.len() == rows * columns, "GEMM target shape mismatch");
    ensure!(
        source.len() == rows * source_columns,
        "GEMM source shape mismatch"
    );
    ensure!(
        coefficients.len() == source_columns * columns,
        "GEMM coefficient shape mismatch"
    );
    if columns == 0 || source_columns == 0 {
        return Ok(GemmObservation {
            scalar_products: 0,
            pack_seconds: 0.0,
            gemm_seconds: 0.0,
            modular_reduce_seconds: 0.0,
        });
    }

    let packed_at = Instant::now();
    let packed_source: Vec<f64> = source.par_iter().map(|&value| value as f64).collect();
    let packed_coefficients: Vec<f64> =
        coefficients.par_iter().map(|&value| value as f64).collect();
    let mut dense: Vec<f64> = target.par_iter().map(|&value| value as f64).collect();
    let pack_seconds = packed_at.elapsed().as_secs_f64();

    let gemm_at = Instant::now();
    unsafe {
        cblas_dgemm(
            CBLAS_COL_MAJOR,
            CBLAS_NO_TRANS,
            CBLAS_NO_TRANS,
            i32::try_from(rows)?,
            i32::try_from(columns)?,
            i32::try_from(source_columns)?,
            -1.0,
            packed_source.as_ptr(),
            i32::try_from(rows)?,
            packed_coefficients.as_ptr(),
            i32::try_from(source_columns)?,
            1.0,
            dense.as_mut_ptr(),
            i32::try_from(rows)?,
        );
    }
    let gemm_seconds = gemm_at.elapsed().as_secs_f64();

    let reduce_at = Instant::now();
    target
        .par_iter_mut()
        .zip(dense.par_iter())
        .for_each(|(output, &value)| {
            let integer = value as i64;
            debug_assert_eq!(integer as f64, value);
            *output = modulus.reduce_i64(integer);
        });
    let modular_reduce_seconds = reduce_at.elapsed().as_secs_f64();

    Ok(GemmObservation {
        scalar_products: rows as u128 * source_columns as u128 * columns as u128,
        pack_seconds,
        gemm_seconds,
        modular_reduce_seconds,
    })
}

#[derive(Debug)]
pub struct DenseEchelon {
    rows: usize,
    prime: u32,
    modulus: Modulus,
    block_size: usize,
    panel_size: usize,
    basis: Vec<u32>,
    pivot_rows: Vec<usize>,
    pivot_columns: Vec<u64>,
    occupied: Vec<bool>,
    pub metrics: ReducerMetrics,
}

impl DenseEchelon {
    pub fn new(rows: usize, prime: u32, block_size: usize) -> Result<Self> {
        Self::with_panel_size(rows, prime, block_size, 64)
    }

    pub fn with_panel_size(
        rows: usize,
        prime: u32,
        block_size: usize,
        panel_size: usize,
    ) -> Result<Self> {
        ensure!(rows > 0, "rank engine needs at least one row");
        ensure!(is_prime(prime), "modulus {prime} is not prime");
        ensure!(prime < (1 << 20), "prime must be below 2^20");
        ensure!(block_size > 0, "GEMM block must be positive");
        ensure!(panel_size > 0, "rank panel must be positive");
        let accumulation_terms = block_size.max(panel_size);
        let worst = accumulation_terms as u128 * (prime as u128 - 1).pow(2) + prime as u128;
        ensure!(
            worst < (1u128 << 53),
            "GEMM block violates exact-binary64 accumulation bound"
        );
        Ok(Self {
            rows,
            prime,
            modulus: Modulus::new(prime),
            block_size,
            panel_size,
            basis: Vec::new(),
            pivot_rows: Vec::new(),
            pivot_columns: Vec::new(),
            occupied: vec![false; rows],
            metrics: ReducerMetrics::default(),
        })
    }

    pub fn panel_size(&self) -> usize {
        self.panel_size
    }

    fn record_gemm(&mut self, observation: GemmObservation, kind: GemmKind) {
        if observation.scalar_products == 0 {
            return;
        }
        self.metrics.gemm_calls += 1;
        self.metrics.gemm_scalar_products_numerator += observation.scalar_products;
        self.metrics.gemm_seconds += observation.gemm_seconds;
        self.metrics.pack_seconds += observation.pack_seconds;
        self.metrics.modular_reduce_seconds += observation.modular_reduce_seconds;
        match kind {
            GemmKind::OldBasis => {
                self.metrics.old_basis_gemm_calls += 1;
                self.metrics.old_basis_gemm_scalar_products_numerator +=
                    observation.scalar_products;
                self.metrics.old_basis_gemm_seconds += observation.gemm_seconds;
            }
            GemmKind::PanelFuture => {
                self.metrics.panel_future_gemm_calls += 1;
                self.metrics.panel_future_gemm_scalar_products_numerator +=
                    observation.scalar_products;
                self.metrics.panel_future_gemm_seconds += observation.gemm_seconds;
            }
            GemmKind::PanelBasis => {
                self.metrics.panel_basis_gemm_calls += 1;
                self.metrics.panel_basis_gemm_scalar_products_numerator +=
                    observation.scalar_products;
                self.metrics.panel_basis_gemm_seconds += observation.gemm_seconds;
            }
        }
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

    pub fn dot_mod(&self, left: &[u32], right: &[u32]) -> Result<u32> {
        ensure!(
            left.len() == self.rows && right.len() == self.rows,
            "dot-product vector shape mismatch"
        );
        let mut result = 0u32;
        for (&a, &b) in left.iter().zip(right) {
            let product = self.modulus.reduce_u64(a as u64 * b as u64);
            let sum = result + product;
            result = if sum >= self.prime {
                sum - self.prime
            } else {
                sum
            };
        }
        Ok(result)
    }

    pub fn left_separator(&self, free_row: usize) -> Result<Vec<u32>> {
        ensure!(free_row < self.rows, "separator free row is out of range");
        ensure!(
            !self.occupied[free_row],
            "separator free row is a pivot row"
        );
        let mut separator = vec![0u32; self.rows];
        separator[free_row] = 1;
        for column in (0..self.rank()).rev() {
            let basis_column = &self.basis[column * self.rows..(column + 1) * self.rows];
            let mut sum = basis_column[free_row];
            for later in column + 1..self.rank() {
                let coefficient = separator[self.pivot_rows[later]];
                if coefficient == 0 {
                    continue;
                }
                let product = self
                    .modulus
                    .reduce_u64(coefficient as u64 * basis_column[self.pivot_rows[later]] as u64);
                let total = sum + product;
                sum = if total >= self.prime {
                    total - self.prime
                } else {
                    total
                };
            }
            separator[self.pivot_rows[column]] = if sum == 0 { 0 } else { self.prime - sum };
        }
        for column in self.basis.chunks_exact(self.rows) {
            ensure!(
                self.dot_mod(&separator, column)? == 0,
                "constructed separator does not annihilate the basis"
            );
        }
        Ok(separator)
    }

    fn reduce_existing(&mut self, matrix: &mut [u32], columns: usize) -> Result<()> {
        ensure!(matrix.len() == self.rows * columns, "batch shape mismatch");
        for start in (0..self.rank()).step_by(self.block_size) {
            let count = (self.rank() - start).min(self.block_size);
            let mut coefficients = vec![0u32; count * columns];
            coefficients
                .par_chunks_mut(count)
                .enumerate()
                .for_each(|(column, values)| {
                    for (local, value) in values.iter_mut().enumerate() {
                        *value = matrix[column * self.rows + self.pivot_rows[start + local]];
                    }
                });
            let observation = delayed_modular_dgemm_subtract(
                matrix,
                columns,
                &self.basis[start * self.rows..(start + count) * self.rows],
                count,
                &coefficients,
                self.rows,
                self.modulus,
            )?;
            self.record_gemm(observation, GemmKind::OldBasis);
        }
        Ok(())
    }

    fn clear_panel_from_prior_basis(
        &mut self,
        rank_before_panel: usize,
        panel_basis: &[u32],
        panel_pivots: &[usize],
    ) -> Result<()> {
        let rank_after_panel = rank_before_panel + panel_pivots.len();
        for block_start in (0..rank_after_panel).step_by(self.block_size) {
            let block_stop = (block_start + self.block_size).min(rank_after_panel);
            let old_stop = rank_before_panel.min(block_stop);
            let new_start = rank_before_panel.max(block_start);
            if block_start >= old_stop || new_start >= block_stop {
                continue;
            }
            let old_columns = old_stop - block_start;
            let panel_offset = new_start - rank_before_panel;
            let new_columns = block_stop - new_start;
            let mut coefficients = vec![0u32; new_columns * old_columns];
            for old_local in 0..old_columns {
                let old_column = block_start + old_local;
                for new_local in 0..new_columns {
                    coefficients[old_local * new_columns + new_local] =
                        self.basis[old_column * self.rows + panel_pivots[panel_offset + new_local]];
                }
            }
            let source =
                &panel_basis[panel_offset * self.rows..(panel_offset + new_columns) * self.rows];
            let target = &mut self.basis[block_start * self.rows..old_stop * self.rows];
            let observation = delayed_modular_dgemm_subtract(
                target,
                old_columns,
                source,
                new_columns,
                &coefficients,
                self.rows,
                self.modulus,
            )?;
            self.record_gemm(observation, GemmKind::PanelBasis);
        }
        Ok(())
    }

    fn clear_panel_from_future_columns(
        &mut self,
        matrix: &mut [u32],
        columns: usize,
        panel_basis: &[u32],
        panel_pivots: &[usize],
    ) -> Result<()> {
        if columns == 0 || panel_pivots.is_empty() {
            return Ok(());
        }
        let count = panel_pivots.len();
        let mut coefficients = vec![0u32; count * columns];
        coefficients
            .par_chunks_mut(count)
            .enumerate()
            .for_each(|(column, values)| {
                for (local, value) in values.iter_mut().enumerate() {
                    *value = matrix[column * self.rows + panel_pivots[local]];
                }
            });
        let observation = delayed_modular_dgemm_subtract(
            matrix,
            columns,
            panel_basis,
            count,
            &coefficients,
            self.rows,
            self.modulus,
        )?;
        self.record_gemm(observation, GemmKind::PanelFuture);
        Ok(())
    }

    pub fn reduce_only(&mut self, vector: &mut [u32]) -> Result<()> {
        self.reduce_existing(vector, 1)
    }

    pub fn process_batch(&mut self, matrix: &mut [u32], source_columns: &[u64]) -> Result<()> {
        let columns = source_columns.len();
        ensure!(matrix.len() == self.rows * columns, "batch shape mismatch");
        self.reduce_existing(matrix, columns)?;
        for panel_start in (0..columns).step_by(self.panel_size) {
            let panel_stop = (panel_start + self.panel_size).min(columns);
            let rank_before_panel = self.rank();
            for column in panel_start..panel_stop {
                let range = column * self.rows..(column + 1) * self.rows;
                for &pivot in &self.pivot_rows {
                    ensure!(
                        matrix[range.start + pivot] == 0,
                        "nonzero at an existing pivot after reduction"
                    );
                }
                let Some(pivot) = (0..self.rows)
                    .find(|&row| !self.occupied[row] && matrix[range.start + row] != 0)
                else {
                    continue;
                };
                let inverse = mod_inverse(matrix[range.start + pivot], self.prime);
                scale_mod(&mut matrix[range.clone()], inverse, self.modulus);
                let vector = matrix[range.clone()].to_vec();

                let prior_in_panel = self.rank() - rank_before_panel;
                if prior_in_panel > 0 {
                    let modulus = self.modulus;
                    let rows = self.rows;
                    self.basis[rank_before_panel * rows..]
                        .par_chunks_mut(rows)
                        .for_each(|basis_column| {
                            let factor = basis_column[pivot];
                            if factor != 0 {
                                subtract_multiple(basis_column, &vector, factor, modulus);
                            }
                        });
                    self.metrics.basis_maintenance_scalar_products_numerator +=
                        self.rows as u128 * prior_in_panel as u128;
                }

                self.basis.extend_from_slice(&vector);
                self.pivot_rows.push(pivot);
                self.pivot_columns.push(source_columns[column]);
                self.occupied[pivot] = true;

                if column + 1 < panel_stop {
                    let modulus = self.modulus;
                    let rows = self.rows;
                    matrix[(column + 1) * rows..panel_stop * rows]
                        .par_chunks_mut(rows)
                        .for_each(|later| {
                            let factor = later[pivot];
                            if factor != 0 {
                                subtract_multiple(later, &vector, factor, modulus);
                            }
                        });
                    self.metrics.basis_maintenance_scalar_products_numerator +=
                        self.rows as u128 * (panel_stop - column - 1) as u128;
                }
            }

            let rank_after_panel = self.rank();
            if rank_after_panel > rank_before_panel {
                let panel_basis = self.basis
                    [rank_before_panel * self.rows..rank_after_panel * self.rows]
                    .to_vec();
                let panel_pivots = self.pivot_rows[rank_before_panel..rank_after_panel].to_vec();
                self.clear_panel_from_prior_basis(rank_before_panel, &panel_basis, &panel_pivots)?;
                if panel_stop < columns {
                    self.clear_panel_from_future_columns(
                        &mut matrix[panel_stop * self.rows..],
                        columns - panel_stop,
                        &panel_basis,
                        &panel_pivots,
                    )?;
                }
            }
        }
        Ok(())
    }
}

#[derive(Debug)]
pub enum Echelon {
    Cpu(DenseEchelon),
    #[cfg(feature = "cuda")]
    Cuda(CudaDenseEchelon),
}

impl Echelon {
    pub fn with_backend(
        backend: &str,
        rows: usize,
        prime: u32,
        block_size: usize,
        panel_size: usize,
        max_batch: usize,
    ) -> Result<Self> {
        #[cfg(not(feature = "cuda"))]
        let _ = max_batch;
        match backend {
            "cpu" => Ok(Self::Cpu(DenseEchelon::with_panel_size(
                rows, prime, block_size, panel_size,
            )?)),
            #[cfg(feature = "cuda")]
            "cuda" => Ok(Self::Cuda(CudaDenseEchelon::with_panel_size(
                rows, prime, block_size, panel_size, max_batch,
            )?)),
            #[cfg(not(feature = "cuda"))]
            "cuda" => anyhow::bail!("CUDA backend requested from a build without --features cuda"),
            value => anyhow::bail!("unknown reducer backend {value:?}; expected cpu or cuda"),
        }
    }

    pub fn rank(&self) -> usize {
        match self {
            Self::Cpu(value) => value.rank(),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.rank(),
        }
    }

    pub fn storage_bytes(&self) -> usize {
        match self {
            Self::Cpu(value) => value.storage_bytes(),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.storage_bytes(),
        }
    }

    pub fn pivot_rows(&self) -> &[usize] {
        match self {
            Self::Cpu(value) => value.pivot_rows(),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.pivot_rows(),
        }
    }

    pub fn pivot_columns(&self) -> &[u64] {
        match self {
            Self::Cpu(value) => value.pivot_columns(),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.pivot_columns(),
        }
    }

    pub fn metrics(&self) -> &ReducerMetrics {
        match self {
            Self::Cpu(value) => &value.metrics,
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => &value.metrics,
        }
    }

    pub fn process_batch(&mut self, matrix: &mut [u32], source_columns: &[u64]) -> Result<()> {
        match self {
            Self::Cpu(value) => value.process_batch(matrix, source_columns),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.process_batch(matrix, source_columns),
        }
    }

    pub fn reduce_only(&mut self, vector: &mut [u32]) -> Result<()> {
        match self {
            Self::Cpu(value) => value.reduce_only(vector),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.reduce_only(vector),
        }
    }

    pub fn left_separator(&self, free_row: usize) -> Result<Vec<u32>> {
        match self {
            Self::Cpu(value) => value.left_separator(free_row),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.left_separator(free_row),
        }
    }

    pub fn dot_mod(&self, left: &[u32], right: &[u32]) -> Result<u32> {
        match self {
            Self::Cpu(value) => value.dot_mod(left, right),
            #[cfg(feature = "cuda")]
            Self::Cuda(value) => value.dot_mod(left, right),
        }
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
        let mut engine = DenseEchelon::with_panel_size(rows, prime, 5, 3).unwrap();
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

    #[cfg(feature = "cuda")]
    #[test]
    fn cuda_backend_matches_cpu_pivots_and_reduction() {
        set_blas_threads(1).unwrap();
        let rows = 17;
        let prime = 101;
        let columns = (0..31)
            .map(|column| {
                (0..rows)
                    .map(|row| {
                        ((column * 19 + row * 23 + column * row * 7 + 3) % prime as usize) as u32
                    })
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();
        let mut cpu = DenseEchelon::with_panel_size(rows, prime, 5, 3).unwrap();
        let mut cuda = CudaDenseEchelon::with_panel_size(rows, prime, 5, 3, 7).unwrap();
        for start in (0..columns.len()).step_by(7) {
            let stop = (start + 7).min(columns.len());
            let mut cpu_matrix = columns[start..stop].concat();
            let mut cuda_matrix = cpu_matrix.clone();
            let source = (start as u64..stop as u64).collect::<Vec<_>>();
            cpu.process_batch(&mut cpu_matrix, &source).unwrap();
            cuda.process_batch(&mut cuda_matrix, &source).unwrap();
            assert_eq!(cuda_matrix, cpu_matrix);
            assert_eq!(cuda.pivot_rows(), cpu.pivot_rows());
            assert_eq!(cuda.pivot_columns(), cpu.pivot_columns());
        }
        let mut cpu_target = (0..rows)
            .map(|row| ((row * row + 11 * row + 7) % prime as usize) as u32)
            .collect::<Vec<_>>();
        let mut cuda_target = cpu_target.clone();
        cpu.reduce_only(&mut cpu_target).unwrap();
        cuda.reduce_only(&mut cuda_target).unwrap();
        assert_eq!(cuda_target, cpu_target);
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

    #[test]
    fn left_separator_annihilates_basis_and_separates() {
        set_blas_threads(1).unwrap();
        let mut engine = DenseEchelon::new(5, 101, 2).unwrap();
        let mut batch = vec![1, 2, 0, 3, 0, 0, 1, 4, 0, 2];
        engine.process_batch(&mut batch, &[7, 11]).unwrap();
        let mut target = vec![0, 0, 0, 1, 0];
        let original = target.clone();
        engine.reduce_only(&mut target).unwrap();
        let free = target.iter().position(|&value| value != 0).unwrap();
        let separator = engine.left_separator(free).unwrap();
        assert_ne!(engine.dot_mod(&separator, &original).unwrap(), 0);
    }
}
