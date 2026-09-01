#!/usr/bin/env python3
"""Clean replay of the bounded G-0185 low-mass STAR quarantine theorem."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import numpy as np


ROWS = 5_769
COLS = 6_795
LOW_ROWS = 70
RANK = 67
PRIMES = (1_000_003, 1_000_033)
EXCLUDED = (1_548, 3_140, 4_259, 5_656)
BASIS_COLUMNS = (0, 15, 130)
SCALES = {0: 10, 15: 1, 130: 2}
WITNESS_SEQUENCES = (2_124, 3_944, 5_155)
EXPECTED = {
    "candidate": "7d3f6c5e78934fa57c08326d2ea9a8543d07c538a47be45e5f70d5b112e3d0e2",
    "matrix": "d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd",
    "star_records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "kernel_basis": "56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232",
    "lift_15": "f92635277b6d24c8c69eac2048af1152008ef5626ab96cc7a41403a7d520aa3d",
    "lift_0": "c3dd7eb92a906b3ad2563dea96f02ec3cbfb51777f34dc681840de7e6e6419e1",
    "lift_130": "5860b2b15c01b5951f76d82751451d450a62b03c4b9c9f576e96fbee62555898",
}


class VerificationError(RuntimeError):
    """A frozen binding or theorem gate failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


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
        path.unlink(missing_ok=True)
        raise


def modular_rref(source: np.ndarray, prime: int) -> tuple[int, list[int], str]:
    matrix = np.remainder(source, prime).astype(np.int64, copy=True)
    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(matrix.shape[1]):
        candidates = np.flatnonzero(matrix[pivot_row:, column])
        if not len(candidates):
            continue
        selected = pivot_row + int(candidates[0])
        if selected != pivot_row:
            matrix[[pivot_row, selected]] = matrix[[selected, pivot_row]]
        inverse = pow(int(matrix[pivot_row, column]), -1, prime)
        matrix[pivot_row] = (matrix[pivot_row] * inverse) % prime
        factors = matrix[:, column].copy()
        factors[pivot_row] = 0
        active = np.flatnonzero(factors)
        if len(active):
            # Every product is below prime^2 < 2^40, so signed int64 is exact.
            matrix[active] = (
                matrix[active] - factors[active, None] * matrix[pivot_row]
            ) % prime
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == matrix.shape[0]:
            break
    digest = hashlib.sha256(matrix.astype("<u8", copy=False).tobytes(order="C")).hexdigest()
    return pivot_row, pivot_columns, digest


def load_kernel_columns(
    path: Path,
    retained_sequences: list[int],
    low_sequence_to_index: dict[int, int],
) -> tuple[np.ndarray, dict[int, dict[int, int]]]:
    with path.open() as stream:
        header = json.loads(next(stream))
        relations = [json.loads(line) for line in stream]
    require(header.get("schema") == "g0189.exact-primitive-left-kernel-basis.v1",
            "kernel-basis schema drift")
    require(header.get("matrix_shape") == [ROWS, COLS], "kernel matrix shape drift")
    require(header.get("basis_shape") == [ROWS, 478], "kernel basis shape drift")
    require(len(relations) == 478, "kernel relation census drift")
    by_column = {int(relation["basis_column"]): relation for relation in relations}
    require(len(by_column) == 478, "duplicate kernel basis column")

    coefficient_matrix = np.zeros((LOW_ROWS, len(BASIS_COLUMNS)), dtype=np.int64)
    term_maps: dict[int, dict[int, int]] = {}
    for matrix_column, basis_column in enumerate(BASIS_COLUMNS):
        relation = by_column[basis_column]
        terms = relation.get("terms")
        require(isinstance(terms, list) and terms, f"empty basis column {basis_column}")
        term_map: dict[int, int] = {}
        previous_row = -1
        for term in terms:
            require(isinstance(term, list) and len(term) == 3,
                    f"malformed term in basis column {basis_column}")
            output_row, sequence, coefficient_text = term
            require(type(output_row) is int and type(sequence) is int,
                    f"noninteger row binding in basis column {basis_column}")
            require(0 <= output_row < ROWS and output_row > previous_row,
                    f"row order/range drift in basis column {basis_column}")
            require(retained_sequences[output_row] == sequence,
                    f"row-to-sequence drift in basis column {basis_column}")
            require(sequence in low_sequence_to_index,
                    f"basis column {basis_column} escapes low-mass rows")
            require(isinstance(coefficient_text, str), "coefficient encoding drift")
            coefficient = int(coefficient_text)
            require(coefficient != 0 and sequence not in term_map,
                    f"zero/duplicate term in basis column {basis_column}")
            term_map[sequence] = coefficient
            coefficient_matrix[low_sequence_to_index[sequence], matrix_column] = coefficient
            previous_row = output_row
        require(len(term_map) == int(relation["support"]),
                f"support statistic drift in basis column {basis_column}")
        term_maps[basis_column] = term_map
    return coefficient_matrix, term_maps


