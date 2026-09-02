use anyhow::{Context, Result, bail, ensure};
use max11_colgen::SparseColumn;
use num_bigint::{BigInt, Sign};
use num_integer::Integer;
use num_traits::{One, Signed, ToPrimitive, Zero};
use serde::Deserialize;
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap, HashSet};
use std::fs::{File, OpenOptions};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

pub const PRIMES: [u64; 2] = [1_000_003, 1_000_033];

#[derive(Debug, Deserialize)]
struct RawSeparator {
    schema: String,
    n: usize,
    linear_weights: Vec<Value>,
    hinge_weights: BTreeMap<String, Value>,
}

#[derive(Clone, Debug)]
enum ScaledInteger {
    Small(i128),
    Big(BigInt),
}

impl ScaledInteger {
    fn from_big(value: BigInt) -> Self {
        value
            .to_i128()
            .map(Self::Small)
            .unwrap_or_else(|| Self::Big(value))
    }

    fn residue(&self, prime: u64) -> u64 {
        match self {
            Self::Small(value) => value.rem_euclid(prime as i128) as u64,
            Self::Big(value) => big_residue(value, prime),
        }
    }
}

#[derive(Clone, Debug)]
pub enum ExactInteger {
    Small(i128),
    Big(BigInt),
}

impl ExactInteger {
    pub fn is_zero(&self) -> bool {
        match self {
            Self::Small(value) => *value == 0,
            Self::Big(value) => value.is_zero(),
        }
    }

    pub fn decimal(&self) -> String {
        match self {
            Self::Small(value) => value.to_string(),
            Self::Big(value) => value.to_string(),
        }
    }

    pub fn residue(&self, prime: u64) -> u64 {
        match self {
            Self::Small(value) => value.rem_euclid(prime as i128) as u64,
            Self::Big(value) => big_residue(value, prime),
        }
    }

    fn sign_magnitude(&self) -> (u8, Vec<u8>) {
        let value = match self {
            Self::Small(value) => BigInt::from(*value),
            Self::Big(value) => value.clone(),
        };
        let (sign, magnitude) = value.to_bytes_be();
        let tag = match sign {
            Sign::NoSign => 0,
            Sign::Plus => 1,
            Sign::Minus => 2,
        };
        (tag, magnitude)
    }
}

fn big_residue(value: &BigInt, prime: u64) -> u64 {
    value
        .mod_floor(&BigInt::from(prime))
        .to_u64()
        .expect("residue lies below u64 prime")
}

fn parse_integer(value: &str) -> Result<BigInt> {
    value
        .parse::<BigInt>()
        .with_context(|| format!("invalid integer {value:?}"))
}

fn parse_fraction(value: &Value) -> Result<(BigInt, BigInt)> {
    let text = match value {
        Value::String(text) => text.clone(),
        Value::Number(number) if number.is_i64() || number.is_u64() => number.to_string(),
        _ => bail!("separator coefficient must be an integer or rational string"),
    };
    let (mut numerator, mut denominator) = if let Some((left, right)) = text.split_once('/') {
        (parse_integer(left)?, parse_integer(right)?)
    } else {
        (parse_integer(&text)?, BigInt::one())
    };
    ensure!(
        !denominator.is_zero(),
        "separator coefficient has zero denominator"
    );
    if denominator.is_negative() {
        numerator = -numerator;
        denominator = -denominator;
    }
    let gcd = numerator.gcd(&denominator);
    Ok((numerator / &gcd, denominator / gcd))
}

