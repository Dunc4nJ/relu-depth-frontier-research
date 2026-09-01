use anyhow::{Context, Result, ensure};
use g0179_star_loop_pricer::{N, NormalForm, Record, full_normal_form};
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::{Value, json};
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet};
use std::fs::{File, read};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use std::time::Instant;

const EXECUTION_FLAG: &str = "--execute-frozen-scan";
const VALIDATION_FLAG: &str = "--validate-frozen-inputs";
const EXPECTED_BASIS_JSONL_SHA256: &str =
    "7870fde3d67eb8eba0eaa10b924a4f8a717f9aa9e9e56acc54411c716edc2385";
const EXPECTED_BASIS_BINARY_SHA256: &str =
    "bc949c3f95da084ab71d7c3aeea35469bb638fcea1ac0602bdb407aae6c3c798";
const EXPECTED_G0190_CERTIFICATE_SHA256: &str =
    "1b1561f74ba266b9ddd72906dbc4f42c4222e56fd1a219c1f88c8f22a19ec055";
const EXPECTED_G0189_RESULT_SHA256: &str =
    "e90a79984c0dd7c582ca9dbbcb7f73b08c0c1505d0597bfcd98d44361ded8005";
const EXPECTED_STAR_SHA256: &str =
    "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4";
const EXPECTED_EXPANSION_RECEIPT_SHA256: &str =
    "6e7d58666b9a58d1ea68141595bdd1404a519f10e7f47068166c7d7a290864d5";
const EXPECTED_G0179_LIB_SHA256: &str =
    "8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73";
const EXPECTED_SOURCE_CANDIDATE_SHA256: &str =
    "24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe";
const EXPECTED_EXCLUDED_SEQUENCES: [usize; 4] = [1548, 3140, 4259, 5656];
const EXPECTED_OLD_BASIS_COLUMNS: [usize; 42] = [
    0, 1, 12, 15, 17, 21, 24, 28, 62, 68, 72, 75, 82, 87, 90, 91, 108, 117, 121, 122, 132, 135,
    148, 161, 215, 220, 226, 232, 235, 240, 241, 242, 246, 250, 271, 272, 273, 277, 280, 282, 283,
    352,
];
const EXPECTED_G0189_OLD_BASIS_COLUMNS: [usize; 17] = [
    12, 15, 17, 21, 24, 28, 68, 72, 75, 82, 87, 90, 91, 108, 117, 121, 122,
];
const EXPECTED_LOWMASS_TRANCHE_COLUMNS: [usize; 3] = [0, 1, 8];
const EXPECTED_G0189_TRANCHE_COLUMNS: [usize; 17] =
    [2, 3, 4, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19];
const EXPECTED_SELECTED_TRANCHE_COLUMNS: [usize; 23] = [
    20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42,
];
const BASIS_ROWS: usize = 5769;
const BASIS_COLUMNS: usize = 43;
const EXPECTED_SELECTED_INCIDENCES: usize = 442;
const EXPECTED_SELECTED_UNIQUE_RECORDS: usize = 262;
const EXPECTED_SELECTED_SUM_ABS_COEFFICIENTS: i128 = 498;
const EXPECTED_SELECTED_MAX_ABS_COEFFICIENT: i128 = 3;
const EXPECTED_SELECTED_MAX_L1: i128 = 76;
const HOSTILE_DIFFERENCE_MAX_L1: i128 = 2 * EXPECTED_SELECTED_MAX_L1 + 1;

#[derive(Debug, Deserialize)]
struct BasisHeader {
    ambient_matrix_shape: [usize; 2],
    basis_shape: [usize; 2],
    binary_i64le_sha256: String,
    max_signed_mass_histogram: BTreeMap<String, usize>,
    row_to_sequence: String,
    schema: String,
    source_candidate_sha256: String,
    term_encoding: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(tag = "kind")]
enum Origin {
    #[serde(rename = "sparse_basis_column")]
    SparseBasisColumn { basis_column: usize },
    #[serde(rename = "exact_basis_combination")]
    ExactBasisCombination {
        formula: String,
        old_basis_coefficients: BTreeMap<String, String>,
    },
}

#[derive(Clone, Debug, Deserialize, Serialize)]
struct Relation {
    tranche_column: usize,
    origin: Origin,
    support: usize,
    max_signed_mass: usize,
    signed_mass_histogram: BTreeMap<String, usize>,
    terms: Vec<(usize, usize, String)>,
}

#[derive(Debug, Deserialize)]
struct StarDocument {
    schema: String,
    records: Vec<Record>,
}

#[derive(Clone, Debug, Eq, PartialEq, Serialize)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
struct ExactResidual {
    linear: [i128; N],
    hinges: BTreeMap<[i8; N], i128>,
}

impl Default for ExactResidual {
    fn default() -> Self {
        Self {
            linear: [0; N],
            hinges: BTreeMap::new(),
        }
    }
}

#[derive(Clone, Debug, Serialize)]
struct ResidualBinding {
    linear: [String; N],
    hinges: Vec<ExactHinge>,
}

#[derive(Debug, Serialize)]
struct LinearWitness {
    coordinate: usize,
    coefficient: String,
}

#[derive(Debug, Serialize)]
struct RelationResult {
    tranche_column: usize,
    origin: Origin,
    terms: Vec<(usize, String)>,
    support: usize,
    sum_abs_coefficients: String,
    classification: &'static str,
    residual_linear: [String; N],
    residual_nonzero_linear_coordinates: usize,
    first_nonzero_linear: Option<LinearWitness>,
    residual_nonzero_hinges: usize,
    residual_d0_eq_zero_hinges: usize,
    residual_d0_not_zero_hinges: usize,
    complete_residual_sha256: String,
    d0_not_zero_residual_sha256: String,
    first_nonzero_hinge: Option<ExactHinge>,
    first_d0_not_zero_hinge: Option<ExactHinge>,
}

#[derive(Debug, Serialize)]
struct NormalFormBinding {
    active_vertices: usize,
    hinge_direction_count: usize,
    normal_form_sha256: String,
    sequence: usize,
}

