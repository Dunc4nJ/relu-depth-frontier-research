use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{N, Record};
use num_bigint::BigInt;
use rayon::prelude::*;
use serde::{Deserialize, Serialize};
use serde_json::json;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, HashMap};
use std::env;
use std::fs::{File, read};
use std::io::Write;
use std::path::Path;
use std::time::Instant;

#[path = "/data/projects/relu-depth-frontier-research/artifacts/math/G-0164/stage_b_global_replay/src/engine.rs"]
mod engine;

use engine::{factorial, validated_full_normal_form};

const PANEL: &str = "/data/projects/relu-depth-frontier-research/artifacts/math/G-0113/panel_solver_input_v1.json";
const PREFIX_K: usize = 4096;

#[derive(Deserialize)]
struct Panel {
    records: Vec<Record>,
}

#[derive(Deserialize)]
struct Member {
    provisional_only: bool,
    result: String,
    target_scale: String,
    terms: Vec<Term>,
}

#[derive(Deserialize)]
struct Term {
    sequence: usize,
    coefficient: String,
}

#[derive(Default)]
struct Aggregate {
    hinges: HashMap<[i8; N], BigInt>,
    linear: [BigInt; N],
    terms: usize,
    hinge_entries_processed: u64,
    labelled_permutations: u64,
}

#[derive(Serialize)]
struct Hinge {
    direction: [i8; N],
    coefficient: String,
}

fn canonical_bigint(raw: &str) -> Result<BigInt> {
    ensure!(
        raw == "0" || {
            let digits = raw.strip_prefix('-').unwrap_or(raw);
            !digits.is_empty()
                && !digits.starts_with('0')
                && digits.bytes().all(|byte| byte.is_ascii_digit())
        },
        "noncanonical integer: {raw}"
    );
    BigInt::parse_bytes(raw.as_bytes(), 10).context("parse integer")
}

