use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{N, Record, hinge_coefficients, validate_direction};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::Deserialize;
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeSet, HashMap};
use std::fs::{File, read};
use std::io::{BufReader, BufWriter, Read, Write};
use std::path::Path;
use std::time::Instant;

const RECORDS: usize = 163_740;
const DIRECTIONS: usize = 4_096;
const BASIS: usize = 659;
const PRIOR_BASIS: usize = 595;
const PROBES_PER_PANEL: usize = 512;
const PAIR_DIRECTIONS: usize = 128;
const PAIR_COORDINATES: usize = 64;
const CURRENT_ROWS: usize = 796;
const PANEL: &str = "/data/projects/relu-depth-frontier-research/artifacts/math/G-0113/panel_solver_input_v1.json";
const GLOBAL: &str = "/tmp/g0168-screen.vvx85D/global_replay_924_member.json";
const MEMBER: &str = "/tmp/g0168-screen.vvx85D/exact_924_member.json";
const PAIR_MATRIX: &str = "/tmp/g0168-screen.vvx85D/duplicate_pairs128.record-major.i64le";
const PAIR_RECEIPT: &str = "/tmp/g0168-screen.vvx85D/duplicate_pairs128_full_price_receipt.json";
const PAIR_SELECTION: &str = "/tmp/g0168-screen.vvx85D/selected_duplicate_pairs_128.json";
const PRIOR_FINGERPRINT_RECEIPT: &str = "/tmp/g0168-screen.vvx85D/fingerprint_receipt.json";
const MATRIX: &str = "/tmp/g0178-rank659-fingerprint.W3xKLW/basis659_probe512x2_direction4096.record-major.i64le";
const OUTPUT: &str = "/tmp/g0178-rank659-fingerprint.W3xKLW/fingerprint_receipt.json";
const SPLITMIX_SEED: u64 = 0x8f3f_73b5_cf1c_9ade;

#[derive(Deserialize)]
struct Panel {
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct GlobalReplay {
    schema: String,
    result: String,
    nonzero_hinge_signed_lexicographic_prefix: Vec<Hinge>,
    inputs: GlobalInputs,
}

#[derive(Deserialize)]
struct GlobalInputs {
    member_sha256: String,
    panel_sha256: String,
}

#[derive(Deserialize)]
struct Hinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Deserialize)]
struct Member {
    result: String,
    rows: usize,
    #[serde(rename = "selected_minor_rank_over_Q")]
    selected_minor_rank_over_q: usize,
    current_selected_minor_rank: usize,
    basis_sequences: Vec<usize>,
    coordinate_rows: Vec<usize>,
    pair_coordinate_direction_indices: Vec<usize>,
    pair_witness_sequences: Vec<usize>,
    terms: Vec<Term>,
    all_924_rows_exactly_replayed: bool,
    inputs: MemberInputs,
}

#[derive(Deserialize)]
struct MemberInputs {
    current_member_sha256: String,
    pair_matrix_sha256: String,
    receipt_sha256: String,
    selection_sha256: String,
}

#[derive(Deserialize)]
struct Term {
    sequence: usize,
    coefficient: String,
}

#[derive(Deserialize)]
struct PairReceipt {
    schema: String,
    records: usize,
    directions: usize,
    directions_i8_sha256: String,
    matrix_bytes: usize,
    matrix_sha256: String,
    inputs: PairReceiptInputs,
}

#[derive(Deserialize)]
struct PairReceiptInputs {
    member_sha256: String,
    panel_sha256: String,
    selection_sha256: String,
}

#[derive(Deserialize)]
struct PairSelection {
    schema: String,
    selected_pairs: Vec<[usize; 2]>,
    selected_direction_indices: Vec<usize>,
    selected_directions_i8_sha256: String,
    selected_residual_items: Vec<Hinge>,
}

#[derive(Deserialize)]
struct PriorFingerprintReceipt {
    schema: String,
    basis_records: usize,
    probe_records: usize,
    directions: usize,
    splitmix_seed: String,
    selected_records: Vec<usize>,
}

