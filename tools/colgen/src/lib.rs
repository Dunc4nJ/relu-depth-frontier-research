use anyhow::{Result, ensure};
use rustc_hash::FxHashMap as HashMap;
use serde::{Deserialize, Serialize};
use std::collections::BTreeMap;
use std::time::Instant;

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

/// Profiling-only active CPU clocks and operation counts for one or more
/// exact column generations. Nanosecond clocks sum across profiled columns and
/// may therefore exceed wall time when callers use Rayon.
#[derive(Clone, Debug, Default, Serialize)]
pub struct GenerationProfile {
    pub total_ns: u128,
    pub signed_matrix_ns: u128,
    pub increment_table_ns: u128,
    pub dp_total_ns: u128,
    pub dp_map_allocation_ns: u128,
    pub dp_hash_dedup_ns: u128,
    pub census_ns: u128,
    pub column_initialization_ns: u128,
    pub hinge_enumeration_ns: u128,
    pub canonicalization_ns: u128,
    pub hinge_hash_dedup_ns: u128,
    pub dp_layers: u128,
    pub dp_input_states: u128,
    pub dp_child_candidates: u128,
    pub dp_unique_states: u128,
    pub dp_dedup_hits: u128,
    pub dp_requested_capacity: u128,
    pub terminal_words: u128,
    pub zero_words: u128,
    pub negative_first_words: u128,
    pub active_hinge_words: u128,
    pub hinge_unique_directions: u128,
    pub hinge_dedup_hits: u128,
}

impl GenerationProfile {
    pub fn merge(&mut self, other: &Self) {
        macro_rules! add_fields {
            ($($field:ident),+ $(,)?) => {
                $(self.$field += other.$field;)+
            };
        }
        add_fields!(
            total_ns,
            signed_matrix_ns,
            increment_table_ns,
            dp_total_ns,
            dp_map_allocation_ns,
            dp_hash_dedup_ns,
            census_ns,
            column_initialization_ns,
            hinge_enumeration_ns,
            canonicalization_ns,
            hinge_hash_dedup_ns,
            dp_layers,
            dp_input_states,
            dp_child_candidates,
            dp_unique_states,
            dp_dedup_hits,
            dp_requested_capacity,
            terminal_words,
            zero_words,
            negative_first_words,
            active_hinge_words,
            hinge_unique_directions,
            hinge_dedup_hits,
        );
    }
}

#[derive(Clone, Copy)]
enum ProfileStage {
    Total,
    SignedMatrix,
    IncrementTable,
    DpTotal,
    DpMapAllocation,
    DpHashDedup,
    Census,
    ColumnInitialization,
    HingeEnumeration,
    Canonicalization,
    HingeHashDedup,
}

#[derive(Clone, Copy)]
enum ProfileCount {
    DpLayers,
    DpInputStates,
    DpChildCandidates,
    DpUniqueStates,
    DpDedupHits,
    DpRequestedCapacity,
    TerminalWords,
    ZeroWords,
    NegativeFirstWords,
    ActiveHingeWords,
    HingeUniqueDirections,
    HingeDedupHits,
}

trait GenerationObserver {
    type Timestamp;

    fn start(&self) -> Self::Timestamp;
    fn record(&mut self, stage: ProfileStage, started: Self::Timestamp);
    fn count(&mut self, counter: ProfileCount, value: usize);
}

struct NoProfile;

impl GenerationObserver for NoProfile {
    type Timestamp = ();

    #[inline(always)]
    fn start(&self) {}

    #[inline(always)]
    fn record(&mut self, _stage: ProfileStage, _started: ()) {}

    #[inline(always)]
    fn count(&mut self, _counter: ProfileCount, _value: usize) {}
}

#[derive(Default)]
struct TimedProfile {
    metrics: GenerationProfile,
}

impl GenerationObserver for TimedProfile {
    type Timestamp = Instant;

    #[inline(always)]
    fn start(&self) -> Instant {
        Instant::now()
    }

    #[inline(always)]
    fn record(&mut self, stage: ProfileStage, started: Instant) {
        let elapsed = started.elapsed().as_nanos();
        match stage {
            ProfileStage::Total => self.metrics.total_ns += elapsed,
            ProfileStage::SignedMatrix => self.metrics.signed_matrix_ns += elapsed,
            ProfileStage::IncrementTable => self.metrics.increment_table_ns += elapsed,
            ProfileStage::DpTotal => self.metrics.dp_total_ns += elapsed,
            ProfileStage::DpMapAllocation => self.metrics.dp_map_allocation_ns += elapsed,
            ProfileStage::DpHashDedup => self.metrics.dp_hash_dedup_ns += elapsed,
            ProfileStage::Census => self.metrics.census_ns += elapsed,
            ProfileStage::ColumnInitialization => {
                self.metrics.column_initialization_ns += elapsed;
            }
            ProfileStage::HingeEnumeration => self.metrics.hinge_enumeration_ns += elapsed,
            ProfileStage::Canonicalization => self.metrics.canonicalization_ns += elapsed,
            ProfileStage::HingeHashDedup => self.metrics.hinge_hash_dedup_ns += elapsed,
        }
    }

