use anyhow::{Context, Result, bail, ensure};
use num_bigint::BigInt;
use num_integer::Integer;
use num_traits::{One, ToPrimitive, Zero};
use rayon::prelude::*;
use rustc_hash::FxHashMap as HashMap;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::cmp::Ordering;
use std::time::Instant;

pub const MAX_N: usize = 16;
type Edge = [usize; 2];
type Side = Vec<Edge>;

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Certificate {
    pub n: usize,
    pub terms: Vec<Term>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct Term {
    pub coefficient: Value,
    pub pair: Vec<Vec<[usize; 2]>>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct SparseColumn {
    pub linear: Vec<i64>,
    pub hinges: HashMap<Vec<i16>, i64>,
}

#[derive(Clone, Debug)]
struct Rational {
    numerator: BigInt,
    denominator: BigInt,
}

impl Rational {
    fn parse(value: &Value) -> Result<Self> {
        let text = match value {
            Value::String(value) => value.trim().to_owned(),
            Value::Number(value) if value.is_i64() || value.is_u64() => value.to_string(),
            _ => bail!("coefficient must be an exact integer or rational string"),
        };
        let (numerator, denominator) = match text.split_once('/') {
            Some((numerator, denominator)) => {
                ensure!(
                    !denominator.contains('/'),
                    "coefficient contains more than one slash"
                );
                (
                    numerator.trim().parse::<BigInt>()?,
                    denominator.trim().parse::<BigInt>()?,
                )
            }
            None => (text.parse::<BigInt>()?, BigInt::one()),
        };
        ensure!(!denominator.is_zero(), "coefficient denominator is zero");
        let (mut numerator, mut denominator) = if denominator < BigInt::zero() {
            (-numerator, -denominator)
        } else {
            (numerator, denominator)
        };
        let divisor = numerator.gcd(&denominator);
        numerator /= &divisor;
        denominator /= divisor;
        Ok(Self {
            numerator,
            denominator,
        })
    }

    pub fn add_integer_one(&self) -> Value {
        let numerator = &self.numerator + &self.denominator;
        Value::String(format_fraction(&numerator, &self.denominator))
    }
}

fn format_fraction(numerator: &BigInt, denominator: &BigInt) -> String {
    debug_assert!(denominator > &BigInt::zero());
    if numerator.is_zero() {
        return "0/1".to_owned();
    }
    let divisor = numerator.gcd(denominator);
    format!("{}/{}", numerator / &divisor, denominator / divisor)
}

#[derive(Clone, Debug)]
enum ExactInt {
    Small(i128),
    Big(BigInt),
}

impl Default for ExactInt {
    fn default() -> Self {
        Self::Small(0)
    }
}

impl ExactInt {
    fn from_big(value: BigInt) -> Self {
        value
            .to_i128()
            .map(Self::Small)
            .unwrap_or_else(|| Self::Big(value))
    }

    fn is_zero(&self) -> bool {
        match self {
            Self::Small(value) => *value == 0,
            Self::Big(value) => value.is_zero(),
        }
    }

    fn to_bigint(&self) -> BigInt {
        match self {
            Self::Small(value) => BigInt::from(*value),
            Self::Big(value) => value.clone(),
        }
    }

    fn add_mul(&mut self, coefficient: &Self, factor: i64) {
        if factor == 0 || coefficient.is_zero() {
            return;
        }
        if let (Self::Small(target), Self::Small(coefficient)) = (&mut *self, coefficient)
            && let Some(product) = coefficient.checked_mul(factor as i128)
            && let Some(sum) = target.checked_add(product)
        {
            *target = sum;
            return;
        }
        let sum = self.to_bigint() + coefficient.to_bigint() * factor;
        *self = Self::from_big(sum);
    }

    fn add_exact(&mut self, other: Self) {
        if let (Self::Small(target), Self::Small(value)) = (&mut *self, &other)
            && let Some(sum) = target.checked_add(*value)
        {
            *target = sum;
            return;
        }
        let sum = self.to_bigint() + other.to_bigint();
        *self = Self::from_big(sum);
    }

    fn rational_string(&self, denominator: &BigInt) -> String {
        format_fraction(&self.to_bigint(), denominator)
    }
}

#[derive(Clone, Copy, Debug, Hash, PartialEq, Eq)]
struct State {
    mask: u16,
    word: [i16; MAX_N],
}

fn checked_factorial(n: usize) -> Result<u64> {
    (1..=n as u64).try_fold(1u64, |product, value| {
        product
            .checked_mul(value)
            .ok_or_else(|| anyhow::anyhow!("factorial({n}) exceeds u64"))
    })
}

fn gcd(mut left: i64, mut right: i64) -> i64 {
    left = left.abs();
    right = right.abs();
    while right != 0 {
        (left, right) = (right, left % right);
    }
    left
}

fn validate_n(n: usize) -> Result<()> {
    ensure!((2..=MAX_N).contains(&n), "n must lie in 2..={MAX_N}");
    let _ = checked_factorial(n)?;
    Ok(())
}

fn parsed_sides(term: &Term, n: usize) -> Result<(Side, Side)> {
    ensure!(
        term.pair.len() == 2,
        "each term must contain exactly two sides"
    );
    let mut parsed = Vec::with_capacity(2);
    for side in &term.pair {
        let mut edges = Vec::with_capacity(side.len());
        for &[first, second] in side {
            ensure!(
                1 <= first && first <= second && second <= n,
                "invalid one-based endpoint pair [{first},{second}]"
            );
            edges.push([first - 1, second - 1]);
        }
        parsed.push(edges);
    }
    ensure!(
        parsed[0].len() == parsed[1].len(),
        "the two sides of a pair must have the same size"
    );
    ensure!(
        parsed[0].len() <= i16::MAX as usize,
        "branch occurrence count exceeds i16"
    );
    Ok((parsed.remove(0), parsed.remove(0)))
}

fn signed_matrix(left: &[[usize; 2]], right: &[[usize; 2]], n: usize) -> Result<Vec<Vec<i16>>> {
    let mut matrix = vec![vec![0i16; n]; n];
    for (sign, side) in [(-1i16, left), (1i16, right)] {
        for &[first, second] in side {
            matrix[first][second] = matrix[first][second]
                .checked_add(sign)
                .context("signed edge multiplicity overflow")?;
            if first != second {
                matrix[second][first] = matrix[second][first]
                    .checked_add(sign)
                    .context("signed edge multiplicity overflow")?;
            }
        }
    }
    Ok(matrix)
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
                .context("back-degree increment overflow")?;
        }
    }
    Ok(result)
}

