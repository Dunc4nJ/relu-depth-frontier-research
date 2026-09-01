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

const EXPECTED_CANDIDATE_SHA256: &str =
    "24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe";
const EXPECTED_STAR_SHA256: &str =
    "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4";
const EXPECTED_EXPANSION_RECEIPT_SHA256: &str =
    "6e7d58666b9a58d1ea68141595bdd1404a519f10e7f47068166c7d7a290864d5";
const EXPECTED_G0179_LIB_SHA256: &str =
    "8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73";
const EXPECTED_EXCLUDED_SEQUENCES: [usize; 4] = [1548, 3140, 4259, 5656];
const EXPECTED_SELECTED_COLUMNS: [usize; 17] = [
    12, 15, 17, 21, 24, 28, 68, 72, 75, 82, 87, 90, 91, 108, 117, 121, 122,
];

#[derive(Debug, Deserialize)]
struct CandidateHeader {
    basis_shape: [usize; 2],
    matrix_shape: [usize; 2],
    schema: String,
    term_encoding: String,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
struct Relation {
    basis_column: usize,
    max_abs_coefficient: String,
    sum_abs_coefficients: String,
    support: usize,
    terms: Vec<(usize, usize, String)>,
}

#[derive(Debug, Deserialize)]
struct StarDocument {
    schema: String,
    records: Vec<Record>,
}

#[derive(Clone, Debug, Serialize)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Debug, Serialize)]
struct RelationResult {
    basis_column: usize,
    terms: Vec<(usize, i8)>,
    residual_linear: [String; N],
    residual_nonzero_hinges: usize,
    residual_d0_eq_zero_hinges: usize,
    residual_d0_not_zero_hinges: usize,
    complete_residual_sha256: String,
    d0_not_zero_residual_sha256: String,
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

fn parse_candidate(bytes: &[u8]) -> Result<(CandidateHeader, Vec<Relation>)> {
    let text = std::str::from_utf8(bytes).context("candidate JSONL is not UTF-8")?;
    let mut lines = text.lines();
    let header: CandidateHeader =
        serde_json::from_str(lines.next().context("candidate JSONL lacks header")?)
            .context("parsing candidate header")?;
    ensure!(
        header.schema == "g0193.greedy-exact-sparse-left-kernel-basis.v1",
        "candidate schema drift"
    );
    ensure!(
        header.basis_shape == [5769, 478],
        "candidate basis shape drift"
    );
    ensure!(
        header.matrix_shape == [5769, 6795],
        "candidate matrix shape drift"
    );
    ensure!(
        header.term_encoding
            == "[output_row, record_sequence, primitive_integer_coefficient_as_decimal_string]",
        "candidate term encoding drift"
    );
    let relations = lines
        .enumerate()
        .map(|(index, line)| {
            let relation: Relation = serde_json::from_str(line)
                .with_context(|| format!("parsing candidate relation line {}", index + 2))?;
            ensure!(
                relation.basis_column == index,
                "basis-column order drift at line {}",
                index + 2
            );
            ensure!(
                relation.support == relation.terms.len(),
                "serialized support mismatch at basis column {}",
                relation.basis_column
            );
            Ok(relation)
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(relations.len() == 478, "candidate relation count drift");
    Ok((header, relations))
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
        receipt["quotient_records"]["retained"] == 5769,
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
    ensure!(retained.len() == 5769, "retained STAR count drift");
    Ok(retained)
}

fn select_relations(relations: &[Relation], retained: &[Record]) -> Result<Vec<Relation>> {
    for relation in relations {
        for &(output_row, sequence, _) in &relation.terms {
            ensure!(
                output_row < retained.len(),
                "output row outside retained records"
            );
            ensure!(
                retained[output_row].sequence == sequence,
                "row-to-sequence mismatch at basis column {}, row {}",
                relation.basis_column,
                output_row
            );
        }
    }
    let selected = relations
        .iter()
        .filter(|relation| {
            relation.support <= 6
                && relation
                    .terms
                    .iter()
                    .all(|term| retained[term.0].signed_mass == 4)
        })
        .cloned()
        .collect::<Vec<_>>();
    let columns = selected
        .iter()
        .map(|relation| relation.basis_column)
        .collect::<Vec<_>>();
    ensure!(
        columns == EXPECTED_SELECTED_COLUMNS,
        "selected basis-column drift"
    );
    ensure!(selected.len() == 17, "selected relation count drift");
    ensure!(
        selected.iter().all(|relation| relation.support == 6),
        "selected support is not exactly six"
    );
    for relation in &selected {
        ensure!(
            relation.max_abs_coefficient == "1" && relation.sum_abs_coefficients == "6",
            "selected coefficient summary drift at basis column {}",
            relation.basis_column
        );
        let mut rows = BTreeSet::new();
        for &(output_row, _, ref coefficient) in &relation.terms {
            ensure!(
                rows.insert(output_row),
                "duplicate term row in selected relation"
            );
            let parsed = coefficient
                .parse::<i8>()
                .with_context(|| format!("parsing coefficient {coefficient}"))?;
            ensure!(
                parsed == -1 || parsed == 1,
                "selected coefficient is not +/-1"
            );
        }
    }
    let unique = selected
        .iter()
        .flat_map(|relation| relation.terms.iter().map(|term| term.1))
        .collect::<BTreeSet<_>>();
    ensure!(
        selected
            .iter()
            .map(|relation| relation.terms.len())
            .sum::<usize>()
            == 102,
        "selected incidence count drift"
    );
    ensure!(unique.len() == 92, "selected unique-record count drift");
    Ok(selected)
}

fn relation_residual(
    relation: &Relation,
    forms: &BTreeMap<usize, NormalForm>,
) -> Result<(RelationResult, Vec<ExactHinge>)> {
    let mut linear = [0i128; N];
    let mut hinges = BTreeMap::<[i8; N], i128>::new();
    let mut terms = Vec::with_capacity(relation.terms.len());
    for &(_, sequence, ref coefficient_text) in &relation.terms {
        let coefficient = coefficient_text.parse::<i8>()?;
        let normal = forms
            .get(&sequence)
            .with_context(|| format!("missing normal form q{sequence}"))?;
        terms.push((sequence, coefficient));
        for (target, &value) in linear.iter_mut().zip(&normal.linear) {
            *target += i128::from(coefficient) * i128::from(value);
        }
        for hinge in &normal.hinges {
            *hinges.entry(hinge.direction).or_default() +=
                i128::from(coefficient) * i128::from(hinge.coefficient);
        }
    }
    hinges.retain(|_, coefficient| *coefficient != 0);
    let complete = hinges
        .iter()
        .map(|(&direction, &coefficient)| ExactHinge {
            direction,
            coefficient: coefficient.to_string(),
        })
        .collect::<Vec<_>>();
    let d0_not_zero = complete
        .iter()
        .filter(|hinge| hinge.direction[0] != 0)
        .cloned()
        .collect::<Vec<_>>();
    ensure!(
        d0_not_zero.iter().all(|hinge| hinge.direction[0] > 0),
        "canonical direction orientation drift at d[0]"
    );
    #[derive(Serialize)]
    struct CompleteBinding<'a> {
        linear: [String; N],
        hinges: &'a [ExactHinge],
    }
    let residual_linear = linear.map(|value| value.to_string());
    let complete_residual_sha256 = canonical_json_sha256(&CompleteBinding {
        linear: residual_linear.clone(),
        hinges: &complete,
    })?;
    let d0_not_zero_residual_sha256 = canonical_json_sha256(&d0_not_zero)?;
    let result = RelationResult {
        basis_column: relation.basis_column,
        terms,
        residual_linear,
        residual_nonzero_hinges: complete.len(),
        residual_d0_eq_zero_hinges: complete.len() - d0_not_zero.len(),
        residual_d0_not_zero_hinges: d0_not_zero.len(),
        complete_residual_sha256,
        d0_not_zero_residual_sha256,
        first_d0_not_zero_hinge: d0_not_zero.first().cloned(),
    };
    Ok((result, d0_not_zero))
}

fn exact_hinge_map(hinges: &[ExactHinge]) -> Result<BTreeMap<[i8; N], i128>> {
    hinges
        .iter()
        .map(|hinge| {
            Ok((
                hinge.direction,
                hinge
                    .coefficient
                    .parse::<i128>()
                    .context("parsing exact hinge coefficient")?,
            ))
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
        arguments.len() == 6,
        "usage: g0189-mass4-full-normal-form-scanner CANDIDATE.jsonl STAR_RECORDS.json G0180_RECEIPT.json G0179_LIB.rs OUTPUT.json THREADS"
    );
    let candidate_path = PathBuf::from(&arguments[0]);
    let star_path = PathBuf::from(&arguments[1]);
    let expansion_receipt_path = PathBuf::from(&arguments[2]);
    let g0179_lib_path = PathBuf::from(&arguments[3]);
    let output_path = PathBuf::from(&arguments[4]);
    let threads = arguments[5].parse::<usize>().context("parsing THREADS")?;
    ensure!((1..=256).contains(&threads), "THREADS must be in 1..=256");
    ensure!(!output_path.exists(), "refusing to overwrite output");
    let executable_path = std::env::current_exe().context("resolving current executable")?;
    let executable_bytes = read(&executable_path).context("reading current executable")?;
    let executable_sha256 = sha256_bytes(&executable_bytes);

    let started = Instant::now();
    let candidate_bytes = read_bound(&candidate_path, EXPECTED_CANDIDATE_SHA256, "candidate")?;
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
    validate_expansion_receipt(&expansion_receipt_bytes)?;
    let (_, relations) = parse_candidate(&candidate_bytes)?;
    let retained = retained_records(serde_json::from_slice::<StarDocument>(&star_bytes)?)?;
    let selected = select_relations(&relations, &retained)?;
    let unique_sequences = selected
        .iter()
        .flat_map(|relation| relation.terms.iter().map(|term| term.1))
        .collect::<BTreeSet<_>>();
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
        selected_records
            .iter()
            .all(|record| record.signed_mass == 4),
        "non-mass-four record entered selected scan"
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
    ensure!(computed.len() == 92, "normal-form count drift");
    let forms = computed.into_iter().collect::<BTreeMap<_, _>>();
    ensure!(forms.len() == 92, "duplicate computed normal forms");

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

    let mut relation_results = Vec::with_capacity(selected.len());
    let mut all_d0_not_zero = Vec::<(usize, ExactHinge)>::new();
    let mut first_relation_d0 = None;
    for (index, relation) in selected.iter().enumerate() {
        let (result, d0_not_zero) = relation_residual(relation, &forms)?;
        if index == 0 {
            first_relation_d0 = Some(d0_not_zero.clone());
        }
        all_d0_not_zero.extend(
            d0_not_zero
                .into_iter()
                .map(|hinge| (relation.basis_column, hinge)),
        );
        relation_results.push(result);
    }
    let leaking_columns = relation_results
        .iter()
        .filter(|result| result.residual_d0_not_zero_hinges != 0)
        .map(|result| result.basis_column)
        .collect::<Vec<_>>();
    let result = if leaking_columns.is_empty() {
        "NO_D0_NONZERO_HINGE_IN_SELECTED_RELATIONS"
    } else {
        "D0_NONZERO_HINGE_FOUND"
    };

    // A coefficient +1 mutation must change the aggregated d[0]!=0 map by
    // exactly one copy of the selected STAR atom's corresponding map.
    let first_sequence = selected[0].terms[0].1;
    let hostile = forms
        .get(&first_sequence)
        .context("hostile-control form absent")?;
    let hostile_d0 = hostile
        .hinges
        .iter()
        .filter(|hinge| hinge.direction[0] != 0)
        .map(|hinge| (hinge.direction, i128::from(hinge.coefficient)))
        .collect::<BTreeMap<_, _>>();
    ensure!(
        !hostile_d0.is_empty(),
        "hostile +1 STAR atom has no d[0]!=0 hinge"
    );
    let mut mutant_relation = selected[0].clone();
    let old_coefficient = mutant_relation.terms[0].2.parse::<i8>()?;
    mutant_relation.terms[0].2 = (old_coefficient + 1).to_string();
    let (_, mutant_d0) = relation_residual(&mutant_relation, &forms)?;
    let original_map = exact_hinge_map(
        first_relation_d0
            .as_deref()
            .context("first relation d[0]!=0 residual absent")?,
    )?;
    let mutant_map = exact_hinge_map(&mutant_d0)?;
    let mut delta = mutant_map;
    for (direction, coefficient) in original_map {
        *delta.entry(direction).or_default() -= coefficient;
    }
    delta.retain(|_, coefficient| *coefficient != 0);
    ensure!(
        delta == hostile_d0,
        "hostile +1 aggregation delta is not the added STAR d[0]!=0 map"
    );

    // Custody is checked again before any output is created.
    ensure!(
        sha256_bytes(&read(&candidate_path)?) == EXPECTED_CANDIDATE_SHA256,
        "candidate changed during scan"
    );
    ensure!(
        sha256_bytes(&read(&star_path)?) == EXPECTED_STAR_SHA256,
        "STAR records changed during scan"
    );
    ensure!(
        sha256_bytes(&read(&expansion_receipt_path)?) == EXPECTED_EXPANSION_RECEIPT_SHA256,
        "G-0180 receipt changed during scan"
    );
    ensure!(
        sha256_bytes(&read(&g0179_lib_path)?) == EXPECTED_G0179_LIB_SHA256,
        "G-0179 library source changed during scan"
    );
    ensure!(
        sha256_bytes(&read(&executable_path)?) == executable_sha256,
        "scanner executable changed during scan"
    );

    let receipt = json!({
        "schema": "g0189.mass4-complete-normal-form-d0-scan.v1",
        "claim_boundary": concat!(
            "Exact complete-normal-form d[0]!=0 leakage scan for the frozen 17-relation, ",
            "support<=6, signed-mass-four G-0187 stratum only. Absence of leakage would not ",
            "prove old-primary membership, MAX11 representability, or a ReLU lower bound."
        ),
        "result": result,
        "bindings": {
            "candidate": {"path": candidate_path, "bytes": candidate_bytes.len(), "sha256": EXPECTED_CANDIDATE_SHA256},
            "star_records": {"path": star_path, "bytes": star_bytes.len(), "sha256": EXPECTED_STAR_SHA256},
            "g0180_expansion_receipt": {"path": expansion_receipt_path, "bytes": expansion_receipt_bytes.len(), "sha256": EXPECTED_EXPANSION_RECEIPT_SHA256},
            "g0179_lib_source": {"path": g0179_lib_path, "bytes": g0179_lib_bytes.len(), "sha256": EXPECTED_G0179_LIB_SHA256},
            "scanner_executable": {"path": executable_path, "bytes": executable_bytes.len(), "sha256": executable_sha256},
            "all_inputs_rehashed_unchanged_at_end": true,
        },
        "selection": {
            "rule": "relation support<=6 and every retained STAR record has signed_mass=4",
            "basis_columns": EXPECTED_SELECTED_COLUMNS,
            "relation_count": selected.len(),
            "term_incidences": selected.iter().map(|relation| relation.terms.len()).sum::<usize>(),
            "unique_record_count": unique_sequences.len(),
            "unique_sequences": unique_sequences,
            "coefficients_exactly_plus_or_minus_one": true,
            "excluded_quotient_sequences": EXPECTED_EXCLUDED_SEQUENCES,
            "row_to_sequence_mapping_checked": true,
        },
        "normal_forms": {
            "producer": "g0179_star_loop_pricer::full_normal_form",
            "computed_once_per_unique_record": true,
            "bindings": normal_form_bindings,
        },
        "relations": relation_results,
        "d0_not_zero_summary": {
            "leaking_relation_count": leaking_columns.len(),
            "leaking_basis_columns": leaking_columns,
            "nonzero_hinge_count_across_relations": all_d0_not_zero.len(),
            "all_d0_not_zero_residual_sha256": canonical_json_sha256(&all_d0_not_zero)?,
            "first_witness": all_d0_not_zero.first(),
        },
        "hostile_plus_one_control": {
            "mutation": format!("add one copy of q{first_sequence} to basis column {}", selected[0].basis_column),
            "added_atom_d0_not_zero_hinges": hostile_d0.len(),
            "mutant_d0_not_zero_hinges": mutant_d0.len(),
            "aggregation_delta_equals_added_atom_d0_map": true,
            "rejected": true,
        },
        "arithmetic": {
            "normal_form_coefficients": "G-0179 exact i64",
            "relation_aggregation": "signed i128; selected coefficients are +/-1 and support is six",
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
            "result": result,
            "leaking_relation_count": receipt["d0_not_zero_summary"]["leaking_relation_count"],
            "nonzero_d0_hinges": receipt["d0_not_zero_summary"]["nonzero_hinge_count_across_relations"],
            "output": output_path,
            "output_sha256": sha256_bytes(&output_bytes),
        }))?
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn canonical_hash_is_stable_and_sensitive() {
        let first = vec![ExactHinge {
            direction: [1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            coefficient: "7".to_owned(),
        }];
        let mut second = first.clone();
        assert_eq!(
            canonical_json_sha256(&first).unwrap(),
            canonical_json_sha256(&second).unwrap()
        );
        second[0].coefficient = "8".to_owned();
        assert_ne!(
            canonical_json_sha256(&first).unwrap(),
            canonical_json_sha256(&second).unwrap()
        );
    }

    #[test]
    fn expected_columns_are_strictly_increasing() {
        assert!(
            EXPECTED_SELECTED_COLUMNS
                .windows(2)
                .all(|pair| pair[0] < pair[1])
        );
    }
}
