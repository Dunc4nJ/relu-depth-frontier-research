use anyhow::{Result, ensure};
use rustc_hash::FxHashMap as HashMap;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;

pub const MAX_N: usize = 16;

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
pub struct SignedRecord {
    #[serde(default)]
    pub sequence: Option<usize>,
    pub active_vertices: usize,
    pub signed_mass: usize,
    pub negative_edges: Vec<[usize; 2]>,
    pub positive_edges: Vec<[usize; 2]>,
    #[serde(default)]
    pub abs_components: Option<usize>,
    #[serde(default)]
    pub abs_beta: Option<isize>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct Universe {
    pub schema: String,
    pub n: usize,
    pub branch_edge_occurrences: usize,
    pub loopless: bool,
    pub records: Vec<SignedRecord>,
}

#[derive(Clone, Debug, Deserialize)]
#[allow(non_snake_case)]
pub struct SavedTemplate {
    #[serde(rename = "A")]
    pub a: Vec<[usize; 2]>,
    #[serde(rename = "B")]
    pub b: Vec<[usize; 2]>,
    #[serde(rename = "lin")]
    pub linear: Vec<i64>,
    #[serde(rename = "h")]
    pub hinges: BTreeMap<String, i64>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SparseColumn {
    pub linear: Vec<i64>,
    pub hinges: HashMap<Vec<i16>, i64>,
}

/// Fully symmetrized carrier for `branch_edges` common loops.
///
/// Each coordinate occurs in `(n-1)!` permutations, so this is the all-ones
/// linear direction scaled by `branch_edges * (n-1)!` and has no hinge part.
pub fn common_loop_carrier_column(n: usize, branch_edges: usize) -> Result<SparseColumn> {
    validate_dimensions(n, branch_edges)?;
    ensure!(
        branch_edges > 0,
        "common-loop carrier requires a positive branch size"
    );
    let factorial = checked_factorial(n - 1)?;
    let coefficient = u64::try_from(branch_edges)?
        .checked_mul(factorial)
        .ok_or_else(|| anyhow::anyhow!("common-loop carrier coefficient overflow"))?;
    let coefficient = i64::try_from(coefficient)?;
    Ok(SparseColumn {
        linear: vec![coefficient; n],
        hinges: HashMap::default(),
    })
}

#[derive(Clone, Debug, Serialize)]
pub struct HingeEntry {
    pub direction: Vec<i16>,
    pub coefficient: i64,
}

#[derive(Clone, Debug, Serialize)]
pub struct ColumnOutput {
    pub record_index: usize,
    pub modulus: Option<u64>,
    pub linear: Vec<i64>,
    pub hinges: Vec<HingeEntry>,
}

impl SparseColumn {
    pub fn output(&self, record_index: usize, modulus: Option<u64>) -> Result<ColumnOutput> {
        let reduce = |value: i64| -> Result<i64> {
            match modulus {
                None => Ok(value),
                Some(p) => {
                    ensure!(p >= 2 && p <= i64::MAX as u64, "unsupported modulus {p}");
                    Ok((value as i128).rem_euclid(p as i128) as i64)
                }
            }
        };
        let mut hinges: Vec<HingeEntry> = self
            .hinges
            .iter()
            .map(|(direction, &coefficient)| {
                Ok(HingeEntry {
                    direction: direction.clone(),
                    coefficient: reduce(coefficient)?,
                })
            })
            .collect::<Result<_>>()?;
        hinges.sort_by(|left, right| left.direction.cmp(&right.direction));
        Ok(ColumnOutput {
            record_index,
            modulus,
            linear: self
                .linear
                .iter()
                .map(|&value| reduce(value))
                .collect::<Result<_>>()?,
            hinges,
        })
    }
}

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq)]
struct State {
    mask: u16,
    word: [i16; MAX_N],
}

fn checked_factorial(n: usize) -> Result<u64> {
    (1..=n as u64).try_fold(1u64, |acc, value| {
        acc.checked_mul(value)
            .ok_or_else(|| anyhow::anyhow!("factorial({n}) exceeds u64"))
    })
}

fn gcd(mut a: i64, mut b: i64) -> i64 {
    a = a.abs();
    b = b.abs();
    while b != 0 {
        let remainder = a % b;
        a = b;
        b = remainder;
    }
    a
}