fn analytic_left_base(left: &[[usize; 2]], n: usize) -> Result<Vec<i64>> {
    let loops = i64::try_from(left.iter().filter(|edge| edge[0] == edge[1]).count())?;
    let nonloops = i64::try_from(left.len())? - loops;
    let loop_factor = i64::try_from(checked_factorial(n - 1)?)?;
    let edge_factor = i64::try_from(checked_factorial(n - 2)?)?;
    (0..n)
        .map(|rank| {
            loops
                .checked_mul(loop_factor)
                .and_then(|value| {
                    nonloops
                        .checked_mul(2)
                        .and_then(|value| value.checked_mul(rank as i64))
                        .and_then(|value| value.checked_mul(edge_factor))
                        .and_then(|edge_value| value.checked_add(edge_value))
                })
                .context("analytic linear base overflow")
        })
        .collect()
}

fn add_checked(target: &mut i64, value: i64, label: &str) -> Result<()> {
    *target = target
        .checked_add(value)
        .with_context(|| format!("{label} coefficient overflow"))?;
    Ok(())
}

fn accumulate_oriented_word(column: &mut SparseColumn, word: &[i16], count: u64) -> Result<()> {
    let Some(first) = word.iter().copied().find(|value| *value != 0) else {
        return Ok(());
    };
    ensure!(
        word.iter().map(|value| i64::from(*value)).sum::<i64>() == 0,
        "right-minus-left word is not zero-sum"
    );
    let count = i64::try_from(count)?;
    if first < 0 {
        for (coordinate, value) in column.linear.iter_mut().zip(word) {
            let correction = count
                .checked_mul(i64::from(*value))
                .context("linear correction product overflow")?;
            add_checked(coordinate, correction, "linear")?;
        }
    }

    let divisor = word
        .iter()
        .fold(0i64, |current, value| gcd(current, i64::from(*value)));
    ensure!(divisor > 0, "nonzero word has zero gcd");
    let orientation = if first > 0 { 1i64 } else { -1i64 };
    let direction: Vec<i16> = word
        .iter()
        .map(|value| i16::try_from(orientation * i64::from(*value) / divisor))
        .collect::<std::result::Result<_, _>>()?;
    ensure!(
        direction.iter().copied().find(|value| *value != 0) > Some(0),
        "hinge orientation failure"
    );

    let mut prefix = 0i64;
    let mut active_on_cone = false;
    for value in &direction[..direction.len() - 1] {
        prefix += i64::from(*value);
        active_on_cone |= prefix < 0;
    }
    if active_on_cone {
        let contribution = count
            .checked_mul(divisor)
            .context("hinge coefficient product overflow")?;
        let entry = column.hinges.entry(direction).or_default();
        add_checked(entry, contribution, "hinge")?;
    }
    Ok(())
}

