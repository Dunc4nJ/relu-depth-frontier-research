use anyhow::{Context, Result, ensure};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::{File, OpenOptions};
use std::hash::{BuildHasherDefault, Hash, Hasher};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const N: usize = 11;
const COLORS: usize = 4;
const DEGREE: i128 = 5;

#[derive(Clone, Debug, Deserialize)]
struct Input {
    schema: String,
    rows_path: String,
    control_sequences: Vec<usize>,
    records: Vec<Record>,
}

#[derive(Clone, Debug, Deserialize)]
struct Record {
    sequence: usize,
    signed_mass: usize,
    active_vertices: usize,
    negative_edges: Vec<[usize; 2]>,
    positive_edges: Vec<[usize; 2]>,
}

#[derive(Clone, Debug, Deserialize)]
struct RowsDocument {
    schema: String,
    rows: Vec<Row>,
}

#[derive(Clone, Debug, Deserialize)]
struct Row {
    levels: [i64; COLORS],
    profile: [u8; COLORS],
    formal_stabilizer: u64,
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
            debug_assert!(count <= 11);
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
type EdgeMap = BTreeMap<(usize, usize), i8>;

fn singleton(state: State, count: u64) -> Polynomial {
    let mut output = Polynomial::default();
    output.insert(state, count);
    output
}

#[derive(Clone, Debug, Serialize)]
struct ControlReport {
    sequence: usize,
    signed_mass: usize,
    active_vertices: usize,
    abs_beta: usize,
    feedback_vertices: usize,
    cycle_cut_states: usize,
    exhaustive_states: usize,
    cycle_cut_seconds: f64,
    exhaustive_seconds: f64,
    speedup: f64,
    panel_vector_sha256: String,
}

#[derive(Debug, Serialize)]
struct Output {
    schema: &'static str,
    result: &'static str,
    claim_boundary: &'static str,
    bindings: BTreeMap<String, String>,
    controls: Vec<ControlReport>,
    median_cyclic_active10_11_speedup: f64,
    all_histograms_exact: bool,
    all_panel_vectors_exact: bool,
    all_formal_assignment_censuses_exact: bool,
    branch_swap_preserved: bool,
    edge_sign_mutant_rejected: bool,
    wall_seconds: f64,
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

fn factorial(n: usize) -> u64 {
    (1..=n as u64).product()
}

fn sha256_path(path: &Path) -> Result<String> {
    let mut digest = Sha256::new();
    let mut input = File::open(path)?;
    let mut buffer = [0u8; 1 << 16];
    loop {
        let read = input.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn sha256_vector(values: &[i128]) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

fn signed_edges(record: &Record, negate: bool) -> Result<EdgeMap> {
    ensure!(record.active_vertices <= N, "active support exceeds N");
    let mut edges = BTreeMap::<(usize, usize), i8>::new();
    for (base_sign, side) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        let sign = if negate { -base_sign } else { base_sign };
        for &[u, v] in side {
            ensure!(u < v, "G-0113 input must be compact, loopless, canonical");
            ensure!(v < record.active_vertices, "edge outside active support");
            *edges.entry((u, v)).or_default() += sign;
        }
    }
    edges.retain(|_, weight| *weight != 0);
    ensure!(
        edges.values().all(|weight| (-5..=5).contains(weight)),
        "weight overflow"
    );
    Ok(edges)
}

fn graph_beta(active: usize, edges: &EdgeMap) -> usize {
    if active == 0 {
        return 0;
    }
    let mut dsu = Dsu::new(active);
    for &(u, v) in edges.keys() {
        dsu.union(u, v);
    }
    let components = (0..active)
        .map(|vertex| dsu.find(vertex))
        .collect::<BTreeSet<_>>()
        .len();
    edges.len() + components - active
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
    let maximum = graph_beta(active, edges).min(4);
    for size in 0..=maximum {
        for removed in 0usize..(1usize << active) {
            if removed.count_ones() as usize != size || !remaining_forest(active, edges, removed) {
                continue;
            }
            return (0..active)
                .filter(|vertex| removed & (1 << vertex) != 0)
                .collect();
        }
    }
    panic!("cycle-rank bound did not yield a feedback set")
}

fn add_edge_q(q: &mut [i8; COLORS - 1], first: usize, second: usize, weight: i8) {
    let color = first.max(second);
    if color > 0 {
        q[color - 1] += weight;
        debug_assert!((-5..=5).contains(&q[color - 1]));
    }
}

fn merge_states(first: State, second: State, edge: Option<(usize, usize, i8)>) -> State {
    let mut counts = [0u8; COLORS];
    for color in 0..COLORS {
        counts[color] = first.counts[color] + second.counts[color];
    }
    let mut q = [0i8; COLORS - 1];
    for index in 0..COLORS - 1 {
        q[index] = first.q[index] + second.q[index];
    }
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
) -> [Polynomial; COLORS] {
    let mut tables: [Polynomial; COLORS] = std::array::from_fn(|color| {
        let mut counts = [0u8; COLORS];
        counts[color] = 1;
        let mut q = [0i8; COLORS - 1];
        for &(fixed_index, weight) in &fixed_neighbours[vertex] {
            add_edge_q(&mut q, color, fixed_colors[fixed_index], weight);
        }
        singleton(State { counts, q }, 1)
    });
    for &(child, weight) in &adjacency[vertex] {
        if child == parent {
            continue;
        }
        let child_tables = tree_tables(child, vertex, adjacency, fixed_neighbours, fixed_colors);
        let mut next: [Polynomial; COLORS] = std::array::from_fn(|_| Polynomial::default());
        for parent_color in 0..COLORS {
            for child_color in 0..COLORS {
                let attached = convolve(
                    &tables[parent_color],
                    &child_tables[child_color],
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

fn cycle_cut_histogram(record: &Record, edges: &EdgeMap) -> Result<(Polynomial, usize)> {
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
    let feedback = feedback_vertices(active, edges);
    ensure!(feedback.len() <= 4, "G-0113 cycle-rank gate exceeded");
    let mut fixed_lookup = vec![None; active];
    for (index, &vertex) in feedback.iter().enumerate() {
        fixed_lookup[vertex] = Some(index);
    }
    let mut adjacency = vec![Vec::<(usize, i8)>::new(); active];
    let mut fixed_neighbours = vec![Vec::<(usize, i8)>::new(); active];
    let mut fixed_edges = Vec::<(usize, usize, i8)>::new();
    let mut forest_check = Dsu::new(active);
    for (&(u, v), &weight) in edges {
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
            for color in &mut fixed_colors {
                *color = code & (COLORS - 1);
                code >>= 2;
                base.counts[*color] += 1;
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
                let tables =
                    tree_tables(root, active, &adjacency, &fixed_neighbours, &fixed_colors);
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

fn exhaustive_histogram(record: &Record, edges: &EdgeMap) -> Polynomial {
    let active = record.active_vertices;
    let assignments = COLORS.pow(active as u32);
    let mut output = Polynomial::default();
    let mut colors = vec![0usize; active];
    for mut code in 0..assignments {
        let mut state = State {
            counts: [0; COLORS],
            q: [0; COLORS - 1],
        };
        for color in &mut colors {
            *color = code & (COLORS - 1);
            code >>= 2;
            state.counts[*color] += 1;
        }
        for (&(u, v), &weight) in edges {
            add_edge_q(&mut state.q, colors[u], colors[v], weight);
        }
        *output.entry(state).or_default() += 1;
    }
    output
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
            total += multiplicity as i128 * row.levels[first].max(row.levels[second]) as i128;
        }
    }
    total
}

fn panel_vector(histogram: &Polynomial, active: usize, rows: &[Row]) -> Result<Vec<i128>> {
    let inactive = N - active;
    let mut values = Vec::with_capacity(rows.len());
    for row in rows {
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
        let mut nonlinear = 0i128;
        let mut represented = 0u64;
        for (state, count) in histogram {
            let mut remainder = [0u8; COLORS];
            let mut compatible = true;
            for color in 0..COLORS {
                if state.counts[color] > row.profile[color] {
                    compatible = false;
                    break;
                }
                remainder[color] = row.profile[color] - state.counts[color];
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
                .map(|(index, q)| *q as i128 * row.levels[index + 1] as i128)
                .sum::<i128>();
            if delta > 0 {
                nonlinear += *count as i128 * multiplicity as i128 * delta;
            }
        }
        let expected = factorial(N)
            / row
                .profile
                .iter()
                .map(|count| factorial(*count as usize))
                .product::<u64>();
        ensure!(represented == expected, "formal assignment census mismatch");
        values.push(DEGREE * ordered_pair_max_sum(row) + nonlinear);
    }
    Ok(values)
}

fn select_controls(input: &Input) -> Result<Vec<usize>> {
    let mut selected = input
        .control_sequences
        .iter()
        .copied()
        .collect::<BTreeSet<_>>();
    for active in [10usize, 11usize] {
        let sequence = input.records.iter().find_map(|record| {
            let edges = signed_edges(record, false).ok()?;
            (record.active_vertices == active && graph_beta(active, &edges) > 0)
                .then_some(record.sequence)
        });
        selected.insert(sequence.with_context(|| format!("no cyclic active-{active} control"))?);
    }
    Ok(selected.into_iter().collect())
}

fn median(mut values: Vec<f64>) -> f64 {
    values.sort_by(f64::total_cmp);
    values[values.len() / 2]
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 4,
        "usage: g0116-cycle-cut-panel-benchmark INPUT.json ROWS.json OUTPUT.json"
    );
    let input_path = PathBuf::from(&args[1]);
    let rows_path = PathBuf::from(&args[2]);
    let output_path = PathBuf::from(&args[3]);
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let started = Instant::now();
    let input: Input = serde_json::from_reader(BufReader::new(File::open(&input_path)?))?;
    ensure!(
        input.schema == "max11-g0113-panel-solver-input-v1",
        "input schema drift"
    );
    ensure!(
        input.rows_path.ends_with("dual_rows_v1.json"),
        "bound row path drift"
    );
    let rows_document: RowsDocument =
        serde_json::from_reader(BufReader::new(File::open(&rows_path)?))?;
    ensure!(
        rows_document.schema == "max11-g0111-actual-dual-rows-v1",
        "row schema drift"
    );
    ensure!(rows_document.rows.len() == 301, "row count drift");
    ensure!(input.records.len() == 163_740, "record count drift");
    ensure!(
        input
            .records
            .iter()
            .enumerate()
            .all(|(index, record)| index == record.sequence),
        "sequence drift"
    );

    let mut controls = Vec::new();
    let mut branch_swap_preserved = true;
    let mut mutant_rejected = false;
    for sequence in select_controls(&input)? {
        let record = &input.records[sequence];
        let edges = signed_edges(record, false)?;
        let beta = graph_beta(record.active_vertices, &edges);
        let cycle_started = Instant::now();
        let (cycle, feedback) = cycle_cut_histogram(record, &edges)?;
        let cycle_seconds = cycle_started.elapsed().as_secs_f64();
        let exhaustive_started = Instant::now();
        let exhaustive = exhaustive_histogram(record, &edges);
        let exhaustive_seconds = exhaustive_started.elapsed().as_secs_f64();
        ensure!(
            cycle == exhaustive,
            "histogram disagreement at sequence {sequence}"
        );
        let vector = panel_vector(&cycle, record.active_vertices, &rows_document.rows)?;
        let exhaustive_vector =
            panel_vector(&exhaustive, record.active_vertices, &rows_document.rows)?;
        ensure!(
            vector == exhaustive_vector,
            "panel disagreement at sequence {sequence}"
        );

        let swapped_edges = signed_edges(record, true)?;
        let (swapped_histogram, _) = cycle_cut_histogram(record, &swapped_edges)?;
        let swapped_vector = panel_vector(
            &swapped_histogram,
            record.active_vertices,
            &rows_document.rows,
        )?;
        branch_swap_preserved &= vector == swapped_vector;

        if !mutant_rejected && !edges.is_empty() {
            let mut mutant = edges.clone();
            let first = *mutant.keys().next().unwrap();
            *mutant.get_mut(&first).unwrap() *= -1;
            let (mutant_histogram, _) = cycle_cut_histogram(record, &mutant)?;
            let mutant_vector = panel_vector(
                &mutant_histogram,
                record.active_vertices,
                &rows_document.rows,
            )?;
            mutant_rejected = mutant_vector != vector;
        }
        controls.push(ControlReport {
            sequence,
            signed_mass: record.signed_mass,
            active_vertices: record.active_vertices,
            abs_beta: beta,
            feedback_vertices: feedback,
            cycle_cut_states: cycle.len(),
            exhaustive_states: exhaustive.len(),
            cycle_cut_seconds: cycle_seconds,
            exhaustive_seconds,
            speedup: exhaustive_seconds / cycle_seconds.max(f64::MIN_POSITIVE),
            panel_vector_sha256: sha256_vector(&vector),
        });
    }
    ensure!(branch_swap_preserved, "branch swap changed panel semantics");
    ensure!(mutant_rejected, "edge-sign mutant escaped panel");
    let cyclic_speedups = controls
        .iter()
        .filter(|item| item.active_vertices >= 10 && item.abs_beta > 0)
        .map(|item| item.speedup)
        .collect::<Vec<_>>();
    ensure!(
        cyclic_speedups.len() >= 2,
        "missing high-active cyclic controls"
    );
    let speedup = median(cyclic_speedups);
    eprintln!(
        "G0116_CONTROL_TIMINGS {}",
        serde_json::to_string(&controls)?
    );
    ensure!(
        speedup >= 10.0,
        "cycle-cut evaluator failed 10x integration gate: {speedup:.3}"
    );

    let mut bindings = BTreeMap::new();
    bindings.insert("input".to_string(), sha256_path(&input_path)?);
    bindings.insert("rows".to_string(), sha256_path(&rows_path)?);
    bindings.insert(
        "producer".to_string(),
        sha256_path(Path::new(concat!(
            env!("CARGO_MANIFEST_DIR"),
            "/src/main.rs"
        )))?,
    );
    let output = Output {
        schema: "max11-g0116-cycle-cut-panel-benchmark-v1",
        result: "PASS_ACCELERATOR_GATE",
        claim_boundary: "Exact evaluator equivalence and performance on frozen controls only; no target membership, global identity, completeness theorem, or MAX11 result.",
        bindings,
        controls,
        median_cyclic_active10_11_speedup: speedup,
        all_histograms_exact: true,
        all_panel_vectors_exact: true,
        all_formal_assignment_censuses_exact: true,
        branch_swap_preserved,
        edge_sign_mutant_rejected: mutant_rejected,
        wall_seconds: started.elapsed().as_secs_f64(),
    };
    let destination = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&output_path)?;
    let mut writer = BufWriter::new(destination);
    serde_json::to_writer_pretty(&mut writer, &output)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    println!("{}", serde_json::to_string_pretty(&output)?);
    Ok(())
}
