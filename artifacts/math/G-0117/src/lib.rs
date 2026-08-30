use anyhow::{Result, ensure};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const N: usize = 11;
pub const DEGREE: usize = 5;

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Record {
    pub sequence: usize,
    pub signed_mass: usize,
    pub active_vertices: usize,
    pub negative_edges: Vec<[usize; 2]>,
    pub positive_edges: Vec<[usize; 2]>,
}

#[derive(Debug)]
pub struct FullNormalForm {
    pub linear: [i64; N],
    pub hinges: HashMap<[i8; N], i64>,
    pub labelled_permutations: u64,
}

fn factorial(value: usize) -> u64 {
    (1..=value as u64).product()
}

fn gcd(mut first: i64, mut second: i64) -> i64 {
    first = first.abs();
    second = second.abs();
    while second != 0 {
        (first, second) = (second, first % second);
    }
    first
}

pub fn active_direction(direction: &[i8; N]) -> bool {
    let mut prefix = 0i16;
    for &value in &direction[..N - 1] {
        prefix += i16::from(value);
        if prefix < 0 {
            return true;
        }
    }
    false
}

pub fn validate_direction(direction: &[i8; N]) -> Result<()> {
    ensure!(
        direction.iter().map(|value| i64::from(*value)).sum::<i64>() == 0,
        "direction must sum to zero"
    );
    let first = direction.iter().copied().find(|value| *value != 0);
    ensure!(
        first.is_some_and(|value| value > 0),
        "direction orientation drift"
    );
    ensure!(
        direction
            .iter()
            .fold(0i64, |current, value| gcd(current, i64::from(*value)))
            == 1,
        "direction is not primitive"
    );
    ensure!(
        active_direction(direction),
        "direction is linear on the ordered cone"
    );
    Ok(())
}

fn increments(record: &Record) -> Result<Vec<Vec<i8>>> {
    ensure!(record.signed_mass <= DEGREE, "signed mass exceeds degree");
    ensure!(record.active_vertices <= N, "active support exceeds n");
    ensure!(
        record.negative_edges.len() == record.signed_mass
            && record.positive_edges.len() == record.signed_mass,
        "edge mass mismatch"
    );
    let active = record.active_vertices;
    let mut matrix = vec![vec![0i8; active]; active];
    for (sign, edges) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        for &[u, v] in edges {
            ensure!(u < v && v < active, "record must be compact and loopless");
            matrix[u][v] += sign;
            matrix[v][u] += sign;
        }
    }
    let mut output = vec![vec![0i8; 1usize << active]; active];
    for vertex in 0..active {
        for mask in 1usize..(1usize << active) {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            output[vertex][mask] = output[vertex][mask ^ bit] + matrix[vertex][other];
        }
    }
    Ok(output)
}

fn matching_injections(table: &[Vec<i8>], active: usize, direction: &[i8; N], scale: i8) -> u64 {
    let full = (1usize << active) - 1;
    let inactive = N - active;
    let mut current = vec![0u64; 1usize << active];
    current[0] = 1;
    for (rank, &coordinate) in direction.iter().enumerate() {
        let expected = i16::from(scale) * i16::from(coordinate);
        let mut next = vec![0u64; 1usize << active];
        for (mask, &count) in current.iter().enumerate() {
            if count == 0 {
                continue;
            }
            let placed = mask.count_ones() as usize;
            if placed > rank {
                continue;
            }
            let inactive_used = rank - placed;
            if expected == 0 && inactive_used < inactive {
                next[mask] += count;
            }
            for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
                let bit = 1usize << vertex;
                if mask & bit == 0 && i16::from(increments_for_vertex[mask]) == expected {
                    next[mask | bit] += count;
                }
            }
        }
        current = next;
    }
    current[full]
}