fn parse_bigint(raw: &str) -> Result<BigInt> {
    BigInt::parse_bytes(raw.as_bytes(), 10).context("parse integer")
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn sha256_file(path: &str) -> Result<String> {
    let mut reader = BufReader::with_capacity(1 << 20, File::open(path)?);
    let mut digest = Sha256::new();
    let mut buffer = vec![0_u8; 1 << 20];
    loop {
        let count = reader.read(&mut buffer)?;
        if count == 0 {
            break;
        }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn next_splitmix(state: &mut u64) -> u64 {
    *state = state.wrapping_add(0x9e37_79b9_7f4a_7c15);
    let mut value = *state;
    value = (value ^ (value >> 30)).wrapping_mul(0xbf58_476d_1ce4_e5b9);
    value = (value ^ (value >> 27)).wrapping_mul(0x94d0_49bb_1331_11eb);
    value ^ (value >> 31)
}

fn main() -> Result<()> {
    ensure!(!Path::new(MATRIX).exists(), "refusing to overwrite matrix");
    ensure!(!Path::new(OUTPUT).exists(), "refusing to overwrite receipt");
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .context("build thread pool")?;
    let started = Instant::now();

    let panel_bytes = read(PANEL)?;
    let global_bytes = read(GLOBAL)?;
    let member_bytes = read(MEMBER)?;
    let pair_receipt_bytes = read(PAIR_RECEIPT)?;
    let pair_selection_bytes = read(PAIR_SELECTION)?;
    let prior_receipt_bytes = read(PRIOR_FINGERPRINT_RECEIPT)?;
    let panel: Panel = serde_json::from_slice(&panel_bytes)?;
    let global: GlobalReplay = serde_json::from_slice(&global_bytes)?;
    let member: Member = serde_json::from_slice(&member_bytes)?;
    let pair_receipt: PairReceipt = serde_json::from_slice(&pair_receipt_bytes)?;
    let pair_selection: PairSelection = serde_json::from_slice(&pair_selection_bytes)?;
    let prior_receipt: PriorFingerprintReceipt = serde_json::from_slice(&prior_receipt_bytes)?;

    let panel_sha256 = sha256(&panel_bytes);
    let global_sha256 = sha256(&global_bytes);
    let member_sha256 = sha256(&member_bytes);
    let pair_receipt_sha256 = sha256(&pair_receipt_bytes);
    let pair_selection_sha256 = sha256(&pair_selection_bytes);
    let prior_receipt_sha256 = sha256(&prior_receipt_bytes);
    let pair_matrix_sha256 = sha256_file(PAIR_MATRIX)?;

    ensure!(panel.records.len() == RECORDS, "record census drift");
    ensure!(global.schema == "g0168.provisional_member_complete_exact_global_replay.v2", "global schema drift");
    ensure!(global.result == "EXACT_GLOBAL_NONZERO", "global premise drift");
    ensure!(global.inputs.member_sha256 == member_sha256, "global/member hash envelope drift");
    ensure!(global.inputs.panel_sha256 == panel_sha256, "global/panel hash envelope drift");
    ensure!(member.result == "EXACT_924_ROW_DUPLICATE_PAIR_BATCH_MEMBER_PROVISIONAL", "member result drift");
    ensure!(member.rows == 924 && member.all_924_rows_exactly_replayed, "finite replay premise drift");
    ensure!(member.selected_minor_rank_over_q == BASIS, "member exact-rank drift");
    ensure!(member.current_selected_minor_rank == PRIOR_BASIS, "member prior-rank drift");
    ensure!(member.basis_sequences.len() == BASIS && member.coordinate_rows.len() == BASIS, "basis/coordinate census drift");
    ensure!(member.pair_coordinate_direction_indices.len() == PAIR_COORDINATES, "pair-coordinate census drift");
    ensure!(member.pair_witness_sequences.len() == PAIR_COORDINATES, "pair-witness census drift");
    ensure!(member.basis_sequences[PRIOR_BASIS..] == member.pair_witness_sequences, "pair-witness/basis-tail drift");
    ensure!(
        member.coordinate_rows[PRIOR_BASIS..]
            == member
                .pair_coordinate_direction_indices
                .iter()
                .map(|index| CURRENT_ROWS + index)
                .collect::<Vec<_>>(),
        "pair-coordinate row provenance drift"
    );
    ensure!(
        member.pair_coordinate_direction_indices.iter().all(|index| *index < PAIR_DIRECTIONS)
            && member.pair_coordinate_direction_indices.iter().copied().collect::<BTreeSet<_>>().len() == PAIR_COORDINATES,
        "pair-coordinate index envelope drift"
    );
    ensure!(pair_receipt.schema == "g0168.duplicate_pairs128_provisional_full_family_coordinates.v1", "pair receipt schema drift");
    ensure!(pair_receipt.records == RECORDS && pair_receipt.directions == PAIR_DIRECTIONS, "pair receipt census drift");
    ensure!(pair_receipt.matrix_bytes == RECORDS * PAIR_DIRECTIONS * 8, "pair matrix byte envelope drift");
    ensure!(std::fs::metadata(PAIR_MATRIX)?.len() == u64::try_from(pair_receipt.matrix_bytes)?, "pair matrix size drift");
    ensure!(pair_receipt.matrix_sha256 == pair_matrix_sha256, "pair matrix/receipt hash drift");
    ensure!(member.inputs.pair_matrix_sha256 == pair_matrix_sha256, "member/pair matrix hash drift");
    ensure!(member.inputs.receipt_sha256 == pair_receipt_sha256, "member/pair receipt hash drift");
    ensure!(member.inputs.selection_sha256 == pair_selection_sha256, "member/pair selection hash drift");
    ensure!(pair_receipt.inputs.selection_sha256 == pair_selection_sha256, "pair receipt/selection hash drift");
    ensure!(pair_receipt.inputs.panel_sha256 == panel_sha256, "pair receipt/panel hash drift");
    ensure!(pair_receipt.inputs.member_sha256 == member.inputs.current_member_sha256, "pair receipt/current-member hash drift");
    ensure!(pair_selection.schema == "g0168.provisional_duplicate_pair_batch128.v1", "pair selection schema drift");
    ensure!(pair_selection.selected_pairs.len() == PAIR_COORDINATES, "pair selection pair census drift");
    ensure!(pair_selection.selected_direction_indices.len() == PAIR_DIRECTIONS, "pair selection index census drift");
    ensure!(pair_selection.selected_residual_items.len() == PAIR_DIRECTIONS, "pair selection residual census drift");
    ensure!(
        pair_selection.selected_pairs.iter().flatten().copied().collect::<Vec<_>>()
            == pair_selection.selected_direction_indices,
        "pair selection flattening drift"
    );
    let selected_direction_bytes = pair_selection
        .selected_residual_items
        .iter()
        .flat_map(|item| item.direction)
        .map(|value| value as u8)
        .collect::<Vec<_>>();
    let selected_direction_sha256 = sha256(&selected_direction_bytes);
    ensure!(selected_direction_sha256 == pair_selection.selected_directions_i8_sha256, "selection direction digest drift");
    ensure!(selected_direction_sha256 == pair_receipt.directions_i8_sha256, "receipt direction digest drift");
    ensure!(prior_receipt.schema == "g0168.provisional_residual_fingerprint_screen.v1", "prior fingerprint schema drift");
    ensure!(prior_receipt.basis_records == PRIOR_BASIS && prior_receipt.probe_records == PROBES_PER_PANEL, "prior fingerprint envelope drift");
    ensure!(prior_receipt.directions == DIRECTIONS, "prior fingerprint direction census drift");
    ensure!(prior_receipt.splitmix_seed == format!("0x{SPLITMIX_SEED:016x}"), "prior fingerprint seed drift");

    ensure!(
        global.nonzero_hinge_signed_lexicographic_prefix.len() == DIRECTIONS,
        "direction census drift"
    );
    let directions = global
        .nonzero_hinge_signed_lexicographic_prefix
        .iter()
        .map(|item| item.direction)
        .collect::<Vec<_>>();
    ensure!(directions.windows(2).all(|pair| pair[0] < pair[1]), "direction order drift");
    for direction in &directions {
        validate_direction(direction)?;
    }

    let basis_set = member.basis_sequences.iter().copied().collect::<BTreeSet<_>>();
    ensure!(basis_set.len() == BASIS && basis_set.iter().all(|sequence| *sequence < RECORDS), "basis envelope drift");
    let mut probe_panel_1 = BTreeSet::new();
    let mut state = SPLITMIX_SEED;
    while probe_panel_1.len() < PROBES_PER_PANEL {
        let sequence = usize::try_from(next_splitmix(&mut state) % u64::try_from(RECORDS)?)?;
        if !basis_set.contains(&sequence) {
            probe_panel_1.insert(sequence);
        }
    }
    let probe_panel_1 = probe_panel_1.into_iter().collect::<Vec<_>>();
    ensure!(
        prior_receipt.selected_records.len() == PRIOR_BASIS + PROBES_PER_PANEL
            && prior_receipt.selected_records[PRIOR_BASIS..] == probe_panel_1,
        "deterministic first probe panel drift"
    );
    let probe_panel_1_set = probe_panel_1.iter().copied().collect::<BTreeSet<_>>();
    let mut probe_panel_2 = BTreeSet::new();
    while probe_panel_2.len() < PROBES_PER_PANEL {
        let sequence = usize::try_from(next_splitmix(&mut state) % u64::try_from(RECORDS)?)?;
        if !basis_set.contains(&sequence) && !probe_panel_1_set.contains(&sequence) {
            probe_panel_2.insert(sequence);
        }
    }
    let probe_panel_2 = probe_panel_2.into_iter().collect::<Vec<_>>();
    ensure!(probe_panel_1_set.is_disjoint(&probe_panel_2.iter().copied().collect()), "probe panels overlap");

    let mut selected_records = member.basis_sequences.clone();
    selected_records.extend(probe_panel_1.iter().copied());
    selected_records.extend(probe_panel_2.iter().copied());
    ensure!(
        selected_records.len() == BASIS + 2 * PROBES_PER_PANEL
            && selected_records.iter().copied().collect::<BTreeSet<_>>().len() == BASIS + 2 * PROBES_PER_PANEL,
        "selected-record census drift"
    );

    let record_major = selected_records
        .par_iter()
        .map(|sequence| -> Result<Vec<i64>> {
            let record = panel.records.get(*sequence).context("selected record out of range")?;
            ensure!(record.sequence == *sequence, "record sequence/index drift");
            hinge_coefficients(record, &directions)
        })
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        record_major.len() == BASIS + 2 * PROBES_PER_PANEL
            && record_major.iter().all(|row| row.len() == DIRECTIONS),
        "fingerprint matrix shape drift"
    );

    let position = selected_records
        .iter()
        .enumerate()
        .map(|(index, sequence)| (*sequence, index))
        .collect::<HashMap<_, _>>();
    let mut exact_dots = (0..DIRECTIONS).map(|_| BigInt::from(0)).collect::<Vec<_>>();
    for term in &member.terms {
        let row = &record_major[*position.get(&term.sequence).context("support outside selected basis")?];
        let coefficient = parse_bigint(&term.coefficient)?;
        for (target, value) in exact_dots.iter_mut().zip(row) {
            *target += &coefficient * BigInt::from(*value);
        }
    }
    let expected = global
        .nonzero_hinge_signed_lexicographic_prefix
        .iter()
        .map(|item| parse_bigint(&item.coefficient))
        .collect::<Result<Vec<_>>>()?;
    ensure!(exact_dots == expected, "global/direct exact 4096-dot bridge failed");

    let file = File::create_new(MATRIX)?;
    let mut writer = BufWriter::with_capacity(1 << 20, file);
    let mut digest = Sha256::new();
    let mut bytes = Vec::with_capacity(DIRECTIONS * 8);
    for row in &record_major {
        bytes.clear();
        for value in row {
            let encoded = value.to_le_bytes();
            digest.update(encoded);
            bytes.extend_from_slice(&encoded);
        }
        writer.write_all(&bytes)?;
    }
    writer.flush()?;
    writer.get_ref().sync_all()?;
    let matrix_bytes = (BASIS + 2 * PROBES_PER_PANEL) * DIRECTIONS * 8;
    ensure!(std::fs::metadata(MATRIX)?.len() == u64::try_from(matrix_bytes)?, "byte census drift");
    let output = json!({
        "schema": "g0178.rank659_two_disjoint_probe_panels.v1",
        "evidence_class": "PROVISIONAL_EXPLORATORY_ONLY_NOT_CERTIFIED",
        "basis_records": BASIS,
        "probe_records_per_panel": PROBES_PER_PANEL,
        "probe_panels": 2,
        "directions": DIRECTIONS,
        "splitmix_seed": format!("0x{SPLITMIX_SEED:016x}"),
        "probe_panel_1_records": probe_panel_1,
        "probe_panel_2_records": probe_panel_2,
        "selected_records": selected_records,
        "matrix_path": MATRIX,
        "matrix_layout": "basis-then-panel1-then-panel2 record-major signed-i64 little-endian",
        "matrix_bytes": matrix_bytes,
        "matrix_sha256": format!("{:x}", digest.finalize()),
        "global_direct_exact_4096_dot_bridge": true,
        "coordinate_envelope": {
            "current_rank": BASIS,
            "previous_rank": PRIOR_BASIS,
            "pair_full_price_directions": PAIR_DIRECTIONS,
            "pair_coordinate_count": PAIR_COORDINATES,
            "pair_coordinate_direction_indices": member.pair_coordinate_direction_indices,
            "pair_coordinate_rows": member.coordinate_rows[PRIOR_BASIS..].to_vec(),
            "pair_witness_sequences": member.pair_witness_sequences,
        },
        "inputs": {
            "panel_sha256": panel_sha256,
            "global_sha256": global_sha256,
            "member_sha256": member_sha256,
            "pair_matrix_sha256": pair_matrix_sha256,
            "pair_receipt_sha256": pair_receipt_sha256,
            "pair_selection_sha256": pair_selection_sha256,
            "prior_fingerprint_receipt_sha256": prior_receipt_sha256,
        },
        "elapsed_seconds": started.elapsed().as_secs_f64(),
        "claim_boundary": "Two finite probe panels only. Rank deficits or residual gaps are targeting evidence, never full-family dependencies or an obstruction claim.",
    });
    let output_bytes = serde_json::to_vec_pretty(&output)?;
    let mut output_file = File::create_new(OUTPUT)?;
    output_file.write_all(&output_bytes)?;
    output_file.write_all(b"\n")?;
    output_file.sync_all()?;
    println!(
        "matrix={} sha256={} panel1={} panel2={} elapsed_seconds={}",
        MATRIX,
        output["matrix_sha256"].as_str().unwrap_or(""),
        PROBES_PER_PANEL,
        PROBES_PER_PANEL,
        output["elapsed_seconds"]
    );
    Ok(())
}
