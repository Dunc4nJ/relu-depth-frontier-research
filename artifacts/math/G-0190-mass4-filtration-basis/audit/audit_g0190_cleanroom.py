#!/usr/bin/env python3
"""Independent, repo-source-only audit of the frozen G-0190 candidate.

This implementation deliberately does not import or execute any G-0190 discovery
verifier/finalizer.  It reconstructs the retained mass-<=4 block from the frozen
STAR census and the frozen 5769x6795 matrix, then composes an exact rank sandwich.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import subprocess
import sys
import time
from typing import Any, Iterable

import numpy as np


TARGET_COMMIT = "81d152cf9a6f20bdcd05e97abf61c38c5b40918e"
ROWS = 5_769
COLUMNS = 6_795
BASIS_DIMENSION = 43
FULL_BASIS_DIMENSION = 478
EXCLUDED_SEQUENCES = {1_548, 3_140, 4_259, 5_656}
SOURCE_COLUMNS = [
    0, 1, 12, 15, 17, 21, 24, 28, 62, 68, 72, 75, 82, 87, 90, 91,
    108, 117, 121, 122, 132, 135, 148, 161, 215, 220, 226, 232, 235,
    240, 241, 242, 246, 250, 271, 272, 273, 277, 280, 282, 283, 352,
]
COMBINATION_42 = {24: 1, 174: 1, 235: 1, 295: -1, 345: 1}
MISSING_DIRECTION = {174: 1, 295: -1, 345: 1}
RANK_PRIMES = (1_000_037, 1_000_099)

RELATIVE_PATHS = {
    "candidate": Path("artifacts/math/G-0190-mass4-filtration-basis/candidate/mass4_filtration_basis43.jsonl"),
    "candidate_binary": Path("artifacts/math/G-0190-mass4-filtration-basis/candidate/mass4_basis5769x43.i64le"),
    "matrix": Path("artifacts/math/G-0180-star-loop-rank-expansion/results/augmented5769x6795.i64le"),
    "star_records": Path("artifacts/math/G-0179-star-loop-quarantine/star_outside_primary_records.json"),
    "g0187_basis": Path("artifacts/math/G-0187-exact-sparse-kernel-basis/candidate/exact_sparse_left_kernel_basis_v1.jsonl"),
    "smt_le33": Path("artifacts/math/G-0190-mass4-filtration-basis/results/mass4_support_le33.smt2"),
    "smt_le34": Path("artifacts/math/G-0190-mass4-filtration-basis/results/mass4_support_le34_witness.smt2"),
}

EXPECTED_SHA256 = {
    "candidate": "7870fde3d67eb8eba0eaa10b924a4f8a717f9aa9e9e56acc54411c716edc2385",
    "candidate_binary": "bc949c3f95da084ab71d7c3aeea35469bb638fcea1ac0602bdb407aae6c3c798",
    "matrix": "d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd",
    "star_records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "g0187_basis": "24ca642c27ab84508daee27a609483e860af09e8c28134cd00e859dbe443f4fe",
    "smt_le33": "5181365d2b50df1d69b697c95941a6f79a3d046165b1acac6d5f7022dc2118ee",
    "smt_le34": "368a6090583e6b8467c0165703e331bcee84b02cfcd54756ad5554449337b527",
}


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_git_blob(repo: Path, revision: str, relative: Path) -> tuple[str, str] | None:
    resolved = subprocess.run(
        ["git", "rev-parse", f"{revision}:{relative.as_posix()}"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if resolved.returncode != 0:
        return None
    object_name = resolved.stdout.strip()
    digest = hashlib.sha256()
    process = subprocess.Popen(
        ["git", "cat-file", "blob", object_name],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert process.stdout is not None
    for block in iter(lambda: process.stdout.read(8 << 20), b""):
        digest.update(block)
    stderr = process.stderr.read().decode() if process.stderr is not None else ""
    return_code = process.wait()
    require(return_code == 0, f"git cat-file failed for {relative}: {stderr}")
    return object_name, digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def run_checked(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    require(
        completed.returncode == 0,
        f"command failed ({completed.returncode}): {command!r}\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}",
    )
    return completed


def is_prime_by_trial_division(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def parse_coefficient(text: Any, context: str) -> int:
    require(isinstance(text, str), f"{context}: coefficient is not text")
    try:
        value = int(text)
    except ValueError as error:
        raise AuditError(f"{context}: coefficient is not an integer") from error
    require(str(value) == text, f"{context}: noncanonical coefficient text")
    require(value != 0, f"{context}: zero coefficient")
    require(-(1 << 63) <= value < (1 << 63), f"{context}: coefficient outside signed i64")
    return value


def sparse_terms_to_dict(
    terms: Any,
    retained_sequences: list[int],
    context: str,
) -> dict[int, int]:
    require(isinstance(terms, list) and terms, f"{context}: empty or malformed terms")
    output: dict[int, int] = {}
    prior_row = -1
    for position, term in enumerate(terms):
        require(isinstance(term, list) and len(term) == 3, f"{context}: malformed term {position}")
        row, sequence, coefficient_text = term
        require(type(row) is int and prior_row < row < ROWS, f"{context}: row order/range drift")
        require(type(sequence) is int, f"{context}: sequence is not an integer")
        require(retained_sequences[row] == sequence, f"{context}: row/sequence mismatch at row {row}")
        coefficient = parse_coefficient(coefficient_text, f"{context} term {position}")
        output[row] = coefficient
        prior_row = row
    require(math.gcd(*[abs(value) for value in output.values()]) == 1, f"{context}: vector not primitive")
    return output


def combine_vectors(vectors: dict[int, dict[int, int]], combination: dict[int, int]) -> dict[int, int]:
    output: dict[int, int] = {}
    for column, multiplier in combination.items():
        for row, coefficient in vectors[column].items():
            output[row] = output.get(row, 0) + multiplier * coefficient
            if output[row] == 0:
                del output[row]
    return dict(sorted(output.items()))


def sparse_dict_to_terms(vector: dict[int, int], retained_sequences: list[int]) -> list[list[Any]]:
    return [[row, retained_sequences[row], str(coefficient)] for row, coefficient in sorted(vector.items())]


def maximum_abs_memmap(matrix: np.memmap, chunk_rows: int = 128) -> int:
    maximum = 0
    for start in range(0, matrix.shape[0], chunk_rows):
        block = np.asarray(matrix[start : start + chunk_rows])
        local = int(np.max(np.abs(block)))
        maximum = max(maximum, local)
    return maximum


def compile_ranker(source: Path, binary: Path) -> dict[str, Any]:
    package = run_checked(["pkg-config", "--cflags", "--libs", "flint"])
    compiler = run_checked(["g++", "--version"]).stdout.splitlines()[0]
    command = [
        "g++", "-std=c++20", "-O3", "-DNDEBUG", "-Wall", "-Wextra", "-Werror",
        str(source), *shlex.split(package.stdout), "-o", str(binary),
    ]
    run_checked(command)
    return {
        "command": command,
        "compiler": compiler,
        "flint_pkg_config_version": run_checked(["pkg-config", "--modversion", "flint"]).stdout.strip(),
        "source_sha256": sha256_file(source),
        "binary_sha256": sha256_file(binary),
    }


def run_rank(binary: Path, matrix: Path, rows: int, columns: int, prime: int) -> dict[str, Any]:
    require(is_prime_by_trial_division(prime), f"rank modulus {prime} is not prime")
    started = time.perf_counter()
    completed = run_checked([str(binary), str(matrix), str(rows), str(columns), str(prime)])
    elapsed = time.perf_counter() - started
    parsed = json.loads(completed.stdout)
    require(parsed == {
        "rows": rows,
        "columns": columns,
        "prime": prime,
        "rank_mod_prime": parsed.get("rank_mod_prime"),
    }, f"malformed ranker output at prime {prime}")
    parsed["prime_verified_by_trial_division"] = True
    parsed["elapsed_seconds"] = elapsed
    return parsed


def smt_integer(value: int) -> str:
    return str(value) if value >= 0 else f"(- {abs(value)})"


def smt_linear_expression(constant: int, terms: list[tuple[int, int]]) -> str:
    pieces: list[str] = []
    if constant:
        pieces.append(smt_integer(constant))
    for column, coefficient in terms:
        variable = f"c_{column}"
        if coefficient == 1:
            pieces.append(variable)
        elif coefficient == -1:
            pieces.append(f"(- {variable})")
        else:
            pieces.append(f"(* {smt_integer(coefficient)} {variable})")
    if not pieces:
        return "0"
    if len(pieces) == 1:
        return pieces[0]
    return f"(+ {' '.join(pieces)})"


def build_support_formula(
    path: Path,
    missing: dict[int, int],
    old_vectors: dict[int, dict[int, int]],
    source_columns: list[int],
    support_limit: int,
) -> dict[str, Any]:
    component_rows = set(missing)
    component_columns: set[int] = set()
    changed = True
    while changed:
        changed = False
        for column in source_columns:
            if column not in component_columns and component_rows.intersection(old_vectors[column]):
                component_columns.add(column)
                before = len(component_rows)
                component_rows.update(old_vectors[column])
                changed = True
    component_columns_sorted = sorted(component_columns)
    component_rows_sorted = sorted(component_rows)
    for column in source_columns:
        if column not in component_columns:
            require(
                component_rows.isdisjoint(old_vectors[column]),
                f"outside column {column} unexpectedly intersects the missing-direction component",
            )

    lines = [
        "; independently rebuilt by G-0195 from frozen G-0187 sparse vectors",
        "; exact rational affine coset: missing + span(old42), support <= 33",
        "(set-option :produce-models false)",
    ]
    lines.extend(f"(declare-fun c_{column} () Real)" for column in component_columns_sorted)
    indicators: list[str] = []
    for row in component_rows_sorted:
        terms = [
            (column, old_vectors[column].get(row, 0))
            for column in component_columns_sorted
            if old_vectors[column].get(row, 0) != 0
        ]
        expression = smt_linear_expression(missing.get(row, 0), terms)
        indicators.append(f"(ite (= {expression} 0) 0 1)")
    support_sum = indicators[0] if len(indicators) == 1 else f"(+ {' '.join(indicators)})"
    lines.extend([
        f"(assert (<= {support_sum} {support_limit}))",
        "(check-sat)",
        "(exit)",
    ])
    write_new(path, ("\n".join(lines) + "\n").encode())
    return {
        "component_columns": component_columns_sorted,
        "component_column_count": len(component_columns_sorted),
        "component_rows": component_rows_sorted,
        "component_row_count": len(component_rows_sorted),
        "outside_columns": [column for column in source_columns if column not in component_columns],
        "outside_columns_support_disjoint": True,
        "support_limit": support_limit,
        "smt2_sha256": sha256_file(path),
    }


def run_z3(z3: Path, smt2: Path) -> dict[str, Any]:
    started = time.perf_counter()
    completed = run_checked([str(z3), "-smt2", str(smt2)])
    elapsed = time.perf_counter() - started
    stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    require(len(stdout_lines) == 1 and stdout_lines[0] in {"sat", "unsat", "unknown"},
            f"unexpected z3 output for {smt2}: {completed.stdout!r}")
    return {
        "result": stdout_lines[0],
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "elapsed_seconds": elapsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--rank-source", required=True, type=Path)
    parser.add_argument("--z3", default=Path("/usr/bin/z3"), type=Path)
    args = parser.parse_args()

    require(sys.byteorder == "little", "audit requires a little-endian host")
    repo = args.repo.resolve(strict=True)
    output_dir = args.output_dir.resolve(strict=True)
    rank_source = args.rank_source.resolve(strict=True)
    verifier_source = Path(__file__).resolve(strict=True)
    z3 = args.z3.resolve(strict=True)
    receipt_path = output_dir / "g0195_cleanroom_receipt_v1.json"
    require(not receipt_path.exists(), f"refusing to overwrite {receipt_path}")

    resolved_commit = run_checked(["git", "rev-parse", f"{TARGET_COMMIT}^{{commit}}"], cwd=repo).stdout.strip()
    require(resolved_commit == TARGET_COMMIT, "target commit resolution drift")

    bindings: dict[str, Any] = {}
    input_opening_hashes: dict[str, str] = {}
    for name, relative in RELATIVE_PATHS.items():
        path = (repo / relative).resolve(strict=True)
        require(path.is_relative_to(repo), f"input escapes repository: {path}")
        worktree_sha = sha256_file(path)
        blob_binding = sha256_git_blob(repo, TARGET_COMMIT, relative)
        require(worktree_sha == EXPECTED_SHA256[name], f"worktree hash drift for {name}")
        binding = {
            "path": str(path),
            "relative_path": relative.as_posix(),
            "bytes": path.stat().st_size,
            "sha256": worktree_sha,
        }
        if blob_binding is None:
            require(name == "matrix", f"tracked target-commit input is missing: {name}")
            binding.update({
                "git_tracked_at_target_commit": False,
                "custody_note": (
                    "This large matrix is ignored by the repository. The audit binds the local file "
                    "by SHA-256, but commit 81d152c does not by itself carry or recover this blob."
                ),
            })
        else:
            blob_oid, blob_sha = blob_binding
            require(blob_sha == EXPECTED_SHA256[name], f"target-commit blob hash drift for {name}")
            binding.update({
                "git_tracked_at_target_commit": True,
                "git_blob_oid": blob_oid,
                "target_commit_blob_sha256": blob_sha,
            })
        bindings[name] = binding
        input_opening_hashes[name] = worktree_sha

    paths = {name: repo / relative for name, relative in RELATIVE_PATHS.items()}
    require(paths["matrix"].stat().st_size == ROWS * COLUMNS * 8, "matrix byte count drift")
    require(paths["candidate_binary"].stat().st_size == ROWS * BASIS_DIMENSION * 8,
            "candidate binary byte count drift")

    star_document = json.loads(paths["star_records"].read_bytes())
    star_records = star_document.get("records")
    require(isinstance(star_records, list) and len(star_records) == 5_773, "STAR record census drift")
    require([record.get("sequence") for record in star_records] == list(range(5_773)),
            "STAR sequence/index order drift")
    for sequence, record in enumerate(star_records):
        mass = record.get("signed_mass")
        require(type(mass) is int and 1 <= mass <= 5, f"invalid signed mass at sequence {sequence}")
        require(len(record.get("negative_edges", [])) == mass, f"negative-edge mass drift at {sequence}")
        require(len(record.get("positive_edges", [])) == mass, f"positive-edge mass drift at {sequence}")

    retained_sequences = [sequence for sequence in range(5_773) if sequence not in EXCLUDED_SEQUENCES]
    require(len(retained_sequences) == ROWS, "retained row census drift")
    selected_rows = [
        {
            "output_row": output_row,
            "record_sequence": sequence,
            "signed_mass": int(star_records[sequence]["signed_mass"]),
        }
        for output_row, sequence in enumerate(retained_sequences)
        if int(star_records[sequence]["signed_mass"]) <= 4
    ]
    selected_histogram = Counter(row["signed_mass"] for row in selected_rows)
    require(len(selected_rows) == 851, "retained mass<=4 row census is not 851")
    require(selected_histogram == Counter({2: 4, 3: 66, 4: 781}),
            f"retained mass<=4 histogram drift: {selected_histogram}")
    selected_row_set = {row["output_row"] for row in selected_rows}
    selected_manifest = output_dir / "derived_retained_mass_le4_rows_v1.json"
    write_new(selected_manifest, canonical_json_bytes({
        "schema": "g0195.derived-retained-mass-le4-rows.v1",
        "excluded_sequences": sorted(EXCLUDED_SEQUENCES),
        "row_to_sequence": "r-th element of sorted([0..5772] minus {1548,3140,4259,5656})",
        "rows": selected_rows,
    }))

    with paths["g0187_basis"].open() as stream:
        g0187_header = json.loads(next(stream))
        g0187_records = [json.loads(line) for line in stream if line.strip()]
    require(g0187_header.get("schema") == "g0193.greedy-exact-sparse-left-kernel-basis.v1",
            "G-0187 schema drift")
    require(g0187_header.get("basis_shape") == [ROWS, FULL_BASIS_DIMENSION], "G-0187 shape drift")
    require(len(g0187_records) == FULL_BASIS_DIMENSION, "G-0187 basis record count drift")
    require([record.get("basis_column") for record in g0187_records] == list(range(FULL_BASIS_DIMENSION)),
            "G-0187 column order drift")
    needed_source_columns = sorted(set(SOURCE_COLUMNS) | set(COMBINATION_42))
    source_vectors = {
        column: sparse_terms_to_dict(
            g0187_records[column].get("terms"), retained_sequences, f"G-0187 column {column}",
        )
        for column in needed_source_columns
    }
    for column, vector in source_vectors.items():
        source_record = g0187_records[column]
        require(source_record.get("support") == len(vector), f"G-0187 support drift at column {column}")
        require(source_record.get("sum_abs_coefficients") == str(sum(abs(v) for v in vector.values())),
                f"G-0187 sum-abs drift at column {column}")
        require(source_record.get("max_abs_coefficient") == str(max(abs(v) for v in vector.values())),
                f"G-0187 max-abs drift at column {column}")

    with paths["candidate"].open() as stream:
        candidate_header = json.loads(next(stream))
        candidate_records = [json.loads(line) for line in stream if line.strip()]
    require(candidate_header.get("schema") == "g0193.filtration-adapted-mass-le4-kernel-basis.v1",
            "candidate schema drift")
    require(candidate_header.get("ambient_matrix_shape") == [ROWS, COLUMNS], "ambient shape drift")
    require(candidate_header.get("basis_shape") == [ROWS, BASIS_DIMENSION], "candidate basis shape drift")
    require(candidate_header.get("source_candidate_sha256") == EXPECTED_SHA256["g0187_basis"],
            "candidate source hash drift")
    require(candidate_header.get("binary_i64le_sha256") == EXPECTED_SHA256["candidate_binary"],
            "candidate binary hash header drift")
    require(candidate_header.get("row_to_sequence") ==
            "r-th element of sorted([0..5772] minus {1548,3140,4259,5656})",
            "candidate row mapping statement drift")
    require(len(candidate_records) == BASIS_DIMENSION, "candidate record count drift")

    candidate_vectors: list[dict[int, int]] = []
    mass_maxima: list[int] = []
    support_total = 0
    for expected_column, record in enumerate(candidate_records):
        context = f"candidate column {expected_column}"
        require(record.get("tranche_column") == expected_column, f"{context}: tranche order drift")
        vector = sparse_terms_to_dict(record.get("terms"), retained_sequences, context)
        require(set(vector) <= selected_row_set, f"{context}: support escapes retained mass<=4 rows")
        masses = [int(star_records[retained_sequences[row]]["signed_mass"]) for row in vector]
        histogram = Counter(masses)
        require(record.get("support") == len(vector), f"{context}: support statistic drift")
        require(record.get("max_signed_mass") == max(masses), f"{context}: max-mass drift")
        require(record.get("signed_mass_histogram") ==
                {str(key): count for key, count in sorted(histogram.items())},
                f"{context}: mass histogram drift")
        origin = record.get("origin")
        require(isinstance(origin, dict), f"{context}: missing origin")
        if expected_column < 42:
            source_column = SOURCE_COLUMNS[expected_column]
            require(origin == {"kind": "sparse_basis_column", "basis_column": source_column},
                    f"{context}: source origin/order drift")
            require(record.get("terms") == g0187_records[source_column].get("terms"),
                    f"{context}: not a literal copy of G-0187 B{source_column}")
            require(vector == source_vectors[source_column], f"{context}: source vector mismatch")
        else:
            require(origin.get("kind") == "exact_basis_combination", "column 42 origin-kind drift")
            require(origin.get("formula") == "B_24 + B_174 + B_235 - B_295 + B_345",
                    "column 42 formula text drift")
            require(origin.get("old_basis_coefficients") ==
                    {str(key): str(value) for key, value in COMBINATION_42.items()},
                    "column 42 coefficient manifest drift")
            constructed = combine_vectors(source_vectors, COMBINATION_42)
            require(vector == constructed, "column 42 is not the claimed exact G-0187 combination")
            require(record.get("terms") == sparse_dict_to_terms(constructed, retained_sequences),
                    "column 42 sparse serialization drift")
        candidate_vectors.append(vector)
        mass_maxima.append(max(masses))
        support_total += len(vector)

    candidate_mass_histogram = Counter(mass_maxima)
    require(candidate_mass_histogram == Counter({3: 3, 4: 40}), "candidate max-mass histogram drift")
    require(candidate_header.get("max_signed_mass_histogram") ==
            {str(key): count for key, count in sorted(candidate_mass_histogram.items())},
            "candidate header max-mass histogram drift")

    dense_basis = np.zeros((ROWS, BASIS_DIMENSION), dtype="<i8")
    for column, vector in enumerate(candidate_vectors):
        for row, coefficient in vector.items():
            dense_basis[row, column] = coefficient
    reconstructed_basis_path = output_dir / "reconstructed_mass4_basis5769x43.i64le"
    dense_basis.tofile(reconstructed_basis_path)
    reconstructed_basis_sha = sha256_file(reconstructed_basis_path)
    require(reconstructed_basis_sha == EXPECTED_SHA256["candidate_binary"],
            "reconstructed dense basis hash does not match frozen sibling")
    require(reconstructed_basis_path.read_bytes() == paths["candidate_binary"].read_bytes(),
            "reconstructed dense basis is not byte-identical to frozen sibling")

    matrix = np.memmap(paths["matrix"], mode="r", dtype="<i8", shape=(ROWS, COLUMNS))
    matrix_max_abs = maximum_abs_memmap(matrix)
    require(matrix_max_abs == 120_960, f"matrix maximum absolute entry drift: {matrix_max_abs}")
    maximum_accumulation_bound = max(
        sum(abs(coefficient) for coefficient in vector.values()) * matrix_max_abs
        for vector in candidate_vectors
    )
    require(maximum_accumulation_bound < (1 << 63), "signed-i64 exact replay bound failed")

    residuals = np.zeros((BASIS_DIMENSION, COLUMNS), dtype="<i8")
    for column, vector in enumerate(candidate_vectors):
        residual = residuals[column]
        for row, coefficient in vector.items():
            residual += np.multiply(matrix[row], coefficient, dtype=np.int64)
    nonzero_residuals = int(np.count_nonzero(residuals))
    require(nonzero_residuals == 0, "candidate contains a non-null vector")
    residual_path = output_dir / "exact_residual43x6795.i64le"
    residuals.tofile(residual_path)

    mutant_column = 0
    mutant_row = next(iter(candidate_vectors[mutant_column]))
    mutant_residual = residuals[mutant_column] + np.asarray(matrix[mutant_row])
    require(np.array_equal(mutant_residual, np.asarray(matrix[mutant_row])),
            "one-unit mutant residual is not exactly the added matrix row")
    mutant_nonzero = int(np.count_nonzero(mutant_residual))
    require(mutant_nonzero > 0, "one-unit mutant was not rejected")
    mutant_path = output_dir / "one_unit_mutant_residual6795.i64le"
    mutant_residual.astype("<i8", copy=False).tofile(mutant_path)

    selected_output_rows = [row["output_row"] for row in selected_rows]
    low_matrix = np.asarray(matrix[selected_output_rows], dtype="<i8")
    require(low_matrix.shape == (851, COLUMNS), "derived low-mass matrix shape drift")
    low_matrix_path = output_dir / "derived_mass_le4_851x6795.i64le"
    low_matrix.tofile(low_matrix_path)
    del low_matrix

    rank_binary = output_dir / "rank_mod_flint"
    rank_build = compile_ranker(rank_source, rank_binary)
    coefficient_rank_profiles = [
        run_rank(rank_binary, reconstructed_basis_path, ROWS, BASIS_DIMENSION, prime)
        for prime in RANK_PRIMES
    ]
    require(all(profile["rank_mod_prime"] == BASIS_DIMENSION for profile in coefficient_rank_profiles),
            "candidate coefficient matrix is not full-column-rank")
    lowmass_rank_profiles = [
        run_rank(rank_binary, low_matrix_path, 851, COLUMNS, prime)
        for prime in RANK_PRIMES
    ]
    require(all(profile["rank_mod_prime"] == 808 for profile in lowmass_rank_profiles),
            "retained mass<=4 block modular rank is not 808")

    missing = combine_vectors(source_vectors, MISSING_DIRECTION)
    require(set(missing) <= selected_row_set, "missing direction fails to cancel above mass four")
    combination_42 = combine_vectors(source_vectors, COMBINATION_42)
    witness = combine_vectors(
        {**source_vectors, -1: missing},
        {-1: 1, 24: 1, 235: 1},
    )
    require(witness == combination_42 == candidate_vectors[42],
            "support-34 witness is not candidate column 42")
    require(len(witness) == 34, "claimed support-34 witness has wrong support")

    rebuilt_smt = output_dir / "independently_rebuilt_support_le33.smt2"
    component = build_support_formula(
        rebuilt_smt,
        missing,
        source_vectors,
        SOURCE_COLUMNS,
        33,
    )
    require(component["component_column_count"] == 18, "rebuilt support component column count drift")
    require(component["component_row_count"] == 169, "rebuilt support component row count drift")

    z3_version = run_checked([str(z3), "-version"]).stdout.strip()
    frozen_le33_result = run_z3(z3, paths["smt_le33"])
    frozen_le34_result = run_z3(z3, paths["smt_le34"])
    rebuilt_le33_result = run_z3(z3, rebuilt_smt)
    require(frozen_le33_result["result"] == "unsat", "frozen support<=33 instance not UNSAT")
    require(frozen_le34_result["result"] == "sat", "frozen support<=34 witness instance not SAT")
    require(rebuilt_le33_result["result"] == "unsat", "independently rebuilt support<=33 instance not UNSAT")

    del matrix
    ending_hashes = {name: sha256_file(repo / relative) for name, relative in RELATIVE_PATHS.items()}
    require(ending_hashes == input_opening_hashes, "one or more frozen inputs changed during audit")

    output_bindings = {}
    for name, path in {
        "verifier_source": verifier_source,
        "rank_source": rank_source,
        "rank_binary": rank_binary,
        "selected_row_manifest": selected_manifest,
        "reconstructed_basis": reconstructed_basis_path,
        "exact_residual": residual_path,
        "mutant_residual": mutant_path,
        "derived_lowmass_matrix": low_matrix_path,
        "rebuilt_support_le33_smt2": rebuilt_smt,
        "z3_binary": z3,
    }.items():
        output_bindings[name] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }

    receipt = {
        "schema": "g0195.g0190-independent-cleanroom-audit.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "GO_MATHEMATICAL_CLAIMS_WITH_CUSTODY_AND_SMT_TRUST_BOUNDARIES",
        "target_commit": TARGET_COMMIT,
        "independence_boundary": (
            "Fresh implementation and fresh agent context, using the tracked artifacts at commit "
            "81d152c plus the locally present matrix bound by SHA-256 d57e...; no G-0190 discovery "
            "verifier/finalizer was imported or executed. This is same-model-lineage T1 computational "
            "replay, not a T2 referee and not proof-assistant certification."
        ),
        "verdicts": {
            "bounded_mathematical_basis_claim": "GO",
            "repo_self_contained_reproducibility_at_81d152c": "NO_GO_MATRIX_BLOB_NOT_TRACKED",
            "smt_cli_replay_and_independent_formula_rebuild": "GO",
            "proof_assistant_certification_of_support_minimum": "NOT_ESTABLISHED",
        },
        "bindings": bindings,
        "derived_artifacts": output_bindings,
        "candidate_integrity": {
            "vectors": BASIS_DIMENSION,
            "total_sparse_terms": support_total,
            "all_rows_strictly_ordered_and_in_range": True,
            "all_row_sequence_bindings_exact": True,
            "all_coefficients_canonical_nonzero_signed_i64": True,
            "all_vectors_primitive": True,
            "all_terms_on_retained_mass_le4_rows": True,
            "max_signed_mass_histogram": {str(k): v for k, v in sorted(candidate_mass_histogram.items())},
            "dense_binary_byte_identical_to_frozen_sibling": True,
            "dense_binary_sha256": reconstructed_basis_sha,
        },
        "retained_mass_le4_reconstruction": {
            "full_star_records": len(star_records),
            "retained_matrix_rows": len(retained_sequences),
            "selected_rows": len(selected_rows),
            "signed_mass_histogram": {str(k): v for k, v in sorted(selected_histogram.items())},
            "selected_row_manifest_sha256": sha256_file(selected_manifest),
            "derived_matrix_shape": [851, COLUMNS],
            "derived_matrix_sha256": sha256_file(low_matrix_path),
        },
        "g0187_lineage": {
            "first_42_source_columns_in_order": SOURCE_COLUMNS,
            "first_42_literal_terms_match": True,
            "column_42_formula": "B_24 + B_174 + B_235 - B_295 + B_345",
            "column_42_exact_match": True,
            "missing_direction_formula": "B_174 - B_295 + B_345",
            "missing_direction_supported_on_mass_le4": True,
        },
        "exact_replay": {
            "operator": "C^T A",
            "vectors": BASIS_DIMENSION,
            "coordinates_per_vector": COLUMNS,
            "scalar_equations_checked": BASIS_DIMENSION * COLUMNS,
            "nonzero_equations": nonzero_residuals,
            "residual_sha256": sha256_file(residual_path),
            "matrix_maximum_absolute_entry": matrix_max_abs,
            "maximum_signed_accumulation_bound": maximum_accumulation_bound,
            "signed_i64_safe": True,
            "hostile_control": {
                "mutation": f"add +1 to candidate column {mutant_column} at output row {mutant_row}",
                "rejected": True,
                "nonzero_coordinates": mutant_nonzero,
                "residual_equals_added_frozen_matrix_row": True,
                "residual_sha256": sha256_file(mutant_path),
            },
        },
        "rank": {
            "implementation": rank_build,
            "coefficient_matrix_profiles": coefficient_rank_profiles,
            "coefficient_rank_Q": BASIS_DIMENSION,
            "coefficient_rank_logic": (
                "Rank 43 modulo either verified prime exhibits a nonzero integer 43-minor; hence "
                "rank_Q(C)>=43, while C has only 43 columns, so rank_Q(C)=43."
            ),
            "lowmass_block_profiles": lowmass_rank_profiles,
            "rank_sandwich": {
                "rows": 851,
                "rank_mod_prime_lower_bound_for_rank_Q": 808,
                "exact_independent_left_null_vectors": BASIS_DIMENSION,
                "rank_Q_upper_bound_from_nulls": 851 - BASIS_DIMENSION,
                "rank_Q": 808,
                "left_nullity_Q": BASIS_DIMENSION,
                "candidate_is_complete_left_kernel_basis": True,
                "logic": (
                    "A nonzero 808-minor modulo a prime remains a nonzero integer minor, so "
                    "rank_Q(A_low)>=808. Forty-three exact independent vectors in ker(A_low^T) "
                    "give rank_Q(A_low)<=851-43=808. Thus rank_Q=808 and nullity_Q=43."
                ),
            },
        },
        "support_minimum": {
            "z3_version": z3_version,
            "z3_binary_sha256": sha256_file(z3),
            "frozen_support_le33": frozen_le33_result,
            "frozen_support_le34_witness": frozen_le34_result,
            "rebuilt_support_le33": rebuilt_le33_result,
            "rebuilt_component": component,
            "support_34_witness_exactly_candidate_column_42": True,
            "support_34_witness_terms": len(witness),
            "formula_scope": (
                "Exact rational affine coset (B174-B295+B345)+span_Q(the frozen old42). "
                "The bipartite row/column component reduction is exact because every omitted old42 "
                "column has support disjoint from the missing-direction component and can be set to zero."
            ),
            "projective_reduction": (
                "Every vector in span_Q(old42,missing) outside span_Q(old42) has nonzero missing "
                "coefficient; scaling it to one preserves support."
            ),
            "certification_boundary": (
                "The CLI results and independently rebuilt formula are strong exact-SMT replay evidence, "
                "but Z3 4.13.3 emitted no independently checked proof object. This is not Lean/Coq/Isabelle "
                "certification and does not eliminate the solver implementation from the trust base."
            ),
        },
        "input_custody": {
            "all_inputs_rehashed_unchanged_at_end": True,
            "opening_sha256": input_opening_hashes,
            "ending_sha256": ending_hashes,
        },
        "claim_boundary": (
            "For exactly the candidate tracked at commit 81d152c, the 851 retained signed-mass<=4 "
            "rows, and the local 6,795-coordinate integer restriction matrix bound by SHA-256 "
            "d57ec8... (but absent from that commit), the left kernel has dimension 43 and the frozen "
            "candidate is a complete exact basis. The missing quotient direction has minimum q-row "
            "support 34 relative to the frozen old42, subject to the stated SMT trust boundary. This "
            "does not classify any mass-four direction into O, decide MAX11, prove ansatz completeness, "
            "or imply an unrestricted neural-network lower bound."
        ),
    }
    write_new(receipt_path, canonical_json_bytes(receipt))
    print(json.dumps({
        "result": receipt["result"],
        "receipt": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "rank_Q": 808,
        "nullity_Q": BASIS_DIMENSION,
        "support_le33": rebuilt_le33_result["result"],
        "support_le34_witness": frozen_le34_result["result"],
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    try:
        main()
    except (AuditError, OSError, ValueError, json.JSONDecodeError, subprocess.CalledProcessError) as error:
        print(f"audit_g0190_cleanroom: {error}", file=sys.stderr)
        raise SystemExit(2)