fn parse_direction(raw: &str, n: usize) -> Result<Vec<i16>> {
    let direction = raw
        .split(',')
        .map(|part| {
            part.parse::<i16>()
                .with_context(|| format!("invalid hinge direction component {part:?}"))
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        direction.len() == n,
        "hinge direction length differs from n"
    );
    Ok(direction)
}

#[derive(Clone, Debug)]
pub struct CompiledSeparator {
    pub n: usize,
    pub denominator: BigInt,
    linear: Vec<ScaledInteger>,
    hinges: HashMap<Vec<i16>, ScaledInteger>,
}

impl CompiledSeparator {
    pub fn from_path(path: &Path) -> Result<Self> {
        let raw: RawSeparator = serde_json::from_reader(
            File::open(path).with_context(|| format!("opening separator {}", path.display()))?,
        )
        .with_context(|| format!("decoding separator {}", path.display()))?;
        Self::compile(raw)
    }

    fn compile(raw: RawSeparator) -> Result<Self> {
        ensure!(
            raw.schema == "max11-exact-sketch-separator-v1",
            "unsupported separator schema {}",
            raw.schema
        );
        ensure!(
            raw.linear_weights.len() == raw.n,
            "linear weight count differs from n"
        );
        let linear_rational = raw
            .linear_weights
            .iter()
            .map(parse_fraction)
            .collect::<Result<Vec<_>>>()?;
        let hinge_rational = raw
            .hinge_weights
            .iter()
            .map(|(key, value)| Ok((parse_direction(key, raw.n)?, parse_fraction(value)?)))
            .collect::<Result<Vec<_>>>()?;
        let denominator = linear_rational
            .iter()
            .map(|(_, denominator)| denominator)
            .chain(
                hinge_rational
                    .iter()
                    .map(|(_, (_, denominator))| denominator),
            )
            .fold(BigInt::one(), |lcm, denominator| lcm.lcm(denominator));
        let scale = |numerator: &BigInt, weight_denominator: &BigInt| {
            ScaledInteger::from_big(numerator * (&denominator / weight_denominator))
        };
        let linear = linear_rational
            .iter()
            .map(|(numerator, weight_denominator)| scale(numerator, weight_denominator))
            .collect();
        let hinges = hinge_rational
            .into_iter()
            .filter_map(|(direction, (numerator, weight_denominator))| {
                (!numerator.is_zero()).then(|| (direction, scale(&numerator, &weight_denominator)))
            })
            .collect();
        Ok(Self {
            n: raw.n,
            denominator,
            linear,
            hinges,
        })
    }

    pub fn denominator_text(&self) -> String {
        self.denominator.to_string()
    }

    pub fn start_price(&self) -> PriceAccumulator<'_> {
        PriceAccumulator {
            separator: self,
            exact: ExactInteger::Small(0),
            modular: [0, 0],
            promoted: false,
        }
    }

    pub fn price_sparse(&self, column: &SparseColumn) -> Result<PriceResult> {
        ensure!(
            column.linear.len() == self.n,
            "column linear dimension differs from separator"
        );
        let mut accumulator = self.start_price();
        for (rank, &coefficient) in column.linear.iter().enumerate() {
            accumulator.add_linear(rank, coefficient)?;
        }
        for (direction, &coefficient) in &column.hinges {
            accumulator.add_hinge(direction, coefficient)?;
        }
        accumulator.finish()
    }
}

pub struct PriceAccumulator<'a> {
    separator: &'a CompiledSeparator,
    exact: ExactInteger,
    modular: [u64; 2],
    promoted: bool,
}

impl PriceAccumulator<'_> {
    fn add_weighted(&mut self, weight: Option<&ScaledInteger>, coefficient: i64) {
        let Some(weight) = weight else { return };
        if coefficient == 0 {
            return;
        }
        for (position, prime) in PRIMES.into_iter().enumerate() {
            let coefficient_mod = (coefficient as i128).rem_euclid(prime as i128) as u64;
            let product = (coefficient_mod as u128 * weight.residue(prime) as u128) % prime as u128;
            self.modular[position] =
                ((self.modular[position] as u128 + product) % prime as u128) as u64;
        }
        match (&mut self.exact, weight) {
            (ExactInteger::Small(sum), ScaledInteger::Small(weight)) => {
                if let Some(product) = weight.checked_mul(coefficient as i128)
                    && let Some(updated) = sum.checked_add(product)
                {
                    *sum = updated;
                    return;
                }
                let updated = BigInt::from(*sum) + BigInt::from(*weight) * coefficient;
                self.exact = ExactInteger::Big(updated);
                self.promoted = true;
            }
            (ExactInteger::Small(sum), ScaledInteger::Big(weight)) => {
                self.exact = ExactInteger::Big(BigInt::from(*sum) + weight * coefficient);
                self.promoted = true;
            }
            (ExactInteger::Big(sum), ScaledInteger::Small(weight)) => {
                *sum += BigInt::from(*weight) * coefficient;
            }
            (ExactInteger::Big(sum), ScaledInteger::Big(weight)) => {
                *sum += weight * coefficient;
            }
        }
    }

    pub fn add_linear(&mut self, rank: usize, coefficient: i64) -> Result<()> {
        ensure!(rank < self.separator.n, "linear rank outside separator");
        self.add_weighted(self.separator.linear.get(rank), coefficient);
        Ok(())
    }

    pub fn add_hinge(&mut self, direction: &[i16], coefficient: i64) -> Result<()> {
        ensure!(
            direction.len() == self.separator.n,
            "hinge direction length differs from n"
        );
        self.add_weighted(self.separator.hinges.get(direction), coefficient);
        Ok(())
    }

    pub fn finish(self) -> Result<PriceResult> {
        for (position, prime) in PRIMES.into_iter().enumerate() {
            ensure!(
                self.exact.residue(prime) == self.modular[position],
                "exact/modular price mismatch at prime {prime}"
            );
        }
        Ok(PriceResult {
            exact: self.exact,
            modular: self.modular,
            promoted: self.promoted,
        })
    }
}