def replay_lift(receipt_path: Path, receipt: dict[str, Any], temporary: Path) -> str:
    verifier = Path(receipt["verifier"]["path"])
    require(sha256_file(verifier) == receipt["verifier"]["sha256"],
            f"lift verifier hash drift: {verifier}")
    bindings = receipt["bindings"]
    command = [
        sys.executable,
        str(verifier),
        "--candidate", str(bindings["candidate"]["path"]),
    ]
    if "kernel_basis" in bindings:
        command.extend(["--kernel-basis", str(bindings["kernel_basis"]["path"])])
    command.extend([
        "--primary-records", str(bindings["primary_records"]["path"]),
        "--star-records", str(bindings["star_records"]["path"]),
        "--g0109-source", str(bindings["g0109_source"]["path"]),
        "--g0109-binary", str(bindings["g0109_binary"]["path"]),
        "--g0179-lib-source", str(bindings["g0179_lib_source"]["path"]),
        "--g0179-main-source", str(bindings["g0179_main_source"]["path"]),
        "--g0179-binary", str(bindings["g0179_binary"]["path"]),
    ])
    output = temporary / f"fresh-{receipt_path.parent.parent.name}.json"
    command.extend(["--output", str(output)])
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    require(completed.returncode == 0,
            f"lift replay failed: {command!r}\n{completed.stdout}\n{completed.stderr}")
    require(not completed.stderr, f"lift replay emitted stderr: {verifier}")
    require(output.read_bytes() == receipt_path.read_bytes(),
            f"fresh lift replay is not byte-identical: {receipt_path}")
    return sha256_file(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--star-records", required=True, type=Path)
    parser.add_argument("--kernel-basis", required=True, type=Path)
    parser.add_argument("--lift-15", required=True, type=Path)
    parser.add_argument("--lift-0", required=True, type=Path)
    parser.add_argument("--lift-130", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    require(not args.output.exists(), f"refusing to overwrite {args.output}")

    paths = {
        "candidate": args.candidate.resolve(strict=True),
        "matrix": args.matrix.resolve(strict=True),
        "star_records": args.star_records.resolve(strict=True),
        "kernel_basis": args.kernel_basis.resolve(strict=True),
        "lift_15": args.lift_15.resolve(strict=True),
        "lift_0": args.lift_0.resolve(strict=True),
        "lift_130": args.lift_130.resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in paths.items()}
    require(opening == EXPECTED, f"frozen input hash drift: {opening}")
    require(paths["matrix"].stat().st_size == ROWS * COLS * 8,
            "restriction matrix byte size drift")

    candidate = json.loads(paths["candidate"].read_bytes())
    require(candidate.get("schema") == "g0185.low-mass-star-quarantine-theorem-candidate.v1",
            "candidate schema drift")
    require(tuple(candidate.get("excluded_star_sequences", [])) == EXCLUDED,
            "candidate exclusion drift")
    require(tuple(candidate.get("kernel_basis_columns", [])) == BASIS_COLUMNS,
            "candidate kernel-column drift")
    theorem = candidate.get("theorem", {})
    require(theorem.get("retained_low_mass_rows") == LOW_ROWS, "candidate row count drift")
    require(theorem.get("exact_rank") == RANK, "candidate rank drift")
    require(theorem.get("exact_kernel_dimension") == 3, "candidate nullity drift")
    declared_lifts = {int(item["basis_column"]): item["sha256"]
                      for item in candidate.get("lift_receipts", [])}
    require(declared_lifts == {15: EXPECTED["lift_15"], 0: EXPECTED["lift_0"],
                               130: EXPECTED["lift_130"]},
            "candidate lift binding drift")

    star_document = json.loads(paths["star_records"].read_bytes())
    records = star_document.get("records")
    require(isinstance(records, list) and len(records) == 5_773, "STAR census drift")
    require([record.get("sequence") for record in records] == list(range(5_773)),
            "STAR sequence/order drift")
    retained = [record for record in records if int(record["sequence"]) not in EXCLUDED]
    require(len(retained) == ROWS, "retained STAR row count drift")
    retained_sequences = [int(record["sequence"]) for record in retained]
    low = [(row, record) for row, record in enumerate(retained)
           if int(record["signed_mass"]) <= 3]
    require(len(low) == LOW_ROWS, "low-mass row count drift")
    mass_histogram = Counter(int(record["signed_mass"]) for _, record in low)
    require(mass_histogram == Counter({2: 4, 3: 66}), "low-mass histogram drift")
    low_sequences = [int(record["sequence"]) for _, record in low]
    low_sequence_to_index = {sequence: index for index, sequence in enumerate(low_sequences)}
    require(len(low_sequence_to_index) == LOW_ROWS, "duplicate low-mass sequence")

    matrix = np.memmap(paths["matrix"], dtype="<i8", mode="r", shape=(ROWS, COLS))
    selected = np.asarray(matrix[[row for row, _ in low], :])
    require(selected.shape == (LOW_ROWS, COLS), "selected matrix shape drift")
    selected_sha256 = hashlib.sha256(
        selected.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    require(selected_sha256 == "332e238b36abc07f9c8fe817afd5b1cf6afb91e810f8ee7adc8b543920f47cb7",
            "derived low-mass matrix digest drift")

    modular: list[dict[str, Any]] = []
    common_pivots: list[int] | None = None
    for prime in PRIMES:
        rank, pivots, rref_sha256 = modular_rref(selected, prime)
        require(rank == RANK and len(pivots) == RANK, f"rank drift at prime {prime}")
        if common_pivots is None:
            common_pivots = pivots
        else:
            require(pivots == common_pivots, "modular pivot columns disagree")
        modular.append({
            "prime": prime,
            "rank": rank,
            "pivot_columns": pivots,
            "rref_u64le_sha256": rref_sha256,
        })

    coefficients, term_maps = load_kernel_columns(
        paths["kernel_basis"], retained_sequences, low_sequence_to_index
    )
    require([int(np.count_nonzero(coefficients[:, index])) for index in range(3)] == [6, 4, 6],
            "kernel generator support drift")
    residual = coefficients.T @ selected
    require(not np.count_nonzero(residual), "exact low-mass kernel replay failed")
    residual_sha256 = hashlib.sha256(
        residual.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    coefficient_sha256 = hashlib.sha256(
        coefficients.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    witness_rows = [low_sequence_to_index[sequence] for sequence in WITNESS_SEQUENCES]
    witness = coefficients[witness_rows, :]
    require(np.array_equal(witness, np.eye(3, dtype=np.int64)),
            "exact independence witness is not the identity")

    hostile = coefficients[:, 0].copy()
    hostile[low_sequence_to_index[447]] += 1
    hostile_residual = hostile @ selected
    require(np.count_nonzero(hostile_residual) > 0, "one-unit kernel mutant escaped")
    require(np.array_equal(hostile_residual, selected[low_sequence_to_index[447]]),
            "hostile residual does not equal the added source row")

    lift_paths = {15: paths["lift_15"], 0: paths["lift_0"], 130: paths["lift_130"]}
    lift_composition: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="g0185-lift-replays-") as raw_temp:
        temporary = Path(raw_temp)
        for basis_column in (15, 0, 130):
            lift_path = lift_paths[basis_column]
            lift = json.loads(lift_path.read_bytes())
            lift_terms = {int(sequence): int(coefficient)
                          for sequence, coefficient in lift["identity"]["left_star"].items()}
            expected_terms = {sequence: SCALES[basis_column] * coefficient
                              for sequence, coefficient in term_maps[basis_column].items()}
            require(lift_terms == expected_terms,
                    f"lift does not bind to basis column {basis_column}")
            semantics = lift.get("exact_semantics", {})
            require(semantics.get("residual_nonzero_hinges") == 0,
                    f"nonzero lift hinge residual for column {basis_column}")
            require(all(int(value) == 0 for value in semantics.get("residual_linear", []))
                    and len(semantics.get("residual_linear", [])) == 11,
                    f"nonzero lift linear residual for column {basis_column}")
            hostile_control = lift.get("hostile_control", {})
            require(hostile_control.get("rejected") is True and
                    (hostile_control.get("mutant_nonzero_hinges", 0) > 0 or
                     hostile_control.get("mutant_nonzero_linear_coordinates", 0) > 0),
                    f"lift hostile control failed for column {basis_column}")
            require(isinstance(lift["identity"].get("right_primary"), dict)
                    and lift["identity"]["right_primary"],
                    f"empty old-primary representation for column {basis_column}")
            fresh_sha256 = replay_lift(lift_path, lift, temporary)
            require(fresh_sha256 == sha256_file(lift_path),
                    f"fresh lift hash mismatch for column {basis_column}")
            lift_composition.append({
                "basis_column": basis_column,
                "scale": SCALES[basis_column],
                "receipt_sha256": sha256_file(lift_path),
                "fresh_replay_byte_identical": True,
                "old_primary_terms": len(lift["identity"]["right_primary"]),
                "complete_union_hinge_directions": semantics["raw_all_term_union_hinge_directions"],
            })

    closing = {name: sha256_file(path) for name, path in paths.items()}
    require(closing == opening, "input changed during theorem replay")
    source = Path(__file__).resolve()
    receipt = {
        "schema": "g0185.low-mass-star-quarantine-clean-replay.v1",
        "result": "PASS_COMPLETE_SIGNED_MASS_AT_MOST_THREE_STAR_KERNEL_QUARANTINE",
        "theorem": (
            "Every rational combination supported on the 70 retained signed-mass-at-most-three "
            "STAR records whose frozen 6,795-coordinate restriction is zero belongs, as a "
            "complete characteristic-zero CPWL function, to the frozen old-primary span O."
        ),
        "claim_boundary": (
            "Only relations supported entirely on the 70 retained signed-mass-at-most-three "
            "STAR records are classified. Mixed higher-mass relations, the remaining global "
            "STAR kernel, MAX11 membership, ansatz completeness, and unrestricted neural-network "
            "lower bounds are outside scope."
        ),
        "bindings": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": opening[name]}
            for name, path in paths.items()
        },
        "verifier": {
            "path": str(source),
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
            "python": sys.version,
            "numpy": np.__version__,
        },
        "row_selection": {
            "excluded_sequences": list(EXCLUDED),
            "retained_rows": ROWS,
            "rule": "signed_mass <= 3",
            "selected_rows": LOW_ROWS,
            "signed_mass_histogram": {str(key): value for key, value in sorted(mass_histogram.items())},
            "selected_record_sequences": low_sequences,
            "selected_matrix_shape": [LOW_ROWS, COLS],
            "selected_matrix_i64le_sha256": selected_sha256,
        },
        "modular_lower_bound": {
            "profiles": modular,
            "identical_pivot_columns": True,
            "proof_direction": (
                "rank_Fp(A_low)=67 supplies a nonzero integer 67-minor, hence rank_Q(A_low)>=67"
            ),
            "int64_safety": "all normalized elimination products are below prime^2 < 2^40",
        },
        "exact_kernel_upper_bound": {
            "basis_columns": list(BASIS_COLUMNS),
            "supports": [6, 4, 6],
            "coefficient_matrix_i64le_sha256": coefficient_sha256,
            "equations_checked": 3 * COLS,
            "nonzero_equations": int(np.count_nonzero(residual)),
            "residual_i64le_sha256": residual_sha256,
            "exact_int64_bound": int(6 * np.max(np.abs(selected))),
            "independence_witness_sequences": list(WITNESS_SEQUENCES),
            "independence_witness": witness.tolist(),
            "proof_direction": (
                "three independent exact left-null vectors give nullity_Q>=3 and rank_Q<=67"
            ),
        },
        "rank_sandwich": {
            "rational_rank": RANK,
            "rational_left_nullity": 3,
            "kernel_basis_columns": list(BASIS_COLUMNS),
            "kernel_span_proved": True,
        },
        "old_primary_lift_composition": lift_composition,
        "hostile_control": {
            "mutation": "basis column 0 coefficient at STAR sequence 447 changed from 1 to 2",
            "nonzero_equations": int(np.count_nonzero(hostile_residual)),
            "residual_equals_added_source_row": True,
            "residual_i64le_sha256": hashlib.sha256(
                hostile_residual.astype("<i8", copy=False).tobytes(order="C")
            ).hexdigest(),
            "rejected": True,
        },
        "logic": {
            "kernel_equals_span_of_three_exact_generators": True,
            "each_generator_is_a_complete_function_in_O": True,
            "therefore_entire_low_mass_kernel_is_contained_in_O": True,
        },
        "all_inputs_rehashed_unchanged_at_end": True,
    }
    write_new(args.output, canonical_json(receipt))
    print(json.dumps({
        "result": receipt["result"],
        "rank_Q": RANK,
        "kernel_dimension_Q": 3,
        "output": str(args.output),
        "output_sha256": sha256_file(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verify_low_mass_quarantine: {error}", file=sys.stderr)
        raise SystemExit(1)
