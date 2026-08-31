use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{
    FullNormalForm, N, Record, active_direction, full_normal_form, linear_vector,
    validate_direction,
};
use num_bigint::BigInt;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};

const PINNED_HINGE_ABS_BOUND: i64 = 199_584_000;
const PINNED_LINEAR_ABS_BOUND: i64 = 235_872_000;

#[derive(Clone, Debug)]
pub(crate) struct ExactNormalForm {
    pub(crate) linear: [BigInt; N],
    pub(crate) hinges: HashMap<[i8; N], BigInt>,
    pub(crate) labelled_permutations: u64,
    pub(crate) compressed_leaves: u64,
}

pub(crate) fn factorial(value: usize) -> u64 {
    (1..=value as u64).product()
}

fn gcd_i64(mut left: i64, mut right: i64) -> i64 {
    left = left.abs();
    right = right.abs();
    while right != 0 {
        (left, right) = (right, left % right);
    }
    left
}

fn exact_increments(record: &Record) -> Result<Vec<Vec<i8>>> {
    ensure!(record.signed_mass <= 5, "signed mass exceeds degree");
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
            matrix[u][v] = matrix[u][v]
                .checked_add(sign)
                .context("increment matrix overflow")?;
            matrix[v][u] = matrix[v][u]
                .checked_add(sign)
                .context("increment matrix overflow")?;
        }
    }
    let mut output = vec![vec![0i8; 1usize << active]; active];
    for vertex in 0..active {
        for mask in 1usize..(1usize << active) {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            output[vertex][mask] = output[vertex][mask ^ bit]
                .checked_add(matrix[vertex][other])
                .context("increment table overflow")?;
        }
    }
    Ok(output)
}

#[allow(clippy::too_many_arguments)]
fn enumerate_exact_words(
    rank: usize,
    active: usize,
    mask: usize,
    inactive_used: usize,
    table: &[Vec<i8>],
    word: &mut [i8; N],
    word_counts: &mut HashMap<[i8; N], u64>,
    compressed_leaves: &mut u64,
) -> Result<()> {
    if rank == N {
        *compressed_leaves = compressed_leaves
            .checked_add(1)
            .context("compressed-leaf census overflow")?;
        let count = word_counts.entry(*word).or_default();
        *count = count.checked_add(1).context("word multiplicity overflow")?;
        return Ok(());
    }
    if inactive_used < N - active {
        word[rank] = 0;
        enumerate_exact_words(
            rank + 1,
            active,
            mask,
            inactive_used + 1,
            table,
            word,
            word_counts,
            compressed_leaves,
        )?;
    }
    for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
        let bit = 1usize << vertex;
        if mask & bit == 0 {
            word[rank] = increments_for_vertex[mask];
            enumerate_exact_words(
                rank + 1,
                active,
                mask | bit,
                inactive_used,
                table,
                word,
                word_counts,
                compressed_leaves,
            )?;
        }
    }
    Ok(())
}

