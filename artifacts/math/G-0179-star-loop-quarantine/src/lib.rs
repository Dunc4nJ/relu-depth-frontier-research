use anyhow::{Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::hash::{BuildHasherDefault, Hash, Hasher};

pub const N: usize = 11;
pub const COLORS: usize = 4;
pub const DEGREE: usize = 5;

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Record {
    pub sequence: usize,
    pub signed_mass: usize,
    pub active_vertices: usize,
    pub negative_loop_count: usize,
    pub positive_loop_count: usize,
    pub negative_edges: Vec<[usize; 2]>,
    pub positive_edges: Vec<[usize; 2]>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Row {
    pub levels: [i64; COLORS],
    pub profile: [u8; COLORS],
    pub formal_stabilizer: u64,
}

#[derive(Clone, Debug, Serialize)]
pub struct HingeTerm {
    pub direction: [i8; N],
    pub coefficient: i64,
}

#[derive(Clone, Debug, Serialize)]
pub struct NormalForm {
    pub sequence: usize,
    pub active_vertices: usize,
    pub diagonal_multiplier: i8,
    pub labelled_permutation_count: u64,
    pub zero_word_permutation_count: u64,
    pub negative_word_permutation_count: u64,
    pub inactive_oriented_permutation_count: u64,
    pub hinge_direction_count: usize,
    pub base_linear: [i64; N],
    pub orientation_correction: [i64; N],
    pub linear: [i64; N],
    pub hinges: Vec<HingeTerm>,
}

#[derive(Clone, Debug)]
pub struct PricedColumn {
    pub panel: Vec<i128>,
    pub linear: [i64; N],
    pub hinges: Vec<i64>,
}

pub fn factorial(value: usize) -> u64 {
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
        "direction is linear on ordered cone"
    );
    Ok(())
}

pub fn positive_mass(direction: &[i8; N]) -> usize {
    direction
        .iter()
        .filter(|value| **value > 0)
        .map(|value| usize::from(value.unsigned_abs()))
        .sum()
}

pub fn validate_record(record: &Record) -> Result<()> {
    ensure!(record.signed_mass <= DEGREE, "signed mass exceeds degree");
    ensure!(record.active_vertices <= N, "active support exceeds N");
    ensure!(
        record.negative_edges.len() == record.signed_mass
            && record.positive_edges.len() == record.signed_mass,
        "edge mass mismatch"
    );
    ensure!(
        record.negative_loop_count
            == record
                .negative_edges
                .iter()
                .filter(|edge| edge[0] == edge[1])
                .count(),
        "negative-loop count mismatch"
    );
    ensure!(
        record.positive_loop_count
            == record
                .positive_edges
                .iter()
                .filter(|edge| edge[0] == edge[1])
                .count(),
        "positive-loop count mismatch"
    );
    for side in [&record.negative_edges, &record.positive_edges] {
        ensure!(
            side.windows(2).all(|pair| pair[0] <= pair[1]),
            "edge order drift"
        );
        for &[u, v] in side {
            ensure!(
                u <= v && v < record.active_vertices,
                "edge outside active support"
            );
        }
    }
    Ok(())
}

fn increment_table(record: &Record) -> Result<Vec<Vec<i8>>> {
    validate_record(record)?;
    let active = record.active_vertices;
    let mut matrix = vec![vec![0i8; active]; active];
    for (sign, edges) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        for &[u, v] in edges {
            if u == v {
                matrix[u][u] += sign;
            } else {
                matrix[u][v] += sign;
                matrix[v][u] += sign;
            }
        }
    }
    let mut output = vec![vec![0i8; 1usize << active]; active];
    for vertex in 0..active {
        // A loop contributes when its vertex is inserted, independently of
        // the previously inserted subset.  This is diagonal_multiplier=1.
        output[vertex][0] = matrix[vertex][vertex];
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
            for (vertex, increments) in table.iter().enumerate().take(active) {
                let bit = 1usize << vertex;
                if mask & bit == 0 && i16::from(increments[mask]) == expected {
                    next[mask | bit] += count;
                }
            }
        }
        current = next;
    }
    current[full]
}

