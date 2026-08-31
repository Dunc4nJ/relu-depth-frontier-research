//! Deterministic incremental rank through a left-annihilator basis.

#[derive(Clone, Debug)]
pub struct LeftAnnihilator {
    dimension: usize,
    prime: u32,
    rows: Vec<Vec<u32>>,
    selected_sequences: Vec<usize>,
}

impl LeftAnnihilator {
    pub fn new(dimension: usize, prime: u32) -> Self {
        assert!(dimension > 0, "dimension must be positive");
        assert!(
            matches!(prime, 2_000_081 | 3_000_017),
            "only the two frozen G-0113 primes are admitted"
        );
        let largest_product_sum = dimension as u128 * u128::from(prime - 1) * u128::from(prime - 1);
        assert!(
            largest_product_sum <= u128::from(u64::MAX),
            "dot-product accumulator would overflow"
        );
        let rows = (0..dimension)
            .map(|index| {
                let mut row = vec![0; dimension];
                row[index] = 1;
                row
            })
            .collect();
        Self {
            dimension,
            prime,
            rows,
            selected_sequences: Vec::with_capacity(dimension),
        }
    }

    pub fn dimension(&self) -> usize {
        self.dimension
    }

    pub fn prime(&self) -> u32 {
        self.prime
    }

    pub fn rank(&self) -> usize {
        self.dimension - self.rows.len()
    }

    pub fn nullity(&self) -> usize {
        self.rows.len()
    }

    pub fn selected_sequences(&self) -> &[usize] {
        &self.selected_sequences
    }

    pub fn ingest_exact(&mut self, sequence: usize, column: &[i128]) -> bool {
        assert_eq!(column.len(), self.dimension, "column dimension drift");
        let prime = i128::from(self.prime);
        let reduced = column
            .iter()
            .map(|value| value.rem_euclid(prime) as u32)
            .collect::<Vec<_>>();
        self.ingest_mod(sequence, &reduced)
    }

    pub fn ingest_mod(&mut self, sequence: usize, column: &[u32]) -> bool {
        assert_eq!(column.len(), self.dimension, "column dimension drift");
        assert!(
            column.iter().all(|value| *value < self.prime),
            "noncanonical field element"
        );
        if self.rows.is_empty() {
            return false;
        }
        let scores = self
            .rows
            .iter()
            .map(|row| dot_mod(row, column, self.prime))
            .collect::<Vec<_>>();
        let Some(pivot) = scores.iter().position(|value| *value != 0) else {
            return false;
        };
        let inverse = inverse_mod(scores[pivot], self.prime);
        let pivot_row = self.rows[pivot].clone();
        for (index, row) in self.rows.iter_mut().enumerate() {
            if index == pivot || scores[index] == 0 {
                continue;
            }
            let factor = multiply_mod(scores[index], inverse, self.prime);
            subtract_multiple_mod(row, &pivot_row, factor, self.prime);
        }
        self.rows.remove(pivot);
        self.selected_sequences.push(sequence);
        true
    }

    pub fn contains_exact(&self, column: &[i128]) -> bool {
        assert_eq!(column.len(), self.dimension, "column dimension drift");
        let prime = i128::from(self.prime);
        let reduced = column
            .iter()
            .map(|value| value.rem_euclid(prime) as u32)
            .collect::<Vec<_>>();
        self.contains_mod(&reduced)
    }

    pub fn contains_mod(&self, column: &[u32]) -> bool {
        assert_eq!(column.len(), self.dimension, "column dimension drift");
        assert!(
            column.iter().all(|value| *value < self.prime),
            "noncanonical field element"
        );
        self.rows
            .iter()
            .all(|row| dot_mod(row, column, self.prime) == 0)
    }

    pub fn annihilator_rows(&self) -> &[Vec<u32>] {
        &self.rows
    }
}

fn dot_mod(left: &[u32], right: &[u32], prime: u32) -> u32 {
    debug_assert_eq!(left.len(), right.len());
    let modulus = u64::from(prime);
    let sum = left
        .iter()
        .zip(right)
        .map(|(one, two)| u64::from(*one) * u64::from(*two))
        .sum::<u64>();
    (sum % modulus) as u32
}

fn multiply_mod(left: u32, right: u32, prime: u32) -> u32 {
    ((u64::from(left) * u64::from(right)) % u64::from(prime)) as u32
}

