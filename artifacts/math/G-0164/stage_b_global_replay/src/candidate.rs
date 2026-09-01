use crate::engine::{exact_hinge_coefficients, exact_linear_vector, factorial};
use anyhow::{Context, Result, ensure};
use g0117_global_coordinate_pricer::{N, Record, validate_direction};
use num_bigint::BigInt;
use serde::de::{self, DeserializeOwned, MapAccess, SeqAccess, Visitor};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};
use std::collections::{BTreeMap, BTreeSet, HashSet};
use std::fs::{File, OpenOptions};
use std::io::{BufReader, Read, Seek, SeekFrom, Write};
use std::path::{Component, Path, PathBuf};
use std::process::Command;

const RECORDS: usize = 163_740;
const PANEL_ROWS: usize = 301;
const LINEAR_ROWS: usize = N;
const INHERITED_DIRECTIONS: usize = 100;
const POOL_ROWS: usize = 128;
const TOTAL_DIRECTIONS: usize = INHERITED_DIRECTIONS + POOL_ROWS;
const BASE_ROWS: usize = PANEL_ROWS + LINEAR_ROWS + INHERITED_DIRECTIONS;
const ROWS: usize = BASE_ROWS + POOL_ROWS;
const RANK: usize = 349;
const PANEL_ENTRY_BYTES: usize = 16;
const PANEL_COLUMN_BYTES: usize = PANEL_ROWS * PANEL_ENTRY_BYTES;

pub const FINITE_MANIFEST_PATH: &str = "artifacts/math/G-0164/all128_manifest_v1.json";
pub const FINITE_MEMBER_PATH: &str = "artifacts/math/G-0164/all128_direct_basis_member_v1.json";
const PREREGISTRATION_PATH: &str = "artifacts/math/G-0164/PREREGISTRATION.md";
const SOLVER_PATH: &str = "artifacts/math/G-0164/all128_direct_basis_master_v1.py";
const SOURCE_AUDIT_PATH: &str =
    "artifacts/reviews/G-0165-g0164-all128-master-source/SOURCE_AUDIT_RECEIPT.json";
const STAGE_A_PATH: &str = "artifacts/math/G-0140/pool128_global_replay_v1.json";
const STAGE_B_PATH: &str = "artifacts/math/G-0140/pool128_coordinate_prices_v1.json";
const STAGE_C_PATH: &str = "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json";
const G0140_MANIFEST_PATH: &str = "artifacts/math/G-0140/pool128_manifest_v1.json";
const PANEL_INPUT_PATH: &str = "artifacts/math/G-0113/panel_solver_input_v1.json";
const PANEL_CACHE_PATH: &str = "artifacts/math/G-0117/full_family_cache_v1.i128le";
const PANEL_CACHE_MANIFEST_PATH: &str = "artifacts/math/G-0117/full_family_cache_manifest_v1.json";

const FINITE_MANIFEST_COMMIT: &str = "c8965eec01026c8547aeec5c65b34894f6434686";
const FINITE_MEMBER_COMMIT: &str = "86491d7c2595b65216f99f4b14471b1bc408246a";
const FINITE_MANIFEST_SHA256: &str =
    "c6d6b0f995f26d87321e3c27a36bf39ed6d8eb40a185a85f25b73a5e98120420";
const FINITE_MEMBER_SHA256: &str =
    "bc4d1c58587aef6cd3b555b166ba7ec8e0f365cb0089cfd889a235e8f2e20119";
const PREREGISTRATION_SHA256: &str =
    "f28813a182327e38e713c8a20e9039f12d9722861455dcb1a5fb0bb332b00c10";
const PREREGISTRATION_COMMIT: &str = "dbd488609efda9d6a4eba33fb2c82d67d49b9288";
const SOLVER_SHA256: &str = "d8ea3d21e419f5a0fa7303a347af068e8f37e3f6fe53730879535f78b5070d90";
const SOLVER_COMMIT: &str = "05e8acaebf1d6e293049858e3d85a1cda9a25eae";
const SOURCE_AUDIT_SHA256: &str =
    "a0974b19fed5206839d129473f10087cdebce05785b052a5e11b1e80795af7d2";
const SOURCE_AUDIT_COMMIT: &str = "fca70c517a124979bc3830e833258725933c0a0a";
const STAGE_A_SHA256: &str = "13735a5c6fc987864c97d8c466863f0de376e5dc8fe446381fdc2d1ebd302e4c";
const STAGE_B_SHA256: &str = "7a923266e812bdd29fad2ecdf2d6b5cf2be85e4aacab3f92fe82bfd3b89f5c81";
const STAGE_C_SHA256: &str = "d2a847b2d39b9111804cac1c3e4f9cc9f1fa152598c5a98610b7c5cc68cb9ba6";
const G0140_MANIFEST_SHA256: &str =
    "79ea5f98ab4594aef377e6512473193b76d25470e71fdf0a823f0ee400aa3e6f";
const BASIS_SEQUENCES_SHA256: &str =
    "c9ec5dbb017e2f735a115ca2eb757adf4d93f072a287f08286c2776b29ec08b3";
const BASIS_MATRIX_SHA256: &str =
    "7451a36e42c479819b6f9ae28ec8c2f7b23360ddc5203b17cf9e3417d1ac9d10";
const SQUARE_MATRIX_SHA256: &str =
    "f06bf820562a96575274bd8358b7ca0eef695e3e991034072deecf97823d3606";
const TARGET_SHA256: &str = "a30ec0a4ff135350f217363831c6ffd2ee0a44f74b4d14549aa3b88da3967874";
const ZERO_540_SHA256: &str = "72863dbaf92ec1aab5a46f8f176a642aa04861a7816654368e8567e5f1d23067";
const PANEL_INPUT_SHA256: &str = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8";
const PANEL_CACHE_MANIFEST_SHA256: &str =
    "e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf";
const PANEL_CACHE_SHA256: &str = "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b";
const SELECTED_DIRECTIONS_SHA256: &str =
    "2cb4c036ee887d9fd285eba3794a80205e6d47f9a9cd48c8ed0618417d88d0e3";
const POOL_RESIDUALS_SHA256: &str =
    "f4a5ad8418ebfa21f08a2d4e8f7d6652e589e7868e6c206d90de6ff00562c7f1";
const RATIONAL_COEFFICIENTS_SHA256: &str =
    "6c41ea0987e37cdc4712d0c589a6325843dae74583b66fdefeb8bf8e66a88b6d";
const INTEGER_COEFFICIENTS_SHA256: &str =
    "7669849235c573ba39b20219e77b5378fcba57c600328f02eb3704543691759f";
const CANDIDATE_INPUT_SNAPSHOT_SHA256: &str =
    "b5317efdad4d2edd6ede0160e5b131688ef37c63f4296c24832e2e09f18acff1";
const MUTANT_RESIDUALS_SHA256: &str =
    "73728d99a6d6c8767db2d6c1b4895776cd7ade62c74003dffa2d949652f47d77";
