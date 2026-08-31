#!/usr/bin/env python3
"""Independent all-term exact semantic replay of the compiled G-0115 MAX9 identity."""

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
CERTIFICATE = HERE / "compiled_full_max9_identity_v1.json"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    CERTIFICATE: "93ffa8bb00c6b774619f840b1de767c15ff98eb7b7c3f9a77ad73471f61bce32",
}


class FullReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise FullReplayError(message)


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
    require(observed == EXPECTED, f"full replay binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_full_replay_kernel", KERNEL_PATH)
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
        document.get("schema") == "g0115-compiled-full-max9-identity-v1"
        and document.get("n") == kernel.N
        and document.get("target") == "MAX9",
        "compiled certificate schema drift",
    )
    terms = document["terms"]
    require(len(terms) == 1217, "compiled term census drift")
    linear = [Fraction() for _ in range(kernel.N)]
    hinges: dict[tuple[int, ...], Fraction] = {}
    observed_directions: set[tuple[int, ...]] = set()
    semantic_by_term = []
    provenance_counts: Counter[str] = Counter()
    arity_counts: Counter[int] = Counter()
    degree_counts: Counter[int] = Counter()
    for position, term in enumerate(terms, start=1):
        pair = kernel.parse_pair(term["pair"])
        coefficient = Fraction(term["coefficient"])
        semantic = kernel.normal_form(dp, pair, kernel.N)
        add_semantic(linear, hinges, semantic, coefficient)
        observed_directions.update(semantic[1])
        semantic_by_term.append((coefficient, semantic))
        provenance = term["provenance"]
        provenance_counts[str(provenance["kind"])] += 1
        if provenance["kind"] == "embedded_lower_MAX":
            arity_counts[int(provenance["source_arity"])] += 1
        degree_counts[len(pair[0])] += 1
        if position % 64 == 0 or position == len(terms):
            print(f"G0115_FULL_REPLAY {position}/{len(terms)}", flush=True)

    universe = set(kernel.direction_universe())
    target_linear = [Fraction() for _ in range(kernel.N - 1)] + [Fraction(1)]
    require(observed_directions <= universe, "compiled identity has outside hinge direction")
    require(not hinges, "compiled identity has nonzero hinge residual")
    require(linear == target_linear, "compiled identity linear vector is not MAX9")
    require(rational_lambda(linear) == 1, "compiled identity rational Lambda drift")
    require(
        dict(provenance_counts)
        == {
            "coefficient_frozen_retained": 328,
            "coefficient_frozen_repair": 752,
            "embedded_lower_MAX": 137,
        },
        "compiled provenance census drift",
    )
    require(
        dict(sorted(arity_counts.items()))
        == {1: 1, 2: 1, 3: 1, 4: 1, 5: 3, 6: 4, 7: 57, 8: 69},
        "compiled lower-arity census drift",
    )

    mutation_index = next(
        index
        for index, (coefficient, semantic) in enumerate(semantic_by_term)
        if coefficient and (semantic[0] or semantic[1])
    )
    mutated_linear = linear.copy()
    mutated_hinges = dict(hinges)
    add_semantic(
        mutated_linear,
        mutated_hinges,
        semantic_by_term[mutation_index][1],
        Fraction(1),
    )
    mutation_rejected = bool(mutated_hinges) or mutated_linear != target_linear
    require(mutation_rejected, "full certificate coefficient mutation escaped")
    public_control = kernel.certificate_replay(dp, kernel.CERT9, kernel.N, 4)
    require(
        public_control["hinges"] == 0
        and public_control["linear"] == ["0"] * 8 + ["1"],
        "bound public MAX9 control failed",
    )

    report = {
        "schema": "g0115-independent-full-max9-replay-v1",
        "result": "PASS",
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()
        }
        | {"script_sha256_at_start": script_hash},
        "term_census": len(terms),
        "provenance_counts": dict(sorted(provenance_counts.items())),
        "lower_arity_counts": {str(key): value for key, value in sorted(arity_counts.items())},
        "degree_counts": {str(key): value for key, value in sorted(degree_counts.items())},
        "exact_semantics": {
            "complete_direction_universe": len(universe),
            "observed_direction_union": len(observed_directions),
            "hinge_residual_nonzeros": len(hinges),
            "linear": [str(value) for value in linear],
            "rational_lambda": str(rational_lambda(linear)),
            "mutation_index": mutation_index,
            "mutation_rejected": mutation_rejected,
        },
        "public_MAX9_control": public_control,
        "independence_boundary": (
            "Recomputed all 1,217 serialized pairs with the bound clean-room DP; did not load "
            "the residual certificate, compiler report, CEGIS cache, solver, or exact checkpoint."
        ),
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "Exact mixed-degree MAX9 identity only; not a MAX10/MAX11 identity or induction theorem."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "full verifier changed during replay")
    write_exclusive(args.report.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