#[derive(Debug)]
pub struct PriceResult {
    pub exact: ExactInteger,
    pub modular: [u64; 2],
    pub promoted: bool,
}

#[derive(Debug)]
pub struct PriceSummary {
    pub evaluated: u64,
    pub annihilated: u64,
    pub violating: u64,
    pub promoted_columns: u64,
    pub vector_sha256: String,
    pub violators_sha256: String,
    pub violators_bytes: u64,
    pub modular_agreement: [u64; 2],
}

pub struct PriceWriter {
    denominator: BigInt,
    vector_hasher: Sha256,
    violator_path: PathBuf,
    violators: BufWriter<File>,
    seen: HashSet<u64>,
    evaluated: u64,
    annihilated: u64,
    violating: u64,
    promoted_columns: u64,
    modular_agreement: [u64; 2],
}

impl PriceWriter {
    pub fn create(n: usize, denominator: &BigInt, violator_path: &Path) -> Result<Self> {
        ensure!(
            denominator.is_positive(),
            "price denominator must be positive"
        );
        if let Some(parent) = violator_path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        let violators = BufWriter::new(
            OpenOptions::new()
                .write(true)
                .create_new(true)
                .open(violator_path)
                .with_context(|| format!("creating violator file {}", violator_path.display()))?,
        );
        let mut vector_hasher = Sha256::new();
        vector_hasher.update(b"MPRICEV1");
        vector_hasher.update((n as u16).to_le_bytes());
        let (_, denominator_bytes) = denominator.to_bytes_be();
        vector_hasher.update((denominator_bytes.len() as u64).to_le_bytes());
        vector_hasher.update(&denominator_bytes);
        Ok(Self {
            denominator: denominator.clone(),
            vector_hasher,
            violator_path: violator_path.to_path_buf(),
            violators,
            seen: HashSet::new(),
            evaluated: 0,
            annihilated: 0,
            violating: 0,
            promoted_columns: 0,
            modular_agreement: [0, 0],
        })
    }

    pub fn record(&mut self, source_index: u64, price: PriceResult) -> Result<()> {
        ensure!(
            self.seen.insert(source_index),
            "duplicate source index {source_index}"
        );
        self.evaluated += 1;
        self.promoted_columns += u64::from(price.promoted);
        self.vector_hasher.update(source_index.to_le_bytes());
        let (sign, magnitude) = price.exact.sign_magnitude();
        self.vector_hasher.update([sign]);
        self.vector_hasher
            .update((magnitude.len() as u64).to_le_bytes());
        self.vector_hasher.update(&magnitude);
        for (position, prime) in PRIMES.into_iter().enumerate() {
            ensure!(
                price.exact.residue(prime) == price.modular[position],
                "post-price modular mismatch at prime {prime}"
            );
            self.modular_agreement[position] += 1;
        }
        if price.exact.is_zero() {
            self.annihilated += 1;
        } else {
            self.violating += 1;
            serde_json::to_writer(
                &mut self.violators,
                &serde_json::json!({
                    "source_index": source_index,
                    "scaled_price": price.exact.decimal(),
                }),
            )?;
            self.violators.write_all(b"\n")?;
        }
        Ok(())
    }