fn validate_dimensions(n: usize, branch_edges: usize) -> Result<()> {
    ensure!((2..=MAX_N).contains(&n), "n must lie in 2..={MAX_N}");
    ensure!(
        branch_edges <= i8::MAX as usize,
        "branch edge count exceeds i8 range"
    );
    let _ = checked_factorial(n)?;
    Ok(())
}

fn signed_matrix(record: &SignedRecord, n: usize, branch_edges: usize) -> Result<Vec<Vec<i16>>> {
    validate_dimensions(n, branch_edges)?;
    ensure!(record.active_vertices <= n, "active vertex count exceeds n");
    ensure!(
        record.signed_mass <= branch_edges,
        "signed mass exceeds branch size"
    );
    ensure!(
        record.negative_edges.len() == record.signed_mass
            && record.positive_edges.len() == record.signed_mass,
        "signed edge counts do not equal signed_mass"
    );
    let mut matrix = vec![vec![0i16; n]; n];
    for (sign, edges) in [
        (-1i16, &record.negative_edges),
        (1i16, &record.positive_edges),
    ] {
        for &[first, second] in edges {
            ensure!(
                first < second && second < n,
                "loopless edge [{first},{second}] is diagonal, noncanonical, or out of range"
            );
            matrix[first][second] = matrix[first][second]
                .checked_add(sign)
                .ok_or_else(|| anyhow::anyhow!("signed matrix entry overflow"))?;
            matrix[second][first] = matrix[second][first]
                .checked_add(sign)
                .ok_or_else(|| anyhow::anyhow!("signed matrix entry overflow"))?;
        }
    }
    Ok(matrix)
}

fn increments(matrix: &[Vec<i16>], n: usize) -> Result<Vec<Vec<i16>>> {
    let width = 1usize << n;
    let mut result = vec![vec![0i16; width]; n];
    for vertex in 0..n {
        for mask in 1usize..width {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            result[vertex][mask] = result[vertex][mask ^ bit]
                .checked_add(matrix[vertex][other])
                .ok_or_else(|| anyhow::anyhow!("back-degree increment overflow"))?;
        }
    }
    Ok(result)
}

fn add_checked(target: &mut i64, summand: i64, label: &str) -> Result<()> {
    *target = target
        .checked_add(summand)
        .ok_or_else(|| anyhow::anyhow!("{label} coefficient overflow"))?;
    Ok(())
}

fn accumulate_word(column: &mut SparseColumn, word: &[i16], count: u64) -> Result<()> {
    let first = word.iter().copied().find(|&value| value != 0);
    let Some(first) = first else {
        return Ok(());
    };
    ensure!(
        word.iter().map(|&value| value as i64).sum::<i64>() == 0,
        "raw word is not zero-sum"
    );
    let count_i64 = i64::try_from(count)?;
    if first < 0 {
        for (coordinate, &value) in column.linear.iter_mut().zip(word) {
            let correction = count_i64
                .checked_mul(value as i64)
                .ok_or_else(|| anyhow::anyhow!("linear correction product overflow"))?;
            add_checked(coordinate, correction, "linear")?;
        }
    }

    let divisor = word
        .iter()
        .fold(0i64, |current, &value| gcd(current, value as i64));
    ensure!(divisor > 0, "nonzero word has zero gcd");
    let orientation = if first > 0 { 1i64 } else { -1i64 };
    let direction: Vec<i16> = word
        .iter()
        .map(|&value| i16::try_from(orientation * value as i64 / divisor))
        .collect::<std::result::Result<_, _>>()?;
    ensure!(direction.iter().copied().find(|&value| value != 0).unwrap() > 0);

    let mut prefix = 0i64;
    let mut active_on_ordered_cone = false;
    for &value in &direction[..direction.len() - 1] {
        prefix += value as i64;
        active_on_ordered_cone |= prefix < 0;
    }
    if active_on_ordered_cone {
        let contribution = count_i64
            .checked_mul(divisor)
            .ok_or_else(|| anyhow::anyhow!("hinge contribution overflow"))?;
        let entry = column.hinges.entry(direction).or_default();
        add_checked(entry, contribution, "hinge")?;
    }
    Ok(())
}