pub(crate) fn exact_full_normal_form(record: &Record) -> Result<ExactNormalForm> {
    let table = exact_increments(record)?;
    let inactive_multiplier = factorial(N - record.active_vertices);
    let mut word_counts = HashMap::<[i8; N], u64>::new();
    let mut compressed_leaves = 0u64;
    enumerate_exact_words(
        0,
        record.active_vertices,
        0,
        0,
        &table,
        &mut [0; N],
        &mut word_counts,
        &mut compressed_leaves,
    )?;
    let labelled_permutations = compressed_leaves
        .checked_mul(inactive_multiplier)
        .context("labelled-permutation census overflow")?;
    ensure!(
        labelled_permutations == factorial(N),
        "full permutation census mismatch"
    );

    let mut linear: [BigInt; N] = std::array::from_fn(|rank| {
        BigInt::from(10u8) * BigInt::from(rank) * BigInt::from(factorial(N - 2))
    });
    let mut hinges = HashMap::<[i8; N], BigInt>::new();
    for (word, compressed_multiplicity) in word_counts {
        let labelled_multiplicity =
            BigInt::from(compressed_multiplicity) * BigInt::from(inactive_multiplier);
        let Some(first) = word.iter().copied().find(|value| *value != 0) else {
            continue;
        };
        if first < 0 {
            for (coordinate, value) in linear.iter_mut().zip(word.iter()) {
                *coordinate += BigInt::from(*value) * &labelled_multiplicity;
            }
        }
        let divisor = word
            .iter()
            .fold(0i64, |current, value| gcd_i64(current, i64::from(*value)));
        ensure!(divisor > 0, "nonzero word has zero gcd");
        let sign = if first > 0 { 1i64 } else { -1i64 };
        let mut direction = [0i8; N];
        for (oriented, value) in direction.iter_mut().zip(word.iter()) {
            *oriented = i8::try_from(sign * i64::from(*value) / divisor)
                .context("primitive direction exceeds i8")?;
        }
        if active_direction(&direction) {
            *hinges.entry(direction).or_default() += BigInt::from(divisor) * &labelled_multiplicity;
        }
    }
    Ok(ExactNormalForm {
        linear,
        hinges,
        labelled_permutations,
        compressed_leaves,
    })
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

pub(crate) fn exact_linear_vector(record: &Record) -> Result<[BigInt; N]> {
    let table = exact_increments(record)?;
    let active = record.active_vertices;
    let inactive = N - active;
    let states = 1usize << active;
    let mut current = vec![[0u64; 3]; states];
    current[0][0] = 1;
    let mut correction: [BigInt; N] = std::array::from_fn(|_| BigInt::from(0));
    for (rank, correction_at_rank) in correction.iter_mut().enumerate() {
        let mut next = vec![[0u64; 3]; states];
        for (mask, counts) in current.iter().enumerate() {
            let placed = mask.count_ones() as usize;
            if placed > rank {
                continue;
            }
            let inactive_used = rank - placed;
            for (status, count) in counts.iter().copied().enumerate() {
                if count == 0 {
                    continue;
                }
                if inactive_used < inactive {
                    next[mask][status] = next[mask][status]
                        .checked_add(count)
                        .context("linear DP count overflow")?;
                }
                for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
                    let bit = 1usize << vertex;
                    if mask & bit != 0 {
                        continue;
                    }
                    let increment = increments_for_vertex[mask];
                    let new_mask = mask | bit;
                    let new_status = next_sign(status, increment);
                    next[new_mask][new_status] = next[new_mask][new_status]
                        .checked_add(count)
                        .context("linear DP count overflow")?;
                    if new_status == 2 {
                        let remaining_slots = N - rank - 1;
                        let remaining_active = active - new_mask.count_ones() as usize;
                        let remaining_inactive = remaining_slots - remaining_active;
                        let completions =
                            factorial(remaining_slots) / factorial(remaining_inactive);
                        *correction_at_rank += BigInt::from(count)
                            * BigInt::from(increment)
                            * BigInt::from(completions);
                    }
                }
            }
        }
        current = next;
    }
    let injection_count = current[(1usize << active) - 1]
        .iter()
        .try_fold(0u64, |total, count| total.checked_add(*count))
        .context("linear injection census overflow")?;
    ensure!(
        injection_count
            .checked_mul(factorial(inactive))
            .context("linear labelled census overflow")?
            == factorial(N),
        "linear rank-injection census mismatch"
    );
    let inactive_multiplier = BigInt::from(factorial(inactive));
    Ok(std::array::from_fn(|rank| {
        BigInt::from(10u8) * BigInt::from(rank) * BigInt::from(factorial(N - 2))
            + &correction[rank] * &inactive_multiplier
    }))
}

fn exact_matching_injections(
    table: &[Vec<i8>],
    active: usize,
    direction: &[i8; N],
    scale: i8,
) -> Result<u64> {
    let full = (1usize << active) - 1;
    let inactive = N - active;
    let mut current = vec![0u64; 1usize << active];
    current[0] = 1;
    for (rank, coordinate) in direction.iter().copied().enumerate() {
        let expected = i16::from(scale) * i16::from(coordinate);
        let mut next = vec![0u64; 1usize << active];
        for (mask, count) in current.iter().copied().enumerate() {
            if count == 0 {
                continue;
            }
            let placed = mask.count_ones() as usize;
            if placed > rank {
                continue;
            }
            let inactive_used = rank - placed;
            if expected == 0 && inactive_used < inactive {
                next[mask] = next[mask]
                    .checked_add(count)
                    .context("hinge DP count overflow")?;
            }
            for (vertex, increments_for_vertex) in table.iter().enumerate().take(active) {
                let bit = 1usize << vertex;
                if mask & bit == 0 && i16::from(increments_for_vertex[mask]) == expected {
                    next[mask | bit] = next[mask | bit]
                        .checked_add(count)
                        .context("hinge DP count overflow")?;
                }
            }
        }
        current = next;
    }
    Ok(current[full])
}