pub fn dynamic_column(term: &Term, n: usize) -> Result<SparseColumn> {
    validate_n(n)?;
    let (left, right) = parsed_sides(term, n)?;
    let matrix = signed_matrix(&left, &right, n)?;
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
                        let total = entry
                            .get()
                            .checked_add(count)
                            .context("permutation multiplicity overflow")?;
                        *entry.get_mut() = total;
                    }
                    std::collections::hash_map::Entry::Vacant(entry) => {
                        entry.insert(count);
                    }
                }
            }
        }
        current = next;
    }
    let observed = current.values().try_fold(0u64, |total, count| {
        total
            .checked_add(*count)
            .context("permutation census overflow")
    })?;
    let expected = checked_factorial(n)?;
    ensure!(
        observed == expected,
        "permutation census mismatch: {observed}/{expected}"
    );
    let mut column = SparseColumn {
        linear: analytic_left_base(&left, n)?,
        hinges: HashMap::default(),
    };
    for (state, count) in current {
        accumulate_oriented_word(&mut column, &state.word[..n], count)?;
    }
    Ok(column)
}

fn literal_accumulate(
    column: &mut SparseColumn,
    left: &[[usize; 2]],
    right: &[[usize; 2]],
    position: &[usize],
) -> Result<()> {
    let n = position.len();
    let side_form = |side: &[[usize; 2]]| -> Vec<i16> {
        let mut form = vec![0i16; n];
        for &[first, second] in side {
            form[position[first].max(position[second])] += 1;
        }
        form
    };
    let left_form = side_form(left);
    let right_form = side_form(right);
    let (base, other) = match left_form.cmp(&right_form) {
        Ordering::Greater => (&right_form, &left_form),
        Ordering::Less | Ordering::Equal => (&left_form, &right_form),
    };
    for (coordinate, value) in column.linear.iter_mut().zip(base) {
        add_checked(coordinate, i64::from(*value), "literal linear")?;
    }
    let direction: Vec<i16> = other
        .iter()
        .zip(base)
        .map(|(other, base)| *other - *base)
        .collect();
    let Some(_) = direction.iter().find(|value| **value != 0) else {
        return Ok(());
    };
    let divisor = direction
        .iter()
        .fold(0i64, |current, value| gcd(current, i64::from(*value)));
    ensure!(divisor > 0, "literal nonzero direction has zero gcd");
    let primitive: Vec<i16> = direction
        .iter()
        .map(|value| i16::try_from(i64::from(*value) / divisor))
        .collect::<std::result::Result<_, _>>()?;
    let mut prefix = 0i64;
    for value in &primitive[..n - 1] {
        prefix += i64::from(*value);
        if prefix < 0 {
            let entry = column.hinges.entry(primitive).or_default();
            add_checked(entry, divisor, "literal hinge")?;
            break;
        }
    }
    Ok(())
}

