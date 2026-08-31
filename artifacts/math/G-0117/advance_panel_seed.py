#!/usr/bin/env python3
"""Convert a frozen G-0113 exact-Q panel member into a G-0117 v2 seed."""

from __future__ import annotations

import argparse
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


SCHEMA = "max11-g0113-panel-exact-postprocess-v1"
MEMBER_RESULT = "EXACT_Q_MEMBER_FINITE_PANEL"
OUTPUT_SCHEMA = "max11-g0117-global-replay-certificate-v2"
RECORDS = 163_740
INPUT_SHA256 = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8"
POSTPROCESSOR_SHA256 = "07f20ee167483aedc0c06f40650fd3edc671ef7fc5cf1e1050b1ad388ba3ec48"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
ROWS = ROOT / "artifacts/math/G-0111/dual_rows_v1.json"
POSTPROCESSOR = ROOT / "artifacts/math/G-0113/exact_panel_postprocess.py"
POSTPROCESSOR_PREREGISTRATION = (
    ROOT / "artifacts/math/G-0113/PANEL_EXACT_POSTPROCESS_PREREGISTRATION.md"
)
PYTHON = ROOT / ".venv/bin/python"
HEX64 = re.compile(r"[0-9a-f]{64}")
CANONICAL_RATIONAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:/[1-9][0-9]*)?")


class HandoffError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise HandoffError(message)


def exact_int(value: object, name: str) -> int:
    require(type(value) is int, f"{name} must be an integer")
    return int(value)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_canonical_fraction(value: object, name: str) -> Fraction:
    require(isinstance(value, str), f"{name} must be a string")
    require(CANONICAL_RATIONAL.fullmatch(value) is not None, f"{name} is malformed")
    try:
        parsed = Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise HandoffError(f"{name} is not a rational") from error
    require(str(parsed) == value, f"{name} is not canonical and reduced")
    return parsed


def require_hash(value: object, name: str) -> str:
    require(isinstance(value, str) and HEX64.fullmatch(value) is not None, f"{name} hash drift")
    return value


