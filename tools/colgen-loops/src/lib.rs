//! Exact sparse columns for loop-inclusive signed-W records.
//!
//! The public record and sparse-column types come from `max11-colgen`.  A
//! loopless canonical record delegates to that crate in production; records
//! with diagonal pairs use the loop-aware subset DP here.

use anyhow::{Result, ensure};
use max11_colgen::{SignedRecord, SparseColumn};
use rustc_hash::FxHashMap as HashMap;
use std::collections::{BTreeMap, BTreeSet};

pub use max11_colgen::{ColumnOutput, HingeEntry, MAX_N};

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

fn gcd(mut left: i64, mut right: i64) -> i64 {
    left = left.abs();
    right = right.abs();
    while right != 0 {
        let remainder = left % right;
        left = right;
        right = remainder;
    }
    left
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

fn signed_matrix(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
    mutate_first_diagonal_sign: bool,
) -> Result<(Vec<Vec<i16>>, usize)> {
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
    let negative: BTreeSet<[usize; 2]> = record.negative_edges.iter().copied().collect();
    let positive: BTreeSet<[usize; 2]> = record.positive_edges.iter().copied().collect();
    ensure!(
        negative.is_disjoint(&positive),
        "opposite signs share an uncancelled edge"
    );

    let mut matrix = vec![vec![0i16; n]; n];
    let mut negative_loop_count = 0usize;
    let mut diagonal_mutated = false;
    for (sign, edges) in [
        (-1i16, &record.negative_edges),
        (1i16, &record.positive_edges),
    ] {
        for &[first, second] in edges {
            ensure!(
                first <= second && second < n,
                "edge [{first},{second}] is noncanonical or out of range"
            );
            if record.signed_mass > 0 {
                ensure!(
                    second < record.active_vertices,
                    "edge endpoint lies outside active vertex range"
                );
            }
            if first == second {
                negative_loop_count += usize::from(sign < 0);
                let contribution = if mutate_first_diagonal_sign && !diagonal_mutated {
                    diagonal_mutated = true;
                    -sign
                } else {
                    sign
                };
                matrix[first][first] = matrix[first][first]
                    .checked_add(contribution)
                    .ok_or_else(|| anyhow::anyhow!("signed diagonal entry overflow"))?;
            } else {
                matrix[first][second] = matrix[first][second]
                    .checked_add(sign)
                    .ok_or_else(|| anyhow::anyhow!("signed matrix entry overflow"))?;
                matrix[second][first] = matrix[second][first]
                    .checked_add(sign)
                    .ok_or_else(|| anyhow::anyhow!("signed matrix entry overflow"))?;
            }
        }
    }
    Ok((matrix, negative_loop_count))
}

fn increments(matrix: &[Vec<i16>], n: usize) -> Result<Vec<Vec<i16>>> {
    let width = 1usize << n;
    let mut result = vec![vec![0i16; width]; n];
    for vertex in 0..n {
        result[vertex][0] = matrix[vertex][vertex];
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

fn active_on_ordered_cone(direction: &[i16]) -> bool {
    let mut prefix = 0i64;
    for &value in &direction[..direction.len() - 1] {
        prefix += value as i64;
        if prefix < 0 {
            return true;
        }
    }
    false
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

    if active_on_ordered_cone(&direction) {
        let contribution = count_i64
            .checked_mul(divisor)
            .ok_or_else(|| anyhow::anyhow!("hinge contribution overflow"))?;
        let entry = column.hinges.entry(direction).or_default();
        add_checked(entry, contribution, "hinge")?;
    }
    Ok(())
}

fn initialized_column(
    n: usize,
    branch_edges: usize,
    negative_loop_count: usize,
    common_loop_count: usize,
) -> Result<SparseColumn> {
    let total_base_loops = negative_loop_count
        .checked_add(common_loop_count)
        .ok_or_else(|| anyhow::anyhow!("base loop count overflow"))?;
    ensure!(
        total_base_loops <= branch_edges,
        "base contains more loops than branch occurrences"
    );
    let loop_orbit = i64::try_from(checked_factorial(n - 1)?)?;
    let edge_orbit = i64::try_from(
        2u64.checked_mul(checked_factorial(n - 2)?)
            .ok_or_else(|| anyhow::anyhow!("nonloop orbit factor overflow"))?,
    )?;
    let loop_factor = i64::try_from(total_base_loops)?;
    let nonloop_factor = i64::try_from(branch_edges - total_base_loops)?;
    let mut linear = Vec::with_capacity(n);
    for rank in 0..n {
        let loops = loop_factor
            .checked_mul(loop_orbit)
            .ok_or_else(|| anyhow::anyhow!("loop base coefficient overflow"))?;
        let nonloops = nonloop_factor
            .checked_mul(edge_orbit)
            .and_then(|value| value.checked_mul(rank as i64))
            .ok_or_else(|| anyhow::anyhow!("nonloop base coefficient overflow"))?;
        linear.push(
            loops
                .checked_add(nonloops)
                .ok_or_else(|| anyhow::anyhow!("base coefficient overflow"))?,
        );
    }
    Ok(SparseColumn {
        linear,
        hinges: HashMap::default(),
    })
}

fn generate_native_with_diagonal_sign(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
    common_loop_count: usize,
    mutate_first_diagonal_sign: bool,
) -> Result<SparseColumn> {
    let (matrix, negative_loop_count) =
        signed_matrix(record, n, branch_edges, mutate_first_diagonal_sign)?;
    ensure!(
        !mutate_first_diagonal_sign || diagonal_mutated(record),
        "diagonal sign mutant requires a loop"
    );
    ensure!(
        common_loop_count <= branch_edges - record.signed_mass,
        "common loop count exceeds cancelled padding"
    );
    let increments = increments(&matrix, n)?;
    let mut current: HashMap<State, u64> = HashMap::default();
    current.insert(
        State {
            mask: 0,
            word: [0; MAX_N],
        },
        1,
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
    let mut column = initialized_column(n, branch_edges, negative_loop_count, common_loop_count)?;
    for (state, count) in current {
        accumulate_word(&mut column, &state.word[..n], count)?;
    }
    Ok(column)
}

fn contains_loop(record: &SignedRecord) -> bool {
    record
        .negative_edges
        .iter()
        .chain(&record.positive_edges)
        .any(|edge| edge[0] == edge[1])
}

/// Generate a canonical loop-inclusive column.
///
/// `common_loop_count` is the number of cancelled common branch occurrences
/// padded as loops; all remaining cancelled padding is nonloop.  Canonical
/// G-0038 records use zero.
pub fn generate_column(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
    common_loop_count: usize,
) -> Result<SparseColumn> {
    if !contains_loop(record) && common_loop_count == 0 {
        return max11_colgen::generate_column(record, n, branch_edges);
    }
    generate_native_with_diagonal_sign(record, n, branch_edges, common_loop_count, false)
}

/// Exercise this crate's native DP even on loopless input for parity controls.
pub fn generate_column_native(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
    common_loop_count: usize,
) -> Result<SparseColumn> {
    generate_native_with_diagonal_sign(record, n, branch_edges, common_loop_count, false)
}

/// Planted defective variant: reverse only diagonal signed increments.
pub fn generate_column_diagonal_sign_mutant(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
    common_loop_count: usize,
) -> Result<SparseColumn> {
    generate_native_with_diagonal_sign(record, n, branch_edges, common_loop_count, true)
}

fn diagonal_mutated(record: &SignedRecord) -> bool {
    contains_loop(record)
}

/// Convert two equal-size branches into a cancelled signed record and the
/// exact number of cancelled common loop occurrences.
pub fn record_from_branches(
    first: &[[usize; 2]],
    second: &[[usize; 2]],
    n: usize,
) -> Result<(SignedRecord, usize)> {
    ensure!(
        first.len() == second.len(),
        "branch occurrence counts differ"
    );
    let mut first_counts: BTreeMap<[usize; 2], usize> = BTreeMap::new();
    let mut second_counts: BTreeMap<[usize; 2], usize> = BTreeMap::new();
    for (counts, edges) in [(&mut first_counts, first), (&mut second_counts, second)] {
        for &[left, right] in edges {
            ensure!(
                left <= right && right < n,
                "branch contains a noncanonical or out-of-range edge"
            );
            let entry = counts.entry([left, right]).or_default();
            *entry = entry
                .checked_add(1)
                .ok_or_else(|| anyhow::anyhow!("edge multiplicity overflow"))?;
        }
    }
    let keys: BTreeSet<[usize; 2]> = first_counts
        .keys()
        .chain(second_counts.keys())
        .copied()
        .collect();
    let mut negative_edges = Vec::new();
    let mut positive_edges = Vec::new();
    let mut common_loop_count = 0usize;
    for edge in keys {
        let left = first_counts.get(&edge).copied().unwrap_or(0);
        let right = second_counts.get(&edge).copied().unwrap_or(0);
        let common = left.min(right);
        if edge[0] == edge[1] {
            common_loop_count += common;
        }
        negative_edges.extend(std::iter::repeat_n(edge, left - common));
        positive_edges.extend(std::iter::repeat_n(edge, right - common));
    }
    ensure!(
        negative_edges.len() == positive_edges.len(),
        "cancelled signed masses differ"
    );
    let active_vertices = negative_edges
        .iter()
        .chain(&positive_edges)
        .flat_map(|edge| edge.iter().copied())
        .max()
        .map_or(0, |vertex| vertex + 1);
    Ok((
        SignedRecord {
            sequence: None,
            active_vertices,
            signed_mass: negative_edges.len(),
            negative_edges,
            positive_edges,
            abs_components: None,
            abs_beta: None,
        },
        common_loop_count,
    ))
}

/// Literal S_n enumeration from the two uncancelled branches.  This route
/// intentionally does not use the signed-matrix/base decomposition.
pub fn brute_force_branches(
    first: &[[usize; 2]],
    second: &[[usize; 2]],
    n: usize,
) -> Result<SparseColumn> {
    validate_dimensions(n, first.len())?;
    ensure!(n <= 10, "literal permutation control is capped at n=10");
    ensure!(
        first.len() == second.len(),
        "branch occurrence counts differ"
    );
    for &[left, right] in first.iter().chain(second) {
        ensure!(left <= right && right < n, "invalid branch edge");
    }
    let mut column = SparseColumn {
        linear: vec![0; n],
        hinges: HashMap::default(),
    };
    let mut order = Vec::with_capacity(n);
    let mut used = vec![false; n];

    fn visit(
        first: &[[usize; 2]],
        second: &[[usize; 2]],
        n: usize,
        order: &mut Vec<usize>,
        used: &mut [bool],
        column: &mut SparseColumn,
    ) -> Result<()> {
        if order.len() == n {
            let mut position = vec![0usize; n];
            for (rank, &vertex) in order.iter().enumerate() {
                position[vertex] = rank;
            }
            let mut forms = [vec![0i16; n], vec![0i16; n]];
            for (form, edges) in forms.iter_mut().zip([first, second]) {
                for &[left, right] in edges {
                    let rank = position[left].max(position[right]);
                    form[rank] = form[rank]
                        .checked_add(1)
                        .ok_or_else(|| anyhow::anyhow!("literal branch coefficient overflow"))?;
                }
            }
            if forms[1] < forms[0] {
                forms.swap(0, 1);
            }
            for (target, &value) in column.linear.iter_mut().zip(&forms[0]) {
                add_checked(target, value as i64, "literal linear")?;
            }
            let direction: Vec<i16> = forms[1]
                .iter()
                .zip(&forms[0])
                .map(|(&right, &left)| right - left)
                .collect();
            let first_nonzero = direction.iter().copied().find(|&value| value != 0);
            if first_nonzero.is_none() {
                return Ok(());
            }
            ensure!(
                first_nonzero.unwrap() > 0,
                "literal direction orientation failed"
            );
            ensure!(direction.iter().map(|&value| value as i64).sum::<i64>() == 0);
            if !active_on_ordered_cone(&direction) {
                return Ok(());
            }
            let divisor = direction
                .iter()
                .fold(0i64, |current, &value| gcd(current, value as i64));
            let primitive: Vec<i16> = direction
                .iter()
                .map(|&value| i16::try_from(value as i64 / divisor))
                .collect::<std::result::Result<_, _>>()?;
            let entry = column.hinges.entry(primitive).or_default();
            add_checked(entry, divisor, "literal hinge")?;
            return Ok(());
        }
        for vertex in 0..n {
            if used[vertex] {
                continue;
            }
            used[vertex] = true;
            order.push(vertex);
            visit(first, second, n, order, used, column)?;
            order.pop();
            used[vertex] = false;
        }
        Ok(())
    }

    visit(first, second, n, &mut order, &mut used, &mut column)?;
    Ok(column)
}

/// The two `s=0` carrier atoms, in MCOLGEN row convention.
pub fn base_atoms(n: usize, branch_edges: usize) -> Result<(SparseColumn, SparseColumn)> {
    let zero = SignedRecord {
        sequence: None,
        active_vertices: 0,
        signed_mass: 0,
        negative_edges: Vec::new(),
        positive_edges: Vec::new(),
        abs_components: None,
        abs_beta: None,
    };
    Ok((
        generate_column_native(&zero, n, branch_edges, 0)?,
        generate_column_native(&zero, n, branch_edges, branch_edges)?,
    ))
}

#[cfg(test)]
mod tests {
    use super::*;

    fn mixed_branches() -> (Vec<[usize; 2]>, Vec<[usize; 2]>) {
        (vec![[0, 0], [0, 2], [3, 4]], vec![[1, 1], [0, 3], [3, 4]])
    }

    #[test]
    fn loop_aware_dp_matches_literal_permutations() {
        let (first, second) = mixed_branches();
        let (record, common_loops) = record_from_branches(&first, &second, 5).unwrap();
        assert_eq!(common_loops, 0);
        let dynamic = generate_column_native(&record, 5, 3, common_loops).unwrap();
        let literal = brute_force_branches(&first, &second, 5).unwrap();
        assert_eq!(dynamic, literal);
        assert!(dynamic.hinges.keys().any(|direction| direction[0] != 0));
    }

    #[test]
    fn loopless_native_dp_matches_dependency() {
        let record = SignedRecord {
            sequence: None,
            active_vertices: 5,
            signed_mass: 2,
            negative_edges: vec![[0, 1], [2, 3]],
            positive_edges: vec![[0, 2], [1, 4]],
            abs_components: None,
            abs_beta: None,
        };
        assert_eq!(
            generate_column_native(&record, 5, 2, 0).unwrap(),
            max11_colgen::generate_column(&record, 5, 2).unwrap()
        );
        assert_eq!(
            generate_column(&record, 5, 2, 0).unwrap(),
            max11_colgen::generate_column(&record, 5, 2).unwrap()
        );
    }

    #[test]
    fn common_loop_and_nonloop_bases_are_distinct() {
        let (nonloops, loops) = base_atoms(5, 5).unwrap();
        assert_eq!(nonloops.linear, vec![0, 60, 120, 180, 240]);
        assert_eq!(loops.linear, vec![120, 120, 120, 120, 120]);
        assert!(nonloops.hinges.is_empty() && loops.hinges.is_empty());
    }

    #[test]
    fn diagonal_sign_mutant_is_detected() {
        let (first, second) = mixed_branches();
        let (record, common_loops) = record_from_branches(&first, &second, 5).unwrap();
        let expected = brute_force_branches(&first, &second, 5).unwrap();
        let mutant = generate_column_diagonal_sign_mutant(&record, 5, 3, common_loops);
        assert!(mutant.is_err() || mutant.unwrap() != expected);
    }

    #[test]
    fn output_reduces_coefficients_modulo_prime() {
        let (first, second) = mixed_branches();
        let (record, common_loops) = record_from_branches(&first, &second, 5).unwrap();
        let column = generate_column(&record, 5, 3, common_loops).unwrap();
        let output = column.output(7, Some(101)).unwrap();
        assert!(output.linear.iter().all(|&value| (0..101).contains(&value)));
        assert!(
            output
                .hinges
                .iter()
                .all(|hinge| (0..101).contains(&hinge.coefficient))
        );
    }
}
