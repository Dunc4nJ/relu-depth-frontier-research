use g0117_global_coordinate_pricer::{N, Record, full_normal_form};
use serde::Deserialize;
use sha2::{Digest, Sha256};
use std::fs::File;
use std::io::BufReader;
use std::path::PathBuf;

#[derive(Deserialize)]
struct PanelInput {
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct Row {
    levels: [i64; 4],
    profile: [u8; 4],
    formal_stabilizer: u64,
}

#[derive(Deserialize)]
struct Rows {
    rows: Vec<Row>,
}

fn root() -> PathBuf {
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .ancestors()
        .nth(3)
        .expect("project root")
        .to_path_buf()
}

fn panel_hash(record: &Record, rows: &[Row]) -> String {
    let form = full_normal_form(record).unwrap();
    let mut digest = Sha256::new();
    for row in rows {
        let mut x = Vec::with_capacity(N);
        for (&level, &count) in row.levels.iter().zip(row.profile.iter()) {
            x.extend(std::iter::repeat_n(level, usize::from(count)));
        }
        assert_eq!(x.len(), N);
        let mut value = form
            .linear
            .iter()
            .zip(x.iter())
            .map(|(&coefficient, &coordinate)| i128::from(coefficient) * i128::from(coordinate))
            .sum::<i128>();
        for (direction, coefficient) in &form.hinges {
            let argument = direction
                .iter()
                .zip(x.iter())
                .map(|(&d, &coordinate)| i128::from(d) * i128::from(coordinate))
                .sum::<i128>();
            value += i128::from(*coefficient) * argument.max(0);
        }
        assert_eq!(value % i128::from(row.formal_stabilizer), 0);
        digest.update((value / i128::from(row.formal_stabilizer)).to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

#[test]
#[ignore = "explicit full-orbit bridge check against frozen 301-row hashes"]
fn full_normal_forms_match_independent_panel_controls() {
    let root = root();
    let input: PanelInput = serde_json::from_reader(BufReader::new(
        File::open(root.join("artifacts/math/G-0113/panel_solver_input_v1.json")).unwrap(),
    ))
    .unwrap();
    let rows: Rows = serde_json::from_reader(BufReader::new(
        File::open(root.join("artifacts/math/G-0111/dual_rows_v1.json")).unwrap(),
    ))
    .unwrap();
    for (sequence, expected) in [
        (
            0usize,
            "f09264dcc0b2d4bd3c9513b82b66aee22cd52cfe380e592f42cf7c5a454a3c58",
        ),
        (
            3usize,
            "475f46c40f0ee5994d15d5f36140fe78c20f6aaf46857b95be2b142f5a8d2099",
        ),
    ] {
        assert_eq!(panel_hash(&input.records[sequence], &rows.rows), expected);
    }
}