const FINITE_CLAIM_BOUNDARY: &str = "Exact membership only for the frozen G-0140 540-row target in the frozen 163,740-column family, using one preregistered 349-column basis member. Complete global replay has not yet been run, so this is not a MAX11 identity, lower bound, minimality result, unrestricted statement, all-n theorem, or Lean theorem.";

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Binding {
    pub path: String,
    pub sha256: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CommitBinding {
    pub path: String,
    pub sha256: String,
    #[serde(alias = "commit")]
    pub git_commit: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FinitePlannedOutput {
    pub path: String,
    pub schema: String,
    pub result: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct FiniteManifest {
    pub schema: String,
    pub result: String,
    pub claim_boundary: String,
    pub preregistration: CommitBinding,
    pub solver: CommitBinding,
    pub source_audit: CommitBinding,
    pub stage_a_receipt: Binding,
    pub stage_b_receipt: Binding,
    pub stage_c_receipt: Binding,
    pub records: usize,
    pub base_rows: usize,
    pub appended_rows: usize,
    pub rows: usize,
    pub rank: usize,
    pub basis_sequences_u64le_sha256: String,
    pub basis_i128le_sha256: String,
    pub square_i128le_sha256: String,
    pub target_i128le_sha256: String,
    pub input_snapshot: BTreeMap<String, String>,
    pub input_snapshot_sha256: String,
    pub planned_output: FinitePlannedOutput,
    pub scientific_solve_executed: bool,
    pub scientific_output_created: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct Term {
    pub sequence: usize,
    pub coefficient: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct DirectBasisMutantReceipt {
    pub basis_index: usize,
    pub sequence: usize,
    pub first_nonzero_row: usize,
    pub first_nonzero_residual: String,
    pub nonzero_rows: usize,
    pub residuals_decimal_lf_sha256: String,
    pub rejected: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DirectBasisMember {
    pub schema: String,
    pub result: String,
    pub claim_boundary: String,
    pub manifest: Binding,
    pub solver: Binding,
    pub source_audit: Binding,
    pub stage_a_receipt: Binding,
    pub stage_b_receipt: Binding,
    pub stage_c_receipt: Binding,
    pub n: usize,
    pub records: usize,
    pub base_rows: usize,
    pub appended_rows: usize,
    pub rows: usize,
    pub selected_pool_indices: Vec<usize>,
    pub selected_directions: Vec<[i8; N]>,
    pub selected_directions_i8_sha256: String,
    pub target: Vec<String>,
    pub target_i128le_sha256: String,
    pub target_construction: String,
    pub rank: usize,
    pub augmented_rank: usize,
    pub basis_sequences: Vec<usize>,
    pub basis_sequences_u64le_sha256: String,
    pub coordinate_rows: Vec<usize>,
    pub basis_i128le_sha256: String,
    pub square_i128le_sha256: String,
    pub rational_coefficients: Vec<String>,
    pub rational_coefficients_decimal_lf_sha256: String,
    pub integer_coefficients: Vec<String>,
    pub integer_coefficients_decimal_lf_sha256: String,
    pub target_scale: String,
    pub support_columns: usize,
    pub terms: Vec<Term>,
    pub all_540_rational_rows_replayed: bool,
    pub rational_residuals_decimal_lf_sha256: String,
    pub all_540_primitive_integer_rows_replayed: bool,
    pub integer_residuals_decimal_lf_sha256: String,
    pub primitive_denominator_clearing: bool,
    pub coefficient_plus_one_mutant: DirectBasisMutantReceipt,
    pub prior_target_scale: String,
    pub prior_target_scale_not_used_as_input: bool,
    pub complete_basis_reused: bool,
    pub pricing_recomputed: bool,
    pub rank_discovery_recomputed: bool,
    pub complete_family_scan_recomputed: bool,
    pub column_generation_executed: bool,
    pub alternative_basis_or_nullspace_search_executed: bool,
    pub input_snapshot_sha256: String,
    pub inputs_rehashed_at_end: bool,
    pub wall_seconds: f64,
    pub maximum_rss_kib: u64,
}

#[derive(Clone, Debug, Serialize)]
pub struct FiniteReplayReceipt {
    pub rows: usize,
    pub panel_rows: usize,
    pub linear_rows: usize,
    pub accumulated_hinge_rows: usize,
    pub selected_basis_columns: usize,
    pub selected_basis_i128le_sha256: String,
    pub square_i128le_sha256: String,
    pub selected_basis_digest_replayed: bool,
    pub square_digest_replayed: bool,
    pub cache_layout: &'static str,
    pub arithmetic: &'static str,
    pub all_rows_exactly_replayed: bool,
    pub residuals_decimal_lf_sha256: String,
    pub coefficient_plus_one_mutant: DirectBasisMutantReceipt,
}

pub struct ValidatedCandidate {
    pub manifest: FiniteManifest,
    pub manifest_binding: Binding,
    pub finite_manifest_binding: Binding,
    pub candidate: DirectBasisMember,
    pub candidate_binding: Binding,
    pub records: Vec<Record>,
    pub accumulated_directions: Vec<[i8; N]>,
    pub finite_replay: FiniteReplayReceipt,
    /// All finite-stage inputs plus the finite manifest and member themselves.
    pub input_snapshot: BTreeMap<String, String>,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct ExactHinge {
    direction: [i8; N],
    coefficient: String,
}

#[derive(Clone, Debug, Deserialize, Serialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct AccumulatedDirectionCheck {
    index: usize,
    source: String,
    source_index: usize,
    direction: [i8; N],
    aggregate_coefficient: String,
    direct_dp_coefficient: String,
    routes_agree: bool,
    exact_zero: bool,
}

#[derive(Deserialize)]
struct StageAPoolView {
    schema: String,
    result: String,
    g0140_manifest: Binding,
    rows: usize,
    records: usize,
    selected_rank: usize,
    support_columns: usize,
    terms: usize,
    complete_global_replay: bool,
    all_hinge_and_linear_residuals_zero: bool,
    accumulated_direction_checks: Vec<AccumulatedDirectionCheck>,
    all_100_accumulated_directions_exact_zero: bool,
    all_11_linear_residuals_exact_zero: bool,
    pool_k: usize,
    pool_count: usize,
    pool_directions_i8_sha256: String,
    pool_exact_residuals_decimal_lf_sha256: String,
    pool: Vec<ExactHinge>,
    inputs_rehashed_at_end: bool,
    manifest_rehashed_at_end: bool,
    candidate_rehashed_at_end: bool,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct PanelInput {
    schema: String,
    control_sequences: Vec<usize>,
    primes: [u64; 2],
    records: Vec<Record>,
    rows_path: String,
    target: Vec<i64>,
}

#[derive(Deserialize)]
struct CacheManifest {
    schema: String,
    result: String,
    records: usize,
    rows: usize,
    entry_bytes: usize,
    payload_bytes: u64,
    layout: String,
    integer_width: String,
    endianness: String,
    data_sha256: String,
}

struct StrictValue(Value);

impl<'de> Deserialize<'de> for StrictValue {
    fn deserialize<D>(deserializer: D) -> std::result::Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        struct StrictVisitor;

        impl<'de> Visitor<'de> for StrictVisitor {
            type Value = StrictValue;

            fn expecting(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
                formatter.write_str("JSON without duplicate object keys")
            }

            fn visit_bool<E>(self, value: bool) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Bool(value)))
            }

            fn visit_i64<E>(self, value: i64) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Number(value.into())))
            }

            fn visit_u64<E>(self, value: u64) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Number(value.into())))
            }

            fn visit_f64<E>(self, value: f64) -> std::result::Result<Self::Value, E>
            where
                E: de::Error,
            {
                serde_json::Number::from_f64(value)
                    .map(Value::Number)
                    .map(StrictValue)
                    .ok_or_else(|| E::custom("non-finite JSON number"))
            }

            fn visit_str<E>(self, value: &str) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::String(value.to_string())))
            }

            fn visit_string<E>(self, value: String) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::String(value)))
            }

            fn visit_none<E>(self) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Null))
            }

            fn visit_unit<E>(self) -> std::result::Result<Self::Value, E> {
                Ok(StrictValue(Value::Null))
            }

            fn visit_some<D>(self, deserializer: D) -> std::result::Result<Self::Value, D::Error>
            where
                D: serde::Deserializer<'de>,
            {
                StrictValue::deserialize(deserializer)
            }

            fn visit_seq<A>(self, mut sequence: A) -> std::result::Result<Self::Value, A::Error>
            where
                A: SeqAccess<'de>,
            {
                let mut values = Vec::new();
                while let Some(value) = sequence.next_element::<StrictValue>()? {
                    values.push(value.0);
                }
                Ok(StrictValue(Value::Array(values)))
            }

            fn visit_map<A>(self, mut map: A) -> std::result::Result<Self::Value, A::Error>
            where
                A: MapAccess<'de>,
            {
                let mut values = serde_json::Map::new();
                while let Some((key, value)) = map.next_entry::<String, StrictValue>()? {
                    if values.insert(key.clone(), value.0).is_some() {
                        return Err(<A::Error as de::Error>::custom(format!(
                            "duplicate JSON key: {key}"
                        )));
                    }
                }
                Ok(StrictValue(Value::Object(values)))
            }
        }

        deserializer.deserialize_any(StrictVisitor)
    }
}