/// Exact coefficient of one primitive, first-positive, ordered-cone-active
/// direction in the full S_11 orbit sum of a loopless degree-five atom.
pub fn hinge_coefficient(record: &Record, direction: &[i8; N]) -> Result<i64> {
    validate_direction(direction)?;
    let table = increments(record)?;
    let mut unlabelled = 0u64;
    for scale in -5i8..=5 {
        if scale == 0 {
            continue;
        }
        unlabelled += u64::from(scale.unsigned_abs())
            * matching_injections(&table, record.active_vertices, direction, scale);
    }
    let labelled = unlabelled
        .checked_mul(factorial(N - record.active_vertices))
        .expect("hinge coefficient overflow");
    Ok(i64::try_from(labelled).expect("hinge coefficient exceeds i64"))
}

fn next_sign(status: usize, increment: i8) -> usize {
    if status != 0 || increment == 0 {
        status
    } else if increment > 0 {
        1
    } else {
        2
    }
}

/// Exact linear vector of the same full orbit sum.  Status 0/1/2 means the
/// raw word's first nonzero entry is unseen/positive/negative.
pub fn linear_vector(record: &Record) -> Result<[i64; N]> {
    let table = increments(record)?;
    let active = record.active_vertices;
    let inactive = N - active;
    let states = 1usize << active;
    let mut current = vec![[0u64; 3]; states];
    current[0][0] = 1;
    let mut correction = [0i128; N];

    for (rank, correction_at_rank) in correction.iter_mut().enumerate() {
        let mut next = vec![[0u64; 3]; states];
        for (mask, counts) in current.iter().enumerate() {
            let placed = mask.count_ones() as usize;
            if placed > rank {
                continue;
            }
            let inactive_used = rank - placed;
            for (status, &count) in counts.iter().enumerate() {
                if count == 0 {
                    continue;
                }
                if inactive_used < inactive {
                    next[mask][status] += count;
                }
                for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
                    let bit = 1usize << vertex;
                    if mask & bit != 0 {
                        continue;
                    }
                    let increment = increments_for_vertex[mask];
                    let new_mask = mask | bit;
                    let new_status = next_sign(status, increment);
                    next[new_mask][new_status] += count;
                    if new_status == 2 {
                        let remaining_slots = N - rank - 1;
                        let remaining_active = active - new_mask.count_ones() as usize;
                        let remaining_inactive = remaining_slots - remaining_active;
                        let completions =
                            factorial(remaining_slots) / factorial(remaining_inactive);
                        *correction_at_rank +=
                            i128::from(count) * i128::from(increment) * i128::from(completions);
                    }
                }
            }
        }
        current = next;
    }

    let injection_count = current[(1usize << active) - 1].iter().sum::<u64>();
    ensure!(
        injection_count * factorial(inactive) == factorial(N),
        "rank-injection census mismatch"
    );
    let inactive_multiplier = i128::from(factorial(inactive));
    let mut output = [0i64; N];
    for rank in 0..N {
        let base = 10i128 * rank as i128 * i128::from(factorial(N - 2));
        let value = base + correction[rank] * inactive_multiplier;
        output[rank] = i64::try_from(value).expect("linear coordinate exceeds i64");
    }
    Ok(output)
}

fn observe_full_word(
    word: &[i8; N],
    multiplicity: u64,
    linear: &mut [i64; N],
    hinges: &mut HashMap<[i8; N], i64>,
) {
    let Some(first) = word.iter().copied().find(|value| *value != 0) else {
        return;
    };
    if first < 0 {
        for (coordinate, &value) in linear.iter_mut().zip(word.iter()) {
            *coordinate += i64::from(value) * multiplicity as i64;
        }
    }
    let divisor = word
        .iter()
        .fold(0i64, |current, value| gcd(current, i64::from(*value)));
    let sign = if first > 0 { 1 } else { -1 };
    let mut direction = [0i8; N];
    for (oriented, &value) in direction.iter_mut().zip(word.iter()) {
        *oriented = (sign * i64::from(value) / divisor) as i8;
    }
    if active_direction(&direction) {
        *hinges.entry(direction).or_default() += divisor * multiplicity as i64;
    }
}

