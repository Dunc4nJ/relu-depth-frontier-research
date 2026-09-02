#!/usr/bin/env python3
"""Exact witness translation, verification, controls, and rational recovery.

The saved loopless systems contain one JSON object per symmetrized graph-pair
column.  A column has an integer linear part (``lin``) and a sparse integer
hinge part (``h``).  This tool keeps that representation authoritative: all
reported identities are checked with :class:`fractions.Fraction` on every row
in the saved system's row universe.
"""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import json
import math
import resource
import sys
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


SCHEMA = "max11-exactlift-witness-v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_columns(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else Path.open
    kwargs = {"mode": "rt", "encoding": "utf-8"}
    with opener(path, **kwargs) as stream:
        for line_number, line in enumerate(stream, 1):
            try:
                column = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
            if not {"A", "B", "lin", "h"}.issubset(column):
                raise ValueError(f"missing column field at {path}:{line_number}")
            yield column


def parse_fraction(raw: Any) -> Fraction:
    if isinstance(raw, int):
        return Fraction(raw)
    if not isinstance(raw, str):
        raise TypeError(f"coefficient must be an integer or string, got {type(raw)}")
    return Fraction(raw)


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def factor_integer(value: int) -> dict[str, int]:
    value = abs(value)
    factors: dict[str, int] = {}
    divisor = 2
    while divisor * divisor <= value:
        while value % divisor == 0:
            key = str(divisor)
            factors[key] = factors.get(key, 0) + 1
            value //= divisor
        divisor = 3 if divisor == 2 else divisor + 2
    if value > 1:
        key = str(value)
        factors[key] = factors.get(key, 0) + 1
    return factors


def canonical_key(
    left: Sequence[Sequence[int]], right: Sequence[Sequence[int]], n: int
) -> bytes:
    """Canonical S_n x side-swap key, matching the saved-system generator."""
    try:
        from pynauty import Graph, certificate
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise RuntimeError("pynauty is required for certificate translation") from exc

    def colored_certificate(first: Sequence[Sequence[int]], second: Sequence[Sequence[int]]) -> bytes:
        size = n + len(first) + len(second)
        adjacency = {vertex: [] for vertex in range(size)}
        edge_vertex = n
        for a, b in first:
            adjacency[edge_vertex] = [int(a), int(b)]
            edge_vertex += 1
        for a, b in second:
            adjacency[edge_vertex] = [int(a), int(b)]
            edge_vertex += 1
        graph = Graph(
            size,
            directed=False,
            adjacency_dict=adjacency,
            vertex_coloring=[
                set(range(n)),
                set(range(n, n + len(first))),
                set(range(n + len(first), size)),
            ],
        )
        return certificate(graph)

    return min(colored_certificate(left, right), colored_certificate(right, left))


def witness_coefficients(witness: dict[str, Any]) -> dict[int, Fraction]:
    coefficients: dict[int, Fraction] = defaultdict(Fraction)
    for entry in witness.get("coefficients", []):
        index = int(entry["column"])
        coefficients[index] += parse_fraction(entry["coefficient"])
    return {index: value for index, value in coefficients.items() if value}