pub fn literal_column(term: &Term, n: usize) -> Result<SparseColumn> {
    validate_n(n)?;
    ensure!(n <= 8, "literal permutation mode is capped at n=8");
    let (left, right) = parsed_sides(term, n)?;
    let mut column = SparseColumn {
        linear: vec![0; n],
        hinges: HashMap::default(),
    };
    let mut order = Vec::with_capacity(n);
    let mut used = vec![false; n];
    let mut position = vec![0usize; n];

    fn visit(
        column: &mut SparseColumn,
        left: &[[usize; 2]],
        right: &[[usize; 2]],
        order: &mut Vec<usize>,
        used: &mut [bool],
        position: &mut [usize],
    ) -> Result<()> {
        let n = used.len();
        if order.len() == n {
            for (rank, vertex) in order.iter().enumerate() {
                position[*vertex] = rank;
            }
            return literal_accumulate(column, left, right, position);
        }
        for vertex in 0..n {
            if used[vertex] {
                continue;
            }
            used[vertex] = true;
            order.push(vertex);
            visit(column, left, right, order, used, position)?;
            order.pop();
            used[vertex] = false;
        }
        Ok(())
    }

    visit(
        &mut column,
        &left,
        &right,
        &mut order,
        &mut used,
        &mut position,
    )?;
    Ok(column)
}

fn compare_columns(index: usize, dynamic: &SparseColumn, literal: &SparseColumn) -> Result<()> {
    if dynamic.linear != literal.linear {
        bail!(
            "term {index}: DP/literal linear mismatch: dp={:?} literal={:?}",
            dynamic.linear,
            literal.linear
        );
    }
    if dynamic.hinges != literal.hinges {
        let mut keys: Vec<_> = dynamic.hinges.keys().chain(literal.hinges.keys()).collect();
        keys.sort();
        keys.dedup();
        let first = keys
            .into_iter()
            .find(|key| dynamic.hinges.get(*key) != literal.hinges.get(*key));
        bail!(
            "term {index}: DP/literal hinge mismatch: dp_nnz={} literal_nnz={} first={:?}",
            dynamic.hinges.len(),
            literal.hinges.len(),
            first.map(|key| (key, dynamic.hinges.get(key), literal.hinges.get(key)))
        );
    }
    Ok(())
}

#[derive(Default)]
struct PartialAccumulator {
    linear: Vec<ExactInt>,
    hinges: HashMap<Vec<i16>, ExactInt>,
    terms_checked: usize,
    nonzero_terms: usize,
    literal_matches: usize,
    emitted_hinge_entries: u64,
    dp_worker_seconds: f64,
    literal_worker_seconds: f64,
}

impl PartialAccumulator {
    fn new(n: usize) -> Self {
        Self {
            linear: vec![ExactInt::default(); n],
            ..Self::default()
        }
    }

    fn add_column(&mut self, column: &SparseColumn, coefficient: &ExactInt) -> Result<()> {
        ensure!(
            self.linear.len() == column.linear.len(),
            "column linear dimension mismatch"
        );
        for (target, value) in self.linear.iter_mut().zip(&column.linear) {
            target.add_mul(coefficient, *value);
        }
        for (direction, value) in &column.hinges {
            self.hinges
                .entry(direction.clone())
                .or_default()
                .add_mul(coefficient, *value);
        }
        self.emitted_hinge_entries = self
            .emitted_hinge_entries
            .checked_add(u64::try_from(column.hinges.len())?)
            .context("emitted hinge-entry census overflow")?;
        Ok(())
    }