pub fn strict_json_value(reader: impl Read) -> Result<Value> {
    let mut deserializer = serde_json::Deserializer::from_reader(reader);
    let value = StrictValue::deserialize(&mut deserializer)?.0;
    deserializer.end()?;
    Ok(value)
}

pub fn strict_json<T: DeserializeOwned>(reader: impl Read) -> Result<T> {
    serde_json::from_value(strict_json_value(reader)?).context("strict JSON schema validation")
}

pub fn sha256_path(path: &Path) -> Result<String> {
    let mut source = File::open(path).with_context(|| format!("open {}", path.display()))?;
    let mut digest = Sha256::new();
    let mut buffer = [0u8; 1 << 20];
    loop {
        let read = source.read(&mut buffer)?;
        if read == 0 {
            break;
        }
        digest.update(&buffer[..read]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

pub fn sha256_bytes(value: &[u8]) -> String {
    format!("{:x}", Sha256::digest(value))
}

fn is_sha256(value: &str) -> bool {
    value.len() == 64
        && value
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
}

pub fn checked_repo_path(root: &Path, raw: &str) -> Result<PathBuf> {
    let relative = Path::new(raw);
    ensure!(
        !raw.is_empty()
            && relative.is_relative()
            && relative
                .components()
                .all(|component| matches!(component, Component::Normal(_))),
        "path is not a contained repository-relative path: {raw}"
    );
    let canonical_root = root
        .canonicalize()
        .context("canonicalize repository root")?;
    let mut cursor = canonical_root.clone();
    for component in relative.components() {
        let Component::Normal(piece) = component else {
            unreachable!()
        };
        cursor.push(piece);
        let metadata = std::fs::symlink_metadata(&cursor)
            .with_context(|| format!("stat bound path component {}", cursor.display()))?;
        ensure!(
            !metadata.file_type().is_symlink(),
            "symlink input path forbidden: {}",
            cursor.display()
        );
    }
    let resolved = cursor
        .canonicalize()
        .with_context(|| format!("canonicalize repository path {raw}"))?;
    ensure!(
        resolved.starts_with(&canonical_root),
        "path escapes repository: {raw}"
    );
    ensure!(resolved.is_file(), "bound input is not a file: {raw}");
    Ok(resolved)
}

pub fn binding_for_path(root: &Path, path: &str) -> Result<Binding> {
    Ok(Binding {
        path: path.to_string(),
        sha256: sha256_path(&checked_repo_path(root, path)?)?,
    })
}

fn binding_matches(root: &Path, binding: &Binding, path: &str, expected: &str) -> Result<()> {
    ensure!(
        binding.path == path
            && binding.sha256 == expected
            && sha256_path(&checked_repo_path(root, path)?)? == expected,
        "binding drift: {path}"
    );
    Ok(())
}

pub fn git_commit_for_path(root: &Path, path: &str) -> Result<String> {
    let resolved = checked_repo_path(root, path)?;
    let result = Command::new("git")
        .args(["log", "-1", "--format=%H", "--", path])
        .current_dir(root)
        .output()
        .context("run git log")?;
    ensure!(result.status.success(), "git log failed for {path}");
    let commit = String::from_utf8(result.stdout)?.trim().to_string();
    ensure!(
        commit.len() == 40 && commit.bytes().all(|byte| byte.is_ascii_hexdigit()),
        "missing Git commit for {path}"
    );
    let blob = Command::new("git")
        .args(["show", &format!("{commit}:{path}")])
        .current_dir(root)
        .output()
        .context("run git show")?;
    ensure!(blob.status.success(), "git show failed for {path}");
    ensure!(
        sha256_bytes(&blob.stdout) == sha256_path(&resolved)?,
        "working bytes differ from committed blob: {path}"
    );
    Ok(commit)
}

pub fn git_is_ancestor(root: &Path, ancestor: &str, descendant: &str, label: &str) -> Result<()> {
    let status = Command::new("git")
        .args(["merge-base", "--is-ancestor", ancestor, descendant])
        .current_dir(root)
        .status()
        .context("run git merge-base")?;
    ensure!(status.success(), "Git ancestry failure: {label}");
    Ok(())
}

pub fn publish_exclusive(path: &Path, bytes: &[u8]) -> Result<()> {
    ensure!(!path.exists(), "refusing to overwrite output");
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    ensure!(parent.is_dir(), "output parent missing");
    let file_name = path
        .file_name()
        .and_then(|name| name.to_str())
        .context("output filename is not UTF-8")?;
    let temporary = path.with_file_name(format!(".{file_name}.tmp.{}", std::process::id()));
    ensure!(
        !temporary.exists(),
        "exclusive temporary output already exists"
    );
    let write_result = (|| -> Result<()> {
        let mut file = OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temporary)?;
        file.write_all(bytes)?;
        file.flush()?;
        file.sync_all()?;
        Ok(())
    })();
    if let Err(error) = write_result {
        let _ = std::fs::remove_file(&temporary);
        return Err(error);
    }
    if let Err(error) = std::fs::hard_link(&temporary, path) {
        let _ = std::fs::remove_file(&temporary);
        return Err(error).context("atomic no-overwrite output publication");
    }
    if let Err(error) = std::fs::remove_file(&temporary) {
        let _ = std::fs::remove_file(path);
        let _ = File::open(parent).and_then(|directory| directory.sync_all());
        return Err(error).context("remove exclusive temporary output link");
    }
    if let Err(error) = File::open(parent).and_then(|directory| directory.sync_all()) {
        let _ = std::fs::remove_file(path);
        let _ = File::open(parent).and_then(|directory| directory.sync_all());
        return Err(error).context("directory fsync after atomic publication");
    }
    Ok(())
}

pub fn canonical_integer(raw: &str) -> bool {
    if raw == "0" {
        return true;
    }
    let digits = raw.strip_prefix('-').unwrap_or(raw);
    !digits.is_empty()
        && !digits.starts_with('0')
        && digits.bytes().all(|byte| byte.is_ascii_digit())
}

pub fn parse_bigint(raw: &str) -> Result<BigInt> {
    ensure!(canonical_integer(raw), "noncanonical integer: {raw}");
    BigInt::parse_bytes(raw.as_bytes(), 10).context("parse integer")
}

fn bigint_abs(value: BigInt) -> BigInt {
    if value < BigInt::from(0) {
        -value
    } else {
        value
    }
}

fn bigint_gcd(mut left: BigInt, mut right: BigInt) -> BigInt {
    left = bigint_abs(left);
    right = bigint_abs(right);
    while right != BigInt::from(0) {
        let remainder = &left % &right;
        left = right;
        right = remainder;
    }
    left
}

pub fn parse_rational(raw: &str) -> Result<(BigInt, BigInt)> {
    let mut pieces = raw.split('/');
    let numerator = parse_bigint(pieces.next().context("missing rational numerator")?)?;
    let denominator = match pieces.next() {
        None => BigInt::from(1),
        Some(raw_denominator) => {
            ensure!(
                canonical_integer(raw_denominator)
                    && raw_denominator != "0"
                    && !raw_denominator.starts_with('-'),
                "invalid rational denominator"
            );
            let value = parse_bigint(raw_denominator)?;
            ensure!(value > BigInt::from(1), "noncanonical denominator /1");
            value
        }
    };
    ensure!(pieces.next().is_none(), "multiple rational separators");
    ensure!(
        bigint_gcd(numerator.clone(), denominator.clone()) == BigInt::from(1),
        "rational is not reduced"
    );
    Ok((numerator, denominator))
}

pub fn normalize_rational_coordinates(values: &[String]) -> Result<(Vec<BigInt>, BigInt)> {
    ensure!(!values.is_empty(), "empty rational coordinate vector");
    let parsed = values
        .iter()
        .map(|value| parse_rational(value))
        .collect::<Result<Vec<_>>>()?;
    let mut scale = BigInt::from(1);
    for (_, denominator) in &parsed {
        let divisor = bigint_gcd(scale.clone(), denominator.clone());
        scale = (scale / divisor) * denominator;
    }
    let mut integers = parsed
        .into_iter()
        .map(|(numerator, denominator)| numerator * (&scale / denominator))
        .collect::<Vec<_>>();
    let divisor = integers.iter().cloned().fold(scale.clone(), bigint_gcd);
    ensure!(divisor > BigInt::from(0), "normalization gcd vanished");
    scale /= &divisor;
    for integer in &mut integers {
        *integer /= &divisor;
    }
    let common = integers.iter().cloned().fold(scale.clone(), bigint_gcd);
    ensure!(
        scale > BigInt::from(0)
            && integers.iter().any(|value| *value != BigInt::from(0))
            && common == BigInt::from(1),
        "rational coordinate vector is not primitive"
    );
    Ok((integers, scale))
}

pub fn u64le_digest(values: impl IntoIterator<Item = usize>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update((value as u64).to_le_bytes());
    }
    format!("{:x}", digest.finalize())
}

pub fn decimal_lf_digest<'a>(values: impl IntoIterator<Item = &'a str>) -> String {
    let mut digest = Sha256::new();
    for value in values {
        digest.update(value.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

pub fn zero_lf_digest(count: usize) -> String {
    let mut digest = Sha256::new();
    for _ in 0..count {
        digest.update(b"0\n");
    }
    format!("{:x}", digest.finalize())
}

pub fn direction_digest(directions: &[[i8; N]]) -> String {
    let mut digest = Sha256::new();
    for direction in directions {
        for coordinate in direction {
            digest.update([*coordinate as u8]);
        }
    }
    format!("{:x}", digest.finalize())
}

pub fn input_snapshot_digest(snapshot: &BTreeMap<String, String>) -> String {
    let mut digest = Sha256::new();
    for (path, value) in snapshot {
        digest.update(path.as_bytes());
        digest.update(b"\t");
        digest.update(value.as_bytes());
        digest.update(b"\n");
    }
    format!("{:x}", digest.finalize())
}

pub fn rehash_snapshot(root: &Path, snapshot: &BTreeMap<String, String>) -> Result<()> {
    for (path, expected) in snapshot {
        ensure!(is_sha256(expected), "malformed snapshot digest: {path}");
        ensure!(
            sha256_path(&checked_repo_path(root, path)?)? == *expected,
            "snapshot input drift: {path}"
        );
    }
    Ok(())
}

const STAGE_A_POOL_KEYS: &[&str] = &[
    "schema",
    "result",
    "claim_boundary",
    "g0140_manifest",
    "g0135_manifest",
    "protocol",
    "producer_source",
    "producer_engine",
    "producer_executable",
    "g0139_result_audit",
    "ancestor_stage_d_result",
    "stage_c_member",
    "source_and_audit_bindings",
    "candidate_schema",
    "candidate_result",
    "rows",
    "records",
    "selected_rank",
    "support_columns",
    "terms",
    "target_scale",
    "target_subtraction_coordinate_10",
    "stage_c_all_412_rational_rows_replayed",
    "stage_c_all_412_integer_rows_replayed",
    "stage_c_primitive_denominator_clearing",
    "stage_c_coefficient_plus_one_mutant_rejected",
    "stage_c_prior_scale_carryover_mutant_rejected",
    "independent_finite_412_row_replay",
    "arithmetic",
    "decision_rule",
    "complete_global_replay",
    "all_hinge_and_linear_residuals_zero",
    "labelled_permutations_expected",
    "labelled_permutations_checked",
    "hinge_entries_processed",
    "aggregate_hinge_support",
    "nonzero_hinge_directions",
    "aggregate_hinge_decimal_lf_sha256",
    "nonzero_hinge_decimal_lf_sha256",
    "complete_residual_decimal_lf_sha256",
    "term_normal_form_transcript_sha256",
    "term_normal_forms",
    "accumulated_direction_checks",
    "all_100_accumulated_directions_exact_zero",
    "linear_residuals_after_target",
    "all_11_linear_residuals_exact_zero",
    "first_nonzero_hinge",
    "first_nonzero_linear",
    "pool_k",
    "pool_count",
    "pool_directions_i8_sha256",
    "pool_exact_residuals_decimal_lf_sha256",
    "pool",
    "coefficient_plus_one",
    "target_scale_plus_one",
    "target_coordinate_plus_one",
    "omitted_final_term",
    "omitted_first_term_direction",
    "census_controls",
    "selection_controls",
    "inputs_rehashed_at_end",
    "manifest_rehashed_at_end",
    "candidate_rehashed_at_end",
    "wall_seconds",
];

const CACHE_MANIFEST_KEYS: &[&str] = &[
    "schema",
    "result",
    "claim_boundary",
    "bindings",
    "records",
    "rows",
    "entry_bytes",
    "payload_bytes",
    "layout",
    "integer_width",
    "endianness",
    "control_vector_sha256",
    "ordered_vector_digests_sha256",
    "data_sha256",
    "value_minimum",
    "value_maximum",
    "wall_seconds",
];

fn validate_exact_object_keys(value: &Value, expected: &[&str], label: &str) -> Result<()> {
    let object = value
        .as_object()
        .with_context(|| format!("{label} must be a JSON object"))?;
    let expected_set = expected.iter().copied().collect::<BTreeSet<_>>();
    let observed = object.keys().map(String::as_str).collect::<BTreeSet<_>>();
    ensure!(
        expected_set.len() == expected.len() && observed == expected_set,
        "{label} key-set drift"
    );
    Ok(())
}

fn snapshot_matches(snapshot: &BTreeMap<String, String>, path: &str, sha256: &str) -> Result<()> {
    ensure!(
        snapshot.get(path).map(String::as_str) == Some(sha256),
        "snapshot binding drift: {path}"
    );
    Ok(())
}

fn validate_commit_binding(
    root: &Path,
    binding: &CommitBinding,
    path: &str,
    sha256: &str,
    commit: &str,
) -> Result<()> {
    ensure!(
        binding.path == path && binding.sha256 == sha256 && binding.git_commit == commit,
        "committed binding drift: {path}"
    );
    ensure!(
        sha256_path(&checked_repo_path(root, path)?)? == sha256,
        "committed binding bytes drift: {path}"
    );
    ensure!(
        git_commit_for_path(root, path)? == commit,
        "committed binding Git identity drift: {path}"
    );
    Ok(())
}

fn validate_strict_axis(
    values: &[usize],
    upper: usize,
    expected: usize,
    label: &str,
) -> Result<()> {
    ensure!(values.len() == expected, "{label} census drift");
    ensure!(
        values.windows(2).all(|pair| pair[0] < pair[1]),
        "{label} is not strictly increasing"
    );
    ensure!(
        values.last().is_some_and(|value| *value < upper),
        "{label} outside range"
    );
    Ok(())
}

fn canonical_positive_integer(raw: &str) -> bool {
    canonical_integer(raw) && raw != "0" && !raw.starts_with('-')
}

fn nonzero_term_projection(sequences: &[usize], coefficients: &[String]) -> Result<Vec<Term>> {
    ensure!(
        sequences.len() == coefficients.len(),
        "basis/coefficient census drift"
    );
    ensure!(
        coefficients.iter().all(|value| canonical_integer(value)),
        "noncanonical integer coefficient"
    );
    Ok(sequences
        .iter()
        .copied()
        .zip(coefficients)
        .filter(|(_, coefficient)| coefficient.as_str() != "0")
        .map(|(sequence, coefficient)| Term {
            sequence,
            coefficient: coefficient.clone(),
        })
        .collect())
}

fn bigints_i128le_digest<'a>(values: impl IntoIterator<Item = &'a BigInt>) -> Result<String> {
    let mut digest = Sha256::new();
    for value in values {
        let encoded = value
            .to_string()
            .parse::<i128>()
            .context("signed i128 digest entry overflow")?;
        digest.update(encoded.to_le_bytes());
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn load_manifest(root: &Path) -> Result<(FiniteManifest, Binding)> {
    let manifest_binding = binding_for_path(root, FINITE_MANIFEST_PATH)?;
    ensure!(
        manifest_binding.sha256 == FINITE_MANIFEST_SHA256,
        "finite manifest digest drift"
    );
    ensure!(
        git_commit_for_path(root, FINITE_MANIFEST_PATH)? == FINITE_MANIFEST_COMMIT,
        "finite manifest commit drift"
    );
    let manifest: FiniteManifest = strict_json(BufReader::new(File::open(checked_repo_path(
        root,
        FINITE_MANIFEST_PATH,
    )?)?))?;
    validate_commit_binding(
        root,
        &manifest.preregistration,
        PREREGISTRATION_PATH,
        PREREGISTRATION_SHA256,
        PREREGISTRATION_COMMIT,
    )?;
    validate_commit_binding(
        root,
        &manifest.solver,
        SOLVER_PATH,
        SOLVER_SHA256,
        SOLVER_COMMIT,
    )?;
    validate_commit_binding(
        root,
        &manifest.source_audit,
        SOURCE_AUDIT_PATH,
        SOURCE_AUDIT_SHA256,
        SOURCE_AUDIT_COMMIT,
    )?;
    binding_matches(
        root,
        &manifest.stage_a_receipt,
        STAGE_A_PATH,
        STAGE_A_SHA256,
    )?;
    binding_matches(
        root,
        &manifest.stage_b_receipt,
        STAGE_B_PATH,
        STAGE_B_SHA256,
    )?;
    binding_matches(
        root,
        &manifest.stage_c_receipt,
        STAGE_C_PATH,
        STAGE_C_SHA256,
    )?;
    ensure!(
        manifest.schema == "max11-g0164-all128-manifest-v1"
            && manifest.result == "FROZEN_BEFORE_G0164_SCIENTIFIC_SOLVE"
            && manifest.claim_boundary == FINITE_CLAIM_BOUNDARY
            && manifest.records == RECORDS
            && manifest.base_rows == BASE_ROWS
            && manifest.appended_rows == POOL_ROWS
            && manifest.rows == ROWS
            && manifest.rank == RANK
            && manifest.basis_sequences_u64le_sha256 == BASIS_SEQUENCES_SHA256
            && manifest.basis_i128le_sha256 == BASIS_MATRIX_SHA256
            && manifest.square_i128le_sha256 == SQUARE_MATRIX_SHA256
            && manifest.target_i128le_sha256 == TARGET_SHA256
            && manifest.planned_output.path == FINITE_MEMBER_PATH
            && manifest.planned_output.schema == "max11-g0164-all128-direct-basis-member-v1"
            && manifest.planned_output.result == "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER"
            && !manifest.scientific_solve_executed
            && !manifest.scientific_output_created,
        "finite manifest contract drift"
    );
    ensure!(
        !manifest.input_snapshot.is_empty()
            && manifest
                .input_snapshot
                .values()
                .all(|value| is_sha256(value))
            && input_snapshot_digest(&manifest.input_snapshot) == manifest.input_snapshot_sha256,
        "finite manifest snapshot digest drift"
    );
    ensure!(
        manifest.input_snapshot_sha256
            == "ca7f3d74fb22f9360dd8de6cf05a255bc0e1e69015abd98011827735507ce235"
            && !manifest.input_snapshot.contains_key(FINITE_MANIFEST_PATH)
            && !manifest.input_snapshot.contains_key(FINITE_MEMBER_PATH),
        "finite manifest snapshot boundary drift"
    );
    for (path, sha256) in [
        (PREREGISTRATION_PATH, PREREGISTRATION_SHA256),
        (SOLVER_PATH, SOLVER_SHA256),
        (SOURCE_AUDIT_PATH, SOURCE_AUDIT_SHA256),
        (STAGE_A_PATH, STAGE_A_SHA256),
        (STAGE_B_PATH, STAGE_B_SHA256),
        (STAGE_C_PATH, STAGE_C_SHA256),
        (G0140_MANIFEST_PATH, G0140_MANIFEST_SHA256),
        (PANEL_INPUT_PATH, PANEL_INPUT_SHA256),
        (PANEL_CACHE_MANIFEST_PATH, PANEL_CACHE_MANIFEST_SHA256),
        (PANEL_CACHE_PATH, PANEL_CACHE_SHA256),
    ] {
        snapshot_matches(&manifest.input_snapshot, path, sha256)?;
    }
    git_is_ancestor(
        root,
        PREREGISTRATION_COMMIT,
        SOLVER_COMMIT,
        "G-0164 preregistration -> finite solver",
    )?;
    git_is_ancestor(
        root,
        SOLVER_COMMIT,
        SOURCE_AUDIT_COMMIT,
        "G-0164 finite solver -> source audit",
    )?;
    git_is_ancestor(
        root,
        SOURCE_AUDIT_COMMIT,
        FINITE_MANIFEST_COMMIT,
        "G-0164 source audit -> finite manifest",
    )?;
    Ok((manifest, manifest_binding))
}

fn load_stage_a_directions(root: &Path, binding: &Binding) -> Result<Vec<[i8; N]>> {
    binding_matches(root, binding, STAGE_A_PATH, STAGE_A_SHA256)?;
    let value = strict_json_value(BufReader::new(File::open(checked_repo_path(
        root,
        STAGE_A_PATH,
    )?)?))?;
    validate_exact_object_keys(&value, STAGE_A_POOL_KEYS, "G-0140 Stage-A receipt")?;
    let receipt: StageAPoolView =
        serde_json::from_value(value).context("typed G-0140 Stage-A receipt")?;
    ensure!(
        receipt.schema == "max11-g0140-pool128-global-replay-v1"
            && receipt.result == "EXACT_RESIDUAL_POOL128"
            && receipt.g0140_manifest.path == G0140_MANIFEST_PATH
            && receipt.g0140_manifest.sha256 == G0140_MANIFEST_SHA256
            && receipt.rows == BASE_ROWS
            && receipt.records == RECORDS
            && receipt.selected_rank == 204
            && receipt.support_columns == 204
            && receipt.terms == 135
            && receipt.complete_global_replay
            && !receipt.all_hinge_and_linear_residuals_zero
            && receipt.all_100_accumulated_directions_exact_zero
            && receipt.all_11_linear_residuals_exact_zero
            && receipt.pool_k == POOL_ROWS
            && receipt.pool_count == POOL_ROWS
            && receipt.pool.len() == POOL_ROWS
            && receipt.accumulated_direction_checks.len() == INHERITED_DIRECTIONS
            && receipt.pool_directions_i8_sha256 == SELECTED_DIRECTIONS_SHA256
            && receipt.pool_exact_residuals_decimal_lf_sha256 == POOL_RESIDUALS_SHA256
            && receipt.inputs_rehashed_at_end
            && receipt.manifest_rehashed_at_end
            && receipt.candidate_rehashed_at_end,
        "G-0140 Stage-A identity/completion drift"
    );
    let mut seen = HashSet::new();
    let mut directions = Vec::with_capacity(TOTAL_DIRECTIONS);
    for (index, check) in receipt.accumulated_direction_checks.iter().enumerate() {
        let (source, source_index) = if index < 68 {
            ("G0128_ACCUMULATED_68", index)
        } else {
            ("G0135_STAGE_A_BATCH32", index - 68)
        };
        validate_direction(&check.direction)?;
        ensure!(
            check.index == index
                && check.source == source
                && check.source_index == source_index
                && check.aggregate_coefficient == "0"
                && check.direct_dp_coefficient == "0"
                && check.routes_agree
                && check.exact_zero
                && seen.insert(check.direction),
            "G-0140 inherited direction drift at {index}"
        );
        directions.push(check.direction);
    }
    ensure!(
        direction_digest(
            &receipt
                .pool
                .iter()
                .map(|item| item.direction)
                .collect::<Vec<_>>()
        ) == receipt.pool_directions_i8_sha256
            && decimal_lf_digest(receipt.pool.iter().map(|item| item.coefficient.as_str()))
                == receipt.pool_exact_residuals_decimal_lf_sha256
            && receipt
                .pool
                .windows(2)
                .all(|pair| pair[0].direction < pair[1].direction),
        "G-0140 pool digest/order drift"
    );
    for item in &receipt.pool {
        validate_direction(&item.direction)?;
        ensure!(
            canonical_integer(&item.coefficient)
                && item.coefficient != "0"
                && seen.insert(item.direction),
            "G-0140 pool item drift"
        );
        directions.push(item.direction);
    }
    ensure!(
        directions.len() == TOTAL_DIRECTIONS,
        "direction census drift"
    );
    Ok(directions)
}

fn load_panel(root: &Path) -> Result<PanelInput> {
    let panel: PanelInput = strict_json(BufReader::new(File::open(checked_repo_path(
        root,
        PANEL_INPUT_PATH,
    )?)?))?;
    ensure!(
        panel.schema == "max11-g0113-panel-solver-input-v1"
            && panel.control_sequences == [0, 1, 284, 5_341, 30_223, 133_449, 134_301]
            && panel.primes == [2_000_081, 3_000_017]
            && panel.rows_path == "artifacts/math/G-0111/dual_rows_v1.json"
            && panel.target.len() == PANEL_ROWS
            && panel.records.len() == RECORDS,
        "panel input metadata drift"
    );
    ensure!(
        panel
            .records
            .iter()
            .enumerate()
            .all(|(sequence, record)| record.sequence == sequence),
        "panel record order drift"
    );
    Ok(panel)
}

fn validate_panel_cache(root: &Path, snapshot: &BTreeMap<String, String>) -> Result<()> {
    let value = strict_json_value(BufReader::new(File::open(checked_repo_path(
        root,
        PANEL_CACHE_MANIFEST_PATH,
    )?)?))?;
    validate_exact_object_keys(&value, CACHE_MANIFEST_KEYS, "panel-cache manifest")?;
    let receipt: CacheManifest =
        serde_json::from_value(value).context("typed panel-cache manifest")?;
    let expected_bytes = u64::try_from(RECORDS)?
        .checked_mul(u64::try_from(PANEL_COLUMN_BYTES)?)
        .context("panel-cache byte-count overflow")?;
    ensure!(
        receipt.schema == "max11-g0117-full-family-panel-cache-v1"
            && receipt.result == "EXACT_PANEL_CACHE_REPRODUCED"
            && receipt.records == RECORDS
            && receipt.rows == PANEL_ROWS
            && receipt.entry_bytes == PANEL_ENTRY_BYTES
            && receipt.payload_bytes == expected_bytes
            && receipt.layout == "sequence-major: offset=((sequence*301)+row)*16"
            && receipt.integer_width == "signed i128"
            && receipt.endianness == "little"
            && receipt.data_sha256 == PANEL_CACHE_SHA256
            && checked_repo_path(root, PANEL_CACHE_PATH)?.metadata()?.len() == expected_bytes,
        "panel-cache identity/layout drift"
    );
    snapshot_matches(
        snapshot,
        PANEL_CACHE_MANIFEST_PATH,
        PANEL_CACHE_MANIFEST_SHA256,
    )?;
    snapshot_matches(snapshot, PANEL_CACHE_PATH, PANEL_CACHE_SHA256)?;
    Ok(())
}

fn load_member(
    root: &Path,
    manifest: &FiniteManifest,
    manifest_binding: &Binding,
    panel: &PanelInput,
    accumulated_directions: &[[i8; N]],
) -> Result<(DirectBasisMember, Binding, BTreeMap<String, String>)> {
    let candidate_binding = binding_for_path(root, FINITE_MEMBER_PATH)?;
    ensure!(
        candidate_binding.sha256 == FINITE_MEMBER_SHA256,
        "finite member digest drift"
    );
    ensure!(
        git_commit_for_path(root, FINITE_MEMBER_PATH)? == FINITE_MEMBER_COMMIT,
        "finite member commit drift"
    );
    git_is_ancestor(
        root,
        FINITE_MANIFEST_COMMIT,
        FINITE_MEMBER_COMMIT,
        "G-0164 finite manifest -> finite member",
    )?;
    let candidate: DirectBasisMember = strict_json(BufReader::new(File::open(
        checked_repo_path(root, FINITE_MEMBER_PATH)?,
    )?))?;
    let manifest_solver = Binding {
        path: manifest.solver.path.clone(),
        sha256: manifest.solver.sha256.clone(),
    };
    let manifest_audit = Binding {
        path: manifest.source_audit.path.clone(),
        sha256: manifest.source_audit.sha256.clone(),
    };
    ensure!(
        candidate.schema == "max11-g0164-all128-direct-basis-member-v1"
            && candidate.result == "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER"
            && candidate.claim_boundary == FINITE_CLAIM_BOUNDARY
            && candidate.manifest == *manifest_binding
            && candidate.solver == manifest_solver
            && candidate.source_audit == manifest_audit
            && candidate.stage_a_receipt == manifest.stage_a_receipt
            && candidate.stage_b_receipt == manifest.stage_b_receipt
            && candidate.stage_c_receipt == manifest.stage_c_receipt
            && candidate.n == N
            && candidate.records == RECORDS
            && candidate.base_rows == BASE_ROWS
            && candidate.appended_rows == POOL_ROWS
            && candidate.rows == ROWS
            && candidate.rank == RANK
            && candidate.augmented_rank == RANK,
        "finite member identity/dimension drift"
    );
    ensure!(
        candidate.selected_pool_indices == (0..POOL_ROWS).collect::<Vec<_>>()
            && candidate.selected_directions.len() == POOL_ROWS
            && accumulated_directions.len() == TOTAL_DIRECTIONS
            && candidate.selected_directions.as_slice()
                == &accumulated_directions[INHERITED_DIRECTIONS..]
            && direction_digest(&candidate.selected_directions) == SELECTED_DIRECTIONS_SHA256
            && candidate.selected_directions_i8_sha256 == SELECTED_DIRECTIONS_SHA256,
        "finite member all-128 direction selection drift"
    );
    let target = candidate
        .target
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    ensure!(
        target.len() == ROWS
            && bigints_i128le_digest(target.iter())? == TARGET_SHA256
            && candidate.target_i128le_sha256 == TARGET_SHA256
            && candidate.target_construction
                == "immutable_G0135_412_entry_unscaled_target_followed_by_all_128_exact_zeros",
        "finite target identity drift"
    );
    ensure!(
        target[..PANEL_ROWS]
            .iter()
            .zip(&panel.target)
            .all(|(observed, expected)| *observed == BigInt::from(*expected))
            && target[PANEL_ROWS..PANEL_ROWS + N - 1]
                .iter()
                .all(|value| *value == BigInt::from(0))
            && target[PANEL_ROWS + N - 1] == BigInt::from(factorial(N))
            && target[PANEL_ROWS + N..]
                .iter()
                .all(|value| *value == BigInt::from(0)),
        "finite target construction replay drift"
    );
    validate_strict_axis(&candidate.basis_sequences, RECORDS, RANK, "basis sequences")?;
    validate_strict_axis(&candidate.coordinate_rows, ROWS, RANK, "coordinate rows")?;
    ensure!(
        u64le_digest(candidate.basis_sequences.iter().copied()) == BASIS_SEQUENCES_SHA256
            && candidate.basis_sequences_u64le_sha256 == BASIS_SEQUENCES_SHA256
            && candidate.basis_i128le_sha256 == BASIS_MATRIX_SHA256
            && candidate.square_i128le_sha256 == SQUARE_MATRIX_SHA256
            && candidate.coordinate_rows[..RANK - POOL_ROWS]
                .iter()
                .all(|row| *row < BASE_ROWS)
            && candidate.coordinate_rows[RANK - POOL_ROWS..]
                == (BASE_ROWS..ROWS).collect::<Vec<_>>(),
        "finite basis/coordinate identity drift"
    );
    ensure!(
        candidate.rational_coefficients.len() == RANK
            && candidate.integer_coefficients.len() == RANK
            && decimal_lf_digest(candidate.rational_coefficients.iter().map(String::as_str))
                == RATIONAL_COEFFICIENTS_SHA256
            && candidate.rational_coefficients_decimal_lf_sha256 == RATIONAL_COEFFICIENTS_SHA256
            && decimal_lf_digest(candidate.integer_coefficients.iter().map(String::as_str))
                == INTEGER_COEFFICIENTS_SHA256
            && candidate.integer_coefficients_decimal_lf_sha256 == INTEGER_COEFFICIENTS_SHA256,
        "finite coefficient census/digest drift"
    );
    let (independent_integers, independent_scale) =
        normalize_rational_coordinates(&candidate.rational_coefficients)?;
    let reported_integers = candidate
        .integer_coefficients
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    let reported_scale = parse_bigint(&candidate.target_scale)?;
    ensure!(
        canonical_positive_integer(&candidate.target_scale)
            && independent_integers == reported_integers
            && independent_scale == reported_scale,
        "independent primitive denominator normalization drift"
    );
    let expected_terms =
        nonzero_term_projection(&candidate.basis_sequences, &candidate.integer_coefficients)?;
    ensure!(
        candidate.support_columns == expected_terms.len()
            && candidate.terms == expected_terms
            && candidate
                .terms
                .windows(2)
                .all(|pair| pair[0].sequence < pair[1].sequence),
        "dynamic nonzero term projection drift"
    );
    ensure!(
        candidate.all_540_rational_rows_replayed
            && candidate.rational_residuals_decimal_lf_sha256 == ZERO_540_SHA256
            && candidate.all_540_primitive_integer_rows_replayed
            && candidate.integer_residuals_decimal_lf_sha256 == ZERO_540_SHA256
            && candidate.primitive_denominator_clearing
            && canonical_positive_integer(&candidate.prior_target_scale)
            && candidate.prior_target_scale_not_used_as_input
            && candidate.complete_basis_reused
            && !candidate.pricing_recomputed
            && !candidate.rank_discovery_recomputed
            && !candidate.complete_family_scan_recomputed
            && !candidate.column_generation_executed
            && !candidate.alternative_basis_or_nullspace_search_executed
            && candidate.inputs_rehashed_at_end
            && candidate.wall_seconds.is_finite()
            && candidate.wall_seconds > 0.0
            && candidate.maximum_rss_kib > 0,
        "finite member replay/search/resource flags drift"
    );
    let mutant = &candidate.coefficient_plus_one_mutant;
    ensure!(
        mutant.basis_index < RANK
            && reported_integers[mutant.basis_index] != BigInt::from(0)
            && mutant.sequence == candidate.basis_sequences[mutant.basis_index]
            && mutant.first_nonzero_row < ROWS
            && canonical_integer(&mutant.first_nonzero_residual)
            && mutant.first_nonzero_residual != "0"
            && mutant.nonzero_rows > 0
            && mutant.nonzero_rows <= ROWS
            && mutant.residuals_decimal_lf_sha256 == MUTANT_RESIDUALS_SHA256
            && mutant.rejected,
        "finite member coefficient-plus-one control drift"
    );
    let mut candidate_snapshot = manifest.input_snapshot.clone();
    ensure!(
        candidate_snapshot
            .insert(
                FINITE_MANIFEST_PATH.to_string(),
                manifest_binding.sha256.clone()
            )
            .is_none()
            && input_snapshot_digest(&candidate_snapshot) == CANDIDATE_INPUT_SNAPSHOT_SHA256
            && candidate.input_snapshot_sha256 == CANDIDATE_INPUT_SNAPSHOT_SHA256,
        "finite member input snapshot drift"
    );
    Ok((candidate, candidate_binding, candidate_snapshot))
}

fn read_panel_column(cache: &mut File, sequence: usize) -> Result<Vec<BigInt>> {
    ensure!(sequence < RECORDS, "panel-cache sequence outside family");
    let offset = sequence
        .checked_mul(PANEL_COLUMN_BYTES)
        .and_then(|value| u64::try_from(value).ok())
        .context("panel-cache offset overflow")?;
    cache.seek(SeekFrom::Start(offset))?;
    let mut encoded = vec![0u8; PANEL_COLUMN_BYTES];
    cache.read_exact(&mut encoded)?;
    let values = encoded
        .chunks_exact(PANEL_ENTRY_BYTES)
        .map(|chunk| {
            let bytes: [u8; PANEL_ENTRY_BYTES] = chunk
                .try_into()
                .expect("chunks_exact preserves the frozen i128 width");
            BigInt::from(i128::from_le_bytes(bytes))
        })
        .collect::<Vec<_>>();
    ensure!(values.len() == PANEL_ROWS, "panel-cache column width drift");
    Ok(values)
}

fn assemble_finite_column(
    mut panel: Vec<BigInt>,
    linear: Vec<BigInt>,
    hinges: Vec<BigInt>,
) -> Result<Vec<BigInt>> {
    ensure!(
        panel.len() == PANEL_ROWS
            && linear.len() == LINEAR_ROWS
            && hinges.len() == TOTAL_DIRECTIONS,
        "finite column component width drift"
    );
    panel.extend(linear);
    panel.extend(hinges);
    ensure!(panel.len() == ROWS, "finite column width drift");
    Ok(panel)
}

fn matrix_i128le_digest(columns: &[Vec<BigInt>], rows: &[usize]) -> Result<String> {
    ensure!(
        columns.len() == RANK
            && columns.iter().all(|column| column.len() == ROWS)
            && rows.iter().all(|row| *row < ROWS),
        "matrix digest dimensions drift"
    );
    let mut digest = Sha256::new();
    for row in rows {
        for column in columns {
            let value = column[*row]
                .to_string()
                .parse::<i128>()
                .context("basis entry exceeds signed i128")?;
            digest.update(value.to_le_bytes());
        }
    }
    Ok(format!("{:x}", digest.finalize()))
}

pub fn exact_matrix_residuals(
    columns: &[Vec<BigInt>],
    coefficients: &[BigInt],
    target: &[BigInt],
    scale: &BigInt,
) -> Result<Vec<BigInt>> {
    ensure!(
        !columns.is_empty()
            && columns.len() == coefficients.len()
            && !target.is_empty()
            && scale > &BigInt::from(0)
            && columns.iter().all(|column| column.len() == target.len()),
        "ragged or empty exact replay"
    );
    let mut residuals = target
        .iter()
        .map(|value| -(scale * value))
        .collect::<Vec<_>>();
    for (column, coefficient) in columns.iter().zip(coefficients) {
        for (residual, value) in residuals.iter_mut().zip(column) {
            *residual += coefficient * value;
        }
    }
    Ok(residuals)
}

fn independent_finite_replay(
    root: &Path,
    panel: &PanelInput,
    candidate: &DirectBasisMember,
    accumulated_directions: &[[i8; N]],
) -> Result<FiniteReplayReceipt> {
    ensure!(
        accumulated_directions.len() == TOTAL_DIRECTIONS
            && candidate.basis_sequences.len() == RANK
            && candidate.coordinate_rows.len() == RANK,
        "finite replay dimensions drift"
    );
    let mut cache = File::open(checked_repo_path(root, PANEL_CACHE_PATH)?)?;
    let mut columns = Vec::with_capacity(RANK);
    for sequence in &candidate.basis_sequences {
        let record = &panel.records[*sequence];
        columns.push(assemble_finite_column(
            read_panel_column(&mut cache, *sequence)?,
            exact_linear_vector(record)?.to_vec(),
            exact_hinge_coefficients(record, accumulated_directions)?,
        )?);
    }
    let selected_basis_digest = matrix_i128le_digest(&columns, &(0..ROWS).collect::<Vec<_>>())?;
    let square_digest = matrix_i128le_digest(&columns, &candidate.coordinate_rows)?;
    ensure!(
        selected_basis_digest == BASIS_MATRIX_SHA256
            && selected_basis_digest == candidate.basis_i128le_sha256
            && square_digest == SQUARE_MATRIX_SHA256
            && square_digest == candidate.square_i128le_sha256,
        "independent finite basis/square digest replay drift"
    );
    let coefficients = candidate
        .integer_coefficients
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    let target = candidate
        .target
        .iter()
        .map(|value| parse_bigint(value))
        .collect::<Result<Vec<_>>>()?;
    let scale = parse_bigint(&candidate.target_scale)?;
    let residuals = exact_matrix_residuals(&columns, &coefficients, &target, &scale)?;
    ensure!(
        residuals.iter().all(|value| *value == BigInt::from(0)),
        "independent finite 540-row BigInt replay failed"
    );
    let residual_strings = residuals
        .iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    ensure!(
        decimal_lf_digest(residual_strings.iter().map(String::as_str)) == ZERO_540_SHA256,
        "independent finite residual digest drift"
    );
    let basis_index = candidate.coefficient_plus_one_mutant.basis_index;
    ensure!(
        basis_index < columns.len() && coefficients[basis_index] != BigInt::from(0),
        "finite mutant basis index drift"
    );
    let mutated = residuals
        .iter()
        .zip(&columns[basis_index])
        .map(|(residual, value)| residual + value)
        .collect::<Vec<_>>();
    let first_nonzero_row = mutated
        .iter()
        .position(|value| *value != BigInt::from(0))
        .context("coefficient-plus-one mutant escaped")?;
    let mutant_strings = mutated.iter().map(ToString::to_string).collect::<Vec<_>>();
    let recomputed_mutant = DirectBasisMutantReceipt {
        basis_index,
        sequence: candidate.basis_sequences[basis_index],
        first_nonzero_row,
        first_nonzero_residual: mutated[first_nonzero_row].to_string(),
        nonzero_rows: mutated
            .iter()
            .filter(|value| **value != BigInt::from(0))
            .count(),
        residuals_decimal_lf_sha256: decimal_lf_digest(mutant_strings.iter().map(String::as_str)),
        rejected: true,
    };
    ensure!(
        recomputed_mutant == candidate.coefficient_plus_one_mutant,
        "independent coefficient-plus-one mutant replay drift"
    );
    Ok(FiniteReplayReceipt {
        rows: ROWS,
        panel_rows: PANEL_ROWS,
        linear_rows: LINEAR_ROWS,
        accumulated_hinge_rows: TOTAL_DIRECTIONS,
        selected_basis_columns: RANK,
        selected_basis_i128le_sha256: selected_basis_digest,
        square_i128le_sha256: square_digest,
        selected_basis_digest_replayed: true,
        square_digest_replayed: true,
        cache_layout: "sequence-major: offset=((sequence*301)+row)*16; signed little-endian i128",
        arithmetic: "signed_num_bigint_BigInt",
        all_rows_exactly_replayed: true,
        residuals_decimal_lf_sha256: ZERO_540_SHA256.to_string(),
        coefficient_plus_one_mutant: recomputed_mutant,
    })
}

pub fn load_and_validate(root: &Path) -> Result<ValidatedCandidate> {
    let root = root
        .canonicalize()
        .context("canonicalize repository root")?;
    let (manifest, manifest_binding) = load_manifest(&root)?;
    let accumulated_directions = load_stage_a_directions(&root, &manifest.stage_a_receipt)?;
    let panel = load_panel(&root)?;
    validate_panel_cache(&root, &manifest.input_snapshot)?;
    let (candidate, candidate_binding, mut input_snapshot) = load_member(
        &root,
        &manifest,
        &manifest_binding,
        &panel,
        &accumulated_directions,
    )?;
    let finite_replay =
        independent_finite_replay(&root, &panel, &candidate, &accumulated_directions)?;
    ensure!(
        input_snapshot
            .insert(
                FINITE_MEMBER_PATH.to_string(),
                candidate_binding.sha256.clone()
            )
            .is_none(),
        "finite member snapshot collision"
    );
    rehash_snapshot(&root, &input_snapshot)?;
    Ok(ValidatedCandidate {
        manifest,
        finite_manifest_binding: manifest_binding.clone(),
        manifest_binding,
        candidate,
        candidate_binding,
        records: panel.records,
        accumulated_directions,
        finite_replay,
        input_snapshot,
    })
}

pub fn self_test() -> Result<()> {
    ensure!(
        strict_json_value(std::io::Cursor::new(br#"{"ok":[1,true,null]}"#)).is_ok()
            && strict_json_value(std::io::Cursor::new(br#"{"x":1,"x":2}"#)).is_err()
            && strict_json_value(std::io::Cursor::new(br#"{"x":1} trailing"#)).is_err()
            && strict_json::<Binding>(std::io::Cursor::new(
                br#"{"path":"x","sha256":"0000000000000000000000000000000000000000000000000000000000000000","extra":true}"#,
            ))
            .is_err(),
        "strict JSON fixture drift"
    );
    let finite_style_binding: CommitBinding = strict_json(std::io::Cursor::new(
        br#"{"path":"x","sha256":"0000000000000000000000000000000000000000000000000000000000000000","commit":"1111111111111111111111111111111111111111"}"#,
    ))?;
    let serialized_binding = serde_json::to_value(&finite_style_binding)?;
    ensure!(
        finite_style_binding.git_commit == "1111111111111111111111111111111111111111"
            && serialized_binding.get("commit").is_none()
            && serialized_binding.get("git_commit").and_then(Value::as_str)
                == Some("1111111111111111111111111111111111111111"),
        "commit-binding alias/serialization fixture drift"
    );
    let rationals = vec!["1/2".to_string(), "-3/4".to_string(), "0".to_string()];
    let (integers, scale) = normalize_rational_coordinates(&rationals)?;
    ensure!(
        integers == [BigInt::from(2), BigInt::from(-3), BigInt::from(0)]
            && scale == BigInt::from(4)
            && parse_rational("2/4").is_err()
            && parse_rational("1/1").is_err()
            && parse_rational("01").is_err(),
        "rational normalization fixture drift"
    );
    let projection = nonzero_term_projection(
        &[2, 5, 9, 12],
        &[
            "3".to_string(),
            "0".to_string(),
            "-4".to_string(),
            "0".to_string(),
        ],
    )?;
    ensure!(
        projection
            == [
                Term {
                    sequence: 2,
                    coefficient: "3".to_string(),
                },
                Term {
                    sequence: 9,
                    coefficient: "-4".to_string(),
                },
            ],
        "dynamic term projection fixture drift"
    );
    let columns = vec![
        vec![BigInt::from(1), BigInt::from(0), BigInt::from(1)],
        vec![BigInt::from(0), BigInt::from(1), BigInt::from(1)],
    ];
    let residuals = exact_matrix_residuals(
        &columns,
        &[BigInt::from(2), BigInt::from(3)],
        &[BigInt::from(2), BigInt::from(3), BigInt::from(5)],
        &BigInt::from(1),
    )?;
    ensure!(
        residuals.iter().all(|value| *value == BigInt::from(0))
            && residuals
                .iter()
                .zip(&columns[0])
                .any(|(residual, value)| residual + value != BigInt::from(0)),
        "exact replay/mutant fixture drift"
    );
    let inconsistent = exact_matrix_residuals(
        &columns,
        &[BigInt::from(2), BigInt::from(3)],
        &[BigInt::from(2), BigInt::from(3), BigInt::from(6)],
        &BigInt::from(1),
    )?;
    ensure!(
        inconsistent.iter().any(|value| *value != BigInt::from(0)),
        "inconsistent-row fixture escaped"
    );
    Ok(())
}

#[cfg(test)]
mod tests {
    #[test]
    fn candidate_self_test() {
        super::self_test().expect("candidate synthetic self-test");
    }
}
