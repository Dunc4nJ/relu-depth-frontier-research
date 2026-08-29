#!/usr/bin/env python3
"""Characteristic-zero replay of the shared small lift of the 35-term candidate."""

from __future__ import annotations

import argparse
from itertools import combinations
import gzip
import hashlib
import importlib.util
import json
from math import comb, factorial
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
GATE_SCRIPT = HERE / "complete_modular_gate.py"
GATE_REPORT = HERE / "complete_modular_gate_v1.json.gz"
EXPECTED_GATE_SCRIPT_HASH = "9bd7fb12aebdaf1dfeb7f3c81772ba2205185c87441c830b6a3e3e66db3777c0"
EXPECTED_GATE_REPORT_HASH = "5f4c51e88a26dbfa1aee53e93c140d8687df7f5a0d1033fb6912ff27812b263b"
DEFAULT_OUTPUT = HERE / "exact_integer_refutation_v1.json.gz"
SCHEMA = "max11-g0048-exact-integer-refutation-v1"
N = 11
INVARIANT_SCALE = 239_500_800
INTEGER_WEIGHTS = (
    32, -16, -16, 24, 8, -48, 32, -12, -12, 128, -16, -48, -16,
    2, 6, -52, -84, 24, 24, 8, 24, -1, 6, 66, -12, -4, -12, -12,
    -7, -12, 2, 2, 6, 2, -1,
)

Direction = tuple[int, ...]

