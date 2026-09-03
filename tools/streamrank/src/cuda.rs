use super::{GemmKind, Modulus, ReducerMetrics, mod_inverse, scale_mod, subtract_multiple};
use anyhow::{Context as _, Result, ensure};
use rayon::prelude::*;
use std::ffi::{CStr, c_char, c_void};
use std::ptr::NonNull;
use std::time::Instant;

#[repr(C)]
#[derive(Clone, Copy, Debug, Default)]
struct CudaObservation {
    gemm_calls: u64,
    scalar_products: u64,
    pack_seconds: f64,
    gemm_seconds: f64,
    modular_reduce_seconds: f64,
    transfer_seconds: f64,
    host_to_device_bytes: u64,
    device_to_host_bytes: u64,
    peak_allocated_bytes: u64,
}

unsafe extern "C" {
    fn max11_cuda_last_error() -> *const c_char;
    fn max11_cuda_create(
        rows: usize,
        prime: u32,
        block_size: usize,
        panel_size: usize,
        max_batch: usize,
        result: *mut *mut c_void,
    ) -> i32;
    fn max11_cuda_destroy(context: *mut c_void) -> i32;
    fn max11_cuda_reduce_existing(
        context: *mut c_void,
        matrix: *mut u32,
        columns: usize,
        pivots: *const usize,
        rank: usize,
        observation: *mut CudaObservation,
    ) -> i32;
    fn max11_cuda_apply_panel(
        context: *mut c_void,
        matrix: *mut u32,
        total_columns: usize,
        future_start: usize,
        panel: *const u32,
        panel_pivots: *const usize,
        panel_columns: usize,
        rank_before: usize,
        host_basis_tail: *mut u32,
        prior_observation: *mut CudaObservation,
        future_observation: *mut CudaObservation,
    ) -> i32;
}

fn cuda_result(status: i32) -> Result<()> {
    if status == 0 {
        return Ok(());
    }
    let pointer = unsafe { max11_cuda_last_error() };
    ensure!(
        !pointer.is_null(),
        "CUDA backend failed without an error message"
    );
    let message = unsafe { CStr::from_ptr(pointer) }
        .to_str()
        .context("CUDA backend returned non-UTF-8 error text")?;
    anyhow::bail!("CUDA backend: {message}")
}

#[derive(Debug)]
pub struct CudaDenseEchelon {
    rows: usize,
    prime: u32,
    modulus: Modulus,
    block_size: usize,
    panel_size: usize,
    max_batch: usize,
    basis: Vec<u32>,
    pivot_rows: Vec<usize>,
    pivot_columns: Vec<u64>,
    occupied: Vec<bool>,
    context: NonNull<c_void>,
    pub metrics: ReducerMetrics,
}

impl CudaDenseEchelon {
    pub fn with_panel_size(
        rows: usize,
        prime: u32,
        block_size: usize,
        panel_size: usize,
        max_batch: usize,
    ) -> Result<Self> {
        ensure!(rows > 0, "rank engine needs at least one row");
        ensure!(super::is_prime(prime), "modulus {prime} is not prime");
        ensure!(prime < (1 << 20), "prime must be below 2^20");
        ensure!(
            block_size > 0 && block_size <= 8192,
            "CUDA GEMM block must lie in 1..=8192"
        );
        ensure!(panel_size > 0, "rank panel must be positive");
        ensure!(max_batch > 0, "CUDA maximum batch must be positive");
        let accumulation_terms = block_size.max(panel_size);
        let worst = accumulation_terms as u128 * (prime as u128 - 1).pow(2) + prime as u128;
        ensure!(
            worst < (1u128 << 53),
            "CUDA GEMM block violates exact-binary64 accumulation bound"
        );
        let mut raw = std::ptr::null_mut();
        cuda_result(unsafe {
            max11_cuda_create(rows, prime, block_size, panel_size, max_batch, &mut raw)
        })?;
        let context = NonNull::new(raw).context("CUDA backend returned a null context")?;
        Ok(Self {
            rows,
            prime,
            modulus: Modulus::new(prime),
            block_size,
            panel_size,
            max_batch,
            basis: Vec::new(),
            pivot_rows: Vec::new(),
            pivot_columns: Vec::new(),
            occupied: vec![false; rows],
            context,
            metrics: ReducerMetrics::default(),
        })
    }