    pub fn finish(mut self) -> Result<PriceSummary> {
        self.vector_hasher.update(b"ENDPV001");
        self.vector_hasher.update(self.evaluated.to_le_bytes());
        self.violators.flush()?;
        drop(self.violators);
        let metadata = std::fs::metadata(&self.violator_path)?;
        Ok(PriceSummary {
            evaluated: self.evaluated,
            annihilated: self.annihilated,
            violating: self.violating,
            promoted_columns: self.promoted_columns,
            vector_sha256: format!("{:x}", self.vector_hasher.finalize()),
            violators_sha256: sha256_path(&self.violator_path)?,
            violators_bytes: metadata.len(),
            modular_agreement: self.modular_agreement,
        })
    }

    pub fn denominator(&self) -> &BigInt {
        &self.denominator
    }
}

pub fn sha256_path(path: &Path) -> Result<String> {
    let mut input = File::open(path)?;
    let mut hasher = Sha256::new();
    std::io::copy(&mut input, &mut hasher)?;
    Ok(format!("{:x}", hasher.finalize()))
}

pub fn five_l_column(n: usize, branch_edges: usize) -> Result<SparseColumn> {
    ensure!(n >= 2, "5L carrier requires n >= 2");
    let factorial = (1..n).try_fold(1i64, |product, value| {
        product
            .checked_mul(value as i64)
            .context("5L factorial overflow")
    })?;
    let coefficient = i64::try_from(branch_edges)?
        .checked_mul(factorial)
        .context("5L carrier coefficient overflow")?;
    Ok(SparseColumn {
        linear: vec![coefficient; n],
        hinges: Default::default(),
    })
}

pub fn target_column(n: usize) -> Result<SparseColumn> {
    ensure!(n >= 1, "target requires n >= 1");
    let mut linear = vec![0; n];
    linear[n - 1] = 1;
    Ok(SparseColumn {
        linear,
        hinges: Default::default(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn separator(linear: &[Value], hinges: &[(&str, Value)]) -> CompiledSeparator {
        CompiledSeparator::compile(RawSeparator {
            schema: "max11-exact-sketch-separator-v1".to_owned(),
            n: linear.len(),
            linear_weights: linear.to_vec(),
            hinge_weights: hinges
                .iter()
                .map(|(key, value)| ((*key).to_owned(), value.clone()))
                .collect(),
        })
        .unwrap()
    }

    #[test]
    fn rational_scaling_and_modular_prices_agree() {
        let compiled = separator(
            &[Value::String("1/6".into()), Value::String("-5/14".into())],
            &[("1,-1", Value::String("2/3".into()))],
        );
        assert_eq!(compiled.denominator_text(), "42");
        let mut column = SparseColumn {
            linear: vec![3, 7],
            hinges: Default::default(),
        };
        column.hinges.insert(vec![1, -1], 11);
        let price = compiled.price_sparse(&column).unwrap();
        // 42 * (3/6 - 35/14 + 22/3) = 224.
        assert_eq!(price.exact.decimal(), "224");
        assert!(!price.promoted);
    }

    #[test]
    fn checked_i128_overflow_promotes_without_changing_value() {
        let huge_value = BigInt::from(i128::MAX) - BigInt::one();
        let huge = huge_value.to_string();
        let compiled = separator(&[Value::String(huge)], &[]);
        let price = compiled
            .price_sparse(&SparseColumn {
                linear: vec![3],
                hinges: Default::default(),
            })
            .unwrap();
        assert_eq!(
            price.exact.decimal(),
            (huge_value * BigInt::from(3)).to_string()
        );
        assert!(price.promoted);
    }

    #[test]
    fn unknown_hinge_has_zero_weight_and_dimension_is_checked() {
        let compiled = separator(&[Value::from(1), Value::from(0)], &[]);
        let mut column = SparseColumn {
            linear: vec![4, 5],
            hinges: Default::default(),
        };
        column.hinges.insert(vec![1, -1], 99);
        let price = compiled.price_sparse(&column).unwrap();
        assert_eq!(price.exact.decimal(), "4");
        let bad = SparseColumn {
            linear: vec![1],
            hinges: Default::default(),
        };
        assert!(compiled.price_sparse(&bad).is_err());
    }

    #[test]
    fn five_l_and_target_match_streamrank_conventions() {
        let five_l = five_l_column(11, 5).unwrap();
        assert_eq!(five_l.linear, vec![18_144_000; 11]);
        assert!(five_l.hinges.is_empty());
        let target = target_column(11).unwrap();
        assert_eq!(target.linear, vec![0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]);
        assert!(target.hinges.is_empty());
    }
}
