use anyhow::{Result, anyhow, ensure};
use std::path::PathBuf;

mod frozen_evaluator {
    #![allow(dead_code)]
    #![allow(clippy::needless_range_loop)]

    include!("../../G-0116/src/main.rs");

    use g0113_panel_solver::rank::LeftAnnihilator;

    const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
    const ROWS_SHA256: &str = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c";
    const EVALUATOR_SHA256: &str =
        "875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd";
    const EVALUATOR_REPORT_SHA256: &str =
        "94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310";
    const RANK_CORE_SHA256: &str =
        "006968bbf4f428e4fa492d06b61b43d64b25e5febcc0751ec81c07d90a399994";
    const RANK_ADDENDUM_SHA256: &str =
        "ae4effe084ac0408c3d107a5c0437cff0c88792a3a1218cf9d3866efaf8962b3";
    const TARGET_I64_LE_SHA256: &str =
        "19beb89b85e3a95989be9a97d749a48609cb4912897bc20da60bfcd1690bf260";
    const FIRST_STAGE: usize = 133_449;
    const RECORDS: usize = 163_740;
    const P1: u32 = 2_000_081;
    const P2: u32 = 3_000_017;

    #[derive(Clone, Debug, Deserialize, Serialize)]
    struct RepresentativeDescriptor {
        left_added_edge: [usize; 2],
        right_added_edge: [usize; 2],
        source_term: usize,
    }

    #[derive(Clone, Debug, Deserialize)]
    struct SolverRecord {
        #[serde(flatten)]
        evaluation: Record,
        orbit_index: usize,
        signed_class_sha256: String,
        stage: String,
        in_disjoint: bool,
        in_shared_distinct: bool,
        representative: RepresentativeDescriptor,
    }

    #[derive(Debug, Deserialize)]
    struct SolverInput {
        schema: String,
        rows_path: String,
        primes: Vec<u32>,
        target: Vec<i128>,
        control_sequences: Vec<usize>,
        records: Vec<SolverRecord>,
    }

    #[derive(Debug, Deserialize)]
    struct GateControl {
        sequence: usize,
        panel_vector_sha256: String,
    }

    #[derive(Debug, Deserialize)]
    struct GateReport {
        result: String,
        bindings: BTreeMap<String, String>,
        controls: Vec<GateControl>,
        all_histograms_exact: bool,
        all_panel_vectors_exact: bool,
        all_formal_assignment_censuses_exact: bool,
        branch_swap_preserved: bool,
        edge_sign_mutant_rejected: bool,
    }

    #[derive(Debug, Serialize)]
    struct PrimeReport {
        prime: u32,
        disjoint_rank: usize,
        disjoint_target_member: bool,
        union_rank: usize,
        union_target_member: bool,
        selected_sequences: Vec<usize>,
    }

    #[derive(Debug, Serialize)]
    struct RetainedColumn {
        sequence: usize,
        orbit_index: usize,
        signed_class_sha256: String,
        stage: String,
        in_disjoint: bool,
        in_shared_distinct: bool,
        representative: RepresentativeDescriptor,
        selected_p1: bool,
        selected_p2: bool,
        gate_control: bool,
        panel_vector_sha256: String,
        vector: Vec<i128>,
    }

    #[derive(Debug, Serialize)]
    struct RetainedOutput {
        schema: &'static str,
        bindings: BTreeMap<String, String>,
        columns: Vec<RetainedColumn>,
    }

    #[derive(Debug, Serialize)]
    struct ScanOutput {
        schema: &'static str,
        result: String,
        claim_boundary: &'static str,
        bindings: BTreeMap<String, String>,
        rayon_threads: usize,
        records: usize,
        disjoint_records: usize,
        shared_distinct_only_records: usize,
        target_i64_le_sha256: String,
        target_i128_le_sha256: String,
        all_vectors_i128_le_sha256: String,
        ordered_vector_digests_sha256: String,
        control_vector_sha256: BTreeMap<usize, String>,
        retained_columns: usize,
        value_minimum: i128,
        value_maximum: i128,
        max_feedback_vertices: usize,
        active_vertex_histogram: BTreeMap<usize, usize>,
        graph_beta_histogram: BTreeMap<usize, usize>,
        primes: Vec<PrimeReport>,
        disjoint_modular_ranks_agree: bool,
        disjoint_modular_target_decisions_agree: bool,
        union_modular_ranks_agree: bool,
        union_modular_target_decisions_agree: bool,
        modular_ranks_agree: bool,
        modular_target_decisions_agree: bool,
        wall_seconds: f64,
    }