fn subtract_multiple_mod(row: &mut [u32], pivot: &[u32], factor: u32, prime: u32) {
    let modulus = u64::from(prime);
    for (value, pivot_value) in row.iter_mut().zip(pivot) {
        let subtraction = (u64::from(factor) * u64::from(*pivot_value)) % modulus;
        *value = ((u64::from(*value) + modulus - subtraction) % modulus) as u32;
    }
}

fn inverse_mod(value: u32, prime: u32) -> u32 {
    assert_ne!(value, 0, "zero has no field inverse");
    let mut base = value;
    let mut exponent = prime - 2;
    let mut result = 1u32;
    while exponent > 0 {
        if exponent & 1 == 1 {
            result = multiply_mod(result, base, prime);
        }
        base = multiply_mod(base, base, prime);
        exponent >>= 1;
    }
    debug_assert_eq!(multiply_mod(value, result, prime), 1);
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    const PRIMES: [u32; 2] = [2_000_081, 3_000_017];

    fn direct_rank(columns: &[Vec<i128>], prime: u32) -> usize {
        if columns.is_empty() {
            return 0;
        }
        let row_count = columns[0].len();
        let column_count = columns.len();
        let modulus = i128::from(prime);
        let mut matrix = (0..row_count)
            .map(|row| {
                columns
                    .iter()
                    .map(|column| column[row].rem_euclid(modulus) as u32)
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();
        let mut rank = 0;
        for column in 0..column_count {
            let Some(pivot) = (rank..row_count).find(|row| matrix[*row][column] != 0) else {
                continue;
            };
            matrix.swap(rank, pivot);
            let inverse = inverse_mod(matrix[rank][column], prime);
            for entry in &mut matrix[rank][column..] {
                *entry = multiply_mod(*entry, inverse, prime);
            }
            let pivot_row = matrix[rank].clone();
            for (row_index, row) in matrix.iter_mut().enumerate() {
                if row_index == rank || row[column] == 0 {
                    continue;
                }
                let factor = row[column];
                subtract_multiple_mod(&mut row[column..], &pivot_row[column..], factor, prime);
            }
            rank += 1;
            if rank == row_count {
                break;
            }
        }
        rank
    }

    fn assert_prefix_agreement(columns: &[Vec<i128>], dimension: usize, prime: u32) {
        let mut oracle = LeftAnnihilator::new(dimension, prime);
        let mut prefix = Vec::new();
        for (sequence, column) in columns.iter().enumerate() {
            let old_rank = direct_rank(&prefix, prime);
            prefix.push(column.clone());
            let expected = direct_rank(&prefix, prime) > old_rank;
            assert_eq!(oracle.ingest_exact(sequence, column), expected);
            assert_eq!(oracle.rank(), direct_rank(&prefix, prime));
            for prior in &prefix {
                assert!(oracle.contains_exact(prior));
            }
        }
        assert_eq!(oracle.selected_sequences().len(), oracle.rank());
    }

    #[test]
    fn duplicate_zero_full_rank_controls_match_direct_elimination() {
        let columns = vec![
            vec![0, 0, 0, 0, 0],
            vec![1, 2, 3, 4, 5],
            vec![1, 2, 3, 4, 5],
            vec![-2, 1, 0, 3, 7],
            vec![5, -1, 4, 2, 0],
            vec![0, 3, -2, 8, 1],
            vec![4, 0, 1, -1, 6],
        ];
        for prime in PRIMES {
            assert_prefix_agreement(&columns, 5, prime);
            assert_eq!(direct_rank(&columns, prime), 5);
        }
    }

    #[test]
    fn rank_deficient_member_and_nonmember_controls() {
        let spanning = vec![
            vec![1, 0, 1, 0, 2],
            vec![0, 1, 0, 1, 3],
            vec![1, 1, 1, 1, 5],
            vec![2, -1, 2, -1, 1],
        ];
        let member = vec![3, 2, 3, 2, 12];
        let nonmember = vec![0, 0, 0, 0, 1];
        for prime in PRIMES {
            assert_prefix_agreement(&spanning, 5, prime);
            let mut oracle = LeftAnnihilator::new(5, prime);
            for (sequence, column) in spanning.iter().enumerate() {
                oracle.ingest_exact(sequence, column);
            }
            assert_eq!(oracle.rank(), direct_rank(&spanning, prime));
            assert!(oracle.contains_exact(&member));
            assert!(!oracle.contains_exact(&nonmember));
        }
    }
}