pub(crate) fn exact_hinge_coefficients(
    record: &Record,
    directions: &[[i8; N]],
) -> Result<Vec<BigInt>> {
    for direction in directions {
        validate_direction(direction)?;
    }
    let table = exact_increments(record)?;
    directions
        .iter()
        .map(|direction| {
            let mut coefficient = BigInt::from(0);
            for scale in -5i8..=5 {
                if scale == 0 {
                    continue;
                }
                coefficient += BigInt::from(scale.unsigned_abs())
                    * BigInt::from(exact_matching_injections(
                        &table,
                        record.active_vertices,
                        direction,
                        scale,
                    )?);
            }
            Ok(coefficient * BigInt::from(factorial(N - record.active_vertices)))
        })
        .collect()
}

fn exact_matches_pinned(record: &Record, exact: &ExactNormalForm) -> Result<()> {
    let pinned: FullNormalForm = full_normal_form(record)?;
    let pinned_linear = linear_vector(record)?;
    ensure!(
        pinned
            .hinges
            .values()
            .all(|value| value.unsigned_abs() <= PINNED_HINGE_ABS_BOUND as u64)
            && pinned
                .linear
                .iter()
                .all(|value| value.unsigned_abs() <= PINNED_LINEAR_ABS_BOUND as u64)
            && pinned_linear
                .iter()
                .all(|value| value.unsigned_abs() <= PINNED_LINEAR_ABS_BOUND as u64),
        "bounded diagnostic kernel exceeded its frozen-domain bound"
    );
    ensure!(
        pinned.labelled_permutations == exact.labelled_permutations,
        "bounded/exact permutation census disagreement"
    );
    ensure!(
        pinned
            .linear
            .iter()
            .zip(exact.linear.iter())
            .all(|(bounded, exact_value)| BigInt::from(*bounded) == *exact_value)
            && pinned_linear
                .iter()
                .zip(exact.linear.iter())
                .all(|(bounded, exact_value)| BigInt::from(*bounded) == *exact_value),
        "bounded/exact linear disagreement"
    );
    let pinned_hinges = pinned
        .hinges
        .into_iter()
        .map(|(direction, value)| (direction, BigInt::from(value)))
        .collect::<HashMap<_, _>>();
    ensure!(
        pinned_hinges == exact.hinges,
        "bounded/exact hinge disagreement"
    );
    Ok(())
}

pub(crate) fn validated_full_normal_form(record: &Record) -> Result<ExactNormalForm> {
    let form = exact_full_normal_form(record)?;
    ensure!(
        form.labelled_permutations == factorial(N),
        "term permutation census drift"
    );
    ensure!(
        form.linear == exact_linear_vector(record)?,
        "independent exact linear route disagreement"
    );
    for direction in form.hinges.keys() {
        validate_direction(direction)?;
    }
    exact_matches_pinned(record, &form)?;
    Ok(form)
}

pub(crate) fn normal_form_digest(
    form: &ExactNormalForm,
    omitted_hinge: Option<[i8; N]>,
    omitted_linear: Option<usize>,
) -> String {
    let mut digest = Sha256::new();
    digest.update(b"G0135-STAGE-D-EXACT-NORMAL-FORM-V1\0");
    digest.update(form.labelled_permutations.to_le_bytes());
    digest.update(form.compressed_leaves.to_le_bytes());
    for (coordinate, value) in form.linear.iter().enumerate() {
        if omitted_linear == Some(coordinate) {
            continue;
        }
        digest.update([coordinate as u8]);
        digest.update(value.to_string().as_bytes());
        digest.update(b"\n");
    }
    for (direction, value) in form.hinges.iter().collect::<BTreeMap<_, _>>() {
        if omitted_hinge.as_ref() == Some(direction) {
            continue;
        }
        for coordinate in direction {
            digest.update([*coordinate as u8]);
        }
        digest.update(value.to_string().as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn exact_routes_agree_on_planted_record() {
        let record = Record {
            sequence: 0,
            signed_mass: 3,
            active_vertices: 6,
            negative_edges: vec![[0, 1], [1, 2], [3, 4]],
            positive_edges: vec![[0, 2], [2, 5], [4, 5]],
        };
        let form = validated_full_normal_form(&record).unwrap();
        let directions = form.hinges.keys().copied().collect::<Vec<_>>();
        let direct = exact_hinge_coefficients(&record, &directions).unwrap();
        assert!(
            directions
                .iter()
                .zip(direct)
                .all(|(direction, value)| form.hinges[direction] == value)
        );
    }
}