    fn source_path(relative: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join(relative)
    }

    fn digest_i128(values: &[i128]) -> String {
        let mut digest = Sha256::new();
        for value in values {
            digest.update(value.to_le_bytes());
        }
        format!("{:x}", digest.finalize())
    }

    fn digest_i64(values: &[i128]) -> Result<String> {
        let mut digest = Sha256::new();
        for value in values {
            let narrowed = i64::try_from(*value).context("target does not fit i64")?;
            digest.update(narrowed.to_le_bytes());
        }
        Ok(format!("{:x}", digest.finalize()))
    }

    fn write_json_exclusive<T: Serialize>(path: &Path, value: &T) -> Result<()> {
        let destination = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .with_context(|| format!("refusing to overwrite or create {}", path.display()))?;
        let mut writer = BufWriter::new(destination);
        serde_json::to_writer_pretty(&mut writer, value)?;
        writer.write_all(b"\n")?;
        writer.flush()?;
        Ok(())
    }

    fn validate_input(input: &SolverInput) -> Result<()> {
        ensure!(
            input.schema == "max11-g0113-panel-solver-input-v1",
            "input schema drift"
        );
        ensure!(
            input.rows_path == "artifacts/math/G-0111/dual_rows_v1.json",
            "bound row path drift"
        );
        ensure!(input.primes == [P1, P2], "prime drift");
        ensure!(input.target.len() == 301, "target dimension drift");
        ensure!(input.records.len() == RECORDS, "record count drift");
        ensure!(
            input.control_sequences == [0, 1, 284, 5_341, 30_223, 133_449, 134_301],
            "literal-control sequence drift"
        );
        for (sequence, record) in input.records.iter().enumerate() {
            ensure!(record.evaluation.sequence == sequence, "sequence drift");
            ensure!(
                record.evaluation.signed_mass <= 5,
                "signed-mass bound drift"
            );
            if sequence < FIRST_STAGE {
                ensure!(
                    record.stage == "DISJOINT" && record.in_disjoint,
                    "DISJOINT stage drift"
                );
            } else {
                ensure!(
                    record.stage == "SHARED_DISTINCT_ONLY"
                        && !record.in_disjoint
                        && record.in_shared_distinct,
                    "SHARED_DISTINCT_ONLY stage drift"
                );
            }
        }
        ensure!(
            input.records[..FIRST_STAGE]
                .windows(2)
                .all(|pair| pair[0].orbit_index < pair[1].orbit_index),
            "DISJOINT orbit order drift"
        );
        ensure!(
            input.records[FIRST_STAGE..]
                .windows(2)
                .all(|pair| pair[0].orbit_index < pair[1].orbit_index),
            "SHARED_DISTINCT_ONLY orbit order drift"
        );
        Ok(())
    }

    fn validate_gate(report_path: &Path) -> Result<BTreeMap<usize, String>> {
        ensure!(
            sha256_path(report_path)? == EVALUATOR_REPORT_SHA256,
            "G-0116 report binding drift"
        );
        let gate: GateReport = serde_json::from_reader(BufReader::new(File::open(report_path)?))?;
        ensure!(
            gate.result == "PASS_ACCELERATOR_GATE",
            "G-0116 gate not green"
        );
        ensure!(
            gate.bindings.get("input").map(String::as_str) == Some(INPUT_SHA256)
                && gate.bindings.get("rows").map(String::as_str) == Some(ROWS_SHA256)
                && gate.bindings.get("producer").map(String::as_str) == Some(EVALUATOR_SHA256),
            "G-0116 report transitive binding drift"
        );
        ensure!(
            gate.all_histograms_exact
                && gate.all_panel_vectors_exact
                && gate.all_formal_assignment_censuses_exact
                && gate.branch_swap_preserved
                && gate.edge_sign_mutant_rejected,
            "G-0116 semantic control drift"
        );
        let controls = gate
            .controls
            .into_iter()
            .map(|control| (control.sequence, control.panel_vector_sha256))
            .collect::<BTreeMap<_, _>>();
        ensure!(controls.len() == 8, "G-0116 control census drift");
        Ok(controls)
    }

