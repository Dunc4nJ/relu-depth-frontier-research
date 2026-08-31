#!/usr/bin/env python3
"""Independent certificate-only exact replay of the corrected G-0115 repair."""

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
import time
from typing import Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
CERTIFICATE = HERE / "semantic_repair_corrected_certificate_v1.json"
PREREGISTRATION = HERE / "CORRECTED_RATIONAL_LAMBDA_PREREGISTRATION.md"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    CERTIFICATE: "ec0120da03f777a8e2497bea23809d96752b4389d217099d1e037cb264a873ab",
    PREREGISTRATION: "56816ae587396e5ced5cb076a2b87b9b74effe5fdde10f579a0ef8aa5a637063",
}


class IndependentReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IndependentReplayError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(payload))
        destination.flush()
        os.fsync(destination.fileno())


def load_kernel():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"independent replay binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_independent_kernel", KERNEL_PATH)
    require(spec is not None and spec.loader is not None, "cannot load semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.bind_inputs()
    return module


def rational_lambda(linear: Sequence[Fraction]) -> Fraction:
    n = len(linear)
    return sum(
        (
            Fraction((-1) ** (n - rank) * math.comb(n - 1, rank - 1)) * value
            for rank, value in enumerate(linear, start=1)
        ),
        Fraction(),
    )


def add_semantic(
    linear: list[Fraction],
    hinges: dict[tuple[int, ...], Fraction],
    semantic,
    coefficient: Fraction,
) -> None:
    for coordinate, value in enumerate(semantic[0]):
        linear[coordinate] += coefficient * int(value)
    for direction, value in semantic[1].items():
        updated = hinges.get(direction, Fraction()) + coefficient * int(value)
        if updated:
            hinges[direction] = updated
        else:
            hinges.pop(direction, None)


def replay_terms(kernel, dp, terms: list[dict[str, object]], label: str):
    linear = [Fraction() for _ in range(kernel.N)]
    hinges: dict[tuple[int, ...], Fraction] = {}
    semantics = []
    for position, term in enumerate(terms, start=1):
        pair = kernel.parse_pair(term["pair"])
        semantic = kernel.normal_form(dp, pair)
        coefficient = Fraction(term["coefficient"])
        add_semantic(linear, hinges, semantic, coefficient)
        semantics.append((coefficient, semantic))
        if position % 64 == 0 or position == len(terms):
            print(f"G0115_INDEPENDENT_REPLAY {label} {position}/{len(terms)}", flush=True)
    return linear, hinges, semantics


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    kernel = load_kernel()
    dp = kernel.load_dp()
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    require(
        document.get("schema") == "max11-g0115-max9-coefficient-frozen-residual-certificate-v1"
        and document.get("n") == kernel.N,
        "certificate schema drift",
    )
    fixed_terms = document["retained_fixed_terms"]
    repair_terms = document["repair_terms"]
    missing_terms = document["missing_public_terms"]
    require(
        len(fixed_terms) == kernel.EXPECTED_RETAINED
        and len(repair_terms) == 752
        and len(missing_terms) == kernel.EXPECTED_MISSING,
        "certificate term census drift",
    )

    fixed_linear, fixed_hinges, fixed_semantics = replay_terms(
        kernel, dp, fixed_terms, "fixed"
    )
    repair_linear, repair_hinges, repair_semantics = replay_terms(
        kernel, dp, repair_terms, "repair"
    )
    missing_linear, missing_hinges, _missing_semantics = replay_terms(
        kernel, dp, missing_terms, "missing"
    )
    combined_linear = [
        fixed_linear[index] + repair_linear[index] for index in range(kernel.N)
    ]
    combined_hinges = dict(fixed_hinges)
    for direction, coefficient in repair_hinges.items():
        updated = combined_hinges.get(direction, Fraction()) + coefficient
        if updated:
            combined_hinges[direction] = updated
        else:
            combined_hinges.pop(direction, None)

    expected_linear = [Fraction(value) for value in document["semantics"]["retained_plus_repair_linear"]]
    require(not combined_hinges, "serialized retained-plus-repair terms have nonzero hinges")
    require(combined_linear == expected_linear, "serialized combined linear vector drift")
    require(rational_lambda(combined_linear) == 1, "serialized combined rational Lambda drift")
    require(repair_hinges == missing_hinges, "serialized repair/missing hinge mismatch")
    require(
        rational_lambda(repair_linear) == rational_lambda(missing_linear),
        "serialized repair/missing Lambda mismatch",
    )
    require(
        rational_lambda(fixed_linear) + rational_lambda(missing_linear) == 1,
        "serialized fixed-plus-missing public Lambda drift",
    )

    mutation_coefficient, mutation_semantic = next(
        (coefficient, semantic)
        for coefficient, semantic in repair_semantics
        if coefficient and (semantic[1] or rational_lambda(list(map(Fraction, semantic[0]))))
    )
    mutated_linear = combined_linear.copy()
    mutated_hinges = dict(combined_hinges)
    add_semantic(mutated_linear, mutated_hinges, mutation_semantic, Fraction(1))
    mutation_rejected = bool(mutated_hinges) or rational_lambda(mutated_linear) != 1
    require(mutation_rejected, "serialized coefficient mutation escaped replay")

    universe = set(kernel.direction_universe())
    observed_directions = set(fixed_hinges) | set(repair_hinges) | set(missing_hinges)
    require(observed_directions <= universe, "serialized certificate uses an outside hinge direction")
    report = {
        "schema": "g0115-independent-serialized-residual-replay-v1",
        "result": "PASS",
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()
        }
        | {"script_sha256_at_start": script_hash},
        "term_census": {
            "fixed": len(fixed_terms),
            "repair": len(repair_terms),
            "missing": len(missing_terms),
            "total_candidate_terms": len(fixed_terms) + len(repair_terms),
        },
        "exact_semantics": {
            "complete_direction_universe": len(universe),
            "observed_direction_union": len(observed_directions),
            "combined_hinge_nonzeros": len(combined_hinges),
            "combined_linear": [str(value) for value in combined_linear],
            "combined_rational_lambda": str(rational_lambda(combined_linear)),
            "repair_missing_hinges_equal": True,
            "repair_lambda": str(rational_lambda(repair_linear)),
            "missing_lambda": str(rational_lambda(missing_linear)),
            "fixed_lambda": str(rational_lambda(fixed_linear)),
            "mutation_rejected": mutation_rejected,
        },
        "independence_boundary": (
            "Recomputed every serialized pair with the bound clean-room normal-form DP; "
            "did not load the CEGIS matrix, linear cache, modular solver, or exact checkpoint."
        ),
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "independent verifier changed during replay")
    write_exclusive(args.report.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