    #[inline(always)]
    fn count(&mut self, counter: ProfileCount, value: usize) {
        let value = value as u128;
        match counter {
            ProfileCount::DpLayers => self.metrics.dp_layers += value,
            ProfileCount::DpInputStates => self.metrics.dp_input_states += value,
            ProfileCount::DpChildCandidates => self.metrics.dp_child_candidates += value,
            ProfileCount::DpUniqueStates => self.metrics.dp_unique_states += value,
            ProfileCount::DpDedupHits => self.metrics.dp_dedup_hits += value,
            ProfileCount::DpRequestedCapacity => self.metrics.dp_requested_capacity += value,
            ProfileCount::TerminalWords => self.metrics.terminal_words += value,
            ProfileCount::ZeroWords => self.metrics.zero_words += value,
            ProfileCount::NegativeFirstWords => self.metrics.negative_first_words += value,
            ProfileCount::ActiveHingeWords => self.metrics.active_hinge_words += value,
            ProfileCount::HingeUniqueDirections => {
                self.metrics.hinge_unique_directions += value;
            }
            ProfileCount::HingeDedupHits => self.metrics.hinge_dedup_hits += value,
        }
    }
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
struct WideState {
    mask: u16,
    word: [i8; MAX_N],
}

/// For n <= 14, the 16-bit visited mask and all n signed-byte word
/// coordinates fit without loss in one u128.  Hashing this key performs two
/// native-word mixes instead of hashing a separately stored mask and byte
/// array on every DP child probe.
#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq)]
struct PackedState(u128);

trait DpState: Copy + Eq + std::hash::Hash {
    fn zero() -> Self;
    fn mask(self) -> usize;
    fn child(self, vertex: usize, depth: usize, increment: i8) -> Result<Self>;
    fn copy_word(self, n: usize, target: &mut [i8; MAX_N]);
}

impl DpState for WideState {
    #[inline(always)]
    fn zero() -> Self {
        Self {
            mask: 0,
            word: [0; MAX_N],
        }
    }

    #[inline(always)]
    fn mask(self) -> usize {
        self.mask as usize
    }

    #[inline(always)]
    fn child(mut self, vertex: usize, depth: usize, increment: i8) -> Result<Self> {
        self.mask |= 1u16 << vertex;
        self.word[depth] = increment;
        Ok(self)
    }

    #[inline(always)]
    fn copy_word(self, _n: usize, target: &mut [i8; MAX_N]) {
        *target = self.word;
    }
}

impl DpState for PackedState {
    #[inline(always)]
    fn zero() -> Self {
        Self(0)
    }

    #[inline(always)]
    fn mask(self) -> usize {
        (self.0 as u16) as usize
    }

    #[inline(always)]
    fn child(self, vertex: usize, depth: usize, increment: i8) -> Result<Self> {
        debug_assert!(depth < 14);
        let mask = 1u128 << vertex;
        let coordinate = u128::from(increment as u8) << (16 + 8 * depth);
        Ok(Self(self.0 | mask | coordinate))
    }

