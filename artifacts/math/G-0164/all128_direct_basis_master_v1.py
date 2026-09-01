#!/usr/bin/env python3
"""G-0164 deterministic exact-Q solve on the certified all-128 basis.

This producer does not scan or rank the 163,740-column family.  It reconstructs
the exact 349 columns and 349 coordinate rows frozen by G-0140 Stage C, solves
that square system once over Q, and replays the result on all 540 finite rows.
The resulting receipt is only a finite-row member; global MAX11 replay is a
separate stage.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import mmap
import os
import resource
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from flint import fmpq_mat, fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()

PREREGISTRATION_PATH = HERE / "PREREGISTRATION.md"
MANIFEST_PATH = HERE / "all128_manifest_v1.json"
OUTPUT_PATH = HERE / "all128_direct_basis_member_v1.json"

STAGE_A_PATH = ROOT / "artifacts/math/G-0140/pool128_global_replay_v1.json"
STAGE_B_PATH = ROOT / "artifacts/math/G-0140/pool128_coordinate_prices_v1.json"
STAGE_C_PATH = ROOT / "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json"
G0140_MANIFEST_PATH = ROOT / "artifacts/math/G-0140/pool128_manifest_v1.json"
SELECTOR_PATH = (
    ROOT
    / "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)

SOURCE_AUDIT_PREREGISTRATION_PATH = (
    ROOT / "artifacts/reviews/G-0165-g0164-all128-master-source/PREREGISTRATION.md"
)
SOURCE_AUDIT_PATH = (
    ROOT
    / "artifacts/reviews/G-0165-g0164-all128-master-source/SOURCE_AUDIT_RECEIPT.json"
)

N = 11
RECORDS = 163_740
BASE_ROWS = 412
POOL_ROWS = 128
ROWS = BASE_ROWS + POOL_ROWS
RANK = 349

PREREGISTRATION_COMMIT = "dbd488609efda9d6a4eba33fb2c82d67d49b9288"
PREREGISTRATION_SHA256 = (
    "f28813a182327e38e713c8a20e9039f12d9722861455dcb1a5fb0bb332b00c10"
)
SELECTOR_SHA256 = "f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3"
STAGE_A_SHA256 = "13735a5c6fc987864c97d8c466863f0de376e5dc8fe446381fdc2d1ebd302e4c"
STAGE_B_SHA256 = "7a923266e812bdd29fad2ecdf2d6b5cf2be85e4aacab3f92fe82bfd3b89f5c81"
STAGE_C_SHA256 = "d2a847b2d39b9111804cac1c3e4f9cc9f1fa152598c5a98610b7c5cc68cb9ba6"
G0140_MANIFEST_SHA256 = (
    "79ea5f98ab4594aef377e6512473193b76d25470e71fdf0a823f0ee400aa3e6f"
)
BASIS_SEQUENCES_SHA256 = (
    "c9ec5dbb017e2f735a115ca2eb757adf4d93f072a287f08286c2776b29ec08b3"
)
BASIS_MATRIX_SHA256 = (
    "7451a36e42c479819b6f9ae28ec8c2f7b23360ddc5203b17cf9e3417d1ac9d10"
)
SQUARE_MATRIX_SHA256 = (
    "f06bf820562a96575274bd8358b7ca0eef695e3e991034072deecf97823d3606"
)
TARGET_SHA256 = "a30ec0a4ff135350f217363831c6ffd2ee0a44f74b4d14549aa3b88da3967874"

MANIFEST_SCHEMA = "max11-g0164-all128-manifest-v1"
OUTPUT_SCHEMA = "max11-g0164-all128-direct-basis-member-v1"
OUTPUT_RESULT = "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER"
SOURCE_AUDIT_SCHEMA = "max11-g0165-g0164-all128-master-source-audit-v1"
SOURCE_AUDIT_STATUS = "PASS"
SOURCE_AUDIT_EVIDENCE = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
SOURCE_AUDIT_CLAIM = (
    "Source/custody clearance for the exact frozen G-0164 direct-basis producer "
    "bytes only; no G-0164 finite member or global replay output was inspected "
    "or created and no scientific solve was run."
)
SOURCE_AUDIT_NO_CLAIM = (
    "This audit does not establish finite membership, a global MAX11 identity, "
    "frozen-family membership or nonmembership, a lower bound, unrestricted "
    "representability, minimality, an all-n theorem, or a Lean theorem."
)
SOURCE_AUDIT_REQUIRED_CHECKS = {
    "coefficient_mutation_control_verified": True,
    "exact_349_square_solve_protocol_verified": True,
    "exact_source_and_preregistration_identity_verified": True,
    "exclusive_output_publication_verified": True,
    "input_snapshot_end_rehash_verified": True,
    "no_pricing_rank_scan_or_retry_verified": True,
    "no_scientific_output_inspected_or_created": True,
    "primitive_integer_replay_verified": True,
    "stored_basis_digest_gates_verified": True,
    "strict_contract_validation_verified": True,
    "synthetic_full_row_member_fixture_passed": True,
    "synthetic_inconsistent_extra_row_rejected": True,
}

FINITE_CLAIM_BOUNDARY = (
    "Exact membership only for the frozen G-0140 540-row target in the frozen "
    "163,740-column family, using one preregistered 349-column basis member. "
    "Complete global replay has not yet been run, so this is not a MAX11 "
    "identity, lower bound, minimality result, unrestricted statement, all-n "
    "theorem, or Lean theorem."
)


class DirectBasisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DirectBasisError(message)


def contained(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise DirectBasisError(f"path escapes project: {path}") from error
    return resolved


def relative(path: Path) -> str:
    return contained(path).relative_to(ROOT).as_posix()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with contained(path).open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> None:
    require(path.is_file(), f"missing {label}: {relative(path)}")
    require(sha256_path(path) == expected, f"{label} SHA-256 drift")


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    raw = contained(path).read_text(encoding="utf-8")
    value = json.loads(raw, object_pairs_hook=no_duplicate_object)
    require(isinstance(value, dict), f"non-object JSON: {relative(path)}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, contained(path))
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_exclusive(path: Path, value: object) -> None:
    path = contained(path)
    require(path.parent.is_dir(), "output parent missing")
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    temporary: Path | None = None
    try:
        descriptor, raw = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(raw)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(encoded)
            destination.flush()
            os.fsync(destination.fileno())
        os.link(temporary, path)
        temporary.unlink()
        temporary = None
    except FileExistsError as error:
        raise DirectBasisError(f"refusing to overwrite {relative(path)}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def digest_signed(values: Iterable[int], width: int) -> str:
    digest = hashlib.sha256()
    for value in values:
        try:
            digest.update(int(value).to_bytes(width, "little", signed=True))
        except OverflowError as error:
            raise DirectBasisError(f"signed-{8 * width} value overflow") from error
    return digest.hexdigest()


def digest_i64(values: Iterable[int]) -> str:
    return digest_signed(values, 8)


def digest_i128(values: Iterable[int]) -> str:
    return digest_signed(values, 16)


def digest_u64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(0 <= int(value) < 1 << 64, "unsigned-64 value overflow")
        digest.update(int(value).to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def digest_decimal_lf(values: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def input_snapshot_digest(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(snapshot.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\t")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def snapshot_add(snapshot: dict[str, str], path: Path, expected: str, label: str) -> None:
    name = relative(path)
    require_sha(path, expected, label)
    if name in snapshot:
        require(snapshot[name] == expected, f"snapshot collision: {name}")
    snapshot[name] = expected


def rehash_snapshot(snapshot: dict[str, str]) -> None:
    for name, expected in sorted(snapshot.items()):
        require_sha(ROOT / name, expected, f"end-bound input {name}")


def git_commit_for_path(path: Path) -> str:
    name = relative(path)
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", name],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    require(
        len(commit) == 40
        and all(character in "0123456789abcdef" for character in commit),
        f"missing Git commit for {name}",
    )
    blob = subprocess.run(
        ["git", "show", f"{commit}:{name}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    require(
        hashlib.sha256(blob.stdout).hexdigest() == sha256_path(path),
        f"working bytes are not the committed Git blob: {name}",
    )
    return commit


def git_is_ancestor(ancestor: str, descendant: str, label: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT
    )
    require(result.returncode == 0, f"Git ancestry failure: {label}")


def canonical_integer(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise DirectBasisError(f"boolean integer at {label}")
    if isinstance(value, int):
        return value
    require(isinstance(value, str), f"non-integer at {label}")
    require(value == "0" or value == "-0" or value.lstrip("-").isdigit(), f"bad integer at {label}")
    require(not (value.startswith("0") and len(value) > 1), f"noncanonical integer at {label}")
    require(not (value.startswith("-0")), f"noncanonical integer at {label}")
    return int(value)


def canonical_fraction(value: Fraction) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def validate_source_audit() -> dict[str, Any]:
    require(SOURCE_AUDIT_PREREGISTRATION_PATH.is_file(), "source-audit preregistration missing")
    require(SOURCE_AUDIT_PATH.is_file(), "source-audit receipt missing")
    audit = load_json(SOURCE_AUDIT_PATH)
    expected_keys = {
        "schema",
        "status",
        "evidence_class",
        "reviewer",
        "preregistration",
        "subject",
        "audit_preregistration",
        "checks",
        "scientific_output_inspected",
        "scientific_output_created",
        "scientific_run_executed",
        "claim_boundary",
        "no_claim",
    }
    require(set(audit) == expected_keys, "source-audit top-level contract drift")
    subject = audit.get("subject")
    prereg = audit.get("preregistration")
    audit_prereg = audit.get("audit_preregistration")
    reviewer = audit.get("reviewer")
    require(isinstance(subject, dict) and set(subject) == {"path", "sha256", "commit"}, "audit subject drift")
    require(isinstance(prereg, dict) and set(prereg) == {"path", "sha256", "commit"}, "audit preregistration drift")
    require(isinstance(audit_prereg, dict) and set(audit_prereg) == {"path", "sha256", "commit"}, "audit-preregistration drift")
    require(isinstance(reviewer, dict) and set(reviewer) == {"agent_name", "model"}, "audit reviewer drift")
    require(
        audit.get("schema") == SOURCE_AUDIT_SCHEMA
        and audit.get("status") == SOURCE_AUDIT_STATUS
        and audit.get("evidence_class") == SOURCE_AUDIT_EVIDENCE
        and audit.get("checks") == SOURCE_AUDIT_REQUIRED_CHECKS
        and audit.get("scientific_output_inspected") is False
        and audit.get("scientific_output_created") is False
        and audit.get("scientific_run_executed") is False
        and audit.get("claim_boundary") == SOURCE_AUDIT_CLAIM
        and audit.get("no_claim") == SOURCE_AUDIT_NO_CLAIM,
        "source-audit typed gate failed",
    )
    require(
        subject == {
            "path": relative(SCRIPT),
            "sha256": sha256_path(SCRIPT),
            "commit": git_commit_for_path(SCRIPT),
        },
        "source-audit subject identity drift",
    )
    require(
        prereg == {
            "path": relative(PREREGISTRATION_PATH),
            "sha256": PREREGISTRATION_SHA256,
            "commit": git_commit_for_path(PREREGISTRATION_PATH),
        },
        "source-audit scientific preregistration drift",
    )
    require(
        audit_prereg["path"] == relative(SOURCE_AUDIT_PREREGISTRATION_PATH)
        and audit_prereg["sha256"] == sha256_path(SOURCE_AUDIT_PREREGISTRATION_PATH)
        and audit_prereg["commit"] == git_commit_for_path(SOURCE_AUDIT_PREREGISTRATION_PATH),
        "source-audit preregistration identity drift",
    )
    audit_commit = git_commit_for_path(SOURCE_AUDIT_PATH)
    git_is_ancestor(subject["commit"], audit_prereg["commit"], "source -> audit preregistration")
    git_is_ancestor(audit_prereg["commit"], audit_commit, "audit preregistration -> receipt")
    return audit


def qmatrix(rows: Sequence[Sequence[int]]) -> fmpq_mat:
    require(bool(rows), "empty exact matrix")
    columns = len(rows[0])
    require(columns > 0 and all(len(row) == columns for row in rows), "ragged exact matrix")
    return fmpq_mat(fmpz_mat([[int(value) for value in row] for row in rows]))


def normalize_member(values: Sequence[Fraction]) -> tuple[list[int], int]:
    require(bool(values), "empty rational member")
    scale = math.lcm(*(Fraction(value).denominator for value in values))
    integers = [int(Fraction(value) * scale) for value in values]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "member normalization gcd vanished")
    scale //= divisor
    integers = [value // divisor for value in integers]
    common = scale
    for value in integers:
        common = math.gcd(common, abs(value))
    require(scale > 0 and any(integers) and common == 1, "member is not primitive")
    return integers, scale


def exact_solve_and_replay(
    matrix_rows: Sequence[Sequence[int]],
    coordinate_rows: Sequence[int],
    target: Sequence[int],
) -> dict[str, Any]:
    row_count = len(matrix_rows)
    rank = len(coordinate_rows)
    require(
        row_count == len(target)
        and rank > 0
        and all(len(row) == rank for row in matrix_rows)
        and len(set(coordinate_rows)) == rank
        and all(0 <= row < row_count for row in coordinate_rows),
        "direct-basis solve shape drift",
    )
    square_rows = [list(matrix_rows[row]) for row in coordinate_rows]
    square = qmatrix(square_rows)
    rhs_minor = qmatrix([[int(target[row])] for row in coordinate_rows])
    rational = square.solve(rhs_minor)
    fractions: list[Fraction] = []
    for index in range(rank):
        entry = rational[index, 0]
        numerator = int(entry.numerator)
        denominator = int(entry.denominator)
        require(
            denominator > 0 and math.gcd(abs(numerator), denominator) == 1,
            f"noncanonical FLINT rational {index}",
        )
        fractions.append(Fraction(numerator, denominator))

    rational_residuals = [
        sum(
            fractions[column] * int(matrix_rows[row][column])
            for column in range(rank)
        )
        - int(target[row])
        for row in range(row_count)
    ]
    require(not any(rational_residuals), "all-row exact-Q replay failed")

    integers, scale = normalize_member(fractions)
    integer_residuals = [
        sum(
            integers[column] * int(matrix_rows[row][column])
            for column in range(rank)
        )
        - scale * int(target[row])
        for row in range(row_count)
    ]
    require(not any(integer_residuals), "all-row primitive-integer replay failed")

    mutant_index = next(index for index, value in enumerate(integers) if value)
    mutant = integers[:]
    mutant[mutant_index] += 1
    mutant_residuals = [
        sum(
            mutant[column] * int(matrix_rows[row][column])
            for column in range(rank)
        )
        - scale * int(target[row])
        for row in range(row_count)
    ]
    require(any(mutant_residuals), "coefficient-plus-one mutant escaped")
    first_mutant_row = next(index for index, value in enumerate(mutant_residuals) if value)
    return {
        "fractions": fractions,
        "integers": integers,
        "scale": scale,
        "rational_residuals": rational_residuals,
        "integer_residuals": integer_residuals,
        "mutant_index": mutant_index,
        "mutant_residuals": mutant_residuals,
        "first_mutant_row": first_mutant_row,
    }


def validate_sealed_inputs() -> dict[str, Any]:
    require_sha(PREREGISTRATION_PATH, PREREGISTRATION_SHA256, "G-0164 preregistration")
    require(
        git_commit_for_path(PREREGISTRATION_PATH) == PREREGISTRATION_COMMIT,
        "G-0164 preregistration commit drift",
    )
    require_sha(SELECTOR_PATH, SELECTOR_SHA256, "G-0140 selector")
    require_sha(STAGE_A_PATH, STAGE_A_SHA256, "G-0140 Stage A")
    require_sha(STAGE_B_PATH, STAGE_B_SHA256, "G-0140 Stage B")
    require_sha(STAGE_C_PATH, STAGE_C_SHA256, "G-0140 Stage C")
    require_sha(G0140_MANIFEST_PATH, G0140_MANIFEST_SHA256, "G-0140 manifest")

    selector = load_module(SELECTOR_PATH, "g0164_g0140_selector")
    base_target, warm_receipt, g0135_producer, g0135_prepared = (
        selector.load_g0135_base_preflight()
    )
    require(len(base_target) == BASE_ROWS, "G-0135 base target width drift")

    stage_a = load_json(STAGE_A_PATH)
    pool = stage_a.get("pool")
    require(
        stage_a.get("schema") == "max11-g0140-pool128-global-replay-v1"
        and stage_a.get("result") == "EXACT_RESIDUAL_POOL128"
        and stage_a.get("records") == RECORDS
        and stage_a.get("pool_count") == POOL_ROWS
        and stage_a.get("pool_k") == POOL_ROWS
        and isinstance(pool, list)
        and len(pool) == POOL_ROWS,
        "G-0140 Stage-A pool contract drift",
    )
    pool_directions = [item.get("direction") for item in pool]
    require(
        all(
            isinstance(direction, list)
            and len(direction) == N
            and all(isinstance(value, int) and not isinstance(value, bool) for value in direction)
            for direction in pool_directions
        ),
        "Stage-A direction shape drift",
    )
    require(
        selector.digest_directions(pool_directions)
        == stage_a.get("pool_directions_i8_sha256"),
        "Stage-A direction digest drift",
    )

    stage_b = load_json(STAGE_B_PATH)
    row_receipts = stage_b.get("rows")
    directions = stage_b.get("directions")
    require(
        stage_b.get("schema") == "max11-g0140-pool128-coordinate-prices-v1"
        and stage_b.get("result") == "EXACT_FULL_FAMILY_POOL128_COORDINATES"
        and stage_b.get("records") == RECORDS
        and stage_b.get("pool_count") == POOL_ROWS
        and stage_b.get("pool_k") == POOL_ROWS
        and stage_b.get("hinge_entries") == POOL_ROWS * RECORDS
        and isinstance(row_receipts, list)
        and len(row_receipts) == POOL_ROWS
        and directions == pool_directions,
        "G-0140 Stage-B contract drift",
    )
    all_pool_rows: list[list[int]] = []
    for index, receipt in enumerate(row_receipts):
        require(isinstance(receipt, dict), f"Stage-B row {index} is not an object")
        coefficients = receipt.get("hinge_coefficients")
        require(
            receipt.get("index") == index
            and receipt.get("direction") == directions[index]
            and receipt.get("records") == RECORDS
            and isinstance(coefficients, list)
            and len(coefficients) == RECORDS
            and all(isinstance(value, int) and not isinstance(value, bool) for value in coefficients),
            f"Stage-B row {index} shape drift",
        )
        require(
            digest_i64(coefficients) == receipt.get("hinge_coefficients_i64_le_sha256"),
            f"Stage-B row {index} digest drift",
        )
        all_pool_rows.append(coefficients)
    require(
        digest_i64(value for row in all_pool_rows for value in row)
        == stage_b.get("direction_major_hinge_i64_le_sha256"),
        "Stage-B complete matrix digest drift",
    )

    stage_c = load_json(STAGE_C_PATH)
    rank_selection = stage_c.get("rank_selection")
    basis = stage_c.get("complete_column_basis")
    require(
        stage_c.get("schema") == "max11-g0140-pool128-exact-rank-selection-v1"
        and stage_c.get("result") == "EXACT_RANK32_SELECTED"
        and stage_c.get("records") == RECORDS
        and stage_c.get("base_rows") == BASE_ROWS
        and stage_c.get("pool_rows") == POOL_ROWS
        and stage_c.get("rows") == ROWS
        and isinstance(rank_selection, dict)
        and isinstance(basis, dict),
        "G-0140 Stage-C envelope drift",
    )
    transcript = rank_selection.get("prefix_rank_transcript")
    require(isinstance(transcript, dict), "Stage-C prefix transcript missing")
    require(
        transcript.get("base_rank") == 221
        and transcript.get("full_pool_rank") == RANK
        and transcript.get("increments") == [1] * POOL_ROWS
        and transcript.get("rank_growing_indices") == list(range(POOL_ROWS))
        and transcript.get("dependent_indices") == []
        and rank_selection.get("all_pool_rows_compatibility_checked") is True
        and rank_selection.get("compatibility_decision_complete") is True,
        "Stage-C all-128 exact-rank transcript drift",
    )
    sequences = basis.get("basis_sequences")
    minor = basis.get("nonzero_minor")
    require(isinstance(minor, dict), "Stage-C basis minor missing")
    coordinate_rows = minor.get("coordinate_rows")
    require(
        basis.get("basis_rank") == RANK
        and basis.get("all_columns_exactly_spanned") is True
        and isinstance(sequences, list)
        and len(sequences) == RANK
        and sequences == sorted(set(sequences))
        and all(isinstance(value, int) and 0 <= value < RECORDS for value in sequences)
        and basis.get("basis_sequences_u64le_sha256") == BASIS_SEQUENCES_SHA256
        and digest_u64(sequences) == BASIS_SEQUENCES_SHA256
        and basis.get("basis_i128le_sha256") == BASIS_MATRIX_SHA256
        and minor.get("rank") == RANK
        and minor.get("column_sequences") == sequences
        and isinstance(coordinate_rows, list)
        and len(coordinate_rows) == RANK
        and coordinate_rows == sorted(set(coordinate_rows))
        and all(isinstance(value, int) and 0 <= value < ROWS for value in coordinate_rows)
        and minor.get("square_i128le_sha256") == SQUARE_MATRIX_SHA256,
        "Stage-C complete-basis contract drift",
    )
    require(
        len([row for row in coordinate_rows if row < BASE_ROWS]) == RANK - POOL_ROWS
        and coordinate_rows[-POOL_ROWS:] == list(range(BASE_ROWS, ROWS)),
        "Stage-C coordinate-row all-128 coverage drift",
    )
    target = base_target + [0] * POOL_ROWS
    receipt_target = [
        canonical_integer(value, f"Stage-C target {index}")
        for index, value in enumerate(stage_c.get("target", []))
    ]
    require(
        len(target) == ROWS
        and receipt_target == target
        and stage_c.get("target_i128le_sha256") == TARGET_SHA256
        and digest_i128(target) == TARGET_SHA256,
        "Stage-C target drift",
    )
    return {
        "selector": selector,
        "base_target": base_target,
        "target": target,
        "warm_receipt": warm_receipt,
        "g0135_producer": g0135_producer,
        "g0135_prepared": g0135_prepared,
        "directions": directions,
        "all_pool_rows": all_pool_rows,
        "stage_c": stage_c,
        "sequences": sequences,
        "coordinate_rows": coordinate_rows,
    }


def reconstruct_basis(state: dict[str, Any]) -> list[list[int]]:
    g0135_prepared = state["g0135_prepared"]
    g0135_producer = state["g0135_producer"]
    ancestor = g0135_prepared["ancestor"]
    columns: list[list[int]] = []
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        warm_receipt, inherited_loader = g0135_producer.validate_warm_start(
            g0135_prepared, cache
        )
        require(warm_receipt == state["warm_receipt"], "G-0135 warm loader drift")
        for sequence in state["sequences"]:
            column = [int(value) for value in inherited_loader(sequence)]
            column.extend(int(row[sequence]) for row in state["all_pool_rows"])
            require(len(column) == ROWS, "all-128 basis column width drift")
            columns.append(column)
    matrix_rows = [
        [columns[column][row] for column in range(RANK)] for row in range(ROWS)
    ]
    require(
        digest_i128(value for row in matrix_rows for value in row)
        == BASIS_MATRIX_SHA256,
        "reconstructed basis digest drift",
    )
    square_rows = [matrix_rows[row] for row in state["coordinate_rows"]]
    require(
        digest_i128(value for row in square_rows for value in row)
        == SQUARE_MATRIX_SHA256,
        "reconstructed square digest drift",
    )
    return matrix_rows


def collect_snapshot(state: dict[str, Any], *, require_audit: bool) -> dict[str, str]:
    snapshot = dict(state["g0135_prepared"]["snapshot"])
    snapshot_add(snapshot, PREREGISTRATION_PATH, PREREGISTRATION_SHA256, "G-0164 preregistration")
    snapshot_add(snapshot, SCRIPT, sha256_path(SCRIPT), "G-0164 solver")
    snapshot_add(snapshot, SELECTOR_PATH, SELECTOR_SHA256, "G-0140 selector")
    snapshot_add(snapshot, G0140_MANIFEST_PATH, G0140_MANIFEST_SHA256, "G-0140 manifest")
    snapshot_add(snapshot, STAGE_A_PATH, STAGE_A_SHA256, "G-0140 Stage A")
    snapshot_add(snapshot, STAGE_B_PATH, STAGE_B_SHA256, "G-0140 Stage B")
    snapshot_add(snapshot, STAGE_C_PATH, STAGE_C_SHA256, "G-0140 Stage C")
    if require_audit:
        validate_source_audit()
        snapshot_add(
            snapshot,
            SOURCE_AUDIT_PREREGISTRATION_PATH,
            sha256_path(SOURCE_AUDIT_PREREGISTRATION_PATH),
            "G-0165 preregistration",
        )
        snapshot_add(
            snapshot,
            SOURCE_AUDIT_PATH,
            sha256_path(SOURCE_AUDIT_PATH),
            "G-0165 receipt",
        )
    return snapshot


def expected_manifest(state: dict[str, Any], snapshot: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "result": "FROZEN_BEFORE_G0164_SCIENTIFIC_SOLVE",
        "claim_boundary": FINITE_CLAIM_BOUNDARY,
        "preregistration": {
            "path": relative(PREREGISTRATION_PATH),
            "sha256": PREREGISTRATION_SHA256,
            "commit": git_commit_for_path(PREREGISTRATION_PATH),
        },
        "solver": {
            "path": relative(SCRIPT),
            "sha256": sha256_path(SCRIPT),
            "commit": git_commit_for_path(SCRIPT),
        },
        "source_audit": {
            "path": relative(SOURCE_AUDIT_PATH),
            "sha256": sha256_path(SOURCE_AUDIT_PATH),
            "commit": git_commit_for_path(SOURCE_AUDIT_PATH),
        },
        "stage_a_receipt": {"path": relative(STAGE_A_PATH), "sha256": STAGE_A_SHA256},
        "stage_b_receipt": {"path": relative(STAGE_B_PATH), "sha256": STAGE_B_SHA256},
        "stage_c_receipt": {"path": relative(STAGE_C_PATH), "sha256": STAGE_C_SHA256},
        "records": RECORDS,
        "base_rows": BASE_ROWS,
        "appended_rows": POOL_ROWS,
        "rows": ROWS,
        "rank": RANK,
        "basis_sequences_u64le_sha256": BASIS_SEQUENCES_SHA256,
        "basis_i128le_sha256": BASIS_MATRIX_SHA256,
        "square_i128le_sha256": SQUARE_MATRIX_SHA256,
        "target_i128le_sha256": TARGET_SHA256,
        "input_snapshot": dict(sorted(snapshot.items())),
        "input_snapshot_sha256": input_snapshot_digest(snapshot),
        "planned_output": {
            "path": relative(OUTPUT_PATH),
            "schema": OUTPUT_SCHEMA,
            "result": OUTPUT_RESULT,
        },
        "scientific_solve_executed": False,
        "scientific_output_created": False,
    }


def freeze_manifest() -> dict[str, Any]:
    require(not MANIFEST_PATH.exists(), "refusing to overwrite G-0164 manifest")
    require(not OUTPUT_PATH.exists(), "G-0164 scientific output already exists")
    state = validate_sealed_inputs()
    snapshot = collect_snapshot(state, require_audit=True)
    manifest = expected_manifest(state, snapshot)
    source_commit = manifest["solver"]["commit"]
    audit_commit = manifest["source_audit"]["commit"]
    git_is_ancestor(git_commit_for_path(PREREGISTRATION_PATH), source_commit, "preregistration -> solver")
    git_is_ancestor(source_commit, audit_commit, "solver -> source audit")
    write_exclusive(MANIFEST_PATH, manifest)
    return manifest


def validate_manifest(state: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    require(MANIFEST_PATH.is_file(), "G-0164 manifest missing")
    require(not OUTPUT_PATH.exists(), "G-0164 scientific output already exists")
    snapshot = collect_snapshot(state, require_audit=True)
    expected = expected_manifest(state, snapshot)
    manifest = load_json(MANIFEST_PATH)
    require(manifest == expected, "G-0164 manifest contract drift")
    manifest_commit = git_commit_for_path(MANIFEST_PATH)
    git_is_ancestor(expected["source_audit"]["commit"], manifest_commit, "source audit -> manifest")
    snapshot[relative(MANIFEST_PATH)] = sha256_path(MANIFEST_PATH)
    return manifest, snapshot


def preflight() -> dict[str, Any]:
    state = validate_sealed_inputs()
    manifest, snapshot = validate_manifest(state)
    matrix_rows = reconstruct_basis(state)
    rehash_snapshot(snapshot)
    return {
        "result": "G0164_ALL128_DIRECT_BASIS_PREFLIGHT_PASS",
        "manifest_sha256": sha256_path(MANIFEST_PATH),
        "records": RECORDS,
        "rows": ROWS,
        "rank": RANK,
        "basis_entries": ROWS * RANK,
        "basis_i128le_sha256": digest_i128(
            value for row in matrix_rows for value in row
        ),
        "target_i128le_sha256": TARGET_SHA256,
        "input_snapshot_sha256": input_snapshot_digest(snapshot),
        "scientific_solve_executed": False,
        "scientific_output_created": False,
        "manifest_result": manifest["result"],
    }


def run() -> dict[str, Any]:
    begun = time.perf_counter()
    state = validate_sealed_inputs()
    manifest, snapshot = validate_manifest(state)
    matrix_rows = reconstruct_basis(state)
    solved = exact_solve_and_replay(
        matrix_rows, state["coordinate_rows"], state["target"]
    )
    fractions: list[Fraction] = solved["fractions"]
    integers: list[int] = solved["integers"]
    scale = int(solved["scale"])
    sequences = state["sequences"]
    terms = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(sequences, integers, strict=True)
        if coefficient
    ]
    require(bool(terms), "normalized support vanished")
    require(
        state["g0135_producer"].normalize_member(fractions) == (integers, scale),
        "independent G-0135 denominator normalization disagreed",
    )
    result = {
        "schema": OUTPUT_SCHEMA,
        "result": OUTPUT_RESULT,
        "claim_boundary": FINITE_CLAIM_BOUNDARY,
        "manifest": {"path": relative(MANIFEST_PATH), "sha256": sha256_path(MANIFEST_PATH)},
        "solver": {"path": relative(SCRIPT), "sha256": sha256_path(SCRIPT)},
        "source_audit": {"path": relative(SOURCE_AUDIT_PATH), "sha256": sha256_path(SOURCE_AUDIT_PATH)},
        "stage_a_receipt": {"path": relative(STAGE_A_PATH), "sha256": STAGE_A_SHA256},
        "stage_b_receipt": {"path": relative(STAGE_B_PATH), "sha256": STAGE_B_SHA256},
        "stage_c_receipt": {"path": relative(STAGE_C_PATH), "sha256": STAGE_C_SHA256},
        "n": N,
        "records": RECORDS,
        "base_rows": BASE_ROWS,
        "appended_rows": POOL_ROWS,
        "rows": ROWS,
        "selected_pool_indices": list(range(POOL_ROWS)),
        "selected_directions": state["directions"],
        "selected_directions_i8_sha256": state["selector"].digest_directions(state["directions"]),
        "target": [str(value) for value in state["target"]],
        "target_i128le_sha256": TARGET_SHA256,
        "target_construction": "immutable_G0135_412_entry_unscaled_target_followed_by_all_128_exact_zeros",
        "rank": RANK,
        "augmented_rank": RANK,
        "basis_sequences": sequences,
        "basis_sequences_u64le_sha256": BASIS_SEQUENCES_SHA256,
        "coordinate_rows": state["coordinate_rows"],
        "basis_i128le_sha256": BASIS_MATRIX_SHA256,
        "square_i128le_sha256": SQUARE_MATRIX_SHA256,
        "rational_coefficients": [canonical_fraction(value) for value in fractions],
        "rational_coefficients_decimal_lf_sha256": digest_decimal_lf(canonical_fraction(value) for value in fractions),
        "integer_coefficients": [str(value) for value in integers],
        "integer_coefficients_decimal_lf_sha256": digest_decimal_lf(integers),
        "target_scale": str(scale),
        "support_columns": len(terms),
        "terms": terms,
        "all_540_rational_rows_replayed": True,
        "rational_residuals_decimal_lf_sha256": digest_decimal_lf(solved["rational_residuals"]),
        "all_540_primitive_integer_rows_replayed": True,
        "integer_residuals_decimal_lf_sha256": digest_decimal_lf(solved["integer_residuals"]),
        "primitive_denominator_clearing": True,
        "coefficient_plus_one_mutant": {
            "basis_index": solved["mutant_index"],
            "sequence": sequences[solved["mutant_index"]],
            "first_nonzero_row": solved["first_mutant_row"],
            "first_nonzero_residual": str(solved["mutant_residuals"][solved["first_mutant_row"]]),
            "nonzero_rows": sum(bool(value) for value in solved["mutant_residuals"]),
            "residuals_decimal_lf_sha256": digest_decimal_lf(solved["mutant_residuals"]),
            "rejected": True,
        },
        "prior_target_scale": str(
            state["g0135_prepared"]["candidate"]["target_scale"]
        ),
        "prior_target_scale_not_used_as_input": True,
        "complete_basis_reused": True,
        "pricing_recomputed": False,
        "rank_discovery_recomputed": False,
        "complete_family_scan_recomputed": False,
        "column_generation_executed": False,
        "alternative_basis_or_nullspace_search_executed": False,
        "input_snapshot_sha256": input_snapshot_digest(snapshot),
        "inputs_rehashed_at_end": False,
        "wall_seconds": 0.0,
        "maximum_rss_kib": 0,
    }
    require(manifest["rank"] == result["rank"], "manifest/result rank drift")
    rehash_snapshot(snapshot)
    result["inputs_rehashed_at_end"] = True
    result["wall_seconds"] = time.perf_counter() - begun
    result["maximum_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_exclusive(OUTPUT_PATH, result)
    return result


def self_test() -> dict[str, Any]:
    rows = [[1, 0], [0, 1], [1, 1]]
    target = [2, 3, 5]
    solved = exact_solve_and_replay(rows, [0, 1], target)
    require(
        solved["fractions"] == [Fraction(2), Fraction(3)]
        and solved["integers"] == [2, 3]
        and solved["scale"] == 1
        and any(solved["mutant_residuals"]),
        "synthetic direct-basis member fixture drift",
    )
    rejected = False
    try:
        exact_solve_and_replay(rows, [0, 1], [2, 3, 6])
    except DirectBasisError:
        rejected = True
    require(rejected, "synthetic inconsistent extra row escaped")
    require(
        input_snapshot_digest({"b": "2", "a": "1"})
        == input_snapshot_digest({"a": "1", "b": "2"}),
        "snapshot ordering drift",
    )
    return {
        "result": "G0164_ALL128_DIRECT_BASIS_SELF_TEST_PASS",
        "checks": {
            "exact_square_solve": True,
            "all_row_rational_replay": True,
            "primitive_integer_replay": True,
            "coefficient_plus_one_rejected": True,
            "inconsistent_extra_row_rejected": True,
            "snapshot_order_canonical": True,
        },
        "scientific_solve_executed": False,
        "scientific_output_created": False,
    }


def static_preflight() -> dict[str, Any]:
    require_sha(PREREGISTRATION_PATH, PREREGISTRATION_SHA256, "G-0164 preregistration")
    require_sha(SELECTOR_PATH, SELECTOR_SHA256, "G-0140 selector")
    require(SCRIPT.is_file(), "solver source missing")
    require(not OUTPUT_PATH.exists(), "scientific output already exists")
    return {
        "result": "G0164_ALL128_STATIC_PREFLIGHT_PASS",
        "preregistration_sha256": PREREGISTRATION_SHA256,
        "solver_sha256": sha256_path(SCRIPT),
        "manifest_schema": MANIFEST_SCHEMA,
        "output_schema": OUTPUT_SCHEMA,
        "source_audit_schema": SOURCE_AUDIT_SCHEMA,
        "required_source_audit_checks": SOURCE_AUDIT_REQUIRED_CHECKS,
        "scientific_inputs_inspected": False,
        "scientific_solve_executed": False,
        "scientific_output_created": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--preflight-static", action="store_true")
    modes.add_argument("--freeze-manifest", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.self_test:
        result = self_test()
    elif arguments.preflight_static:
        result = static_preflight()
    elif arguments.freeze_manifest:
        result = freeze_manifest()
    elif arguments.preflight:
        result = preflight()
    else:
        result = run()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DirectBasisError as error:
        print(f"INVALID_NO_SCIENTIFIC_RESULT: {error}", file=sys.stderr)
        raise SystemExit(2) from error