fn initialized_column(n: usize, branch_edges: usize) -> Result<SparseColumn> {
    let orbit = checked_factorial(n - 2)?;
    let base_factor = 2u64
        .checked_mul(u64::try_from(branch_edges)?)
        .and_then(|value| value.checked_mul(orbit))
        .ok_or_else(|| anyhow::anyhow!("linear base factor overflow"))?;
    let base_factor = i64::try_from(base_factor)?;
    let mut linear = Vec::with_capacity(n);
    for rank in 0..n {
        linear.push(
            base_factor
                .checked_mul(i64::try_from(rank)?)
                .ok_or_else(|| anyhow::anyhow!("linear base coordinate overflow"))?,
        );
    }
    Ok(SparseColumn {
        linear,
        hinges: HashMap::default(),
    })
}

pub fn generate_column(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
) -> Result<SparseColumn> {
    let matrix = signed_matrix(record, n, branch_edges)?;
    let increments = increments(&matrix, n)?;
    let mut current: HashMap<State, u64> = HashMap::default();
    current.insert(
        State {
            mask: 0,
            word: [0; MAX_N],
        },
        1u64,
    );
    for depth in 0..n {
        let capacity = current.len().saturating_mul((n - depth).min(4));
        let mut next: HashMap<State, u64> =
            HashMap::with_capacity_and_hasher(capacity, Default::default());
        for (state, count) in current {
            let mask = state.mask as usize;
            for (vertex, vertex_increments) in increments.iter().enumerate().take(n) {
                let bit = 1usize << vertex;
                if mask & bit != 0 {
                    continue;
                }
                let mut child = state;
                child.mask = u16::try_from(mask | bit)?;
                child.word[depth] = vertex_increments[mask];
                match next.entry(child) {
                    std::collections::hash_map::Entry::Occupied(mut entry) => {
                        let value = entry
                            .get()
                            .checked_add(count)
                            .ok_or_else(|| anyhow::anyhow!("permutation multiplicity overflow"))?;
                        *entry.get_mut() = value;
                    }
                    std::collections::hash_map::Entry::Vacant(entry) => {
                        entry.insert(count);
                    }
                }
            }
        }
        current = next;
    }

    let expected = checked_factorial(n)?;
    let observed = current.values().try_fold(0u64, |acc, &value| {
        acc.checked_add(value)
            .ok_or_else(|| anyhow::anyhow!("permutation census overflow"))
    })?;
    ensure!(
        observed == expected,
        "permutation census mismatch: {observed}/{expected}"
    );
    let mut column = initialized_column(n, branch_edges)?;
    for (state, count) in current {
        accumulate_word(&mut column, &state.word[..n], count)?;
    }
    Ok(column)
}

pub fn brute_force_column(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
) -> Result<SparseColumn> {
    ensure!(n <= 10, "literal permutation control is capped at n=10");
    let matrix = signed_matrix(record, n, branch_edges)?;
    let mut column = initialized_column(n, branch_edges)?;
    let mut order = Vec::with_capacity(n);
    let mut used = vec![false; n];

    fn visit(
        matrix: &[Vec<i16>],
        n: usize,
        order: &mut Vec<usize>,
        used: &mut [bool],
        column: &mut SparseColumn,
    ) -> Result<()> {
        if order.len() == n {
            let mut word = vec![0i16; n];
            for rank in 0..n {
                let vertex = order[rank];
                for &earlier in &order[..rank] {
                    word[rank] = word[rank]
                        .checked_add(matrix[vertex][earlier])
                        .ok_or_else(|| anyhow::anyhow!("literal raw word overflow"))?;
                }
            }
            return accumulate_word(column, &word, 1);
        }
        for vertex in 0..n {
            if used[vertex] {
                continue;
            }
            used[vertex] = true;
            order.push(vertex);
            visit(matrix, n, order, used, column)?;
            order.pop();
            used[vertex] = false;
        }
        Ok(())
    }

    visit(&matrix, n, &mut order, &mut used, &mut column)?;
    Ok(column)
}

