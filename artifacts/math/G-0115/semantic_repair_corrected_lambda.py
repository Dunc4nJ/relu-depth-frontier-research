#!/usr/bin/env python3
"""Run the preregistered G-0115 search with rational-safe Lambda semantics."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
V3_PATH = HERE / "semantic_repair_ffpack_cegis_v3.py"
PREREGISTRATION = HERE / "CORRECTED_RATIONAL_LAMBDA_PREREGISTRATION.md"
MALFORMED_CHECKPOINT = HERE / "semantic_repair_exact_checkpoint_v3.json"
EXPECTED = {
    V3_PATH: "803b204cc57ffcc896000c532e64dc07f014cdec44678be6b0a4f6335e780eb1",
    PREREGISTRATION: "56816ae587396e5ced5cb076a2b87b9b74effe5fdde10f579a0ef8aa5a637063",
    MALFORMED_CHECKPOINT: "948f107038dc9b376340db575fc8db0809f01e4bd81835ea0104ccb740cb19a1",
}
TARGET_CONTROLS: dict[str, object] = {}


class CorrectedLambdaError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CorrectedLambdaError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w") as destination:
        json.dump(payload, destination, indent=2, sort_keys=True)
        destination.write("\n")


def load_v3():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"corrected-Lambda binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_bound_native_v3", V3_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v3 accelerator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def rational_lambda(linear: Sequence[object]) -> Fraction:
    n = len(linear)
    weights = [(-1) ** (n - rank) * math.comb(n - 1, rank - 1) for rank in range(1, n + 1)]
    return sum(
        (Fraction(weight) * Fraction(value) for weight, value in zip(weights, linear, strict=True)),
        Fraction(),
    )


def complete_integer_cache_control(matrix_path: Path, linear_path: Path) -> dict[str, object]:
    matrix = np.load(matrix_path, mmap_mode="r", allow_pickle=False)
    linear = np.load(linear_path, mmap_mode="r", allow_pickle=False)
    require(matrix.shape[0] == linear.shape[0] and linear.shape[1] == 9, "cache shape drift")
    weights = np.asarray(
        [(-1) ** (9 - rank) * math.comb(8, rank - 1) for rank in range(1, 10)],
        dtype=np.int64,
    )
    observed = np.asarray(linear, dtype=np.int64) @ weights
    expected = np.asarray(matrix[:, -1], dtype=np.int64)
    mismatch = np.flatnonzero(observed != expected)
    require(len(mismatch) == 0, "integral cache Lambda mismatch")
    return {
        "columns_checked": int(matrix.shape[0]),
        "mismatches": 0,
        "weights_int64_sha256": hashlib.sha256(weights.tobytes()).hexdigest(),
        "observed_lambda_int64_sha256": hashlib.sha256(observed.tobytes()).hexdigest(),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--linear", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--exact-checkpoint", type=Path, required=True)
    args = parser.parse_args(argv)
    outputs = (args.report, args.certificate, args.exact_checkpoint)
    require(all(not path.exists() for path in outputs), "outputs must be unused")
    script_hash = sha256(SCRIPT)
    cache_control = complete_integer_cache_control(args.matrix.resolve(), args.linear.resolve())
    v3 = load_v3()
    v2 = v3.load_v2()
    cegis = v2.load_cegis()
    v3.EXACT_CHECKPOINT_PATH = args.exact_checkpoint.resolve()
    original_load_bound_modules = cegis.load_bound_modules

    def corrected_bound_modules():
        bindings, kernel, solver = original_load_bound_modules()
        kernel.lambda_value = rational_lambda
        original_target_system = solver.target_system

        def checked_target_system(kernel_arg, dp, retained, missing):
            target = original_target_system(kernel_arg, dp, retained, missing)
            retained_lift_linear = [Fraction() for _ in range(kernel_arg.N)]
            retained_lift_hinges: dict[tuple[int, ...], Fraction] = {}
            for term in target["retained_lift_records"]:
                kernel_arg.add_scaled(
                    retained_lift_linear,
                    retained_lift_hinges,
                    kernel_arg.normal_form(dp, kernel_arg.parse_pair(term["pair"])),
                    Fraction(term["coefficient"]),
                )
            retained_lift_lambda = rational_lambda(retained_lift_linear)
            require(
                retained_lift_lambda == target["retained_public_lambda"],
                "corrected retained lift/public Lambda disagreement",
            )
            require(
                retained_lift_lambda + target["target_lambda"] == 1,
                "corrected target does not complete Lambda to one",
            )
            malformed = json.loads(MALFORMED_CHECKPOINT.read_text(encoding="utf-8"))
            malformed_coefficients = [Fraction(value) for value in malformed["coefficients"]]
            malformed_support = list(map(int, malformed["basis_columns"]))
            linear_cache = np.load(args.linear.resolve(), mmap_mode="r", allow_pickle=False)
            malformed_repair_linear = [
                sum(
                    coefficient * int(linear_cache[column, coordinate])
                    for column, coefficient in zip(
                        malformed_support, malformed_coefficients, strict=True
                    )
                )
                / 680400
                for coordinate in range(kernel_arg.N)
            ]
            malformed_combined_lambda = rational_lambda(
                [
                    retained_lift_linear[index] + malformed_repair_linear[index]
                    for index in range(kernel_arg.N)
                ]
            )
            require(malformed_combined_lambda != 1, "malformed target negative control escaped")
            TARGET_CONTROLS.update(
                {
                    "corrected_missing_lambda": str(target["target_lambda"]),
                    "corrected_retained_public_lambda": str(target["retained_public_lambda"]),
                    "corrected_retained_lift_lambda": str(retained_lift_lambda),
                    "corrected_completion_lambda": str(
                        retained_lift_lambda + target["target_lambda"]
                    ),
                    "malformed_missing_lambda": "-28",
                    "malformed_combined_lambda": str(malformed_combined_lambda),
                    "malformed_checkpoint_rejected": True,
                }
            )
            return target

        solver.target_system = checked_target_system
        solver.pivot_coordinates = lambda matrix, columns, prime: v3.native_pivot_coordinates(
            matrix, columns, prime, v2
        )
        solver.exact_minor_solution = lambda matrix, target, columns, rows: (
            v3.determinant_free_exact_minor_solution(
                matrix, target, columns, rows, solver
            )
        )
        return bindings, kernel, solver

    cegis.load_bound_modules = corrected_bound_modules
    cegis.projection_rref = v2.native_projection_rref
    cegis.modular_full_replay = v2.native_modular_full_replay
    with tempfile.TemporaryDirectory(prefix="g0115-corrected-report-") as directory_raw:
        temporary_report = Path(directory_raw) / "inner-report.json"
        report = cegis.solve_cache(
            args.matrix.resolve(),
            args.linear.resolve(),
            args.metadata.resolve(),
            temporary_report,
            args.certificate.resolve(),
        )
    require(sha256(SCRIPT) == script_hash, "corrected-Lambda runner changed during solve")
    report["corrected_rational_lambda"] = {
        "runner_sha256": script_hash,
        "preregistration_sha256": EXPECTED[PREREGISTRATION],
        "v3_accelerator_sha256": EXPECTED[V3_PATH],
        "integer_cache_control": cache_control,
        "target_controls": TARGET_CONTROLS,
        "complete_replay_calls": v2.REPLAY_RECORDS,
        "pivot_calls": v3.PIVOT_RECORDS,
        "exact_calls": v3.EXACT_RECORDS,
    }
    write_exclusive(args.report, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