def convert(
    source: dict[str, Any],
    source_sha256: str,
    verification: dict[str, object],
) -> dict[str, object]:
    require(source.get("schema") == SCHEMA, "postprocess schema drift")
    require(exact_int(source.get("records"), "records") == RECORDS, "record census drift")
    bindings = source.get("bindings")
    require(isinstance(bindings, dict), "missing postprocess bindings")
    carried_bindings = {
        name: require_hash(bindings.get(name), f"binding {name}")
        for name in ("input", "rows", "report", "retained", "producer", "preregistration")
    }
    require(carried_bindings["input"] == INPUT_SHA256, "G-0113 input binding drift")
    require(
        carried_bindings["producer"] == POSTPROCESSOR_SHA256,
        "exact postprocessor binding drift",
    )
    require(source.get("exact_target_member") is True, "postprocess is not an exact member")
    exact_rank = exact_int(source.get("exact_union_rank"), "exact union rank")
    augmented_rank = exact_int(source.get("exact_augmented_rank"), "exact augmented rank")
    modular_rank = exact_int(source.get("agreed_modular_rank"), "agreed modular rank")
    retained_union = exact_int(source.get("retained_union_columns"), "retained union columns")
    require(0 < exact_rank <= 301, "exact rank outside panel dimension")
    require(exact_rank == augmented_rank, "exact rank/augmented-rank disagreement")
    require(modular_rank <= exact_rank <= retained_union, "rank bounds drift")
    require(
        source.get("exact_rank_exceeds_modular_rank") is (exact_rank > modular_rank),
        "exact/modular rank flag drift",
    )
    controls = source.get("planted_controls")
    require(
        isinstance(controls, dict)
        and controls.get("member") is True
        and controls.get("coefficient_plus_one_mutant_rejected") is True
        and controls.get("nonmember_separator") is True,
        "planted exact controls are not all green",
    )

    payload = source.get("payload")
    require(isinstance(payload, dict), "missing member payload")
    require(payload.get("result") == MEMBER_RESULT, "postprocess payload is not a member")
    require(payload.get("all_301_rows_replayed") is True, "301-row exact replay missing")
    require(
        payload.get("coefficient_plus_one_mutant_rejected") is True,
        "coefficient mutant was not rejected",
    )
    support = payload.get("support_sequences")
    raw_coefficients = payload.get("coefficients")
    coordinate_rows = payload.get("coordinate_rows")
    require(isinstance(support, list), "support is not a list")
    require(isinstance(raw_coefficients, list), "coefficients are not a list")
    require(isinstance(coordinate_rows, list), "coordinate rows are not a list")
    require(
        len(support) == len(raw_coefficients) == len(coordinate_rows) == exact_rank,
        "support/coefficient/rank length mismatch",
    )
    sequences = [exact_int(value, f"support[{index}]") for index, value in enumerate(support)]
    require(all(0 <= value < RECORDS for value in sequences), "support sequence outside family")
    require(sequences == sorted(set(sequences)), "support order/uniqueness drift")
    rows = [exact_int(value, f"coordinate_rows[{index}]") for index, value in enumerate(coordinate_rows)]
    require(len(set(rows)) == len(rows) and all(0 <= row < 301 for row in rows), "coordinate-row drift")
    coefficients = [
        parse_canonical_fraction(value, f"coefficient[{index}]")
        for index, value in enumerate(raw_coefficients)
    ]
    mutant_index = exact_int(payload.get("coefficient_mutant_index"), "coefficient mutant index")
    require(0 <= mutant_index < exact_rank, "coefficient mutant index outside support")
    require(coefficients[mutant_index] != 0, "registered coefficient mutant is zero")

    denominator_lcm = 1
    for coefficient in coefficients:
        denominator_lcm = math.lcm(denominator_lcm, coefficient.denominator)
    require(
        exact_int(payload.get("coefficient_denominator_lcm"), "coefficient denominator lcm")
        == denominator_lcm,
        "coefficient denominator LCM drift",
    )
    cleared = [
        coefficient.numerator * (denominator_lcm // coefficient.denominator)
        for coefficient in coefficients
    ]
    terms = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(sequences, cleared, strict=True)
        if coefficient != 0
    ]
    require(terms, "denominator-cleared certificate is empty")
    require_hash(source_sha256, "source postprocess")
    return {
        "schema": OUTPUT_SCHEMA,
        "claim_boundary": (
            "Denominator-cleared exact-Q finite-panel seed for complete global replay; "
            "not a global identity, family-completeness theorem, or MAX11 result."
        ),
        "source_exact_postprocess": {
            "sha256": source_sha256,
            "schema": SCHEMA,
            "result": MEMBER_RESULT,
            "bindings": carried_bindings,
            "verification": verification,
        },
        "target_scale": str(denominator_lcm),
        "terms": terms,
    }


def decision_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: item
        for key, item in value.items()
        if key not in {"wall_seconds", "maximum_rss_kib"}
    }


