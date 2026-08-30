use g0117_global_coordinate_pricer::{N, Record, hinge_coefficient, linear_vector};
use serde::Deserialize;
use std::collections::{BTreeMap, BTreeSet};
use std::fs::File;
use std::io::BufReader;
use std::path::PathBuf;

#[derive(Deserialize)]
struct FrozenInput {
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct HingeTerm {
    direction: [i8; N],
    coefficient: i64,
}

#[derive(Deserialize)]
struct NormalForm {
    sequence: usize,
    linear: [i64; N],
    hinges: Vec<HingeTerm>,
}

#[derive(Deserialize)]
struct FrozenOutput {
    normal_forms: Vec<NormalForm>,
}

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("project root")
        .to_path_buf()
}

#[test]
#[ignore = "explicit frozen-artifact validation; includes active-11 coordinate queries"]
fn subset_pricer_matches_frozen_g0109_normal_forms() {
    let root = root();
    let input: FrozenInput = serde_json::from_reader(BufReader::new(
        File::open(root.join("artifacts/math/G-0109/selected_records_v1.json")).unwrap(),
    ))
    .unwrap();
    let output: FrozenOutput = serde_json::from_reader(BufReader::new(
        File::open(root.join("artifacts/math/G-0109/selected_normal_forms_v1.json")).unwrap(),
    ))
    .unwrap();
    let records = input
        .records
        .into_iter()
        .map(|record| (record.sequence, record))
        .collect::<BTreeMap<_, _>>();
    let forms = output
        .normal_forms
        .into_iter()
        .map(|form| (form.sequence, form))
        .collect::<BTreeMap<_, _>>();

    for sequence in [0usize, 4, 202, 6_972_321] {
        let record = &records[&sequence];
        let form = &forms[&sequence];
        assert_eq!(
            linear_vector(record).unwrap(),
            form.linear,
            "linear {sequence}"
        );
        for term in &form.hinges {
            assert_eq!(
                hinge_coefficient(record, &term.direction).unwrap(),
                term.coefficient,
                "supported direction {sequence} {:?}",
                term.direction
            );
        }
    }

    let star = &records[&6_972_321];
    let star_support = forms[&6_972_321]
        .hinges
        .iter()
        .map(|term| term.direction)
        .collect::<BTreeSet<_>>();
    let absent = forms[&6_631_416]
        .hinges
        .iter()
        .map(|term| term.direction)
        .filter(|direction| !star_support.contains(direction))
        .take(16)
        .collect::<Vec<_>>();
    assert_eq!(absent.len(), 16);
    for direction in absent {
        assert_eq!(hinge_coefficient(star, &direction).unwrap(), 0);
    }
}
