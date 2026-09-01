use g0179_star_loop_pricer::{
    N, Record, Row, branch_swap, factorial, full_normal_form, hinge_coefficients, linear_vector,
    literal_panel_value, panel_vector, pure_nonloop_carrier,
};
use serde::Deserialize;
use std::fs::File;
use std::io::BufReader;
use std::path::PathBuf;

const ROWS: &str =
    "/data/projects/relu-depth-frontier-research/artifacts/math/G-0111/dual_rows_v1.json";

fn records_path() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("star_outside_primary_records.json")
}

#[derive(Deserialize)]
struct RecordDocument {
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct RowDocument {
    rows: Vec<Row>,
}

#[test]
fn cycle_cut_matches_literal_on_frozen_301_rows_and_both_orientations() {
    let records: RecordDocument =
        serde_json::from_reader(BufReader::new(File::open(records_path()).unwrap())).unwrap();
    let rows: RowDocument =
        serde_json::from_reader(BufReader::new(File::open(ROWS).unwrap())).unwrap();
    assert_eq!(records.records.len(), 5_773);
    assert_eq!(rows.rows.len(), 301);
    for sequence in [1548usize, 22, 2986, 447] {
        let record = &records.records[sequence];
        assert_eq!(record.sequence, sequence);
        let production = panel_vector(record, &rows.rows).unwrap();
        let literal = rows
            .rows
            .iter()
            .map(|row| literal_panel_value(record, row).unwrap())
            .collect::<Vec<_>>();
        assert_eq!(
            production, literal,
            "literal mismatch for sequence {sequence}"
        );
        assert_eq!(
            production,
            panel_vector(&branch_swap(record), &rows.rows).unwrap(),
            "branch-swap mismatch for sequence {sequence}"
        );
    }
}

#[test]
fn literal_control_rejects_a_dropped_loop_mutant() {
    let records: RecordDocument =
        serde_json::from_reader(BufReader::new(File::open(records_path()).unwrap())).unwrap();
    let rows: RowDocument =
        serde_json::from_reader(BufReader::new(File::open(ROWS).unwrap())).unwrap();
    let record = records.records[447].clone();
    assert_eq!(record.negative_loop_count, 1);
    let mut mutant = record.clone();
    mutant.negative_loop_count = 0;
    let loop_position = mutant
        .negative_edges
        .iter()
        .position(|edge| edge[0] == edge[1])
        .unwrap();
    mutant.negative_edges[loop_position] = [3, 5];
    mutant.negative_edges.sort();
    let original = rows
        .rows
        .iter()
        .map(|row| literal_panel_value(&record, row).unwrap())
        .collect::<Vec<_>>();
    let mutated = rows
        .rows
        .iter()
        .map(|row| literal_panel_value(&mutant, row).unwrap())
        .collect::<Vec<_>>();
    assert_ne!(
        original, mutated,
        "dropped-loop mutant escaped literal control"
    );
}

#[test]
fn sequence_1548_is_exactly_five_nonloop_carriers() {
    let records: RecordDocument =
        serde_json::from_reader(BufReader::new(File::open(records_path()).unwrap())).unwrap();
    let rows: RowDocument =
        serde_json::from_reader(BufReader::new(File::open(ROWS).unwrap())).unwrap();
    let record = &records.records[1548];
    assert_eq!(record.sequence, 1548);
    assert_eq!(record.signed_mass, 1);

    let normal_form = full_normal_form(record).unwrap();
    assert!(normal_form.hinges.is_empty());
    let (carrier_panel, carrier_linear) = pure_nonloop_carrier(&rows.rows).unwrap();
    assert_eq!(
        panel_vector(record, &rows.rows).unwrap(),
        carrier_panel
            .iter()
            .map(|value| 5 * value)
            .collect::<Vec<_>>()
    );
    assert_eq!(
        linear_vector(record).unwrap(),
        std::array::from_fn(|rank| 5 * carrier_linear[rank])
    );

    // This is an independent selected-direction sanity check in addition to
    // the complete normal-form assertion above.
    let mass_two = [1, -2, 1, 0, 0, 0, 0, 0, 0, 0, 0];
    assert_eq!(hinge_coefficients(record, &[mass_two]).unwrap(), [0]);
    assert_eq!(
        carrier_linear[N - 1],
        2 * (N - 1) as i64 * factorial(N - 2) as i64
    );
}