    fn merge(mut self, mut other: Self) -> Result<Self> {
        ensure!(
            self.linear.len() == other.linear.len(),
            "partial linear dimension mismatch"
        );
        if self.hinges.len() < other.hinges.len() {
            std::mem::swap(&mut self, &mut other);
        }
        for (target, value) in self.linear.iter_mut().zip(other.linear) {
            target.add_exact(value);
        }
        for (direction, value) in other.hinges {
            self.hinges.entry(direction).or_default().add_exact(value);
        }
        self.terms_checked += other.terms_checked;
        self.nonzero_terms += other.nonzero_terms;
        self.literal_matches += other.literal_matches;
        self.emitted_hinge_entries = self
            .emitted_hinge_entries
            .checked_add(other.emitted_hinge_entries)
            .context("merged hinge-entry census overflow")?;
        self.dp_worker_seconds += other.dp_worker_seconds;
        self.literal_worker_seconds += other.literal_worker_seconds;
        Ok(self)
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct Residual {
    pub direction: Option<Vec<i16>>,
    pub rank_one_based: Option<usize>,
    pub value: String,
}

#[derive(Clone, Debug)]
pub struct Analysis {
    pub verified: bool,
    pub n: usize,
    pub terms_total: usize,
    pub nonzero_terms: usize,
    pub dp_columns_checked: usize,
    pub literal_dp_matches: usize,
    pub permutations_per_literal_term: Option<u64>,
    pub coefficient_common_denominator: String,
    pub linear_rows: usize,
    pub bad_linear_rows: usize,
    pub hinge_rows_union: usize,
    pub bad_hinge_rows: usize,
    pub first_bad_linear: Option<Residual>,
    pub first_bad_hinge: Option<Residual>,
    pub emitted_hinge_entries: u64,
    pub compute_wall_seconds: f64,
    pub dp_worker_seconds: f64,
    pub literal_worker_seconds: f64,
}

pub fn analyze_certificate(
    certificate: &Certificate,
    threads: usize,
    literal_check: bool,
) -> Result<Analysis> {
    validate_n(certificate.n)?;
    ensure!((1..=64).contains(&threads), "threads must lie in 1..=64");
    ensure!(
        !literal_check || certificate.n <= 8,
        "literal checks are capped at n=8"
    );
    ensure!(!certificate.terms.is_empty(), "certificate has no terms");

    let rationals: Vec<Rational> = certificate
        .terms
        .iter()
        .enumerate()
        .map(|(index, term)| {
            let _ = parsed_sides(term, certificate.n)
                .with_context(|| format!("validating term {index}"))?;
            Rational::parse(&term.coefficient)
                .with_context(|| format!("parsing coefficient for term {index}"))
        })
        .collect::<Result<_>>()?;
    let common_denominator = rationals.iter().fold(BigInt::one(), |current, rational| {
        current.lcm(&rational.denominator)
    });
    let scaled: Vec<ExactInt> = rationals
        .iter()
        .map(|rational| {
            ExactInt::from_big(&rational.numerator * (&common_denominator / &rational.denominator))
        })
        .collect();

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let started = Instant::now();
    let mut total = pool.install(|| {
        certificate
            .terms
            .par_iter()
            .zip(scaled.par_iter())
            .enumerate()
            .try_fold(
                || PartialAccumulator::new(certificate.n),
                |mut partial, (index, (term, coefficient))| -> Result<_> {
                    let dp_started = Instant::now();
                    let dynamic = dynamic_column(term, certificate.n)
                        .with_context(|| format!("dynamic evaluation of term {index}"))?;
                    partial.dp_worker_seconds += dp_started.elapsed().as_secs_f64();
                    if literal_check {
                        let literal_started = Instant::now();
                        let literal = literal_column(term, certificate.n)
                            .with_context(|| format!("literal evaluation of term {index}"))?;
                        partial.literal_worker_seconds += literal_started.elapsed().as_secs_f64();
                        compare_columns(index, &dynamic, &literal)?;
                        partial.literal_matches += 1;
                    }
                    partial.terms_checked += 1;
                    if !coefficient.is_zero() {
                        partial.nonzero_terms += 1;
                        partial.add_column(&dynamic, coefficient)?;
                    }
                    Ok(partial)
                },
            )
            .try_reduce(
                || PartialAccumulator::new(certificate.n),
                |left, right| left.merge(right),
            )
    })?;
    let compute_wall_seconds = started.elapsed().as_secs_f64();
    ensure!(
        total.terms_checked == certificate.terms.len(),
        "term census mismatch: {}/{}",
        total.terms_checked,
        certificate.terms.len()
    );
    total.linear[certificate.n - 1].add_exact(ExactInt::from_big(-&common_denominator));

    let bad_linear_rows = total.linear.iter().filter(|value| !value.is_zero()).count();
    let first_bad_linear = total
        .linear
        .iter()
        .enumerate()
        .find(|(_, value)| !value.is_zero())
        .map(|(rank, value)| Residual {
            direction: None,
            rank_one_based: Some(rank + 1),
            value: value.rational_string(&common_denominator),
        });
    let hinge_rows_union = total.hinges.len();
    let bad_hinge_rows = total
        .hinges
        .values()
        .filter(|value| !value.is_zero())
        .count();
    let mut bad_directions: Vec<_> = total
        .hinges
        .iter()
        .filter(|(_, value)| !value.is_zero())
        .collect();
    bad_directions.sort_by(|left, right| left.0.cmp(right.0));
    let first_bad_hinge = bad_directions.first().map(|(direction, value)| Residual {
        direction: Some((*direction).clone()),
        rank_one_based: None,
        value: value.rational_string(&common_denominator),
    });

    Ok(Analysis {
        verified: bad_linear_rows == 0 && bad_hinge_rows == 0,
        n: certificate.n,
        terms_total: certificate.terms.len(),
        nonzero_terms: total.nonzero_terms,
        dp_columns_checked: total.terms_checked,
        literal_dp_matches: total.literal_matches,
        permutations_per_literal_term: literal_check
            .then(|| checked_factorial(certificate.n))
            .transpose()?,
        coefficient_common_denominator: common_denominator.to_string(),
        linear_rows: certificate.n,
        bad_linear_rows,
        hinge_rows_union,
        bad_hinge_rows,
        first_bad_linear,
        first_bad_hinge,
        emitted_hinge_entries: total.emitted_hinge_entries,
        compute_wall_seconds,
        dp_worker_seconds: total.dp_worker_seconds,
        literal_worker_seconds: total.literal_worker_seconds,
    })
}

pub fn mutate_coefficient(certificate: &mut Certificate) -> Result<()> {
    let first = certificate
        .terms
        .first_mut()
        .context("cannot mutate an empty certificate")?;
    let coefficient = Rational::parse(&first.coefficient)?;
    first.coefficient = coefficient.add_integer_one();
    Ok(())
}

pub fn mutate_endpoint(certificate: &mut Certificate) -> Result<()> {
    validate_n(certificate.n)?;
    let edge = certificate
        .terms
        .first_mut()
        .and_then(|term| term.pair.first_mut())
        .and_then(|side| side.first_mut())
        .context("cannot mutate a certificate with no endpoint")?;
    if edge[1] < certificate.n {
        edge[1] += 1;
    } else if edge[0] > 1 {
        edge[0] -= 1;
    } else {
        bail!("no distinct valid endpoint mutation exists");
    }
    ensure!(
        edge[0] <= edge[1],
        "endpoint mutation broke canonical order"
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn term(coefficient: &str, left: &[[usize; 2]], right: &[[usize; 2]]) -> Term {
        Term {
            coefficient: Value::String(coefficient.to_owned()),
            pair: vec![left.to_vec(), right.to_vec()],
        }
    }

    #[test]
    fn dp_matches_literal_with_loops_repeats_and_common_edges() {
        let sample = term(
            "1/1",
            &[[1, 1], [1, 2], [1, 2], [3, 5]],
            &[[2, 2], [1, 2], [2, 4], [4, 5]],
        );
        assert_eq!(
            dynamic_column(&sample, 5).unwrap(),
            literal_column(&sample, 5).unwrap()
        );
    }

    #[test]
    fn exact_n2_identity_and_mutant_are_distinguished() {
        let mut certificate = Certificate {
            n: 2,
            terms: vec![term("1/2", &[[1, 1]], &[[2, 2]])],
        };
        let positive = analyze_certificate(&certificate, 1, true).unwrap();
        assert!(positive.verified);
        assert_eq!(positive.literal_dp_matches, 1);
        mutate_coefficient(&mut certificate).unwrap();
        let negative = analyze_certificate(&certificate, 1, true).unwrap();
        assert!(!negative.verified);
    }

    #[test]
    fn arbitrary_precision_path_preserves_an_exact_identity() {
        let huge = BigInt::from(10u8).pow(50);
        let compensating_numerator = BigInt::one() - BigInt::from(2u8) * &huge;
        let certificate = Certificate {
            n: 2,
            terms: vec![
                term(&huge.to_string(), &[[1, 1]], &[[2, 2]]),
                term(&format!("{compensating_numerator}/2"), &[[1, 1]], &[[2, 2]]),
            ],
        };
        let analysis = analyze_certificate(&certificate, 1, true).unwrap();
        assert!(analysis.verified);
        assert_eq!(analysis.coefficient_common_denominator, "2");
    }

    #[test]
    fn malformed_endpoint_is_rejected() {
        let certificate: Certificate = serde_json::from_value(json!({
            "n": 5,
            "terms": [{"coefficient": "1", "pair": [[ [2, 1] ], [ [3, 4] ]]}]
        }))
        .unwrap();
        assert!(analyze_certificate(&certificate, 1, false).is_err());
    }
}