fn sha256_bytes(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let mut output = String::with_capacity(64);
    for byte in digest {
        use std::fmt::Write as _;
        write!(&mut output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

fn canonical_json_sha256<T: Serialize>(value: &T) -> Result<String> {
    Ok(sha256_bytes(&serde_json::to_vec(value)?))
}

fn read_bound(path: &Path, expected_sha256: &str, label: &str) -> Result<Vec<u8>> {
    let bytes = read(path).with_context(|| format!("reading {label} at {}", path.display()))?;
    let observed = sha256_bytes(&bytes);
    ensure!(
        observed == expected_sha256,
        "{label} SHA-256 drift: expected {expected_sha256}, observed {observed}"
    );
    Ok(bytes)
}

fn parse_basis(bytes: &[u8]) -> Result<(BasisHeader, Vec<Relation>)> {
    let text = std::str::from_utf8(bytes).context("basis JSONL is not UTF-8")?;
    let mut lines = text.lines();
    let header: BasisHeader =
        serde_json::from_str(lines.next().context("basis JSONL lacks header")?)
            .context("parsing basis header")?;
    let relations = lines
        .enumerate()
        .map(|(index, line)| {
            let relation: Relation = serde_json::from_str(line)
                .with_context(|| format!("parsing basis relation line {}", index + 2))?;
            ensure!(
                relation.tranche_column == index,
                "tranche-column order drift at line {}",
                index + 2
            );
            ensure!(
                relation.support == relation.terms.len(),
                "serialized support mismatch at tranche column {}",
                relation.tranche_column
            );
            Ok(relation)
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        relations.len() == BASIS_COLUMNS,
        "basis relation count drift"
    );
    Ok((header, relations))
}

fn retained_records(document: StarDocument) -> Result<Vec<Record>> {
    ensure!(
        document.schema == "g0179.star-outside-primary-loop-records.v1",
        "STAR record schema drift"
    );
    ensure!(document.records.len() == 5773, "STAR record count drift");
    ensure!(
        document
            .records
            .iter()
            .enumerate()
            .all(|(index, record)| index == record.sequence),
        "STAR records are not in exact sequence order"
    );
    let excluded = EXPECTED_EXCLUDED_SEQUENCES
        .into_iter()
        .collect::<BTreeSet<_>>();
    let retained = document
        .records
        .into_iter()
        .filter(|record| !excluded.contains(&record.sequence))
        .collect::<Vec<_>>();
    ensure!(retained.len() == BASIS_ROWS, "retained STAR count drift");
    Ok(retained)
}

fn validate_basis_header(header: &BasisHeader) -> Result<()> {
    ensure!(
        header.schema == "g0193.filtration-adapted-mass-le4-kernel-basis.v1",
        "basis schema drift"
    );
    ensure!(
        header.ambient_matrix_shape == [BASIS_ROWS, 6795],
        "ambient matrix shape drift"
    );
    ensure!(
        header.basis_shape == [BASIS_ROWS, BASIS_COLUMNS],
        "basis shape drift"
    );
    ensure!(
        header.binary_i64le_sha256 == EXPECTED_BASIS_BINARY_SHA256,
        "basis header binary binding drift"
    );
    ensure!(
        header.source_candidate_sha256 == EXPECTED_SOURCE_CANDIDATE_SHA256,
        "basis source-candidate binding drift"
    );
    ensure!(
        header.row_to_sequence == "r-th element of sorted([0..5772] minus {1548,3140,4259,5656})",
        "basis row-to-sequence statement drift"
    );
    ensure!(
        header.term_encoding
            == "[output_row, record_sequence, primitive_integer_coefficient_as_decimal_string]",
        "basis term encoding drift"
    );
    ensure!(
        header.max_signed_mass_histogram
            == BTreeMap::from([("3".to_owned(), 3), ("4".to_owned(), 40)]),
        "basis max-mass histogram drift"
    );
    Ok(())
}

fn validate_g0190_certificate(bytes: &[u8]) -> Result<()> {
    let receipt: Value = serde_json::from_slice(bytes).context("parsing G-0190 certificate")?;
    ensure!(
        receipt["schema"] == "g0193.mass-le4-filtration-final-certificate.v1",
        "G-0190 certificate schema drift"
    );
    ensure!(
        receipt["result"]
            == "COMPLETE_EXACT_43_DIMENSIONAL_MASS_LE4_KERNEL_BASIS_WITH_GLOBAL_COSET_SUPPORT_MINIMUM",
        "G-0190 certificate result drift"
    );
    ensure!(
        receipt["bindings"]["basis_binary"]["sha256"] == EXPECTED_BASIS_BINARY_SHA256,
        "G-0190 binary binding drift"
    );
    ensure!(
        receipt["bindings"]["basis_sparse_jsonl"]["sha256"] == EXPECTED_BASIS_JSONL_SHA256,
        "G-0190 sparse-basis binding drift"
    );
    ensure!(
        receipt["bindings"]["basis_sparse_jsonl"]["records"] == BASIS_COLUMNS,
        "G-0190 sparse-basis record count drift"
    );
    ensure!(
        receipt["dimension_sandwich"]["exact_independent_null_vectors"] == BASIS_COLUMNS,
        "G-0190 independence count drift"
    );
    ensure!(
        receipt["dimension_sandwich"]["exact_nullity"] == BASIS_COLUMNS,
        "G-0190 exact nullity drift"
    );
    ensure!(
        receipt["mass_tranche"]["vectors"] == BASIS_COLUMNS,
        "G-0190 tranche vector count drift"
    );
    ensure!(
        receipt["mass_tranche"]["genuinely_mass4_vectors"] == 40,
        "G-0190 mass-four vector count drift"
    );
    Ok(())
}

fn validate_expansion_receipt(bytes: &[u8]) -> Result<()> {
    let receipt: Value = serde_json::from_slice(bytes).context("parsing G-0180 receipt")?;
    ensure!(
        receipt["schema"] == "g0180.quotient-expansion-price-matrix.v1",
        "G-0180 receipt schema drift"
    );
    ensure!(
        receipt["bindings"]["records_sha256"] == EXPECTED_STAR_SHA256,
        "G-0180 receipt STAR binding drift"
    );
    ensure!(
        receipt["bindings"]["source"]["g0179_dependency_lib_sha256"] == EXPECTED_G0179_LIB_SHA256,
        "G-0180 receipt G-0179 dependency binding drift"
    );
    ensure!(
        receipt["quotient_records"]["available"] == 5773,
        "available record count drift"
    );
    ensure!(
        receipt["quotient_records"]["retained"] == BASIS_ROWS,
        "retained record count drift"
    );
    let excluded: Vec<usize> =
        serde_json::from_value(receipt["quotient_records"]["excluded_sequences_exactly"].clone())?;
    ensure!(
        excluded == EXPECTED_EXCLUDED_SEQUENCES,
        "G-0180 excluded sequence drift"
    );
    Ok(())
}

fn validate_g0189_result(bytes: &[u8]) -> Result<BTreeSet<usize>> {
    let receipt: Value = serde_json::from_slice(bytes).context("parsing G-0189 result")?;
    ensure!(
        receipt["schema"] == "g0189.mass4-complete-normal-form-d0-scan.v1",
        "G-0189 result schema drift"
    );
    ensure!(
        receipt["result"] == "NO_D0_NONZERO_HINGE_IN_SELECTED_RELATIONS",
        "G-0189 top-level result drift"
    );
    let columns: Vec<usize> =
        serde_json::from_value(receipt["selection"]["basis_columns"].clone())?;
    ensure!(
        columns == EXPECTED_G0189_OLD_BASIS_COLUMNS,
        "G-0189 selected old-basis columns drift"
    );
    let relation_results = receipt["relations"]
        .as_array()
        .context("G-0189 result lacks relation array")?;
    ensure!(relation_results.len() == 17, "G-0189 relation count drift");
    for (relation, expected_column) in relation_results
        .iter()
        .zip(EXPECTED_G0189_OLD_BASIS_COLUMNS)
    {
        ensure!(
            relation["basis_column"] == expected_column,
            "G-0189 relation order drift"
        );
        ensure!(
            relation["residual_nonzero_hinges"] == 0,
            "G-0189 relation is not a complete zero-hinge identity"
        );
        let linear = relation["residual_linear"]
            .as_array()
            .context("G-0189 relation lacks residual linear array")?;
        ensure!(
            linear.len() == N && linear.iter().all(|value| value == "0"),
            "G-0189 relation is not a complete zero-linear identity"
        );
    }
    Ok(columns.into_iter().collect())
}

fn parse_coefficient(text: &str, context: &str) -> Result<i128> {
    let coefficient = text
        .parse::<i128>()
        .with_context(|| format!("parsing coefficient {text} at {context}"))?;
    ensure!(coefficient != 0, "zero coefficient serialized at {context}");
    Ok(coefficient)
}

fn validate_relations_and_binary(
    relations: &[Relation],
    retained: &[Record],
    binary: &[u8],
) -> Result<()> {
    ensure!(
        binary.len() == BASIS_ROWS * BASIS_COLUMNS * std::mem::size_of::<i64>(),
        "basis binary length drift"
    );
    let mut expected = vec![0i64; BASIS_ROWS * BASIS_COLUMNS];
    for relation in relations {
        let mut rows = BTreeSet::new();
        let mut observed_histogram = BTreeMap::<String, usize>::new();
        let mut observed_max_mass = 0usize;
        for (term_index, &(output_row, sequence, ref coefficient_text)) in
            relation.terms.iter().enumerate()
        {
            ensure!(output_row < BASIS_ROWS, "basis term row out of range");
            ensure!(
                rows.insert(output_row),
                "duplicate output row at tranche column {}",
                relation.tranche_column
            );
            ensure!(
                retained[output_row].sequence == sequence,
                "row-to-sequence mismatch at tranche column {}, term {}",
                relation.tranche_column,
                term_index
            );
            let coefficient = parse_coefficient(
                coefficient_text,
                &format!(
                    "tranche column {}, term {term_index}",
                    relation.tranche_column
                ),
            )?;
            let coefficient_i64 =
                i64::try_from(coefficient).context("basis coefficient exceeds i64")?;
            expected[output_row * BASIS_COLUMNS + relation.tranche_column] = coefficient_i64;
            let mass = retained[output_row].signed_mass;
            observed_max_mass = observed_max_mass.max(mass);
            *observed_histogram.entry(mass.to_string()).or_default() += 1;
        }
        ensure!(
            observed_max_mass == relation.max_signed_mass,
            "max signed mass drift at tranche column {}",
            relation.tranche_column
        );
        ensure!(
            observed_histogram == relation.signed_mass_histogram,
            "signed-mass histogram drift at tranche column {}",
            relation.tranche_column
        );
    }
    for (index, chunk) in binary.chunks_exact(8).enumerate() {
        let observed = i64::from_le_bytes(chunk.try_into().expect("chunks_exact yields 8 bytes"));
        ensure!(
            observed == expected[index],
            "sparse/binary basis mismatch at row {}, tranche column {}",
            index / BASIS_COLUMNS,
            index % BASIS_COLUMNS
        );
    }
    Ok(())
}

fn validate_origins_and_select(
    relations: &[Relation],
    classified_old_columns: &BTreeSet<usize>,
) -> Result<Vec<Relation>> {
    ensure!(
        classified_old_columns
            == &EXPECTED_G0189_OLD_BASIS_COLUMNS
                .into_iter()
                .collect::<BTreeSet<_>>(),
        "classified old-basis set drift"
    );
    for (tranche_column, expected_old_column) in EXPECTED_OLD_BASIS_COLUMNS.into_iter().enumerate()
    {
        match relations[tranche_column].origin {
            Origin::SparseBasisColumn { basis_column } => ensure!(
                basis_column == expected_old_column,
                "old-basis origin drift at tranche column {tranche_column}"
            ),
            Origin::ExactBasisCombination { .. } => {
                anyhow::bail!("unexpected exact-combination origin before tranche column 42")
            }
        }
    }
    match &relations[42].origin {
        Origin::ExactBasisCombination {
            formula,
            old_basis_coefficients,
        } => {
            ensure!(
                formula == "B_24 + B_174 + B_235 - B_295 + B_345",
                "optimized basis formula drift"
            );
            ensure!(
                old_basis_coefficients
                    == &BTreeMap::from([
                        ("174".to_owned(), "1".to_owned()),
                        ("235".to_owned(), "1".to_owned()),
                        ("24".to_owned(), "1".to_owned()),
                        ("295".to_owned(), "-1".to_owned()),
                        ("345".to_owned(), "1".to_owned()),
                    ]),
                "optimized old-basis coefficients drift"
            );
        }
        Origin::SparseBasisColumn { .. } => anyhow::bail!("optimized basis origin drift"),
    }

    let lowmass_columns = relations
        .iter()
        .filter(|relation| relation.max_signed_mass < 4)
        .map(|relation| relation.tranche_column)
        .collect::<Vec<_>>();
    ensure!(
        lowmass_columns == EXPECTED_LOWMASS_TRANCHE_COLUMNS,
        "low-mass tranche-column set drift"
    );
    let mapped_g0189_columns = relations
        .iter()
        .filter_map(|relation| match relation.origin {
            Origin::SparseBasisColumn { basis_column }
                if classified_old_columns.contains(&basis_column) =>
            {
                Some(relation.tranche_column)
            }
            _ => None,
        })
        .collect::<Vec<_>>();
    ensure!(
        mapped_g0189_columns == EXPECTED_G0189_TRANCHE_COLUMNS,
        "G-0189-to-filtration column mapping drift"
    );

    let selected = relations
        .iter()
        .filter(|relation| {
            relation.max_signed_mass == 4
                && match relation.origin {
                    Origin::SparseBasisColumn { basis_column } => {
                        !classified_old_columns.contains(&basis_column)
                    }
                    Origin::ExactBasisCombination { .. } => true,
                }
        })
        .cloned()
        .collect::<Vec<_>>();
    let selected_columns = selected
        .iter()
        .map(|relation| relation.tranche_column)
        .collect::<Vec<_>>();
    ensure!(
        selected_columns == EXPECTED_SELECTED_TRANCHE_COLUMNS,
        "selected tranche-column drift"
    );

    let incidence_count = selected
        .iter()
        .map(|relation| relation.terms.len())
        .sum::<usize>();
    let unique_records = selected
        .iter()
        .flat_map(|relation| relation.terms.iter().map(|term| term.1))
        .collect::<BTreeSet<_>>();
    let mut support_histogram = BTreeMap::<usize, usize>::new();
    let mut max_abs_coefficient = 0i128;
    let mut total_abs_coefficient = 0i128;
    let mut maximum_relation_l1 = 0i128;
    let mut nonunit_incidences = 0usize;
    for relation in &selected {
        let mut relation_l1 = 0i128;
        for (term_index, term) in relation.terms.iter().enumerate() {
            let coefficient = parse_coefficient(
                &term.2,
                &format!(
                    "selected tranche column {}, term {term_index}",
                    relation.tranche_column
                ),
            )?;
            let magnitude = coefficient
                .checked_abs()
                .context("selected coefficient absolute-value overflow")?;
            max_abs_coefficient = max_abs_coefficient.max(magnitude);
            relation_l1 = relation_l1
                .checked_add(magnitude)
                .context("selected relation l1 overflow")?;
            if magnitude != 1 {
                nonunit_incidences += 1;
            }
        }
        total_abs_coefficient = total_abs_coefficient
            .checked_add(relation_l1)
            .context("selected total l1 overflow")?;
        maximum_relation_l1 = maximum_relation_l1.max(relation_l1);
        *support_histogram.entry(relation.support).or_default() += 1;
    }
    ensure!(
        incidence_count == EXPECTED_SELECTED_INCIDENCES,
        "selected incidence count drift"
    );
    ensure!(
        unique_records.len() == EXPECTED_SELECTED_UNIQUE_RECORDS,
        "selected unique-record count drift"
    );
    ensure!(
        support_histogram
            == BTreeMap::from([
                (8, 1),
                (10, 1),
                (12, 2),
                (16, 9),
                (17, 1),
                (18, 4),
                (22, 2),
                (24, 1),
                (34, 1),
                (65, 1),
            ]),
        "selected support histogram drift"
    );
    ensure!(
        max_abs_coefficient == EXPECTED_SELECTED_MAX_ABS_COEFFICIENT,
        "selected maximum coefficient drift"
    );
    ensure!(
        total_abs_coefficient == EXPECTED_SELECTED_SUM_ABS_COEFFICIENTS,
        "selected aggregate l1 drift"
    );
    ensure!(
        maximum_relation_l1 == EXPECTED_SELECTED_MAX_L1,
        "selected maximum relation l1 drift"
    );
    ensure!(
        nonunit_incidences == 53,
        "selected non-unit incidence drift"
    );
    Ok(selected)
}

fn checked_add_scaled_form(
    residual: &mut ExactResidual,
    normal: &NormalForm,
    coefficient: i128,
) -> Result<()> {
    for (coordinate, (target, &value)) in residual.linear.iter_mut().zip(&normal.linear).enumerate()
    {
        let product = coefficient
            .checked_mul(i128::from(value))
            .with_context(|| {
                format!("linear multiplication overflow at coordinate {coordinate}")
            })?;
        *target = target
            .checked_add(product)
            .with_context(|| format!("linear accumulation overflow at coordinate {coordinate}"))?;
    }
    for hinge in &normal.hinges {
        let product = coefficient
            .checked_mul(i128::from(hinge.coefficient))
            .context("hinge multiplication overflow")?;
        let current = residual
            .hinges
            .get(&hinge.direction)
            .copied()
            .unwrap_or_default();
        let updated = current
            .checked_add(product)
            .context("hinge accumulation overflow")?;
        if updated == 0 {
            residual.hinges.remove(&hinge.direction);
        } else {
            residual.hinges.insert(hinge.direction, updated);
        }
    }
    Ok(())
}

fn aggregate_relation(
    relation: &Relation,
    forms: &BTreeMap<usize, NormalForm>,
    plus_one_first_atom: bool,
) -> Result<ExactResidual> {
    let mut residual = ExactResidual::default();
    for (term_index, &(_, sequence, ref coefficient_text)) in relation.terms.iter().enumerate() {
        let mut coefficient = parse_coefficient(
            coefficient_text,
            &format!(
                "tranche column {}, term {term_index}",
                relation.tranche_column
            ),
        )?;
        if plus_one_first_atom && term_index == 0 {
            coefficient = coefficient
                .checked_add(1)
                .context("hostile coefficient overflow")?;
        }
        let normal = forms
            .get(&sequence)
            .with_context(|| format!("missing normal form q{sequence}"))?;
        checked_add_scaled_form(&mut residual, normal, coefficient)?;
    }
    Ok(residual)
}

fn checked_difference(left: &ExactResidual, right: &ExactResidual) -> Result<ExactResidual> {
    let mut difference = left.clone();
    for (coordinate, (target, &value)) in
        difference.linear.iter_mut().zip(&right.linear).enumerate()
    {
        *target = target
            .checked_sub(value)
            .with_context(|| format!("linear subtraction overflow at coordinate {coordinate}"))?;
    }
    for (&direction, &value) in &right.hinges {
        let current = difference
            .hinges
            .get(&direction)
            .copied()
            .unwrap_or_default();
        let updated = current
            .checked_sub(value)
            .context("hinge subtraction overflow")?;
        if updated == 0 {
            difference.hinges.remove(&direction);
        } else {
            difference.hinges.insert(direction, updated);
        }
    }
    Ok(difference)
}

fn residual_binding(residual: &ExactResidual) -> ResidualBinding {
    ResidualBinding {
        linear: residual.linear.map(|value| value.to_string()),
        hinges: residual
            .hinges
            .iter()
            .map(|(&direction, &coefficient)| ExactHinge {
                direction,
                coefficient: coefficient.to_string(),
            })
            .collect(),
    }
}

fn relation_result(relation: &Relation, residual: &ExactResidual) -> Result<RelationResult> {
    let binding = residual_binding(residual);
    let nonzero_linear = binding
        .linear
        .iter()
        .filter(|coefficient| coefficient.as_str() != "0")
        .count();
    let d0_not_zero = binding
        .hinges
        .iter()
        .filter(|hinge| hinge.direction[0] != 0)
        .cloned()
        .collect::<Vec<_>>();
    ensure!(
        d0_not_zero.iter().all(|hinge| hinge.direction[0] > 0),
        "canonical direction orientation drift at d[0]"
    );
    let classification = if nonzero_linear == 0 && binding.hinges.is_empty() {
        "EXACT_ZERO_IDENTITY"
    } else if d0_not_zero.is_empty() {
        "NONZERO_RESIDUAL_WITH_D0_ZERO_HINGES_ONLY"
    } else {
        "D0_NONZERO_HINGE_LEAKAGE"
    };
    let first_nonzero_linear = binding
        .linear
        .iter()
        .enumerate()
        .find(|(_, coefficient)| coefficient.as_str() != "0")
        .map(|(coordinate, coefficient)| LinearWitness {
            coordinate,
            coefficient: coefficient.clone(),
        });
    let sum_abs_coefficients =
        relation
            .terms
            .iter()
            .enumerate()
            .try_fold(0i128, |sum, (term_index, term)| {
                let coefficient = parse_coefficient(
                    &term.2,
                    &format!(
                        "result tranche column {}, term {term_index}",
                        relation.tranche_column
                    ),
                )?;
                sum.checked_add(
                    coefficient
                        .checked_abs()
                        .context("result coefficient absolute-value overflow")?,
                )
                .context("result l1 overflow")
            })?;
    Ok(RelationResult {
        tranche_column: relation.tranche_column,
        origin: relation.origin.clone(),
        terms: relation
            .terms
            .iter()
            .map(|term| (term.1, term.2.clone()))
            .collect(),
        support: relation.support,
        sum_abs_coefficients: sum_abs_coefficients.to_string(),
        classification,
        residual_linear: binding.linear.clone(),
        residual_nonzero_linear_coordinates: nonzero_linear,
        first_nonzero_linear,
        residual_nonzero_hinges: binding.hinges.len(),
        residual_d0_eq_zero_hinges: binding.hinges.len() - d0_not_zero.len(),
        residual_d0_not_zero_hinges: d0_not_zero.len(),
        complete_residual_sha256: canonical_json_sha256(&binding)?,
        d0_not_zero_residual_sha256: canonical_json_sha256(&d0_not_zero)?,
        first_nonzero_hinge: binding.hinges.first().cloned(),
        first_d0_not_zero_hinge: d0_not_zero.first().cloned(),
    })
}

#[derive(Debug, Serialize)]
struct HostileControl {
    tranche_column: usize,
    added_sequence: usize,
    added_atom_nonzero_linear_coordinates: usize,
    added_atom_nonzero_hinges: usize,
    added_atom_d0_not_zero_hinges: usize,
    exact_complete_delta_sha256: String,
    delta_equals_added_atom_complete_normal_form: bool,
    mutation_changes_complete_residual: bool,
}

fn hostile_controls(
    selected: &[Relation],
    originals: &[ExactResidual],
    forms: &BTreeMap<usize, NormalForm>,
) -> Result<Vec<HostileControl>> {
    ensure!(
        selected.len() == originals.len(),
        "hostile-control relation/result count mismatch"
    );
    selected
        .iter()
        .zip(originals)
        .map(|(relation, original)| {
            let mutant = aggregate_relation(relation, forms, true)?;
            let delta = checked_difference(&mutant, original)?;
            let added_sequence = relation.terms[0].1;
            let added_form = forms
                .get(&added_sequence)
                .with_context(|| format!("hostile added form q{added_sequence} absent"))?;
            let mut expected_delta = ExactResidual::default();
            checked_add_scaled_form(&mut expected_delta, added_form, 1)?;
            ensure!(
                delta == expected_delta,
                "hostile +1 complete delta mismatch at tranche column {}",
                relation.tranche_column
            );
            ensure!(
                mutant != *original,
                "hostile +1 mutation did not change tranche column {}",
                relation.tranche_column
            );
            let binding = residual_binding(&expected_delta);
            let nonzero_linear = binding
                .linear
                .iter()
                .filter(|coefficient| coefficient.as_str() != "0")
                .count();
            let d0_not_zero = binding
                .hinges
                .iter()
                .filter(|hinge| hinge.direction[0] != 0)
                .count();
            Ok(HostileControl {
                tranche_column: relation.tranche_column,
                added_sequence,
                added_atom_nonzero_linear_coordinates: nonzero_linear,
                added_atom_nonzero_hinges: binding.hinges.len(),
                added_atom_d0_not_zero_hinges: d0_not_zero,
                exact_complete_delta_sha256: canonical_json_sha256(&binding)?,
                delta_equals_added_atom_complete_normal_form: true,
                mutation_changes_complete_residual: true,
            })
        })
        .collect()
}

fn write_json_new(path: &Path, value: &Value) -> Result<()> {
    let mut writer = BufWriter::new(
        File::create_new(path).with_context(|| format!("creating {}", path.display()))?,
    );
    serde_json::to_writer(&mut writer, value)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    writer.get_ref().sync_all()?;
    Ok(())
}

fn main() -> Result<()> {
    let arguments = std::env::args().skip(1).collect::<Vec<_>>();
    ensure!(
        arguments.len() == 10
            && (arguments[0] == EXECUTION_FLAG || arguments[0] == VALIDATION_FLAG),
        concat!(
            "usage: g0194-mass4-filtration-full-nf-scanner ",
            "(--validate-frozen-inputs|--execute-frozen-scan) ",
            "BASIS.jsonl BASIS.i64le G0190_CERT.json G0189_RESULT.json STAR_RECORDS.json ",
            "G0180_RECEIPT.json G0179_LIB.rs OUTPUT.json THREADS"
        )
    );
    let execute_scan = arguments[0] == EXECUTION_FLAG;
    let basis_jsonl_path = PathBuf::from(&arguments[1]);
    let basis_binary_path = PathBuf::from(&arguments[2]);
    let g0190_certificate_path = PathBuf::from(&arguments[3]);
    let g0189_result_path = PathBuf::from(&arguments[4]);
    let star_path = PathBuf::from(&arguments[5]);
    let expansion_receipt_path = PathBuf::from(&arguments[6]);
    let g0179_lib_path = PathBuf::from(&arguments[7]);
    let output_path = PathBuf::from(&arguments[8]);
    let threads = arguments[9].parse::<usize>().context("parsing THREADS")?;
    ensure!((1..=256).contains(&threads), "THREADS must be in 1..=256");
    if execute_scan {
        ensure!(!output_path.exists(), "refusing to overwrite output");
    }
    let executable_path = std::env::current_exe().context("resolving current executable")?;
    let executable_bytes = read(&executable_path).context("reading current executable")?;
    let executable_sha256 = sha256_bytes(&executable_bytes);

    let started = Instant::now();
    let basis_jsonl_bytes = read_bound(
        &basis_jsonl_path,
        EXPECTED_BASIS_JSONL_SHA256,
        "G-0190 sparse basis",
    )?;
    let basis_binary_bytes = read_bound(
        &basis_binary_path,
        EXPECTED_BASIS_BINARY_SHA256,
        "G-0190 basis binary",
    )?;
    let g0190_certificate_bytes = read_bound(
        &g0190_certificate_path,
        EXPECTED_G0190_CERTIFICATE_SHA256,
        "G-0190 final certificate",
    )?;
    let g0189_result_bytes = read_bound(
        &g0189_result_path,
        EXPECTED_G0189_RESULT_SHA256,
        "G-0189 registered result",
    )?;
    let star_bytes = read_bound(&star_path, EXPECTED_STAR_SHA256, "STAR records")?;
    let expansion_receipt_bytes = read_bound(
        &expansion_receipt_path,
        EXPECTED_EXPANSION_RECEIPT_SHA256,
        "G-0180 expansion receipt",
    )?;
    let g0179_lib_bytes = read_bound(
        &g0179_lib_path,
        EXPECTED_G0179_LIB_SHA256,
        "G-0179 library source",
    )?;

    let (basis_header, relations) = parse_basis(&basis_jsonl_bytes)?;
    validate_basis_header(&basis_header)?;
    validate_g0190_certificate(&g0190_certificate_bytes)?;
    validate_expansion_receipt(&expansion_receipt_bytes)?;
    let classified_old_columns = validate_g0189_result(&g0189_result_bytes)?;
    let retained = retained_records(serde_json::from_slice::<StarDocument>(&star_bytes)?)?;
    validate_relations_and_binary(&relations, &retained, &basis_binary_bytes)?;
    let selected = validate_origins_and_select(&relations, &classified_old_columns)?;

    let unique_sequences = selected
        .iter()
        .flat_map(|relation| relation.terms.iter().map(|term| term.1))
        .collect::<BTreeSet<_>>();
    if !execute_scan {
        println!(
            "{}",
            serde_json::to_string(&json!({
                "result": "FROZEN_INPUTS_AND_SELECTOR_VALID_NO_NORMAL_FORMS_COMPUTED",
                "selected_tranche_columns": EXPECTED_SELECTED_TRANCHE_COLUMNS,
                "selected_relations": selected.len(),
                "term_incidences": EXPECTED_SELECTED_INCIDENCES,
                "unique_records": unique_sequences.len(),
                "output_created": false,
            }))?
        );
        return Ok(());
    }
    let selected_records = unique_sequences
        .iter()
        .map(|sequence| {
            retained
                .iter()
                .find(|record| record.sequence == *sequence)
                .cloned()
                .with_context(|| format!("selected record q{sequence} absent"))
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        selected_records.len() == EXPECTED_SELECTED_UNIQUE_RECORDS,
        "normal-form input count drift"
    );

    let pool = rayon::ThreadPoolBuilder::new()
        .num_threads(threads)
        .build()
        .context("building Rayon pool")?;
    let computed = pool.install(|| {
        selected_records
            .par_iter()
            .map(|record| Ok((record.sequence, full_normal_form(record)?)))
            .collect::<Result<Vec<_>>>()
    })?;
    ensure!(
        computed.len() == EXPECTED_SELECTED_UNIQUE_RECORDS,
        "normal-form count drift"
    );
    let forms = computed.into_iter().collect::<BTreeMap<_, _>>();
    ensure!(
        forms.len() == EXPECTED_SELECTED_UNIQUE_RECORDS,
        "duplicate computed normal forms"
    );

    let normal_form_bindings = forms
        .values()
        .map(|normal| {
            Ok(NormalFormBinding {
                active_vertices: normal.active_vertices,
                hinge_direction_count: normal.hinge_direction_count,
                normal_form_sha256: canonical_json_sha256(normal)?,
                sequence: normal.sequence,
            })
        })
        .collect::<Result<Vec<_>>>()?;

    let residuals = selected
        .iter()
        .map(|relation| aggregate_relation(relation, &forms, false))
        .collect::<Result<Vec<_>>>()?;
    let relation_results = selected
        .iter()
        .zip(&residuals)
        .map(|(relation, residual)| relation_result(relation, residual))
        .collect::<Result<Vec<_>>>()?;
    let controls = hostile_controls(&selected, &residuals, &forms)?;
    ensure!(
        controls.len() == selected.len(),
        "hostile-control count drift"
    );

    let exact_zero_columns = relation_results
        .iter()
        .filter(|result| result.classification == "EXACT_ZERO_IDENTITY")
        .map(|result| result.tranche_column)
        .collect::<Vec<_>>();
    let face_confined_nonzero_columns = relation_results
        .iter()
        .filter(|result| result.classification == "NONZERO_RESIDUAL_WITH_D0_ZERO_HINGES_ONLY")
        .map(|result| result.tranche_column)
        .collect::<Vec<_>>();
    let leaking_columns = relation_results
        .iter()
        .filter(|result| result.classification == "D0_NONZERO_HINGE_LEAKAGE")
        .map(|result| result.tranche_column)
        .collect::<Vec<_>>();
    let outcome = if exact_zero_columns.len() == selected.len() {
        "ALL_23_SELECTED_DIRECTIONS_ARE_EXACT_GLOBAL_IDENTITIES"
    } else if leaking_columns.is_empty() {
        "NONZERO_FACE_CONFINED_RESIDUALS_ONLY"
    } else {
        "D0_NONZERO_HINGE_LEAKAGE_FOUND"
    };

    let all_complete_residuals = selected
        .iter()
        .zip(&residuals)
        .map(|(relation, residual)| (relation.tranche_column, residual_binding(residual)))
        .collect::<Vec<_>>();
    let all_d0_not_zero = selected
        .iter()
        .zip(&residuals)
        .flat_map(|(relation, residual)| {
            residual
                .hinges
                .iter()
                .filter_map(move |(&direction, &coefficient)| {
                    (direction[0] != 0).then_some((
                        relation.tranche_column,
                        ExactHinge {
                            direction,
                            coefficient: coefficient.to_string(),
                        },
                    ))
                })
        })
        .collect::<Vec<_>>();

    // Custody is checked again immediately before the no-overwrite output creation.
    for (path, expected, label) in [
        (
            &basis_jsonl_path,
            EXPECTED_BASIS_JSONL_SHA256,
            "basis JSONL",
        ),
        (
            &basis_binary_path,
            EXPECTED_BASIS_BINARY_SHA256,
            "basis binary",
        ),
        (
            &g0190_certificate_path,
            EXPECTED_G0190_CERTIFICATE_SHA256,
            "G-0190 certificate",
        ),
        (
            &g0189_result_path,
            EXPECTED_G0189_RESULT_SHA256,
            "G-0189 result",
        ),
        (&star_path, EXPECTED_STAR_SHA256, "STAR records"),
        (
            &expansion_receipt_path,
            EXPECTED_EXPANSION_RECEIPT_SHA256,
            "G-0180 receipt",
        ),
        (&g0179_lib_path, EXPECTED_G0179_LIB_SHA256, "G-0179 source"),
    ] {
        ensure!(
            sha256_bytes(&read(path).with_context(|| format!("re-reading {label}"))?) == expected,
            "{label} changed during scan"
        );
    }
    ensure!(
        sha256_bytes(&read(&executable_path)?) == executable_sha256,
        "scanner executable changed during scan"
    );

    let exact_i128_coordinate_bound = i128::from(i64::MAX) * EXPECTED_SELECTED_MAX_L1;
    let hostile_i128_coordinate_bound = i128::from(i64::MAX) * HOSTILE_DIFFERENCE_MAX_L1;
    let receipt = json!({
        "schema": "g0194.mass4-filtration-complete-normal-form-classification.v1",
        "claim_boundary": concat!(
            "Exact complete ordered-chamber normal-form classification of the frozen 23 ",
            "previously unclassified directions in the G-0190 filtration-adapted mass<=4 ",
            "kernel basis. Exact-zero results certify intrinsic identities. A d[0]!=0 hinge ",
            "certifies non-membership in the loopless old-primary span O. A nonzero residual ",
            "with only d[0]=0 hinges does not by itself decide membership in O. No outcome ",
            "alone proves MAX11 representability or a neural-network lower bound."
        ),
        "result": outcome,
        "bindings": {
            "g0190_basis_jsonl": {"path": basis_jsonl_path, "bytes": basis_jsonl_bytes.len(), "sha256": EXPECTED_BASIS_JSONL_SHA256},
            "g0190_basis_binary": {"path": basis_binary_path, "bytes": basis_binary_bytes.len(), "sha256": EXPECTED_BASIS_BINARY_SHA256},
            "g0190_final_certificate": {"path": g0190_certificate_path, "bytes": g0190_certificate_bytes.len(), "sha256": EXPECTED_G0190_CERTIFICATE_SHA256},
            "g0189_registered_result": {"path": g0189_result_path, "bytes": g0189_result_bytes.len(), "sha256": EXPECTED_G0189_RESULT_SHA256},
            "star_records": {"path": star_path, "bytes": star_bytes.len(), "sha256": EXPECTED_STAR_SHA256},
            "g0180_expansion_receipt": {"path": expansion_receipt_path, "bytes": expansion_receipt_bytes.len(), "sha256": EXPECTED_EXPANSION_RECEIPT_SHA256},
            "g0179_lib_source": {"path": g0179_lib_path, "bytes": g0179_lib_bytes.len(), "sha256": EXPECTED_G0179_LIB_SHA256},
            "scanner_executable": {"path": executable_path, "bytes": executable_bytes.len(), "sha256": executable_sha256},
            "all_inputs_rehashed_unchanged_at_end": true,
        },
        "selection": {
            "rule": "max_signed_mass=4, excluding the 17 old-basis columns certified as exact zero identities by frozen G-0189; require the exact frozen result tranche 20..42",
            "tranche_columns": EXPECTED_SELECTED_TRANCHE_COLUMNS,
            "relation_count": selected.len(),
            "term_incidences": EXPECTED_SELECTED_INCIDENCES,
            "unique_record_count": unique_sequences.len(),
            "unique_sequences": unique_sequences,
            "support_histogram": {"8":1,"10":1,"12":2,"16":9,"17":1,"18":4,"22":2,"24":1,"34":1,"65":1},
            "maximum_abs_coefficient": EXPECTED_SELECTED_MAX_ABS_COEFFICIENT.to_string(),
            "nonunit_coefficient_incidences": 53,
            "aggregate_sum_abs_coefficients": EXPECTED_SELECTED_SUM_ABS_COEFFICIENTS.to_string(),
            "maximum_relation_sum_abs_coefficients": EXPECTED_SELECTED_MAX_L1.to_string(),
            "excluded_lowmass_tranche_columns": EXPECTED_LOWMASS_TRANCHE_COLUMNS,
            "excluded_g0189_tranche_columns": EXPECTED_G0189_TRANCHE_COLUMNS,
            "excluded_quotient_sequences": EXPECTED_EXCLUDED_SEQUENCES,
            "row_to_sequence_mapping_checked": true,
            "sparse_jsonl_equals_full_row_major_binary": true,
        },
        "normal_forms": {
            "producer": "g0179_star_loop_pricer::full_normal_form",
            "computed_once_per_unique_record": true,
            "bindings": normal_form_bindings,
        },
        "relations": relation_results,
        "classification_summary": {
            "exact_zero_count": exact_zero_columns.len(),
            "exact_zero_tranche_columns": exact_zero_columns,
            "nonzero_face_confined_count": face_confined_nonzero_columns.len(),
            "nonzero_face_confined_tranche_columns": face_confined_nonzero_columns,
            "d0_nonzero_leakage_count": leaking_columns.len(),
            "d0_nonzero_leakage_tranche_columns": leaking_columns,
            "all_complete_residuals_sha256": canonical_json_sha256(&all_complete_residuals)?,
            "all_d0_not_zero_hinges_sha256": canonical_json_sha256(&all_d0_not_zero)?,
            "total_d0_not_zero_hinges": all_d0_not_zero.len(),
            "first_d0_not_zero_witness": all_d0_not_zero.first(),
        },
        "hostile_plus_one_controls": {
            "mutation": "for every selected relation, add +1 to its first atom coefficient",
            "relations_tested": controls.len(),
            "all_complete_deltas_equal_added_atom_normal_forms": true,
            "all_mutations_change_complete_residual": true,
            "controls": controls,
        },
        "arithmetic": {
            "normal_form_coefficients": "G-0179 exact i64",
            "relation_coefficients": "exact signed i128 parsed from canonical decimal strings",
            "relation_aggregation": "checked signed i128 multiplication, addition, and subtraction",
            "maximum_relation_l1": EXPECTED_SELECTED_MAX_L1.to_string(),
            "coordinate_absolute_bound_from_i64_inputs": exact_i128_coordinate_bound.to_string(),
            "hostile_mutant_minus_original_max_l1": HOSTILE_DIFFERENCE_MAX_L1.to_string(),
            "hostile_coordinate_absolute_bound_from_i64_inputs": hostile_i128_coordinate_bound.to_string(),
            "signed_i128_safe": hostile_i128_coordinate_bound < i128::MAX,
            "zero_test": "exact integer equality",
        },
        "environment": {
            "threads": threads,
            "wall_seconds": started.elapsed().as_secs_f64(),
        },
    });
    write_json_new(&output_path, &receipt)?;
    let output_bytes = read(&output_path)?;
    println!(
        "{}",
        serde_json::to_string(&json!({
            "result": outcome,
            "exact_zero_count": receipt["classification_summary"]["exact_zero_count"],
            "nonzero_face_confined_count": receipt["classification_summary"]["nonzero_face_confined_count"],
            "d0_nonzero_leakage_count": receipt["classification_summary"]["d0_nonzero_leakage_count"],
            "output": output_path,
            "output_sha256": sha256_bytes(&output_bytes),
        }))?
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use g0179_star_loop_pricer::HingeTerm;

    fn synthetic_form() -> NormalForm {
        NormalForm {
            sequence: 7,
            active_vertices: 2,
            diagonal_multiplier: 1,
            labelled_permutation_count: 1,
            zero_word_permutation_count: 0,
            negative_word_permutation_count: 0,
            inactive_oriented_permutation_count: 0,
            hinge_direction_count: 1,
            base_linear: [0; N],
            orientation_correction: [0; N],
            linear: [2, -2, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            hinges: vec![HingeTerm {
                direction: [1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
                coefficient: 5,
            }],
        }
    }

    #[test]
    fn checked_complete_delta_recovers_added_form() {
        let form = synthetic_form();
        let mut original = ExactResidual::default();
        checked_add_scaled_form(&mut original, &form, -2).unwrap();
        let mut mutant = original.clone();
        checked_add_scaled_form(&mut mutant, &form, 1).unwrap();
        let delta = checked_difference(&mutant, &original).unwrap();
        let mut expected = ExactResidual::default();
        checked_add_scaled_form(&mut expected, &form, 1).unwrap();
        assert_eq!(delta, expected);
    }

    #[test]
    fn canonical_complete_hash_is_stable_and_sensitive() {
        let form = synthetic_form();
        let mut first = ExactResidual::default();
        checked_add_scaled_form(&mut first, &form, 1).unwrap();
        let mut second = first.clone();
        assert_eq!(
            canonical_json_sha256(&residual_binding(&first)).unwrap(),
            canonical_json_sha256(&residual_binding(&second)).unwrap()
        );
        second.linear[0] += 1;
        assert_ne!(
            canonical_json_sha256(&residual_binding(&first)).unwrap(),
            canonical_json_sha256(&residual_binding(&second)).unwrap()
        );
    }

    #[test]
    fn selector_is_exactly_contiguous_tail() {
        assert_eq!(
            EXPECTED_SELECTED_TRANCHE_COLUMNS,
            std::array::from_fn::<_, 23, _>(|index| index + 20)
        );
        assert!(
            EXPECTED_SELECTED_MAX_L1 * i128::from(i64::MAX) < i128::MAX,
            "the preregistered exact coordinate bound must fit i128"
        );
        assert!(
            HOSTILE_DIFFERENCE_MAX_L1 * i128::from(i64::MAX) < i128::MAX,
            "the hostile-control subtraction bound must fit i128"
        );
    }

    #[test]
    fn zero_coefficients_are_rejected() {
        assert!(parse_coefficient("0", "synthetic").is_err());
        assert_eq!(parse_coefficient("-3", "synthetic").unwrap(), -3);
    }
}
