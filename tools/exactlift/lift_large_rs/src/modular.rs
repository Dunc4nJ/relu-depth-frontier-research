use std::time::{Duration, Instant};

const CBLAS_ROW_MAJOR: i32 = 101;
const CBLAS_NO_TRANS: i32 = 111;

#[link(name = "openblas")]
unsafe extern "C" {
    fn cblas_dgemm(
        layout: i32,
        transa: i32,
        transb: i32,
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

#[derive(Debug, Clone, Default)]
pub struct FactorTimings {
    pub diagonal_inverse: Duration,
    pub lower_solve: Duration,
    pub schur_update: Duration,
    pub total: Duration,
}

#[derive(Debug)]
pub struct BlockFactor {
    pub n: usize,
    pub block: usize,
    pub prime: u32,
    /// Row-major block L/U factors. A diagonal block stores its inverse.
    pub data: Vec<u32>,
    pub timings: FactorTimings,
}

fn mod_inv(value: u32, prime: u32) -> Option<u32> {
    if value == 0 {
        return None;
    }
    let (mut old_r, mut r) = (value as i64, prime as i64);
    let (mut old_s, mut s) = (1_i64, 0_i64);
    while r != 0 {
        let q = old_r / r;
        (old_r, r) = (r, old_r - q * r);
        (old_s, s) = (s, old_s - q * s);
    }
    if old_r != 1 {
        return None;
    }
    Some(old_s.rem_euclid(prime as i64) as u32)
}

fn invert_square(input: &[u32], n: usize, prime: u32) -> Result<Vec<u32>, String> {
    let width = 2 * n;
    let mut augmented = vec![0_u32; n * width];
    for row in 0..n {
        augmented[row * width..row * width + n]
            .copy_from_slice(&input[row * n..(row + 1) * n]);
        augmented[row * width + n + row] = 1;
    }
    for pivot_col in 0..n {
        let pivot_row = (pivot_col..n)
            .find(|&row| augmented[row * width + pivot_col] != 0)
            .ok_or_else(|| format!("singular diagonal block at local column {pivot_col}"))?;
        if pivot_row != pivot_col {
            for col in 0..width {
                augmented.swap(pivot_row * width + col, pivot_col * width + col);
            }
        }
        let inverse = mod_inv(augmented[pivot_col * width + pivot_col], prime)
            .ok_or_else(|| "noninvertible pivot".to_string())?;
        for col in 0..width {
            augmented[pivot_col * width + col] =
                ((augmented[pivot_col * width + col] as u64 * inverse as u64)
                    % prime as u64) as u32;
        }
        let pivot_snapshot = augmented[pivot_col * width..(pivot_col + 1) * width].to_vec();
        for row in 0..n {
            if row == pivot_col {
                continue;
            }
            let multiplier = augmented[row * width + pivot_col];
            if multiplier == 0 {
                continue;
            }
            for col in 0..width {
                let subtract = multiplier as u64 * pivot_snapshot[col] as u64 % prime as u64;
                augmented[row * width + col] =
                    (augmented[row * width + col] as u64 + prime as u64 - subtract) as u32
                        % prime;
            }
        }
    }
    let mut inverse = vec![0_u32; n * n];
    for row in 0..n {
        inverse[row * n..(row + 1) * n]
            .copy_from_slice(&augmented[row * width + n..(row + 1) * width]);
    }
    Ok(inverse)
}

fn dgemm(
    m: usize,
    n: usize,
    k: usize,
    alpha: f64,
    a: &[f64],
    b: &[f64],
    beta: f64,
    c: &mut [f64],
) {
    assert!(m <= i32::MAX as usize && n <= i32::MAX as usize && k <= i32::MAX as usize);
    unsafe {
        cblas_dgemm(
            CBLAS_ROW_MAJOR,
            CBLAS_NO_TRANS,
            CBLAS_NO_TRANS,
            m as i32,
            n as i32,
            k as i32,
            alpha,
            a.as_ptr(),
            k as i32,
            b.as_ptr(),
            n as i32,
            beta,
            c.as_mut_ptr(),
            n as i32,
        );
    }
}

#[inline]
fn reduce_f64(value: f64, prime: u32) -> u32 {
    debug_assert!(value.abs() < (1_u64 << 53) as f64);
    (value.round() as i64).rem_euclid(prime as i64) as u32
}

impl BlockFactor {
    pub fn factor(
        mut data: Vec<u32>,
        n: usize,
        block: usize,
        prime: u32,
        threads: usize,
        row_tile: usize,
    ) -> Result<Self, String> {
        if data.len() != n * n {
            return Err(format!("dense matrix has {} entries, expected {}", data.len(), n * n));
        }
        if block == 0 || row_tile == 0 {
            return Err("block and row tile must be positive".to_string());
        }
        if block as u128 * prime as u128 * prime as u128 >= (1_u128 << 52) {
            return Err("block x prime^2 exceeds exact f64 GEMM budget".to_string());
        }
        unsafe { openblas_set_num_threads(threads as i32) };
        let started = Instant::now();
        let mut timings = FactorTimings::default();

        for start in (0..n).step_by(block) {
            let width = block.min(n - start);
            let trailing = n - start - width;
            let phase = Instant::now();
            let mut diagonal = vec![0_u32; width * width];
            for row in 0..width {
                diagonal[row * width..(row + 1) * width].copy_from_slice(
                    &data[(start + row) * n + start..(start + row) * n + start + width],
                );
            }
            let inverse = invert_square(&diagonal, width, prime)
                .map_err(|error| format!("block starting {start}: {error}"))?;
            for row in 0..width {
                data[(start + row) * n + start..(start + row) * n + start + width]
                    .copy_from_slice(&inverse[row * width..(row + 1) * width]);
            }
            timings.diagonal_inverse += phase.elapsed();

            if trailing == 0 {
                continue;
            }

            let inverse_f64: Vec<f64> = inverse.iter().map(|&value| value as f64).collect();
            let phase = Instant::now();
            for row_start in (start + width..n).step_by(row_tile) {
                let rows = row_tile.min(n - row_start);
                let mut left = vec![0_f64; rows * width];
                for row in 0..rows {
                    for col in 0..width {
                        left[row * width + col] =
                            data[(row_start + row) * n + start + col] as f64;
                    }
                }
                let mut product = vec![0_f64; rows * width];
                dgemm(rows, width, width, 1.0, &left, &inverse_f64, 0.0, &mut product);
                for row in 0..rows {
                    for col in 0..width {
                        data[(row_start + row) * n + start + col] =
                            reduce_f64(product[row * width + col], prime);
                    }
                }
            }
            timings.lower_solve += phase.elapsed();

            let phase = Instant::now();
            let mut upper = vec![0_f64; width * trailing];
            for row in 0..width {
                for col in 0..trailing {
                    upper[row * trailing + col] =
                        data[(start + row) * n + start + width + col] as f64;
                }
            }
            for row_start in (start + width..n).step_by(row_tile) {
                let rows = row_tile.min(n - row_start);
                let mut lower = vec![0_f64; rows * width];
                let mut updated = vec![0_f64; rows * trailing];
                for row in 0..rows {
                    for col in 0..width {
                        lower[row * width + col] =
                            data[(row_start + row) * n + start + col] as f64;
                    }
                    for col in 0..trailing {
                        updated[row * trailing + col] =
                            data[(row_start + row) * n + start + width + col] as f64;
                    }
                }
                dgemm(rows, trailing, width, -1.0, &lower, &upper, 1.0, &mut updated);
                for row in 0..rows {
                    for col in 0..trailing {
                        data[(row_start + row) * n + start + width + col] =
                            reduce_f64(updated[row * trailing + col], prime);
                    }
                }
            }
            timings.schur_update += phase.elapsed();
        }
        timings.total = started.elapsed();
        Ok(Self { n, block, prime, data, timings })
    }

    pub fn solve(&self, rhs: &[u32]) -> Result<Vec<u32>, String> {
        if rhs.len() != self.n {
            return Err("right-hand side length mismatch".to_string());
        }
        let p = self.prime as u64;
        let mut y = vec![0_u32; self.n];
        for start in (0..self.n).step_by(self.block) {
            let width = self.block.min(self.n - start);
            for local in 0..width {
                let row = start + local;
                let mut sum = 0_u64;
                for col in 0..start {
                    sum += self.data[row * self.n + col] as u64 * y[col] as u64;
                }
                y[row] = (rhs[row] as u64 + p - sum % p) as u32 % self.prime;
            }
        }

        let mut solution = vec![0_u32; self.n];
        let starts: Vec<usize> = (0..self.n).step_by(self.block).collect();
        for &start in starts.iter().rev() {
            let width = self.block.min(self.n - start);
            let mut block_rhs = vec![0_u32; width];
            for local in 0..width {
                let row = start + local;
                let mut sum = 0_u64;
                for col in start + width..self.n {
                    sum += self.data[row * self.n + col] as u64 * solution[col] as u64;
                }
                block_rhs[local] =
                    (y[row] as u64 + p - sum % p) as u32 % self.prime;
            }
            for row in 0..width {
                let mut sum = 0_u64;
                for col in 0..width {
                    sum += self.data[(start + row) * self.n + start + col] as u64
                        * block_rhs[col] as u64;
                }
                solution[start + row] = (sum % p) as u32;
            }
        }
        Ok(solution)
    }

    pub fn solve_transpose(&self, rhs: &[u32]) -> Result<Vec<u32>, String> {
        if rhs.len() != self.n {
            return Err("right-hand side length mismatch".to_string());
        }
        let p = self.prime as u64;
        let starts: Vec<usize> = (0..self.n).step_by(self.block).collect();
        let mut z = vec![0_u32; self.n];
        for &start in &starts {
            let width = self.block.min(self.n - start);
            let mut block_rhs = vec![0_u32; width];
            for local in 0..width {
                let col = start + local;
                let mut sum = 0_u64;
                for row in 0..start {
                    sum += self.data[row * self.n + col] as u64 * z[row] as u64;
                }
                block_rhs[local] =
                    (rhs[col] as u64 + p - sum % p) as u32 % self.prime;
            }
            for col in 0..width {
                let mut sum = 0_u64;
                for row in 0..width {
                    // Diagonal stores B^-1, so use B^-T here.
                    sum += self.data[(start + row) * self.n + start + col] as u64
                        * block_rhs[row] as u64;
                }
                z[start + col] = (sum % p) as u32;
            }
        }

        let mut solution = vec![0_u32; self.n];
        for &start in starts.iter().rev() {
            let width = self.block.min(self.n - start);
            for local in 0..width {
                let col = start + local;
                let mut sum = 0_u64;
                for row in start + width..self.n {
                    sum += self.data[row * self.n + col] as u64 * solution[row] as u64;
                }
                solution[col] = (z[col] as u64 + p - sum % p) as u32 % self.prime;
            }
        }
        Ok(solution)
    }
}

pub fn matvec_mod(matrix: &[u32], n: usize, vector: &[u32], prime: u32) -> Vec<u32> {
    let p = prime as u64;
    (0..n)
        .map(|row| {
            let sum: u64 = (0..n)
                .map(|col| matrix[row * n + col] as u64 * vector[col] as u64)
                .sum();
            (sum % p) as u32
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_matrix() -> (Vec<u32>, usize, u32) {
        let p = 65_521;
        let n = 7;
        let mut matrix = vec![0_u32; n * n];
        for row in 0..n {
            for col in 0..n {
                matrix[row * n + col] = ((17 * row + 29 * col + 3 * row * col + 7) % 101) as u32;
            }
            matrix[row * n + row] += 1_000;
        }
        (matrix, n, p)
    }

    #[test]
    fn block_factor_solves_both_orientations() {
        let (matrix, n, p) = sample_matrix();
        let factor = BlockFactor::factor(matrix.clone(), n, 3, p, 1, 4).unwrap();
        let expected: Vec<u32> = (0..n).map(|index| (index * index + 2) as u32).collect();
        let rhs = matvec_mod(&matrix, n, &expected, p);
        assert_eq!(factor.solve(&rhs).unwrap(), expected);

        let mut transposed = vec![0_u32; n * n];
        for row in 0..n {
            for col in 0..n {
                transposed[row * n + col] = matrix[col * n + row];
            }
        }
        let rhs_transposed = matvec_mod(&transposed, n, &expected, p);
        assert_eq!(factor.solve_transpose(&rhs_transposed).unwrap(), expected);
    }
}
