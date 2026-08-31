#!/usr/bin/env python3
"""Independent serialized-pair replay of the unrestricted degree-four MAX9 certificate."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
CERTIFICATE = HERE / "unrestricted_full_semantic_certificate_v1.json"
PREREGISTRATION = HERE / "UNRESTRICTED_FULL_SEMANTIC_PREREGISTRATION.md"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    CERTIFICATE: "628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e",
    PREREGISTRATION: "61e39e655912e0f967ae76c90676012c06d506305d64267533ebf73ee50ec017",
}


class DegreeFourReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DegreeFourReplayError(message)


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
    require(observed == EXPECTED, f"degree-four replay binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_degree4_replay_kernel", KERNEL_PATH)
    require(spec is not None and spec.loader is not None, "cannot load semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.bind_inputs()
    return module


def rational_lambda(linear: list[Fraction]) -> Fraction:
    n = len(linear)
    return sum(
        (
            Fraction((-1) ** (n - rank) * math.comb(n - 1, rank - 1)) * value
            for rank, value in enumerate(linear, start=1)
        ),
        Fraction(),
    )


def add_semantic(linear, hinges, semantic, coefficient: Fraction) -> None:
    for coordinate, value in enumerate(semantic[0]):
        linear[coordinate] += coefficient * int(value)
    for direction, value in semantic[1].items():
        updated = hinges.get(direction, Fraction()) + coefficient * int(value)
        if updated:
            hinges[direction] = updated
        else:
            hinges.pop(direction, None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    kernel = load_kernel()
    dp = kernel.load_dp()
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    require(
        document.get("schema") == "g0115-unrestricted-degree4-full-max9-certificate-v1"
        and document.get("n") == kernel.N
        and document.get("degree") == 4,
        "degree-four certificate schema drift",
    )
    terms = document["terms"]
    require(len(terms) == 395, "degree-four support census drift")
    columns = [int(term["column_index"]) for term in terms]
    signed_hashes = [str(term["signed_certificate_sha256"]) for term in terms]
    require(
        len(set(columns)) == len(columns)
        and len(set(signed_hashes)) == len(signed_hashes)
        and min(columns) == 0
        and max(columns) == 771,
        "degree-four support identity/order drift",
    )
    linear = [Fraction() for _ in range(kernel.N)]
    hinges: dict[tuple[int, ...], Fraction] = {}
    observed_directions: set[tuple[int, ...]] = set()
    semantics = []
    group_counts: Counter[str] = Counter()
    maximum_numerator_bits = 0
    maximum_denominator_bits = 0
    for position, term in enumerate(terms, start=1):
        pair = kernel.parse_pair(term["pair"])
        require(len(pair[0]) == len(pair[1]) == 4, "non-degree-four term escaped")
        coefficient = Fraction(term["coefficient"])
        semantic = kernel.normal_form(dp, pair, kernel.N)
        add_semantic(linear, hinges, semantic, coefficient)
        observed_directions.update(semantic[1])
        semantics.append(semantic)
        group_counts[str(term["group"])] += 1
        maximum_numerator_bits = max(maximum_numerator_bits, abs(coefficient.numerator).bit_length())
        maximum_denominator_bits = max(maximum_denominator_bits, coefficient.denominator.bit_length())
        if position % 64 == 0 or position == len(terms):
            print(f"G0115_DEGREE4_REPLAY {position}/{len(terms)}", flush=True)

    universe = set(kernel.direction_universe())
    target_linear = [Fraction() for _ in range(kernel.N - 1)] + [Fraction(1)]
    require(observed_directions <= universe, "degree-four certificate has outside hinge direction")
    require(not hinges, "degree-four certificate has nonzero hinge residual")
    require(linear == target_linear, "degree-four certificate linear target drift")
    require(rational_lambda(linear) == 1, "degree-four certificate rational Lambda drift")
    require(dict(group_counts) == {"retained": 328, "repair": 67}, "support group census drift")

    mutated_linear = linear.copy()
    mutated_hinges = dict(hinges)
    add_semantic(mutated_linear, mutated_hinges, semantics[0], Fraction(1))
    mutation_rejected = bool(mutated_hinges) or mutated_linear != target_linear
    require(mutation_rejected, "degree-four coefficient mutation escaped")
    public_control = kernel.certificate_replay(dp, kernel.CERT9, kernel.N, 4)
    require(
        public_control["hinges"] == 0
        and public_control["linear"] == ["0"] * 8 + ["1"],
        "public MAX9 control failed",
    )
    report = {
        "schema": "g0115-independent-unrestricted-degree4-max9-replay-v1",
        "result": "PASS",
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()
        }
        | {"script_sha256_at_start": script_hash},
        "support": {
            "terms": len(terms),
            "group_counts": dict(sorted(group_counts.items())),
            "minimum_column": min(columns),
            "maximum_column": max(columns),
            "unique_columns": len(set(columns)),
            "unique_signed_classes": len(set(signed_hashes)),
            "maximum_numerator_bits": maximum_numerator_bits,
            "maximum_denominator_bits": maximum_denominator_bits,
        },
        "exact_semantics": {
            "complete_direction_universe": len(universe),
            "observed_direction_union": len(observed_directions),
            "hinge_residual_nonzeros": len(hinges),
            "linear": [str(value) for value in linear],
            "rational_lambda": str(rational_lambda(linear)),
            "mutation_rejected": mutation_rejected,
        },
        "public_MAX9_control": public_control,
        "independence_boundary": (
            "Recomputed all 395 serialized degree-four pairs with the bound clean-room DP; "
            "did not load the unrestricted matrix, CEGIS report, modular solver, exact basis, "
            "residual certificate, or mixed-degree compiled identity."
        ),
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "Exact degree-four MAX9 identity in this lift-class span only; not coefficient "
            "transport, MAX10/MAX11, or induction."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "degree-four verifier changed during replay")
    write_exclusive(args.report.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
