#![forbid(unsafe_code)]

#[cfg(test)]
mod tests {
    use std::collections::{BTreeMap, BTreeSet};

    const SOURCE: &str = include_str!(
        "../../../../math/G-0140/stage_e_global_replay/src/main.rs"
    );

    const SCIENTIFIC_OUTPUTS: [&str; 5] = [
        "artifacts/math/G-0140/pool128_global_replay_v1.json",
        "artifacts/math/G-0140/pool128_coordinate_prices_v1.json",
        "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json",
        "artifacts/math/G-0140/rank_aware_master_result_v1.json",
        "artifacts/math/G-0140/new_member_global_replay_v1.json",
    ];

    const REQUIRED_CHECKS: [&str; 20] = [
        "exact_named_binding_contract",
        "displaced_recursive_lookalikes_rejected",
        "correct_decoy_with_missing_named_binding_rejected",
        "duplicate_path_occurrences_rejected",
        "unknown_envelope_fields_rejected",
        "audit_git_commit_rejected",
        "duplicate_json_keys_rejected",
        "trailing_json_data_rejected",
        "producer_self_test_passed",
        "producer_static_preflight_passed",
        "compiled_source_manifest_lock_match_working_bytes",
        "engine_byte_identity_with_stage_a_verified",
        "g0155_stage_d_source_audit_gate_verified",
        "scientific_output_commit_chain_gate_verified",
        "scientific_outputs_excluded_from_manifest_bindings",
        "dynamic_stage_d_member_contract_verified",
        "global_zero_and_residual_branches_verified",
        "complete_label_census_and_end_rehash_verified",
        "overwrite_refusal_verified",
        "prohibited_scientific_modes_not_run",
    ];