fn sha256(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn merge(mut left: Aggregate, right: Aggregate) -> Aggregate {
    if left.hinges.len() < right.hinges.len() {
        return merge(right, left);
    }
    left.terms += right.terms;
    left.hinge_entries_processed += right.hinge_entries_processed;
    left.labelled_permutations += right.labelled_permutations;
    for (target, value) in left.linear.iter_mut().zip(right.linear) {
        *target += value;
    }
    for (direction, value) in right.hinges {
        *left.hinges.entry(direction).or_default() += value;
    }
    left
}

fn residual_digest(aggregate: &Aggregate) -> String {
    let mut digest = Sha256::new();
    digest.update(b"G0168-PROVISIONAL-668-MEMBER-COMPLETE-EXACT-RESIDUAL-V1\0");
    for (direction, coefficient) in aggregate.hinges.iter().collect::<BTreeMap<_, _>>() {
        if *coefficient == BigInt::from(0) {
            continue;
        }
        digest.update(b"H\t");
        digest.update(direction.map(|value| value as u8));
        digest.update(b"\t");
        digest.update(coefficient.to_string().as_bytes());
        digest.update(b"\n");
    }
    for (coordinate, coefficient) in aggregate.linear.iter().enumerate() {
        if *coefficient == BigInt::from(0) {
            continue;
        }
        digest.update(b"L\t");
        digest.update(coordinate.to_le_bytes());
        digest.update(b"\t");
        digest.update(coefficient.to_string().as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

fn main() -> Result<()> {
    let arguments = env::args().collect::<Vec<_>>();
    ensure!(arguments.len() == 3, "usage: GLOBAL_REPLAY MEMBER OUTPUT");
    let member_path = &arguments[1];
    let output_path = &arguments[2];
    ensure!(!Path::new(output_path).exists(), "refusing to overwrite {output_path}");
    let started = Instant::now();
    let panel_bytes = read(PANEL).with_context(|| format!("read {PANEL}"))?;
    let member_bytes = read(member_path).with_context(|| format!("read {member_path}"))?;
    let panel: Panel = serde_json::from_slice(&panel_bytes).context("parse panel")?;
    let member: Member = serde_json::from_slice(&member_bytes).context("parse member")?;
    ensure!(panel.records.len() == 163_740, "family census drift");
    ensure!(
        member.provisional_only
            && member.result.starts_with("EXACT_")
            && member.result.ends_with("_MEMBER_PROVISIONAL"),
        "finite replay premise missing"
    );
    ensure!(!member.terms.is_empty(), "empty member");
    let mut sequences = member.terms.iter().map(|term| term.sequence).collect::<Vec<_>>();
    let original_sequences = sequences.clone();
    sequences.sort_unstable();
    sequences.dedup();
    ensure!(sequences.len() == member.terms.len(), "duplicate term sequence");
    ensure!(
        original_sequences.windows(2).all(|pair| pair[0] < pair[1]),
        "terms not strictly sequence ordered"
    );

    let mut aggregate = member
        .terms
        .par_iter()
        .map(|term| -> Result<Aggregate> {
            let record = panel.records.get(term.sequence).context("term sequence out of range")?;
            ensure!(record.sequence == term.sequence, "record sequence/index disagreement");
            let coefficient = canonical_bigint(&term.coefficient)?;
            ensure!(coefficient != BigInt::from(0), "zero support coefficient");
            let form = validated_full_normal_form(record)?;
            let mut out = Aggregate::default();
            out.terms = 1;
            out.hinge_entries_processed = u64::try_from(form.hinges.len())?;
            out.labelled_permutations = form.labelled_permutations;
            for (target, value) in out.linear.iter_mut().zip(form.linear) {
                *target += &coefficient * value;
            }
            for (direction, value) in form.hinges {
                *out.hinges.entry(direction).or_default() += &coefficient * value;
            }
            Ok(out)
        })
        .try_reduce(Aggregate::default, |left, right| Ok(merge(left, right)))?;

    ensure!(aggregate.terms == member.terms.len(), "term census drift");
    ensure!(
        aggregate.labelled_permutations
            == u64::try_from(member.terms.len())? * factorial(N),
        "labelled permutation census drift"
    );
    let target_scale = canonical_bigint(&member.target_scale)?;
    aggregate.linear[N - 1] -= &target_scale * BigInt::from(factorial(N));

    let nonzero = aggregate
        .hinges
        .iter()
        .filter(|(_, coefficient)| **coefficient != BigInt::from(0))
        .map(|(direction, coefficient)| (*direction, coefficient.to_string()))
        .collect::<BTreeMap<_, _>>();
    let prefix = nonzero
        .iter()
        .take(PREFIX_K)
        .map(|(direction, coefficient)| Hinge {
            direction: *direction,
            coefficient: coefficient.clone(),
        })
        .collect::<Vec<_>>();
    let linear = aggregate
        .linear
        .iter()
        .enumerate()
        .filter(|(_, coefficient)| **coefficient != BigInt::from(0))
        .map(|(coordinate, coefficient)| json!({
            "coordinate": coordinate,
            "coefficient": coefficient.to_string(),
        }))
        .collect::<Vec<_>>();
    let global_zero = nonzero.is_empty() && linear.is_empty();
    let output = json!({
        "schema": "g0168.provisional_member_complete_exact_global_replay.v2",
        "evidence_class": "PROVISIONAL_EXPLORATORY_ONLY_NOT_CERTIFIED",
        "result": if global_zero { "EXACT_GLOBAL_ZERO" } else { "EXACT_GLOBAL_NONZERO" },
        "global_zero": global_zero,
        "inputs": {
            "panel_path": PANEL,
            "panel_sha256": sha256(&panel_bytes),
            "member_path": member_path,
            "member_sha256": sha256(&member_bytes),
            "records": panel.records.len(),
            "support_terms": member.terms.len(),
        },
        "exact_census": {
            "factorial_11": factorial(N),
            "labelled_permutations": aggregate.labelled_permutations,
            "hinge_entries_processed": aggregate.hinge_entries_processed,
            "nonzero_hinge_directions": nonzero.len(),
            "nonzero_linear_coordinates": linear.len(),
        },
        "complete_exact_residual_sha256": residual_digest(&aggregate),
        "first_nonzero_hinge": prefix.first(),
        "nonzero_hinge_signed_lexicographic_prefix": prefix,
        "nonzero_linear": linear,
        "elapsed_seconds": started.elapsed().as_secs_f64(),
        "claim_boundary": "Complete exact symbolic replay of this provisional finite member; source/result require independent certification before promotion.",
    });
    let bytes = serde_json::to_vec_pretty(&output)?;
    let mut file = File::create_new(output_path)?;
    file.write_all(&bytes)?;
    file.write_all(b"\n")?;
    file.sync_all()?;
    println!(
        "global_zero={} nonzero_hinges={} nonzero_linear={} output={}",
        global_zero,
        nonzero.len(),
        linear.len(),
        output_path
    );
    Ok(())
}
