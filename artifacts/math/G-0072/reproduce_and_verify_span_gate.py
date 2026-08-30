#!/usr/bin/env python3
"""Fail-closed same-implementation reproduction for the frozen G-0072 gate.

This wrapper deliberately does not claim clean-room independence.  It makes the
recorded reproduction command usable in a checkout, runs to a distinct path,
and refuses success unless the deterministic scientific payload, signed matrix,
target, and both registered rank gaps match the committed receipt.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCER = HERE / "asymmetric_loop_edge_span_gate.py"
EXPECTED_PRODUCER_SHA256 = (
    "59981f53d5c7ddbeef7cbd1d82b7b0df1289f692f593aca49aea2c925592521f"
)
EXPECTED_SCIENTIFIC_SHA256 = (
    "ca8a5090e331b5784fd9f5ffbf31a6c2826c319726a61cb3aa14f68544032495"
)
EXPECTED_MATRIX_SHA256 = (
    "ae76bf944e75f3be2e83789e4e9c50e8d627f6ab810afd3a32d1caece6b07480"
)
EXPECTED_TARGET = [0] * 10 + [39_916_800]
EXPECTED_RANKS = {
    1_000_003: (3_518, 3_519),
    1_000_033: (3_518, 3_519),
}


class ReplayError(RuntimeError):
    """The producer or deterministic reproduction contract drifted."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def reconstruct_scientific_payload(document: dict[str, object]) -> dict[str, object]:
    bindings = document.get("bindings")
    matrix = document.get("matrix")
    prime_results = document.get("prime_results")
    if not isinstance(bindings, dict) or not isinstance(matrix, dict):
        raise ReplayError("malformed bindings or matrix")
    if not isinstance(prime_results, list) or any(
        not isinstance(report, dict) for report in prime_results
    ):
        raise ReplayError("malformed prime results")
    return {
        "schema": document.get("schema"),
        "result": document.get("result"),
        "subject": {
            "bindings": bindings.get("bindings"),
            "script_sha256": bindings.get("script_sha256"),
            "base_count": bindings.get("base_count"),
            "raw_seed_manifest_sha256": bindings.get("raw_seed_manifest_sha256"),
            "orbits": bindings.get("orbits"),
            "semantic_smoke": bindings.get("semantic_smoke"),
            "countsketch": bindings.get("countsketch"),
        },
        "controls": document.get("controls"),
        "matrix": {key: value for key, value in matrix.items() if key != "seconds"},
        "target": document.get("target"),
        "prime_results": [
            {key: value for key, value in report.items() if key != "seconds"}
            for report in prime_results
        ],
        "modular_solutions": document.get("modular_solutions"),
        "interpretation_boundary": document.get("interpretation_boundary"),
    }


def verify(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise ReplayError("replay receipt is not a JSON object")
    scientific = reconstruct_scientific_payload(document)
    reconstructed = hashlib.sha256(canonical_bytes(scientific)).hexdigest()
    recorded = document.get("scientific_payload_sha256")
    if reconstructed != recorded or reconstructed != EXPECTED_SCIENTIFIC_SHA256:
        raise ReplayError(
            f"scientific payload drift: reconstructed={reconstructed} recorded={recorded}"
        )
    matrix = document["matrix"]
    if (
        matrix.get("signed_matrix_sha256") != EXPECTED_MATRIX_SHA256
        or matrix.get("rows") != 4_107
        or matrix.get("total_columns") != 3_756
    ):
        raise ReplayError("signed matrix digest or shape drift")
    target = document.get("target")
    if not isinstance(target, dict) or target.get("linear_coordinates") != EXPECTED_TARGET:
        raise ReplayError("target linear coordinates drift")
    if target.get("hinge_coordinates") != "all zero":
        raise ReplayError("target hinge coordinates drift")
    reports = document["prime_results"]
    observed_primes: set[int] = set()
    for report in reports:
        prime = int(report["prime"])
        observed_primes.add(prime)
        expected = EXPECTED_RANKS.get(prime)
        if expected is None:
            raise ReplayError(f"unexpected prime {prime}")
        if (
            (int(report["column_rank"]), int(report["augmented_rank"])) != expected
            or int(report["rank_gap"]) != 1
            or report["target_in_sketched_span"] is not False
        ):
            raise ReplayError(f"rank/membership drift at prime {prime}")
    if observed_primes != set(EXPECTED_RANKS):
        raise ReplayError("registered prime set drift")
    return {
        "status": "CONSISTENT",
        "output": str(path),
        "output_sha256": sha256_path(path),
        "scientific_payload_sha256": reconstructed,
        "signed_matrix_sha256": matrix["signed_matrix_sha256"],
        "rank_pairs": {
            str(report["prime"]): [report["column_rank"], report["augmented_rank"]]
            for report in reports
        },
        "independence_boundary": (
            "same frozen producer implementation; correlated reproducibility only, not clean-room replay"
        ),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "asymmetric_loop_edge_span_gate_replay_v1.json.gz",
    )
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.output.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output}")
    observed = sha256_path(PRODUCER)
    if observed != EXPECTED_PRODUCER_SHA256:
        raise ReplayError(f"producer drift: {observed}")
    command = [
        sys.executable,
        "-B",
        str(PRODUCER),
        "--run",
        "--workers",
        str(arguments.workers),
        "--buckets",
        "4096",
        "--seed",
        "max11-g0072-loop-edge-orbit-span-v1",
        "--primes",
        "1000003,1000033",
        "--minimum-available-gib",
        "12",
        "--expected-script-sha256",
        EXPECTED_PRODUCER_SHA256,
        "--output",
        str(arguments.output),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    print(json.dumps(verify(arguments.output), sort_keys=True))


if __name__ == "__main__":
    main()