    fn between<'a>(source: &'a str, start: &str, end: &str) -> &'a str {
        let start_index = source.find(start).expect("start marker must exist");
        let tail = &source[start_index..];
        let end_index = tail.find(end).expect("end marker must exist");
        &tail[..end_index]
    }

    fn source_check_fields() -> Vec<&'static str> {
        between(
            SOURCE,
            "struct StageESourceAuditChecks {",
            "struct StageESourceAuditReceipt {",
        )
        .lines()
        .filter_map(|line| {
            line.trim()
                .strip_suffix(": bool,")
                .map(str::trim)
        })
        .collect()
    }

    fn binding(path: &str, tag: &str) -> (String, String) {
        (path.to_string(), format!("sha256:{tag}"))
    }

    fn manifest_union(
        direct: &BTreeMap<String, String>,
        transitive: &[(String, String)],
    ) -> Result<BTreeMap<String, String>, String> {
        let mut union = BTreeMap::new();
        for (path, digest) in direct {
            if union.insert(path.clone(), digest.clone()).is_some() {
                return Err(format!("duplicate direct binding: {path}"));
            }
        }
        for (path, digest) in transitive {
            if union.insert(path.clone(), digest.clone()).is_some() {
                return Err(format!("duplicate direct/transitive binding: {path}"));
            }
        }
        Ok(union)
    }

    fn output_boundary(union: &BTreeMap<String, String>) -> Result<(), String> {
        for output in SCIENTIFIC_OUTPUTS {
            if union.contains_key(output) {
                return Err(format!("future scientific output bound: {output}"));
            }
        }
        Ok(())
    }

    #[derive(Clone)]
    struct ReceiptChain {
        b_binds_a: &'static str,
        c_binds_a: &'static str,
        c_binds_b: &'static str,
        d_binds_a: &'static str,
        d_binds_b: &'static str,
        d_binds_c: &'static str,
        ancestry: BTreeSet<(&'static str, &'static str)>,
    }

    fn valid_receipt_chain(chain: &ReceiptChain) -> bool {
        chain.b_binds_a == "A"
            && chain.c_binds_a == "A"
            && chain.c_binds_b == "B"
            && chain.d_binds_a == "A"
            && chain.d_binds_b == "B"
            && chain.d_binds_c == "C"
            && [("manifest", "A"), ("A", "B"), ("B", "C"), ("C", "D")]
                .into_iter()
                .all(|edge| chain.ancestry.contains(&edge))
    }

    fn valid_chain_fixture() -> ReceiptChain {
        ReceiptChain {
            b_binds_a: "A",
            c_binds_a: "A",
            c_binds_b: "B",
            d_binds_a: "A",
            d_binds_b: "B",
            d_binds_c: "C",
            ancestry: BTreeSet::from([
                ("manifest", "A"),
                ("A", "B"),
                ("B", "C"),
                ("C", "D"),
            ]),
        }
    }

    #[test]
    fn exact_stage_e_receipt_contract_is_exhaustive() {
        assert_eq!(source_check_fields(), REQUIRED_CHECKS);

        let semantics = between(
            SOURCE,
            "fn validate_stage_e_source_audit_semantics",
            "fn validate_stage_e_source_audit_gate",
        );
        for field in REQUIRED_CHECKS {
            let needle = format!("checks.{field}");
            assert_eq!(
                semantics.matches(&needle).count(),
                1,
                "required check not enforced exactly once: {field}"
            );
        }
        assert!(SOURCE.contains("#[serde(deny_unknown_fields)]\nstruct StageESourceAuditChecks"));
        assert!(SOURCE.contains("#[serde(deny_unknown_fields)]\nstruct StageESourceAuditReceipt"));
        assert!(SOURCE.contains(
            "const STAGE_E_SOURCE_AUDIT_SCHEMA: &str = \"max11-g0157-g0140-stage-e-final2-source-audit-v1\";"
        ));
        assert!(SOURCE.contains(
            "const SOURCE_CUSTODY_PASS_RESULT: &str = \"SOURCE_CUSTODY_AUDIT_PASS_T1\";"
        ));
        assert!(SOURCE.contains(
            "const STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS: &str = \"T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT\";"
        ));
        assert!(semantics.contains("receipt.result == SOURCE_CUSTODY_PASS_RESULT"));
        assert!(semantics.contains("receipt.evidence_class == STAGE_E_SOURCE_AUDIT_EVIDENCE_CLASS"));
        assert!(semantics.contains("receipt.claim_boundary == STAGE_E_SOURCE_AUDIT_CLAIM_BOUNDARY"));
        assert!(semantics.contains("receipt.no_claim == STAGE_E_SOURCE_AUDIT_NO_CLAIM"));
    }

    #[test]
    fn direct_and_transitive_union_rejects_every_scientific_output() {
        let source_array = between(
            SOURCE,
            "const G0140_SCIENTIFIC_OUTPUT_PATHS",
            "const PRIOR_MASTER_RESULT_PATH",
        );
        for constant in [
            "G0140_STAGE_A_RESULT_PATH",
            "STAGE_B_OUTPUT_PATH",
            "STAGE_C_OUTPUT_PATH",
            "STAGE_D_OUTPUT_PATH",
            "STAGE_E_OUTPUT_PATH",
        ] {
            assert_eq!(source_array.matches(constant).count(), 1);
        }

        let boundary = between(
            SOURCE,
            "fn validate_protocol_manifest_output_boundary",
            "#[derive(Default)]",
        );
        assert!(boundary.contains("for output_path in G0140_SCIENTIFIC_OUTPUT_PATHS"));
        assert!(boundary.contains("!protocol.bindings_by_path.contains_key(output_path)"));

        let manifest = between(SOURCE, "fn validate_g0140_manifest", "fn validate_panel");
        let direct_index = manifest
            .find("for (label, binding) in &manifest.bindings")
            .expect("direct binding loop");
        let transitive_index = manifest
            .find("for binding in &manifest.transitive_inputs")
            .expect("transitive binding loop");
        let snapshot_index = manifest
            .find("let snapshot = ManifestSnapshot")
            .expect("manifest snapshot");
        let boundary_index = manifest
            .find("validate_protocol_manifest_output_boundary(&snapshot)")
            .expect("output boundary call");
        assert!(direct_index < transitive_index);
        assert!(transitive_index < snapshot_index);
        assert!(snapshot_index < boundary_index);
        assert!(manifest[direct_index..transitive_index]
            .contains("bindings_by_path\n                    .insert(binding.path.clone(), binding.sha256.clone())"));
        assert!(manifest[transitive_index..snapshot_index]
            .contains("bindings_by_path\n                    .insert(binding.path.clone(), binding.sha256.clone())"));

        let affirmative_chain = valid_chain_fixture();
        assert!(valid_receipt_chain(&affirmative_chain));

        for output in SCIENTIFIC_OUTPUTS {
            let direct = BTreeMap::from([
                binding("synthetic/source-audit-receipt.json", "audit"),
                binding(output, "hostile-direct"),
            ]);
            let union = manifest_union(&direct, &[]).expect("direct union construction");
            assert!(output_boundary(&union).is_err());
            assert!(valid_receipt_chain(&affirmative_chain));
            println!("HOSTILE_EXCLUSION origin=direct path={output} result=REJECT");

            let direct = BTreeMap::from([binding(
                "synthetic/source-audit-receipt.json",
                "audit",
            )]);
            let transitive = [binding(output, "hostile-transitive")];
            let union = manifest_union(&direct, &transitive)
                .expect("transitive union construction");
            assert!(output_boundary(&union).is_err());
            assert!(valid_receipt_chain(&affirmative_chain));
            println!("HOSTILE_EXCLUSION origin=transitive path={output} result=REJECT");
        }
    }

    #[test]
    fn exact_receipt_bridges_committed_blobs_and_ancestry_remain_enforced() {
        let stage_b = between(SOURCE, "fn validate_stage_b_receipt", "fn validate_old_member_receipt");
        assert!(stage_b.contains("receipt.stage_a_receipt == *stage_a_binding"));

        let stage_c = between(SOURCE, "fn load_stage_c_selection_view", "fn validate_stage_d_trials");
        assert!(stage_c.contains("receipt.stage_a_receipt == *stage_a_binding"));

        let stage_d = between(
            SOURCE,
            "fn load_and_validate_stage_d_member",
            "struct ValidatedInputs",
        );
        assert!(stage_d.contains("binding_matches(root, &candidate.stage_b_receipt, STAGE_B_OUTPUT_PATH)"));
        assert!(stage_d.contains("&candidate.stage_c_receipt"));
        assert!(stage_d.contains("stage_c.stage_b_receipt == candidate.stage_b_receipt"));

        let load = between(SOURCE, "fn load_and_validate_inputs", "fn term_receipt");
        for label in ["\"A\".to_string()", "\"B\".to_string()", "\"C\".to_string()", "\"D\".to_string()"] {
            assert!(load.contains(label), "missing committed output binding: {label}");
        }
        assert!(load.contains("git_commit_for_path(root, G0140_STAGE_A_RESULT_PATH)"));
        assert!(load.contains("git_commit_for_path(root, STAGE_B_OUTPUT_PATH)"));
        assert!(load.contains("git_commit_for_path(root, STAGE_C_OUTPUT_PATH)"));
        assert!(load.contains("git_commit_for_path(root, STAGE_D_OUTPUT_PATH)"));
        assert!(load.contains("&protocol_manifest_commit,\n        &stage_output_git_commits[\"A\"]"));
        assert!(load.contains("[(\"A\", \"B\"), (\"B\", \"C\"), (\"C\", \"D\")]"));

        let committed_blob = between(SOURCE, "fn git_commit_for_path", "fn git_is_ancestor");
        assert!(committed_blob.contains("[\"log\", \"-1\", \"--format=%H\", \"--\", path]"));
        assert!(committed_blob.contains("[\"show\", &format!(\"{commit}:{path}\")]"));
        assert!(committed_blob.contains(
            "sha256_bytes(&blob.stdout) == sha256_path(&checked_repo_path(root, path)?)?"
        ));

        let chain = valid_chain_fixture();
        assert!(valid_receipt_chain(&chain));

        for edge in [("manifest", "A"), ("A", "B"), ("B", "C"), ("C", "D")] {
            let mut mutant = chain.clone();
            mutant.ancestry.remove(&edge);
            assert!(!valid_receipt_chain(&mutant), "ancestry mutant escaped: {edge:?}");
        }

        let mut mutant = chain.clone();
        mutant.b_binds_a = "decoy-A";
        assert!(!valid_receipt_chain(&mutant));
        let mut mutant = chain.clone();
        mutant.c_binds_b = "decoy-B";
        assert!(!valid_receipt_chain(&mutant));
        let mut mutant = chain;
        mutant.d_binds_c = "decoy-C";
        assert!(!valid_receipt_chain(&mutant));
    }
}
