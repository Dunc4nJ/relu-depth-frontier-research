use anyhow::{Context, Result, bail, ensure};
use num_bigint::BigInt;
use num_integer::Integer;
use num_traits::{One, ToPrimitive, Zero};
use rayon::prelude::*;
use rustc_hash::FxHashMap as HashMap;
use serde::de::{DeserializeSeed, Error as DeError, IgnoredAny, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::cmp::Ordering;
use std::fmt;
use std::fs::File;
use std::io::BufReader;
use std::path::Path;
use std::time::Instant;

pub const MAX_N: usize = 16;
pub const MAX_LITERAL_N: usize = 11;
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

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct StreamSummary {
    n: usize,
    terms: usize,
}

struct TermsSeed<'a, F> {
    n: usize,
    callback: &'a mut F,
}

impl<'de, F> DeserializeSeed<'de> for TermsSeed<'_, F>
where
    F: FnMut(usize, usize, Term) -> Result<()>,
{
    type Value = usize;

    fn deserialize<D>(self, deserializer: D) -> std::result::Result<Self::Value, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        deserializer.deserialize_seq(TermsVisitor {
            n: self.n,
            callback: self.callback,
        })
    }
}

struct TermsVisitor<'a, F> {
    n: usize,
    callback: &'a mut F,
}

impl<'de, F> Visitor<'de> for TermsVisitor<'_, F>
where
    F: FnMut(usize, usize, Term) -> Result<()>,
{
    type Value = usize;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a certificate terms array")
    }

    fn visit_seq<A>(self, mut sequence: A) -> std::result::Result<Self::Value, A::Error>
    where
        A: SeqAccess<'de>,
    {
        let mut count = 0usize;
        while let Some(term) = sequence.next_element::<Term>()? {
            (self.callback)(self.n, count, term).map_err(A::Error::custom)?;
            count = count
                .checked_add(1)
                .ok_or_else(|| A::Error::custom("certificate term count overflow"))?;
        }
        Ok(count)
    }
}

struct CertificateSeed<'a, F> {
    callback: &'a mut F,
}

impl<'de, F> DeserializeSeed<'de> for CertificateSeed<'_, F>
where
    F: FnMut(usize, usize, Term) -> Result<()>,
{
    type Value = StreamSummary;

    fn deserialize<D>(self, deserializer: D) -> std::result::Result<Self::Value, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        deserializer.deserialize_map(CertificateVisitor {
            callback: self.callback,
        })
    }
}

struct CertificateVisitor<'a, F> {
    callback: &'a mut F,
}

impl<'de, F> Visitor<'de> for CertificateVisitor<'_, F>
where
    F: FnMut(usize, usize, Term) -> Result<()>,
{
    type Value = StreamSummary;

    fn expecting(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str("a certificate object with n before terms")
    }

    fn visit_map<A>(self, mut object: A) -> std::result::Result<Self::Value, A::Error>
    where
        A: MapAccess<'de>,
    {
        let mut n = None;
        let mut terms = None;
        while let Some(field) = object.next_key::<String>()? {
            match field.as_str() {
                "n" => {
                    if n.replace(object.next_value()?).is_some() {
                        return Err(A::Error::duplicate_field("n"));
                    }
                }
                "terms" => {
                    if terms.is_some() {
                        return Err(A::Error::duplicate_field("terms"));
                    }
                    let n = n.ok_or_else(|| {
                        A::Error::custom("certificate field n must precede terms")
                    })?;
                    terms = Some(object.next_value_seed(TermsSeed {
                        n,
                        callback: self.callback,
                    })?);
                }
                _ => {
                    object.next_value::<IgnoredAny>()?;
                }
            }
        }
        Ok(StreamSummary {
            n: n.ok_or_else(|| A::Error::missing_field("n"))?,
            terms: terms.ok_or_else(|| A::Error::missing_field("terms"))?,
        })
    }
}