def translate_upstream(system: Path, certificate: Path, output: Path) -> dict[str, Any]:
    upstream = json.loads(certificate.read_text(encoding="utf-8"))
    n = int(upstream["n"])

    by_key: dict[bytes, tuple[int, list[list[int]], list[list[int]]]] = {}
    for index, column in enumerate(iter_columns(system)):
        key = canonical_key(column["A"], column["B"], n)
        if key in by_key:
            raise ValueError(f"duplicate canonical column key at index {index}")
        by_key[key] = (index, column["A"], column["B"])

    translated: dict[int, Fraction] = defaultdict(Fraction)
    representatives: dict[int, tuple[list[list[int]], list[list[int]]]] = {}
    unmatched: list[int] = []
    for term_index, term in enumerate(upstream["terms"]):
        sides = term["pair"]
        zero_based = [
            [[int(a) - 1, int(b) - 1] for a, b in side]
            for side in sides
        ]
        match = by_key.get(canonical_key(zero_based[0], zero_based[1], n))
        if match is None:
            unmatched.append(term_index)
            continue
        column_index, left, right = match
        translated[column_index] += parse_fraction(term["coefficient"])
        representatives[column_index] = (left, right)

    if unmatched:
        raise ValueError(f"{len(unmatched)} upstream terms were not in the saved basis: {unmatched[:10]}")

    entries = []
    for index, coefficient in sorted(translated.items()):
        if not coefficient:
            continue
        left, right = representatives[index]
        entries.append(
            {
                "column": index,
                "coefficient": fraction_text(coefficient),
                "A": left,
                "B": right,
            }
        )

    payload = {
        "schema": SCHEMA,
        "n": n,
        "method": "canonical S_n x side-swap translation of pinned upstream certificate",
        "system": str(system),
        "system_sha256": sha256_file(system),
        "upstream_certificate": str(certificate),
        "upstream_sha256": sha256_file(certificate),
        "upstream_terms": len(upstream["terms"]),
        "support_size": len(entries),
        "coefficients": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def verify_witness(system: Path, witness_path: Path) -> dict[str, Any]:
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    coefficients = witness_coefficients(witness)
    if not coefficients:
        raise ValueError("witness has empty support")

    linear: list[Fraction] | None = None
    hinges: dict[str, Fraction] = defaultdict(Fraction)
    all_hinges: set[str] = set()
    seen: set[int] = set()
    expected = {int(entry["column"]): entry for entry in witness["coefficients"]}
    column_count = 0

    for index, column in enumerate(iter_columns(system)):
        column_count += 1
        all_hinges.update(column["h"])
        coefficient = coefficients.get(index)
        if coefficient is None:
            continue
        seen.add(index)
        if linear is None:
            linear = [Fraction() for _ in column["lin"]]
        entry = expected[index]
        if "A" in entry and entry["A"] != column["A"]:
            raise ValueError(f"witness A mismatch at column {index}")
        if "B" in entry and entry["B"] != column["B"]:
            raise ValueError(f"witness B mismatch at column {index}")
        for row, value in enumerate(column["lin"]):
            linear[row] += coefficient * int(value)
        for direction, value in column["h"].items():
            hinges[direction] += coefficient * int(value)

    missing = sorted(set(coefficients) - seen)
    if missing:
        raise ValueError(f"witness refers to missing columns: {missing[:10]}")
    assert linear is not None

    target = [Fraction() for _ in linear]
    target[-1] = Fraction(1)
    linear_residual = [actual - desired for actual, desired in zip(linear, target)]
    nonzero_hinges = {key: value for key, value in hinges.items() if value}
    good = not any(linear_residual) and not nonzero_hinges

    denominator_lcm = math.lcm(*(value.denominator for value in coefficients.values()))
    max_residuals = sorted(nonzero_hinges.items())[:10]
    return {
        "verdict": "PASS" if good else "FAIL",
        "exact": True,
        "n": len(linear),
        "system": str(system),
        "system_sha256": sha256_file(system),
        "witness": str(witness_path),
        "witness_sha256": sha256_file(witness_path),
        "columns_in_system": column_count,
        "support_size": len(coefficients),
        "rows_checked": len(all_hinges) + len(linear),
        "hinge_rows_checked": len(all_hinges),
        "linear_rows_checked": len(linear),
        "coefficient_denominator_lcm": denominator_lcm,
        "coefficient_denominator_factorization": factor_integer(denominator_lcm),
        "nonzero_linear_residuals": [
            {"row": row, "value": fraction_text(value)}
            for row, value in enumerate(linear_residual)
            if value
        ],
        "nonzero_hinge_residual_count": len(nonzero_hinges),
        "nonzero_hinge_residual_examples": [
            {"direction": direction, "value": fraction_text(value)}
            for direction, value in max_residuals
        ],
    }


def witness_to_upstream(system: Path, witness_path: Path, output: Path) -> dict[str, Any]:
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    n = int(witness["n"])
    coefficients = witness_coefficients(witness)
    terms = []
    seen = set()
    for index, column in enumerate(iter_columns(system)):
        coefficient = coefficients.get(index)
        if coefficient is None:
            continue
        seen.add(index)
        pair = [
            [[int(a) + 1, int(b) + 1] for a, b in side]
            for side in (column["A"], column["B"])
        ]
        terms.append({"coefficient": fraction_text(coefficient), "pair": pair})
    missing = sorted(set(coefficients) - seen)
    if missing:
        raise ValueError(f"witness refers to missing columns: {missing[:10]}")
    payload = {"n": n, "terms": terms}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def mutate_upstream(certificate: Path, output: Path, delta: Fraction) -> dict[str, Any]:
    payload = json.loads(certificate.read_text(encoding="utf-8"))
    for term in payload["terms"]:
        coefficient = parse_fraction(term["coefficient"])
        if coefficient:
            term["coefficient"] = fraction_text(coefficient + delta)
            break
    else:
        raise ValueError("certificate has no nonzero coefficient to mutate")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def mutate_witness(witness: Path, output: Path, delta: Fraction) -> dict[str, Any]:
    payload = json.loads(witness.read_text(encoding="utf-8"))
    for entry in payload.get("coefficients", []):
        coefficient = parse_fraction(entry["coefficient"])
        if coefficient:
            entry["coefficient"] = fraction_text(coefficient + delta)
            break
    else:
        raise ValueError("witness has no nonzero coefficient to mutate")
    payload["mutation"] = {
        "source_witness": str(witness),
        "source_witness_sha256": sha256_file(witness),
        "delta": fraction_text(delta),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def bind_upstream_verification(
    candidate: Path,
    verified_certificate: Path,
    verification_report: Path,
    verifier: Path,
    output: Path,
) -> dict[str, Any]:
    candidate_hash = sha256_file(candidate)
    verified_hash = sha256_file(verified_certificate)
    report = json.loads(verification_report.read_text(encoding="utf-8"))
    verifier_hash = sha256_file(verifier)
    checks = {
        "candidate_is_verified_certificate": candidate_hash == verified_hash,
        "report_verdict_pass": report.get("verdict") == "PASS",
        "report_certificate_hash_matches": report.get("certificate_sha256") == candidate_hash,
        "report_verifier_hash_matches": report.get("verifier_sha256") == verifier_hash,
    }
    payload = {
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "method": "byte identity to a hash-bound completed upstream verification",
        "candidate": str(candidate),
        "candidate_sha256": candidate_hash,
        "verified_certificate": str(verified_certificate),
        "verified_certificate_sha256": verified_hash,
        "verification_report": str(verification_report),
        "verification_report_sha256": sha256_file(verification_report),
        "verifier": str(verifier),
        "verifier_sha256": verifier_hash,
        "checks": checks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def scan_system(system: Path) -> tuple[int, int, dict[str, int]]:
    n = 0
    columns = 0
    row_index: dict[str, int] = {}
    for column in iter_columns(system):
        columns += 1
        if not n:
            n = len(column["lin"])
        elif n != len(column["lin"]):
            raise ValueError("inconsistent linear row count")
        for direction in column["h"]:
            if direction not in row_index:
                row_index[direction] = len(row_index)
    if not columns:
        raise ValueError("empty system")
    return n, columns, row_index


def pivot_columns(rref: Any, rank: int) -> list[int]:
    pivots: list[int] = []
    candidate = 0
    for row in range(rank):
        while candidate < rref.ncols() and not rref[row, candidate]:
            candidate += 1
        if candidate == rref.ncols():
            raise RuntimeError(f"could not find pivot for RREF row {row}")
        pivots.append(candidate)
        candidate += 1
    return pivots


def column_entries(column: dict[str, Any], row_index: dict[str, int]) -> Iterator[tuple[int, int]]:
    for direction, value in column["h"].items():
        yield row_index[direction], int(value)
    hinge_rows = len(row_index)
    for row, value in enumerate(column["lin"]):
        if value:
            yield hinge_rows + row, int(value)


def recover_exact(
    system: Path,
    n: int,
    prime: int,
    output: Path,
    report_path: Path,
    basis_cache: Path | None = None,
) -> dict[str, Any]:
    """Recover a sparse exact-Q solution using a modular column/row basis."""
    try:
        import flint
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise RuntimeError("python-flint is required for exact recovery") from exc

    started = time.monotonic()
    inferred_n, column_count, row_index = scan_system(system)
    if inferred_n != n:
        raise ValueError(f"requested n={n}, system has n={inferred_n}")
    row_count = len(row_index) + n
    timings: dict[str, float] = {}

    if basis_cache and basis_cache.exists():
        cache = json.loads(basis_cache.read_text(encoding="utf-8"))
        if cache["system_sha256"] != sha256_file(system) or int(cache["prime"]) != prime:
            raise ValueError("basis cache does not match system digest and prime")
        column_pivots = list(map(int, cache["column_pivots"]))
        row_pivots = list(map(int, cache["row_pivots"]))
        rank = len(column_pivots)
    else:
        phase = time.monotonic()
        modular = flint.nmod_mat(row_count, column_count, prime)
        for column_number, column in enumerate(iter_columns(system)):
            for row, value in column_entries(column, row_index):
                modular[row, column_number] = value % prime
        timings["build_full_modular_seconds"] = time.monotonic() - phase

        phase = time.monotonic()
        modular_rref, rank = modular.rref(inplace=True)
        column_pivots = pivot_columns(modular_rref, rank)
        timings["full_modular_rref_seconds"] = time.monotonic() - phase
        del modular, modular_rref
        gc.collect()

        phase = time.monotonic()
        pivot_position = {column: position for position, column in enumerate(column_pivots)}
        transposed_basis = flint.nmod_mat(rank, row_count, prime)
        for column_number, column in enumerate(iter_columns(system)):
            position = pivot_position.get(column_number)
            if position is None:
                continue
            for row, value in column_entries(column, row_index):
                transposed_basis[position, row] = value % prime
        timings["build_transposed_basis_seconds"] = time.monotonic() - phase

        phase = time.monotonic()
        transposed_rref, transpose_rank = transposed_basis.rref(inplace=True)
        if transpose_rank != rank:
            raise RuntimeError(f"basis transpose rank {transpose_rank} != rank {rank}")
        row_pivots = pivot_columns(transposed_rref, rank)
        timings["transposed_basis_rref_seconds"] = time.monotonic() - phase
        del transposed_basis, transposed_rref
        gc.collect()

        if basis_cache:
            basis_cache.parent.mkdir(parents=True, exist_ok=True)
            basis_cache.write_text(
                json.dumps(
                    {
                        "system": str(system),
                        "system_sha256": sha256_file(system),
                        "prime": prime,
                        "rank": rank,
                        "column_pivots": column_pivots,
                        "row_pivots": row_pivots,
                        "timings_seconds": timings,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n",
                encoding="utf-8",
            )

    phase = time.monotonic()
    column_position = {column: position for position, column in enumerate(column_pivots)}
    row_position = {row: position for position, row in enumerate(row_pivots)}
    square_rows = [[0] * rank for _ in range(rank)]
    representatives: dict[int, tuple[list[list[int]], list[list[int]]]] = {}
    for column_number, column in enumerate(iter_columns(system)):
        col = column_position.get(column_number)
        if col is None:
            continue
        representatives[column_number] = (column["A"], column["B"])
        for global_row, value in column_entries(column, row_index):
            row = row_position.get(global_row)
            if row is not None:
                square_rows[row][col] = value
    rhs_values = [0] * rank
    target_global_row = len(row_index) + n - 1
    if target_global_row not in row_position:
        raise RuntimeError("selected independent rows omit the sole nonzero target row")
    rhs_values[row_position[target_global_row]] = 1
    integer_matrix = flint.fmpz_mat(square_rows)
    integer_rhs = flint.fmpz_mat(rank, 1, rhs_values)
    timings["build_exact_square_seconds"] = time.monotonic() - phase
    del square_rows
    gc.collect()

    phase = time.monotonic()
    rational_matrix = flint.fmpq_mat(integer_matrix)
    rational_rhs = flint.fmpq_mat(integer_rhs)
    solution = rational_matrix.solve(rational_rhs, algorithm="dixon")
    timings["exact_dixon_solve_seconds"] = time.monotonic() - phase

    entries = []
    denominators = []
    for position, column_number in enumerate(column_pivots):
        coefficient = Fraction(str(solution[position, 0]))
        if not coefficient:
            continue
        denominators.append(coefficient.denominator)
        left, right = representatives[column_number]
        entries.append(
            {
                "column": column_number,
                "coefficient": fraction_text(coefficient),
                "A": left,
                "B": right,
            }
        )

    payload = {
        "schema": SCHEMA,
        "n": n,
        "method": "mod-p full column basis, independent row minor, exact FLINT Dixon solve",
        "prime": prime,
        "system": str(system),
        "system_sha256": sha256_file(system),
        "rank_mod_prime": rank,
        "row_count": row_count,
        "column_count": column_count,
        "support_size": len(entries),
        "coefficient_denominator_lcm": math.lcm(*denominators),
        "coefficients": entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verification = verify_witness(system, output)
    timings["total_seconds"] = time.monotonic() - started
    report = {
        "verdict": verification["verdict"],
        "witness": str(output),
        "witness_sha256": sha256_file(output),
        "system": str(system),
        "system_sha256": sha256_file(system),
        "prime": prime,
        "rank": rank,
        "rows": row_count,
        "columns": column_count,
        "support_size": len(entries),
        "coefficient_denominator_lcm": payload["coefficient_denominator_lcm"],
        "coefficient_denominator_factorization": factor_integer(
            payload["coefficient_denominator_lcm"]
        ),
        "timings_seconds": timings,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "verification": verification,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if verification["verdict"] != "PASS":
        raise RuntimeError("exact solution failed full-row verification")
    return report


def is_union_spanning_tree(column: dict[str, Any], n: int) -> bool:
    edges = {tuple(map(int, edge)) for edge in column["A"] + column["B"]}
    if len(edges) != n - 1:
        return False
    adjacency = [[] for _ in range(n)]
    for a, b in edges:
        if a == b:
            return False
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen = {0}
    stack = [0]
    while stack:
        vertex = stack.pop()
        for neighbor in adjacency[vertex]:
            if neighbor not in seen:
                seen.add(neighbor)
                stack.append(neighbor)
    return len(seen) == n


def tree_null_control(system: Path, prime: int, output: Path) -> dict[str, Any]:
    try:
        import flint
    except ImportError as exc:  # pragma: no cover - environment diagnostic
        raise RuntimeError("python-flint is required for the tree-null control") from exc

    started = time.monotonic()
    n, _, row_index = scan_system(system)
    selected = []
    for index, column in enumerate(iter_columns(system)):
        if is_union_spanning_tree(column, n):
            selected.append(index)
    selected_position = {column: position for position, column in enumerate(selected)}
    rows = len(row_index) + n
    matrix = flint.nmod_mat(rows, len(selected), prime)
    augmented = flint.nmod_mat(rows, len(selected) + 1, prime)
    for column_number, column in enumerate(iter_columns(system)):
        position = selected_position.get(column_number)
        if position is None:
            continue
        for row, value in column_entries(column, row_index):
            residue = value % prime
            matrix[row, position] = residue
            augmented[row, position] = residue
    augmented[len(row_index) + n - 1, len(selected)] = 1
    rank = matrix.rank()
    augmented_rank = augmented.rank()
    report = {
        "verdict": "PASS" if (len(selected), rank, augmented_rank) == (739, 360, 361) else "FAIL",
        "control": "n=9 beta=0 union-spanning-tree subfamily rejects MAX9",
        "system": str(system),
        "system_sha256": sha256_file(system),
        "prime": prime,
        "selected_columns": len(selected),
        "rows": rows,
        "rank_A": rank,
        "rank_augmented": augmented_rank,
        "consistent": rank == augmented_rank,
        "expected": {"selected_columns": 739, "rank_A": 360, "rank_augmented": 361},
        "seconds": time.monotonic() - started,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def write_report(report: dict[str, Any], path: Path | None) -> None:
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    translate = commands.add_parser("translate-upstream")
    translate.add_argument("--system", type=Path, required=True)
    translate.add_argument("--certificate", type=Path, required=True)
    translate.add_argument("--output", type=Path, required=True)

    verify = commands.add_parser("verify")
    verify.add_argument("--system", type=Path, required=True)
    verify.add_argument("--witness", type=Path, required=True)
    verify.add_argument("--report", type=Path)

    upstream = commands.add_parser("to-upstream")
    upstream.add_argument("--system", type=Path, required=True)
    upstream.add_argument("--witness", type=Path, required=True)
    upstream.add_argument("--output", type=Path, required=True)

    mutate = commands.add_parser("mutate-upstream")
    mutate.add_argument("--certificate", type=Path, required=True)
    mutate.add_argument("--output", type=Path, required=True)
    mutate.add_argument("--delta", default="1")

    mutate_exact = commands.add_parser("mutate-witness")
    mutate_exact.add_argument("--witness", type=Path, required=True)
    mutate_exact.add_argument("--output", type=Path, required=True)
    mutate_exact.add_argument("--delta", default="1")

    bind = commands.add_parser("bind-upstream-verification")
    bind.add_argument("--candidate", type=Path, required=True)
    bind.add_argument("--verified-certificate", type=Path, required=True)
    bind.add_argument("--verification-report", type=Path, required=True)
    bind.add_argument("--verifier", type=Path, required=True)
    bind.add_argument("--output", type=Path, required=True)

    recover = commands.add_parser("recover")
    recover.add_argument("--system", type=Path, required=True)
    recover.add_argument("--n", type=int, required=True)
    recover.add_argument("--prime", type=int, default=1_000_003)
    recover.add_argument("--output", type=Path, required=True)
    recover.add_argument("--report", type=Path, required=True)
    recover.add_argument("--basis-cache", type=Path)

    tree = commands.add_parser("tree-null-control")
    tree.add_argument("--system", type=Path, required=True)
    tree.add_argument("--prime", type=int, default=1_000_003)
    tree.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "translate-upstream":
        payload = translate_upstream(args.system, args.certificate, args.output)
        write_report(
            {
                "verdict": "PASS",
                "output": str(args.output),
                "support_size": payload["support_size"],
                "upstream_terms": payload["upstream_terms"],
            },
            None,
        )
        return 0
    if args.command == "verify":
        report = verify_witness(args.system, args.witness)
        write_report(report, args.report)
        return 0 if report["verdict"] == "PASS" else 1
    if args.command == "to-upstream":
        payload = witness_to_upstream(args.system, args.witness, args.output)
        write_report(
            {"verdict": "PASS", "output": str(args.output), "terms": len(payload["terms"])},
            None,
        )
        return 0
    if args.command == "mutate-upstream":
        payload = mutate_upstream(args.certificate, args.output, parse_fraction(args.delta))
        write_report(
            {"verdict": "PASS", "output": str(args.output), "terms": len(payload["terms"])},
            None,
        )
        return 0
    if args.command == "mutate-witness":
        payload = mutate_witness(args.witness, args.output, parse_fraction(args.delta))
        write_report(
            {
                "verdict": "PASS",
                "output": str(args.output),
                "support_size": len(payload["coefficients"]),
            },
            None,
        )
        return 0
    if args.command == "bind-upstream-verification":
        payload = bind_upstream_verification(
            args.candidate,
            args.verified_certificate,
            args.verification_report,
            args.verifier,
            args.output,
        )
        write_report(payload, None)
        return 0 if payload["verdict"] == "PASS" else 1
    if args.command == "recover":
        report = recover_exact(
            args.system,
            args.n,
            args.prime,
            args.output,
            args.report,
            args.basis_cache,
        )
        write_report(report, None)
        return 0
    if args.command == "tree-null-control":
        report = tree_null_control(args.system, args.prime, args.output)
        write_report(report, None)
        return 0 if report["verdict"] == "PASS" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    sys.exit(main())