def verify_artifact_chain(
    source: dict[str, Any],
    postprocess_path: Path,
    report_path: Path,
    retained_path: Path,
) -> dict[str, object]:
    bindings = source.get("bindings")
    require(isinstance(bindings, dict), "missing postprocess bindings")
    actual = {
        "input": sha256_path(INPUT),
        "rows": sha256_path(ROWS),
        "report": sha256_path(report_path),
        "retained": sha256_path(retained_path),
        "producer": sha256_path(POSTPROCESSOR),
        "preregistration": sha256_path(POSTPROCESSOR_PREREGISTRATION),
    }
    for name, digest in actual.items():
        require(bindings.get(name) == digest, f"actual {name} artifact binding drift")
    require(actual["input"] == INPUT_SHA256, "actual frozen input hash drift")
    require(actual["producer"] == POSTPROCESSOR_SHA256, "actual postprocessor hash drift")
    require(PYTHON.is_file(), "frozen project Python executable missing")

    with tempfile.TemporaryDirectory() as temporary:
        replay_path = Path(temporary) / "recomputed_postprocess.json"
        completed = subprocess.run(
            [
                str(PYTHON),
                str(POSTPROCESSOR),
                str(report_path),
                str(retained_path),
                str(replay_path),
            ],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        require(
            completed.returncode == 0,
            f"exact postprocess clean replay failed: {completed.stderr[-1000:]}",
        )
        replay = json.loads(replay_path.read_text(encoding="utf-8"))
    require(isinstance(replay, dict), "recomputed postprocess root drift")
    require(
        decision_projection(source) == decision_projection(replay),
        "supplied postprocess differs from clean exact recomputation",
    )
    return {
        "decision_projection_recomputed": True,
        "postprocess_sha256": sha256_path(postprocess_path),
        "python_executable_sha256": sha256_path(PYTHON),
        "actual_artifact_bindings": actual,
    }


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def planted_source() -> dict[str, Any]:
    bindings = {
        "input": INPUT_SHA256,
        "rows": "1" * 64,
        "report": "2" * 64,
        "retained": "3" * 64,
        "producer": POSTPROCESSOR_SHA256,
        "preregistration": "4" * 64,
    }
    return {
        "schema": SCHEMA,
        "bindings": bindings,
        "records": RECORDS,
        "retained_union_columns": 3,
        "agreed_modular_rank": 3,
        "exact_union_rank": 3,
        "exact_augmented_rank": 3,
        "exact_target_member": True,
        "exact_rank_exceeds_modular_rank": False,
        "planted_controls": {
            "member": True,
            "coefficient_plus_one_mutant_rejected": True,
            "nonmember_separator": True,
        },
        "payload": {
            "result": MEMBER_RESULT,
            "support_sequences": [5, 9, 12],
            "coordinate_rows": [0, 7, 300],
            "coefficients": ["1/2", "-3/7", "0"],
            "coefficient_denominator_lcm": 14,
            "all_301_rows_replayed": True,
            "coefficient_mutant_index": 0,
            "coefficient_plus_one_mutant_rejected": True,
        },
    }


def expect_rejection(source: dict[str, Any], label: str) -> None:
    try:
        convert(source, "a" * 64, {"decision_projection_recomputed": True})
    except HandoffError:
        return
    raise HandoffError(f"planted {label} mutant was accepted")


def self_test() -> None:
    source = planted_source()
    converted = convert(source, "a" * 64, {"decision_projection_recomputed": True})
    require(converted["target_scale"] == "14", "planted target scale mismatch")
    require(
        converted["terms"]
        == [
            {"sequence": 5, "coefficient": "7"},
            {"sequence": 9, "coefficient": "-6"},
        ],
        "planted denominator clearing mismatch",
    )
    mutants: list[tuple[str, dict[str, Any]]] = []
    nonmember = deepcopy(source)
    nonmember["exact_target_member"] = False
    mutants.append(("nonmember", nonmember))
    duplicate = deepcopy(source)
    duplicate["payload"]["support_sequences"] = [5, 5, 12]
    mutants.append(("duplicate sequence", duplicate))
    noncanonical = deepcopy(source)
    noncanonical["payload"]["coefficients"][0] = "2/4"
    mutants.append(("noncanonical rational", noncanonical))
    rank_mismatch = deepcopy(source)
    rank_mismatch["exact_union_rank"] = 2
    rank_mismatch["exact_augmented_rank"] = 2
    rank_mismatch["agreed_modular_rank"] = 2
    rank_mismatch["retained_union_columns"] = 2
    mutants.append(("rank mismatch", rank_mismatch))
    missing_mutant = deepcopy(source)
    missing_mutant["payload"]["coefficient_plus_one_mutant_rejected"] = False
    mutants.append(("missing coefficient mutant", missing_mutant))
    binding_drift = deepcopy(source)
    binding_drift["bindings"]["producer"] = "f" * 64
    mutants.append(("binding drift", binding_drift))
    for label, mutant in mutants:
        expect_rejection(mutant, label)

    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "certificate.json"
        write_exclusive(output, converted)
        try:
            write_exclusive(output, converted)
        except FileExistsError:
            pass
        else:
            raise HandoffError("exclusive output control failed")
    print(json.dumps({"result": "PASS", "mutants_rejected": len(mutants) + 1}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("postprocess", nargs="?", type=Path)
    parser.add_argument("report", nargs="?", type=Path)
    parser.add_argument("retained", nargs="?", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        require(
            args.postprocess is None
            and args.report is None
            and args.retained is None
            and args.output is None,
            "self-test takes no paths",
        )
        self_test()
        return
    require(
        args.postprocess is not None
        and args.report is not None
        and args.retained is not None
        and args.output is not None,
        "postprocess, report, retained, and output required",
    )
    source = json.loads(args.postprocess.read_text(encoding="utf-8"))
    require(isinstance(source, dict), "postprocess root must be an object")
    verification = verify_artifact_chain(
        source,
        args.postprocess,
        args.report,
        args.retained,
    )
    converted = convert(source, sha256_path(args.postprocess), verification)
    write_exclusive(args.output, converted)
    print(json.dumps(converted, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
