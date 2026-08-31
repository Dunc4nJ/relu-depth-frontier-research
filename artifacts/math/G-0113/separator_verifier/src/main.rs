use anyhow::{Result, anyhow, ensure};
use std::path::PathBuf;

mod frozen_evaluator {
    #![allow(dead_code)]
    #![allow(clippy::needless_range_loop)]

    include!("../../../G-0116/src/main.rs");

    use num_bigint::BigInt;
    use num_traits::Zero;
    use serde_json::Value;
    use std::str::FromStr;

    const INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
    const ROWS_SHA256: &str = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c";
    const GATE_SHA256: &str = "94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310";
    const EVALUATOR_SHA256: &str =
        "875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd";
    const SCANNER_SHA256: &str = "8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f";
    const EXACT_POSTPROCESSOR_SHA256: &str =
        "07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48";
    const RECORDS: usize = 163_740;

    #[derive(Debug, Deserialize)]
    struct ReplayInput {
        schema: String,
        target: Vec<i128>,
        records: Vec<Record>,
    }

    #[derive(Debug, Serialize)]
    struct Failure {
        sequence: usize,
        separator_pairing: String,
        panel_vector_sha256: String,
    }

    #[derive(Debug, Serialize)]
    struct ReplayOutput {
        schema: &'static str,
        result: &'static str,
        claim_boundary: &'static str,
        bindings: BTreeMap<String, String>,
        records: usize,
        rayon_threads: usize,
        separator_entries: usize,
        target_pairing: String,
        zero_column_pairings: usize,
        nonzero_column_pairings: usize,
        first_failure: Option<Failure>,
        all_vectors_i128_le_sha256: String,
        ordered_vector_digests_sha256: String,
        control_vector_sha256: BTreeMap<usize, String>,
        all_scan_hashes_replayed: bool,
        all_controls_replayed: bool,
        wall_seconds: f64,
    }

    fn source_path(relative: &str) -> PathBuf {
        Path::new(env!("CARGO_MANIFEST_DIR")).join(relative)
    }