fn hinge_from_table(record: &Record, table: &[Vec<i8>], direction: &[i8; N]) -> i64 {
    let mut unlabelled = 0u64;
    for scale in -5i8..=5 {
        if scale == 0 {
            continue;
        }
        unlabelled += u64::from(scale.unsigned_abs())
            * matching_injections(table, record.active_vertices, direction, scale);
    }
    let labelled = unlabelled
        .checked_mul(factorial(N - record.active_vertices))
        .expect("hinge coefficient overflow");
    i64::try_from(labelled).expect("hinge coefficient exceeds i64")
}

pub fn hinge_coefficients(record: &Record, directions: &[[i8; N]]) -> Result<Vec<i64>> {
    for direction in directions {
        validate_direction(direction)?;
    }
    hinge_coefficients_prevalidated(record, directions)
}

/// Prices directions already validated by a custody gate at batch ingress.
///
/// This skips only repeated direction validation; record validation and the
/// exact pricing computation are identical to [`hinge_coefficients`].
pub fn hinge_coefficients_prevalidated(
    record: &Record,
    directions: &[[i8; N]],
) -> Result<Vec<i64>> {
    let table = increment_table(record)?;
    Ok(directions
        .iter()
        .map(|direction| hinge_from_table(record, &table, direction))
        .collect())
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

pub fn base_linear(record: &Record) -> Result<[i64; N]> {
    validate_record(record)?;
    let negative_loops = record.negative_loop_count;
    let nonloop_carriers = DEGREE - negative_loops;
    Ok(std::array::from_fn(|rank| {
        negative_loops as i64 * factorial(N - 1) as i64
            + nonloop_carriers as i64 * 2 * rank as i64 * factorial(N - 2) as i64
    }))
}

pub fn linear_vector(record: &Record) -> Result<[i64; N]> {
    let table = increment_table(record)?;
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
                for (vertex, increments) in table.iter().enumerate().take(active) {
                    let bit = 1usize << vertex;
                    if mask & bit != 0 {
                        continue;
                    }
                    let increment = increments[mask];
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
    let base = base_linear(record)?;
    Ok(std::array::from_fn(|rank| {
        i64::try_from(i128::from(base[rank]) + correction[rank] * inactive_multiplier)
            .expect("linear coordinate exceeds i64")
    }))
}

#[derive(Default)]
struct FullAccumulator {
    inactive_multiplicity: u64,
    labelled_permutations: u64,
    zero_word_permutations: u64,
    negative_word_permutations: u64,
    inactive_oriented_permutations: u64,
    correction: [i64; N],
    hinges: BTreeMap<[i8; N], i64>,
}

impl FullAccumulator {
    fn observe(&mut self, word: &[i8; N]) {
        let multiplicity = self.inactive_multiplicity;
        self.labelled_permutations += multiplicity;
        let Some(first) = word.iter().copied().find(|value| *value != 0) else {
            self.zero_word_permutations += multiplicity;
            return;
        };
        if first < 0 {
            self.negative_word_permutations += multiplicity;
            for (target, &value) in self.correction.iter_mut().zip(word) {
                *target += i64::from(value) * multiplicity as i64;
            }
        }
        let divisor = word
            .iter()
            .fold(0i64, |current, value| gcd(current, i64::from(*value)));
        let sign = if first > 0 { 1i64 } else { -1i64 };
        let mut direction = [0i8; N];
        for (target, &value) in direction.iter_mut().zip(word) {
            *target = (sign * i64::from(value) / divisor) as i8;
        }
        if active_direction(&direction) {
            *self.hinges.entry(direction).or_default() += divisor * multiplicity as i64;
        } else {
            self.inactive_oriented_permutations += multiplicity;
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn enumerate_words(
    rank: usize,
    active: usize,
    used: usize,
    inactive_used: usize,
    table: &[Vec<i8>],
    word: &mut [i8; N],
    accumulator: &mut FullAccumulator,
) {
    if rank == N {
        accumulator.observe(word);
        return;
    }
    if inactive_used < N - active {
        word[rank] = 0;
        enumerate_words(
            rank + 1,
            active,
            used,
            inactive_used + 1,
            table,
            word,
            accumulator,
        );
    }
    for vertex in 0..active {
        let bit = 1usize << vertex;
        if used & bit == 0 {
            word[rank] = table[vertex][used];
            enumerate_words(
                rank + 1,
                active,
                used | bit,
                inactive_used,
                table,
                word,
                accumulator,
            );
        }
    }
}

pub fn full_normal_form(record: &Record) -> Result<NormalForm> {
    let table = increment_table(record)?;
    let mut accumulator = FullAccumulator {
        inactive_multiplicity: factorial(N - record.active_vertices),
        ..FullAccumulator::default()
    };
    enumerate_words(
        0,
        record.active_vertices,
        0,
        0,
        &table,
        &mut [0i8; N],
        &mut accumulator,
    );
    ensure!(
        accumulator.labelled_permutations == factorial(N),
        "full permutation census mismatch"
    );
    let base = base_linear(record)?;
    let linear = std::array::from_fn(|rank| base[rank] + accumulator.correction[rank]);
    let hinges = accumulator
        .hinges
        .into_iter()
        .map(|(direction, coefficient)| HingeTerm {
            direction,
            coefficient,
        })
        .collect::<Vec<_>>();
    Ok(NormalForm {
        sequence: record.sequence,
        active_vertices: record.active_vertices,
        diagonal_multiplier: 1,
        labelled_permutation_count: accumulator.labelled_permutations,
        zero_word_permutation_count: accumulator.zero_word_permutations,
        negative_word_permutation_count: accumulator.negative_word_permutations,
        inactive_oriented_permutation_count: accumulator.inactive_oriented_permutations,
        hinge_direction_count: hinges.len(),
        base_linear: base,
        orientation_correction: accumulator.correction,
        linear,
        hinges,
    })
}

type EdgeMap = BTreeMap<(usize, usize), i8>;

fn signed_structure(record: &Record) -> Result<(EdgeMap, Vec<i8>)> {
    validate_record(record)?;
    let mut edges = EdgeMap::new();
    let mut loops = vec![0i8; record.active_vertices];
    for (sign, side) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        for &[u, v] in side {
            if u == v {
                loops[u] += sign;
            } else {
                *edges.entry((u, v)).or_default() += sign;
            }
        }
    }
    edges.retain(|_, weight| *weight != 0);
    ensure!(
        edges
            .values()
            .chain(loops.iter())
            .all(|weight| (-5..=5).contains(weight)),
        "signed weight overflow"
    );
    Ok((edges, loops))
}

#[derive(Clone)]
struct Dsu {
    parent: Vec<usize>,
    rank: Vec<u8>,
}

impl Dsu {
    fn new(n: usize) -> Self {
        Self {
            parent: (0..n).collect(),
            rank: vec![0; n],
        }
    }
    fn find(&mut self, value: usize) -> usize {
        if self.parent[value] != value {
            self.parent[value] = self.find(self.parent[value]);
        }
        self.parent[value]
    }
    fn union(&mut self, first: usize, second: usize) -> bool {
        let mut a = self.find(first);
        let mut b = self.find(second);
        if a == b {
            return false;
        }
        if self.rank[a] < self.rank[b] {
            std::mem::swap(&mut a, &mut b);
        }
        self.parent[b] = a;
        if self.rank[a] == self.rank[b] {
            self.rank[a] += 1;
        }
        true
    }
}

fn remaining_forest(active: usize, edges: &EdgeMap, removed: usize) -> bool {
    let mut dsu = Dsu::new(active);
    for &(u, v) in edges.keys() {
        if removed & (1 << u) != 0 || removed & (1 << v) != 0 {
            continue;
        }
        if !dsu.union(u, v) {
            return false;
        }
    }
    true
}

fn feedback_vertices(active: usize, edges: &EdgeMap) -> Vec<usize> {
    for size in 0..=active {
        for removed in 0usize..(1usize << active) {
            if removed.count_ones() as usize == size && remaining_forest(active, edges, removed) {
                return (0..active)
                    .filter(|vertex| removed & (1 << vertex) != 0)
                    .collect();
            }
        }
    }
    unreachable!("removing every vertex leaves a forest")
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct State {
    counts: [u8; COLORS],
    q: [i8; COLORS - 1],
}

impl State {
    fn packed(self) -> u32 {
        let mut output = 0u32;
        for (index, count) in self.counts.into_iter().enumerate() {
            output |= u32::from(count) << (4 * index);
        }
        for (index, value) in self.q.into_iter().enumerate() {
            debug_assert!((-16..16).contains(&value));
            output |= u32::from((value + 16) as u8) << (16 + 5 * index);
        }
        output
    }
}

impl Hash for State {
    fn hash<H: Hasher>(&self, state: &mut H) {
        state.write_u32(self.packed());
    }
}

#[derive(Default)]
struct FastHasher(u64);

impl Hasher for FastHasher {
    fn write(&mut self, bytes: &[u8]) {
        let mut hash = if self.0 == 0 {
            0xcbf2_9ce4_8422_2325
        } else {
            self.0
        };
        for byte in bytes {
            hash ^= u64::from(*byte);
            hash = hash.wrapping_mul(0x0000_0100_0000_01b3);
        }
        self.0 = hash;
    }
    fn finish(&self) -> u64 {
        self.0
    }
    fn write_u32(&mut self, value: u32) {
        self.0 = u64::from(value).wrapping_mul(0x9e37_79b9_7f4a_7c15);
    }
}

type Polynomial = HashMap<State, u64, BuildHasherDefault<FastHasher>>;

fn singleton(state: State, count: u64) -> Polynomial {
    let mut output = Polynomial::default();
    output.insert(state, count);
    output
}

fn add_color_q(q: &mut [i8; COLORS - 1], color: usize, weight: i8) {
    if color > 0 {
        q[color - 1] += weight;
        debug_assert!((-5..=5).contains(&q[color - 1]));
    }
}

fn add_edge_q(q: &mut [i8; COLORS - 1], first: usize, second: usize, weight: i8) {
    add_color_q(q, first.max(second), weight);
}

fn merge_states(first: State, second: State, edge: Option<(usize, usize, i8)>) -> State {
    let counts = std::array::from_fn(|index| first.counts[index] + second.counts[index]);
    let mut q = std::array::from_fn(|index| first.q[index] + second.q[index]);
    if let Some((one, two, weight)) = edge {
        add_edge_q(&mut q, one, two, weight);
    }
    State { counts, q }
}

fn convolve(left: &Polynomial, right: &Polynomial, edge: Option<(usize, usize, i8)>) -> Polynomial {
    let mut output = Polynomial::default();
    for (&left_state, &left_count) in left {
        for (&right_state, &right_count) in right {
            let state = merge_states(left_state, right_state, edge);
            *output.entry(state).or_default() += left_count * right_count;
        }
    }
    output
}

fn tree_tables(
    vertex: usize,
    parent: usize,
    adjacency: &[Vec<(usize, i8)>],
    fixed_neighbours: &[Vec<(usize, i8)>],
    fixed_colors: &[usize],
    loop_weights: &[i8],
) -> [Polynomial; COLORS] {
    let mut tables: [Polynomial; COLORS] = std::array::from_fn(|color| {
        let mut counts = [0u8; COLORS];
        counts[color] = 1;
        let mut q = [0i8; COLORS - 1];
        add_color_q(&mut q, color, loop_weights[vertex]);
        for &(fixed_index, weight) in &fixed_neighbours[vertex] {
            add_edge_q(&mut q, color, fixed_colors[fixed_index], weight);
        }
        singleton(State { counts, q }, 1)
    });
    for &(child, weight) in &adjacency[vertex] {
        if child == parent {
            continue;
        }
        let child_tables = tree_tables(
            child,
            vertex,
            adjacency,
            fixed_neighbours,
            fixed_colors,
            loop_weights,
        );
        let mut next: [Polynomial; COLORS] = std::array::from_fn(|_| Polynomial::default());
        for parent_color in 0..COLORS {
            for (child_color, child_table) in child_tables.iter().enumerate() {
                let attached = convolve(
                    &tables[parent_color],
                    child_table,
                    Some((parent_color, child_color, weight)),
                );
                for (state, count) in attached {
                    *next[parent_color].entry(state).or_default() += count;
                }
            }
        }
        tables = next;
    }
    tables
}

fn cycle_cut_histogram(record: &Record) -> Result<(Polynomial, usize)> {
    let (edges, loops) = signed_structure(record)?;
    let active = record.active_vertices;
    if active == 0 {
        return Ok((
            singleton(
                State {
                    counts: [0; COLORS],
                    q: [0; COLORS - 1],
                },
                1,
            ),
            0,
        ));
    }
    // Loops are unary colour terms and never enter this feedback graph.
    let feedback = feedback_vertices(active, &edges);
    let mut fixed_lookup = vec![None; active];
    for (index, &vertex) in feedback.iter().enumerate() {
        fixed_lookup[vertex] = Some(index);
    }
    let mut adjacency = vec![Vec::<(usize, i8)>::new(); active];
    let mut fixed_neighbours = vec![Vec::<(usize, i8)>::new(); active];
    let mut fixed_edges = Vec::<(usize, usize, i8)>::new();
    let mut forest_check = Dsu::new(active);
    for (&(u, v), &weight) in &edges {
        match (fixed_lookup[u], fixed_lookup[v]) {
            (Some(one), Some(two)) => fixed_edges.push((one, two, weight)),
            (Some(fixed), None) => fixed_neighbours[v].push((fixed, weight)),
            (None, Some(fixed)) => fixed_neighbours[u].push((fixed, weight)),
            (None, None) => {
                ensure!(forest_check.union(u, v), "feedback deletion left a cycle");
                adjacency[u].push((v, weight));
                adjacency[v].push((u, weight));
            }
        }
    }
    let fixed_assignments = COLORS.pow(feedback.len() as u32);
    let partials = (0..fixed_assignments)
        .into_par_iter()
        .map(|mut code| {
            let mut fixed_colors = vec![0usize; feedback.len()];
            let mut base = State {
                counts: [0; COLORS],
                q: [0; COLORS - 1],
            };
            for (index, color) in fixed_colors.iter_mut().enumerate() {
                *color = code & (COLORS - 1);
                code >>= 2;
                base.counts[*color] += 1;
                add_color_q(&mut base.q, *color, loops[feedback[index]]);
            }
            for &(first, second, weight) in &fixed_edges {
                add_edge_q(
                    &mut base.q,
                    fixed_colors[first],
                    fixed_colors[second],
                    weight,
                );
            }
            let mut global = singleton(base, 1);
            let mut seen = vec![false; active];
            for &vertex in &feedback {
                seen[vertex] = true;
            }
            for root in 0..active {
                if seen[root] {
                    continue;
                }
                let mut stack = vec![root];
                seen[root] = true;
                while let Some(vertex) = stack.pop() {
                    for &(other, _) in &adjacency[vertex] {
                        if !seen[other] {
                            seen[other] = true;
                            stack.push(other);
                        }
                    }
                }
                let tables = tree_tables(
                    root,
                    active,
                    &adjacency,
                    &fixed_neighbours,
                    &fixed_colors,
                    &loops,
                );
                let mut component = Polynomial::default();
                for table in tables {
                    for (state, count) in table {
                        *component.entry(state).or_default() += count;
                    }
                }
                global = convolve(&global, &component, None);
            }
            global
        })
        .collect::<Vec<_>>();
    let mut total = Polynomial::default();
    for partial in partials {
        for (state, count) in partial {
            *total.entry(state).or_default() += count;
        }
    }
    ensure!(
        total.values().sum::<u64>() == COLORS.pow(active as u32) as u64,
        "cycle-cut colouring census failed"
    );
    Ok((total, feedback.len()))
}

fn ordered_loop_sum(row: &Row) -> i128 {
    let mut total = 0i128;
    for color in 0..COLORS {
        if row.profile[color] == 0 {
            continue;
        }
        let mut remainder = row.profile;
        remainder[color] -= 1;
        let multiplicity = factorial(N - 1)
            / remainder
                .iter()
                .map(|count| factorial(*count as usize))
                .product::<u64>();
        total += i128::from(row.levels[color]) * i128::from(multiplicity);
    }
    total
}

fn ordered_pair_max_sum(row: &Row) -> i128 {
    let mut total = 0i128;
    for first in 0..COLORS {
        for second in 0..COLORS {
            if row.profile[first] == 0
                || row.profile[second] == 0
                || (first == second && row.profile[first] < 2)
            {
                continue;
            }
            let mut remainder = row.profile;
            remainder[first] -= 1;
            remainder[second] -= 1;
            let multiplicity = factorial(N - 2)
                / remainder
                    .iter()
                    .map(|count| factorial(*count as usize))
                    .product::<u64>();
            total +=
                i128::from(multiplicity) * i128::from(row.levels[first].max(row.levels[second]));
        }
    }
    total
}

fn validate_row(row: &Row) -> Result<()> {
    ensure!(row.levels[0] == 0, "row minimum level must be zero");
    ensure!(
        row.levels.windows(2).all(|pair| pair[0] < pair[1]),
        "levels not increasing"
    );
    ensure!(
        row.profile
            .iter()
            .map(|value| *value as usize)
            .sum::<usize>()
            == N,
        "profile sum drift"
    );
    ensure!(
        row.formal_stabilizer
            == row
                .profile
                .iter()
                .map(|count| factorial(*count as usize))
                .product::<u64>(),
        "formal stabilizer drift"
    );
    Ok(())
}

fn panel_from_histogram(
    record: &Record,
    histogram: &Polynomial,
    rows: &[Row],
) -> Result<Vec<i128>> {
    let inactive = N - record.active_vertices;
    let mut values = Vec::with_capacity(rows.len());
    for row in rows {
        validate_row(row)?;
        let mut nonlinear = 0i128;
        let mut represented = 0u64;
        for (state, count) in histogram {
            let mut remainder = [0u8; COLORS];
            let mut compatible = true;
            for (color, target) in remainder.iter_mut().enumerate() {
                if state.counts[color] > row.profile[color] {
                    compatible = false;
                    break;
                }
                *target = row.profile[color] - state.counts[color];
            }
            if !compatible
                || remainder.iter().map(|value| *value as usize).sum::<usize>() != inactive
            {
                continue;
            }
            let multiplicity = factorial(inactive)
                / remainder
                    .iter()
                    .map(|value| factorial(*value as usize))
                    .product::<u64>();
            represented += count * multiplicity;
            let delta = state
                .q
                .iter()
                .enumerate()
                .map(|(index, q)| i128::from(*q) * i128::from(row.levels[index + 1]))
                .sum::<i128>();
            if delta > 0 {
                nonlinear += i128::from(*count) * i128::from(multiplicity) * delta;
            }
        }
        let expected = factorial(N) / row.formal_stabilizer;
        ensure!(represented == expected, "formal assignment census mismatch");
        let base = i128::try_from(record.negative_loop_count)? * ordered_loop_sum(row)
            + i128::try_from(DEGREE - record.negative_loop_count)? * ordered_pair_max_sum(row);
        values.push(base + nonlinear);
    }
    Ok(values)
}

pub fn panel_vector(record: &Record, rows: &[Row]) -> Result<Vec<i128>> {
    let (histogram, _feedback_vertices) = cycle_cut_histogram(record)?;
    panel_from_histogram(record, &histogram, rows)
}

pub fn literal_panel_value(record: &Record, row: &Row) -> Result<i128> {
    validate_record(record)?;
    validate_row(row)?;
    let active = record.active_vertices;
    let inactive = N - active;
    let assignments = COLORS.pow(active as u32);
    let mut total = 0i128;
    let mut colors = vec![0usize; active];
    for mut code in 0..assignments {
        let mut counts = [0u8; COLORS];
        for color in &mut colors {
            *color = code & (COLORS - 1);
            code >>= 2;
            counts[*color] += 1;
        }
        let mut remainder = [0u8; COLORS];
        if (0..COLORS).any(|color| counts[color] > row.profile[color]) {
            continue;
        }
        for (color, target) in remainder.iter_mut().enumerate() {
            *target = row.profile[color] - counts[color];
        }
        if remainder.iter().map(|value| *value as usize).sum::<usize>() != inactive {
            continue;
        }
        let multiplicity = factorial(inactive)
            / remainder
                .iter()
                .map(|value| factorial(*value as usize))
                .product::<u64>();
        let branch = |edges: &[[usize; 2]]| -> i128 {
            edges
                .iter()
                .map(|&[u, v]| i128::from(row.levels[colors[u]].max(row.levels[colors[v]])))
                .sum()
        };
        let signed_negative = branch(&record.negative_edges);
        let signed_positive = branch(&record.positive_edges);
        let signed_value = signed_negative.max(signed_positive);
        total += i128::from(multiplicity) * signed_value;
        if active == 0 {
            debug_assert_eq!(signed_value, 0);
        }
    }
    // Direct signed branches above omit degree-five padding.  Padding is a
    // common nonloop carrier, except that each negative signed loop replaces
    // one such carrier by L in G-0109's canonical base convention.
    total += i128::try_from(DEGREE - record.signed_mass)? * ordered_pair_max_sum(row);
    Ok(total)
}

pub fn pure_loop_carrier(rows: &[Row]) -> Result<(Vec<i128>, [i64; N])> {
    for row in rows {
        validate_row(row)?;
    }
    Ok((
        rows.iter().map(ordered_loop_sum).collect(),
        [factorial(N - 1) as i64; N],
    ))
}

pub fn pure_nonloop_carrier(rows: &[Row]) -> Result<(Vec<i128>, [i64; N])> {
    for row in rows {
        validate_row(row)?;
    }
    Ok((
        rows.iter().map(ordered_pair_max_sum).collect(),
        std::array::from_fn(|rank| 2 * rank as i64 * factorial(N - 2) as i64),
    ))
}

pub fn price_column(record: &Record, rows: &[Row], directions: &[[i8; N]]) -> Result<PricedColumn> {
    Ok(PricedColumn {
        panel: panel_vector(record, rows)?,
        linear: linear_vector(record)?,
        hinges: hinge_coefficients(record, directions)?,
    })
}

pub fn branch_swap(record: &Record) -> Record {
    Record {
        sequence: record.sequence,
        signed_mass: record.signed_mass,
        active_vertices: record.active_vertices,
        negative_loop_count: record.positive_loop_count,
        positive_loop_count: record.negative_loop_count,
        negative_edges: record.positive_edges.clone(),
        positive_edges: record.negative_edges.clone(),
    }
}

pub fn directions_unique(directions: &[[i8; N]]) -> bool {
    directions.iter().copied().collect::<BTreeSet<_>>().len() == directions.len()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn loop_sample() -> Record {
        Record {
            sequence: 0,
            signed_mass: 3,
            active_vertices: 5,
            negative_loop_count: 1,
            positive_loop_count: 0,
            negative_edges: vec![[0, 0], [0, 1], [2, 3]],
            positive_edges: vec![[0, 2], [1, 4], [3, 4]],
        }
    }

    fn rows() -> Vec<Row> {
        vec![
            Row {
                levels: [0, 2, 5, 9],
                profile: [1, 2, 3, 5],
                formal_stabilizer: 1_440,
            },
            Row {
                levels: [0, 1, 4, 11],
                profile: [2, 1, 2, 6],
                formal_stabilizer: 2_880,
            },
            Row {
                levels: [0, 3, 7, 8],
                profile: [3, 2, 1, 5],
                formal_stabilizer: 1_440,
            },
        ]
    }

    #[test]
    fn loop_dp_matches_complete_normal_form_and_branch_swap() {
        let record = loop_sample();
        let swapped = branch_swap(&record);
        let first = full_normal_form(&record).unwrap();
        let second = full_normal_form(&swapped).unwrap();
        assert_eq!(first.labelled_permutation_count, factorial(N));
        assert_eq!(first.linear, linear_vector(&record).unwrap());
        assert_eq!(first.linear, second.linear);
        let first_hinges = first
            .hinges
            .iter()
            .map(|term| (term.direction, term.coefficient))
            .collect::<BTreeMap<_, _>>();
        let second_hinges = second
            .hinges
            .iter()
            .map(|term| (term.direction, term.coefficient))
            .collect::<BTreeMap<_, _>>();
        assert_eq!(first_hinges, second_hinges);
        let directions = first_hinges.keys().take(12).copied().collect::<Vec<_>>();
        let priced = hinge_coefficients(&record, &directions).unwrap();
        for (direction, coefficient) in directions.iter().zip(priced) {
            assert_eq!(coefficient, first_hinges[direction]);
        }
    }

    #[test]
    fn loop_cycle_cut_matches_literal_rows_and_branch_swap() {
        let record = loop_sample();
        let swapped = branch_swap(&record);
        let production = panel_vector(&record, &rows()).unwrap();
        let swapped_production = panel_vector(&swapped, &rows()).unwrap();
        let literal = rows()
            .iter()
            .map(|row| literal_panel_value(&record, row).unwrap())
            .collect::<Vec<_>>();
        assert_eq!(production, literal);
        assert_eq!(production, swapped_production);
    }

    #[test]
    fn loops_are_not_feedback_edges() {
        let pure = Record {
            sequence: 0,
            signed_mass: 1,
            active_vertices: 2,
            negative_loop_count: 1,
            positive_loop_count: 1,
            negative_edges: vec![[0, 0]],
            positive_edges: vec![[1, 1]],
        };
        let (_histogram, feedback) = cycle_cut_histogram(&pure).unwrap();
        assert_eq!(feedback, 0);
        assert_eq!(panel_vector(&pure, &rows()).unwrap().len(), rows().len());
    }

    #[test]
    fn pure_loop_carrier_has_constant_linear_and_zero_hinge_by_definition() {
        let (panel, linear) = pure_loop_carrier(&rows()).unwrap();
        assert_eq!(panel.len(), rows().len());
        assert_eq!(linear, [factorial(10) as i64; N]);
        for (value, row) in panel.iter().zip(rows()) {
            let assignments = factorial(N) / row.formal_stabilizer;
            let weighted_sum = row
                .profile
                .iter()
                .zip(row.levels)
                .map(|(&count, level)| i128::from(count) * i128::from(level))
                .sum::<i128>();
            assert_eq!(*value, i128::from(assignments) * weighted_sum / N as i128);
        }
    }

    #[test]
    fn directions_above_signed_mass_have_zero_hinge_coefficient() {
        let record = loop_sample();
        let mass_four = [1, -4, 3, 0, 0, 0, 0, 0, 0, 0, 0];
        let mass_five = [1, -5, 4, 0, 0, 0, 0, 0, 0, 0, 0];
        assert_eq!(positive_mass(&mass_four), 4);
        assert_eq!(positive_mass(&mass_five), 5);
        let directions = [mass_four, mass_five];
        let validated = hinge_coefficients(&record, &directions).unwrap();
        assert_eq!(validated, [0, 0]);
        assert_eq!(
            hinge_coefficients_prevalidated(&record, &directions).unwrap(),
            validated
        );
    }

    #[test]
    fn pure_nonloop_carrier_has_expected_linear_vector() {
        let (panel, linear) = pure_nonloop_carrier(&rows()).unwrap();
        assert_eq!(panel.len(), rows().len());
        assert_eq!(
            linear,
            std::array::from_fn(|rank| 2 * rank as i64 * factorial(N - 2) as i64)
        );
    }
}
