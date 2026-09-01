use anyhow::{Context, Result, ensure};
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::fs::{File, OpenOptions};
use std::io::{BufReader, BufWriter, Write};
use std::mem::size_of;
use std::path::PathBuf;

const N: usize = 11;
const DEGREE: usize = 5;

#[derive(Debug, Clone, Deserialize)]
struct Record {
    sequence: usize,
    signed_mass: usize,
    active_vertices: usize,
    negative_edges: Vec<[usize; 2]>,
    positive_edges: Vec<[usize; 2]>,
    negative_loop_count: usize,
    positive_loop_count: usize,
}

#[derive(Deserialize)]
struct Input {
    schema: String,
    records: Vec<Record>,
}

#[derive(Serialize)]
struct HingeTerm {
    direction: [i8; N],
    coefficient: i64,
}

#[derive(Serialize)]
struct RawTerm {
    word: [i8; N],
    multiplicity: u64,
}

#[derive(Serialize)]
struct RawForm {
    sequence: usize,
    active_vertices: usize,
    diagonal_multiplier: i8,
    labelled_permutation_count: u64,
    base_linear: [i64; N],
    raw_terms: Vec<RawTerm>,
}

#[derive(Serialize)]
struct NormalForm {
    sequence: usize,
    active_vertices: usize,
    diagonal_multiplier: i8,
    labelled_permutation_count: u64,
    zero_word_permutation_count: u64,
    negative_word_permutation_count: u64,
    inactive_oriented_permutation_count: u64,
    hinge_direction_count: usize,
    base_linear: [i64; N],
    orientation_correction: [i64; N],
    linear: [i64; N],
    hinges: Vec<HingeTerm>,
}

#[repr(C)]
struct TrieNodeLayout {
    children: [i32; 11],
    depth: usize,
}

#[repr(C)]
struct TerminalMetaLayout {
    prefix_local: usize,
    weights: [u64; 4],
}

#[derive(Serialize)]
struct Layout {
    trie_node_bytes: usize,
    terminal_meta_bytes: usize,
    vec_header_bytes: usize,
    usize_bytes: usize,
}

#[derive(Serialize)]
struct Output {
    schema: &'static str,
    claim_boundary: &'static str,
    rust_layout: Layout,
    normal_forms: Vec<NormalForm>,
    double_diagonal_loop_mutant: Option<RawForm>,
}