    fn json_string<'a>(value: &'a Value, path: &[&str]) -> Result<&'a str> {
        let mut cursor = value;
        for key in path {
            cursor = cursor
                .get(*key)
                .with_context(|| format!("missing JSON field {}", path.join(".")))?;
        }
        cursor
            .as_str()
            .with_context(|| format!("non-string JSON field {}", path.join(".")))
    }

    fn json_bool(value: &Value, key: &str) -> Result<bool> {
        value
            .get(key)
            .and_then(Value::as_bool)
            .with_context(|| format!("missing/non-boolean JSON field {key}"))
    }

    fn write_json_exclusive<T: Serialize>(path: &Path, value: &T) -> Result<()> {
        let destination = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .with_context(|| format!("refusing to overwrite {}", path.display()))?;
        let mut writer = BufWriter::new(destination);
        serde_json::to_writer_pretty(&mut writer, value)?;
        writer.write_all(b"\n")?;
        writer.flush()?;
        Ok(())
    }

    fn parse_control_hashes(scan: &Value) -> Result<BTreeMap<usize, String>> {
        let object = scan
            .get("control_vector_sha256")
            .and_then(Value::as_object)
            .context("missing control hash object")?;
        object
            .iter()
            .map(|(sequence, digest)| {
                Ok((
                    sequence
                        .parse::<usize>()
                        .context("invalid control sequence")?,
                    digest
                        .as_str()
                        .context("invalid control digest")?
                        .to_string(),
                ))
            })
            .collect()
    }

    fn exact_pairing(separator: &[BigInt], values: &[i128]) -> BigInt {
        debug_assert_eq!(separator.len(), values.len());
        let mut pairing = BigInt::zero();
        for (coefficient, value) in separator.iter().zip(values) {
            if *value != 0 {
                pairing += coefficient * BigInt::from(*value);
            }
        }
        pairing
    }

    pub fn replay(
        input_path: &Path,
        rows_path: &Path,
        gate_path: &Path,
        scan_path: &Path,
        exact_path: &Path,
        output_path: &Path,
    ) -> Result<()> {
        ensure!(!output_path.exists(), "refusing to overwrite replay output");
        ensure!(
            sha256_path(input_path)? == INPUT_SHA256,
            "input binding drift"
        );
        ensure!(sha256_path(rows_path)? == ROWS_SHA256, "row binding drift");
        ensure!(sha256_path(gate_path)? == GATE_SHA256, "gate binding drift");
        ensure!(
            sha256_path(&source_path("../../G-0116/src/main.rs"))? == EVALUATOR_SHA256,
            "evaluator source binding drift"
        );
        let scan_sha = sha256_path(scan_path)?;
        let exact_sha = sha256_path(exact_path)?;
        let scan: Value = serde_json::from_reader(BufReader::new(File::open(scan_path)?))?;
        let exact: Value = serde_json::from_reader(BufReader::new(File::open(exact_path)?))?;
        ensure!(
            json_string(&scan, &["schema"])? == "max11-g0113-panel-scan-v1",
            "scan schema drift"
        );
        ensure!(
            json_string(&scan, &["bindings", "producer"])? == SCANNER_SHA256,
            "scanner source drift"
        );
        for key in [
            "disjoint_modular_ranks_agree",
            "disjoint_modular_target_decisions_agree",
            "union_modular_ranks_agree",
            "union_modular_target_decisions_agree",
            "modular_ranks_agree",
            "modular_target_decisions_agree",
        ] {
            ensure!(json_bool(&scan, key)?, "modular disagreement at {key}");
        }
        ensure!(
            json_string(&exact, &["schema"])? == "max11-g0113-panel-exact-postprocess-v1",
            "exact schema drift"
        );
        ensure!(
            json_string(&exact, &["bindings", "producer"])? == EXACT_POSTPROCESSOR_SHA256,
            "exact postprocessor source drift"
        );
        ensure!(
            json_string(&exact, &["bindings", "report"])? == scan_sha,
            "exact/scan binding drift"
        );
        ensure!(
            json_string(&exact, &["payload", "result"])?
                == "EXACT_Q_NONMEMBER_RETAINED_SPAN_PENDING_ALL_COLUMN_REPLAY",
            "separator replay requires the exact nonmember branch"
        );
        let separator_values = exact
            .get("payload")
            .and_then(|payload| payload.get("primitive_integer_separator"))
            .and_then(Value::as_array)
            .context("missing separator array")?;
        let separator = separator_values
            .iter()
            .map(|value| {
                BigInt::from_str(value.as_str().context("separator entry must be a string")?)
                    .context("invalid separator integer")
            })
            .collect::<Result<Vec<_>>>()?;
        ensure!(separator.len() == 301, "separator dimension drift");
        let expected_target_pairing =
            BigInt::from_str(json_string(&exact, &["payload", "target_pairing"])?)
                .context("invalid exact target pairing")?;
        ensure!(!expected_target_pairing.is_zero(), "zero target pairing");

        let input: ReplayInput = serde_json::from_reader(BufReader::new(File::open(input_path)?))?;
        ensure!(
            input.schema == "max11-g0113-panel-solver-input-v1",
            "input schema drift"
        );
        ensure!(input.records.len() == RECORDS, "record count drift");
        ensure!(input.target.len() == 301, "target dimension drift");
        ensure!(
            input
                .records
                .iter()
                .enumerate()
                .all(|(sequence, record)| record.sequence == sequence),
            "record sequence drift"
        );
        let rows_document: RowsDocument =
            serde_json::from_reader(BufReader::new(File::open(rows_path)?))?;
        ensure!(
            rows_document.schema == "max11-g0111-actual-dual-rows-v1",
            "row schema drift"
        );
        ensure!(rows_document.rows.len() == 301, "row count drift");
        let target_pairing = exact_pairing(&separator, &input.target);
        ensure!(
            target_pairing == expected_target_pairing,
            "target separator pairing drift"
        );

        let expected_all_vectors = json_string(&scan, &["all_vectors_i128_le_sha256"])?;
        let expected_ordered_digests = json_string(&scan, &["ordered_vector_digests_sha256"])?;
        let expected_controls = parse_control_hashes(&scan)?;
        ensure!(expected_controls.len() == 8, "control census drift");
        let mut observed_controls = BTreeMap::new();
        let mut all_vector_bytes = Sha256::new();
        let mut ordered_vector_digests = Sha256::new();
        let mut failures = 0usize;
        let mut first_failure = None;
        let started = Instant::now();

        for (sequence, record) in input.records.iter().enumerate() {
            let edges = signed_edges(record, false)?;
            let (histogram, _) = cycle_cut_histogram(record, &edges)?;
            let vector = panel_vector(&histogram, record.active_vertices, &rows_document.rows)?;
            ensure!(vector.len() == 301, "panel vector dimension drift");
            let mut vector_digest = Sha256::new();
            for value in &vector {
                let bytes = value.to_le_bytes();
                vector_digest.update(bytes);
                all_vector_bytes.update(bytes);
            }
            let vector_digest = vector_digest.finalize();
            ordered_vector_digests.update(vector_digest);
            let vector_hash = format!("{vector_digest:x}");
            if let Some(expected) = expected_controls.get(&sequence) {
                ensure!(
                    vector_hash == *expected,
                    "control vector drift at {sequence}"
                );
                observed_controls.insert(sequence, vector_hash.clone());
            }
            let pairing = exact_pairing(&separator, &vector);
            if !pairing.is_zero() {
                failures += 1;
                if first_failure.is_none() {
                    first_failure = Some(Failure {
                        sequence,
                        separator_pairing: pairing.to_string(),
                        panel_vector_sha256: vector_hash,
                    });
                }
            }
            if (sequence + 1) % 5_000 == 0 || sequence + 1 == RECORDS {
                eprintln!(
                    "G0113_SEPARATOR_PROGRESS records={}/{} failures={} elapsed={:.3}",
                    sequence + 1,
                    RECORDS,
                    failures,
                    started.elapsed().as_secs_f64()
                );
            }
        }

        let all_vectors_hash = format!("{:x}", all_vector_bytes.finalize());
        let ordered_hash = format!("{:x}", ordered_vector_digests.finalize());
        let all_scan_hashes_replayed =
            all_vectors_hash == expected_all_vectors && ordered_hash == expected_ordered_digests;
        let all_controls_replayed = observed_controls == expected_controls;
        ensure!(all_scan_hashes_replayed, "complete scan hash replay failed");
        ensure!(all_controls_replayed, "complete control replay failed");
        let result = if failures == 0 {
            "PASS_EXACT_ALL_COLUMN_SEPARATOR"
        } else {
            "REJECTED_BY_EXACT_COLUMN"
        };
        let mut bindings = BTreeMap::new();
        bindings.insert("input".to_string(), INPUT_SHA256.to_string());
        bindings.insert("rows".to_string(), ROWS_SHA256.to_string());
        bindings.insert("gate".to_string(), GATE_SHA256.to_string());
        bindings.insert("evaluator".to_string(), EVALUATOR_SHA256.to_string());
        bindings.insert("scan".to_string(), scan_sha);
        bindings.insert("exact_postprocess".to_string(), exact_sha);
        bindings.insert(
            "producer".to_string(),
            sha256_path(&source_path("src/main.rs"))?,
        );
        let output = ReplayOutput {
            schema: "max11-g0113-exact-all-column-separator-replay-v1",
            result,
            claim_boundary: "Exact finite-panel separation for the enumerated source-derived degree-five family only; no family-completeness, unrestricted-network, or MAX11 claim.",
            bindings,
            records: RECORDS,
            rayon_threads: 12,
            separator_entries: separator.len(),
            target_pairing: target_pairing.to_string(),
            zero_column_pairings: RECORDS - failures,
            nonzero_column_pairings: failures,
            first_failure,
            all_vectors_i128_le_sha256: all_vectors_hash,
            ordered_vector_digests_sha256: ordered_hash,
            control_vector_sha256: observed_controls,
            all_scan_hashes_replayed,
            all_controls_replayed,
            wall_seconds: started.elapsed().as_secs_f64(),
        };
        write_json_exclusive(output_path, &output)?;
        println!("{}", serde_json::to_string_pretty(&output)?);
        Ok(())
    }

    #[cfg(test)]
    mod tests {
        use super::{BigInt, FromStr, exact_pairing};

        #[test]
        fn pairing_preserves_arbitrary_precision_and_sign() {
            let huge =
                BigInt::from_str("100000000000000000000000000000000000000000000000007").unwrap();
            let separator = vec![huge.clone(), -huge.clone(), BigInt::from(3)];
            let values = vec![5, 2, -7];
            assert_eq!(exact_pairing(&separator, &values), huge * 3 - 21);
        }
    }
}

fn main() -> Result<()> {
    let args = std::env::args().collect::<Vec<_>>();
    ensure!(
        args.len() == 7,
        "usage: g0113-separator-verifier INPUT ROWS GATE SCAN EXACT OUTPUT"
    );
    rayon::ThreadPoolBuilder::new()
        .num_threads(12)
        .build_global()
        .map_err(|error| anyhow!("cannot build frozen 12-thread Rayon pool: {error}"))?;
    frozen_evaluator::replay(
        &PathBuf::from(&args[1]),
        &PathBuf::from(&args[2]),
        &PathBuf::from(&args[3]),
        &PathBuf::from(&args[4]),
        &PathBuf::from(&args[5]),
        &PathBuf::from(&args[6]),
    )
}