    #[inline(always)]
    fn copy_word(self, n: usize, target: &mut [i8; MAX_N]) {
        for (depth, value) in target.iter_mut().enumerate().take(n) {
            *value = ((self.0 >> (16 + 8 * depth)) as u8) as i8;
        }
    }
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

fn increments(matrix: &[Vec<i16>], n: usize) -> Result<Vec<Vec<i8>>> {
    let width = 1usize << n;
    let mut result = vec![vec![0i8; width]; n];
    for vertex in 0..n {
        for mask in 1usize..width {
            let bit = mask & mask.wrapping_neg();
            let other = bit.trailing_zeros() as usize;
            let increment = i16::from(result[vertex][mask ^ bit])
                .checked_add(matrix[vertex][other])
                .ok_or_else(|| anyhow::anyhow!("back-degree increment overflow"))?;
            result[vertex][mask] = i8::try_from(increment)
                .map_err(|_| anyhow::anyhow!("back-degree increment exceeds compact i8 range"))?;
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
    let mut observer = NoProfile;
    accumulate_word_observed(column, word, count, &mut observer)
}

fn accumulate_word_observed<T, O>(
    column: &mut SparseColumn,
    word: &[T],
    count: u64,
    observer: &mut O,
) -> Result<()>
where
    T: Copy + Into<i64>,
    O: GenerationObserver,
{
    let canonicalization_started = observer.start();
    let first = word
        .iter()
        .copied()
        .map(Into::into)
        .find(|&value| value != 0);
    let Some(first) = first else {
        observer.count(ProfileCount::ZeroWords, 1);
        observer.record(ProfileStage::Canonicalization, canonicalization_started);
        return Ok(());
    };
    ensure!(
        word.iter().copied().map(Into::into).sum::<i64>() == 0,
        "raw word is not zero-sum"
    );
    let count_i64 = i64::try_from(count)?;
    if first < 0 {
        observer.count(ProfileCount::NegativeFirstWords, 1);
        for (coordinate, value) in column
            .linear
            .iter_mut()
            .zip(word.iter().copied().map(Into::into))
        {
            let correction = count_i64
                .checked_mul(value)
                .ok_or_else(|| anyhow::anyhow!("linear correction product overflow"))?;
            add_checked(coordinate, correction, "linear")?;
        }
    }

    let divisor = word.iter().copied().map(Into::into).fold(0i64, gcd);
    ensure!(divisor > 0, "nonzero word has zero gcd");
    let orientation = if first > 0 { 1i64 } else { -1i64 };
    let direction: Vec<i16> = word
        .iter()
        .copied()
        .map(Into::into)
        .map(|value| i16::try_from(orientation * value / divisor))
        .collect::<std::result::Result<_, _>>()?;
    ensure!(direction.iter().copied().find(|&value| value != 0).unwrap() > 0);

    let mut prefix = 0i64;
    let mut active_on_ordered_cone = false;
    for &value in &direction[..direction.len() - 1] {
        prefix += value as i64;
        active_on_ordered_cone |= prefix < 0;
    }
    if active_on_ordered_cone {
        observer.count(ProfileCount::ActiveHingeWords, 1);
        let contribution = count_i64
            .checked_mul(divisor)
            .ok_or_else(|| anyhow::anyhow!("hinge contribution overflow"))?;
        observer.record(ProfileStage::Canonicalization, canonicalization_started);
        let hashing_started = observer.start();
        match column.hinges.entry(direction) {
            std::collections::hash_map::Entry::Occupied(mut entry) => {
                observer.count(ProfileCount::HingeDedupHits, 1);
                add_checked(entry.get_mut(), contribution, "hinge")?;
            }
            std::collections::hash_map::Entry::Vacant(entry) => {
                observer.count(ProfileCount::HingeUniqueDirections, 1);
                entry.insert(contribution);
            }
        }
        observer.record(ProfileStage::HingeHashDedup, hashing_started);
    } else {
        observer.record(ProfileStage::Canonicalization, canonicalization_started);
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
    let mut observer = NoProfile;
    generate_column_observed(record, n, branch_edges, &mut observer)
}

/// Generate an exact column while collecting profiling-only active clocks.
/// The returned column is required to be byte-for-byte equivalent after the
/// normal sorted output conversion; callers should sample because the clock
/// reads inside hash-table operations deliberately perturb throughput.
pub fn generate_column_profiled(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
) -> Result<(SparseColumn, GenerationProfile)> {
    let mut observer = TimedProfile::default();
    let column = generate_column_observed(record, n, branch_edges, &mut observer)?;
    Ok((column, observer.metrics))
}

fn generate_column_observed<O: GenerationObserver>(
    record: &SignedRecord,
    n: usize,
    branch_edges: usize,
    observer: &mut O,
) -> Result<SparseColumn> {
    let total_started = observer.start();
    let stage_started = observer.start();
    let matrix = signed_matrix(record, n, branch_edges)?;
    observer.record(ProfileStage::SignedMatrix, stage_started);
    let stage_started = observer.start();
    let increments = increments(&matrix, n)?;
    observer.record(ProfileStage::IncrementTable, stage_started);
    let column = if n <= 14 {
        let current = run_subset_dp::<PackedState, _>(&increments, n, observer)?;
        finish_column(current, n, branch_edges, observer)?
    } else {
        let current = run_subset_dp::<WideState, _>(&increments, n, observer)?;
        finish_column(current, n, branch_edges, observer)?
    };
    observer.record(ProfileStage::Total, total_started);
    Ok(column)
}

fn run_subset_dp<S, O>(
    increments: &[Vec<i8>],
    n: usize,
    observer: &mut O,
) -> Result<HashMap<S, u64>>
where
    S: DpState,
    O: GenerationObserver,
{
    let mut current: HashMap<S, u64> = HashMap::default();
    current.insert(S::zero(), 1u64);
    let dp_started = observer.start();
    for depth in 0..n {
        observer.count(ProfileCount::DpLayers, 1);
        observer.count(ProfileCount::DpInputStates, current.len());
        let capacity = current.len().saturating_mul((n - depth).min(4));
        observer.count(ProfileCount::DpRequestedCapacity, capacity);
        let allocation_started = observer.start();
        let mut next: HashMap<S, u64> =
            HashMap::with_capacity_and_hasher(capacity, Default::default());
        observer.record(ProfileStage::DpMapAllocation, allocation_started);
        for (state, count) in current {
            let mask = state.mask();
            for (vertex, vertex_increments) in increments.iter().enumerate().take(n) {
                let bit = 1usize << vertex;
                if mask & bit != 0 {
                    continue;
                }
                observer.count(ProfileCount::DpChildCandidates, 1);
                let child = state.child(vertex, depth, vertex_increments[mask])?;
                let hashing_started = observer.start();
                match next.entry(child) {
                    std::collections::hash_map::Entry::Occupied(mut entry) => {
                        observer.count(ProfileCount::DpDedupHits, 1);
                        let value = entry
                            .get()
                            .checked_add(count)
                            .ok_or_else(|| anyhow::anyhow!("permutation multiplicity overflow"))?;
                        *entry.get_mut() = value;
                    }
                    std::collections::hash_map::Entry::Vacant(entry) => {
                        observer.count(ProfileCount::DpUniqueStates, 1);
                        entry.insert(count);
                    }
                }
                observer.record(ProfileStage::DpHashDedup, hashing_started);
            }
        }
        current = next;
    }
    observer.record(ProfileStage::DpTotal, dp_started);
    Ok(current)
}

fn finish_column<S, O>(
    current: HashMap<S, u64>,
    n: usize,
    branch_edges: usize,
    observer: &mut O,
) -> Result<SparseColumn>
where
    S: DpState,
    O: GenerationObserver,
{
    let census_started = observer.start();
    let expected = checked_factorial(n)?;
    let observed = current.values().try_fold(0u64, |acc, &value| {
        acc.checked_add(value)
            .ok_or_else(|| anyhow::anyhow!("permutation census overflow"))
    })?;
    ensure!(
        observed == expected,
        "permutation census mismatch: {observed}/{expected}"
    );
    observer.record(ProfileStage::Census, census_started);
    let initialization_started = observer.start();
    let mut column = initialized_column(n, branch_edges)?;
    observer.record(ProfileStage::ColumnInitialization, initialization_started);
    observer.count(ProfileCount::TerminalWords, current.len());
    let hinge_started = observer.start();
    let mut word = [0i8; MAX_N];
    for (state, count) in current {
        state.copy_word(n, &mut word);
        accumulate_word_observed(&mut column, &word[..n], count, observer)?;
    }
    observer.record(ProfileStage::HingeEnumeration, hinge_started);
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
    fn profiling_path_preserves_exact_column() {
        let record = sample_record();
        let expected = generate_column(&record, 5, 2).unwrap();
        let (profiled, profile) = generate_column_profiled(&record, 5, 2).unwrap();
        assert_eq!(profiled, expected);
        assert_eq!(profile.dp_layers, 5);
        assert!(profile.dp_child_candidates > 0);
        assert!(profile.total_ns > 0);
        assert_eq!(
            profile.dp_child_candidates,
            profile.dp_unique_states + profile.dp_dedup_hits
        );
        assert_eq!(profile.terminal_words, 17);
        assert_eq!(
            profile.active_hinge_words,
            profile.hinge_unique_directions + profile.hinge_dedup_hits
        );
    }

    #[test]
    fn compact_state_covers_signed_mass_endpoint() {
        assert_eq!(std::mem::size_of::<PackedState>(), 16);
        assert_eq!(std::mem::size_of::<WideState>(), 18);
        let mut packed = PackedState::zero();
        let expected = [-128, -127, -1, 0, 1, 42, 126, 127, -9, 17, -33, 88, -64, 63];
        for (depth, &increment) in expected.iter().enumerate() {
            packed = packed.child(depth, depth, increment).unwrap();
        }
        let mut decoded = [0i8; MAX_N];
        packed.copy_word(expected.len(), &mut decoded);
        assert_eq!(&decoded[..expected.len()], &expected);
        assert_eq!(packed.mask(), (1usize << expected.len()) - 1);
        let record = SignedRecord {
            sequence: None,
            active_vertices: 3,
            signed_mass: 127,
            negative_edges: vec![[0, 1]; 127],
            positive_edges: vec![[0, 2]; 127],
            abs_components: None,
            abs_beta: None,
        };
        assert_eq!(
            generate_column(&record, 3, 127).unwrap(),
            brute_force_column(&record, 3, 127).unwrap()
        );
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