fn stream_certificate<F>(path: &Path, mut callback: F) -> Result<StreamSummary>
where
    F: FnMut(usize, usize, Term) -> Result<()>,
{
    let source = File::open(path).with_context(|| format!("opening {}", path.display()))?;
    let mut decoder = serde_json::Deserializer::from_reader(BufReader::new(source));
    let summary = CertificateSeed {
        callback: &mut callback,
    }
    .deserialize(&mut decoder)
    .with_context(|| format!("stream-decoding {}", path.display()))?;
    decoder
        .end()
        .with_context(|| format!("checking trailing data in {}", path.display()))?;
    Ok(summary)
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

struct DecimalParts<'a> {
    numerator_negative: bool,
    numerator_magnitude: &'a str,
    denominator_negative: bool,
    denominator_magnitude: &'a str,
}

fn decimal_magnitude<'a>(text: &'a str, label: &str) -> Result<(bool, &'a str)> {
    let text = text.trim();
    ensure!(!text.is_empty(), "{label} is empty");
    let (negative, magnitude) = match text.as_bytes()[0] {
        b'-' => (true, &text[1..]),
        b'+' => (false, &text[1..]),
        _ => (false, text),
    };
    ensure!(!magnitude.is_empty(), "{label} has no digits");
    ensure!(
        magnitude.bytes().all(|byte| byte.is_ascii_digit()),
        "{label} is not a decimal integer"
    );
    let canonical = magnitude.trim_start_matches('0');
    Ok((negative, if canonical.is_empty() { "0" } else { canonical }))
}