GATE: Any = None


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_gate() -> tuple[Any, dict[str, object]]:
    if sha256_path(GATE_SCRIPT) != EXPECTED_GATE_SCRIPT_HASH:
        raise ValueError("complete gate script drift")
    if sha256_path(GATE_REPORT) != EXPECTED_GATE_REPORT_HASH:
        raise ValueError("complete gate report drift")
    spec = importlib.util.spec_from_file_location("g0048_complete_gate", GATE_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import complete gate")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with gzip.open(GATE_REPORT, "rt", encoding="utf-8") as source:
        report = json.load(source)
    if report.get("result") != "COMPLETE_REPLAY_REFUTES_SELECTED_ROW_CANDIDATE":
        raise ValueError("complete modular gate result drift")
    return module, report


def init_worker() -> None:
    global GATE
    GATE, _report = load_gate()
    GATE.init_worker()


def column_worker(record: dict[str, object]) -> tuple[int, dict[Direction, int], tuple[int, ...]]:
    index, hinges, vector, _active, _t_count = GATE.complete_column_worker(record)
    return index, hinges, vector


def exact_lower_f_decomposition(vector: list[int]) -> list[int]:
    coefficients: list[int] = []
    for rank in range(1, N):
        value = vector[rank - 1] - sum(
            coefficients[m - 1] * comb(rank - 1, m - 1)
            for m in range(1, rank)
        )
        coefficients.append(value)
    last = sum(
        coefficients[m - 1] * comb(N - 1, m - 1) for m in range(1, N)
    )
    if last != vector[-1]:
        raise AssertionError("exact correction escaped lower-F span")
    return coefficients


def add_hinges(
    residual: dict[Direction, int], hinges: dict[Direction, int], coefficient: int
) -> None:
    for direction, value in hinges.items():
        updated = residual.get(direction, 0) + coefficient * value
        if updated:
            residual[direction] = updated
        else:
            residual.pop(direction, None)


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    gate, gate_report = load_gate()
    search, theorem, _extract = gate.load_inputs()
    records = search.load_records(theorem)
    universe = search.direction_universe()
    frozen_universe = tuple(
        tuple(map(int, direction))
        for direction in gate_report["frozen_row_universe"]["directions"]
    )
    if universe != frozen_universe:
        raise AssertionError("regenerated universe differs from frozen gate")
    support = list(map(int, gate_report["frozen_support"]["zero_based_record_indices"]))
    if len(support) != len(INTEGER_WEIGHTS):
        raise AssertionError("integer lift/support length mismatch")

    scaling_checks = []
    for item in gate_report["frozen_two_prime_candidate_vectors"]:
        prime = int(item["prime"])
        modular = list(map(int, item["support_coefficients"]))
        lifted = [
            (INVARIANT_SCALE * coefficient) % prime for coefficient in modular
        ]
        exact_reduced = [weight % prime for weight in INTEGER_WEIGHTS]
        if lifted != exact_reduced:
            raise AssertionError(f"shared integer lift mismatch mod {prime}")
        scaling_checks.append(
            {
                "prime": prime,
                "scale_times_modular_vector_equals_integer_weights_mod_prime": True,
            }
        )

    gate.SEARCH = search
    gate.THEOREM = theorem
    payloads = [records[index] for index in support]
    columns: dict[int, tuple[dict[Direction, int], tuple[int, ...]]] = {}
    context = mp.get_context("fork")
    with context.Pool(processes=workers, initializer=init_worker, maxtasksperchild=32) as pool:
        for index, hinges, vector in pool.imap_unordered(column_worker, payloads, chunksize=1):
            columns[index] = hinges, vector
    if set(columns) != set(support):
        raise AssertionError("exact replay support regeneration incomplete")

    residual: dict[Direction, int] = {}
    atom_vector = [0] * N
    for index, weight in zip(support, INTEGER_WEIGHTS, strict=True):
        hinges, vector = columns[index]
        add_hinges(residual, hinges, weight)
        for rank, value in enumerate(vector):
            atom_vector[rank] += weight * value
    dense_residual = [residual.get(direction, 0) for direction in universe]
    first_direction = min(residual) if residual else None

    target_scaled = [0] * (N - 1) + [INVARIANT_SCALE]
    correction_vector = [
        target_scaled[index] - atom_vector[index] for index in range(N)
    ]
    f_coefficients = exact_lower_f_decomposition(correction_vector)
    subset_vectors = [theorem.subset_max_vector(N, m) for m in range(1, N)]
    corrected = atom_vector[:]
    reconstructed_correction = [0] * N
    for coefficient, f_vector in zip(f_coefficients, subset_vectors, strict=True):
        for rank, value in enumerate(f_vector):
            contribution = coefficient * value
            reconstructed_correction[rank] += contribution
            corrected[rank] += contribution
    if reconstructed_correction != correction_vector or corrected != target_scaled:
        raise AssertionError("exact lower-F correction replay failed")

    invariant = theorem.dot(theorem.alternating_invariant(N), atom_vector)
    if invariant != INVARIANT_SCALE:
        raise AssertionError("exact integer lift invariant mismatch")

    modular_reduction_checks = []
    for modular_result in gate_report["modular_results"]:
        prime = int(modular_result["prime"])
        modular_dense = list(map(int, modular_result["complete_hinge_residual_vector_in_frozen_row_order"]))
        expected = [(INVARIANT_SCALE * value) % prime for value in modular_dense]
        observed = [value % prime for value in dense_residual]
        if expected != observed:
            raise AssertionError(f"exact residual disagrees with modular gate mod {prime}")
        modular_f = list(map(int, modular_result["F1_through_F10_correction_coefficients"]))
        if [value % prime for value in f_coefficients] != [
            (INVARIANT_SCALE * value) % prime for value in modular_f
        ]:
            raise AssertionError(f"exact F correction disagrees mod {prime}")
        modular_reduction_checks.append(
            {
                "prime": prime,
                "exact_hinge_residual_reduces_to_scaled_modular_residual": True,
                "exact_F_correction_reduces_to_scaled_modular_correction": True,
            }
        )

    mutation_index = support[0]
    mutant_residual = dict(residual)
    add_hinges(mutant_residual, columns[mutation_index][0], 1)
    mutant_atom_vector = [
        atom_vector[rank] + columns[mutation_index][1][rank] for rank in range(N)
    ]
    mutant_linear_residual = [
        mutant_atom_vector[rank] + reconstructed_correction[rank] - target_scaled[rank]
        for rank in range(N)
    ]
    target_mutant = target_scaled[:]
    target_mutant[-1] += 1
    target_mutant_residual = [
        corrected[rank] - target_mutant[rank] for rank in range(N)
    ]
    if not mutant_residual and not any(mutant_linear_residual):
        raise AssertionError("coefficient mutant was not rejected")
    if target_mutant_residual != [0] * (N - 1) + [-1]:
        raise AssertionError("target mutant control failed")

    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("script changed during exact replay")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "SHARED_SMALL_INTEGER_LIFT_REFUTED_BY_EXACT_NONZERO_HINGES",
        "script_sha256": script_hash_before,
        "bindings": {
            "complete_gate_script_sha256": EXPECTED_GATE_SCRIPT_HASH,
            "complete_gate_report_sha256": EXPECTED_GATE_REPORT_HASH,
            "row_universe_sha256": gate_report["frozen_row_universe"]["directions_sha256"],
            "support_descriptors_sha256": gate_report["frozen_support"]["descriptors_sha256"],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "integer_lift": {
            "invariant_scale": INVARIANT_SCALE,
            "support_indices": support,
            "weights": list(INTEGER_WEIGHTS),
            "weights_sha256": canonical_sha256(list(INTEGER_WEIGHTS)),
            "two_prime_scaling_checks": scaling_checks,
        },
        "exact_hinge_replay": {
            "tested_rows": len(universe),
            "nonzero_hinge_count": len(residual),
            "residual_vector_in_frozen_row_order": dense_residual,
            "residual_vector_sha256": canonical_sha256(dense_residual),
            "lex_first_residual": (
                {"direction": list(first_direction), "value": residual[first_direction]}
                if first_direction is not None
                else None
            ),
            "modular_reduction_checks": modular_reduction_checks,
        },
        "exact_linear_replay": {
            "padded_atom_vector": atom_vector,
            "alternating_invariant_pairing": invariant,
            "target_scaled_MAX11_vector": target_scaled,
            "target_minus_atom_correction_vector": correction_vector,
            "F1_through_F10_integer_coefficients": f_coefficients,
            "F_basis_reconstructed_correction_vector": reconstructed_correction,
            "corrected_vector": corrected,
            "all_eleven_coordinates_equal_scaled_MAX11": corrected == target_scaled,
        },
        "mutation_controls": {
            "coefficient_plus_one": {
                "mutated_zero_based_record_index": mutation_index,
                "rejected": bool(mutant_residual) or any(mutant_linear_residual),
                "nonzero_hinge_count": len(mutant_residual),
                "lex_first_hinge_residual": (
                    {
                        "direction": list(min(mutant_residual)),
                        "value": mutant_residual[min(mutant_residual)],
                    }
                    if mutant_residual
                    else None
                ),
                "linear_residual": mutant_linear_residual,
            },
            "target_plus_one": {
                "mutated_zero_based_coordinate": N - 1,
                "rejected": True,
                "linear_residual": target_mutant_residual,
            },
        },
        "claim_boundary": (
            "This exactly refutes the shared centered small-integer lift of the two modular "
            "selected-row vectors. It does not prove that no different rational vector on the "
            "same support exists, and it does not rule out other low-mass or unrestricted atoms."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