fn factorial(value: usize) -> u64 {
    (1..=value as u64).product()
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

fn active_direction(direction: &[i8; N]) -> bool {
    let mut prefix = 0i64;
    for value in &direction[..N - 1] {
        prefix += *value as i64;
        if prefix < 0 {
            return true;
        }
    }
    false
}

struct Accumulator {
    inactive_multiplicity: u64,
    labelled_permutations: u64,
    zero_word_permutations: u64,
    negative_word_permutations: u64,
    inactive_oriented_permutations: u64,
    correction: [i64; N],
    hinges: BTreeMap<[i8; N], i64>,
}

impl Accumulator {
    fn observe(&mut self, word: &[i8; N]) {
        let multiplicity = self.inactive_multiplicity;
        self.labelled_permutations += multiplicity;
        let Some(first) = word.iter().copied().find(|value| *value != 0) else {
            self.zero_word_permutations += multiplicity;
            return;
        };
        if first < 0 {
            self.negative_word_permutations += multiplicity;
            for (rank, value) in word.iter().enumerate() {
                self.correction[rank] += *value as i64 * multiplicity as i64;
            }
        }
        let divisor = word
            .iter()
            .fold(0i64, |current, value| gcd(current, *value as i64));
        debug_assert!(divisor > 0);
        let sign = if first > 0 { 1i64 } else { -1i64 };
        let mut direction = [0i8; N];
        for rank in 0..N {
            direction[rank] = (sign * word[rank] as i64 / divisor) as i8;
        }
        debug_assert_eq!(direction.iter().map(|v| *v as i64).sum::<i64>(), 0);
        debug_assert_eq!(
            direction
                .iter()
                .fold(0i64, |current, value| gcd(current, *value as i64)),
            1
        );
        if active_direction(&direction) {
            *self.hinges.entry(direction).or_default() +=
                divisor * multiplicity as i64;
        } else {
            self.inactive_oriented_permutations += multiplicity;
        }
    }
}

#[allow(clippy::too_many_arguments)]
fn enumerate_rank_injections(
    rank: usize,
    active: usize,
    used: usize,
    inactive_used: usize,
    increments: &[Vec<i8>],
    word: &mut [i8; N],
    accumulator: &mut Accumulator,
) {
    if rank == N {
        debug_assert_eq!(used.count_ones() as usize, active);
        debug_assert_eq!(inactive_used, N - active);
        accumulator.observe(word);
        return;
    }

    if inactive_used < N - active {
        word[rank] = 0;
        enumerate_rank_injections(
            rank + 1,
            active,
            used,
            inactive_used + 1,
            increments,
            word,
            accumulator,
        );
    }
    for vertex in 0..active {
        let bit = 1usize << vertex;
        if used & bit == 0 {
            word[rank] = increments[vertex][used];
            enumerate_rank_injections(
                rank + 1,
                active,
                used | bit,
                inactive_used,
                increments,
                word,
                accumulator,
            );
        }
    }
}

fn normal_form(record: &Record, diagonal_multiplier: i8) -> Result<NormalForm> {
    ensure!(record.signed_mass <= DEGREE, "signed mass exceeds degree");
    ensure!(record.active_vertices <= N, "active support exceeds n");
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

    let active = record.active_vertices;
    let mut matrix = vec![vec![0i8; active]; active];
    for (sign, edges) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        for &[u, v] in edges {
            ensure!(u <= v && v < active, "edge outside active support");
            if u == v {
                matrix[u][u] += sign * diagonal_multiplier;
            } else {
                matrix[u][v] += sign;
                matrix[v][u] += sign;
            }
        }
    }

    let mut increments = vec![vec![0i8; 1usize << active]; active];
    for vertex in 0..active {
        increments[vertex][0] = matrix[vertex][vertex];
        for mask in 1usize..(1usize << active) {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            increments[vertex][mask] = increments[vertex][mask ^ bit] + matrix[vertex][other];
        }
    }

    let inactive_multiplicity = factorial(N - active);
    let mut accumulator = Accumulator {
        inactive_multiplicity,
        labelled_permutations: 0,
        zero_word_permutations: 0,
        negative_word_permutations: 0,
        inactive_oriented_permutations: 0,
        correction: [0; N],
        hinges: BTreeMap::new(),
    };
    enumerate_rank_injections(
        0,
        active,
        0,
        0,
        &increments,
        &mut [0i8; N],
        &mut accumulator,
    );
    ensure!(
        accumulator.labelled_permutations == factorial(N),
        "full permutation census mismatch"
    );

    let loop_count = record.negative_loop_count;
    let nonloop_count = DEGREE - loop_count;
    let mut base_linear = [0i64; N];
    let mut linear = [0i64; N];
    for rank in 0..N {
        base_linear[rank] = loop_count as i64 * factorial(N - 1) as i64
            + nonloop_count as i64 * 2 * rank as i64 * factorial(N - 2) as i64;
        linear[rank] = base_linear[rank] + accumulator.correction[rank];
    }

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
        active_vertices: active,
        diagonal_multiplier,
        labelled_permutation_count: accumulator.labelled_permutations,
        zero_word_permutation_count: accumulator.zero_word_permutations,
        negative_word_permutation_count: accumulator.negative_word_permutations,
        inactive_oriented_permutation_count: accumulator.inactive_oriented_permutations,
        hinge_direction_count: hinges.len(),
        base_linear,
        orientation_correction: accumulator.correction,
        linear,
        hinges,
    })
}

struct RawAccumulator {
    inactive_multiplicity: u64,
    labelled_permutations: u64,
    words: BTreeMap<[i8; N], u64>,
}

impl RawAccumulator {
    fn observe(&mut self, word: &[i8; N]) {
        self.labelled_permutations += self.inactive_multiplicity;
        *self.words.entry(*word).or_default() += self.inactive_multiplicity;
    }
}

