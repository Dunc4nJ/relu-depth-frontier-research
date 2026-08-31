#!/usr/bin/env python3
"""Independent exact replay of the serialized G-0115 transport rank witnesses."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Sequence

from flint import fmpq_mat, fmpz_mat, nmod_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
REPORT = HERE / "transport_functional_rank_gate_v1.json"
KERNEL = HERE / "semantic_repair.py"
EXPECTED = {
    REPORT: "5b84d5ba45094c5603c127b0a632978de6e05e7684911d167b5246e16af28c9b",
    KERNEL: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
}
CAP = 64
WITNESS = 65


class WitnessReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WitnessReplayError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_kernel():
    require(sha256(KERNEL) == EXPECTED[KERNEL], "kernel drift")
    spec = importlib.util.spec_from_file_location("g0115_rank_replay_kernel", KERNEL)
    require(spec is not None and spec.loader is not None, "cannot load kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def atomic_json(path: Path, value: object) -> None:
    require(not path.exists(), f"output exists: {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def replay_one(name: str, witness: dict[str, object], universe: Sequence[tuple[int, ...]]) -> dict[str, object]:
    require(witness.get("convention") == name, f"{name}: convention drift")
    require(witness.get("parameter_cap") == CAP and witness.get("cap_exceeded") is True, f"{name}: cap drift")
    signatures = witness.get("witness_signatures")
    indices = witness.get("witness_hinge_indices")
    directions = witness.get("witness_hinge_directions")
    raw_minor = witness.get("witness_minor")
    require(
        isinstance(signatures, list)
        and isinstance(indices, list)
        and isinstance(directions, list)
        and isinstance(raw_minor, list)
        and len(signatures) == len(indices) == len(directions) == len(raw_minor) == WITNESS,
        f"{name}: witness dimension drift",
    )
    require(len(set(map(str, signatures))) == WITNESS and len(set(map(int, indices))) == WITNESS, f"{name}: duplicate witness descriptors")
    require(
        [list(universe[int(index)]) for index in indices] == directions,
        f"{name}: hinge direction/index mismatch",
    )
    minor: list[list[Fraction]] = []
    digest = hashlib.sha256()
    for raw_row in raw_minor:
        require(isinstance(raw_row, list) and len(raw_row) == WITNESS, f"{name}: row width drift")
        row = [Fraction(str(value)) for value in raw_row]
        minor.append(row)
        digest.update(canonical([str(value) for value in row]))
    require(digest.hexdigest() == witness.get("witness_minor_sha256"), f"{name}: minor digest drift")
    exact_rank = int(fmpq_mat([[str(value) for value in row] for row in minor]).rank())
    require(exact_rank == WITNESS, f"{name}: exact Q rank drift")
    prime = int(witness["modular_discovery_prime"])
    modular_rows = []
    for row in minor:
        modular_rows.append([
            value.numerator % prime * pow(value.denominator, prime - 2, prime) % prime
            for value in row
        ])
    modular_rank = int(nmod_mat(modular_rows, prime).rank())
    require(modular_rank == WITNESS, f"{name}: modular rank drift")
    integer_minor = all(value.denominator == 1 for row in minor for value in row)
    require(integer_minor == bool(witness["integer_minor"]), f"{name}: integer-minor flag drift")
    integer_rank = None
    if integer_minor:
        integer_rank = int(fmpz_mat([[value.numerator for value in row] for row in minor]).rank())
        require(integer_rank == WITNESS, f"{name}: integer rank drift")
    return {
        "exact_Q_rank": exact_rank,
        "modular_rank": modular_rank,
        "integer_rank": integer_rank,
        "minor_sha256": digest.hexdigest(),
        "cap": CAP,
        "cap_exceeded": exact_rank > CAP,
    }


def run(output: Path) -> dict[str, object]:
    script_hash = sha256(SCRIPT)
    bindings = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED}
    expected = {str(path.relative_to(ROOT)): value for path, value in EXPECTED.items()}
    require(bindings == expected, f"input drift: {bindings}")
    document = json.loads(REPORT.read_text(encoding="utf-8"))
    require(document.get("result") == "EXACT_PARAMETER_CAP_EXCEEDED", "producer result drift")
    kernel = load_kernel()
    universe = kernel.direction_universe()
    require(len(universe) == 20_685, "direction universe drift")
    witnesses = document.get("rank_witnesses")
    require(isinstance(witnesses, dict) and set(witnesses) == {"raw_sum", "full_atom_average"}, "witness convention drift")
    replay = {name: replay_one(name, witness, universe) for name, witness in sorted(witnesses.items())}
    require(all(item["cap_exceeded"] for item in replay.values()), "independent cap replay failed")
    result = {
        "schema": "max11-g0115-independent-transport-rank-witness-replay-v1",
        "result": "PASS",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "replay": replay,
        "independence_boundary": (
            "Replayed the two serialized 65x65 rational minors and their bound hinge indices "
            "without importing the rank-gate producer or loading its 1.8 GB semantic matrix. "
            "This independently certifies the stated minor ranks; the producer report remains "
            "the binding from those minors to the enumerated functional families."
        ),
        "claim_boundary": (
            "Exact replay of rank-65 witnesses above the frozen cap64 only; not a complete "
            "family rank, functional nonmembership result, other-operator obstruction, or MAX11 decision."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "script changed during replay")
    atomic_json(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output.resolve())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
