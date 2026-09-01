#!/usr/bin/env python3
"""Two-prime exact rank gate for the quotient STAR expansion matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


ROWS = 5_769
COLUMNS = 6_795
BASE_COLUMNS = 5_771
BASE_RANK = 5_291
TARGET_RANK = 5_769
PRIMES = (1_000_003, 1_000_033)
GATES = (("hash_prefix_480", 6_251), ("rank_directed_1024", 6_795))
BASE_RECEIPT_HASHES = {
    1_000_003: "c368c31700b498847256337973d51d9804351704f44cbb74da163aea750bf5d5",
    1_000_033: "1b20292d0e297ed7bdceccd53d637abed5836d07d78b9976c7f5c8d7d64c4e51",
}
REQUIRED_BINDINGS = {
    "assembly_receipt",
    "directions",
    "expansion_receipt",
    "intrinsic_relations",
    "semantic_binding",
    "semantic_controls",
    "structural_receipt",
}
DIRECTIONS_SHA256 = "546f0a248816487f104fe609261667ade9ef7823d3f38a6dadc70a2a5ca8da16"
RELATIONS_SHA256 = "c2fe511b628169929cce87fc116ab7fde09defc5746d1e40663660502d2ad6fa"
SEMANTIC_CONTROLS_SHA256 = "f74d95d3fe443b42cfe28df9617e1435e78062418b718900b7010b7d2bd0209b"
SEMANTIC_BINDING_SHA256 = "4c5b6f131671892660f417359480ae3ce412bfe01a5d1f67e05c1bd1352c0327"
STRUCTURAL_RECEIPT_SHA256 = "720b9c7d52f6f5c6e07f72dd8bebfbe65b4e5d508d10235612a66835c44de072"
RECORDS_SHA256 = "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4"
BASE_MATRIX_SHA256 = "0e7236e06adc906f2859338b12848e6fc04156963d1567de84dd1e83784162ad"
QUOTIENT_SEQUENCE_SHA256 = "2bf3aa764a3311578aea110f29dcca60284d69b4b5f4b3cb71c1fc5bf1a44606"
PREFIX_480_SHA256 = "3d83256a9c755a84a2b8b873f5baecc8e8e991c6007dcf2e108dbb9a07b37e5e"
PREFIX_1024_SHA256 = "197da75ae725a389d57934b2cb7ba81446420420ac7a60f7d0204b2e2c259323"
FULL_DIRECTION_ORDER_SHA256 = "973ed1a113beb8ed79d01cdbb3391e4fcdb9c94749082264acdebfd0f78340f8"
PRICER_SOURCE_HASHES = {
    "cargo_manifest": "6ecbd74cf899a594c8e95aa3144109bcf45ea0c61d1a8fa02593d89a14b85c6a",
    "cargo_lock": "f6374521cecd8cd0d90c787956fa6ec8f7902ae5da65e22879dbdc80011505b0",
    "main_source": "7eb9e6ab9722d5f31e0702033f18c3d553ce51c660fb3f900678fd0a0b86a237",
    "g0179_dependency_lib": "8385a29ecc566cc01fb19a0158797ec7cb898c86ed3a5dbd60d2a78ca3edcb73",
    "executable": "eaaf2d068be7c196ab57a17396fcdb5bb8f8e61443efc25468e2bcaa2330dfd9",
}
ASSEMBLER_SOURCE_SHA256 = "e313cbc10ad30d62797f5657fb347deaf2b40239e85838d2e98fc99146531c01"
RANKER_SOURCE_SHA256 = "5bd74383f47570b2ce80c4dd5599d8f4bd47d04c99b993ade4fe43bea4fe600d"
RANKER_BINARY_SHA256 = "7829a042b22873fb59bfdfa2902317f04af4ac03759e9a4d75eac90876c82728"


class CertificateError(RuntimeError):
    """A rank, receipt, or custody invariant failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def regular(path: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise CertificateError(f"{label} is not a regular file: {resolved}")
    return resolved


def validate_receipted_file(
    raw_path: Any, claimed_hash: Any, expected_hash: str, label: str
) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise CertificateError(f"{label} receipt path missing")
    if claimed_hash != expected_hash:
        raise CertificateError(f"{label} receipt hash drift")
    path = regular(Path(raw_path), label)
    if sha256_file(path) != expected_hash:
        raise CertificateError(f"{label} file hash drift")
    return path


def parse_binding(items: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for item in items:
        if "=" not in item:
            raise CertificateError("binding-file must use NAME=PATH")
        name, raw_path = item.split("=", 1)
        if not name or "/" in name or name in result:
            raise CertificateError(f"invalid or duplicate binding name: {name!r}")
        result[name] = regular(Path(raw_path), f"binding {name}")
    if set(result) != REQUIRED_BINDINGS:
        raise CertificateError(
            f"binding names must be exactly {sorted(REQUIRED_BINDINGS)}, found {sorted(result)}"
        )
    return result


def validate_producer_bindings(
    bindings: dict[str, Path], matrix: Path, matrix_hash: str
) -> None:
    if sha256_file(bindings["directions"]) != DIRECTIONS_SHA256:
        raise CertificateError("frozen direction-document hash drift")
    if sha256_file(bindings["intrinsic_relations"]) != RELATIONS_SHA256:
        raise CertificateError("intrinsic-relation receipt hash drift")
    if sha256_file(bindings["semantic_controls"]) != SEMANTIC_CONTROLS_SHA256:
        raise CertificateError("semantic-control receipt hash drift")
    if sha256_file(bindings["semantic_binding"]) != SEMANTIC_BINDING_SHA256:
        raise CertificateError("semantic-control binding hash drift")
    if sha256_file(bindings["structural_receipt"]) != STRUCTURAL_RECEIPT_SHA256:
        raise CertificateError("structural-premise receipt hash drift")
    directions = json.loads(bindings["directions"].read_bytes())
    if (
        directions.get("schema") != "g0180.star-loop-rank-expansion-directions.v1"
        or directions.get("result")
        != "NESTED_480_AND_1024_EXPANSION_FROZEN_BEFORE_STAR_PRICING"
    ):
        raise CertificateError("direction-document semantic drift")

    semantic_controls = json.loads(bindings["semantic_controls"].read_bytes())
    semantic_binding = json.loads(bindings["semantic_binding"].read_bytes())
    structural = json.loads(bindings["structural_receipt"].read_bytes())
    if (
        semantic_controls.get("schema") != "g0179.exclusive-rank-semantic-controls.v1"
        or semantic_controls.get("result") != "BOTH_KNOWN_OLD_SPAN_UNIT_COLUMNS_CERTIFIED"
        or semantic_binding.get("schema") != "g0179.semantic-old-primary-binding.v1"
        or semantic_binding.get("result") != "OLD_PRIMARY_HARDCODE_BINDINGS_CERTIFIED"
        or structural.get("schema") != "g0179.d0-quarantine-structural-premises.v2"
        or structural.get("result") != "QUARANTINE_STRUCTURAL_PREMISES_CERTIFIED"
        or structural.get("old_primary", {}).get("all_representative_branches_loopless")
        is not True
        or structural.get("star_outside_primary", {}).get(
            "all_full_to_cancelled_decompositions_replayed"
        )
        is not True
        or structural.get("star_outside_primary", {}).get("records") != 5_773
    ):
        raise CertificateError("upstream semantic or structural premise drift")

    expansion = json.loads(bindings["expansion_receipt"].read_bytes())
    expansion_bindings = expansion.get("bindings", {})
    expansion_source = expansion_bindings.get("source", {})
    expansion_matrix = expansion.get("matrix", {})
    quotient_records = expansion.get("quotient_records", {})
    expansion_directions = expansion.get("directions", {})
    if (
        expansion.get("schema") != "g0180.quotient-expansion-price-matrix.v1"
        or expansion.get("result")
        != "EXACT_5769_BY_1024_EXPANSION_PRICED_AWAITING_AUGMENTED_RANK"
        or expansion_matrix.get("shape") != [ROWS, COLUMNS - BASE_COLUMNS]
        or expansion_matrix.get("bytes") != ROWS * (COLUMNS - BASE_COLUMNS) * 8
        or quotient_records.get("excluded_sequences_exactly") != [1548, 3140, 4259, 5656]
        or quotient_records.get("retained") != ROWS
        or quotient_records.get("sequence_u64le_sha256") != QUOTIENT_SEQUENCE_SHA256
        or expansion_bindings.get("records_sha256") != RECORDS_SHA256
        or expansion_bindings.get("directions_sha256") != DIRECTIONS_SHA256
        or expansion_bindings.get("intrinsic_relations_sha256") != RELATIONS_SHA256
        or expansion_directions.get("priced_prefix") != COLUMNS - BASE_COLUMNS
        or expansion_directions.get("prefix_480_i8_sha256") != PREFIX_480_SHA256
        or expansion_directions.get("prefix_1024_i8_sha256") != PREFIX_1024_SHA256
        or expansion_directions.get("full_frozen_order_i8_sha256")
        != FULL_DIRECTION_ORDER_SHA256
        or expansion_directions.get("all_priced_directions_unique_primitive_active_d0_eq_1")
        is not True
        or expansion.get("rank_gate", {}).get("base_matrix_sha256") != BASE_MATRIX_SHA256
    ):
        raise CertificateError("expansion producer receipt drift")
    expansion_records_path = validate_receipted_file(
        expansion_bindings.get("records"),
        expansion_bindings.get("records_sha256"),
        RECORDS_SHA256,
        "expansion records",
    )
    del expansion_records_path
    expansion_directions_path = validate_receipted_file(
        expansion_bindings.get("directions"),
        expansion_bindings.get("directions_sha256"),
        DIRECTIONS_SHA256,
        "expansion directions",
    )
    if expansion_directions_path != bindings["directions"]:
        raise CertificateError("expansion direction path custody drift")
    expansion_relations_path = validate_receipted_file(
        expansion_bindings.get("intrinsic_relations"),
        expansion_bindings.get("intrinsic_relations_sha256"),
        RELATIONS_SHA256,
        "expansion intrinsic relations",
    )
    if expansion_relations_path != bindings["intrinsic_relations"]:
        raise CertificateError("expansion relation path custody drift")
    if not isinstance(expansion_source, dict):
        raise CertificateError("expansion source binding missing")
    for source_name, expected_hash in PRICER_SOURCE_HASHES.items():
        validate_receipted_file(
            expansion_source.get(source_name),
            expansion_source.get(f"{source_name}_sha256"),
            expected_hash,
            f"pricer {source_name}",
        )
    expansion_matrix_path = validate_receipted_file(
        expansion_matrix.get("path"),
        expansion_matrix.get("sha256"),
        expansion_matrix.get("sha256"),
        "expansion matrix",
    )

    assembly = json.loads(bindings["assembly_receipt"].read_bytes())
    assembly_matrix = assembly.get("matrix", {})
    row_custody = assembly.get("row_custody", {})
    assembly_bindings = assembly.get("bindings", {})
    if (
        assembly.get("schema") != "g0180.quotient-augmented-matrix.v1"
        or assembly.get("result")
        != "EXACT_QUOTIENT_BASE_PLUS_1024_EXPANSION_ASSEMBLED_AWAITING_RANK"
        or assembly_matrix.get("shape") != [ROWS, COLUMNS]
        or assembly_matrix.get("base_columns") != BASE_COLUMNS
        or assembly_matrix.get("expansion_columns") != COLUMNS - BASE_COLUMNS
        or assembly_matrix.get("bytes") != ROWS * COLUMNS * 8
        or assembly_matrix.get("sha256") != matrix_hash
        or Path(assembly_matrix.get("path", "")).resolve() != matrix
        or row_custody.get("skipped_base_row_indices_zero_based") != [3139, 5654]
        or row_custody.get("skipped_record_sequences") != [3140, 5656]
        or row_custody.get("output_rows") != ROWS
        or assembly_bindings.get("expansion_receipt", {}).get("sha256")
        != sha256_file(bindings["expansion_receipt"])
        or assembly_bindings.get("relations", {}).get("sha256") != RELATIONS_SHA256
        or assembly_bindings.get("expansion", {}).get("sha256")
        != expansion_matrix.get("sha256")
        or assembly.get("rank_prefixes")
        != [
            {"name": "quotient-base", "column_end_exclusive": BASE_COLUMNS},
            {"name": "hash-prefix-480", "column_end_exclusive": BASE_COLUMNS + 480},
            {"name": "rank-directed-1024", "column_end_exclusive": COLUMNS},
        ]
    ):
        raise CertificateError("augmented assembly receipt or row custody drift")
    assembly_expected = {
        "base": BASE_MATRIX_SHA256,
        "expansion": expansion_matrix.get("sha256"),
        "expansion_receipt": sha256_file(bindings["expansion_receipt"]),
        "records": RECORDS_SHA256,
        "relations": RELATIONS_SHA256,
        "assembler_source": ASSEMBLER_SOURCE_SHA256,
    }
    assembly_paths = {
        name: validate_receipted_file(
            assembly_bindings.get(name, {}).get("path"),
            assembly_bindings.get(name, {}).get("sha256"),
            expected_hash,
            f"assembly {name}",
        )
        for name, expected_hash in assembly_expected.items()
    }
    if (
        assembly_paths["expansion"] != expansion_matrix_path
        or assembly_paths["expansion_receipt"] != bindings["expansion_receipt"]
        or assembly_paths["relations"] != bindings["intrinsic_relations"]
    ):
        raise CertificateError("assembly-to-expansion path custody drift")


def validate_base_receipt(path: Path, prime: int) -> tuple[dict[str, Any], list[int]]:
    if sha256_file(path) != BASE_RECEIPT_HASHES[prime]:
        raise CertificateError(f"base rank receipt hash drift at p={prime}")
    receipt = json.loads(path.read_bytes())
    expected = {
        "schema": "g0181.flint-signed-le-rank-certificate.v2",
        "input_rows": 5_771,
        "input_columns": 5_771,
        "selected_rows": 5_771,
        "selected_columns": 5_771,
        "prime": prime,
        "rank_mod_prime": BASE_RANK,
        "determinant_mod_prime": 0,
        "full_rank_mod_prime": False,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise CertificateError(f"base receipt p={prime} field {key} drift")
    pivots = receipt.get("pivot_columns")
    if not isinstance(pivots, list) or len(pivots) != BASE_RANK:
        raise CertificateError(f"base receipt p={prime} pivot census drift")
    if pivots != sorted(set(pivots)) or not all(0 <= pivot < BASE_COLUMNS for pivot in pivots):
        raise CertificateError(f"base receipt p={prime} pivot structure drift")
    return receipt, pivots


def run_gate(
    ranker: Path,
    matrix: Path,
    output: Path,
    gate_name: str,
    column_end: int,
    prime: int,
    base_pivots: list[int],
) -> dict[str, Any]:
    command = [
        str(ranker),
        str(matrix),
        "i64le",
        str(ROWS),
        str(COLUMNS),
        "0",
        str(column_end),
        "-",
        str(prime),
        str(output),
    ]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        raise CertificateError(
            f"ranker failed for {gate_name}, p={prime}, exit={completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    if completed.stdout or completed.stderr:
        raise CertificateError("ranker emitted output on successful run")
    receipt = json.loads(output.read_bytes())
    expected = {
        "schema": "g0180.flint-signed-le-rectangular-rank-certificate.v1",
        "matrix_path": str(matrix),
        "encoding": "i64le",
        "bytes_per_cell": 8,
        "input_rows": ROWS,
        "input_columns": COLUMNS,
        "input_bytes": ROWS * COLUMNS * 8,
        "coordinate_start_inclusive": 0,
        "coordinate_end_exclusive": column_end,
        "excluded_source_rows": [],
        "selected_rows": ROWS,
        "selected_columns": column_end,
        "selected_cells": ROWS * column_end,
        "reduction_crosscheck_cells": ROWS * column_end,
        "prime": prime,
        "pivot_columns_reduced": True,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise CertificateError(
                f"receipt {gate_name}, p={prime}, field {key}: "
                f"{receipt.get(key)!r} != {value!r}"
            )
    rank = receipt.get("rank_mod_prime")
    full = receipt.get("full_row_rank_mod_prime")
    pivots = receipt.get("pivot_columns")
    if isinstance(rank, bool) or not isinstance(rank, int) or not BASE_RANK <= rank <= TARGET_RANK:
        raise CertificateError("invalid augmented rank")
    if full is not (rank == TARGET_RANK):
        raise CertificateError("augmented full-row-rank flag drift")
    if not isinstance(pivots, list) or len(pivots) != rank or pivots != sorted(set(pivots)):
        raise CertificateError("invalid augmented pivot list")
    if pivots[:BASE_RANK] != base_pivots:
        raise CertificateError("base-prefix pivots changed after appending expansion columns")
    if any(pivot < BASE_COLUMNS for pivot in pivots[BASE_RANK:]):
        raise CertificateError("new pivot appeared inside the exhausted base prefix")
    return {
        "gate": gate_name,
        "column_end_exclusive": column_end,
        "prime": prime,
        "rank_mod_prime": rank,
        "rank_increment_over_base": rank - BASE_RANK,
        "remaining_row_deficiency": TARGET_RANK - rank,
        "full_row_rank_mod_prime": full,
        "receipt_path": str(output),
        "receipt_bytes": output.stat().st_size,
        "receipt_sha256": sha256_file(output),
        "selected_raw_cells_sha256": receipt["selected_raw_cells_sha256"],
        "selected_modp_u64le_sha256": receipt["selected_modp_u64le_sha256"],
        "rref_modp_u64le_sha256": receipt["rref_modp_u64le_sha256"],
        "new_pivot_columns": pivots[BASE_RANK:],
        "command": command,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--expected-matrix-sha256", required=True)
    parser.add_argument("--ranker", required=True, type=Path)
    parser.add_argument("--ranker-source", required=True, type=Path)
    parser.add_argument("--base-rank-1000003", required=True, type=Path)
    parser.add_argument("--base-rank-1000033", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--binding-file", action="append", default=[], metavar="NAME=PATH")
    arguments = parser.parse_args()

    matrix = regular(arguments.matrix, "matrix")
    ranker = regular(arguments.ranker, "ranker")
    ranker_source = regular(arguments.ranker_source, "ranker source")
    wrapper_source = Path(__file__).resolve(strict=True)
    if not os.access(ranker, os.X_OK):
        raise CertificateError("ranker is not executable")
    if sha256_file(ranker) != RANKER_BINARY_SHA256:
        raise CertificateError("ranker binary hash drift")
    if sha256_file(ranker_source) != RANKER_SOURCE_SHA256:
        raise CertificateError("ranker source hash drift")
    if matrix.stat().st_size != ROWS * COLUMNS * 8:
        raise CertificateError("augmented matrix size drift")
    if len(arguments.expected_matrix_sha256) != 64:
        raise CertificateError("malformed expected matrix hash")
    matrix_hash = sha256_file(matrix)
    if matrix_hash != arguments.expected_matrix_sha256.lower():
        raise CertificateError("augmented matrix external hash pin failed")

    base_paths = {
        1_000_003: regular(arguments.base_rank_1000003, "base rank p=1000003"),
        1_000_033: regular(arguments.base_rank_1000033, "base rank p=1000033"),
    }
    base_pivots: dict[int, list[int]] = {}
    for prime, path in base_paths.items():
        _receipt, base_pivots[prime] = validate_base_receipt(path, prime)
    if base_pivots[1_000_003] != base_pivots[1_000_033]:
        raise CertificateError("base pivot lists disagree across primes")

    bindings = parse_binding(arguments.binding_file)
    validate_producer_bindings(bindings, matrix, matrix_hash)
    output = arguments.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    primary_paths = {
        "matrix": matrix,
        "ranker": ranker,
        "ranker_source": ranker_source,
        "wrapper_source": wrapper_source,
        "base_rank_1000003": base_paths[1_000_003],
        "base_rank_1000033": base_paths[1_000_033],
    }
    primary_before = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in primary_paths.items()
    }
    bindings_before = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in sorted(bindings.items())
    }

    results: list[dict[str, Any]] = []
    for gate_index, (gate_name, column_end) in enumerate(GATES):
        gate_results = []
        for prime in PRIMES:
            receipt_path = output / f"{gate_name}_rank_mod_{prime}.json"
            item = run_gate(
                ranker,
                matrix,
                receipt_path,
                gate_name,
                column_end,
                prime,
                base_pivots[prime],
            )
            gate_results.append(item)
            results.append(item)
        if gate_index == 0 and all(item["full_row_rank_mod_prime"] for item in gate_results):
            break

    primary_after = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in primary_paths.items()
    }
    bindings_after = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in sorted(bindings.items())
    }
    if primary_after != primary_before or bindings_after != bindings_before:
        raise CertificateError("an input, source, binary, or binding changed during rank certification")

    gate_summaries = []
    for gate_name, column_end in GATES:
        subset = [item for item in results if item["gate"] == gate_name]
        if not subset:
            gate_summaries.append(
                {"gate": gate_name, "column_end_exclusive": column_end, "status": "NOT_RUN_EARLIER_GATE_PASSED"}
            )
            continue
        all_full = all(item["full_row_rank_mod_prime"] for item in subset)
        any_full = any(item["full_row_rank_mod_prime"] for item in subset)
        gate_summaries.append(
            {
                "gate": gate_name,
                "column_end_exclusive": column_end,
                "status": (
                    "TWO_PRIME_FULL_ROW_RANK"
                    if all_full
                    else "Q_PASS_PRIME_DISCREPANCY"
                    if any_full
                    else "FAIL"
                ),
                "ranks": [item["rank_mod_prime"] for item in subset],
                "rank_increments": [item["rank_increment_over_base"] for item in subset],
                "remaining_deficiencies": [item["remaining_row_deficiency"] for item in subset],
                "any_prime_full_row_rank": any_full,
                "all_two_primes_full_row_rank": all_full,
            }
        )
    q_passes = [item for item in gate_summaries if item.get("any_prime_full_row_rank")]
    two_prime_passes = [
        item for item in gate_summaries if item.get("all_two_primes_full_row_rank")
    ]
    earliest_q_pass = q_passes[0]["gate"] if q_passes else None
    earliest_two_prime_pass = two_prime_passes[0]["gate"] if two_prime_passes else None
    any_modular_full = any(item["full_row_rank_mod_prime"] for item in results)
    bundle = {
        "schema": "g0180.quotient-expansion-two-prime-rank-bundle.v1",
        "result": (
            "QUOTIENT_D0_EQ_1_RESTRICTION_TWO_PRIME_FULL_ROW_RANK_CERTIFIED"
            if two_prime_passes
            else "QUOTIENT_D0_EQ_1_RESTRICTION_Q_FULL_ROW_RANK_CERTIFIED_PRIME_DISCREPANCY_AUDIT_REQUIRED"
            if q_passes
            else "NO_MODULAR_FULL_ROW_RANK_AT_FROZEN_GATES_Q_RANK_UNRESOLVED"
        ),
        "claim_boundary": (
            "Exact modular row rank of the frozen quotient STAR restriction only. Full row "
            "rank modulo either prime proves rational full row rank for this finite restriction. "
            "Promotion of the target-specific quarantine additionally uses the separately "
            "certified intrinsic O-relations and the zero d0=1 restriction of the target and O. "
            "No old-span nonmembership, ansatz completeness, or unrestricted neural-network "
            "lower bound is certified here."
        ),
        "proof_logic": (
            "A full-row-rank integer matrix modulo a prime contains a maximal minor nonzero "
            "modulo that prime; the same integer minor is nonzero over Q."
        ),
        "fixed_primes": list(PRIMES),
        "base_rank_mod_both_primes": BASE_RANK,
        "target_quotient_row_rank": TARGET_RANK,
        "q_full_row_rank_certified_by_any_modular_gate": any_modular_full,
        "earliest_q_full_row_rank_pass_gate": earliest_q_pass,
        "earliest_two_prime_full_row_rank_gate": earliest_two_prime_pass,
        "gate_summaries": gate_summaries,
        "rank_receipts": results,
        "inputs_and_sources": primary_before,
        "producer_bindings": bindings_before,
        "matrix_external_hash_pin": {
            "expected_sha256": arguments.expected_matrix_sha256.lower(),
            "actual_sha256": matrix_hash,
            "passed": True,
        },
        "base_pivot_lists_identical_across_primes": True,
        "all_inputs_rehashed_unchanged_after_runs": True,
    }
    bundle_path = output / "certificate_bundle.json"
    write_new(bundle_path, canonical_json(bundle))
    bundle_hash = sha256_file(bundle_path)
    write_new(
        output / "certificate_bundle.json.sha256",
        f"{bundle_hash}  {bundle_path.name}\n".encode(),
    )
    print(
        json.dumps(
            {
                "bundle": str(bundle_path),
                "bundle_sha256": bundle_hash,
                "result": bundle["result"],
                "earliest_q_full_row_rank_pass_gate": earliest_q_pass,
                "earliest_two_prime_full_row_rank_gate": earliest_two_prime_pass,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"certify_augmented: {error}", file=sys.stderr)
        raise SystemExit(1)