pub fn record_from_branches(a: &[[usize; 2]], b: &[[usize; 2]], n: usize) -> Result<SignedRecord> {
    ensure!(a.len() == b.len(), "branch occurrence counts differ");
    let mut balance: BTreeMap<[usize; 2], isize> = BTreeMap::new();
    for (sign, edges) in [(-1isize, a), (1isize, b)] {
        for &[first, second] in edges {
            ensure!(
                first < second && second < n,
                "branch contains invalid loopless edge"
            );
            *balance.entry([first, second]).or_default() += sign;
        }
    }
    let mut negative_edges = Vec::new();
    let mut positive_edges = Vec::new();
    for (edge, value) in balance {
        if value < 0 {
            negative_edges.extend(std::iter::repeat_n(edge, value.unsigned_abs()));
        } else {
            positive_edges.extend(std::iter::repeat_n(edge, value as usize));
        }
    }
    ensure!(
        negative_edges.len() == positive_edges.len(),
        "cancelled signed masses differ"
    );
    Ok(SignedRecord {
        sequence: None,
        active_vertices: n,
        signed_mass: negative_edges.len(),
        negative_edges,
        positive_edges,
        abs_components: None,
        abs_beta: None,
    })
}

pub fn parse_saved_hinges(
    saved: &BTreeMap<String, i64>,
    n: usize,
) -> Result<HashMap<Vec<i16>, i64>> {
    saved
        .iter()
        .map(|(key, &value)| {
            let direction: Vec<i16> = key
                .split(',')
                .map(str::parse)
                .collect::<std::result::Result<_, _>>()?;
            ensure!(
                direction.len() == n,
                "saved hinge direction length mismatch"
            );
            Ok((direction, value))
        })
        .collect::<Result<HashMap<_, _>>>()
}

pub fn saved_column(template: &SavedTemplate, n: usize) -> Result<SparseColumn> {
    ensure!(
        template.linear.len() == n,
        "saved linear vector length mismatch"
    );
    Ok(SparseColumn {
        linear: template.linear.clone(),
        hinges: parse_saved_hinges(&template.hinges, n)?,
    })
}

#[derive(Clone, Debug, Deserialize)]
pub struct HingeWeight {
    pub direction: Vec<i16>,
    pub weight_mod_prime: u64,
}

#[derive(Clone, Debug, Deserialize)]
pub struct LinearWeight {
    pub rank: usize,
    pub weight_mod_prime: u64,
}

#[derive(Clone, Debug, Deserialize)]
pub struct ModularDual {
    pub label: String,
    pub modulus: u64,
    pub hinge_weights: Vec<HingeWeight>,
    pub linear_weights: Vec<LinearWeight>,
}

#[derive(Clone, Debug, Deserialize)]
pub struct DualFile {
    pub n: usize,
    pub branch_edge_occurrences: usize,
    pub modular_duals: Vec<ModularDual>,
}

#[derive(Debug)]
pub struct CompiledDual {
    pub fields: Vec<ModularDual>,
    weights: HashMap<Vec<i16>, Vec<u64>>,
    linear: Vec<Vec<u64>>,
}

impl CompiledDual {
    pub fn new(dual: DualFile) -> Result<Self> {
        validate_dimensions(dual.n, dual.branch_edge_occurrences)?;
        ensure!(!dual.modular_duals.is_empty(), "dual contains no fields");
        let mut weights: HashMap<Vec<i16>, Vec<u64>> = HashMap::default();
        let mut linear = vec![vec![0u64; dual.n]; dual.modular_duals.len()];
        for (field_index, field) in dual.modular_duals.iter().enumerate() {
            ensure!(field.modulus >= 2, "dual modulus is too small");
            for item in &field.hinge_weights {
                ensure!(
                    item.direction.len() == dual.n,
                    "dual direction length mismatch"
                );
                ensure!(
                    item.weight_mod_prime < field.modulus,
                    "unreduced hinge weight"
                );
                let row = weights
                    .entry(item.direction.clone())
                    .or_insert_with(|| vec![0; dual.modular_duals.len()]);
                ensure!(row[field_index] == 0, "duplicate nonzero hinge weight");
                row[field_index] = item.weight_mod_prime;
            }
            for item in &field.linear_weights {
                ensure!(item.rank < dual.n, "linear rank out of range");
                ensure!(
                    item.weight_mod_prime < field.modulus,
                    "unreduced linear weight"
                );
                ensure!(
                    linear[field_index][item.rank] == 0,
                    "duplicate nonzero linear weight"
                );
                linear[field_index][item.rank] = item.weight_mod_prime;
            }
        }
        Ok(Self {
            fields: dual.modular_duals,
            weights,
            linear,
        })
    }