fn with_decimal_parts<T>(
    value: &Value,
    operation: impl FnOnce(DecimalParts<'_>) -> Result<T>,
) -> Result<T> {
    let owned;
    let text = match value {
        Value::String(value) => value.trim(),
        Value::Number(value) if value.is_i64() || value.is_u64() => {
            owned = value.to_string();
            owned.as_str()
        }
        _ => bail!("coefficient must be an exact integer or rational string"),
    };
    let (numerator, denominator) = match text.split_once('/') {
        Some((numerator, denominator)) => {
            ensure!(
                !denominator.contains('/'),
                "coefficient contains more than one slash"
            );
            (numerator, denominator)
        }
        None => (text, "1"),
    };
    let (numerator_negative, numerator_magnitude) =
        decimal_magnitude(numerator, "coefficient numerator")?;
    let (denominator_negative, denominator_magnitude) =
        decimal_magnitude(denominator, "coefficient denominator")?;
    ensure!(
        denominator_magnitude != "0",
        "coefficient denominator is zero"
    );
    operation(DecimalParts {
        numerator_negative,
        numerator_magnitude,
        denominator_negative,
        denominator_magnitude,
    })
}

fn parse_magnitude(magnitude: &str, label: &str) -> Result<BigInt> {
    BigInt::parse_bytes(magnitude.as_bytes(), 10)
        .with_context(|| format!("parsing {label} with {} decimal digits", magnitude.len()))
}

#[derive(Clone, Copy, Debug)]
struct CoefficientStats {
    numerator_digits_min: usize,
    numerator_digits_max: usize,
    denominator_digits_min: usize,
    denominator_digits_max: usize,
}

#[derive(Debug, Default)]
struct DenominatorScanner {
    first: Option<String>,
    lcm: Option<BigInt>,
    numerator_digits_min: Option<usize>,
    numerator_digits_max: usize,
    denominator_digits_min: Option<usize>,
    denominator_digits_max: usize,
}

impl DenominatorScanner {
    fn observe(&mut self, coefficient: &Value) -> Result<()> {
        with_decimal_parts(coefficient, |parts| {
            let denominator = parts.denominator_magnitude;
            self.numerator_digits_min = Some(
                self.numerator_digits_min
                    .map_or(parts.numerator_magnitude.len(), |current| {
                        current.min(parts.numerator_magnitude.len())
                    }),
            );
            self.numerator_digits_max = self
                .numerator_digits_max
                .max(parts.numerator_magnitude.len());
            self.denominator_digits_min = Some(
                self.denominator_digits_min
                    .map_or(denominator.len(), |current| current.min(denominator.len())),
            );
            self.denominator_digits_max = self.denominator_digits_max.max(denominator.len());
            match (&self.first, &mut self.lcm) {
                (None, _) => self.first = Some(denominator.to_owned()),
                (Some(first), None) if first == denominator => {}
                (Some(first), slot @ None) => {
                    let first = parse_magnitude(first, "first coefficient denominator")?;
                    let denominator = parse_magnitude(denominator, "coefficient denominator")?;
                    *slot = Some(first.lcm(&denominator));
                }
                (_, Some(current)) => {
                    let denominator = parse_magnitude(denominator, "coefficient denominator")?;
                    *current = current.lcm(&denominator);
                }
            }
            Ok(())
        })
    }

    fn finish(self) -> Result<DenominatorPlan> {
        let first = self
            .first
            .context("certificate has no coefficient denominators")?;
        let stats = CoefficientStats {
            numerator_digits_min: self
                .numerator_digits_min
                .context("certificate has no coefficient numerators")?,
            numerator_digits_max: self.numerator_digits_max,
            denominator_digits_min: self
                .denominator_digits_min
                .context("certificate has no coefficient denominators")?,
            denominator_digits_max: self.denominator_digits_max,
        };
        match self.lcm {
            Some(common_denominator) => Ok(DenominatorPlan {
                common_denominator,
                repeated_raw_denominator: None,
                stats,
            }),
            None => Ok(DenominatorPlan {
                common_denominator: parse_magnitude(&first, "common coefficient denominator")?,
                repeated_raw_denominator: Some(first),
                stats,
            }),
        }
    }
}

#[derive(Debug)]
struct DenominatorPlan {
    common_denominator: BigInt,
    repeated_raw_denominator: Option<String>,
    stats: CoefficientStats,
}

impl DenominatorPlan {
    fn scale(&self, coefficient: &Value) -> Result<ExactInt> {
        with_decimal_parts(coefficient, |parts| {
            let mut numerator =
                parse_magnitude(parts.numerator_magnitude, "coefficient numerator")?;
            if parts.numerator_negative ^ parts.denominator_negative {
                numerator = -numerator;
            }
            if let Some(repeated) = &self.repeated_raw_denominator {
                ensure!(
                    repeated == parts.denominator_magnitude,
                    "coefficient denominator changed between streaming passes"
                );
                return Ok(ExactInt::from_big(numerator));
            }
            let denominator =
                parse_magnitude(parts.denominator_magnitude, "coefficient denominator")?;
            let (scale, remainder) = self.common_denominator.div_rem(&denominator);
            ensure!(
                remainder.is_zero(),
                "common denominator is not divisible by term denominator"
            );
            Ok(ExactInt::from_big(numerator * scale))
        })
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
        match (&mut *self, coefficient) {
            (Self::Big(target), Self::Big(value)) if factor == 1 => *target += value,
            (Self::Big(target), Self::Big(value)) if factor == -1 => *target -= value,
            (Self::Big(target), Self::Big(value)) => *target += value * factor,
            (Self::Big(target), Self::Small(value)) => {
                if let Some(product) = value.checked_mul(i128::from(factor)) {
                    *target += product;
                } else {
                    *target += BigInt::from(*value) * factor;
                }
            }
            (Self::Small(target), Self::Big(value)) => {
                let mut sum = value * factor;
                sum += *target;
                *self = Self::from_big(sum);
            }
            (Self::Small(_), Self::Small(_)) => unreachable!("checked small path returned"),
        }
    }

    fn add_exact(&mut self, other: Self) {
        if let (Self::Small(target), Self::Small(value)) = (&mut *self, &other)
            && let Some(sum) = target.checked_add(*value)
        {
            *target = sum;
            return;
        }
        match (&mut *self, other) {
            (Self::Big(target), Self::Big(value)) => *target += value,
            (Self::Big(target), Self::Small(value)) => *target += value,
            (Self::Small(target), Self::Big(mut value)) => {
                value += *target;
                *self = Self::from_big(value);
            }
            (Self::Small(_), Self::Small(_)) => unreachable!("checked small path returned"),
        }
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
    ensure!(
        n <= MAX_LITERAL_N,
        "literal permutation mode is capped at n={MAX_LITERAL_N}"
    );
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
    pub coefficient_numerator_digits_min: usize,
    pub coefficient_numerator_digits_max: usize,
    pub coefficient_denominator_digits_min: usize,
    pub coefficient_denominator_digits_max: usize,
    pub repeated_coefficient_denominator: bool,
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

struct AnalysisFinish {
    n: usize,
    terms_total: usize,
    literal_check: bool,
    common_denominator: BigInt,
    coefficient_stats: CoefficientStats,
    repeated_coefficient_denominator: bool,
    total: PartialAccumulator,
    compute_wall_seconds: f64,
}

fn finish_analysis(input: AnalysisFinish) -> Result<Analysis> {
    let AnalysisFinish {
        n,
        terms_total,
        literal_check,
        common_denominator,
        coefficient_stats,
        repeated_coefficient_denominator,
        mut total,
        compute_wall_seconds,
    } = input;
    ensure!(
        total.terms_checked == terms_total,
        "term census mismatch: {}/{}",
        total.terms_checked,
        terms_total
    );
    total.linear[n - 1].add_exact(ExactInt::from_big(-&common_denominator));

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
        n,
        terms_total,
        nonzero_terms: total.nonzero_terms,
        dp_columns_checked: total.terms_checked,
        literal_dp_matches: total.literal_matches,
        permutations_per_literal_term: literal_check.then(|| checked_factorial(n)).transpose()?,
        coefficient_common_denominator: common_denominator.to_string(),
        coefficient_numerator_digits_min: coefficient_stats.numerator_digits_min,
        coefficient_numerator_digits_max: coefficient_stats.numerator_digits_max,
        coefficient_denominator_digits_min: coefficient_stats.denominator_digits_min,
        coefficient_denominator_digits_max: coefficient_stats.denominator_digits_max,
        repeated_coefficient_denominator,
        linear_rows: n,
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

pub fn analyze_certificate(
    certificate: &Certificate,
    threads: usize,
    literal_check: bool,
) -> Result<Analysis> {
    validate_n(certificate.n)?;
    ensure!((1..=64).contains(&threads), "threads must lie in 1..=64");
    ensure!(
        !literal_check || certificate.n <= MAX_LITERAL_N,
        "literal checks are capped at n={MAX_LITERAL_N}"
    );
    ensure!(!certificate.terms.is_empty(), "certificate has no terms");

    let mut scanner = DenominatorScanner::default();
    for (index, term) in certificate.terms.iter().enumerate() {
        let _ = parsed_sides(term, certificate.n)
            .with_context(|| format!("validating term {index}"))?;
        scanner
            .observe(&term.coefficient)
            .with_context(|| format!("scanning coefficient for term {index}"))?;
    }
    let plan = scanner.finish()?;
    let scaled: Vec<ExactInt> = certificate
        .terms
        .iter()
        .enumerate()
        .map(|(index, term)| {
            plan.scale(&term.coefficient)
                .with_context(|| format!("scaling coefficient for term {index}"))
        })
        .collect::<Result<_>>()?;

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let started = Instant::now();
    let total = pool.install(|| {
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
    let repeated_coefficient_denominator = plan.repeated_raw_denominator.is_some();
    finish_analysis(AnalysisFinish {
        n: certificate.n,
        terms_total: certificate.terms.len(),
        literal_check,
        common_denominator: plan.common_denominator,
        coefficient_stats: plan.stats,
        repeated_coefficient_denominator,
        total,
        compute_wall_seconds,
    })
}

struct PendingTerm {
    index: usize,
    term: Term,
    coefficient: ExactInt,
}

struct EvaluatedTerm {
    column: SparseColumn,
    coefficient: ExactInt,
    dp_seconds: f64,
    literal_seconds: f64,
}

fn evaluate_streaming_batch(
    pool: &rayon::ThreadPool,
    n: usize,
    literal_check: bool,
    batch: &mut Vec<PendingTerm>,
    total: &mut PartialAccumulator,
) -> Result<()> {
    if batch.is_empty() {
        return Ok(());
    }
    let pending = std::mem::take(batch);
    let evaluated = pool.install(|| {
        pending
            .into_par_iter()
            .map(|pending| -> Result<EvaluatedTerm> {
                let dp_started = Instant::now();
                let dynamic = dynamic_column(&pending.term, n)
                    .with_context(|| format!("dynamic evaluation of term {}", pending.index))?;
                let dp_seconds = dp_started.elapsed().as_secs_f64();
                let mut literal_seconds = 0.0;
                if literal_check {
                    let literal_started = Instant::now();
                    let literal = literal_column(&pending.term, n)
                        .with_context(|| format!("literal evaluation of term {}", pending.index))?;
                    literal_seconds = literal_started.elapsed().as_secs_f64();
                    compare_columns(pending.index, &dynamic, &literal)?;
                }
                Ok(EvaluatedTerm {
                    column: dynamic,
                    coefficient: pending.coefficient,
                    dp_seconds,
                    literal_seconds,
                })
            })
            .collect::<Result<Vec<_>>>()
    })?;
    for evaluated in evaluated {
        total.dp_worker_seconds += evaluated.dp_seconds;
        total.literal_worker_seconds += evaluated.literal_seconds;
        total.terms_checked += 1;
        if literal_check {
            total.literal_matches += 1;
        }
        if !evaluated.coefficient.is_zero() {
            total.nonzero_terms += 1;
            total.add_column(&evaluated.column, &evaluated.coefficient)?;
        }
    }
    Ok(())
}

/// Analyze a certificate with bounded input memory.
///
/// The file is streamed twice. Pass one validates terms and determines one
/// denominator clearing factor. Pass two parses at most `threads` terms at a
/// time, computes their structural columns in parallel, and accumulates their
/// scaled integer coefficients into one exact map. A repeated textual
/// denominator is parsed only once, which is the important dense-lift path.
pub fn analyze_certificate_path(
    path: &Path,
    threads: usize,
    literal_check: bool,
) -> Result<Analysis> {
    ensure!((1..=64).contains(&threads), "threads must lie in 1..=64");
    let started = Instant::now();
    let mut scanner = DenominatorScanner::default();
    let first = stream_certificate(path, |n, index, term| {
        validate_n(n)?;
        let _ = parsed_sides(&term, n).with_context(|| format!("validating term {index}"))?;
        scanner
            .observe(&term.coefficient)
            .with_context(|| format!("scanning coefficient for term {index}"))
    })?;
    validate_n(first.n)?;
    ensure!(
        !literal_check || first.n <= MAX_LITERAL_N,
        "literal checks are capped at n={MAX_LITERAL_N}"
    );
    ensure!(first.terms > 0, "certificate has no terms");
    let plan = scanner.finish()?;

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()?;
    let mut total = PartialAccumulator::new(first.n);
    let mut batch = Vec::with_capacity(threads);
    let second = stream_certificate(path, |n, index, term| {
        ensure!(
            n == first.n,
            "certificate n changed between streaming passes"
        );
        let coefficient = plan
            .scale(&term.coefficient)
            .with_context(|| format!("scaling coefficient for term {index}"))?;
        batch.push(PendingTerm {
            index,
            term,
            coefficient,
        });
        if batch.len() == threads {
            evaluate_streaming_batch(&pool, first.n, literal_check, &mut batch, &mut total)?;
        }
        Ok(())
    })?;
    evaluate_streaming_batch(&pool, first.n, literal_check, &mut batch, &mut total)?;
    ensure!(
        second == first,
        "certificate shape changed between streaming passes"
    );
    let compute_wall_seconds = started.elapsed().as_secs_f64();
    let repeated_coefficient_denominator = plan.repeated_raw_denominator.is_some();
    finish_analysis(AnalysisFinish {
        n: first.n,
        terms_total: first.terms,
        literal_check,
        common_denominator: plan.common_denominator,
        coefficient_stats: plan.stats,
        repeated_coefficient_denominator,
        total,
        compute_wall_seconds,
    })
}

pub fn certificate_shape(path: &Path) -> Result<(usize, usize)> {
    let summary = stream_certificate(path, |_, _, _| Ok(()))?;
    validate_n(summary.n)?;
    Ok((summary.n, summary.terms))
}

pub fn sample_certificate_path(path: &Path, indices: &[usize]) -> Result<Certificate> {
    ensure!(!indices.is_empty(), "sample indices must not be empty");
    ensure!(
        indices.windows(2).all(|pair| pair[0] < pair[1]),
        "sample indices must be strictly increasing"
    );
    let mut selected = Vec::with_capacity(indices.len());
    let mut next = 0usize;
    let summary = stream_certificate(path, |_, index, term| {
        if next < indices.len() && index == indices[next] {
            selected.push(term);
            next += 1;
        }
        Ok(())
    })?;
    validate_n(summary.n)?;
    ensure!(
        next == indices.len(),
        "sample index exceeds source term count: selected {next}/{}",
        indices.len()
    );
    Ok(Certificate {
        n: summary.n,
        terms: selected,
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
    fn boundary_straddling_certificate_promotes_big_target_small_product() {
        let boundary = BigInt::from(i128::MAX);
        let left = [[1, 1], [1, 2], [1, 2], [3, 5]];
        let right = [[2, 2], [1, 2], [2, 4], [4, 5]];
        let certificate = Certificate {
            n: 5,
            terms: vec![
                term(&(&boundary + 1u8).to_string(), &left, &right),
                term(&boundary.to_string(), &left, &right),
            ],
        };
        let mut scanner = DenominatorScanner::default();
        for term in &certificate.terms {
            scanner.observe(&term.coefficient).unwrap();
        }
        let plan = scanner.finish().unwrap();
        let scaled = certificate
            .terms
            .iter()
            .map(|term| plan.scale(&term.coefficient).unwrap())
            .collect::<Vec<_>>();
        assert!(matches!(&scaled[0], ExactInt::Big(_)));
        assert!(matches!(&scaled[1], ExactInt::Small(value) if *value == i128::MAX));

        let column = dynamic_column(&certificate.terms[0], certificate.n).unwrap();
        let (direction, factor) = column
            .hinges
            .iter()
            .find(|(_, factor)| factor.abs() > 1)
            .expect("fixture must have a hinge multiplicity whose product crosses i128");
        let mut accumulator = PartialAccumulator::new(certificate.n);
        for coefficient in &scaled {
            accumulator.add_column(&column, coefficient).unwrap();
        }
        let expected = (boundary * 2u8 + 1u8) * BigInt::from(*factor);
        assert_eq!(
            accumulator.hinges.get(direction).unwrap().to_bigint(),
            expected
        );
    }

    #[test]
    fn streaming_repeated_huge_denominator_preserves_an_exact_identity() {
        let denominator = BigInt::from(10u8).pow(200);
        let first_numerator = BigInt::from(10u8).pow(250);
        let second_numerator = &denominator / 2 - &first_numerator;
        let certificate = Certificate {
            n: 2,
            terms: vec![
                term(
                    &format!("{first_numerator}/{denominator}"),
                    &[[1, 1]],
                    &[[2, 2]],
                ),
                term(
                    &format!("{second_numerator}/{denominator}"),
                    &[[1, 1]],
                    &[[2, 2]],
                ),
            ],
        };
        let path = std::env::temp_dir().join(format!(
            "max11-verify11-streaming-control-{}.json",
            std::process::id()
        ));
        serde_json::to_writer(File::create(&path).unwrap(), &certificate).unwrap();
        let analysis = analyze_certificate_path(&path, 2, true).unwrap();
        std::fs::remove_file(path).unwrap();
        assert!(analysis.verified);
        assert_eq!(analysis.literal_dp_matches, 2);
        assert_eq!(
            analysis.coefficient_common_denominator,
            denominator.to_string()
        );
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