#[allow(clippy::too_many_arguments)]
fn enumerate_rank_injections_raw(
    rank: usize,
    active: usize,
    used: usize,
    inactive_used: usize,
    increments: &[Vec<i8>],
    word: &mut [i8; N],
    accumulator: &mut RawAccumulator,
) {
    if rank == N {
        accumulator.observe(word);
        return;
    }
    if inactive_used < N - active {
        word[rank] = 0;
        enumerate_rank_injections_raw(
            rank + 1,
            active,
            used,
            inactive_used + 1,
            increments,
            word,
            accumulator,
        );
    }
    for vertex in 0..active {
        let bit = 1usize << vertex;
        if used & bit == 0 {
            word[rank] = increments[vertex][used];
            enumerate_rank_injections_raw(
                rank + 1,
                active,
                used | bit,
                inactive_used,
                increments,
                word,
                accumulator,
            );
        }
    }
}

fn raw_form(record: &Record, diagonal_multiplier: i8) -> Result<RawForm> {
    let active = record.active_vertices;
    let mut matrix = vec![vec![0i8; active]; active];
    for (sign, edges) in [
        (-1i8, &record.negative_edges),
        (1i8, &record.positive_edges),
    ] {
        for &[u, v] in edges {
            ensure!(u <= v && v < active, "edge outside active support");
            if u == v {
                matrix[u][u] += sign * diagonal_multiplier;
            } else {
                matrix[u][v] += sign;
                matrix[v][u] += sign;
            }
        }
    }
    let mut increments = vec![vec![0i8; 1usize << active]; active];
    for vertex in 0..active {
        increments[vertex][0] = matrix[vertex][vertex];
        for mask in 1usize..(1usize << active) {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            increments[vertex][mask] = increments[vertex][mask ^ bit] + matrix[vertex][other];
        }
    }
    let mut accumulator = RawAccumulator {
        inactive_multiplicity: factorial(N - active),
        labelled_permutations: 0,
        words: BTreeMap::new(),
    };
    enumerate_rank_injections_raw(
        0,
        active,
        0,
        0,
        &increments,
        &mut [0i8; N],
        &mut accumulator,
    );
    ensure!(
        accumulator.labelled_permutations == factorial(N),
        "mutant full permutation census mismatch"
    );
    let loop_count = record.negative_loop_count;
    let nonloop_count = DEGREE - loop_count;
    let mut base_linear = [0i64; N];
    for rank in 0..N {
        base_linear[rank] = loop_count as i64 * factorial(N - 1) as i64
            + nonloop_count as i64 * 2 * rank as i64 * factorial(N - 2) as i64;
    }
    Ok(RawForm {
        sequence: record.sequence,
        active_vertices: active,
        diagonal_multiplier,
        labelled_permutation_count: accumulator.labelled_permutations,
        base_linear,
        raw_terms: accumulator
            .words
            .into_iter()
            .map(|(word, multiplicity)| RawTerm { word, multiplicity })
            .collect(),
    })
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 3,
        "usage: g0109-normal-form-probe INPUT.json OUTPUT.json"
    );
    let input_path = PathBuf::from(&args[1]);
    let output_path = PathBuf::from(&args[2]);
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let input: Input = serde_json::from_reader(BufReader::new(
        File::open(&input_path).with_context(|| format!("open {}", input_path.display()))?,
    ))?;
    ensure!(input.schema == "max11-g0109-normal-form-input-v1", "input schema drift");
    ensure!(!input.records.is_empty(), "no records supplied");

    let normal_forms = input
        .records
        .iter()
        .map(|record| normal_form(record, 1))
        .collect::<Result<Vec<_>>>()?;
    let loop_record = input
        .records
        .iter()
        .find(|record| record.negative_loop_count + record.positive_loop_count > 0);
    let double_diagonal_loop_mutant = loop_record
        .map(|record| raw_form(record, 2))
        .transpose()?;

    let output = Output {
        schema: "max11-g0109-normal-form-probe-v1",
        claim_boundary: "Exact ordered-cone normal forms for the preregistered small record sample only; no complete stream pricing or MAX11 claim.",
        rust_layout: Layout {
            trie_node_bytes: size_of::<TrieNodeLayout>(),
            terminal_meta_bytes: size_of::<TerminalMetaLayout>(),
            vec_header_bytes: size_of::<Vec<usize>>(),
            usize_bytes: size_of::<usize>(),
        },
        normal_forms,
        double_diagonal_loop_mutant,
    };

    let handle = OpenOptions::new()
        .create_new(true)
        .write(true)
        .open(&output_path)
        .with_context(|| format!("create {}", output_path.display()))?;
    let mut writer = BufWriter::new(handle);
    serde_json::to_writer(&mut writer, &output)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    Ok(())
}