    pub fn price(&self, column: &SparseColumn) -> Vec<u64> {
        let mut result = vec![0u64; self.fields.len()];
        for (rank, &coefficient) in column.linear.iter().enumerate() {
            for (field_index, field) in self.fields.iter().enumerate() {
                add_mod_product(
                    &mut result[field_index],
                    coefficient,
                    self.linear[field_index][rank],
                    field.modulus,
                );
            }
        }
        for (direction, &coefficient) in &column.hinges {
            if let Some(weights) = self.weights.get(direction) {
                for (field_index, field) in self.fields.iter().enumerate() {
                    add_mod_product(
                        &mut result[field_index],
                        coefficient,
                        weights[field_index],
                        field.modulus,
                    );
                }
            }
        }
        result
    }
}

fn add_mod_product(accumulator: &mut u64, coefficient: i64, weight: u64, modulus: u64) {
    let left = (coefficient as i128).rem_euclid(modulus as i128) as u128;
    *accumulator = ((*accumulator as u128 + left * weight as u128) % modulus as u128) as u64;
}

pub fn mutate_one_sign(record: &SignedRecord) -> Result<SignedRecord> {
    let mut mutant = record.clone();
    let edge = mutant
        .negative_edges
        .pop()
        .or_else(|| mutant.positive_edges.pop())
        .ok_or_else(|| anyhow::anyhow!("zero signed record has no sign to flip"))?;
    if mutant.negative_edges.len() + 1 == record.negative_edges.len() {
        mutant.positive_edges.push(edge);
    } else {
        mutant.negative_edges.push(edge);
    }
    // Deliberately retain the original signed_mass.  Validation must reject the
    // resulting one-sign corruption because the two signed masses no longer agree.
    Ok(mutant)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_record() -> SignedRecord {
        SignedRecord {
            sequence: None,
            active_vertices: 5,
            signed_mass: 2,
            negative_edges: vec![[0, 1], [2, 3]],
            positive_edges: vec![[0, 2], [1, 4]],
            abs_components: None,
            abs_beta: None,
        }
    }

    #[test]
    fn dynamic_program_matches_literal_permutations() {
        let record = sample_record();
        let dynamic = generate_column(&record, 5, 2).unwrap();
        let literal = brute_force_column(&record, 5, 2).unwrap();
        assert_eq!(dynamic, literal);
    }

    #[test]
    fn branch_swap_is_exactly_invariant() {
        let record = sample_record();
        let mut swapped = record.clone();
        std::mem::swap(&mut swapped.negative_edges, &mut swapped.positive_edges);
        assert_eq!(
            generate_column(&record, 5, 2).unwrap(),
            generate_column(&swapped, 5, 2).unwrap()
        );
    }

    #[test]
    fn one_sign_corruption_is_rejected() {
        let record = sample_record();
        let mutant = mutate_one_sign(&record).unwrap();
        assert!(generate_column(&mutant, 5, 2).is_err());
    }

    #[test]
    fn zero_signed_graph_has_only_universal_linear_base() {
        let record = SignedRecord {
            sequence: None,
            active_vertices: 0,
            signed_mass: 0,
            negative_edges: vec![],
            positive_edges: vec![],
            abs_components: None,
            abs_beta: None,
        };
        let column = generate_column(&record, 5, 2).unwrap();
        assert!(column.hinges.is_empty());
        assert_eq!(column.linear, vec![0, 24, 48, 72, 96]);
    }

    #[test]
    fn record_from_branches_cancels_common_edges() {
        let record =
            record_from_branches(&[[0, 1], [0, 2], [3, 4]], &[[0, 1], [1, 2], [3, 4]], 5).unwrap();
        assert_eq!(record.signed_mass, 1);
        assert_eq!(record.negative_edges, vec![[0, 2]]);
        assert_eq!(record.positive_edges, vec![[1, 2]]);
    }

    #[test]
    fn common_loop_carriers_scale_with_branch_size() {
        let four_l = common_loop_carrier_column(11, 4).unwrap();
        let five_l = common_loop_carrier_column(11, 5).unwrap();
        assert_eq!(four_l.linear, vec![14_515_200; 11]);
        assert_eq!(five_l.linear, vec![18_144_000; 11]);
        assert!(four_l.hinges.is_empty());
        assert!(five_l.hinges.is_empty());
    }
}
