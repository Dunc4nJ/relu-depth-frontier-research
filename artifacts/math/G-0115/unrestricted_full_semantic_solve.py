#!/usr/bin/env python3
"""Solve the preregistered unrestricted 22,666-class full MAX9 system."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
V3_PATH = HERE / "semantic_repair_ffpack_cegis_v3.py"
PREREGISTRATION = HERE / "UNRESTRICTED_FULL_SEMANTIC_PREREGISTRATION.md"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    V3_PATH: "803b204cc57ffcc896000c532e64dc07f014cdec44678be6b0a4f6335e780eb1",
    PREREGISTRATION: "61e39e655912e0f967ae76c90676012c06d506305d64267533ebf73ee50ec017",
}
HINGES = 20_685
LINEAR = 9
COORDINATES = HINGES + LINEAR
COLUMNS = 22_666
RETAINED = 328
PREFIXES = (328, 1024, 2048, 4096, 8192, 16384, 22666)
PRIMES = (1_000_003, 1_000_033, 1_000_037)
INITIAL_HINGES = 247
RESIDUAL_BATCH = 256


class UnrestrictedSolveError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise UnrestrictedSolveError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_sha(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast("B")).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(payload))
        destination.flush()
        os.fsync(destination.fileno())


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bind_modules():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"unrestricted solver binding drift: {observed}")
    kernel = load_module("g0115_unrestricted_solve_kernel", KERNEL_PATH)
    kernel.bind_inputs()
    v3 = load_module("g0115_unrestricted_solve_v3", V3_PATH)
    v2 = v3.load_v2()
    return kernel, v3, v2


def evenly_spaced(values: Sequence[int] | np.ndarray, limit: int) -> list[int]:
    checked = list(map(int, values))
    if len(checked) <= limit:
        return checked
    require(limit >= 2, "sampling limit too small")
    return [checked[index * (len(checked) - 1) // (limit - 1)] for index in range(limit)]


def exact_full_replay(
    matrix: np.ndarray,
    support: Sequence[int],
    coefficients: Sequence[Fraction],
    target: np.ndarray,
) -> tuple[list[int], int]:
    denominator = 1
    for coefficient in coefficients:
        denominator = math.lcm(denominator, coefficient.denominator)
    integer_coefficients = [
        coefficient.numerator * (denominator // coefficient.denominator)
        for coefficient in coefficients
    ]
    observed: dict[int, int] = {}
    for column, coefficient in zip(support, integer_coefficients, strict=True):
        if not coefficient:
            continue
        row = matrix[column]
        for coordinate in map(int, np.flatnonzero(row)):
            observed[coordinate] = observed.get(coordinate, 0) + coefficient * int(row[coordinate])
    residual = [
        coordinate
        for coordinate in range(matrix.shape[1])
        if observed.get(coordinate, 0) != int(target[coordinate]) * denominator
    ]
    return residual, denominator


def validate_matrix(matrix_path: Path, metadata_path: Path):
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(
        metadata.get("schema") == "g0115-unrestricted-full-semantic-matrix-v1"
        and metadata.get("result") == "PASS",
        "matrix metadata gate failed",
    )
    require(metadata["matrix"]["file_sha256"] == sha256(matrix_path), "matrix file hash drift")
    matrix = np.load(matrix_path, mmap_mode="r", allow_pickle=False)
    require(
        matrix.shape == (COLUMNS, COORDINATES) and matrix.dtype == np.dtype("<i4"),
        "matrix shape/dtype drift",
    )
    return metadata, matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    args = parser.parse_args()
    require(not args.report.exists() and not args.certificate.exists(), "outputs must be unused")
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    kernel, v3, v2 = bind_modules()
    matrix_metadata, matrix = validate_matrix(args.matrix.resolve(), args.metadata.resolve())
    retained, repair, _missing = kernel.load_map_and_targets()
    records = retained + repair
    require(len(records) == COLUMNS and len(retained) == RETAINED, "column record census drift")
    order = [
        {"group": "retained", "signed_certificate_sha256": record["signed_certificate_sha256"]}
        for record in retained
    ] + [
        {"group": "repair", "signed_certificate_sha256": record["signed_certificate_sha256"]}
        for record in repair
    ]
    require(
        canonical_sha(order) == matrix_metadata["column_order"]["canonical_sha256"],
        "matrix/record column order drift",
    )
    target = np.zeros(COORDINATES, dtype=np.int64)
    target[-1] = 1
    require(raw_sha(target) == matrix_metadata["target"]["int64_sha256"], "target hash drift")
    selected = set(evenly_spaced(range(HINGES), INITIAL_HINGES))
    selected.update(range(HINGES, COORDINATES))
    require(len(selected) == INITIAL_HINGES + LINEAR, "initial row census drift")
    initial_rows = sorted(selected)
    prefix_records = []
    chosen = None

    for prefix in PREFIXES:
        prefix_record: dict[str, object] = {"prefix": prefix, "iterations": []}
        for iteration in range(1, COORDINATES + 1):
            selected_rows = sorted(selected)
            projection = np.ascontiguousarray(matrix[:prefix, selected_rows].T, dtype=np.int64)
            projection_target = np.ascontiguousarray(target[selected_rows], dtype=np.int64)
            modular_records = []
            guide = None
            guide_support = None
            guide_coefficients = None
            for prime in PRIMES:
                record, support, coefficients = v2.native_projection_rref(
                    projection, projection_target, prime, None
                )
                modular_records.append(record)
                if record["target_member"] and guide is None:
                    guide = prime
                    guide_support = support
                    guide_coefficients = coefficients
                if prime == PRIMES[0] and record["target_member"]:
                    break
            iteration_record: dict[str, object] = {
                "iteration": iteration,
                "selected_rows": len(selected_rows),
                "selected_rows_int64_sha256": raw_sha(np.asarray(selected_rows, dtype=np.int64)),
                "projection": modular_records,
            }
            prefix_record["iterations"].append(iteration_record)
            if guide is None:
                prefix_record["outcome"] = "MODULAR_PROJECTED_NONMEMBER"
                print(
                    f"G0115_UNRESTRICTED prefix={prefix} rows={len(selected_rows)} nonmember_all_primes",
                    flush=True,
                )
                break
            require(guide_support is not None and guide_coefficients is not None, "missing guide")
            residual = v2.native_modular_full_replay(
                matrix, guide_support, guide_coefficients, target, guide
            )
            iteration_record["guide_prime"] = guide
            iteration_record["guide_support"] = len(guide_support)
            iteration_record["complete_modular_residual_nonzeros"] = len(residual)
            if len(residual):
                new_rows = [row for row in map(int, residual) if row not in selected]
                require(new_rows, "modular residual contains no unseen row")
                added = evenly_spaced(new_rows, RESIDUAL_BATCH)
                selected.update(added)
                iteration_record["added_rows"] = len(added)
                iteration_record["added_rows_int64_sha256"] = raw_sha(np.asarray(added, dtype=np.int64))
                print(
                    f"G0115_UNRESTRICTED prefix={prefix} rows={len(selected_rows)} "
                    f"rank={len(guide_support)} residual={len(residual)} add={len(added)}",
                    flush=True,
                )
                continue

            pivot_rows = v3.native_pivot_coordinates(projection, guide_support, guide, v2)
            v3.EXACT_CHECKPOINT_PATH = None
            _bindings, _kernel_unused, exact_solver = v2.load_cegis().load_bound_modules()
            exact_coefficients = v3.determinant_free_exact_minor_solution(
                projection, projection_target, guide_support, pivot_rows, exact_solver
            )
            exact_residual, denominator = exact_full_replay(
                matrix, guide_support, exact_coefficients, target
            )
            iteration_record["exact_attempt"] = {
                "basis_columns": len(guide_support),
                "pivot_rows": len(pivot_rows),
                "solution_common_denominator_digits": len(str(denominator)),
                "complete_exact_residual_nonzeros": len(exact_residual),
            }
            if exact_residual:
                new_rows = [row for row in exact_residual if row not in selected]
                require(new_rows, "exact residual contains no unseen row")
                added = evenly_spaced(new_rows, RESIDUAL_BATCH)
                selected.update(added)
                iteration_record["exact_attempt"]["added_rows"] = len(added)
                print(
                    f"G0115_UNRESTRICTED_EXACT_MISS prefix={prefix} residual={len(exact_residual)}",
                    flush=True,
                )
                continue
            nonzero = [
                (column, coefficient)
                for column, coefficient in zip(guide_support, exact_coefficients, strict=True)
                if coefficient
            ]
            require(nonzero, "exact solution is zero")
            mutation_column = nonzero[0][0]
            mutation_failure_coordinates = int(np.count_nonzero(matrix[mutation_column]))
            require(mutation_failure_coordinates > 0, "coefficient mutation escaped")
            positive_prime_controls = []
            for prime in PRIMES:
                record, support, coefficients = v2.native_projection_rref(
                    projection, projection_target, prime, None
                )
                require(record["target_member"], f"positive vanished modulo {prime}")
                replay_residual = v2.native_modular_full_replay(
                    matrix, support, coefficients, target, prime
                )
                record["complete_replay_residual_nonzeros"] = len(replay_residual)
                require(len(replay_residual) == 0, f"positive modular replay failed at {prime}")
                positive_prime_controls.append(record)
            chosen = {
                "prefix": prefix,
                "selected_rows": selected_rows,
                "support": guide_support,
                "coefficients": exact_coefficients,
                "nonzero": nonzero,
                "guide_prime": guide,
                "positive_prime_controls": positive_prime_controls,
                "mutation_failure_coordinates": mutation_failure_coordinates,
                "denominator": denominator,
            }
            prefix_record["outcome"] = "EXACT_MEMBER"
            break
        prefix_records.append(prefix_record)
        if chosen is not None:
            break

    result = "EXACT_MEMBER" if chosen is not None else "MODULAR_FULL_FAMILY_GATE_ONLY"
    exact_summary = None
    if chosen is not None:
        terms = []
        for column, coefficient in chosen["nonzero"]:
            record = records[column]
            terms.append(
                {
                    "coefficient": str(coefficient),
                    "pair": record["representative"]["pair"],
                    "column_index": column,
                    "group": "retained" if column < RETAINED else "repair",
                    "representative_sequence": int(record["sequence"]),
                    "signed_certificate_sha256": record["signed_certificate_sha256"],
                }
            )
        certificate = {
            "schema": "g0115-unrestricted-degree4-full-max9-certificate-v1",
            "n": 9,
            "degree": 4,
            "terms": terms,
            "semantics": {
                "complete_hinge_direction_count": HINGES,
                "hinge_residual_nonzeros": 0,
                "linear": ["0"] * 8 + ["1"],
            },
            "bindings": {
                "matrix_sha256": matrix_metadata["matrix"]["file_sha256"],
                "column_order_sha256": matrix_metadata["column_order"]["canonical_sha256"],
                "solver_sha256_at_start": script_hash,
                "preregistration_sha256": EXPECTED[PREREGISTRATION],
            },
            "claim_boundary": (
                "Exact degree-four MAX9 identity in the unrestricted 22,666-class G-0115 lift "
                "span; not a coefficient transport law, MAX10/MAX11 result, or induction theorem."
            ),
        }
        write_exclusive(args.certificate.resolve(), certificate)
        exact_summary = {
            "positive_prefix": chosen["prefix"],
            "selected_rows": len(chosen["selected_rows"]),
            "basis_size": len(chosen["support"]),
            "nonzero_coefficients": len(chosen["nonzero"]),
            "solution_common_denominator_digits": len(str(chosen["denominator"])),
            "complete_coordinate_residual_nonzeros": 0,
            "mutation_failure_coordinates": chosen["mutation_failure_coordinates"],
            "positive_prime_controls": chosen["positive_prime_controls"],
            "certificate_path": str(args.certificate.resolve().relative_to(ROOT)),
            "certificate_sha256": sha256(args.certificate.resolve()),
            "certificate_canonical_sha256": canonical_sha(certificate),
        }

    report = {
        "schema": "g0115-unrestricted-full-semantic-cegis-v1",
        "result": result,
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()
        }
        | {
            "script_sha256_at_start": script_hash,
            "matrix_metadata_sha256": sha256(args.metadata.resolve()),
            "matrix_sha256": matrix_metadata["matrix"]["file_sha256"],
        },
        "target": {
            "coordinates": COORDINATES,
            "hinges": HINGES,
            "linear": [0] * 8 + [1],
            "int64_sha256": raw_sha(target),
        },
        "search": {
            "prefixes": list(PREFIXES),
            "initial_rows": len(initial_rows),
            "initial_rows_int64_sha256": raw_sha(np.asarray(initial_rows, dtype=np.int64)),
            "residual_batch": RESIDUAL_BATCH,
            "records": prefix_records,
        },
        "exact": exact_summary,
        "native_acceleration": {
            "v2_wrapper_sha256": v3.EXPECTED_V2,
            "v3_wrapper_sha256": EXPECTED[V3_PATH],
            "complete_replay_calls": v2.REPLAY_RECORDS,
            "pivot_calls": v3.PIVOT_RECORDS,
            "exact_calls": v3.EXACT_RECORDS,
        },
        "wall_seconds": time.perf_counter() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claim_boundary": (
            "An exact positive is a degree-four MAX9 identity in this complete lift-class span "
            "only. A modular gate is not a Q obstruction. Neither implies transport or induction."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "unrestricted solver changed during execution")
    write_exclusive(args.report.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0 if result == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
