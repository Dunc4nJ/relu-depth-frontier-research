mod frozen_subject {
    #![allow(dead_code)]

    include!("../../../../math/G-0140/stage_b_pricer/src/main.rs");

    fn reject_value(label: &str, value: &Value, audit_path: &str) -> Result<()> {
        let rejection = validate_source_audit_envelope(value, audit_path);
        ensure!(
            rejection.is_err(),
            "hostile contract probe escaped: {label}"
        );
        println!("REJECT {label}: {}", rejection.unwrap_err());
        Ok(())
    }

    fn reject_raw(label: &str, raw: &[u8]) -> Result<()> {
        let rejection = strict_json_value(raw);
        ensure!(
            rejection.is_err(),
            "hostile raw-JSON probe escaped: {label}"
        );
        println!("REJECT {label}: {}", rejection.unwrap_err());
        Ok(())
    }

    fn exercise_branch(
        label: &str,
        valid: Value,
        audit_path: &str,
        expected_schema: &str,
        duplicate_binding_name: &str,
        expected_main_path: &str,
    ) -> Result<usize> {
        validate_source_audit_envelope(&valid, audit_path)?;
        println!("ACCEPT {label}-exact-valid");
        let mut cases = 1usize;

        let mut mutant = valid.clone();
        mutant["schema"] = Value::String("lookalike-schema-v1".to_string());
        reject_value(&format!("{label}-wrong-schema"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["result"] = Value::String("LOOKALIKE_PASS".to_string());
        reject_value(&format!("{label}-wrong-result"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["verdict"] = Value::String("FAIL".to_string());
        reject_value(&format!("{label}-wrong-verdict"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["no_claim"] = Value::String("nearby no-claim".to_string());
        reject_value(&format!("{label}-wrong-no-claim"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["scientific_output_observed"] = Value::Bool(true);
        reject_value(
            &format!("{label}-scientific-observation-true"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["unknown_extension"] = Value::Bool(true);
        reject_value(&format!("{label}-unknown-root"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["audit_git_commit"] = Value::String("0".repeat(40));
        reject_value(&format!("{label}-audit-git-commit"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["subject"]["unknown_subject_field"] = Value::Bool(true);
        reject_value(&format!("{label}-unknown-subject"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["subject"]["bindings"]["main_source"]["unknown_binding_field"] = Value::Bool(true);
        reject_value(&format!("{label}-unknown-binding"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["required_checks"]["unknown_check"] = Value::Bool(true);
        reject_value(
            &format!("{label}-unknown-required-check"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["required_checks"]
            .as_object_mut()
            .context("required-check fixture is not an object")?
            .remove("duplicate_json_keys_rejected");
        reject_value(
            &format!("{label}-missing-required-check"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["required_checks"]["duplicate_json_keys_rejected"] = Value::Bool(false);
        reject_value(
            &format!("{label}-false-required-check"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let mut mutant = valid.clone();
        let displaced = mutant["subject"]
            .as_object_mut()
            .context("subject fixture is not an object")?
            .remove("bindings")
            .context("subject fixture omits bindings")?;
        mutant["unrelated_receipt_lookalikes"] = displaced;
        reject_value(&format!("{label}-displaced-bindings"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        let decoy = mutant["subject"]["bindings"]
            .as_object_mut()
            .context("bindings fixture is not an object")?
            .remove("main_source")
            .context("bindings fixture omits main_source")?;
        mutant["subject"]["unrelated_main_source_decoy"] = decoy;
        reject_value(
            &format!("{label}-missing-main-plus-decoy"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["subject"]["bindings"][duplicate_binding_name]["path"] =
            Value::String(expected_main_path.to_string());
        reject_value(
            &format!("{label}-duplicate-subject-path"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["subject"]["bindings"]["main_source"]["path"] =
            Value::String("artifacts/decoy/main.rs".to_string());
        reject_value(&format!("{label}-wrong-named-path"), &mutant, audit_path)?;
        cases += 1;

        let mut mutant = valid.clone();
        mutant["preregistration"]["path"] =
            Value::String("artifacts/reviews/decoy/PREREGISTRATION.md".to_string());
        reject_value(
            &format!("{label}-wrong-preregistration-path"),
            &mutant,
            audit_path,
        )?;
        cases += 1;

        let encoded = serde_json::to_string(&valid)?;
        let duplicate_root = format!(
            "{{\"schema\":\"{expected_schema}\",{}",
            encoded
                .strip_prefix('{')
                .context("encoded fixture is not an object")?
        );
        reject_raw(
            &format!("{label}-duplicate-root-key"),
            duplicate_root.as_bytes(),
        )?;
        cases += 1;

        let nested_anchor = "\"agent_name\":\"FreshReviewer\"";
        ensure!(
            encoded.contains(nested_anchor),
            "nested duplicate-key anchor drift"
        );
        let duplicate_nested = encoded.replacen(
            nested_anchor,
            "\"agent_name\":\"FreshReviewer\",\"agent_name\":\"DecoyReviewer\"",
            1,
        );
        reject_raw(
            &format!("{label}-duplicate-nested-key"),
            duplicate_nested.as_bytes(),
        )?;
        cases += 1;

        let trailing = format!("{encoded}\n{{}}");
        reject_raw(&format!("{label}-trailing-data"), trailing.as_bytes())?;
        cases += 1;

        let reparsed = strict_json_value(encoded.as_bytes())?;
        validate_source_audit_envelope(&reparsed, audit_path)?;
        println!("ACCEPT {label}-strict-json-roundtrip");
        cases += 1;

        Ok(cases)
    }

    pub fn run_contract_matrix() -> Result<()> {
        self_test()?;
        println!("ACCEPT frozen-subject-self-test");

        let stage_a_cases = exercise_branch(
            "g0150",
            stage_a_source_audit_fixture(),
            STAGE_A_SOURCE_AUDIT_PATH,
            STAGE_A_SOURCE_AUDIT_SCHEMA,
            "engine_source",
            STAGE_A_SOURCE_PATH,
        )?;
        let stage_b_cases = exercise_branch(
            "g0151",
            stage_b_source_audit_fixture(),
            STAGE_B_SOURCE_AUDIT_PATH,
            STAGE_B_SOURCE_AUDIT_SCHEMA,
            "cargo_manifest",
            STAGE_B_SOURCE_PATH,
        )?;

        ensure!(stage_a_cases == 22, "G-0150 probe census drift");
        ensure!(stage_b_cases == 22, "G-0151 probe census drift");
        println!(
            "G-0151 exact frozen Rust contract probe PASS: stage_a_cases={stage_a_cases} stage_b_cases={stage_b_cases}"
        );
        Ok(())
    }

    pub fn validate_stage_b_receipt_file(receipt_path: &Path) -> Result<()> {
        let receipt = strict_json_value(std::fs::File::open(receipt_path)?)?;
        validate_source_audit_envelope(&receipt, STAGE_B_SOURCE_AUDIT_PATH)?;
        println!("G-0151 proposed receipt accepted by exact frozen Rust envelope");
        Ok(())
    }
}

fn main() -> anyhow::Result<()> {
    let arguments = std::env::args().collect::<Vec<_>>();
    match arguments.as_slice() {
        [_program] => frozen_subject::run_contract_matrix(),
        [_program, flag, receipt] if flag == "--receipt" => {
            frozen_subject::validate_stage_b_receipt_file(std::path::Path::new(receipt))
        }
        _ => anyhow::bail!("usage: g0151-stage-b-final2-contract-probe [--receipt RECEIPT]"),
    }
}
