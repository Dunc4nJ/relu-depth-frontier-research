#!/usr/bin/env python3
"""Parallel exact driver for the pinned upstream certificate verifier.

This is intentionally independent of ``exactlift.py`` and the saved JSONL
systems.  Worker processes import the pinned upstream verifier by path and call
its ``read_pair`` and ``symmetrized_pair`` functions unchanged.  Only the outer
term loop and exact-Fraction aggregation are parallelized.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import resource
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_upstream(path: str):
    spec = importlib.util.spec_from_file_location("pinned_upstream_verify_certificate", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned upstream verifier {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_chunk(
    verifier_path: str, n: int, terms: list[dict[str, Any]]
) -> tuple[list[Fraction], dict[tuple[int, ...], Fraction], int]:
    upstream = load_upstream(verifier_path)
    linear = [Fraction() for _ in range(n)]
    hinges: dict[tuple[int, ...], Fraction] = defaultdict(Fraction)
    nonzero_terms = 0
    for term in terms:
        coefficient = Fraction(term["coefficient"])
        if not coefficient:
            continue
        nonzero_terms += 1
        left, right = upstream.read_pair(term["pair"], n)
        term_linear, term_hinges = upstream.symmetrized_pair(left, right, n)
        for row, value in enumerate(term_linear):
            linear[row] += coefficient * value
        for direction, value in term_hinges.items():
            hinges[direction] += coefficient * value
    return linear, dict(hinges), nonzero_terms


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def parallel_verify(
    verifier: Path, certificate: Path, workers: int, output: Path
) -> dict[str, Any]:
    if not 1 <= workers <= 6:
        raise ValueError("workers must be between 1 and the bead ceiling of 6")
    payload = json.loads(certificate.read_text(encoding="utf-8"))
    n = int(payload["n"])
    terms = payload["terms"]
    chunks = [terms[offset::workers] for offset in range(workers)]
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = [
            pool.submit(verify_chunk, str(verifier.resolve()), n, chunk)
            for chunk in chunks
            if chunk
        ]
        partials = [future.result() for future in futures]

    linear = [Fraction() for _ in range(n)]
    hinges: dict[tuple[int, ...], Fraction] = defaultdict(Fraction)
    nonzero_terms = 0
    for partial_linear, partial_hinges, partial_nonzero in partials:
        nonzero_terms += partial_nonzero
        for row, value in enumerate(partial_linear):
            linear[row] += value
        for direction, value in partial_hinges.items():
            hinges[direction] += value
    linear[-1] -= 1
    bad_linear = [(row, value) for row, value in enumerate(linear) if value]
    bad_hinges = [(direction, value) for direction, value in hinges.items() if value]
    report = {
        "verdict": "PASS" if not bad_linear and not bad_hinges else "FAIL",
        "method": "parallel outer loop over unchanged pinned upstream read_pair/symmetrized_pair",
        "exact": True,
        "verifier": str(verifier),
        "verifier_sha256": sha256_file(verifier),
        "certificate": str(certificate),
        "certificate_sha256": sha256_file(certificate),
        "n": n,
        "terms": len(terms),
        "nonzero_terms": nonzero_terms,
        "workers": workers,
        "seconds": time.monotonic() - started,
        "parent_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "child_max_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "nonzero_linear_residuals": [
            {"row": row, "value": fraction_text(value)} for row, value in bad_linear
        ],
        "nonzero_hinge_residual_count": len(bad_hinges),
        "nonzero_hinge_residual_examples": [
            {"direction": list(direction), "value": fraction_text(value)}
            for direction, value in sorted(bad_hinges)[:10]
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verifier", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = parallel_verify(args.verifier, args.certificate, args.workers, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