#[allow(clippy::too_many_arguments)]
fn enumerate_full_words(
    rank: usize,
    active: usize,
    mask: usize,
    inactive_used: usize,
    table: &[Vec<i8>],
    word: &mut [i8; N],
    multiplicity: u64,
    linear: &mut [i64; N],
    hinges: &mut HashMap<[i8; N], i64>,
    labelled_permutations: &mut u64,
) {
    if rank == N {
        *labelled_permutations += multiplicity;
        observe_full_word(word, multiplicity, linear, hinges);
        return;
    }
    if inactive_used < N - active {
        word[rank] = 0;
        enumerate_full_words(
            rank + 1,
            active,
            mask,
            inactive_used + 1,
            table,
            word,
            multiplicity,
            linear,
            hinges,
            labelled_permutations,
        );
    }
    for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
        let bit = 1usize << vertex;
        if mask & bit == 0 {
            word[rank] = increments_for_vertex[mask];
            enumerate_full_words(
                rank + 1,
                active,
                mask | bit,
                inactive_used,
                table,
                word,
                multiplicity,
                linear,
                hinges,
                labelled_permutations,
            );
        }
    }
}

/// Complete exact ordered-cone normal form.  This deliberately enumerates the
/// full labelled S_11 orbit and is reserved for sparse certificate replay, not
/// family-wide pricing.
pub fn full_normal_form(record: &Record) -> Result<FullNormalForm> {
    let table = increments(record)?;
    let multiplicity = factorial(N - record.active_vertices);
    let mut linear = [0i64; N];
    for (rank, coordinate) in linear.iter_mut().enumerate() {
        *coordinate = 10 * rank as i64 * factorial(N - 2) as i64;
    }
    let mut hinges = HashMap::new();
    let mut labelled_permutations = 0;
    enumerate_full_words(
        0,
        record.active_vertices,
        0,
        0,
        &table,
        &mut [0; N],
        multiplicity,
        &mut linear,
        &mut hinges,
        &mut labelled_permutations,
    );
    ensure!(
        labelled_permutations == factorial(N),
        "full permutation census mismatch"
    );
    Ok(FullNormalForm {
        linear,
        hinges,
        labelled_permutations,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::BTreeMap;

    #[derive(Default)]
    struct Literal {
        linear: [i64; N],
        hinges: BTreeMap<[i8; N], i64>,
        permutations: u64,
    }

    fn observe(word: [i8; N], multiplicity: u64, literal: &mut Literal) {
        literal.permutations += multiplicity;
        let Some(first) = word.iter().copied().find(|value| *value != 0) else {
            return;
        };
        if first < 0 {
            for (coordinate, &value) in literal.linear.iter_mut().zip(word.iter()) {
                *coordinate += i64::from(value) * multiplicity as i64;
            }
        }
        let divisor = word
            .iter()
            .fold(0i64, |current, value| gcd(current, i64::from(*value)));
        let sign = if first > 0 { 1 } else { -1 };
        let mut direction = [0i8; N];
        for (oriented, &value) in direction.iter_mut().zip(word.iter()) {
            *oriented = (sign * i64::from(value) / divisor) as i8;
        }
        if active_direction(&direction) {
            *literal.hinges.entry(direction).or_default() += divisor * multiplicity as i64;
        }
    }

    fn recurse(
        rank: usize,
        active: usize,
        mask: usize,
        inactive_used: usize,
        table: &[Vec<i8>],
        word: &mut [i8; N],
        literal: &mut Literal,
    ) {
        if rank == N {
            observe(*word, factorial(N - active), literal);
            return;
        }
        if inactive_used < N - active {
            word[rank] = 0;
            recurse(
                rank + 1,
                active,
                mask,
                inactive_used + 1,
                table,
                word,
                literal,
            );
        }
        for vertex in 0..active {
            let bit = 1usize << vertex;
            if mask & bit == 0 {
                word[rank] = table[vertex][mask];
                recurse(
                    rank + 1,
                    active,
                    mask | bit,
                    inactive_used,
                    table,
                    word,
                    literal,
                );
            }
        }
    }

    fn literal(record: &Record) -> Literal {
        let table = increments(record).unwrap();
        let mut output = Literal::default();
        for rank in 0..N {
            output.linear[rank] = 10 * rank as i64 * factorial(N - 2) as i64;
        }
        recurse(
            0,
            record.active_vertices,
            0,
            0,
            &table,
            &mut [0; N],
            &mut output,
        );
        output
    }

    fn sample() -> Record {
        Record {
            sequence: 0,
            signed_mass: 3,
            active_vertices: 6,
            negative_edges: vec![[0, 1], [1, 2], [3, 4]],
            positive_edges: vec![[0, 2], [2, 5], [4, 5]],
        }
    }

    #[test]
    fn subset_dp_matches_literal_complete_support() {
        let record = sample();
        let expected = literal(&record);
        assert_eq!(expected.permutations, factorial(N));
        assert!(!expected.hinges.is_empty());
        assert_eq!(linear_vector(&record).unwrap(), expected.linear);
        let production = full_normal_form(&record).unwrap();
        assert_eq!(production.labelled_permutations, expected.permutations);
        assert_eq!(production.linear, expected.linear);
        assert_eq!(
            production.hinges.into_iter().collect::<BTreeMap<_, _>>(),
            expected.hinges
        );
        for (direction, coefficient) in &expected.hinges {
            assert_eq!(hinge_coefficient(&record, direction).unwrap(), *coefficient);
        }
    }

    #[test]
    fn branch_swap_and_relabel_preserve_hinges() {
        let record = sample();
        let expected = literal(&record);
        let direction = *expected.hinges.keys().next().unwrap();
        let swapped = Record {
            negative_edges: record.positive_edges.clone(),
            positive_edges: record.negative_edges.clone(),
            ..record.clone()
        };
        let permutation = [5usize, 2, 4, 0, 3, 1];
        let map_edges = |edges: &[[usize; 2]]| {
            edges
                .iter()
                .map(|edge| {
                    let mut mapped = [permutation[edge[0]], permutation[edge[1]]];
                    mapped.sort();
                    mapped
                })
                .collect::<Vec<_>>()
        };
        let relabelled = Record {
            negative_edges: map_edges(&record.negative_edges),
            positive_edges: map_edges(&record.positive_edges),
            ..record.clone()
        };
        let value = hinge_coefficient(&record, &direction).unwrap();
        assert_eq!(hinge_coefficient(&swapped, &direction).unwrap(), value);
        assert_eq!(hinge_coefficient(&relabelled, &direction).unwrap(), value);
    }

    #[test]
    fn rejects_noncanonical_directions_and_edge_mutation_changes_semantics() {
        let record = sample();
        let expected = literal(&record);
        let direction = *expected.hinges.keys().next().unwrap();
        let mut negative = direction;
        for value in &mut negative {
            *value = -*value;
        }
        assert!(hinge_coefficient(&record, &negative).is_err());
        let mut mutated = record.clone();
        mutated.positive_edges[0] = [0, 3];
        assert_ne!(
            linear_vector(&mutated).unwrap(),
            linear_vector(&record).unwrap()
        );
        let mutation_literal = literal(&mutated);
        assert!(
            mutation_literal.hinges != expected.hinges
                || mutation_literal.linear != expected.linear
        );
    }

    #[test]
    fn large_valid_direction_cannot_overflow_scale_product() {
        let record = sample();
        let direction = [0, 1, -26, 25, 0, 0, 0, 0, 0, 0, 0];
        validate_direction(&direction).unwrap();
        assert_eq!(hinge_coefficient(&record, &direction).unwrap(), 0);
    }
}