    fn record(&mut self, observation: CudaObservation, kind: GemmKind) {
        if observation.gemm_calls == 0
            && observation.host_to_device_bytes == 0
            && observation.device_to_host_bytes == 0
        {
            return;
        }
        self.metrics.gemm_calls += observation.gemm_calls;
        self.metrics.gemm_scalar_products_numerator += observation.scalar_products as u128;
        self.metrics.gemm_seconds += observation.gemm_seconds;
        self.metrics.pack_seconds += observation.pack_seconds;
        self.metrics.modular_reduce_seconds += observation.modular_reduce_seconds;
        self.metrics.gpu_peak_allocated_bytes = self
            .metrics
            .gpu_peak_allocated_bytes
            .max(observation.peak_allocated_bytes);
        self.metrics.gpu_host_to_device_bytes_numerator += observation.host_to_device_bytes as u128;
        self.metrics.gpu_device_to_host_bytes_numerator += observation.device_to_host_bytes as u128;
        self.metrics.gpu_transfer_seconds += observation.transfer_seconds;
        match kind {
            GemmKind::OldBasis => {
                self.metrics.old_basis_gemm_calls += observation.gemm_calls;
                self.metrics.old_basis_gemm_scalar_products_numerator +=
                    observation.scalar_products as u128;
                self.metrics.old_basis_gemm_seconds += observation.gemm_seconds;
            }
            GemmKind::PanelFuture => {
                self.metrics.panel_future_gemm_calls += observation.gemm_calls;
                self.metrics.panel_future_gemm_scalar_products_numerator +=
                    observation.scalar_products as u128;
                self.metrics.panel_future_gemm_seconds += observation.gemm_seconds;
            }
            GemmKind::PanelBasis => {
                self.metrics.panel_basis_gemm_calls += observation.gemm_calls;
                self.metrics.panel_basis_gemm_scalar_products_numerator +=
                    observation.scalar_products as u128;
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
                if coefficient != 0 {
                    let product = self.modulus.reduce_u64(
                        coefficient as u64 * basis_column[self.pivot_rows[later]] as u64,
                    );
                    let total = sum + product;
                    sum = if total >= self.prime {
                        total - self.prime
                    } else {
                        total
                    };
                }
            }
            separator[self.pivot_rows[column]] = if sum == 0 { 0 } else { self.prime - sum };
        }
        for column in self.basis.chunks_exact(self.rows) {
            ensure!(
                self.dot_mod(&separator, column)? == 0,
                "constructed separator does not annihilate the CUDA basis mirror"
            );
        }
        Ok(separator)
    }

    fn reduce_existing(&mut self, matrix: &mut [u32], columns: usize) -> Result<()> {
        ensure!(
            columns <= self.max_batch,
            "batch exceeds CUDA workspace capacity"
        );
        ensure!(matrix.len() == self.rows * columns, "batch shape mismatch");
        let mut observation = CudaObservation::default();
        cuda_result(unsafe {
            max11_cuda_reduce_existing(
                self.context.as_ptr(),
                matrix.as_mut_ptr(),
                columns,
                self.pivot_rows.as_ptr(),
                self.rank(),
                &mut observation,
            )
        })?;
        self.record(observation, GemmKind::OldBasis);
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
            let basis_update_at = Instant::now();
            for column in panel_start..panel_stop {
                let range = column * self.rows..(column + 1) * self.rows;
                for &pivot in &self.pivot_rows {
                    ensure!(
                        matrix[range.start + pivot] == 0,
                        "nonzero at an existing pivot after CUDA reduction"
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
            self.metrics.basis_update_seconds += basis_update_at.elapsed().as_secs_f64();

            let rank_after_panel = self.rank();
            if rank_after_panel > rank_before_panel {
                let panel_columns = rank_after_panel - rank_before_panel;
                let panel_basis = self.basis
                    [rank_before_panel * self.rows..rank_after_panel * self.rows]
                    .to_vec();
                let panel_pivots = self.pivot_rows[rank_before_panel..rank_after_panel].to_vec();
                let block_start = rank_before_panel - rank_before_panel % self.block_size;
                let tail_pointer = if block_start == rank_before_panel {
                    std::ptr::null_mut()
                } else {
                    self.basis[block_start * self.rows..rank_before_panel * self.rows].as_mut_ptr()
                };
                let mut prior = CudaObservation::default();
                let mut future = CudaObservation::default();
                cuda_result(unsafe {
                    max11_cuda_apply_panel(
                        self.context.as_ptr(),
                        matrix.as_mut_ptr(),
                        columns,
                        panel_stop,
                        panel_basis.as_ptr(),
                        panel_pivots.as_ptr(),
                        panel_columns,
                        rank_before_panel,
                        tail_pointer,
                        &mut prior,
                        &mut future,
                    )
                })?;
                self.record(prior, GemmKind::PanelBasis);
                self.record(future, GemmKind::PanelFuture);
            }
        }
        Ok(())
    }
}

impl Drop for CudaDenseEchelon {
    fn drop(&mut self) {
        let _ = unsafe { max11_cuda_destroy(self.context.as_ptr()) };
    }
}