    fn combined_agreement(
        disjoint_p1: (usize, bool),
        disjoint_p2: (usize, bool),
        union_p1: (usize, bool),
        union_p2: (usize, bool),
    ) -> (bool, bool) {
        (
            disjoint_p1.0 == disjoint_p2.0 && union_p1.0 == union_p2.0,
            disjoint_p1.1 == disjoint_p2.1 && union_p1.1 == union_p2.1,
        )
    }

    pub fn run_scan(
        input_path: &Path,
        rows_path: &Path,
        gate_report_path: &Path,
        report_path: &Path,
        retained_path: &Path,
    ) -> Result<()> {
        ensure!(report_path != retained_path, "output paths must differ");
        ensure!(
            !report_path.exists() && !retained_path.exists(),
            "refusing to overwrite solver outputs"
        );
        let evaluator_path = source_path("../G-0116/src/main.rs");
        let rank_path = source_path("src/rank.rs");
        let addendum_path = source_path("PANEL_SOLVER_RANK_ADDENDUM.md");
        ensure!(
            sha256_path(&evaluator_path)? == EVALUATOR_SHA256,
            "frozen G-0116 evaluator source drift"
        );
        ensure!(
            sha256_path(&rank_path)? == RANK_CORE_SHA256,
            "frozen rank source drift"
        );
        ensure!(
            sha256_path(&addendum_path)? == RANK_ADDENDUM_SHA256,
            "rank addendum drift"
        );
        ensure!(
            sha256_path(input_path)? == INPUT_SHA256,
            "input binding drift"
        );
        ensure!(sha256_path(rows_path)? == ROWS_SHA256, "row binding drift");
        let expected_control_hashes = validate_gate(gate_report_path)?;

        let started = Instant::now();
        let input: SolverInput = serde_json::from_reader(BufReader::new(File::open(input_path)?))?;
        validate_input(&input)?;
        let target_i64_hash = digest_i64(&input.target)?;
        ensure!(
            target_i64_hash == TARGET_I64_LE_SHA256,
            "target normalization drift"
        );
        let target_i128_hash = digest_i128(&input.target);
        let rows_document: RowsDocument =
            serde_json::from_reader(BufReader::new(File::open(rows_path)?))?;
        ensure!(
            rows_document.schema == "max11-g0111-actual-dual-rows-v1",
            "row schema drift"
        );
        ensure!(rows_document.rows.len() == 301, "row count drift");

        let mut p1 = LeftAnnihilator::new(301, P1);
        let mut p2 = LeftAnnihilator::new(301, P2);
        let mut disjoint_p1 = None;
        let mut disjoint_p2 = None;
        let mut all_vector_bytes = Sha256::new();
        let mut ordered_vector_digests = Sha256::new();
        let mut observed_controls = BTreeMap::<usize, String>::new();
        let mut retained = Vec::<RetainedColumn>::new();
        let mut value_minimum = i128::MAX;
        let mut value_maximum = i128::MIN;
        let mut max_feedback_vertices = 0usize;
        let mut active_histogram = BTreeMap::<usize, usize>::new();
        let mut beta_histogram = BTreeMap::<usize, usize>::new();

        for (sequence, solver_record) in input.records.iter().enumerate() {
            let record = &solver_record.evaluation;
            let edges = signed_edges(record, false)?;
            let beta = graph_beta(record.active_vertices, &edges);
            *active_histogram.entry(record.active_vertices).or_default() += 1;
            *beta_histogram.entry(beta).or_default() += 1;
            let (histogram, feedback) = cycle_cut_histogram(record, &edges)?;
            max_feedback_vertices = max_feedback_vertices.max(feedback);
            let vector = panel_vector(&histogram, record.active_vertices, &rows_document.rows)?;
            ensure!(vector.len() == 301, "panel-vector dimension drift");

            let mut vector_digest = Sha256::new();
            for value in &vector {
                let bytes = value.to_le_bytes();
                vector_digest.update(bytes);
                all_vector_bytes.update(bytes);
                value_minimum = value_minimum.min(*value);
                value_maximum = value_maximum.max(*value);
            }
            let vector_digest = vector_digest.finalize();
            ordered_vector_digests.update(vector_digest);
            let vector_hash = format!("{vector_digest:x}");

            if let Some(expected) = expected_control_hashes.get(&sequence) {
                ensure!(
                    vector_hash == *expected,
                    "frozen vector control failed at sequence {sequence}"
                );
                observed_controls.insert(sequence, vector_hash.clone());
            }

            let selected_p1 = p1.ingest_exact(sequence, &vector);
            let selected_p2 = p2.ingest_exact(sequence, &vector);
            let gate_control = expected_control_hashes.contains_key(&sequence);
            if selected_p1 || selected_p2 || gate_control {
                retained.push(RetainedColumn {
                    sequence,
                    orbit_index: solver_record.orbit_index,
                    signed_class_sha256: solver_record.signed_class_sha256.clone(),
                    stage: solver_record.stage.clone(),
                    in_disjoint: solver_record.in_disjoint,
                    in_shared_distinct: solver_record.in_shared_distinct,
                    representative: solver_record.representative.clone(),
                    selected_p1,
                    selected_p2,
                    gate_control,
                    panel_vector_sha256: vector_hash,
                    vector,
                });
            }

            if sequence + 1 == FIRST_STAGE {
                disjoint_p1 = Some((p1.rank(), p1.contains_exact(&input.target)));
                disjoint_p2 = Some((p2.rank(), p2.contains_exact(&input.target)));
                eprintln!(
                    "G0113_STAGE DISJOINT records={} p1_rank={} p2_rank={} elapsed={:.3}",
                    FIRST_STAGE,
                    p1.rank(),
                    p2.rank(),
                    started.elapsed().as_secs_f64()
                );
            }
            if (sequence + 1) % 5_000 == 0 || sequence + 1 == RECORDS {
                eprintln!(
                    "G0113_PROGRESS records={}/{} p1_rank={} p2_rank={} retained={} elapsed={:.3}",
                    sequence + 1,
                    RECORDS,
                    p1.rank(),
                    p2.rank(),
                    retained.len(),
                    started.elapsed().as_secs_f64()
                );
            }
        }

        ensure!(
            observed_controls == expected_control_hashes,
            "G-0116 control replay census drift"
        );
        let (disjoint_p1_rank, disjoint_p1_member) =
            disjoint_p1.context("missing p1 stage boundary")?;
        let (disjoint_p2_rank, disjoint_p2_member) =
            disjoint_p2.context("missing p2 stage boundary")?;
        let union_p1_member = p1.contains_exact(&input.target);
        let union_p2_member = p2.contains_exact(&input.target);
        let disjoint_ranks_agree = disjoint_p1_rank == disjoint_p2_rank;
        let disjoint_targets_agree = disjoint_p1_member == disjoint_p2_member;
        let union_ranks_agree = p1.rank() == p2.rank();
        let union_targets_agree = union_p1_member == union_p2_member;
        let (ranks_agree, targets_agree) = combined_agreement(
            (disjoint_p1_rank, disjoint_p1_member),
            (disjoint_p2_rank, disjoint_p2_member),
            (p1.rank(), union_p1_member),
            (p2.rank(), union_p2_member),
        );
        let result = if !ranks_agree || !targets_agree {
            "MODULAR_DISAGREEMENT"
        } else if p1.rank() == 301 {
            "FULL_PANEL_RANK_SEED_PENDING_EXACT_Q"
        } else if union_p1_member {
            "MODULAR_MEMBER_PENDING_EXACT_Q"
        } else {
            "MODULAR_NONMEMBER_PENDING_EXACT_SEPARATOR"
        };

        let mut bindings = BTreeMap::new();
        bindings.insert("input".to_string(), INPUT_SHA256.to_string());
        bindings.insert("rows".to_string(), ROWS_SHA256.to_string());
        bindings.insert("evaluator".to_string(), EVALUATOR_SHA256.to_string());
        bindings.insert(
            "evaluator_report".to_string(),
            EVALUATOR_REPORT_SHA256.to_string(),
        );
        bindings.insert("rank_core".to_string(), RANK_CORE_SHA256.to_string());
        bindings.insert(
            "rank_addendum".to_string(),
            RANK_ADDENDUM_SHA256.to_string(),
        );
        bindings.insert(
            "producer".to_string(),
            sha256_path(&source_path("src/main.rs"))?,
        );
        let retained_output = RetainedOutput {
            schema: "max11-g0113-panel-retained-columns-v1",
            bindings: bindings.clone(),
            columns: retained,
        };
        write_json_exclusive(retained_path, &retained_output)?;
        bindings.insert("retained".to_string(), sha256_path(retained_path)?);

        let report = ScanOutput {
            schema: "max11-g0113-panel-scan-v1",
            result: result.to_string(),
            claim_boundary: "Finite 301-row modular rank and membership only; no global CPWL identity, characteristic-zero separator, completeness theorem, or MAX11 result.",
            bindings,
            rayon_threads: 12,
            records: RECORDS,
            disjoint_records: FIRST_STAGE,
            shared_distinct_only_records: RECORDS - FIRST_STAGE,
            target_i64_le_sha256: target_i64_hash,
            target_i128_le_sha256: target_i128_hash,
            all_vectors_i128_le_sha256: format!("{:x}", all_vector_bytes.finalize()),
            ordered_vector_digests_sha256: format!("{:x}", ordered_vector_digests.finalize()),
            control_vector_sha256: observed_controls,
            retained_columns: retained_output.columns.len(),
            value_minimum,
            value_maximum,
            max_feedback_vertices,
            active_vertex_histogram: active_histogram,
            graph_beta_histogram: beta_histogram,
            primes: vec![
                PrimeReport {
                    prime: P1,
                    disjoint_rank: disjoint_p1_rank,
                    disjoint_target_member: disjoint_p1_member,
                    union_rank: p1.rank(),
                    union_target_member: union_p1_member,
                    selected_sequences: p1.selected_sequences().to_vec(),
                },
                PrimeReport {
                    prime: P2,
                    disjoint_rank: disjoint_p2_rank,
                    disjoint_target_member: disjoint_p2_member,
                    union_rank: p2.rank(),
                    union_target_member: union_p2_member,
                    selected_sequences: p2.selected_sequences().to_vec(),
                },
            ],
            disjoint_modular_ranks_agree: disjoint_ranks_agree,
            disjoint_modular_target_decisions_agree: disjoint_targets_agree,
            union_modular_ranks_agree: union_ranks_agree,
            union_modular_target_decisions_agree: union_targets_agree,
            modular_ranks_agree: ranks_agree,
            modular_target_decisions_agree: targets_agree,
            wall_seconds: started.elapsed().as_secs_f64(),
        };
        write_json_exclusive(report_path, &report)?;
        println!("{}", serde_json::to_string_pretty(&report)?);
        Ok(())
    }

    #[cfg(test)]
    mod scanner_tests {
        use super::combined_agreement;

        #[test]
        fn stage_disagreement_cannot_be_hidden_by_final_agreement() {
            assert_eq!(
                combined_agreement((17, true), (16, false), (23, true), (23, true)),
                (false, false)
            );
        }

        #[test]
        fn both_boundaries_must_agree() {
            assert_eq!(
                combined_agreement((17, false), (17, false), (23, true), (23, true)),
                (true, true)
            );
            assert_eq!(
                combined_agreement((17, false), (17, false), (23, true), (22, false)),
                (false, false)
            );
        }
    }
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 6,
        "usage: g0113-panel-solver INPUT.json ROWS.json G0116_GATE.json REPORT.json RETAINED.json"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .map_err(|error| anyhow!("cannot build frozen 12-thread Rayon pool: {error}"))?;
    frozen_evaluator::run_scan(
        &PathBuf::from(&args[1]),
        &PathBuf::from(&args[2]),
        &PathBuf::from(&args[3]),
        &PathBuf::from(&args[4]),
        &PathBuf::from(&args[5]),
    )
}
